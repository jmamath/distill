"""Topic-aware signal scoring pipeline.

Pass-1 scores each NormalizedItem against the topic thesis using its
abstract/summary only. Items that do not clear SCORING_THRESHOLD are dropped
here — no full-text fetch, no disk write.

Pass-2 fetches full text for cleared items, scores via LLM, computes
deterministic credibility and freshness, and writes signal files to disk.

Public API:
    load_theme_definitions(themes_dir) → dict[str, str]
    pass1_score(items, topic_config, theme_definitions) → list[tuple[NormalizedItem, Pass1Score]]
    pass2_score(items, topic_config, topic_dir, adapter) → list[Path]
"""

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

from pydantic import ValidationError
from google import genai
from google.genai import types

from config import GEMINI_API_KEY, SCORING_FALLBACK_MODEL, SCORING_MODEL, SCORING_THRESHOLD
from sources.base import NormalizedItem, SourceAdapter
from topics.config import TopicConfig
from topics.credibility import compute_source_credibility, compute_temporal_freshness
from topics.frontmatter import ThemeFrontmatter, load_frontmatter, write_with_frontmatter
from topics.models import Pass1Score, Pass2Score, make_signal_id
from topics.prompts import build_pass1_prompt, build_pass2_prompt

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


def _call_pass1_model(client: genai.Client, prompt: str, model: str) -> str:
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
    theme_definitions: dict[str, str],
) -> Pass1Score | None:
    """Score a single item against the topic thesis using its abstract only.

    Tries each model in _MODELS with one retry before moving to the fallback.
    Returns None if all models fail — the caller drops the item.
    """
    prompt = build_pass1_prompt(item, topic_config, theme_definitions)

    for model in _MODELS:
        raw = ""
        for attempt in range(2):
            try:
                raw = _call_pass1_model(client, prompt, model)
                data = json.loads(raw)
                return Pass1Score(
                    relevance=int(data["relevance"]),
                    reason=str(data["reason"]),
                )
            except (json.JSONDecodeError, ValidationError) as exc:
                logger.warning("pass1: model %s parse failed (%s) — raw: %s", model, exc, raw)
                break
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


def pass1_score(
    items: list[NormalizedItem],
    topic_config: TopicConfig,
    theme_definitions: dict[str, str],
) -> list[tuple[NormalizedItem, Pass1Score]]:
    """Score items against the topic thesis using abstract/summary only.

    Each item is scored individually with one LLM call. Items that score below
    SCORING_THRESHOLD or fail scoring entirely are dropped and logged. No disk
    writes occur in this function.

    Args:
        items: Normalized items from one or more source adapters.
        topic_config: The active topic configuration (thesis, taxonomy, scope).
        theme_definitions: Mapping of theme_id → description loaded from
            themes/*.md frontmatter. Passed to the prompt builder so both
            passes share a single source of truth for theme descriptions.

    Returns:
        Pairs of (item, score) for items that cleared the threshold, in input
        order. Pass-2 receives this list to continue processing.
    """
    if not items:
        return []

    client = genai.Client(api_key=GEMINI_API_KEY)
    results: list[tuple[NormalizedItem, Pass1Score]] = []

    for item in items:
        score = _score_one(client, item, topic_config, theme_definitions)
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


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def load_theme_definitions(themes_dir: Path) -> dict[str, str]:
    """Return {theme_id: description} for every *.md file in themes_dir.

    Reads ThemeFrontmatter from each file; the description field is the
    single-line summary included in both pass-1 and pass-2 prompts. Theme
    bodies are intentionally excluded so the LLM cannot anchor on existing
    wiki content.

    Args:
        themes_dir: Path to the themes/ directory for a topic.

    Returns:
        Mapping of theme_id → description, in filesystem order.

    Raises:
        FileNotFoundError: if themes_dir does not exist.
        pydantic.ValidationError: if a theme file is missing required frontmatter.
    """
    if not themes_dir.exists():
        raise FileNotFoundError(f"themes directory not found: {themes_dir}")
    definitions: dict[str, str] = {}
    for path in sorted(themes_dir.glob("*.md")):
        fm_dict, _ = load_frontmatter(path)
        theme = ThemeFrontmatter(**fm_dict)
        definitions[theme.id] = theme.description
    return definitions


def _load_credibility_table(path: Path) -> dict[str, object]:
    """Load source_credibility.json; return empty dict if absent."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        logger.warning("pass2: no source_credibility.json at %s — credibility will be null", path)
        return {}


def _parse_published_at(published_at: str) -> datetime:
    """Parse an ISO 8601 date or datetime string to a timezone-aware datetime."""
    s = published_at.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
        return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return datetime(int(s[:4]), int(s[5:7]), int(s[8:10]), tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Pass-2 LLM call
# ---------------------------------------------------------------------------


def _call_pass2_model(
    client: genai.Client,
    prompt: str,
    full_text_bytes: bytes,
    mime_type: str,
    model: str,
) -> str:
    response = client.models.generate_content(
        model=model,
        contents=[
            types.Content(
                parts=[
                    types.Part(text=prompt),
                    types.Part(inline_data=types.Blob(mime_type=mime_type, data=full_text_bytes)),
                ]
            )
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        ),
    )
    return response.text.strip()


def _score_pass2_one(
    client: genai.Client,
    prompt: str,
    full_text_bytes: bytes,
    mime_type: str,
    item_url: str,
) -> Pass2Score | None:
    """Score one item via pass-2 LLM call.

    Tries each model in _MODELS with one retry before falling back. Returns
    None if all models fail — the caller drops the item without a disk write.
    """
    for model in _MODELS:
        raw = ""
        for attempt in range(2):
            try:
                raw = _call_pass2_model(client, prompt, full_text_bytes, mime_type, model)
                return Pass2Score(**json.loads(raw))
            except (json.JSONDecodeError, ValidationError) as exc:
                logger.warning("pass2: model %s parse failed (%s) — raw: %s", model, exc, raw)
                break
            except Exception as exc:
                if "404" in str(exc):
                    logger.warning("pass2: model %s not found, trying fallback", model)
                    break
                if attempt == 0:
                    logger.warning(
                        "pass2: model %s attempt 1 failed (%s), retrying in 5s", model, exc
                    )
                    time.sleep(5)
                else:
                    logger.warning("pass2: model %s exhausted, trying fallback", model)

    logger.error("pass2: all models failed for item %r", item_url)
    return None


# ---------------------------------------------------------------------------
# Pass-2 orchestration
# ---------------------------------------------------------------------------


def pass2_score(
    items: list[tuple[NormalizedItem, Pass1Score]],
    topic_config: TopicConfig,
    topic_dir: Path,
    adapter: SourceAdapter,
) -> list[Path]:
    """Fetch full text, score, and write signal files for pass-1-cleared items.

    For each item:
    1. Fetches full text via adapter.fetch_full_text; drops the item on failure.
    2. Scores with the LLM, passing full text bytes alongside the prompt.
    3. Computes source_credibility and temporal_freshness deterministically.
    4. Writes the signal file to topic_dir/signals/{yyyy}/{mm}/{dd}/{signal_id}.md.
       Skips without overwriting if the file already exists (idempotent).

    Args:
        items: Pass-1 survivors as (NormalizedItem, Pass1Score) pairs.
        topic_config: The active topic configuration.
        topic_dir: Root of the topic data directory (e.g. data/research_topics/data_advantage/).
        adapter: Source adapter used to fetch full text.

    Returns:
        Paths of all signal files written or already present from this run.
    """
    if not items:
        return []

    theme_definitions = load_theme_definitions(topic_dir / "themes")
    credibility_table = _load_credibility_table(topic_dir / "source_credibility.json")
    client = genai.Client(api_key=GEMINI_API_KEY)
    written: list[Path] = []

    for item, _ in items:
        signal_id = make_signal_id(item.source_id, item.published_at, item.url)
        yyyy, mm, dd = item.published_at[:10].split("-")
        signal_path = topic_dir / "signals" / yyyy / mm / dd / f"{signal_id}.md"

        if signal_path.exists():
            logger.info("pass2: signal %s already exists — skipping", signal_id)
            written.append(signal_path)
            continue

        try:
            full_text_bytes = adapter.fetch_full_text(item.url)
            item.full_text_fetched = True
        except Exception as exc:
            logger.warning("pass2: fetch_full_text failed for %r (%s) — dropping", item.url, exc)
            continue

        prompt = build_pass2_prompt(item, topic_config, theme_definitions)
        score = _score_pass2_one(
            client, prompt, full_text_bytes, adapter.full_text_mime_type, item.url
        )
        if score is None:
            continue

        source_credibility = compute_source_credibility(score.affiliations, credibility_table)
        temporal_freshness = compute_temporal_freshness(_parse_published_at(item.published_at))

        frontmatter = {
            "signal_id": signal_id,
            "source_id": item.source_id,
            "source_type": item.source_type,
            "url": item.url,
            "published_at": item.published_at,
            "title": item.title,
            "authors": item.authors,
            "affiliations": score.affiliations,
            "ingested_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "full_text_fetched": True,
            "applicability_score": score.applicability_score,
            "applicability_rationale": score.applicability_rationale,
            "strategic_significance": score.strategic_significance,
            "strategic_significance_rationale": score.strategic_significance_rationale,
            "paper_audience": score.paper_audience,
            "source_credibility": source_credibility,
            "temporal_freshness": temporal_freshness,
            "candidate_themes": [
                ct.model_dump()
                for ct in sorted(score.candidate_themes, key=lambda t: -t.confidence)
            ],
            "claims": score.claims,
        }
        write_with_frontmatter(signal_path, frontmatter, f"\n## Rationale\n\n{score.rationale}\n")
        logger.info("pass2: wrote signal %s", signal_path)
        written.append(signal_path)

    logger.info("pass2 complete: %d/%d items written", len(written), len(items))
    return written
