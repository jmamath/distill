# Plan 18 — Duplicate Hypothesis Cleanup (Merge Pass)

**Depends on:** Plan 9 (the belief graph it operates on — `hypotheses.json` / `evidence.json` and the free-opening behaviour that creates duplicates); Plan 8 (storage load/save + merge-by-id helpers).

---

Fold hypotheses that ask the same question under different wording into one, as a periodic batch pass over the store.

**Why this matters:** Plan 9 opens a hypothesis whenever a claim names a real question and deliberately does *not* deduplicate on the way in — preventing it per claim is expensive and error-prone. So near-duplicates accumulate: "fuzzy beats exact" and "shard-local beats corpus-wide" for the same underlying bet. Left alone, one question's evidence is split across two records, so neither reaches confidence, the store looks more fragmented than the knowledge is, and a briefing can surface the same question twice while under-counting its evidence. This pass restores one-question-one-bet after the fact.

**Why its own plan, separate from Plan 9:** the belief update runs per signal, continuously as signals arrive. Consolidation only pays off once duplicates have accumulated, so it runs on its own slower cadence — periodically, or after a large backfill batch — over the whole store. Different trigger and different frequency, so it is a separate entry point that the belief loop never calls.

## What this plan does

A batch job reads `hypotheses.json`, proposes merges, confirms them, and rewrites the store — three steps, each with one decision to pin at the `doing/` boundary:

1. **Flag candidates** — find pairs of hypotheses that plausibly ask the same question. *To pin:* the candidate signal; embedding similarity over `statement` is the leading option, narrowed by shared `theme_ids` (and matching `comparison` subjects for comparative bets).
2. **Confirm the merge** — for each candidate pair, judge whether they really are one question. This is the pass's single model call; its prompt / model + fallback / parse contract is this plan's model-judgment surface, to pin at `doing/`.
3. **Consolidate** — fold the confirmed duplicate into the survivor: repoint its `evidence.json` rows, combine the Beta evidence (both bets began from the same uniform prior, so the survivor accumulates the union — exact combination pinned at `doing/`), and retire the absorbed record.

## Safety rules (invariants)

- **Never merge disagreement.** Two hypotheses with the same subjects but opposite findings ("A beats B" vs "B beats A") are real conflict, not duplication — never merged.
- **Every merge is reversible.** The absorbed hypothesis is retired (status → `superseded`) with a pointer to the survivor, never deleted, so a merge can be undone.
- **Idempotent.** Re-running the pass with no new duplicates changes nothing.

## Changes (indicative — pinned at `doing/`)

| File | Action | Description |
|---|---|---|
| `src/topics/hypothesis_merge.py` | **NEW** | The batch merge pass: flag → confirm → consolidate over `hypotheses.json` / `evidence.json`, via Plan 8 storage helpers |
| `tests/test_hypothesis_merge.py` | **NEW** | Duplicates fold into one; disagreeing pairs are never merged; a merge is reversible; the pass is idempotent |

## Verification

- Two hypotheses for the same question collapse to one, and the survivor carries the union of their evidence (mass and provenance).
- A same-subjects / opposite-finding pair is left untouched.
- A merge can be undone from what the pass records.
- Running the pass twice in a row is a no-op the second time.
