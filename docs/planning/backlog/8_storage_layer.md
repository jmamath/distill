# Plan 8 — Topic Storage Helpers And Layout Documentation

**Original task id:** 15.4
**Depends on:** Plan 1 (bootstrap tooling, seeds `overview.md`, `themes/`, `entities.json`, `timeline.json`, `open_questions.json`); Plan 1 pass-2 pipeline (defines the signal frontmatter schema that storage helpers must honour).

---

Add the read/merge helpers that make topic files safely accessible to downstream stages, seed the initial `hypotheses.json` and `evidence.json`, and document the full flat layout.

**Why this matters:** A strategic briefing product cannot rely on per-run summaries alone. It needs durable topic memory that persists across runs. The signal schema is already defined by the pass-2 pipeline plan; this task adds the read/merge helpers and documents the complete on-disk contract so every downstream stage builds against a stable foundation.

## Changes

| File | Action | Description |
|---|---|---|
| `src/topics/storage.py` | **NEW** | Save/load helpers for topic files and run outputs (frontmatter-aware read/write, list/merge by stable id); signal helpers conform to the pass-2 schema and support partial updates so the wiki updater can write back `classification` and `theme_id_assigned`; evidence helpers expose a credibility-weighted `strength` increment with provenance append; open-question helpers expose a `count` increment with provenance append |
| `data/research_topics/README.md` | **UPDATE** | Document the flat layout from architecture §6, including signal schema reference |
| `data/research_topics/data_advantage/hypotheses.json` | **NEW** | Durable belief store for strategic topic hypotheses with prior/posterior state and a derived `convergence` score updated by the knowledge update loop |
| `data/research_topics/data_advantage/evidence.json` | **NEW** | Evidence records linking claims to hypotheses; each record holds `id`, `claim`, `stance`, a `strength` counter (incremented per supporting signal, weighted by `source_credibility`), and a `provenance` list of `{signal_id, weight_applied}` entries |
| `data/research_topics/data_advantage/raw/` | **NEW** | Original fetched payloads, partitioned `{yyyy-mm-dd}/{source_name}{.xml/.html}` (native format, not coerced to JSON) |
| `tests/test_topic_storage.py` | **NEW** | Round-trip read/write for each file type; frontmatter preserved on update |

## Storage layout must support

- raw ingested items (`raw/`)
- scored signals (`signals/`)
- durable belief graph state (`hypotheses.json`, `evidence.json`)
- wiki state (flat: `themes/*.md`, `entities.json`, `timeline.json`, `open_questions.json`, `overview.md`); storage helpers do JSON load/merge by id (in addition to YAML frontmatter for themes/overview)
- generated briefings (`briefings/`)
- dossiers (`dossiers/`)

## Initial schema must make explicit

- hypothesis node fields for belief state, action posture, strategic rationale, dependency edges, linked evidence ids, and a derived `convergence` score
- evidence record fields for `id`, `claim`, `stance`, a `strength` counter incremented per supporting signal (weighted by signal `source_credibility`; `null` credibility falls back to a neutral weight defined in the knowledge update loop plan), and a `provenance` list of `{signal_id, weight_applied}` entries
- open question record fields extended with a `count` of distinct signals that raised it and a `provenance` list of `{signal_id}` references
- dependency edges stored on hypothesis records rather than in a separate edge file

**Explicitly out of scope:** `overview.md`, `themes/`, `entities.json`, `timeline.json`, `open_questions.json` — those come from Plan 1 (bootstrap). There is **no** `wiki/` subdirectory; the wiki is the flat human-readable tree.

## Verification

- One topic folder can store a complete run end-to-end using the flat layout
- Wiki files are human-readable and editable
- The structure is reusable for another topic id
- Storage helpers preserve YAML frontmatter on partial updates (no drift)
