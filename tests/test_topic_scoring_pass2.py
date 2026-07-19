"""Tests for Sub-task C — Pass-2 Orchestration and Signal Writing.

All tests are offline: the Gemini client and adapter.fetch_full_text are
mocked so no API key or network access is required.

Run from the project root with the virtualenv active:
    source .venv/bin/activate
    PYTHONPATH=src pytest tests/test_topic_scoring_pass2.py
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from sources.base import NormalizedItem, SourceAdapter
from topics.config import TaxonomyEntry, TopicConfig
from topics.models import Pass1Score
from topics.scoring import load_theme_definitions, pass2_score

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _write_theme(themes_dir: Path, theme_id: str, description: str) -> None:
    content = (
        "---\n"
        f"id: {theme_id}\n"
        f"name: {theme_id.replace('-', ' ').title()}\n"
        f"description: {description}\n"
        "created_at: '2026-01-01T00:00:00Z'\n"
        "updated_at: '2026-01-01T00:00:00Z'\n"
        "---\n\nTheme body.\n"
    )
    (themes_dir / f"{theme_id}.md").write_text(content)


def _make_topic_dir(tmp_path: Path) -> Path:
    topic_dir = tmp_path / "data_advantage"
    themes_dir = topic_dir / "themes"
    themes_dir.mkdir(parents=True)
    _write_theme(themes_dir, "synthetic-data-generation", "Model-generated training data.")
    _write_theme(themes_dir, "quality-filtering-curation", "High-signal subset selection.")
    credibility = {"MIT": 9, "Stanford University": 9}
    (topic_dir / "source_credibility.json").write_text(json.dumps(credibility))
    return topic_dir


def _make_item(
    url: str = "https://arxiv.org/abs/2404.01234",
    published_at: str = "2026-04-29T00:00:00Z",
) -> NormalizedItem:
    return NormalizedItem(
        source_id="arxiv",
        source_type="research_paper",
        title="Scaling Synthetic Data with Self-Play",
        url=url,
        published_at=published_at,
        authors=["Alice Smith"],
        summary="We propose a self-play framework for generating synthetic training data.",
    )


def _make_topic() -> TopicConfig:
    return TopicConfig(
        topic_id="data_advantage",
        name="Emerging Data Advantages in AI",
        thesis="Tracks which data assets create durable competitive edges.",
        audience_ref="ml_practitioner",
        taxonomy=[
            TaxonomyEntry(id="synthetic-data-generation", name="Synthetic Data Generation"),
            TaxonomyEntry(id="quality-filtering-curation", name="Quality Filtering"),
        ],
    )


def _valid_score_payload(affiliations: list[str] | None = None) -> dict:
    return {
        "applicability_score": 8,
        "applicability_rationale": "Directly advances the synthetic data theme.",
        "strategic_significance": 7,
        "strategic_significance_rationale": "Could shift best practice for instruction-tuning.",
        "paper_audience": "ML practitioners building post-training pipelines",
        "candidate_themes": [
            {
                "theme_id": "synthetic-data-generation",
                "confidence": 9,
                "rationale": "Core contribution is a scalable synthetic pipeline.",
            }
        ],
        "claims": ["Self-play achieves parity with human data."],
        "affiliations": affiliations if affiliations is not None else ["MIT"],
        "rationale": "This paper is highly relevant to the data advantage topic.",
    }


class _FakeAdapter(SourceAdapter):
    raw_extension = ".pdf"
    full_text_mime_type = "application/pdf"

    def source_id(self) -> str:
        return "arxiv"

    def fetch(self, query_params: dict) -> bytes:
        return b""

    def parse(self, raw: bytes) -> list[NormalizedItem]:
        return []

    def fetch_full_text(self, url: str) -> bytes:
        return b"%PDF-fake"


def _mock_client(payload: dict | None = None, affiliations: list[str] | None = None) -> MagicMock:
    if payload is None:
        payload = _valid_score_payload(affiliations=affiliations)
    client = MagicMock()
    response = MagicMock()
    response.text = json.dumps(payload)
    client.models.generate_content.return_value = response
    return client


# ---------------------------------------------------------------------------
# load_theme_definitions
# ---------------------------------------------------------------------------


class TestLoadThemeDefinitions:
    def test_returns_id_to_description_map(self, tmp_path):
        themes_dir = tmp_path / "themes"
        themes_dir.mkdir()
        _write_theme(themes_dir, "synthetic-data-generation", "Model-generated training data.")
        _write_theme(themes_dir, "quality-filtering-curation", "High-signal subset selection.")

        defs = load_theme_definitions(themes_dir)

        assert defs["synthetic-data-generation"] == "Model-generated training data."
        assert defs["quality-filtering-curation"] == "High-signal subset selection."

    def test_empty_directory_returns_empty_dict(self, tmp_path):
        themes_dir = tmp_path / "themes"
        themes_dir.mkdir()
        assert load_theme_definitions(themes_dir) == {}

    def test_missing_directory_raises(self, tmp_path):
        with pytest.raises(Exception):
            load_theme_definitions(tmp_path / "nonexistent")


# ---------------------------------------------------------------------------
# pass2_score — happy path
# ---------------------------------------------------------------------------


class TestPass2ScoreHappyPath:
    def test_writes_signal_file(self, tmp_path):
        topic_dir = _make_topic_dir(tmp_path)
        item = _make_item()
        abstract_score = Pass1Score(relevance=8, reason="Relevant.")

        with patch("topics.scoring.genai.Client", return_value=_mock_client()):
            paths = pass2_score([(item, abstract_score)], _make_topic(), topic_dir, _FakeAdapter())

        assert len(paths) == 1
        assert paths[0].exists()

    def test_signal_file_path_follows_date_hierarchy(self, tmp_path):
        topic_dir = _make_topic_dir(tmp_path)
        item = _make_item(published_at="2026-04-29T00:00:00Z")

        with patch("topics.scoring.genai.Client", return_value=_mock_client()):
            paths = pass2_score(
                [(item, Pass1Score(relevance=8, reason="ok"))],
                _make_topic(), topic_dir, _FakeAdapter(),
            )

        assert "signals/2026/04/29" in str(paths[0])

    def test_full_text_fetched_true_in_frontmatter(self, tmp_path):
        topic_dir = _make_topic_dir(tmp_path)
        item = _make_item()

        with patch("topics.scoring.genai.Client", return_value=_mock_client()):
            paths = pass2_score(
                [(item, Pass1Score(relevance=8, reason="ok"))],
                _make_topic(), topic_dir, _FakeAdapter(),
            )

        fm_text = paths[0].read_text().split("---")[1]
        fm = yaml.safe_load(fm_text)
        assert fm["full_text_fetched"] is True

    def test_frontmatter_contains_required_fields(self, tmp_path):
        topic_dir = _make_topic_dir(tmp_path)
        item = _make_item()

        with patch("topics.scoring.genai.Client", return_value=_mock_client()):
            paths = pass2_score(
                [(item, Pass1Score(relevance=8, reason="ok"))],
                _make_topic(), topic_dir, _FakeAdapter(),
            )

        fm_text = paths[0].read_text().split("---")[1]
        fm = yaml.safe_load(fm_text)
        for field in (
            "signal_id", "source_id", "source_type", "url", "published_at",
            "title", "authors", "affiliations", "ingested_at", "full_text_fetched",
            "applicability_score", "applicability_rationale",
            "strategic_significance", "strategic_significance_rationale",
            "paper_audience", "source_credibility", "temporal_freshness",
            "candidate_themes", "claims",
        ):
            assert field in fm, f"missing frontmatter field: {field}"
        assert fm["claims"] == ["Self-play achieves parity with human data."]
        assert "new_evidences" not in fm

    def test_body_contains_rationale_section(self, tmp_path):
        topic_dir = _make_topic_dir(tmp_path)
        item = _make_item()

        with patch("topics.scoring.genai.Client", return_value=_mock_client()):
            paths = pass2_score(
                [(item, Pass1Score(relevance=8, reason="ok"))],
                _make_topic(), topic_dir, _FakeAdapter(),
            )

        body = paths[0].read_text().split("---", 2)[2]
        assert "## Rationale" in body
        assert "highly relevant" in body

    def test_empty_items_returns_empty_list(self, tmp_path):
        topic_dir = _make_topic_dir(tmp_path)
        with patch("topics.scoring.genai.Client", return_value=_mock_client()):
            result = pass2_score([], _make_topic(), topic_dir, _FakeAdapter())
        assert result == []


# ---------------------------------------------------------------------------
# pass2_score — idempotency
# ---------------------------------------------------------------------------


class TestPass2ScoreIdempotency:
    def test_rerun_skips_existing_file(self, tmp_path):
        topic_dir = _make_topic_dir(tmp_path)
        item = _make_item()
        abstract_score = Pass1Score(relevance=8, reason="ok")

        with patch("topics.scoring.genai.Client", return_value=_mock_client()) as MockClient:
            pass2_score([(item, abstract_score)], _make_topic(), topic_dir, _FakeAdapter())
            first_call_count = MockClient.return_value.models.generate_content.call_count

        with patch("topics.scoring.genai.Client", return_value=_mock_client()) as MockClient:
            paths2 = pass2_score([(item, abstract_score)], _make_topic(), topic_dir, _FakeAdapter())
            second_call_count = MockClient.return_value.models.generate_content.call_count

        assert len(paths2) == 1
        assert second_call_count == 0, "LLM should not be called when signal already exists"

    def test_rerun_does_not_overwrite_content(self, tmp_path):
        topic_dir = _make_topic_dir(tmp_path)
        item = _make_item()
        abstract_score = Pass1Score(relevance=8, reason="ok")

        with patch("topics.scoring.genai.Client", return_value=_mock_client()):
            paths = pass2_score([(item, abstract_score)], _make_topic(), topic_dir, _FakeAdapter())

        original_content = paths[0].read_text()

        with patch("topics.scoring.genai.Client", return_value=_mock_client()):
            pass2_score([(item, abstract_score)], _make_topic(), topic_dir, _FakeAdapter())

        assert paths[0].read_text() == original_content


# ---------------------------------------------------------------------------
# pass2_score — fetch_full_text failure
# ---------------------------------------------------------------------------


class TestPass2ScoreFetchFailure:
    def test_fetch_failure_drops_item(self, tmp_path):
        topic_dir = _make_topic_dir(tmp_path)
        item = _make_item()
        abstract_score = Pass1Score(relevance=8, reason="ok")

        failing_adapter = _FakeAdapter()
        failing_adapter.fetch_full_text = MagicMock(side_effect=RuntimeError("network error"))

        with patch("topics.scoring.genai.Client", return_value=_mock_client()):
            paths = pass2_score(
                [(item, abstract_score)], _make_topic(), topic_dir, failing_adapter
            )

        assert paths == []
        assert not list((topic_dir / "signals").glob("**/*.md"))

    def test_fetch_failure_writes_no_partial_file(self, tmp_path):
        topic_dir = _make_topic_dir(tmp_path)
        items = [
            (_make_item(url=f"https://arxiv.org/abs/2404.0000{i}"), Pass1Score(relevance=8, reason="ok"))
            for i in range(3)
        ]

        call_count = 0

        def flaky_fetch(url: str) -> bytes:
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise RuntimeError("transient error")
            return b"%PDF-fake"

        adapter = _FakeAdapter()
        adapter.fetch_full_text = flaky_fetch

        with patch("topics.scoring.genai.Client", return_value=_mock_client()):
            paths = pass2_score(items, _make_topic(), topic_dir, adapter)

        assert len(paths) == 2


# ---------------------------------------------------------------------------
# pass2_score — credibility and freshness
# ---------------------------------------------------------------------------


class TestPass2ScoreCredibilityAndFreshness:
    def test_source_credibility_matched_affiliation(self, tmp_path):
        topic_dir = _make_topic_dir(tmp_path)
        item = _make_item()

        with patch("topics.scoring.genai.Client", return_value=_mock_client(affiliations=["MIT"])):
            paths = pass2_score(
                [(item, Pass1Score(relevance=8, reason="ok"))],
                _make_topic(), topic_dir, _FakeAdapter(),
            )

        fm = yaml.safe_load(paths[0].read_text().split("---")[1])
        assert fm["source_credibility"] == 9.0

    def test_source_credibility_null_when_no_match(self, tmp_path):
        topic_dir = _make_topic_dir(tmp_path)
        item = _make_item()

        with patch("topics.scoring.genai.Client", return_value=_mock_client(affiliations=["Unknown Uni"])):
            paths = pass2_score(
                [(item, Pass1Score(relevance=8, reason="ok"))],
                _make_topic(), topic_dir, _FakeAdapter(),
            )

        fm = yaml.safe_load(paths[0].read_text().split("---")[1])
        assert fm["source_credibility"] is None

    def test_temporal_freshness_in_range(self, tmp_path):
        topic_dir = _make_topic_dir(tmp_path)
        item = _make_item(published_at="2026-04-29T00:00:00Z")

        with patch("topics.scoring.genai.Client", return_value=_mock_client()):
            paths = pass2_score(
                [(item, Pass1Score(relevance=8, reason="ok"))],
                _make_topic(), topic_dir, _FakeAdapter(),
            )

        fm = yaml.safe_load(paths[0].read_text().split("---")[1])
        assert 0 <= fm["temporal_freshness"] <= 10

    def test_temporal_freshness_null_for_old_item(self, tmp_path):
        """An item published 365+ days ago should score 0."""
        topic_dir = _make_topic_dir(tmp_path)
        item = _make_item(published_at="2020-01-01T00:00:00Z")

        with patch("topics.scoring.genai.Client", return_value=_mock_client()):
            paths = pass2_score(
                [(item, Pass1Score(relevance=8, reason="ok"))],
                _make_topic(), topic_dir, _FakeAdapter(),
            )

        fm = yaml.safe_load(paths[0].read_text().split("---")[1])
        assert fm["temporal_freshness"] == 0

    def test_missing_credibility_file_sets_null(self, tmp_path):
        topic_dir = _make_topic_dir(tmp_path)
        (topic_dir / "source_credibility.json").unlink()
        item = _make_item()

        with patch("topics.scoring.genai.Client", return_value=_mock_client()):
            paths = pass2_score(
                [(item, Pass1Score(relevance=8, reason="ok"))],
                _make_topic(), topic_dir, _FakeAdapter(),
            )

        fm = yaml.safe_load(paths[0].read_text().split("---")[1])
        assert fm["source_credibility"] is None


# ---------------------------------------------------------------------------
# pass2_score — candidate_themes ordering
# ---------------------------------------------------------------------------


class TestPass2ScoreCandidateThemes:
    def test_candidate_themes_sorted_by_descending_confidence(self, tmp_path):
        topic_dir = _make_topic_dir(tmp_path)
        item = _make_item()
        payload = _valid_score_payload()
        payload["candidate_themes"] = [
            {"theme_id": "quality-filtering-curation", "confidence": 5, "rationale": "Secondary."},
            {"theme_id": "synthetic-data-generation", "confidence": 9, "rationale": "Primary."},
        ]

        with patch("topics.scoring.genai.Client", return_value=_mock_client(payload)):
            paths = pass2_score(
                [(item, Pass1Score(relevance=8, reason="ok"))],
                _make_topic(), topic_dir, _FakeAdapter(),
            )

        fm = yaml.safe_load(paths[0].read_text().split("---")[1])
        confidences = [ct["confidence"] for ct in fm["candidate_themes"]]
        assert confidences == sorted(confidences, reverse=True)

    def test_candidate_themes_each_have_rationale(self, tmp_path):
        topic_dir = _make_topic_dir(tmp_path)
        item = _make_item()

        with patch("topics.scoring.genai.Client", return_value=_mock_client()):
            paths = pass2_score(
                [(item, Pass1Score(relevance=8, reason="ok"))],
                _make_topic(), topic_dir, _FakeAdapter(),
            )

        fm = yaml.safe_load(paths[0].read_text().split("---")[1])
        for ct in fm["candidate_themes"]:
            assert "rationale" in ct
            assert ct["rationale"]
