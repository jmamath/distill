# Plan 3 — First Bootstrap Run (Data Advantage)

**Original task id:** 15.1b
**Depends on:** Plan 2 (topic configuration contract) must be complete — the full `topic.md` (audience profile, source priorities, taxonomy, scoring dimensions, action vocabulary) is the input to the deep-research prompt.
**Status: passed** — First bootstrap run completed 2026-04-22: `data/research_topics/data_advantage/dossiers/bootstrap_2026_04_22.md` seeded `themes/`, `entities.json`, `timeline.json`, `open_questions.json`, and `overview.md`.

---

Run the first real deep-research pass and use Plan 1's tooling to seed the `data_advantage` wiki. This is the operator task, not a code task — the output is real data files, not new source code.

**Why this matters:** Without seeded themes and entities, "novelty" and "landscape fit" in later tasks have nothing to attach to. The seeded wiki also proves the dossier contract and on-disk layout before any live ingestion exists.

## Changes

| File | Action | Description |
|---|---|---|
| `data/research_topics/data_advantage/topic.md` | **UPDATE** | Already exists from Plan 2; used as-is to generate the bootstrap prompt |
| `data/research_topics/data_advantage/dossiers/bootstrap_<date>.md` | **NEW** | Pasted output from the deep research run |
| `data/research_topics/data_advantage/themes/` | **NEW** | One `.md` per theme; frontmatter + full prose section from dossier |
| `data/research_topics/data_advantage/entities.json` | **NEW** | Flat JSON array of entity records |
| `data/research_topics/data_advantage/timeline.json` | **NEW** | Flat JSON array of timeline entries |
| `data/research_topics/data_advantage/open_questions.json` | **NEW** | Flat JSON array of open questions with `theme_ids` and `priority` |
| `data/research_topics/data_advantage/overview.md` | **NEW** | Rendered: intro prose + theme list with links + top open questions |

## Operator workflow

1. Run `prompt.py` against the completed `data_advantage/topic.md` → paste output into external deep research tool.
2. Paste full response into `dossiers/bootstrap_<date>.md`.
3. Run the seeder (from the project root, venv active):
   ```bash
   source sonaryn_env/bin/activate
   PYTHONPATH=research_briefing/src python -m topics.bootstrap.seeder \
       --dossier research_briefing/data/research_topics/data_advantage/dossiers/bootstrap_<date>.md
   ```
   `--topic-dir` and `--date` are optional; both default to sensible values (grandparent of the dossier file, and today's date respectively).
4. Inspect the generated files: `themes/`, `entities.json`, `timeline.json`, `open_questions.json`, `overview.md`.

## Verification

- One bootstrap run produces a complete seeded tree from one dossier paste.
- Operator judges the seeded wiki **useful enough** to read in one sitting and truer than an empty folder.
- No code changes needed — any needed fixes go back to Plan 1.

**Explicitly out of scope:** source adapters (Plan 4), live scoring, wiki updater, brief generation.
