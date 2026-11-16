"""Build docs/architecture.png (infographic) and docs/VisitIQ_Architecture.pptx (7 slides).

Usage:  python scripts/build_ppt.py
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

DOCS = Path(__file__).resolve().parent.parent / "docs"
RED, DARK, LIGHT, GREY, WHITE = "C0392B", "2C3E50", "FDEDEC", "7F8C8D", "FFFFFF"

FLOW = [("Question", "user"), ("Input guardrails", "PII, injection,\nunsafe, medical"), ("Planner", "intents +\nconstraints"),
        ("Retriever", "ChromaDB +\nMiniLM"), ("Data analyst", "pandas tables,\nmetro graph"),
        ("Itinerary planner", "hours, budget,\ntimeline"), ("Responder", "Groq gpt-oss-120b\n(cited)"),
        ("Validator", "citations,\nnumbers, hours"), ("Output guardrails", "safety +\ncheck before you go"),
        ("Cited answer", "with sources\nand agent trace")]


# --- PNG infographic --------------------------------------------------------------------
def _font(size: int, bold: bool = False):
    for name in (["segoeuib.ttf", "arialbd.ttf"] if bold else ["segoeui.ttf", "arial.ttf"]):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def build_png(path: Path) -> None:
    W, H = 1800, 900
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 110], fill="#" + RED)
    d.text((50, 28), "VisitIQ - multi-agent RAG for Hyderabad tourists", font=_font(46, True), fill="white")

    # ingestion lane
    d.text((50, 140), "1. Ingestion (upload time)", font=_font(30, True), fill="#" + DARK)
    ing = ["PDF / TXT / CSV / XLSX", "Validate: type, 19 MB,\nmagic bytes, empty", "Relevance check\n(Hyderabad tourism)",
           "Sanitise + chunk\n(800 / 120)", "MiniLM embeddings\n-> ChromaDB", "Tables -> pandas\nregistry"]
    bw, gap, y = 255, 40, 200
    for i, label in enumerate(ing):
        x = 50 + i * (bw + gap)
        d.rounded_rectangle([x, y, x + bw, y + 110], 18, fill="#" + LIGHT, outline="#" + RED, width=3)
        d.multiline_text((x + bw / 2, y + 55), label, font=_font(22), fill="#" + DARK, anchor="mm", align="center")
        if i:
            d.line([x - gap + 4, y + 55, x - 6, y + 55], fill="#" + GREY, width=4)
            d.polygon([(x - 6, y + 47), (x - 6, y + 63), (x + 2, y + 55)], fill="#" + GREY)

    # query lane (two rows)
    d.text((50, 370), "2. Answering (LangGraph state machine)", font=_font(30, True), fill="#" + DARK)
    bw, bh, gap = 318, 120, 35
    rows = [FLOW[:5], FLOW[5:]]
    for r, row in enumerate(rows):
        y = 430 + r * 200
        for i, (title, sub) in enumerate(row):
            x = 50 + i * (bw + gap) if r == 0 else 50 + (4 - i) * (bw + gap)
            fill = "#" + (WHITE if title in ("Question", "Cited answer") else LIGHT)
            d.rounded_rectangle([x, y, x + bw, y + bh], 18, fill=fill, outline="#" + RED, width=3)
            d.text((x + bw / 2, y + 32), title, font=_font(26, True), fill="#" + RED, anchor="mm")
            d.multiline_text((x + bw / 2, y + 80), sub, font=_font(20), fill="#" + DARK, anchor="mm", align="center")
    grey = "#" + GREY
    for i in range(4):  # row 0 left-to-right, row 1 right-to-left
        x = 50 + (i + 1) * (bw + gap)
        d.line([x - gap + 4, 490, x - 8, 490], fill=grey, width=4)
        d.polygon([(x - 8, 482), (x - 8, 498), (x, 490)], fill=grey)
        x2 = 50 + i * (bw + gap) + bw
        d.line([x2 + gap - 4, 690, x2 + 8, 690], fill=grey, width=4)
        d.polygon([(x2 + 8, 682), (x2 + 8, 698), (x2, 690)], fill=grey)
    cx = 50 + 4 * (bw + gap) + bw / 2
    d.line([cx, 550, cx, 622], fill=grey, width=4)
    d.polygon([(cx - 8, 622), (cx + 8, 622), (cx, 630)], fill=grey)
    d.text((50, 830), "Validator fails -> one retry -> verified template answer", font=_font(22), fill=grey)
    d.text((W - 600, 830), "Facts from code, words from the LLM", font=_font(24, True), fill="#" + RED)
    img.save(path)


def build_flow_png(path: Path) -> None:
    """Detailed flow matching the Mermaid chart in docs/SPEC.md section 4."""
    W, H = 1950, 1010
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    grey, red, dark = "#" + GREY, "#" + RED, "#" + DARK
    bw, bh, step = 200, 90, 235
    boxes: dict[str, tuple[int, int, int, int]] = {}

    def box(key, col, y, label, style="step"):
        x = 50 + col * step
        fill = {"step": "#" + LIGHT, "io": "white", "store": "#EAF2F8", "stop": "#FDEBD0"}[style]
        outline = {"store": "#2471A3", "stop": "#CA6F1E"}.get(style, red)
        if style == "store":
            d.rounded_rectangle([x, y, x + bw, y + bh], 40, fill=fill, outline=outline, width=3)
        else:
            d.rounded_rectangle([x, y, x + bw, y + bh], 14, fill=fill, outline=outline, width=3)
        d.multiline_text((x + bw / 2, y + bh / 2), label, font=_font(19, True), fill=dark, anchor="mm", align="center")
        boxes[key] = (x, y, x + bw, y + bh)

    def cx(key, dx=0):
        return (boxes[key][0] + boxes[key][2]) / 2 + dx

    def line(points, label=None, dashed=False, label_at=0, colour=grey):
        for (x1, y1), (x2, y2) in zip(points, points[1:]):
            if dashed:
                length = max(abs(x2 - x1), abs(y2 - y1))
                for s in range(0, int(length), 18):
                    t1, t2 = s / length, min(s + 10, length) / length
                    d.line([x1 + (x2 - x1) * t1, y1 + (y2 - y1) * t1, x1 + (x2 - x1) * t2, y1 + (y2 - y1) * t2],
                           fill=colour, width=3)
            else:
                d.line([x1, y1, x2, y2], fill=colour, width=3)
        (x1, y1), (x2, y2) = points[-2], points[-1]
        ux, uy = (x2 > x1) - (x2 < x1), (y2 > y1) - (y2 < y1)
        px, py = -uy, ux
        d.polygon([(x2, y2), (x2 - 12 * ux + 7 * px, y2 - 12 * uy + 7 * py),
                   (x2 - 12 * ux - 7 * px, y2 - 12 * uy - 7 * py)], fill=colour)
        if label:
            (lx1, ly1), (lx2, ly2) = points[label_at], points[label_at + 1]
            d.text(((lx1 + lx2) / 2 + 6, (ly1 + ly2) / 2 - 6), label, font=_font(16), fill=colour,
                   anchor="lm" if lx1 == lx2 else "mb")

    d.rectangle([0, 0, W, 90], fill=red)
    d.text((50, 22), "VisitIQ - detailed agent and data flow", font=_font(40, True), fill="white")

    # ingestion lane
    d.text((50, 115), "1. Ingestion (upload time)", font=_font(28, True), fill=dark)
    ya, yb = 170, 320
    for i, (k, lbl, st) in enumerate([("up", "Upload file", "io"), ("val", "File validator\next, size, magic bytes", "step"),
                                      ("load", "Loader\nPDF/TXT/CSV/XLSX", "step"), ("rel", "Relevance check\nHyderabad tourism?", "step"),
                                      ("san", "Injection\nsanitiser", "step"), ("chk", "Chunker\n800 / 120", "step"),
                                      ("emb", "HF embeddings\nMiniLM-L6-v2", "step"), ("db", "ChromaDB", "store")]):
        box(k, i, ya, lbl, st)
    box("err1", 1, yb, "Friendly error\nmessage", "stop")
    box("tab", 2, yb, "Table registry\n(pandas)", "store")
    box("err2", 3, yb, "Friendly error\nmessage", "stop")
    for a, b in [("up", "val"), ("val", "load"), ("load", "rel"), ("rel", "san"), ("san", "chk"), ("chk", "emb"), ("emb", "db")]:
        line([(boxes[a][2], ya + bh / 2), (boxes[b][0], ya + bh / 2)])
    line([(cx("val"), ya + bh), (cx("val"), yb)], "reject", colour="#CA6F1E")
    line([(cx("load"), ya + bh), (cx("load"), yb)], "tables")
    line([(cx("rel"), ya + bh), (cx("rel"), yb)], "reject", colour="#CA6F1E")

    # answering lane
    d.text((50, 470), "2. Answering (LangGraph)", font=_font(28, True), fill=dark)
    yd, ye = 620, 830
    for i, (k, lbl, st) in enumerate([("q", "User question", "io"), ("ig", "Input\nguardrails", "step"), ("pl", "Planner", "step"),
                                      ("rt", "Retriever", "step"), ("an", "Data analyst", "step"),
                                      ("it", "Itinerary\nplanner", "step"), ("rs", "Responder", "step"), ("vd", "Validator", "step")]):
        box(k, i, yd, lbl, st)
    box("ref", 1, ye, "Safe refusal", "stop")
    box("ans", 6, ye, "Answer with\ncitations", "io")
    box("og", 7, ye, "Output\nguardrails", "step")
    for a, b in [("q", "ig"), ("ig", "pl"), ("pl", "rt")]:
        line([(boxes[a][2], yd + bh / 2), (boxes[b][0], yd + bh / 2)])
    line([(boxes["rt"][2], yd + bh / 2), (boxes["an"][0], yd + bh / 2)])
    d.text((cx("an"), yd + bh + 8), "data / itinerary intent", font=_font(15), fill=grey, anchor="mt")
    line([(boxes["an"][2], yd + bh / 2), (boxes["it"][0], yd + bh / 2)])
    d.text((cx("it"), yd + bh + 8), "itinerary intent", font=_font(15), fill=grey, anchor="mt")
    line([(boxes["it"][2], yd + bh / 2), (boxes["rs"][0], yd + bh / 2)])
    line([(boxes["rs"][2], yd + bh / 2), (boxes["vd"][0], yd + bh / 2)])
    line([(cx("ig"), yd + bh), (cx("ig"), ye)], "blocked", colour="#CA6F1E")
    line([(cx("vd", 40), yd + bh), (cx("vd", 40), ye)], "pass")
    line([(boxes["og"][0], ye + bh / 2), (boxes["ans"][2], ye + bh / 2)])
    line([(cx("vd", -40), yd + bh), (cx("vd", -40), yd + bh + 60), (cx("rs", 40), yd + bh + 60), (cx("rs", 40), yd + bh)],
         "fail: 1 retry", label_at=1, colour=red)
    # results also flow straight to the responder
    line([(cx("rt", 40), yd), (cx("rt", 40), yd - 45), (cx("rs", 40), yd - 45), (cx("rs", 40), yd)],
         "retrieved chunks", label_at=1)
    line([(cx("an", 40), yd), (cx("an", 40), yd - 22), (cx("rs", -40), yd - 22), (cx("rs", -40), yd)])
    # reads from the stores
    line([(cx("db"), ya + bh), (cx("db"), 540), (cx("rt", -40), 540), (cx("rt", -40), yd)], "semantic search",
         dashed=True, label_at=1, colour="#2471A3")
    line([(cx("tab"), yb + bh), (cx("tab"), 515), (cx("an", -40), 515), (cx("an", -40), yd)], "pandas filters",
         dashed=True, label_at=1, colour="#2471A3")

    legend = [("#" + LIGHT, red, "agent / step"), ("#EAF2F8", "#2471A3", "data store"), ("#FDEBD0", "#CA6F1E", "error / refusal")]
    for i, (f, o, t) in enumerate(legend):
        x = 50 + i * 300
        d.rounded_rectangle([x, 955, x + 40, 985], 6, fill=f, outline=o, width=2)
        d.text((x + 52, 970), t, font=_font(18), fill=dark, anchor="lm")
    img.save(path)


# --- PPTX ---------------------------------------------------------------------------------
def _rgb(hex_: str) -> RGBColor:
    return RGBColor.from_string(hex_)


def _title(slide, text: str, sub: str | None = None) -> None:
    bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(1.0))
    bar.fill.solid(); bar.fill.fore_color.rgb = _rgb(RED); bar.line.fill.background()
    tf = bar.text_frame; tf.text = text
    p = tf.paragraphs[0]; p.font.size = Pt(30); p.font.bold = True; p.font.color.rgb = _rgb(WHITE)
    if sub:
        tb = slide.shapes.add_textbox(Inches(0.5), Inches(1.1), Inches(12.3), Inches(0.5))
        tb.text_frame.text = sub
        tb.text_frame.paragraphs[0].font.size = Pt(16); tb.text_frame.paragraphs[0].font.color.rgb = _rgb(GREY)


def _box(slide, x, y, w, h, title, body="", fill=LIGHT, title_size=16, body_size=12):
    s = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    s.fill.solid(); s.fill.fore_color.rgb = _rgb(fill); s.line.color.rgb = _rgb(RED); s.line.width = Pt(1.5)
    tf = s.text_frame; tf.word_wrap = True
    tf.text = title
    p = tf.paragraphs[0]; p.font.bold = True; p.font.size = Pt(title_size); p.font.color.rgb = _rgb(RED)
    p.alignment = PP_ALIGN.CENTER
    for line in body.split("\n") if body else []:
        q = tf.add_paragraph(); q.text = line; q.font.size = Pt(body_size); q.font.color.rgb = _rgb(DARK)
        q.alignment = PP_ALIGN.CENTER
    return s


def _arrow(slide, x1, y1, x2, y2):
    c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    c.line.color.rgb = _rgb(GREY); c.line.width = Pt(2)
    c.line._get_or_add_ln().append(_arrow_head())


def _arrow_head():
    from pptx.oxml.ns import qn
    from lxml import etree
    el = etree.Element(qn("a:tailEnd")); el.set("type", "triangle")
    return el


def _bullets(slide, x, y, w, h, items, size=16):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame; tf.word_wrap = True
    for i, it in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = "• " + it; p.font.size = Pt(size); p.font.color.rgb = _rgb(DARK); p.space_after = Pt(8)


def build_pptx(path: Path, png: Path) -> None:
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    blank = prs.slide_layouts[6]

    # 1 title
    s = prs.slides.add_slide(blank)
    bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
    bg.fill.solid(); bg.fill.fore_color.rgb = _rgb(RED); bg.line.fill.background()
    tb = s.shapes.add_textbox(Inches(0.8), Inches(2.3), Inches(11.5), Inches(3))
    tf = tb.text_frame; tf.text = "VisitIQ"
    tf.paragraphs[0].font.size = Pt(66); tf.paragraphs[0].font.bold = True; tf.paragraphs[0].font.color.rgb = _rgb(WHITE)
    for line, size in [("A multi-agent RAG tourist assistant for Hyderabad", 28),
                       ("Streamlit · LangGraph · ChromaDB · HuggingFace MiniLM · Groq gpt-oss-120b", 18)]:
        p = tf.add_paragraph(); p.text = line; p.font.size = Pt(size); p.font.color.rgb = _rgb(WHITE)

    # 2 architecture infographic
    s = prs.slides.add_slide(blank)
    _title(s, "Architecture at a glance", "Upload-time ingestion feeds a LangGraph pipeline of six agents and two guardrail layers")
    s.shapes.add_picture(str(png), Inches(0.6), Inches(1.7), width=Inches(12.1))

    # 3 ingestion
    s = prs.slides.add_slide(blank)
    _title(s, "Ingestion: only clean, relevant Hyderabad data gets in")
    steps = [("Upload", "PDF, TXT, CSV, XLSX\nmulti-file"), ("Validate", "extension + magic bytes\n≤ 19 MB, not empty"),
             ("Relevance", "Hyderabad + tourism\nkeyword score, LLM tiebreak"), ("Sanitise", "strip prompt-injection\nlines"),
             ("Chunk + embed", "800 chars / 120 overlap\nall-MiniLM-L6-v2"), ("Store", "ChromaDB (cosine)\n+ pandas tables")]
    for i, (t, b) in enumerate(steps):
        x = 0.4 + i * 2.15
        _box(s, x, 2.0, 1.9, 1.6, t, b)
        if i:
            _arrow(s, x - 0.25, 2.8, x, 2.8)
    _box(s, 0.4, 4.4, 6.0, 2.3, "Rejected with a clear message",
         "sample.jpg, archive.zip → unsupported type\n20 MB file → too large\nfake_pdf.pdf → corrupt\nempty.csv → empty\n"
         "pharmacy_invoice.pdf, bengaluru_guide.pdf → not relevant", fill=WHITE)
    _box(s, 6.8, 4.4, 6.1, 2.3, "Accepted (sample set)",
         "9 files → 431 chunks\n8 structured tables: attractions, restaurants, events,\nmetro lines, metro fares, airport buses, "
         "day passes, local fares", fill=WHITE)

    # 4 agents
    s = prs.slides.add_slide(blank)
    _title(s, "Agent roles", "Deterministic code computes the facts; the LLM only plans and writes")
    agents = [("Planner", "classifies intent\nextracts day, area, budget,\nveg, origin/destination"),
              ("Retriever", "semantic search\nsub-question expansion\nsimilarity threshold"),
              ("Data analyst", "filters tables with pandas\nopening-hours checks\nDijkstra metro route + fare"),
              ("Itinerary planner", "morning / lunch / afternoon\n/ evening event\nbudget fitting"),
              ("Responder", "answers only from [S#]\nsources; template when\nno LLM"),
              ("Validator", "citations exist, numbers\ngrounded, stops open,\nbudget stated; 1 retry")]
    for i, (t, b) in enumerate(agents):
        x, y = 0.5 + (i % 3) * 4.2, 1.8 + (i // 3) * 2.7
        _box(s, x, y, 3.9, 2.3, t, b, title_size=20, body_size=14)

    # 5 guardrails
    s = prs.slides.add_slide(blank)
    _title(s, "Reliability and safety guardrails")
    cols = [("Input", ["Prompt injection refused", "Illegal / unsafe requests refused", "Medical & legal advice refused (108 for emergencies)",
                       "Other cities and off-topic refused", "PII (phone, email, Aadhaar, card, PAN, passport) redacted"]),
            ("Reasoning", ["Facts computed by code, not the LLM", "Every fact labelled [S#] with file / page / row",
                           "Validator re-checks prices, times, hours, budget", "One retry, then a verified template answer"]),
            ("Output", ["\"I don't have that information\" when unsure", "Safety note for night / solo / scam topics",
                        "\"Check before you go\" on prices and timings", "Medical advice scrubbed; no prompt leaks"])]
    for i, (t, items) in enumerate(cols):
        x = 0.5 + i * 4.2
        _box(s, x, 1.4, 3.9, 0.7, t, title_size=20)
        _bullets(s, x, 2.3, 3.9, 4.5, items, size=15)

    # 6 results
    s = prs.slides.add_slide(blank)
    _title(s, "Verified behaviour", "scripts/smoke_test.py - 12 / 12 acceptance cases pass; 132 automated pytest tests")
    res = [("A1", "Charminar day, Friday, ₹2,000", "7 stops, ₹1,505, Friday-closed sites excluded"),
           ("A2", "Golconda Monday + metro", "Open 09:00-17:30; Blue Line 4 stops ₹18 + auto"),
           ("A3", "Veg, Banjara Hills, < ₹500", "8 restaurants, every filter met"),
           ("E1-E3", "Bad uploads", "jpg/zip, 20 MB, pharmacy/Bengaluru rejected"),
           ("E4-E7", "Unsafe / off-scope", "Mumbai, injection, medical, illegal refused"),
           ("E8-E9", "Impossible requests", "₹100 plan flagged; 2 AM closed + safety note")]
    for i, (cid, q, out) in enumerate(res):
        y = 1.8 + i * 0.85
        _box(s, 0.6, y, 1.4, 0.7, cid, title_size=16)
        _bullets(s, 2.2, y + 0.05, 4.5, 0.7, [q], size=16)
        _bullets(s, 6.8, y + 0.05, 6.0, 0.7, [out], size=16)

    # 7 limitations
    s = prs.slides.add_slide(blank)
    _title(s, "Limitations and next steps")
    _box(s, 0.5, 1.4, 6.0, 0.7, "Limitations", title_size=20)
    _bullets(s, 0.5, 2.3, 6.0, 4.8, ["Static sample data: no live prices, traffic or weather", "Hyderabad only, English only, no OCR",
                                     "Fixed travel-time estimates", "Keyword guardrails can be evaded or over-block",
                                     "Groq free-tier rate limits (falls back to rule-based mode)"])
    _box(s, 6.9, 1.4, 6.0, 0.7, "Next steps", title_size=20)
    _bullets(s, 6.9, 2.3, 6.0, 4.8, ["Live feeds: metro status, event APIs, maps routing", "Hybrid BM25 + vector search and re-ranking",
                                     "LLM-based safety classifier alongside the rules", "Multi-day trips and user preferences",
                                     "Telugu / Hindi support"])
    prs.save(path)


def main() -> None:
    DOCS.mkdir(exist_ok=True)
    png = DOCS / "architecture.png"
    build_png(png)
    build_flow_png(DOCS / "detailed_flow.png")
    build_pptx(DOCS / "VisitIQ_Architecture.pptx", png)
    print(f"Wrote {png}\nWrote {DOCS / 'detailed_flow.png'}\nWrote {DOCS / 'VisitIQ_Architecture.pptx'}")


if __name__ == "__main__":
    main()
