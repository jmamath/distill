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
| `src/output/daily_tweet.py` | **NEW** | First renderer: generates tweet candidates from signals classified by Plan 17 (`adjacent` / `wholly_new` only); derives `strategic_significance` from current wiki state; derives `action` from audience match between `paper_audience` and `topic.md.audience`; applies `daily_tweet_limit` top-N filter; writes `tweets/{yyyy-mm-dd}.json` |
| `data/research_topics/data_advantage/tweets/` | **NEW** | Per-day tweet candidate files |
| `tests/test_output_daily_tweet.py` | **NEW** | Fixture scored signals → expected tweet JSON shape; only `adjacent` and `wholly_new` signals produce candidates; `replication` signals are skipped; idempotent on re-run |
| `src/topics/bootstrap/seeder.py` | **UPDATE** | Stops seeding `overview.md` — retired stored view; see "Overview retirement" below |
| `data/research_topics/data_advantage/overview.md` | **DELETE** | Retired; the landing view becomes a read-time composition over `themes/` + `hypotheses.json` |

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

- Only signals with `classification: adjacent` or `classification: wholly_new` (written back by Plan 17) generate candidates — replication is not worth surfacing
- Daily top-N filter: at most `daily_tweet_limit` candidates per day (configurable in `topic.md`, default `1`); ranked by `applicability_score` × `source_credibility` × audience match between `paper_audience` and `topic.md.audience`
- One candidate per signal at most; the renderer may skip a signal if the underlying hypothesis update is not independently worth a tweet
- `strategic_significance` is derived at render time from current wiki state (e.g., did the signal flip a hypothesis posterior, retire an open question, or extend a high-priority theme)
- `action` text is derived from `paper_audience` × `topic.md.audience` match — phrased as a direct hook to the reader, not a generic verb
- Text must be derivable from the signal and the relevant theme — no hallucinated context
- Each candidate must address: what changed, how it fits the landscape, why it matters for the audience

### Audience actionability axis

The `action` field in each tweet candidate is the operational form of the **audience actionability** scoring concept: it answers "can a technical decision-maker take a concrete action based on this signal?" The four actions from `topic.md`'s `action_vocabulary` (ignore, monitor, prototype, invest) map directly to the phrasing of the tweet's call-to-action. `ignore` signals are filtered out before candidate generation. The choice of action is derived at render time from `paper_audience` × `topic.md.audience` match — not stored in the signal file — so it can be re-derived if the audience profile changes.

## Overview retirement (2026-07-05)

`overview.md` was the topic's stored landing page — themes plus top open hypotheses. It held no information of its own: both halves copied stores that already exist (`themes/`, `hypotheses.json`), which is why it was the one file left without an owner after the Plan 9 / Plan 17 split — a stored derived view needs someone to re-render it whenever either source moves. It is retired instead of assigned.

The rule it follows already exists in Plan 9: derived views are composed at read time, not stored (the same reason no global comparative ranking is stored). This plan is where the composition lives, because renderers already read current wiki state at render time — `strategic_significance` is derived exactly this way. "Themes + top open hypotheses" is one more read-time view; if a durable landing artifact is ever wanted, a renderer can emit a dated one, which nobody expects to self-update.

The seeder change and file deletion are recorded here, not in Plans 1/3, because done plans stay closed. `AGENTS.md`'s structure listing drops the `overview.md` line when this ships. Plan 9 §2 and Plan 15's verification now point here.

## Verification

- A batch of scored signals produces a valid `tweets/{yyyy-mm-dd}.json`
- Replication-only signals produce no candidates
- Daily output is capped at `daily_tweet_limit` (default `1`)
- `action` text references audience interest derived from `paper_audience` × `topic.md.audience` match
- Re-running on the same signals is idempotent (no duplicate ids)
- A second renderer can be added under `output/` without touching `daily_tweet.py`, `wiki_updater.py`, or `scoring.py`
- `overview.md` is gone: bootstrap no longer writes it, the live topic no longer contains it, and the landing view is derivable at read time from `themes/` + `hypotheses.json`
