"""Minimal asynchronous Gemini JSON client for recovery-agent nodes."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from google import genai
from google.genai import types

from app.core.config import settings


class GeminiCallError(RuntimeError):
    """Raised when Gemini cannot return a parseable JSON object."""


_TRANSIENT_MARKERS = ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED", "500")
_MAX_ATTEMPTS = 3
_BACKOFF_SECONDS = (1, 2)  # delay before attempt 2, then before attempt 3


def _is_transient(exc: Exception) -> bool:
    text = str(exc)
    return any(marker in text for marker in _TRANSIENT_MARKERS)


async def call_json(
    system_prompt: str,
    user_prompt: str,
    *,
    max_tokens: int = 1024,
    temperature: float = 0.3,
) -> dict[str, Any]:
    """Call Gemini with JSON mode and return its parsed object response.

    Retries up to _MAX_ATTEMPTS times, but only on transient errors (model
    overloaded / rate limited / server-side 5xx) -- a malformed-JSON or auth
    error will not be retried since retrying can't fix those.

    thinking_budget=0 disables Gemini's internal "thinking" tokens for this
    call. Without it, gemini-2.5-flash can silently spend most of
    max_output_tokens on invisible reasoning before writing the actual JSON
    answer, truncating it mid-object -- these are short, structured
    classification/decision tasks that don't need extended chain-of-thought.
    """
    if not settings.gemini_api_key:
        raise GeminiCallError("GEMINI_API_KEY is not configured")

    client = genai.Client(api_key=settings.gemini_api_key)
    last_error: Exception | None = None

    for attempt in range(_MAX_ATTEMPTS):
        try:
            response = await client.aio.models.generate_content(
                model=settings.gemini_model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type="application/json",
                    max_output_tokens=max_tokens,
                    temperature=temperature,
                    thinking_config=types.ThinkingConfig(thinking_budget=0),
                ),
            )
            raw = response.text
            break
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt < _MAX_ATTEMPTS - 1 and _is_transient(exc):
                await asyncio.sleep(_BACKOFF_SECONDS[attempt])
                continue
            raise GeminiCallError(f"Gemini API call failed: {exc}") from exc
    else:
        raise GeminiCallError(f"Gemini API call failed: {last_error}")

    if not raw:
        raise GeminiCallError("Gemini returned an empty response")

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise GeminiCallError(
            f"Could not parse Gemini JSON response: {raw[:300]!r}"
        ) from exc

    if not isinstance(parsed, dict):
        raise GeminiCallError(f"Expected a JSON object, got {type(parsed).__name__}")

    return parsed