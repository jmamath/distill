# Plan 16 — Remove `new_open_questions` From The Pass-2 Signal Schema

**Continues:** Plan 7 (Pass-2 Scoring Pipeline, in `done/`).
**Status: passed** — shipped and verified; `new_open_questions` is absent from `src/` and the test suite asserts the new shape.
**Built against:** the hypothesis/evidence schema (now documented authoritatively in Plan 8). That schema was already stable in code when this shipped, so there is no live dependency — this plan is complete.

---

Drop the `new_open_questions` field from the pass-2 signal schema. Open questions are no longer a separate claim type — they are hypotheses sitting near a uniform prior — so a scored signal has no reason to emit free-text questions.

**Why this matters:** The signal schema is a shared contract between scoring, storage, the wiki update loop, and output generation. Carrying a field that the rest of the system no longer recognises invites drift and dead code. Removing it keeps the signal aligned with the belief-graph model: a signal contributes *evidence*, and the synthesis of a new resolvable hypothesis from unmatched evidence is owned downstream (Plan 9), where the current hypothesis store is in scope.

## What shipped

- `src/topics/models.py` — removed `new_open_questions` and the `OpenQuestion` model from `Pass2Score`; the signal carries `new_evidences` only.
- `src/topics/prompts.py` — dropped the `new_open_questions` instruction from `build_pass2_prompt`.
- `src/topics/scoring.py` — signal frontmatter no longer includes `new_open_questions`.
- `tests/test_pass2_schema.py`, `tests/test_topic_scoring_pass2.py` — assertions updated to the new shape.

## The evidence → hypothesis boundary

When a signal surfaces something the store has no hypothesis for, it emits `new_evidences` only. Plan 9 (`hypothesis_updater`) owns synthesising a new resolvable hypothesis from unmatched evidence, because that step needs access to the current hypothesis store rather than just the signal text. This boundary is diagrammed in `docs/diagrams/evidence_to_hypothesis_boundary.md`.

## Verification

- No references to `new_open_questions` or `OpenQuestion` remain anywhere in `src/`.
- `Pass2Score` parses and round-trips without the field; written signal frontmatter omits it.
- The pass-2 test suite passes with the new-shape assertions.
