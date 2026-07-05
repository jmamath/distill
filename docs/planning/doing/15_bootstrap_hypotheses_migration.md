# Plan 15 — Migrate Live Open Questions To Hypotheses

**Continues:** Plan 1 (Bootstrap Tooling, now in `done/`).
**Depends on:** Plan 8 (authoritative hypothesis schema + `resolution_criterion`).

---

Replace the legacy `open_questions.json` data in the live `data_advantage` topic with uniform-prior hypotheses in `hypotheses.json`, so the topic store reflects the current "open questions are hypotheses" model.

**Why this matters:** The bootstrap *code* already produces hypotheses — the seeder, parser, and dossier prompt no longer reference open questions, and the tests assert `open_questions.json` is never written. But the live topic on disk still carries the old `open_questions.json` (10 vague questions) from before that change. Until it is migrated, the running system disagrees with its own code and schema: a reader sees a store that the pipeline can no longer produce or update.

## What remains

This is an **operator task, not a code change.** The 10 questions in `data/research_topics/data_advantage/open_questions.json` are vague by design and cannot be mechanically rewritten into resolvable bets — that requires research judgment. The migration is therefore a fresh bootstrap pass plus human review:

1. Re-run the bootstrap dossier prompt for the `data_advantage` topic (an LLM deep-research run).
2. The dossier emits hypotheses as resolvable directional bets (per Plan 8's authoring constraint), with a `resolution_criterion` wherever the statement is not already unambiguous.
3. Run the seeder to write uniform-prior (`alpha = beta = 1.0`) hypothesis records into `hypotheses.json`.
4. Human review of the generated bets: each must be resolvable — two reviewers could independently settle it the same way.
5. Delete the now-stale `data/research_topics/data_advantage/open_questions.json`.

The quality of the generated bets is validated by Plan 13's hypothesis-generation eval (separate plan).

## Verification

- `data/research_topics/data_advantage/open_questions.json` no longer exists.
- `hypotheses.json` is populated with resolvable, uniform-prior hypotheses covering the strategic questions the topic tracks.
- An "open question" surfaces only as a low-evidence hypothesis in `hypotheses.json` — no separate question store anywhere. (`overview.md` is retired; Plan 10 composes the "top open hypotheses" view at read time.)
