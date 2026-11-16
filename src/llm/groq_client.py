"""Groq LLM client with retries, exponential backoff, timeout and a fallback model."""
from __future__ import annotations

import time

from src.config import GROQ_API_KEY, GROQ_FALLBACK_MODEL, GROQ_MODEL, LLM_MAX_RETRIES, LLM_TIMEOUT_S
from src.utils.errors import LLMUnavailableError
from src.utils.logging import get_logger

log = get_logger("llm")

PLACEHOLDER_KEYS = {"", "your_groq_api_key_here", "changeme"}


class LLMClient:
    def __init__(self, api_key: str | None = None, model: str = GROQ_MODEL, fallback_model: str = GROQ_FALLBACK_MODEL):
        self.api_key = (api_key if api_key is not None else GROQ_API_KEY).strip()
        self.model = model
        self.fallback_model = fallback_model
        self.last_model_used: str | None = None
        self.status = "ready"
        self._client = None
        if self.api_key in PLACEHOLDER_KEYS:
            self.status = "GROQ_API_KEY is not set in .env"
        else:
            try:
                from groq import Groq
                self._client = Groq(api_key=self.api_key, timeout=LLM_TIMEOUT_S, max_retries=0)
            except Exception as exc:
                self.status = f"Groq client could not start: {exc}"
                log.exception("Groq init failed")

    @property
    def available(self) -> bool:
        return self._client is not None

    def _call(self, model: str, messages: list[dict], json_mode: bool, temperature: float, max_tokens: int) -> str:
        import groq

        kwargs = {"model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens}
        if model.startswith("openai/gpt-oss"):
            # Reasoning tokens count towards max_tokens; keep reasoning short and out of the content.
            kwargs.update(reasoning_effort="low", include_reasoning=False, max_tokens=max_tokens + 1024)
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        delay = 1.0
        last_exc: Exception | None = None
        for attempt in range(1, LLM_MAX_RETRIES + 1):
            try:
                resp = self._client.chat.completions.create(**kwargs)
                self.last_model_used = model
                return resp.choices[0].message.content or ""
            except groq.AuthenticationError as exc:
                self._client = None
                self.status = "The Groq API key was rejected (401). Check GROQ_API_KEY in .env."
                raise LLMUnavailableError(self.status, detail=str(exc)) from exc
            except (groq.RateLimitError, groq.APIConnectionError, groq.APITimeoutError, groq.InternalServerError) as exc:
                last_exc = exc
                log.warning("Groq %s attempt %d/%d failed: %s", model, attempt, LLM_MAX_RETRIES, type(exc).__name__)
                if attempt < LLM_MAX_RETRIES:
                    time.sleep(delay)
                    delay *= 2
            except groq.APIStatusError as exc:  # e.g. model decommissioned / bad request
                last_exc = exc
                log.warning("Groq %s status error: %s", model, exc)
                break
        raise LLMUnavailableError(detail=f"{model}: {last_exc}")

    def chat(self, messages: list[dict], json_mode: bool = False, temperature: float = 0.1, max_tokens: int = 900) -> str:
        if not self.available:
            raise LLMUnavailableError(f"LLM not available: {self.status}")
        try:
            return self._call(self.model, messages, json_mode, temperature, max_tokens)
        except LLMUnavailableError:
            if not self.available or self.fallback_model == self.model:
                raise
            log.warning("Primary model failed; trying fallback %s", self.fallback_model)
            return self._call(self.fallback_model, messages, json_mode, temperature, max_tokens)

    def ping(self) -> bool:
        try:
            return bool(self.chat([{"role": "user", "content": "Reply with the single word: ok"}], max_tokens=5))
        except LLMUnavailableError as exc:
            log.warning("Ping failed: %s", exc.user_message)
            return False
