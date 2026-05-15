"""Tests for the bootstrap parser and seeder (Task 15.0).

Covers: JSON block extraction, DossierPayload validation, prose-section
extraction, theme-id mismatch rejection, seeder file layout, frontmatter
content, idempotency, second-dossier merge, overview rendering, and the
no-partial-write guarantee.

Run from the project root with the virtualenv active:
    source .venv/bin/activate
    PYTHONPATH=src pytest tests/test_bootstrap_parser.py
"""

import json
from pathlib import Path

import pytest

from topics.bootstrap.parser import (
    DossierPayload,
    ParsedDossier,
    extract_json_block,
    extract_theme_sections,
    parse_dossier,
)
from topics.bootstrap.seeder import seed_topic
from topics.frontmatter import load_frontmatter

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_VALID_JSON = """\
{
  "themes": [
    {
      "id": "synthetic-data-generation",
      "name": "Synthetic Data Generation",
      "description": "Using model-generated data to train better models.",
      "taxonomy_ref": "synthetic-data",
      "key_entity_ids": ["anthropic", "common-crawl"]
    },
    {
      "id": "rlhf-data-curation",
      "name": "RLHF Data Curation",
      "description": "Curating high-quality preference data for alignment.",
      "taxonomy_ref": "alignment-data",
      "key_entity_ids": ["anthropic"]
    }
  ],
  "entities": [
    {
      "id": "anthropic",
      "name": "Anthropic",
      "entity_type": "lab",
      "description": "AI safety company and creator of Claude."
    },
    {
      "id": "common-crawl",
      "name": "Common Crawl",
      "entity_type": "dataset",
      "description": "Large open web crawl dataset."
    }
  ],
  "timeline": [
    {
      "id": "2024-03-15-constitutional-ai-v2",
      "date": "2024-03-15",
      "title": "Anthropic released Constitutional AI v2",
      "theme_ids": ["rlhf-data-curation"],
      "entity_ids": ["anthropic"],
      "body": "The update refined the preference data pipeline for constitutional AI training."
    }
  ],
  "open_questions": [
    {
      "id": "oq-synthetic-quality-threshold",
      "question": "At what quality level does synthetic data match real-world data?",
      "theme_ids": ["synthetic-data-generation"],
      "priority": "high"
    },
    {
      "id": "oq-rlhf-collapse",
      "question": "How do RLHF pipelines avoid reward model collapse under synthetic data?",
      "theme_ids": ["rlhf-data-curation"],
      "priority": "medium"
    }
  ]
}"""

_VALID_DOSSIER = f"""\
# Data Advantage Landscape — Bootstrap Dossier

This is prose context for the operator. It is not parsed.

## Theme: synthetic-data-generation

Synthetic data generation has become a key lever in modern AI training pipelines.
Models trained on high-quality synthetic data can match or exceed those trained on
raw web crawls for many downstream tasks.

## Theme: rlhf-data-curation

Preference data quality is now the primary bottleneck in RLHF pipelines. The field
has moved from crowdsourced preference labels to model-generated and model-filtered
datasets.

```json
{_VALID_JSON}
```"""

_SECOND_JSON = """\
{
  "themes": [
    {
      "id": "retrieval-augmented-training",
      "name": "Retrieval-Augmented Training",
      "description": "Using retrieval at training time to improve model quality.",
      "taxonomy_ref": "retrieval-methods",
      "key_entity_ids": ["cohere"]
    }
  ],
  "entities": [
    {
      "id": "cohere",
      "name": "Cohere",
      "entity_type": "company",
      "description": "Enterprise NLP company."
    },
    {
      "id": "anthropic",
      "name": "Anthropic",
      "entity_type": "lab",
      "description": "AI safety company and creator of Claude."
    }
  ],
  "timeline": [],
  "open_questions": [
    {
      "id": "oq-synthetic-quality-threshold",
      "question": "At what quality level does synthetic data match real-world data?",
      "theme_ids": ["synthetic-data-generation"],
      "priority": "high"
    },
    {
      "id": "oq-rat-cost",
      "question": "Is retrieval-augmented training cost-competitive with synthetic pipelines?",
      "theme_ids": ["retrieval-augmented-training"],
      "priority": "medium"
    }
  ]
}"""

_SECOND_DOSSIER = f"""\
# Data Advantage — Second Dossier

## Theme: retrieval-augmented-training

RAT is an emerging alternative to pure synthetic data pipelines. By incorporating
retrieval at training time, models can ground their outputs in factual documents
rather than relying purely on memorized patterns.

```json
{_SECOND_JSON}
```"""


# ---------------------------------------------------------------------------
# Parser tests
# ---------------------------------------------------------------------------


def test_extract_json_block():
    """Parser extracts the JSON string from the trailing fence."""
    raw = extract_json_block(_VALID_DOSSIER)
    data = json.loads(raw)
    assert "themes" in data
    assert "entities" in data


def test_extract_theme_sections():
    """extract_theme_sections returns intro and per-theme prose dict."""
    intro, sections = extract_theme_sections(_VALID_DOSSIER)
    assert "This is prose context" in intro
    assert "synthetic-data-generation" in sections
    assert "rlhf-data-curation" in sections
    assert "Synthetic data generation has become" in sections["synthetic-data-generation"]
    assert "Preference data quality" in sections["rlhf-data-curation"]
    # JSON fence must not bleed into the last theme section.
    assert "```json" not in sections["rlhf-data-curation"]


def test_parse_dossier_valid():
    """parse_dossier returns a correctly typed ParsedDossier from a valid fixture."""
    parsed = parse_dossier(_VALID_DOSSIER)
    assert isinstance(parsed, ParsedDossier)
    assert len(parsed.payload.themes) == 2
    assert parsed.payload.themes[0].id == "synthetic-data-generation"
    assert len(parsed.payload.entities) == 2
    assert parsed.payload.entities[0].entity_type == "lab"
    assert len(parsed.payload.timeline) == 1
    assert len(parsed.payload.open_questions) == 2
    assert "synthetic-data-generation" in parsed.theme_sections
    assert "rlhf-data-curation" in parsed.theme_sections
    assert "This is prose context" in parsed.intro


def test_parse_dossier_invalid_json():
    """parse_dossier raises ValueError with a clear message on malformed JSON."""
    bad_dossier = "## Theme: foo\n\nSome prose.\n\n```json\n{ bad json !! }\n```"
    with pytest.raises(ValueError, match="not valid JSON"):
        parse_dossier(bad_dossier)


def test_parse_dossier_no_json_block():
    """parse_dossier raises ValueError when the dossier contains no JSON fence."""
    prose_only = "# Research Output\n\nJust prose, no JSON block at all.\n"
    with pytest.raises(ValueError, match="No fenced JSON block"):
        parse_dossier(prose_only)


def test_parser_rejects_json_theme_missing_prose_section():
    """parse_dossier raises ValueError when a JSON theme id has no ## Theme: section."""
    dossier = """\
## Theme: bar

Some prose for bar.

```json
{
  "themes": [
    {"id": "foo", "name": "Foo", "description": "desc", "key_entity_ids": []}
  ],
  "entities": [],
  "timeline": [],
  "open_questions": []
}
```"""
    with pytest.raises(ValueError, match="no matching"):
        parse_dossier(dossier)


def test_parser_rejects_prose_section_missing_json_theme():
    """parse_dossier raises ValueError when a ## Theme: heading has no JSON entry."""
    dossier = """\
## Theme: extra-section

Prose for an extra section with no JSON entry.

```json
{
  "themes": [],
  "entities": [],
  "timeline": [],
  "open_questions": []
}
```"""
    with pytest.raises(ValueError, match="no matching"):
        parse_dossier(dossier)


# ---------------------------------------------------------------------------
# Seeder tests
# ---------------------------------------------------------------------------


def test_seeder_creates_files(tmp_path):
    """Seeder writes themes/, entities.json, timeline.json, open_questions.json,
    overview.md, and dossiers/."""
    parsed = parse_dossier(_VALID_DOSSIER)
    seed_topic(tmp_path, parsed, dossier_raw=_VALID_DOSSIER, dossier_date="2026-04-21")

    assert (tmp_path / "themes" / "synthetic-data-generation.md").exists()
    assert (tmp_path / "themes" / "rlhf-data-curation.md").exists()
    assert (tmp_path / "entities.json").exists()
    assert (tmp_path / "timeline.json").exists()
    assert (tmp_path / "open_questions.json").exists()
    assert (tmp_path / "overview.md").exists()
    assert (tmp_path / "dossiers" / "bootstrap_2026-04-21.md").exists()
    # Old per-file directories must not exist.
    assert not (tmp_path / "entities").is_dir()
    assert not (tmp_path / "timeline").is_dir()
    assert not (tmp_path / "watchlist.md").exists()


def test_seeder_frontmatter_content(tmp_path):
    """Seeded theme file has correct frontmatter fields and prose body from the dossier."""
    parsed = parse_dossier(_VALID_DOSSIER)
    seed_topic(tmp_path, parsed, dossier_raw=_VALID_DOSSIER, dossier_date="2026-04-21")

    fm, body = load_frontmatter(tmp_path / "themes" / "synthetic-data-generation.md")
    assert fm["id"] == "synthetic-data-generation"
    assert fm["origin"] == "bootstrap"
    assert fm["novelty_status"] == "globally_novel"
    assert "anthropic" in fm["key_entity_ids"]
    assert "common-crawl" in fm["key_entity_ids"]
    # Body must be the prose section extracted from the dossier, not a JSON body field.
    assert "Synthetic data generation has become" in body


def test_seeder_idempotent(tmp_path):
    """Running the seeder twice on the same payload produces no new theme files."""
    parsed = parse_dossier(_VALID_DOSSIER)
    seed_topic(tmp_path, parsed, dossier_raw=_VALID_DOSSIER, dossier_date="2026-04-21")

    files_after_first = _collect_files(tmp_path)

    # Re-seed with the same payload — must be a no-op for wiki files.
    seed_topic(tmp_path, parsed, dossier_raw=_VALID_DOSSIER, dossier_date="2026-04-22")

    files_after_second = _collect_files(tmp_path)

    # All files from the first run must still exist.
    for rel in files_after_first:
        assert rel in files_after_second, f"File disappeared: {rel}"

    # Theme files are unchanged (same set).
    first_themes = {f for f in files_after_first if f.startswith("themes/")}
    second_themes = {f for f in files_after_second if f.startswith("themes/")}
    assert first_themes == second_themes, "Theme files changed on second seed run"

    # JSON reference files exist in both runs.
    for json_file in ("entities.json", "timeline.json", "open_questions.json"):
        assert json_file in files_after_first
        assert json_file in files_after_second


def test_seeder_merges_second_dossier(tmp_path):
    """A second dossier adds new ids; existing ids are not duplicated in JSON arrays."""
    parsed1 = parse_dossier(_VALID_DOSSIER)
    seed_topic(tmp_path, parsed1, dossier_raw=_VALID_DOSSIER, dossier_date="2026-04-21")

    parsed2 = parse_dossier(_SECOND_DOSSIER)
    seed_topic(tmp_path, parsed2, dossier_raw=_SECOND_DOSSIER, dossier_date="2026-04-22")

    # New theme from dossier 2 must exist.
    assert (tmp_path / "themes" / "retrieval-augmented-training.md").exists()
    # Original themes must still exist.
    assert (tmp_path / "themes" / "synthetic-data-generation.md").exists()

    # entities.json: cohere added, anthropic not duplicated.
    entities = json.loads((tmp_path / "entities.json").read_text())
    entity_ids = [e["id"] for e in entities]
    assert "cohere" in entity_ids
    assert "anthropic" in entity_ids
    assert entity_ids.count("anthropic") == 1

    # open_questions.json: shared id must appear exactly once; new id present.
    questions = json.loads((tmp_path / "open_questions.json").read_text())
    question_ids = [q["id"] for q in questions]
    assert question_ids.count("oq-synthetic-quality-threshold") == 1
    assert "oq-rat-cost" in question_ids


def test_overview_contains_theme_links_and_top_questions(tmp_path):
    """overview.md contains a link to each theme and a top open questions section."""
    parsed = parse_dossier(_VALID_DOSSIER)
    seed_topic(tmp_path, parsed, dossier_raw=_VALID_DOSSIER, dossier_date="2026-04-21")

    _, body = load_frontmatter(tmp_path / "overview.md")
    assert "themes/synthetic-data-generation.md" in body
    assert "themes/rlhf-data-curation.md" in body
    assert "At what quality level does synthetic data match real-world data?" in body


def test_no_partial_writes_on_parse_failure(tmp_path):
    """A failed parse leaves the topic directory empty (no partial writes)."""
    bad_dossier = "Prose only, no JSON block.\n"
    with pytest.raises(ValueError):
        parsed = parse_dossier(bad_dossier)
        seed_topic(tmp_path, parsed, dossier_raw=bad_dossier, dossier_date="2026-04-21")

    # Directory must be empty (seed_topic is never reached).
    assert not any(tmp_path.iterdir())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _collect_files(base: Path) -> set[str]:
    """Return a set of relative file paths under base."""
    return {str(p.relative_to(base)) for p in base.rglob("*") if p.is_file()}
