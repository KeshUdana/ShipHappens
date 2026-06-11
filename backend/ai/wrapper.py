"""
PBI-19 / Feature #6 — Shared structured-output wrapper.

Single entry-point for every Gemini call in the AI module.
All AI prompts (blueprint, generate, regenerate, answer_key, dedup) use this
wrapper instead of duplicating the retry / logging / cost-tracking boilerplate.

Public API:
    from ai.wrapper import call_structured, UsageRecord

    result = call_structured(
        model=fast_model,
        contents=[*file_parts, prompt],
        schema=BlueprintSchema,
        retries=1,
        label="blueprint",
        on_usage=my_db_writer,        # optional: persist token costs
    )
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Callable, Optional, Type, TypeVar

from google.genai import types
from pydantic import BaseModel, ValidationError

from ai.client import client

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


# ── Cost tracking (Feature #6) ───────────────────────────────────────────────
#
# Approximate per-million-token prices in USD (Sep 2025 Gemini list prices).
# Update here if Google revises pricing.

_PRICING_USD_PER_MTOKENS: dict[str, tuple[float, float]] = {
    # model:           (input_per_mtok, output_per_mtok)
    "gemini-2.5-flash": (0.075, 0.30),
    "gemini-2.5-pro":   (1.25,  10.00),
    "gemini-2.5-flash-lite": (0.05, 0.20),
    "text-embedding-004": (0.15, 0.0),
    "gemini-embedding-001": (0.15, 0.0),
}


@dataclass
class UsageRecord:
    """One Gemini call's usage stats — passed to `on_usage` callbacks."""

    label: str
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float
    status: str          # "success" | "failed"
    error_message: Optional[str] = None


def _estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Best-effort cost estimate. Returns 0 for unknown models."""
    if model not in _PRICING_USD_PER_MTOKENS:
        # Strip version suffix and try again (e.g. 'gemini-2.5-pro-001' -> 'gemini-2.5-pro')
        for known in _PRICING_USD_PER_MTOKENS:
            if model.startswith(known):
                in_price, out_price = _PRICING_USD_PER_MTOKENS[known]
                return (input_tokens / 1_000_000) * in_price + (output_tokens / 1_000_000) * out_price
        return 0.0
    in_price, out_price = _PRICING_USD_PER_MTOKENS[model]
    return (input_tokens / 1_000_000) * in_price + (output_tokens / 1_000_000) * out_price


def _extract_usage(response) -> tuple[int, int, int]:
    """Pull (input, output, total) tokens from a generate_content response."""
    meta = getattr(response, "usage_metadata", None)
    if meta is None:
        return (0, 0, 0)
    inp = getattr(meta, "prompt_token_count", 0) or 0
    out = getattr(meta, "candidates_token_count", 0) or 0
    tot = getattr(meta, "total_token_count", 0) or (inp + out)
    return (inp, out, tot)


OnUsage = Callable[[UsageRecord], None]

# Global usage hooks — notified for every call_structured attempt in addition
# to any per-call on_usage callback. Lets out-of-band consumers (eval runner,
# cost dashboards) observe token spend without threading a callback through
# every public AI function.
_usage_hooks: list[OnUsage] = []


def add_usage_hook(hook: OnUsage) -> None:
    if hook not in _usage_hooks:
        _usage_hooks.append(hook)


def remove_usage_hook(hook: OnUsage) -> None:
    if hook in _usage_hooks:
        _usage_hooks.remove(hook)


def _emit_usage(record: UsageRecord, on_usage: Optional[OnUsage]) -> None:
    for hook in [*(_usage_hooks), *([on_usage] if on_usage else [])]:
        try:
            hook(record)
        except Exception:
            logger.exception("Usage hook raised; ignoring.")


def call_structured(
    model: str,
    contents: list,
    schema: Type[T],
    *,
    retries: int = 1,
    label: str = "ai",
    post_validate: Optional[Callable[[T], None]] = None,
    on_usage: Optional[OnUsage] = None,
) -> T:
    """
    Call Gemini with structured JSON output. Retries on parse/validation failures.

    Args:
        model:          Gemini model name (e.g. fast_model, pro_model).
        contents:       List of content parts passed to generate_content.
        schema:         Pydantic model class to validate the response against.
        retries:        Additional attempts after the first (retries=1 → 2 total).
        label:          Short string prepended to log messages (e.g. "blueprint").
        post_validate:  Optional callable(result) → None. Raise ValueError to retry.
        on_usage:       Optional callable(UsageRecord) → None. Called after EVERY
                        attempt — success or failure — so callers can persist
                        token usage / cost to the DB (api_usage_log table).

    Returns:
        A validated instance of `schema`.

    Raises:
        RuntimeError:  All attempts exhausted. Last exception chained.
    """
    total_attempts = retries + 1
    last_exc: Exception | None = None

    for attempt in range(1, total_attempts + 1):
        logger.info(
            "[%s] Attempt %d / %d — model=%s", label, attempt, total_attempts, model,
        )

        raw = ""
        response = None
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

            # Record usage on success
            inp, out, tot = _extract_usage(response)
            _emit_usage(UsageRecord(
                label=label, model=model,
                input_tokens=inp, output_tokens=out, total_tokens=tot,
                cost_usd=_estimate_cost(model, inp, out),
                status="success",
            ), on_usage)

            if attempt > 1:
                logger.info("[%s] Succeeded on attempt %d.", label, attempt)
            return result

        except (ValidationError, json.JSONDecodeError, ValueError) as exc:
            last_exc = exc
            logger.warning(
                "[%s] Parse/validation failure on attempt %d / %d: %s\n"
                "Raw text was:\n%s",
                label, attempt, total_attempts, exc, raw,
            )
            # Record usage on parse failure too (tokens were still spent)
            if response is not None:
                inp, out, tot = _extract_usage(response)
                _emit_usage(UsageRecord(
                    label=label, model=model,
                    input_tokens=inp, output_tokens=out, total_tokens=tot,
                    cost_usd=_estimate_cost(model, inp, out),
                    status="failed",
                    error_message=f"parse: {exc}",
                ), on_usage)

    if response is None:
        # All attempts failed before we even got a response (e.g. quota)
        _emit_usage(UsageRecord(
            label=label, model=model,
            input_tokens=0, output_tokens=0, total_tokens=0, cost_usd=0.0,
            status="failed", error_message=str(last_exc),
        ), on_usage)

    raise RuntimeError(
        f"[{label}] All {total_attempts} attempt(s) failed. Last error: {last_exc}"
    ) from last_exc
