# Plan 1 — Bootstrap Tooling

**Original task id:** 15.0
**Status: passed** — 13 tests passing as of 2026-04-25. Spec: `docs/specs/15_0_bootstrap_tooling.test.md`.

> **Superseded scope:** This plan originally seeded a separate `open_questions.json`. That store was later replaced by uniform-prior hypotheses in `hypotheses.json`. The code change shipped (the seeder/parser/prompt produce hypotheses), and the remaining live-data migration is tracked in **Plan 15**, not here. This file is left as the immutable record of the original bootstrap tooling.

---

Build the code that can parse a deep-research dossier and seed the topic wiki from it. No actual research run happens here — the goal is a working, tested pipeline ready for 15.0b to use.

**Why this matters:** Without a parser and seeder, 15.0b's operator run has no way to turn a pasted dossier into structured Markdown. Building and testing the tooling first also validates the dossier contract before committing to a real research pass.

## Changes

| File | Action | Description |
|---|---|---|
| `src/topics/frontmatter.py` | **NEW** | Pydantic models per file type + safe load/update/write for YAML frontmatter |
| `src/topics/bootstrap/prompt.py` | **NEW** | Builds the bootstrap deep research prompt from minimal `topic.md` fields |
| `src/topics/bootstrap/parser.py` | **NEW** | Extracts and validates the JSON block; maps records to typed structures |
| `src/topics/bootstrap/seeder.py` | **NEW** | Writes `themes/*.md` (frontmatter + prose body), `entities.json`, `timeline.json`, `hypotheses.json`, `overview.md` (rendered from intro prose + theme list + top open hypotheses); archives raw dossier under `dossiers/` |
| `tests/test_bootstrap_parser.py` | **NEW** | Fixture dossier → expected records; idempotent re-parse |

## Contract

- **Dossier format:** human-readable Markdown with a `## Theme: {kebab-id}` heading per theme **and** one trailing fenced `json` block. The parser uses both: prose sections feed theme bodies, JSON feeds metadata and reference data. Parser rejects mismatches between heading ids and JSON theme ids before any disk write.
- **Seeded theme defaults:** `origin: "bootstrap"` in frontmatter; `novelty_status: "globally_novel"` for bootstrap (literature-grounded); body = full prose section from the dossier.
- **Reference data defaults:** entities, timeline entries, and hypotheses written as flat JSON arrays at the topic root; merged by stable id on subsequent seeds.
- **Forward-only links** between files; **stable `<a id="...">` anchors** inside theme bodies for adjacent updates (see `research_briefing_architecture.md` §6, §11, §12).
- **Idempotency:** same dossier re-seeded is a no-op; second dossier merges into JSON arrays by stable id, appends only new theme files.
- **No partial writes** on failure — parser rejects invalid JSON and id mismatches before the seeder touches disk.

## Verification

- Parser rejects invalid JSON with a clear error; no partial writes on failure.
- Re-running the seeder on the same fixture dossier is a no-op (idempotent).
- A second fixture dossier merges correctly without duplicates.
