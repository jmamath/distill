"""Topic-aware signal scoring pipeline.

Pass-1 (this file) scores each NormalizedItem against the topic thesis using
its abstract/summary only. Items that do not clear SCORING_THRESHOLD are
dropped here — no full-text fetch, no disk write.

Pass-2 (added in 15.3b) fetches full text for cleared items and produces the
final FullScore that is persisted to signals/.

Public API:
    pass1_filter(items, topic_config) → list[tuple[NormalizedItem, AbstractScore]]
"""

import json
import logging
import time

from google import genai
from google.genai import types

from config import GEMINI_API_KEY, SCORING_FALLBACK_MODEL, SCORING_MODEL, SCORING_THRESHOLD
from sources.base import NormalizedItem
from topics.config import TopicConfig
from topics.models import AbstractScore
from topics.prompts import build_pass1_prompt

logger = logging.getLogger(__name__)

_MODELS = [SCORING_MODEL, SCORING_FALLBACK_MODEL]

_PASS1_RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "relevance": {"type": "INTEGER"},
        "reason": {"type": "STRING"},
    },
    "required": ["relevance", "reason"],
}


def _call_model(client: genai.Client, prompt: str, model: str) -> str:
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=_PASS1_RESPONSE_SCHEMA,
        ),
    )
    return response.text.strip()


def _score_one(
    client: genai.Client,
    item: NormalizedItem,
    topic_config: TopicConfig,
) -> AbstractScore | None:
    """Score a single item against the topic thesis using its abstract only.

    Tries each model in _MODELS with one retry before moving to the fallback.
    Returns None if all models fail — the caller drops the item.
    """
    prompt = build_pass1_prompt(item, topic_config)

    for model in _MODELS:
        for attempt in range(2):
            try:
                raw = _call_model(client, prompt, model)
                data = json.loads(raw)
                return AbstractScore(
                    relevance=int(data["relevance"]),
                    reason=str(data["reason"]),
                )
            except Exception as exc:
                if "404" in str(exc):
                    logger.warning("pass1: model %s not found, trying fallback", model)
                    break
                if attempt == 0:
                    logger.warning(
                        "pass1: model %s attempt 1 failed (%s), retrying in 5s", model, exc
                    )
                    time.sleep(5)
                else:
                    logger.warning("pass1: model %s exhausted, trying fallback", model)

    logger.error("pass1: all models failed for item %r", item.url)
    return None


def pass1_filter(
    items: list[NormalizedItem],
    topic_config: TopicConfig,
) -> list[tuple[NormalizedItem, AbstractScore]]:
    """Score items against the topic thesis using abstract/summary only.

    Each item is scored individually with one LLM call. Items that score below
    SCORING_THRESHOLD or fail scoring entirely are dropped and logged. No disk
    writes occur in this function.

    Args:
        items: Normalized items from one or more source adapters.
        topic_config: The active topic configuration (thesis, taxonomy, scope).

    Returns:
        Pairs of (item, score) for items that cleared the threshold, in input
        order. Pass-2 receives this list to continue processing.
    """
    if not items:
        return []

    client = genai.Client(api_key=GEMINI_API_KEY)
    results: list[tuple[NormalizedItem, AbstractScore]] = []

    for item in items:
        score = _score_one(client, item, topic_config)
        if score is None:
            logger.warning("pass1: dropping %r — scoring failed on all models", item.url)
            continue
        if score.relevance < SCORING_THRESHOLD:
            logger.info(
                "pass1: dropping %r (relevance=%d < threshold=%d): %s",
                item.url, score.relevance, SCORING_THRESHOLD, score.reason,
            )
            continue
        logger.info(
            "pass1: keeping %r (relevance=%d): %s",
            item.url, score.relevance, score.reason,
        )
        results.append((item, score))

    logger.info(
        "pass1 complete: %d/%d items cleared threshold=%d",
        len(results), len(items), SCORING_THRESHOLD,
    )
    return results
