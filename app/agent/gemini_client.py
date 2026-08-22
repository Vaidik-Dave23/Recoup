"""Minimal asynchronous Gemini JSON client for recovery-agent nodes."""

from __future__ import annotations

import json
from typing import Any

from google import genai
from google.genai import types

from app.core.config import settings


class GeminiCallError(RuntimeError):
    """Raised when Gemini cannot return a parseable JSON object."""


async def call_json(
    system_prompt: str,
    user_prompt: str,
    *,
    max_tokens: int = 600,
    temperature: float = 0.3,
) -> dict[str, Any]:
    """Call Gemini with JSON mode and return its parsed object response."""
    if not settings.gemini_api_key:
        raise GeminiCallError("GEMINI_API_KEY is not configured")

    try:
        client = genai.Client(api_key=settings.gemini_api_key)
        response = await client.aio.models.generate_content(
            model=settings.gemini_model,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                max_output_tokens=max_tokens,
                temperature=temperature,
            ),
        )
        raw = response.text
    except Exception as exc:  # noqa: BLE001
        raise GeminiCallError(f"Gemini API call failed: {exc}") from exc

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
