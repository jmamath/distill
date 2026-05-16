# Plan 10 — Output Generation: Daily Tweet

**Original task id:** 15.6

---

Build the `output/` package and implement the first renderer: daily tweet candidates from each day's wiki changes, included in the daily PR.

**Why this matters:** The system's purpose is to help technical decision-makers allocate attention and investment — combining fresh signals with accumulated topic memory to produce a strategically framed take, not a paper summary. The tweet is the current output format for that take; the `output/` package is designed so future formats (weekly tweet, monthly Substack post) can be added by implementing one interface, with no changes to the wiki or scoring layers.

## Changes

| File | Action | Description |
|---|---|---|
| `src/output/__init__.py` | **NEW** | Output package |
| `src/output/base.py` | **NEW** | `OutputRenderer` interface: `render(signals, wiki_state, topic_config) → OutputArtifact`; defines the contract all renderers must satisfy |
| `src/output/daily_tweet.py` | **NEW** | First renderer: generates tweet candidates from signals classified by Plan 3 (`adjacent` / `wholly_new` only); derives `strategic_significance` from current wiki state; derives `action` from audience match between `paper_audience` and `topic.md.audience`; applies `daily_tweet_limit` top-N filter; writes `tweets/{yyyy-mm-dd}.json` |
| `data/research_topics/data_advantage/tweets/` | **NEW** | Per-day tweet candidate files |
| `tests/test_output_daily_tweet.py` | **NEW** | Fixture scored signals → expected tweet JSON shape; only `adjacent` and `wholly_new` signals produce candidates; `replication` signals are skipped; idempotent on re-run |

## Output contract (`tweets/{yyyy-mm-dd}.json`)

```json
[
  {
    "id": "...",
    "text": "...",
    "theme_ids": ["..."],
    "signal_ids": ["..."],
    "status": "candidate"
  }
]
```

`status` is always `"candidate"` at generation time. The human sets it to `"approved"` or `"rejected"` in the PR review. A post-merge publish step (out of scope for this task) consumes `approved` entries.

## Generation rules

- Only signals with `classification: adjacent` or `classification: wholly_new` (written back by Plan 3) generate candidates — replication is not worth surfacing
- Daily top-N filter: at most `daily_tweet_limit` candidates per day (configurable in `topic.md`, default `1`); ranked by `applicability_score` × `source_credibility` × audience match between `paper_audience` and `topic.md.audience`
- One candidate per signal at most; the renderer may skip a signal if the underlying hypothesis update is not independently worth a tweet
- `strategic_significance` is derived at render time from current wiki state (e.g., did the signal flip a hypothesis posterior, retire an open question, or extend a high-priority theme)
- `action` text is derived from `paper_audience` × `topic.md.audience` match — phrased as a direct hook to the reader, not a generic verb
- Text must be derivable from the signal and the relevant theme — no hallucinated context
- Each candidate must address: what changed, how it fits the landscape, why it matters for the audience

## Verification

- A batch of scored signals produces a valid `tweets/{yyyy-mm-dd}.json`
- Replication-only signals produce no candidates
- Daily output is capped at `daily_tweet_limit` (default `1`)
- `action` text references audience interest derived from `paper_audience` × `topic.md.audience` match
- Re-running on the same signals is idempotent (no duplicate ids)
- A second renderer can be added under `output/` without touching `daily_tweet.py`, `wiki_updater.py`, or `scoring.py`
