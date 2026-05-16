# Plan 6 — Source Credibility And Temporal Freshness

**Original task id:** 15.3b-i
**Depends on:** Plan 4 (`NormalizedItem.affiliations`).
**Status: passed** — 16 tests passing as of 2026-05-14. Raw ranking data gitignored under `data/credibility/`; regeneration script in `data/credibility/README.md`.

---

Define and implement the two deterministic scoring functions used downstream by pass-2 orchestration. Both are pure computations — no LLM call, no disk write beyond the operator-seeded JSON table.

**Why this matters:** Credibility and freshness need to be settled before the signal schema is designed so the schema can reference them as first-class fields with a clear derivation. Seeding the institution table is also an operator task that cannot be automated — the right credibility proxy depends on the topic. Separating these pure functions from the LLM pass means they can be updated or recomputed without re-running the expensive model step.

## Changes

| File | Action | Description |
|---|---|---|
| `data/research_topics/data_advantage/source_credibility.json` | **NEW** | Topic-scoped institution weight table on a 0–10 log scale; seeded from ICLR 2026 fractional affiliation rankings (2050 institutions) |
| `data/iclr2026_institutions_ranked_fractional.csv` | **NEW** | Source data: ICLR 2026 accepted papers with fractional institution counts (1/N credit per paper); used to derive `source_credibility.json` |
| `src/topics/credibility.py` | **NEW** | `compute_source_credibility(affiliations: list[str], table: dict) → float | None`: averages weights of matched institutions; unmatched excluded; zero matches → `None`. `compute_temporal_freshness(published_at: datetime) → int`: 0–10 linear decay over a fixed 365-day window, independent of `signal_horizon` |
| `tests/test_credibility.py` | **NEW** | Credibility: matched orgs averaged, unmatched excluded, all unmatched → `None`, empty affiliations → `None`. Freshness: today → 10, 180 days → 5, 365 days → 0, beyond 365 → 0 |

## Source credibility table

Topic-scoped — the proxy depends on the topic, so the table travels with the topic rather than living globally. Seeded from ICLR 2026 fractional rankings using a log scale: `max(1, round(10 * log(count+1) / log(max_count+1)))`. Pivoting to a different topic means swapping the table. The table is static and editable; updating weights does not require re-running pass-2 since `affiliations` is preserved on the signal.

## Temporal freshness

Uses a fixed 365-day reference window, deliberately decoupled from `signal_horizon`. `signal_horizon` is an ingestion filter — it controls what enters the pipeline. Freshness scoring is separate: a paper just past the ingestion window should not hard-floor to 0; it should still carry a low but meaningful score.

```
score = max(0, round(10 * (1 - age_days / 365)))
```

At 36 days → 9, at 180 days → 5, at 365 days → 0. No cliff, no dependency on topic config. In pass-2 ranking, `temporal_freshness` is a **tiebreaker/modifier**, not a primary axis — `applicability_score × source_credibility` drives the rank; freshness breaks ties among otherwise comparable signals.

## Verification

- Matched institutions are averaged; unmatched are excluded from the mean
- Zero matched institutions → `None` (not `0`)
- An item published today scores 10; at 180 days scores 5; at or beyond 365 days scores 0
- Both functions are importable and testable with no external dependencies
