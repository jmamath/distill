"""Hypothesis update decisions for the belief graph (Plan 9).

This module is the entry point that turns pass-2 signal claims into belief
updates. It owns the per-claim *decisions*; the merge/Beta *mechanics* live in
`topics.storage`. Decision 1 triages each claim to attach, open, route, or drop.
Decision 2 re-resolves an attached or opening claim's stance against the one
matched hypothesis. The deterministic belief-update/route mechanics (§4) and
the signal-consumption loop follow in later steps.

Public API:
    triage_claim(client, claim, hypotheses, candidate_themes, topic_config)
        → TriageDecision | None
    resolve_stance(client, claim, matched_hypothesis) → StanceDecision | None
    make_evidence_id(claim, hypothesis_id) → str
    open_hypothesis_record(decision, theme_ids, created_at) → dict

Run the tests offline (Gemini is mocked):
    PYTHONPATH=src pytest tests/test_hypothesis_updater.py
"""

import hashlib
import json
import logging
import re
import time
from collections.abc import Mapping

from pydantic import ValidationError
from google import genai
from google.genai import types

from config import SCORING_FALLBACK_MODEL, SCORING_MODEL
from topics.config import TopicConfig
from topics.models import StanceDecision, TriageDecision
from topics.prompts import build_stance_prompt, build_triage_prompt

logger = logging.getLogger(__name__)

# Same model pair and fallback discipline as pass-1/pass-2 (see topics.scoring).
# Matching is the loop's hardest call; a stronger dedicated model is deferred
# until Sub-task C shows quality sagging.
_MODELS = [SCORING_MODEL, SCORING_FALLBACK_MODEL]

_MAX_HYPOTHESIS_ID_LENGTH = 60
_HYPOTHESIS_ID_HASH_LENGTH = 10


# ---------------------------------------------------------------------------
# §2 Decision 1 — triage (model judgment)
# ---------------------------------------------------------------------------


def _call_triage_model(client: genai.Client, prompt: str, model: str) -> str:
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        ),
    )
    return response.text.strip()


def triage_claim(
    client: genai.Client,
    claim: str,
    hypotheses: list[dict],
    candidate_themes: list[str],
    topic_config: TopicConfig,
) -> TriageDecision | None:
    """Decide where one claim goes: attach, open, route, or drop.

    Matching and route-out are one model call, not two — a claim is often only
    recognizable as a non-evidence artifact *because* nothing attaches to it.
    Tries each model in the scoring pair with one retry before falling back.
    An `attach` naming a hypothesis_id outside `hypotheses` is rejected as a
    parse failure, never coerced.

    Args:
        client: Configured Gemini client.
        claim: The claim text extracted by pass-2.
        hypotheses: Current hypothesis records (hypotheses.json shape).
        candidate_themes: Theme ids from the claim's signal frontmatter.
        topic_config: The active topic configuration.

    Returns:
        A validated TriageDecision, or None if all models fail — the caller
        skips the claim and the unstamped signal is re-opened on the next run.
    """
    prompt = build_triage_prompt(claim, hypotheses, candidate_themes, topic_config)
    candidate_ids = {hyp["id"] for hyp in hypotheses}

    for model in _MODELS:
        raw = ""
        for attempt in range(2):
            try:
                raw = _call_triage_model(client, prompt, model)
                return TriageDecision.model_validate(
                    json.loads(raw), context={"candidate_ids": candidate_ids}
                )
            except (json.JSONDecodeError, ValidationError) as exc:
                logger.warning("triage: model %s parse failed (%s) — raw: %s", model, exc, raw)
                break
            except Exception as exc:
                if "404" in str(exc):
                    logger.warning("triage: model %s not found, trying fallback", model)
                    break
                if attempt == 0:
                    logger.warning(
                        "triage: model %s attempt 1 failed (%s), retrying in 5s", model, exc
                    )
                    time.sleep(5)
                else:
                    logger.warning("triage: model %s exhausted, trying fallback", model)

    logger.error("triage: all models failed for claim %r", claim)
    return None


# ---------------------------------------------------------------------------
# §3 Decision 2 — stance resolution (model judgment)
# ---------------------------------------------------------------------------


def _call_stance_model(client: genai.Client, prompt: str, model: str) -> str:
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        ),
    )
    return response.text.strip()


def resolve_stance(
    client: genai.Client,
    claim: str,
    matched_hypothesis: Mapping[str, object],
) -> StanceDecision | None:
    """Resolve how one evidential claim bears on its matched hypothesis.

    Pass-2 extracts the claim text but does not assign direction, because a
    stance has no stable meaning until the hypothesis is named. The validated
    result is always `for`, `against`, or `mixed`; `neutral` and malformed
    responses are rejected rather than stored. Tries each scoring model with
    one retry before falling back.

    Args:
        client: Configured Gemini client.
        claim: The claim text extracted by pass-2.
        matched_hypothesis: The existing or newly opened hypothesis record.

    Returns:
        A validated StanceDecision, or None if all models fail. The caller
        must skip the claim so its signal remains eligible for a later retry.

    Raises:
        KeyError: if the matched hypothesis lacks `id` or `statement`.
    """
    prompt = build_stance_prompt(claim, matched_hypothesis)

    for model in _MODELS:
        raw = ""
        for attempt in range(2):
            try:
                raw = _call_stance_model(client, prompt, model)
                return StanceDecision.model_validate(json.loads(raw))
            except (json.JSONDecodeError, ValidationError) as exc:
                logger.warning(
                    "stance: model %s parse failed (%s) — raw: %s",
                    model,
                    exc,
                    raw,
                )
                break
            except Exception as exc:
                if "404" in str(exc):
                    logger.warning("stance: model %s not found, trying fallback", model)
                    break
                if attempt == 0:
                    logger.warning(
                        "stance: model %s attempt 1 failed (%s), retrying in 5s",
                        model,
                        exc,
                    )
                    time.sleep(5)
                else:
                    logger.warning("stance: model %s exhausted, trying fallback", model)

    logger.error("stance: all models failed for claim %r", claim)
    return None


# ---------------------------------------------------------------------------
# §2 mechanics — deterministic consequences of a triage decision
# ---------------------------------------------------------------------------


def make_evidence_id(claim: str, hypothesis_id: str) -> str:
    """Return the stable dedup id for one claim attached to one hypothesis.

    Keyed on claim hash + hypothesis_id so the same claim re-matched to the
    same hypothesis (e.g. a crashed run re-opening an unstamped signal) maps
    to the same evidence record and attaches once. The same claim matched to a
    *different* hypothesis is distinct evidence and gets a distinct id.

    Args:
        claim: The claim text; hashed after whitespace stripping.
        hypothesis_id: Id of the matched (or newly opened) hypothesis.

    Returns:
        A stable, filesystem-safe evidence id embedding the hypothesis id.
    """
    claim_hash = hashlib.sha256(claim.strip().encode()).hexdigest()[:10]
    return f"ev_{hypothesis_id}_{claim_hash}"


def _make_hypothesis_id(statement: str) -> str:
    """Return a stable, collision-resistant id for a non-blank statement.

    The readable prefix is bounded so the full id stays within
    `_MAX_HYPOTHESIS_ID_LENGTH`; the digest preserves distinctions beyond that
    prefix. Statements with no ASCII slug use a generic readable prefix.

    Raises:
        ValueError: if `statement` contains no non-whitespace text.
    """
    normalized_statement = " ".join(statement.split())
    if not normalized_statement:
        raise ValueError("hypothesis statement must not be blank")

    slug = re.sub(r"[^a-z0-9]+", "_", normalized_statement.casefold()).strip("_")
    digest = hashlib.sha256(normalized_statement.casefold().encode()).hexdigest()[
        :_HYPOTHESIS_ID_HASH_LENGTH
    ]
    max_prefix_length = (
        _MAX_HYPOTHESIS_ID_LENGTH - _HYPOTHESIS_ID_HASH_LENGTH - 1
    )
    prefix = slug[:max_prefix_length].rstrip("_") or "hypothesis"
    return f"{prefix}_{digest}"


def open_hypothesis_record(
    decision: TriageDecision,
    theme_ids: list[str],
    created_at: str,
) -> dict:
    """Build the hypothesis record for an `open` triage decision.

    The record starts at the uniform prior Beta(1, 1) — this is also how a
    genuinely new uncertainty enters the store (an "open question" is just a
    low-evidence hypothesis near its prior). The id is derived from the
    statement, so re-opening the same statement yields the same id and
    `storage.merge_by_id` keeps one record. `action_posture` is derived at
    read time and never stored.

    Args:
        decision: A TriageDecision whose decision is `open`.
        theme_ids: Theme ids grouping the new bet (from the signal's
            candidate themes).
        created_at: ISO date stamped as created_at / last_updated_at.

    Returns:
        A new hypothesis record in the hypotheses.json shape.

    Raises:
        ValueError: if `decision` is not an `open` decision or its statement is
            blank.
    """
    if decision.decision != "open":
        raise ValueError(f"expected an open decision, got {decision.decision!r}")
    if decision.new_statement is None:
        raise ValueError("open decision requires a new_statement")

    comparison = (
        decision.comparison.model_dump() if decision.comparison is not None else None
    )
    return {
        "id": _make_hypothesis_id(decision.new_statement),
        "statement": decision.new_statement,
        "theme_ids": list(theme_ids),
        "status": "active",
        "belief": {"alpha": 1.0, "beta": 1.0},
        "comparison": comparison,
        "created_at": created_at,
        "last_updated_at": created_at,
    }
