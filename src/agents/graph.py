"""LangGraph workflow wiring all agents together.

CLI:  python -m src.agents.graph "Is Golconda Fort open on Mondays?"
"""
from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field
from datetime import date

from langgraph.graph import END, START, StateGraph

from src.agents.data_analyst import DataAnalyst
from src.agents.itinerary import build_itinerary
from src.agents.planner import plan
from src.agents.responder import SourceBook, build_context, respond, template_answer
from src.agents.retriever import retrieve
from src.agents.state import AgentState, Constraints
from src.agents.validator import validate
from src.config import WEEKDAYS
from src.data.tables import TableRegistry
from src.guardrails.input_guard import check_input
from src.guardrails.output_guard import finalise
from src.llm.groq_client import LLMClient
from src.utils.errors import VisitIQError
from src.utils.logging import get_logger
from src.vectordb.store import VectorStore

log = get_logger("graph")
MAX_ATTEMPTS = 2


@dataclass
class Deps:
    store: VectorStore
    registry: TableRegistry
    llm: LLMClient | None = None
    today: date | None = None
    analyst: DataAnalyst = field(init=False)

    def __post_init__(self) -> None:
        self.analyst = DataAnalyst(self.registry)


def _trace(agent: str, detail: str, start: float) -> list[dict]:
    return [{"agent": agent, "detail": detail, "ms": int((time.perf_counter() - start) * 1000)}]


def build_graph(deps: Deps):
    session: dict = {}  # per-run scratch space for objects that are not JSON-serialisable (SourceBook)

    def input_guard(state: AgentState) -> dict:
        t = time.perf_counter()
        res = check_input(state["query"])
        update = {"clean_query": res.clean_query or state["query"], "blocked": not res.allowed,
                  "guard_category": res.category, "warnings": res.warnings,
                  "trace": _trace("Input guardrails", f"{res.category}" + (f"; flags: {', '.join(res.flags)}" if res.flags else ""), t)}
        if not res.allowed:
            update["final_answer"] = res.message
        session["flags"] = res.flags
        return update

    def refuse(state: AgentState) -> dict:
        return {"trace": _trace("Safe refusal", f"category={state.get('guard_category')}", time.perf_counter())}

    def planner(state: AgentState) -> dict:
        t = time.perf_counter()
        today = deps.today or date.today()
        attractions = deps.registry.get("attractions")
        names = list(attractions["name"]) if attractions is not None else []
        out, method = plan(state["clean_query"], deps.llm, today, names)
        c: Constraints = out.constraints
        warnings = []
        if "itinerary" in out.intents and not c.day:
            c.day, c.date = WEEKDAYS[today.weekday()], today.isoformat()
            warnings.append(f"No day was mentioned, so I planned for today ({c.day}).")
        summary = ", ".join(f"{k}={v}" for k, v in c.model_dump(exclude_defaults=True).items() if k != "topics")
        return {"intents": out.intents, "constraints": c.model_dump(), "warnings": warnings,
                "trace": _trace("Planner", f"[{method}] intents={out.intents}; {summary}", t)}

    def retriever(state: AgentState) -> dict:
        t = time.perf_counter()
        c = Constraints(**state["constraints"])
        warnings = []
        try:
            hits = retrieve(state["clean_query"], c, state["intents"], deps.store)
        except VisitIQError as exc:
            hits, warnings = [], [exc.user_message]
        if deps.store.count() == 0:
            warnings.append("The knowledge base is empty. Click 'Load sample documents' in the sidebar or upload files.")
        detail = f"{len(hits)} chunks; top: " + ", ".join(f"{h['metadata'].get('source')} ({h['similarity']:.2f})" for h in hits[:3])
        return {"retrieved": hits, "warnings": warnings, "trace": _trace("Retriever", detail, t)}

    def analyst(state: AgentState) -> dict:
        t = time.perf_counter()
        c = Constraints(**state["constraints"])
        analysis = deps.analyst.analyse(c, state["intents"])
        parts = []
        for key in ("attraction_status", "attractions", "excluded"):
            if analysis.get(key):
                parts.append(f"{key}={len(analysis[key])}")
        if analysis.get("restaurants"):
            parts.append(f"restaurants={analysis['restaurants']['total_matches']}")
        if analysis.get("events"):
            parts.append(f"events={len(analysis['events']['items'])}")
        if analysis.get("route"):
            parts.append("route=" + ("found" if analysis["route"].get("found") else "not found"))
        missing = [k for k in ("attractions", "restaurants", "events", "metro_lines") if deps.registry.get(k) is None]
        warnings = [f"Structured data missing for: {', '.join(missing)}. Load the sample CSV/Excel files."] if missing else []
        return {"analysis": analysis, "warnings": warnings, "trace": _trace("Data analyst", "; ".join(parts) or "no table results", t)}

    def itinerary(state: AgentState) -> dict:
        t = time.perf_counter()
        it = build_itinerary(Constraints(**state["constraints"]), state.get("analysis") or {}, deps.analyst)
        detail = (f"{len([s for s in it['stops'] if s['type'] != 'free'])} stops, total Rs {it['total']}"
                  + (f" / budget Rs {it['budget']} ({'OK' if it['feasible'] else 'OVER'})" if it.get("budget") else ""))
        return {"itinerary": it, "trace": _trace("Itinerary planner", detail, t)}

    def responder(state: AgentState) -> dict:
        t = time.perf_counter()
        attempts = state.get("attempts", 0) + 1
        feedback = (state.get("validation") or {}).get("issues") if attempts > 1 else None
        draft, book, facts, used = respond(state, deps.llm, feedback)
        session["book"], session["facts"] = book, facts
        mode = f"LLM ({deps.llm.last_model_used})" if used and deps.llm else "template (no LLM)"
        return {"draft": draft, "attempts": attempts, "llm_used": used, "facts": facts,
                "sources": book.items, "trace": _trace("Responder", f"attempt {attempts}, {mode}, {len(book.items)} sources", t)}

    def validator(state: AgentState) -> dict:
        t = time.perf_counter()
        book: SourceBook = session.get("book") or build_context(state)[0]
        facts = session.get("facts") or []
        result = validate(state["draft"], book, facts, state, deps.analyst)
        update: dict = {}
        if result["passed"]:
            detail = f"passed ({result['citations']} citations"
        elif state.get("attempts", 1) < MAX_ATTEMPTS and state.get("llm_used"):
            result["retry"] = True
            detail = "failed, asking responder to fix: " + "; ".join(result["issues"])
        else:
            fallback = template_answer(state, book, facts)
            if state.get("llm_used"):
                fallback = "_Some details in the generated answer could not be verified, so here are the verified facts:_\n\n" + fallback
            update["draft"] = fallback
            update["llm_used"] = False
            detail = "failed twice; replaced with verified template answer: " + "; ".join(result["issues"])
        checks = result.get("checks") or {}
        if checks.get("stops_checked"):
            detail += f"; itinerary stops open {checks['stops_open']}/{checks['stops_checked']}"
            if checks.get("budget_ok") is not None:
                detail += f", budget {'OK' if checks['budget_ok'] else 'exceeded (stated)'}"
        if result["passed"]:
            detail += ")"
        update.update({"validation": result, "trace": _trace("Validator", detail, t)})
        return update

    def output_guard(state: AgentState) -> dict:
        t = time.perf_counter()
        flags = list(session.get("flags", []))
        answer = finalise(state["draft"], flags)
        return {"final_answer": answer, "trace": _trace("Output guardrails", "PII redaction, safety and check-before-you-go notes", t)}

    g = StateGraph(AgentState)
    for name, fn in [("input_guard", input_guard), ("refuse", refuse), ("planner", planner), ("retriever", retriever),
                     ("analyst", analyst), ("itinerary", itinerary), ("responder", responder),
                     ("validator", validator), ("output_guard", output_guard)]:
        g.add_node(name, fn)
    g.add_edge(START, "input_guard")
    g.add_conditional_edges("input_guard", lambda s: "refuse" if s.get("blocked") else "planner",
                            {"refuse": "refuse", "planner": "planner"})
    g.add_edge("refuse", END)
    g.add_edge("planner", "retriever")
    g.add_conditional_edges("retriever",
                            lambda s: "analyst" if {"data_filter", "itinerary", "transport"} & set(s["intents"]) else "responder",
                            {"analyst": "analyst", "responder": "responder"})
    g.add_conditional_edges("analyst", lambda s: "itinerary" if "itinerary" in s["intents"] else "responder",
                            {"itinerary": "itinerary", "responder": "responder"})
    g.add_edge("itinerary", "responder")
    g.add_edge("responder", "validator")
    g.add_conditional_edges("validator", lambda s: "responder" if s["validation"].get("retry") else "output_guard",
                            {"responder": "responder", "output_guard": "output_guard"})
    g.add_edge("output_guard", END)
    return g.compile()


def run_query(query: str, deps: Deps) -> AgentState:
    graph = build_graph(deps)
    try:
        return graph.invoke({"query": query, "attempts": 0, "warnings": [], "trace": []})
    except VisitIQError as exc:
        log.warning("Handled error for query: %s", exc.user_message)
        return {"query": query, "final_answer": exc.user_message, "warnings": [], "trace": [], "blocked": True,
                "guard_category": "error"}
    except Exception:
        log.exception("Unexpected error while answering %r", query)
        return {"query": query, "final_answer": "Sorry, something went wrong while answering. The error was logged; "
                                                "please try again or rephrase.", "warnings": [], "trace": [],
                "blocked": True, "guard_category": "error"}


def default_deps() -> Deps:
    return Deps(store=VectorStore(), registry=TableRegistry(), llm=LLMClient())


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    q = " ".join(sys.argv[1:]) or "Is Golconda Fort open on Mondays, and how do I get there by metro from Hitech City?"
    result = run_query(q, default_deps())
    print(result.get("final_answer"))
    print("\n--- agent trace ---")
    for step in result.get("trace", []):
        print(f"{step['agent']:18s} {step['ms']:5d} ms  {step['detail']}")
    for w in result.get("warnings", []):
        print("warning:", w)
