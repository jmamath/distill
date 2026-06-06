# Plan 1 — Bootstrap Tooling

**Original task id:** 15.0
**Status: passed** — 13 tests passing as of 2026-04-25. Spec: `docs/specs/15_0_bootstrap_tooling.test.md`.
**Reopened: 2026-06-06** — see "Revision — open questions become hypotheses" below. Moved back to `doing/` because the original `open_questions.json` contract is now superseded.

---

## Revision (2026-06-06) — open questions become hypotheses

**Status of this revision: pending.** Everything above shipped and passed; this section reopens the plan. Open questions are no longer a separate claim store — they are hypotheses sitting near a uniform prior. The authoritative hypothesis schema, the betting-market authoring constraint, and the `resolution_criterion` field live in **Plan 8**; this revision makes bootstrap produce that shape.

**Depends on:** Plan 8 (hypothesis schema + `resolution_criterion`) must land first.

### What changes

- `src/topics/bootstrap/seeder.py` — replace `_seed_open_questions_json` with `_seed_hypotheses_json`: write uniform-prior (`alpha = beta = 1.0`) hypothesis records to `hypotheses.json` instead of `open_questions.json`. `_seed_overview` renders its "Top Open Questions" view from low-confidence, high-priority hypotheses rather than reading a JSON file.
- `src/topics/bootstrap/parser.py` — `DossierOpenQuestion` becomes a hypothesis-shaped model carrying `statement`, an **optional** `resolution_criterion` (metric/threshold/scope/horizon), `theme_ids`, and an initial `action_posture`. The parser validates the criterion's *shape* when present; it does **not** hard-reject on its absence — resolvability is a quality property enforced by the dossier prompt and Plan 13's eval, not by a structural parse check.
- `src/topics/bootstrap/prompt.py` — the dossier prompt asks the model to emit hypotheses as *resolvable* directional bets (concrete enough that two reviewers would settle them the same way), using a resolution criterion wherever the statement isn't already unambiguous; magnitude → threshold bets, "which approach wins" → scoped binary bets (see Plan 8's authoring constraint). It no longer asks for vague open questions.
- `tests/test_bootstrap_parser.py` — fixtures carry hypotheses; assert resolution criteria parse and that a record without one is rejected.

### Migration of existing data

The current `data/research_topics/data_advantage/open_questions.json` (10 vague questions) is regenerated into hypotheses by re-running bootstrap against a fresh dossier — an LLM run plus human review, not a script. The quality of the generated bets is validated by Plan 13's hypothesis-generation eval.

---

Build the code that can parse a deep-research dossier and seed the topic wiki from it. No actual research run happens here — the goal is a working, tested pipeline ready for 15.0b to use.

**Why this matters:** Without a parser and seeder, 15.0b's operator run has no way to turn a pasted dossier into structured Markdown. Building and testing the tooling first also validates the dossier contract before committing to a real research pass.

## Changes

| File | Action | Description |
|---|---|---|
| `src/topics/frontmatter.py` | **NEW** | Pydantic models per file type + safe load/update/write for YAML frontmatter |
| `src/topics/bootstrap/prompt.py` | **NEW** | Builds the bootstrap deep research prompt from minimal `topic.md` fields |
| `src/topics/bootstrap/parser.py` | **NEW** | Extracts and validates the JSON block; maps records to typed structures |
| `src/topics/bootstrap/seeder.py` | **NEW** | Writes `themes/*.md` (frontmatter + prose body), `entities.json`, `timeline.json`, `open_questions.json`, `overview.md` (rendered from intro prose + theme list + top open questions); archives raw dossier under `dossiers/` |
| `tests/test_bootstrap_parser.py` | **NEW** | Fixture dossier → expected records; idempotent re-parse |

## Contract

- **Dossier format:** human-readable Markdown with a `## Theme: {kebab-id}` heading per theme **and** one trailing fenced `json` block. The parser uses both: prose sections feed theme bodies, JSON feeds metadata and reference data. Parser rejects mismatches between heading ids and JSON theme ids before any disk write.
- **Seeded theme defaults:** `origin: "bootstrap"` in frontmatter; `novelty_status: "globally_novel"` for bootstrap (literature-grounded); body = full prose section from the dossier.
- **Reference data defaults:** entities, timeline entries, and open questions written as flat JSON arrays at the topic root; merged by stable id on subsequent seeds.
- **Forward-only links** between files; **stable `<a id="...">` anchors** inside theme bodies for adjacent updates (see `research_briefing_architecture.md` §6, §11, §12).
- **Idempotency:** same dossier re-seeded is a no-op; second dossier merges into JSON arrays by stable id, appends only new theme files.
- **No partial writes** on failure — parser rejects invalid JSON and id mismatches before the seeder touches disk.

## Verification

- Parser rejects invalid JSON with a clear error; no partial writes on failure.
- Re-running the seeder on the same fixture dossier is a no-op (idempotent).
- A second fixture dossier merges correctly without duplicates.
