"""Tests for Plan 9 Decisions 1–2 and their deterministic contracts.

All tests are offline: the Gemini client is mocked, so no API key or network
access is required. The `[llm]` behaviours (is a given triage verdict
*correct*?) are Sub-task C's eval; here we verify the deterministic contract —
branch validation, dedup keying, and the uniform-prior open.

Run from the project root with the virtualenv active:
    PYTHONPATH=src pytest tests/test_hypothesis_updater.py
"""

import json
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from topics.config import TaxonomyEntry, TopicConfig
from topics.hypothesis_updater import (
    make_evidence_id,
    open_hypothesis_record,
    resolve_stance,
    triage_claim,
)
from topics.models import StanceDecision, TriageDecision
from topics.prompts import build_stance_prompt, build_triage_prompt
from topics.storage import merge_by_id

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


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


def _make_hypotheses() -> list[dict]:
    return [
        {
            "id": "dedup_improves_quality",
            "statement": "Training-data deduplication improves downstream model quality.",
            "theme_ids": ["quality-filtering-curation"],
            "status": "active",
            "belief": {"alpha": 4.2, "beta": 1.5},
            "comparison": None,
        },
        {
            "id": "fuzzy_beats_exact_dedup",
            "statement": "Fuzzy deduplication outperforms exact deduplication.",
            "theme_ids": ["quality-filtering-curation"],
            "status": "active",
            "belief": {"alpha": 1.0, "beta": 1.0},
            "comparison": {"subject_a": "fuzzy dedup", "subject_b": "exact dedup"},
        },
    ]


def _mock_client(payload: dict) -> MagicMock:
    client = MagicMock()
    response = MagicMock()
    response.text = json.dumps(payload)
    client.models.generate_content.return_value = response
    return client


# ---------------------------------------------------------------------------
# TriageDecision — branch payload validation
# ---------------------------------------------------------------------------


def test_attach_requires_hypothesis_id():
    with pytest.raises(ValidationError):
        TriageDecision(decision="attach", rationale="bears on dedup")


def test_open_requires_new_statement():
    with pytest.raises(ValidationError):
        TriageDecision(decision="open", rationale="a standing question")


def test_route_requires_entity():
    with pytest.raises(ValidationError):
        TriageDecision(decision="route", rationale="a dataset release")


def test_drop_must_carry_no_payload():
    with pytest.raises(ValidationError):
        TriageDecision(
            decision="drop",
            entity={"name": "X", "entity_type": "dataset", "description": "d"},
            rationale="incidental",
        )


def test_comparison_only_valid_on_open():
    with pytest.raises(ValidationError):
        TriageDecision(
            decision="attach",
            hypothesis_id="dedup_improves_quality",
            comparison={"subject_a": "a", "subject_b": "b"},
            rationale="r",
        )


def test_attach_rejects_hypothesis_id_outside_candidates():
    data = {"decision": "attach", "hypothesis_id": "invented_id", "rationale": "r"}
    with pytest.raises(ValidationError):
        TriageDecision.model_validate(data, context={"candidate_ids": {"real_id"}})
    # Without context the membership check is skipped (shape-only validation).
    assert TriageDecision.model_validate(data).hypothesis_id == "invented_id"


def test_entity_may_cofire_on_attach():
    decision = TriageDecision(
        decision="attach",
        hypothesis_id="dedup_improves_quality",
        entity={"name": "C4-clean", "entity_type": "dataset", "description": "d"},
        rationale="release claim carrying a result",
    )
    assert decision.entity is not None and decision.entity.entity_type == "dataset"


def test_unknown_entity_type_rejected():
    with pytest.raises(ValidationError):
        TriageDecision(
            decision="route",
            entity={"name": "X", "entity_type": "gadget", "description": "d"},
            rationale="r",
        )


# ---------------------------------------------------------------------------
# triage_claim — model call, parse, fallback
# ---------------------------------------------------------------------------


def test_triage_attach_round_trip():
    client = _mock_client(
        {
            "decision": "attach",
            "hypothesis_id": "dedup_improves_quality",
            "rationale": "the claim reports a dedup quality result",
        }
    )
    decision = triage_claim(
        client,
        "Exact dedup of C4 raised accuracy 2%.",
        _make_hypotheses(),
        ["quality-filtering-curation"],
        _make_topic(),
    )
    assert decision is not None
    assert decision.decision == "attach"
    assert decision.hypothesis_id == "dedup_improves_quality"


def test_triage_attach_to_unknown_hypothesis_returns_none():
    client = _mock_client(
        {"decision": "attach", "hypothesis_id": "not_a_real_bet", "rationale": "r"}
    )
    decision = triage_claim(
        client, "Some claim.", _make_hypotheses(), [], _make_topic()
    )
    assert decision is None


def test_triage_malformed_json_falls_back_then_returns_none():
    client = MagicMock()
    response = MagicMock()
    response.text = "not json at all"
    client.models.generate_content.return_value = response
    decision = triage_claim(
        client, "Some claim.", _make_hypotheses(), [], _make_topic()
    )
    assert decision is None
    # One parse failure per model in the pair — no blind retries on bad JSON.
    assert client.models.generate_content.call_count == 2


def test_triage_open_with_comparison_round_trip():
    client = _mock_client(
        {
            "decision": "open",
            "new_statement": "Per-dump dedup outperforms global dedup for web corpora.",
            "comparison": {"subject_a": "per-dump dedup", "subject_b": "global dedup"},
            "rationale": "a standing question no current bet tracks",
        }
    )
    decision = triage_claim(
        client, "We compare per-dump and global dedup.", _make_hypotheses(), [], _make_topic()
    )
    assert decision is not None
    assert decision.decision == "open"
    assert decision.comparison is not None
    assert decision.comparison.subject_a == "per-dump dedup"


# ---------------------------------------------------------------------------
# build_triage_prompt — identity shown, belief state withheld
# ---------------------------------------------------------------------------


def test_prompt_shows_identity_and_withholds_belief_state():
    prompt = build_triage_prompt(
        "Exact dedup of C4 raised accuracy 2%.",
        _make_hypotheses(),
        ["quality-filtering-curation"],
        _make_topic(),
    )
    assert "dedup_improves_quality" in prompt
    assert "Training-data deduplication improves downstream model quality." in prompt
    assert "fuzzy dedup vs exact dedup" in prompt
    assert "quality-filtering-curation" in prompt
    # Belief state must be withheld so the matcher cannot over-attach to a
    # hypothesis it can see is already confident.
    assert "alpha" not in prompt
    assert "beta" not in prompt
    assert "4.2" not in prompt


def test_prompt_with_empty_hypothesis_store():
    prompt = build_triage_prompt("A claim.", [], [], _make_topic())
    assert "(none yet)" in prompt


# ---------------------------------------------------------------------------
# §3 Decision 2 — stance resolution against the matched hypothesis
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("stance", ["for", "against", "mixed"])
def test_stance_decision_accepts_directional_verdicts(stance: str):
    decision = StanceDecision(stance=stance, rationale="resolved against the bet")
    assert decision.stance == stance


def test_stance_decision_rejects_neutral():
    with pytest.raises(ValidationError):
        StanceDecision(stance="neutral", rationale="not directional")


def test_stance_decision_rejects_unexpected_fields():
    with pytest.raises(ValidationError):
        StanceDecision(
            stance="for",
            rationale="supports the bet",
            confidence=0.9,
        )


def test_resolve_stance_classifies_claim_against_matched_hypothesis():
    client = _mock_client(
        {
            "stance": "against",
            "rationale": "the reported null result opposes the directional bet",
        }
    )

    decision = resolve_stance(
        client,
        "Fuzzy and exact deduplication showed no significant difference.",
        _make_hypotheses()[1],
    )

    assert decision is not None
    assert decision.stance == "against"


def test_resolve_stance_rejects_neutral_from_model():
    client = _mock_client({"stance": "neutral", "rationale": "no effect"})

    decision = resolve_stance(client, "No difference was observed.", _make_hypotheses()[1])

    assert decision is None
    assert client.models.generate_content.call_count == 2


def test_stance_prompt_names_only_matched_hypothesis_and_withholds_belief():
    matched = _make_hypotheses()[1]
    prompt = build_stance_prompt("A null result.", matched)

    assert matched["id"] in prompt
    assert matched["statement"] in prompt
    assert "dedup_improves_quality" not in prompt
    assert "alpha" not in prompt
    assert "beta" not in prompt
    assert "neutral verdict is not valid" in prompt


def test_stance_prompt_requires_hypothesis_identity():
    with pytest.raises(KeyError):
        build_stance_prompt("A claim.", {"id": "missing_statement"})


# ---------------------------------------------------------------------------
# §2 mechanics — claim-level dedup id, uniform-prior open
# ---------------------------------------------------------------------------


def test_evidence_id_dedups_same_claim_same_hypothesis():
    ev_id = make_evidence_id("Exact dedup raised accuracy 2%.", "dedup_improves_quality")
    again = make_evidence_id("Exact dedup raised accuracy 2%.", "dedup_improves_quality")
    assert ev_id == again

    existing = [{"id": ev_id, "claim": "Exact dedup raised accuracy 2%."}]
    merged = merge_by_id(existing, [{"id": again, "claim": "Exact dedup raised accuracy 2%."}])
    assert len(merged) == 1  # same claim re-matched to the same hypothesis attaches once


def test_evidence_id_distinct_across_hypotheses_and_claims():
    base = make_evidence_id("claim A", "hyp_1")
    assert base != make_evidence_id("claim A", "hyp_2")
    assert base != make_evidence_id("claim B", "hyp_1")


def test_open_creates_uniform_prior_hypothesis():
    decision = TriageDecision(
        decision="open",
        new_statement="Fuzzy deduplication outperforms exact deduplication on web text.",
        rationale="a standing question",
    )
    record = open_hypothesis_record(
        decision, ["quality-filtering-curation"], created_at="2026-07-18"
    )
    assert record["belief"] == {"alpha": 1.0, "beta": 1.0}
    assert record["status"] == "active"
    assert record["statement"] == decision.new_statement
    assert record["theme_ids"] == ["quality-filtering-curation"]
    assert record["comparison"] is None
    assert record["created_at"] == record["last_updated_at"] == "2026-07-18"
    # action_posture is derived at read time (Plan 9 §4) — never stored.
    assert "action_posture" not in record


@pytest.mark.parametrize(
    ("statement", "expected_id"),
    [
        (
            "Fuzzy deduplication outperforms exact deduplication on web text.",
            "fuzzy_deduplication_outperforms_exact_deduplicati_1c82448427",
        ),
        (
            "  Fuzzy   deduplication OUTPERFORMS exact deduplication.  ",
            "fuzzy_deduplication_outperforms_exact_deduplicati_4735e14971",
        ),
        (
            "合成データは人間が作成したデータを上回る。",
            "hypothesis_e2b47997da",
        ),
    ],
)
def test_open_hypothesis_record_generates_expected_id(
    statement: str,
    expected_id: str,
):
    decision = TriageDecision(
        decision="open",
        new_statement=statement,
        rationale="r",
    )

    record = open_hypothesis_record(decision, [], created_at="2026-07-18")

    assert record["id"] == expected_id


def test_open_id_is_stable_so_reruns_merge_to_one_record():
    decision = TriageDecision(
        decision="open",
        new_statement="Fuzzy deduplication outperforms exact deduplication on web text.",
        comparison={"subject_a": "fuzzy dedup", "subject_b": "exact dedup"},
        rationale="r",
    )
    first = open_hypothesis_record(decision, [], created_at="2026-07-18")
    second = open_hypothesis_record(decision, [], created_at="2026-07-19")
    assert first["id"] == second["id"]
    assert merge_by_id([first], [second]) == [first]
    assert first["comparison"] == {"subject_a": "fuzzy dedup", "subject_b": "exact dedup"}


def test_open_ids_distinguish_long_statements_with_the_same_prefix():
    first = TriageDecision(
        decision="open",
        new_statement=(
            "Synthetic data outperforms human-curated data for downstream model "
            "quality in code tasks."
        ),
        rationale="r",
    )
    second = TriageDecision(
        decision="open",
        new_statement=(
            "Synthetic data outperforms human-curated data for downstream model "
            "quality in reasoning tasks."
        ),
        rationale="r",
    )

    first_id = open_hypothesis_record(first, [], created_at="2026-07-18")["id"]
    second_id = open_hypothesis_record(second, [], created_at="2026-07-18")["id"]

    assert first_id != second_id
    assert len(first_id) <= 60
    assert len(second_id) <= 60


def test_open_rejects_blank_statement_before_creating_an_id():
    decision = TriageDecision(decision="open", new_statement="   ", rationale="r")

    with pytest.raises(ValueError, match="statement must not be blank"):
        open_hypothesis_record(decision, [], created_at="2026-07-18")
