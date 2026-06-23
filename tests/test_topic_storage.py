"""Tests for the canonical topic storage front door (Plan 8).

Covers the storage *mechanics* that every downstream stage builds against:
JSON-array round-trips for the belief-graph stores (hypotheses.json,
evidence.json) and the wiki reference stores (entities.json, timeline.json);
idempotent merge-by-id; the credibility-weighted strength increment with
provenance append; the Beta belief update; raw payload persistence; and YAML
frontmatter preservation on partial updates of themes/overview.

> **Why:** This module is the single front door for durable topic memory. If a
> round-trip drops a field, a merge duplicates a record, or a partial frontmatter
> update silently rewrites the body, every downstream stage inherits corrupt
> state. These checks pin the on-disk contract so the belief graph stays
> trustworthy across runs.

Run from the project root with the virtualenv active:
    source .venv/bin/activate
    PYTHONPATH=src pytest tests/test_topic_storage.py
"""

import json

import pytest

from topics import storage
from topics.frontmatter import load_frontmatter, write_with_frontmatter


# ---------------------------------------------------------------------------
# Layer 1 — JSON-array primitives and merge-by-id
# ---------------------------------------------------------------------------


def test_load_missing_file_returns_empty(tmp_path):
    assert storage.load_json_array(tmp_path / "absent.json") == []


def test_load_malformed_file_returns_empty(tmp_path):
    path = tmp_path / "broken.json"
    path.write_text("{ not json", encoding="utf-8")
    assert storage.load_json_array(path) == []


def test_non_array_top_level_returns_empty(tmp_path):
    path = tmp_path / "object.json"
    path.write_text('{"id": "x"}', encoding="utf-8")
    assert storage.load_json_array(path) == []


def test_save_then_load_round_trips_records(tmp_path):
    path = tmp_path / "records.json"
    records = [
        {"id": "a", "value": 1, "nested": {"k": "é"}},
        {"id": "b", "value": 2, "list": [1, 2, 3]},
    ]
    storage.save_json_array(path, records)
    assert storage.load_json_array(path) == records


def test_save_creates_parent_dirs(tmp_path):
    path = tmp_path / "deep" / "nested" / "records.json"
    storage.save_json_array(path, [{"id": "a"}])
    assert path.exists()


def test_save_preserves_unicode_unescaped(tmp_path):
    path = tmp_path / "u.json"
    storage.save_json_array(path, [{"id": "a", "name": "café"}])
    assert "café" in path.read_text(encoding="utf-8")


def test_merge_appends_new_ids():
    existing = [{"id": "a"}]
    incoming = [{"id": "b"}, {"id": "c"}]
    merged = storage.merge_by_id(existing, incoming)
    assert [r["id"] for r in merged] == ["a", "b", "c"]


def test_merge_skips_existing_ids_and_keeps_existing_unchanged():
    existing = [{"id": "a", "value": "original"}]
    incoming = [{"id": "a", "value": "REPLACED"}, {"id": "b"}]
    merged = storage.merge_by_id(existing, incoming)
    assert merged == [{"id": "a", "value": "original"}, {"id": "b"}]


def test_merge_is_idempotent():
    existing = [{"id": "a"}]
    incoming = [{"id": "a"}, {"id": "b"}]
    once = storage.merge_by_id(existing, incoming)
    twice = storage.merge_by_id(once, incoming)
    assert once == twice == [{"id": "a"}, {"id": "b"}]


def test_merge_custom_id_key():
    existing = [{"signal_id": "s1"}]
    incoming = [{"signal_id": "s1"}, {"signal_id": "s2"}]
    merged = storage.merge_by_id(existing, incoming, id_key="signal_id")
    assert [r["signal_id"] for r in merged] == ["s1", "s2"]


def test_merge_missing_id_raises():
    with pytest.raises(KeyError):
        storage.merge_by_id([], [{"no_id": "x"}])


# ---------------------------------------------------------------------------
# Layer 2 — belief-graph store round-trips
# ---------------------------------------------------------------------------


def test_hypotheses_round_trip(tmp_path):
    records = [
        {
            "id": "data_scarcity_moat_weakening",
            "statement": "Data scarcity is becoming a weaker moat.",
            "theme_ids": ["synthetic-data-generation"],
            "status": "active",
            "belief": {"alpha": 8.7, "beta": 3.6},
            "action_posture": "monitor",
            "comparison": None,
            "resolution_criterion": {
                "metric": "fraction of synthetic-trained releases",
                "threshold": "> 50%",
                "scope": "frontier-class releases",
                "horizon": "2027-06-30",
            },
            "depends_on": [{"hypothesis_id": "synthetic_data_quality_rising", "relationship": "supports"}],
            "created_at": "2026-04-26",
            "last_updated_at": "2026-04-26",
        }
    ]
    storage.save_hypotheses(tmp_path, records)
    assert storage.load_hypotheses(tmp_path) == records
    assert (tmp_path / storage.HYPOTHESES_FILENAME).exists()


def test_evidence_round_trip(tmp_path):
    records = [
        {
            "id": "ev_001",
            "hypothesis_id": "data_scarcity_moat_weakening",
            "claim": "Synthetic eval sets match human-labeled baselines.",
            "stance": "for",
            "strength": 1.7,
            "provenance": [
                {"signal_id": "arxiv_2026-04-26_a3f7b2c1de", "weight_applied": 0.8},
                {"signal_id": "arxiv_2026-05-01_b9c3d4e2fa", "weight_applied": 0.9},
            ],
            "summary": "Two papers showed benchmark parity.",
            "created_at": "2026-04-26",
            "last_updated_at": "2026-05-01",
        }
    ]
    storage.save_evidence(tmp_path, records)
    assert storage.load_evidence(tmp_path) == records


def test_empty_belief_stores_load_as_empty(tmp_path):
    assert storage.load_hypotheses(tmp_path) == []
    assert storage.load_evidence(tmp_path) == []


# ---------------------------------------------------------------------------
# Credibility weighting + evidence strength increment
# ---------------------------------------------------------------------------


def test_credibility_to_weight_scales_to_unit():
    assert storage.credibility_to_weight(10) == 1.0
    assert storage.credibility_to_weight(8) == pytest.approx(0.8)
    assert storage.credibility_to_weight(0) == 0.0


def test_credibility_none_falls_back_to_neutral():
    assert storage.credibility_to_weight(None) == storage.NEUTRAL_CREDIBILITY_WEIGHT


def test_add_signal_to_evidence_appends_and_increments():
    evidence = {"id": "ev_001", "strength": 0.0, "provenance": []}
    updated = storage.add_signal_to_evidence(evidence, signal_id="sig_1", source_credibility=8)
    assert updated["strength"] == pytest.approx(0.8)
    assert updated["provenance"] == [{"signal_id": "sig_1", "weight_applied": 0.8}]


def test_add_signal_to_evidence_accumulates_across_signals():
    evidence = {"id": "ev_001", "strength": 0.0, "provenance": []}
    evidence = storage.add_signal_to_evidence(evidence, signal_id="sig_1", source_credibility=8)
    evidence = storage.add_signal_to_evidence(evidence, signal_id="sig_2", source_credibility=9)
    assert evidence["strength"] == pytest.approx(1.7)
    assert [p["signal_id"] for p in evidence["provenance"]] == ["sig_1", "sig_2"]


def test_add_signal_to_evidence_null_credibility_uses_neutral():
    evidence = {"id": "ev_001", "strength": 0.0, "provenance": []}
    updated = storage.add_signal_to_evidence(evidence, signal_id="sig_1", source_credibility=None)
    assert updated["strength"] == pytest.approx(storage.NEUTRAL_CREDIBILITY_WEIGHT)


def test_add_signal_to_evidence_does_not_mutate_input():
    evidence = {"id": "ev_001", "strength": 0.5, "provenance": [{"signal_id": "old", "weight_applied": 0.5}]}
    storage.add_signal_to_evidence(evidence, signal_id="sig_1", source_credibility=10)
    assert evidence["strength"] == 0.5
    assert len(evidence["provenance"]) == 1


def test_add_signal_to_evidence_defaults_missing_fields():
    updated = storage.add_signal_to_evidence({"id": "ev_x"}, signal_id="sig_1", source_credibility=10)
    assert updated["strength"] == 1.0
    assert updated["provenance"] == [{"signal_id": "sig_1", "weight_applied": 1.0}]


# ---------------------------------------------------------------------------
# Beta belief update
# ---------------------------------------------------------------------------


def test_belief_for_moves_alpha():
    assert storage.apply_belief_update({"alpha": 1.0, "beta": 1.0}, "for", 0.8) == {"alpha": 1.8, "beta": 1.0}


def test_belief_against_moves_beta():
    assert storage.apply_belief_update({"alpha": 1.0, "beta": 1.0}, "against", 0.8) == {"alpha": 1.0, "beta": 1.8}


def test_belief_mixed_splits_and_raises_mass_not_mean():
    result = storage.apply_belief_update({"alpha": 2.0, "beta": 2.0}, "mixed", 1.0)
    assert result == {"alpha": 2.5, "beta": 2.5}
    # mean unchanged (0.5) but evidence mass grew from 4 to 5
    assert result["alpha"] + result["beta"] == 5.0


def test_belief_neutral_is_noop():
    belief = {"alpha": 3.0, "beta": 2.0}
    assert storage.apply_belief_update(belief, "neutral", 0.9) == belief


def test_belief_defaults_to_uniform_prior():
    assert storage.apply_belief_update({}, "for", 1.0) == {"alpha": 2.0, "beta": 1.0}


def test_belief_unknown_stance_raises():
    with pytest.raises(ValueError):
        storage.apply_belief_update({"alpha": 1.0, "beta": 1.0}, "sideways", 1.0)


def test_belief_update_does_not_mutate_input():
    belief = {"alpha": 1.0, "beta": 1.0}
    storage.apply_belief_update(belief, "for", 5.0)
    assert belief == {"alpha": 1.0, "beta": 1.0}


# ---------------------------------------------------------------------------
# Raw payload persistence
# ---------------------------------------------------------------------------


def test_save_raw_payload_native_layout(tmp_path):
    dest = storage.save_raw_payload(
        tmp_path, b"<rss>...</rss>", date="2026-05-01", source_name="arxiv", extension=".xml"
    )
    assert dest == tmp_path / "raw" / "2026-05-01" / "arxiv.xml"
    assert dest.read_bytes() == b"<rss>...</rss>"


def test_save_raw_payload_normalises_extension(tmp_path):
    dest = storage.save_raw_payload(
        tmp_path, b"<html></html>", date="2026-05-01", source_name="lab_blog", extension="html"
    )
    assert dest.name == "lab_blog.html"


# ---------------------------------------------------------------------------
# YAML frontmatter preserved on partial updates (themes / overview)
# ---------------------------------------------------------------------------


def test_frontmatter_partial_update_preserves_body_and_other_keys(tmp_path):
    path = tmp_path / "themes" / "synthetic-data-generation.md"
    body = "## Synthetic Data\n\nLong-form theme prose that must survive edits.\n"
    write_with_frontmatter(
        path,
        {"id": "synthetic-data-generation", "name": "Synthetic Data", "updated_at": "2026-04-26"},
        body,
    )

    storage.update_frontmatter(path, {"updated_at": "2026-05-01"})

    fm, preserved_body = load_frontmatter(path)
    assert fm["updated_at"] == "2026-05-01"
    assert fm["id"] == "synthetic-data-generation"
    assert fm["name"] == "Synthetic Data"
    assert preserved_body == body


def test_frontmatter_round_trip_via_storage_reexports(tmp_path):
    path = tmp_path / "overview.md"
    storage.write_with_frontmatter(path, {"topic_id": "data_advantage"}, "# Overview\n")
    fm, body = storage.load_frontmatter(path)
    assert fm == {"topic_id": "data_advantage"}
    assert body == "# Overview\n"


# ---------------------------------------------------------------------------
# Wiki JSON stores (entities / timeline) round-trip + merge
# ---------------------------------------------------------------------------


def test_wiki_json_store_round_trip_and_merge(tmp_path):
    entities_path = tmp_path / "entities.json"
    storage.save_json_array(entities_path, [{"id": "e1", "name": "C4"}])
    merged = storage.merge_by_id(
        storage.load_json_array(entities_path),
        [{"id": "e1", "name": "C4-REPLACED"}, {"id": "e2", "name": "RedPajama"}],
    )
    storage.save_json_array(entities_path, merged)
    reloaded = storage.load_json_array(entities_path)
    assert reloaded == [{"id": "e1", "name": "C4"}, {"id": "e2", "name": "RedPajama"}]
    # round-trips as valid JSON
    assert json.loads(entities_path.read_text(encoding="utf-8")) == reloaded
