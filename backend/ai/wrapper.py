"""
PBI-19 — Shared structured-output wrapper.

Single entry-point for every Gemini call in the AI module.
All three prompts (blueprint, generate, regenerate) use this instead of
duplicating the retry/logging boilerplate.

Public API:
    from ai.wrapper import call_structured

    result = call_structured(
        model=fast_model,
        contents=[*file_parts, prompt],
        schema=BlueprintSchema,
        retries=1,
        label="blueprint",
    )

    # With optional post-parse validation (e.g. marks-sum check):
    result = call_structured(
        model=pro_model,
        contents=[prompt],
        schema=PaperSchema,
        retries=1,
        label="generate",
        post_validate=lambda p: _validate_paper(p, blueprint),
    )
"""

from __future__ import annotations

import json
import logging
from typing import Callable, Optional, Type, TypeVar

from google.genai import types
from pydantic import BaseModel, ValidationError

from ai.client import client

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


def call_structured(
    model: str,
    contents: list,
    schema: Type[T],
    *,
    retries: int = 1,
    label: str = "ai",
    post_validate: Optional[Callable[[T], None]] = None,
) -> T:
    """
    Call Gemini with structured JSON output and retry on parse / validation failures.

    Args:
        model:          Gemini model name (e.g. fast_model, pro_model).
        contents:       List of content parts passed to generate_content.
        schema:         Pydantic model class to validate the response against.
        retries:        Number of additional attempts after the first.
                        retries=1 → 2 total attempts (initial + 1 retry).
        label:          Short string prepended to log messages (e.g. "blueprint").
        post_validate:  Optional callable(result) → None.  Raise ValueError or
                        any subclass to trigger a retry with an error message in
                        the log.  Use this for domain-specific constraints (e.g.
                        marks-sum checks) that Pydantic cannot enforce.

    Returns:
        A validated instance of `schema`.

    Raises:
        RuntimeError:  All attempts exhausted.  The last exception is chained.
    """
    total_attempts = retries + 1
    last_exc: Exception | None = None

    for attempt in range(1, total_attempts + 1):
        logger.info(
            "[%s] Attempt %d / %d — model=%s",
            label,
            attempt,
            total_attempts,
            model,
        )

        raw = ""
        try:
            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=schema,
                ),
            )
            raw = response.text
            logger.debug("[%s] Raw response (%d chars):\n%s", label, len(raw), raw)

            result: T = schema.model_validate_json(raw)

            if post_validate is not None:
                post_validate(result)

            if attempt > 1:
                logger.info(
                    "[%s] Succeeded on attempt %d after earlier failure.", label, attempt
                )
            return result

        except (ValidationError, json.JSONDecodeError, ValueError) as exc:
            last_exc = exc
            logger.warning(
                "[%s] Parse/validation failure on attempt %d / %d: %s\n"
                "Raw text was:\n%s",
                label,
                attempt,
                total_attempts,
                exc,
                raw,
            )

    raise RuntimeError(
        f"[{label}] All {total_attempts} attempt(s) failed. Last error: {last_exc}"
    ) from last_exc
