"""Tests for Task 15.3a — Pass-1 Topic Relevance Filter.

All tests are offline: the Gemini client is mocked so no API key or network
access is required. The mock controls the returned relevance score and reason,
letting each test target a specific filtering behaviour.

Run from the project root with the virtualenv active:
    source .venv/bin/activate
    PYTHONPATH=src pytest tests/test_topic_scoring_pass1.py
"""

from unittest.mock import MagicMock, call, patch

import pytest

from sources.base import NormalizedItem
from topics.config import TaxonomyEntry, TopicConfig
from topics.models import AbstractScore
from topics.scoring import pass1_filter

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

_TOPIC = TopicConfig(
    topic_id="data_advantage",
    name="Emerging Data Advantages in AI",
    thesis=(
        "A technical strategy brief tracking which new data assets, collection "
        "methods, and dataset-generation approaches create durable competitive "
        "advantage in AI systems."
    ),
    audience_ref="technical_decision_makers",
    scope_in=[
        "Scale-unlocking corpora",
        "Quality-and-filtering advances",
        "Synthetic and self-generated data",
    ],
    scope_out=[
        "Model architecture research without a data insight",
        "Pure inference or serving optimization",
    ],
    taxonomy=[
        TaxonomyEntry(id="synthetic-data-generation", name="Synthetic Data Generation"),
        TaxonomyEntry(id="filtering-and-curation", name="Filtering and Curation"),
    ],
)

_THEME_DEFS = {
    "synthetic-data-generation": "Using model-generated data to train better models.",
    "filtering-and-curation": "Quality filtering, deduplication, and dataset curation.",
}


def _make_item(title: str, summary: str, source_id: str = "arxiv") -> NormalizedItem:
    return NormalizedItem(
        source_id=source_id,
        source_type="paper",
        title=title,
        url=f"https://arxiv.org/abs/{abs(hash(title)):x}",
        published_at="2026-04-28",
        summary=summary,
    )


_ON_TOPIC = _make_item(
    "FineWeb-Edu: Educational Content Filtering at Scale",
    "We introduce FineWeb-Edu, a 1.3T-token filtered subset of FineWeb focused "
    "on educational quality. Filtering by educational quality scores substantially "
    "improves downstream model performance on knowledge benchmarks, demonstrating "
    "that data quality filtering is a first-class lever for model capability.",
)

_OFF_TOPIC = _make_item(
    "FlashAttention-3: Fast Attention via Asynchrony and Low-Precision",
    "We present FlashAttention-3, achieving up to 2x speedup over FlashAttention-2 "
    "on H100 GPUs through asynchrony and FP8 low-precision arithmetic. The approach "
    "targets inference throughput and has no data collection or curation contribution.",
)


def _mock_response(relevance: int, reason: str) -> MagicMock:
    """Build a mock Gemini response object returning the given score."""
    mock = MagicMock()
    mock.text = f'{{"relevance": {relevance}, "reason": "{reason}"}}'
    return mock


def _patch_client(side_effects: list):
    """Patch genai.Client so generate_content returns side_effects in order."""
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = side_effects

    patcher = patch("topics.scoring.genai.Client", return_value=mock_client)
    return patcher, mock_client


# ---------------------------------------------------------------------------
# 1. On-topic item clears threshold
# ---------------------------------------------------------------------------


def test_on_topic_item_clears_threshold():
    """An item with relevance >= SCORING_THRESHOLD is returned by pass1_filter.

    > **Why:** If on-topic items are incorrectly dropped at pass-1, the wiki
    never learns about relevant signals regardless of how good pass-2 is.
    """
    patcher, mock_client = _patch_client([_mock_response(8, "Directly about data filtering.")])

    with patcher:
        results = pass1_filter([_ON_TOPIC], _TOPIC, _THEME_DEFS)

    assert len(results) == 1
    item, score = results[0]
    assert item is _ON_TOPIC
    assert score.relevance == 8
    assert "data filtering" in score.reason


# ---------------------------------------------------------------------------
# 2. Off-topic item is dropped
# ---------------------------------------------------------------------------


def test_off_topic_item_is_dropped():
    """An item with relevance < SCORING_THRESHOLD is not returned.

    > **Why:** Pass-1 exists specifically to gate off-topic items before the
    expensive full-text fetch. If it passes everything, pass-2 runs on noise.
    """
    patcher, mock_client = _patch_client([_mock_response(3, "Inference optimization, not data.")])

    with patcher:
        results = pass1_filter([_OFF_TOPIC], _TOPIC, _THEME_DEFS)

    assert results == []


# ---------------------------------------------------------------------------
# 3. Boundary: item at exactly threshold clears
# ---------------------------------------------------------------------------


def test_item_at_threshold_clears():
    """An item with relevance == SCORING_THRESHOLD (6) is kept, not dropped.

    > **Why:** The threshold is inclusive. A closed boundary means items at 6
    are accepted; an off-by-one error here silently discards borderline signals.
    """
    patcher, mock_client = _patch_client([_mock_response(6, "Borderline but relevant.")])

    with patcher:
        results = pass1_filter([_ON_TOPIC], _TOPIC, _THEME_DEFS)

    assert len(results) == 1
    _, score = results[0]
    assert score.relevance == 6


# ---------------------------------------------------------------------------
# 4. Boundary: item one below threshold is dropped
# ---------------------------------------------------------------------------


def test_item_one_below_threshold_dropped():
    """An item with relevance == SCORING_THRESHOLD - 1 (5) is dropped.

    > **Why:** Paired with the previous test to pin both sides of the boundary.
    """
    patcher, mock_client = _patch_client([_mock_response(5, "Marginally related.")])

    with patcher:
        results = pass1_filter([_ON_TOPIC], _TOPIC, _THEME_DEFS)

    assert results == []


# ---------------------------------------------------------------------------
# 5. Mixed batch returns only relevant items in order
# ---------------------------------------------------------------------------


def test_mixed_batch_returns_only_relevant():
    """pass1_filter applied to a mixed batch returns only on-topic items.

    > **Why:** The daily ingestion run produces a heterogeneous batch. If the
    filter cannot correctly partition it, either noise leaks into the wiki or
    valid signals are lost.
    """
    patcher, mock_client = _patch_client([
        _mock_response(8, "On-topic data filtering paper."),
        _mock_response(2, "Pure inference optimization, no data angle."),
    ])

    items = [_ON_TOPIC, _OFF_TOPIC]
    with patcher:
        results = pass1_filter(items, _TOPIC, _THEME_DEFS)

    assert len(results) == 1
    item, score = results[0]
    assert item is _ON_TOPIC
    assert score.relevance == 8


# ---------------------------------------------------------------------------
# 6. Empty input returns empty without calling the API
# ---------------------------------------------------------------------------


def test_empty_input_returns_empty():
    """pass1_filter with an empty list returns [] without calling the Gemini API.

    > **Why:** An empty batch from the adapter (e.g. quiet feed day) should
    short-circuit immediately — no API quota consumed.
    """
    with patch("topics.scoring.genai.Client") as mock_client_cls:
        results = pass1_filter([], _TOPIC, _THEME_DEFS)

    assert results == []
    mock_client_cls.assert_not_called()


# ---------------------------------------------------------------------------
# 7. AbstractScore fields are fully populated on returned items
# ---------------------------------------------------------------------------


def test_abstract_score_fields_populated():
    """AbstractScore on returned items has correct relevance (int) and reason (str).

    > **Why:** Downstream consumers (logging, pass-2 context) read these fields
    directly. A missing or wrong-typed field causes a silent AttributeError.
    """
    patcher, mock_client = _patch_client([_mock_response(9, "Core data curation insight.")])

    with patcher:
        results = pass1_filter([_ON_TOPIC], _TOPIC, _THEME_DEFS)

    assert len(results) == 1
    _, score = results[0]
    assert isinstance(score, AbstractScore)
    assert isinstance(score.relevance, int)
    assert isinstance(score.reason, str)
    assert score.relevance == 9
    assert score.reason == "Core data curation insight."


# ---------------------------------------------------------------------------
# 8. Scoring failure drops the item (no crash, no partial result)
# ---------------------------------------------------------------------------


def test_scoring_failure_drops_item():
    """If the Gemini API raises on all attempts, the item is dropped silently.

    > **Why:** A network error on one item must not crash the batch — the
    remaining items in the run should still be processed.
    """
    patcher, mock_client = _patch_client([RuntimeError("API unavailable")] * 4)

    with patcher:
        results = pass1_filter([_ON_TOPIC], _TOPIC, _THEME_DEFS)

    assert results == []


# ---------------------------------------------------------------------------
# 9. Prompt contains topic thesis and item abstract
# ---------------------------------------------------------------------------


def test_prompt_contains_thesis_and_abstract():
    """The pass-1 prompt sent to the model includes the topic thesis and item abstract.

    > **Why:** If the thesis or abstract are missing from the prompt, the LLM
    scores against nothing and the filter becomes meaningless.
    """
    patcher, mock_client = _patch_client([_mock_response(7, "Relevant.")])

    with patcher:
        pass1_filter([_ON_TOPIC], _TOPIC, _THEME_DEFS)

    assert mock_client.models.generate_content.called
    prompt_sent = mock_client.models.generate_content.call_args[1]["contents"]
    assert _TOPIC.thesis[:30] in prompt_sent
    assert _ON_TOPIC.summary[:30] in prompt_sent


# ---------------------------------------------------------------------------
# 10. Multiple on-topic items all returned, in input order
# ---------------------------------------------------------------------------


def test_multiple_on_topic_items_all_returned():
    """Two on-topic items are both returned, preserving input order.

    > **Why:** Order preservation matters — pass-2 processes items in the same
    order and the final signal files should reflect ingestion priority.
    """
    second = _make_item(
        "DataComp: A Large-Scale Benchmark for Data Curation",
        "DataComp is a benchmark for evaluating data curation strategies. "
        "We provide a fixed compute budget and vary only the training data, "
        "isolating the effect of dataset quality from model capacity.",
    )

    patcher, mock_client = _patch_client([
        _mock_response(8, "On-topic filtering benchmark."),
        _mock_response(7, "Data curation benchmark directly relevant."),
    ])

    with patcher:
        results = pass1_filter([_ON_TOPIC, second], _TOPIC, _THEME_DEFS)

    assert len(results) == 2
    assert results[0][0] is _ON_TOPIC
    assert results[1][0] is second
