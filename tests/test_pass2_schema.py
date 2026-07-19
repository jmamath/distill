"""Tests for Sub-task B — Pass-2 Prompt And Signal Schema.

All tests are offline: no LLM calls, no disk I/O.

Run from the project root with the virtualenv active:
    source .venv/bin/activate
    PYTHONPATH=src pytest tests/test_pass2_schema.py
"""

import json

import pytest

from sources.base import NormalizedItem
from topics.config import TaxonomyEntry, TopicConfig
from topics.models import (
    CandidateTheme,
    Pass2Score,
    make_signal_id,
)
from topics.prompts import build_pass2_prompt

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

_TOPIC = TopicConfig(
    topic_id="data_advantage",
    name="Emerging Data Advantages in AI",
    thesis="Tracks which data assets and generation methods create durable competitive edges.",
    audience_ref="ml_practitioner",
    taxonomy=[
        TaxonomyEntry(id="synthetic-data-generation", name="Synthetic Data Generation"),
        TaxonomyEntry(id="quality-filtering-curation", name="Quality Filtering & Curation"),
    ],
)

_THEME_DEFINITIONS = {
    "synthetic-data-generation": "Model-generated training data for distillation and instruction tuning.",
    "quality-filtering-curation": "Techniques for selecting high-signal subsets from raw corpora.",
}

_ITEM = NormalizedItem(
    source_id="arxiv",
    source_type="research_paper",
    title="Scaling Synthetic Data with Self-Play",
    url="https://arxiv.org/abs/2404.01234",
    published_at="2026-04-29T00:00:00Z",
    authors=["Alice Smith", "Bob Jones"],
    summary="We propose a self-play framework for generating synthetic training data at scale.",
)


# ---------------------------------------------------------------------------
# Pass2Score schema tests
# ---------------------------------------------------------------------------


class TestPass2Score:
    def _valid_payload(self):
        return {
            "applicability_score": 8,
            "applicability_rationale": "Directly advances the synthetic data theme with a novel self-play loop.",
            "strategic_significance": 7,
            "strategic_significance_rationale": "Could shift best practice for instruction-tuning data at scale.",
            "paper_audience": "industry practitioners building post-training pipelines",
            "candidate_themes": [
                {
                    "theme_id": "synthetic-data-generation",
                    "confidence": 9,
                    "rationale": "Core contribution is a scalable synthetic pipeline.",
                }
            ],
            "claims": [
                "Self-play achieves parity with human-curated data on benchmark X."
            ],
            "affiliations": ["MIT", "Google DeepMind"],
            "rationale": "This paper directly advances the synthetic data theme.",
        }

    def test_roundtrip_from_json(self):
        payload = self._valid_payload()
        score = Pass2Score(**payload)
        recovered = Pass2Score(**json.loads(score.model_dump_json()))
        assert recovered == score

    def test_applicability_score_bounds(self):
        payload = self._valid_payload()
        payload["applicability_score"] = 11
        with pytest.raises(Exception):
            Pass2Score(**payload)

        payload["applicability_score"] = -1
        with pytest.raises(Exception):
            Pass2Score(**payload)

    def test_strategic_significance_bounds(self):
        payload = self._valid_payload()
        payload["strategic_significance"] = 11
        with pytest.raises(Exception):
            Pass2Score(**payload)

        payload["strategic_significance"] = -1
        with pytest.raises(Exception):
            Pass2Score(**payload)

    def test_empty_lists_are_valid(self):
        score = Pass2Score(
            applicability_score=3,
            applicability_rationale="Tangentially relevant to the topic thesis.",
            strategic_significance=2,
            strategic_significance_rationale="Incremental result with limited strategic impact.",
            paper_audience="general",
            candidate_themes=[],
            claims=[],
            affiliations=[],
            rationale="Marginally relevant.",
        )
        assert score.candidate_themes == []
        assert score.claims == []

    def test_legacy_stanced_evidence_field_is_rejected(self):
        payload = self._valid_payload()
        payload.pop("claims")
        payload["new_evidences"] = [
            {"claim": "A claim with no named hypothesis.", "stance": "for"}
        ]

        with pytest.raises(Exception):
            Pass2Score(**payload)


class TestCandidateTheme:
    def test_requires_rationale(self):
        with pytest.raises(Exception):
            CandidateTheme(theme_id="synthetic-data-generation", confidence=7)

    def test_confidence_bounds(self):
        with pytest.raises(Exception):
            CandidateTheme(
                theme_id="synthetic-data-generation", confidence=11, rationale="x"
            )

    def test_valid_construction(self):
        theme = CandidateTheme(
            theme_id="synthetic-data-generation",
            confidence=9,
            rationale="Core contribution directly implements this theme.",
        )
        assert theme.theme_id == "synthetic-data-generation"
        assert theme.rationale != ""


# ---------------------------------------------------------------------------
# signal_id tests
# ---------------------------------------------------------------------------


class TestMakeSignalId:
    def test_deterministic_same_url(self):
        id1 = make_signal_id("arxiv", "2026-04-29", "https://arxiv.org/abs/2404.01234")
        id2 = make_signal_id("arxiv", "2026-04-29", "https://arxiv.org/abs/2404.01234")
        assert id1 == id2

    def test_different_urls_produce_different_ids(self):
        id1 = make_signal_id("arxiv", "2026-04-29", "https://arxiv.org/abs/2404.01234")
        id2 = make_signal_id("arxiv", "2026-04-29", "https://arxiv.org/abs/2404.99999")
        assert id1 != id2

    def test_format(self):
        signal_id = make_signal_id("arxiv", "2026-04-29T00:00:00Z", "https://arxiv.org/abs/2404.01234")
        parts = signal_id.split("_")
        assert parts[0] == "arxiv"
        assert parts[1] == "2026-04-29"
        assert len(parts[2]) == 10

    def test_uses_date_portion_only(self):
        id_with_time = make_signal_id("arxiv", "2026-04-29T14:23:11Z", "https://example.com/x")
        id_date_only = make_signal_id("arxiv", "2026-04-29", "https://example.com/x")
        assert id_with_time == id_date_only


# ---------------------------------------------------------------------------
# build_pass2_prompt tests
# ---------------------------------------------------------------------------


class TestBuildPass2Prompt:
    def test_includes_theme_definitions(self):
        prompt = build_pass2_prompt(_ITEM, _TOPIC, _THEME_DEFINITIONS)
        assert "synthetic-data-generation" in prompt
        assert "Model-generated training data" in prompt

    def test_includes_item_metadata(self):
        prompt = build_pass2_prompt(_ITEM, _TOPIC, _THEME_DEFINITIONS)
        assert _ITEM.title in prompt
        assert _ITEM.url in prompt
        assert "Alice Smith" in prompt

    def test_excludes_theme_bodies(self):
        # theme bodies would be the full Markdown body of a theme file — only
        # descriptions (one-liners) are included, never multi-paragraph content
        prompt = build_pass2_prompt(_ITEM, _TOPIC, _THEME_DEFINITIONS)
        # confirm the description is present but no stray "## " section headers
        # that would indicate wiki body content leaked in
        assert "## " not in prompt

    def test_excludes_existing_evidences(self):
        # existing_evidences would only appear if passed explicitly; the
        # function signature does not accept them — verify the prompt builder
        # cannot accidentally include them
        import inspect
        sig = inspect.signature(build_pass2_prompt)
        assert "existing_evidences" not in sig.parameters
        assert "evidence" not in sig.parameters

    def test_prompt_requests_json_output(self):
        prompt = build_pass2_prompt(_ITEM, _TOPIC, _THEME_DEFINITIONS)
        assert "JSON" in prompt
        assert "applicability_score" in prompt
        assert "strategic_significance" in prompt
        assert "candidate_themes" in prompt
        assert '"claims"' in prompt
        assert "new_evidences" not in prompt
        assert "for|against" not in prompt

    def test_candidate_themes_rule_in_prompt(self):
        prompt = build_pass2_prompt(_ITEM, _TOPIC, _THEME_DEFINITIONS)
        assert "at most 3" in prompt
        assert "descending confidence" in prompt

    def test_prompt_requests_score_rationales(self):
        prompt = build_pass2_prompt(_ITEM, _TOPIC, _THEME_DEFINITIONS)
        assert "applicability_rationale" in prompt
        assert "strategic_significance_rationale" in prompt
