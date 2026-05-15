---
name: Bootstrap Parser and Seeder
plan: "15_0"
executor: script
kind: regression
status: passed
last_run: 2026-04-25
script: tests/test_bootstrap_parser.py
---

## Preconditions

- Virtual environment is active: `source sonaryn_env/bin/activate`
- Working directory is the project root
- `research_briefing/src/` is on `PYTHONPATH`

## Steps

1. **Parser extracts JSON block from a well-formed fixture dossier**
   - Run `pytest research_briefing/tests/test_bootstrap_parser.py::test_extract_json_block`
   - Expect: test passes; extracted string is valid JSON matching the fixture's trailing block
   > **Why:** If the extractor fails on a valid dossier, the operator's pasted research output can never be turned into structured wiki files — the entire bootstrap workflow is blocked.

2. **Parser returns intro and per-theme prose sections from a well-formed fixture**
   - Run `pytest research_briefing/tests/test_bootstrap_parser.py::test_extract_theme_sections`
   - Expect: test passes; intro contains pre-theme prose; each `## Theme: {id}` section maps to its prose body; the JSON fence does not bleed into the last section
   > **Why:** If prose sections are not extracted correctly, theme files will be written with wrong or empty bodies, and the overview will render with missing content — both silent failures that corrupt the wiki without an error.

3. **Parser returns a typed ParsedDossier from a valid fixture**
   - Run `pytest research_briefing/tests/test_bootstrap_parser.py::test_parse_dossier_valid`
   - Expect: test passes; returned `ParsedDossier` contains the expected themes, entities, timeline entries, open questions, and prose sections
   > **Why:** A payload with missing or mistyped fields will silently produce an incomplete wiki — themes or entities will be absent without any error, leaving the knowledge base incomplete before the first live ingestion run.

4. **Parser raises a clear error on invalid JSON**
   - Run `pytest research_briefing/tests/test_bootstrap_parser.py::test_parse_dossier_invalid_json`
   - Expect: test passes; a `ValueError` is raised with a message that names the problem
   > **Why:** If invalid JSON is accepted silently or raises an opaque error, the operator has no way to tell whether a bad paste caused data corruption or whether the pipeline simply didn't run.

5. **Parser raises a clear error when no JSON block is found**
   - Run `pytest research_briefing/tests/test_bootstrap_parser.py::test_parse_dossier_no_json_block`
   - Expect: test passes; a `ValueError` is raised explaining that no fenced JSON block was found
   > **Why:** An operator pasting prose-only output will get a confusing exception trace rather than an actionable error message if this check is missing.

6. **Parser rejects a dossier where a JSON theme id has no matching `## Theme:` section**
   - Run `pytest research_briefing/tests/test_bootstrap_parser.py::test_parser_rejects_json_theme_missing_prose_section`
   - Expect: test passes; `ValueError` is raised with a message containing "no matching"
   > **Why:** A JSON theme id with no prose heading means the seeder would write a theme file with an empty body — no error surfaced, no human-readable content written. The parser must catch this before any disk write.

7. **Parser rejects a dossier where a `## Theme:` section has no matching JSON entry**
   - Run `pytest research_briefing/tests/test_bootstrap_parser.py::test_parser_rejects_prose_section_missing_json_theme`
   - Expect: test passes; `ValueError` is raised with a message containing "no matching"
   > **Why:** A prose section with no JSON counterpart indicates the research agent invented a theme outside the schema — that heading would be silently ignored, creating a divergence between what the human reads and what is stored.

8. **Seeder writes all expected files from a fixture payload**
   - Run `pytest research_briefing/tests/test_bootstrap_parser.py::test_seeder_creates_files`
   - Expect: test passes; `themes/*.md`, `entities.json`, `timeline.json`, `open_questions.json`, `overview.md`, and `dossiers/` entries all exist; `entities/` and `timeline/` per-file directories and `watchlist.md` do not exist
   > **Why:** A seeder that writes the old per-file layout instead of flat JSON arrays will break downstream consumers that expect the new format, and the reverse — old consumers reading new layout — will produce empty results with no error.

9. **Seeded theme file has correct frontmatter and prose body from the dossier**
   - Run `pytest research_briefing/tests/test_bootstrap_parser.py::test_seeder_frontmatter_content`
   - Expect: test passes; theme frontmatter contains `id`, `origin`, `novelty_status`, `key_entity_ids`; body text matches the extracted prose section from the dossier
   > **Why:** If the body is empty or copied from the old JSON `body` field rather than the prose section, the knowledge base loses its narrative content — the wiki becomes a list of metadata stubs with no human-readable substance.

10. **Seeder is idempotent — second run on the same dossier is a no-op for theme files and JSON arrays**
    - Run `pytest research_briefing/tests/test_bootstrap_parser.py::test_seeder_idempotent`
    - Expect: test passes; theme file set is identical after two consecutive seeder runs; JSON reference files exist in both runs
    > **Why:** If re-running the seeder duplicates records in JSON arrays or overwrites editorial changes in theme files, any manual edits to the wiki are destroyed each time the operator re-seeds.

11. **Seeder merges a second dossier into JSON arrays by stable id without duplicating records**
    - Run `pytest research_briefing/tests/test_bootstrap_parser.py::test_seeder_merges_second_dossier`
    - Expect: test passes; entities from both dossiers are present in `entities.json`; shared `anthropic` id appears exactly once; shared open question appears exactly once; new question from dossier 2 is present
    > **Why:** A seeder that appends duplicates creates inconsistent arrays — downstream consumers pick up two conflicting records for the same entity or question, making the wiki incoherent.

12. **overview.md contains a link to each theme and the top open questions**
    - Run `pytest research_briefing/tests/test_bootstrap_parser.py::test_overview_contains_theme_links_and_top_questions`
    - Expect: test passes; `overview.md` body contains `themes/{id}.md` links for every seeded theme and at least one open question text
    > **Why:** An overview that does not render theme links or surface open questions provides no value as a landing page — the operator has no single place to understand what the wiki contains or what needs investigation.

13. **Seeder writes no files if the parser has already rejected the input**
    - Run `pytest research_briefing/tests/test_bootstrap_parser.py::test_no_partial_writes_on_parse_failure`
    - Expect: test passes; the topic directory contains no new files after a failed parse attempt
    > **Why:** A partial write leaves the wiki in an undefined state — some themes seeded, others not — with no way to tell which data is trustworthy without manually inspecting every file.

## Teardown

Each test that writes files must use `tmp_path` so the filesystem is cleaned up automatically by pytest.
