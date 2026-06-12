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
   - Expect: test passes; returned `ParsedDossier` contains the expected themes, entities, timeline entries, hypotheses, and prose sections
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
   - Expect: test passes; `themes/*.md`, `entities.json`, `timeline.json`, `hypotheses.json`, `overview.md`, and `dossiers/` entries all exist; `open_questions.json`, `entities/` and `timeline/` per-file directories, and `watchlist.md` do not exist
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
    - Expect: test passes; entities from both dossiers are present in `entities.json`; shared `anthropic` id appears exactly once; shared hypothesis id appears exactly once; new hypothesis from dossier 2 is present
    > **Why:** A seeder that appends duplicates creates inconsistent arrays — downstream consumers pick up two conflicting records for the same entity or hypothesis, making the wiki incoherent.

12. **overview.md contains a link to each theme and the top open hypotheses**
    - Run `pytest research_briefing/tests/test_bootstrap_parser.py::test_overview_contains_theme_links_and_top_hypotheses`
    - Expect: test passes; `overview.md` body contains `themes/{id}.md` links for every seeded theme and at least one hypothesis statement under "Top Open Hypotheses"
    > **Why:** An overview that does not render theme links or surface open hypotheses provides no value as a landing page — the operator has no single place to understand what the wiki contains or what needs investigation.

13. **Seeded hypothesis records carry the durable belief shape**
    - Run `pytest research_briefing/tests/test_bootstrap_parser.py::test_seeder_hypothesis_record_shape`
    - Expect: test passes; each seeded hypothesis has a uniform prior (`belief.alpha == belief.beta == 1.0`), `status: active`, `created_at`/`last_updated_at` timestamps, the authored `statement`/`theme_ids`/`action_posture` carried through, and the optional `resolution_criterion` preserved with all four sub-fields when present
    > **Why:** If bootstrap seeds the wrong belief shape — a non-uniform prior, a missing status, or a dropped resolution criterion — every downstream Bayesian update starts from corrupted state, and the betting-market resolvability guarantee silently breaks before the first ingestion run.

14. **Comparative hypotheses survive parse and seed as pairwise edges**
    - Run `pytest research_briefing/tests/test_bootstrap_parser.py::test_parse_comparative_hypothesis research_briefing/tests/test_bootstrap_parser.py::test_seeder_preserves_comparison`
    - Expect: tests pass; a hypothesis with a populated `comparison` parses into a typed `{subject_a, subject_b}` and the seeded record carries that comparison through unchanged, with no empty `resolution_criterion` synthesized
    > **Why:** A non-null `comparison` is the *only* marker that distinguishes a pairwise-edge bet from a standalone one (Plan 8 stores no type tag). If it is dropped or coerced on the way to disk, the belief graph silently loses every head-to-head edge and "who leads" views can never be derived.

15. **Seeder writes no files if the parser has already rejected the input**
    - Run `pytest research_briefing/tests/test_bootstrap_parser.py::test_no_partial_writes_on_parse_failure`
    - Expect: test passes; the topic directory contains no new files after a failed parse attempt
    > **Why:** A partial write leaves the wiki in an undefined state — some themes seeded, others not — with no way to tell which data is trustworthy without manually inspecting every file.

## Teardown

Each test that writes files must use `tmp_path` so the filesystem is cleaned up automatically by pytest.
