# Plan 10 — Output Generation: Daily Tweet

**Original task id:** 15.6

**Depends on:** Plan 9 (current belief state), Plan 17 (theme novelty and growth), and Plan 19 (source-grounded finding contract).

---

Build the `output/` package and implement the first renderer: daily tweet candidates from each day's wiki changes, included in the daily PR.

**Why this matters:** The system's purpose is to help technical decision-makers allocate attention and investment — combining fresh signals with accumulated topic memory to produce a strategically framed take, not a paper summary. The tweet is the current output format for that take; the `output/` package is designed so future formats (weekly tweet, monthly Substack post) can be added by implementing one interface, with no changes to the wiki or scoring layers.

## Contextual assessment belongs here, not in pass-2

Plan 19 makes pass-2 a source-grounded finding extractor and deliberately removes `applicability_score`, `strategic_significance`, `paper_audience`, and `temporal_freshness` from durable signals. This plan owns those interpretations because an output is where the current graph, current audience, and current time finally meet.

```mermaid
flowchart LR
    finding[("Plan 19 finding<br/>statement + source support")]:::data
    graph[("Current graph<br/>beliefs + evidence + themes")]:::data
    audience[("Audience profile<br/>current time")]:::data
    assess{{"Per-finding assessment<br/>applicability · significance<br/>audience fit · recency"}}:::llm
    rank["Rank and select"]:::det
    render["Render output artifact"]:::det

    finding --> assess
    graph --> assess
    audience --> assess
    assess --> rank --> render

    classDef llm fill:#fdeecf,stroke:#b9821f,color:#5c3d00;
    classDef det fill:#d9f2e6,stroke:#1a7f52,color:#0b3d26;
    classDef data fill:#eeeeec,stroke:#9a9a96,color:#333333;
```

Assessments are made **per finding**, not once per paper:

- **Applicability** asks how practical and actionable the finding is for this audience under the conditions the source demonstrated.
- **Strategic significance** asks how much the finding changes the current landscape—for example, contradicting a strong belief, resolving an important uncertainty, or adding credible evidence where the graph is thin.
- **Audience fit and action** ask whether this reader should ignore, monitor, prototype, or invest based on the finding and current graph—not based on a stored `paper_audience` label.
- **Recency** is calculated from `published_at` when rendering, so it changes with time rather than going stale in signal frontmatter.

These judgments rank and frame outputs only. They never gate extraction, remove findings from the graph, or increase Beta evidence weight: importance is not truth. The canonical finding remains unchanged when its assessment changes.

The simplest implementation is to assess during rendering from an explicit graph and audience snapshot. Caching is deferred until measured runtime cost justifies it. The exact prompt/model/validation contract, ranking rollup, and audit fields are pinned when this plan moves to `doing`; every generated artifact must retain enough rationale and input provenance to explain its ranking at that time.

## Changes

| File | Action | Description |
|---|---|---|
| `src/output/__init__.py` | **NEW** | Output package |
| `src/output/base.py` | **NEW** | `OutputRenderer` interface: `render(signals, wiki_state, topic_config) → OutputArtifact`; defines the contract all renderers must satisfy |
| `src/output/daily_tweet.py` | **NEW** | First renderer: assesses Plan 9 graph objects and Plan 17 narrative outcomes against the current audience, selects `adjacent` / `wholly_new` candidates, and writes `tweets/{yyyy-mm-dd}.json` |
| `data/research_topics/data_advantage/tweets/` | **NEW** | Per-day tweet candidate files |
| `tests/test_output_daily_tweet.py` | **NEW** | Fixture findings + graph/audience snapshots → expected tweet JSON shape and contextual rankings; replication-only signals are skipped; idempotent on re-run |
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

- Only Plan 17 outcomes classified `adjacent` or `wholly_new` generate candidates — replication remains valuable graph evidence but is not worth surfacing
- Daily top-N filter: at most `daily_tweet_limit` candidates per day (configurable in `topic.md`, default `1`); ranked from the current per-finding applicability, strategic significance, audience fit, recency, and source credibility (exact rollup pinned at `doing`)
- One candidate per source signal at most; the renderer rolls up its graph/renderer outcomes and may skip it when no update is independently worth surfacing
- A mixed paper is judged per finding; its best output-worthy finding may represent the signal, while routine findings do not inherit its score
- `strategic_significance` is derived at render time from current graph state (e.g., did the finding flip a hypothesis posterior, retire an open question, or extend a high-priority theme)
- `action` text is derived from the finding + graph + target audience — phrased as a direct hook to the reader, not a generic verb
- Text must be derivable from the source-grounded finding and relevant graph/theme context — no hallucinated support
- Each candidate must address: what changed, how it fits the landscape, why it matters for the audience

### Audience actionability axis

The `action` field in each tweet candidate is the operational form of the **audience actionability** judgment: it answers "can this audience take a concrete action from this finding, given what the graph currently knows?" The four actions from `topic.md`'s `action_vocabulary` (ignore, monitor, prototype, invest) map directly to the phrasing of the tweet's call-to-action. `ignore` findings are filtered out before candidate generation. The choice is derived at render time and can change when the graph or audience changes; it is never stored as a property of the source.

**Hypothesis `action_posture`** is derived the same way — at read time — but from the *belief*, not audience match (handoff from Plan 9 §4): a confidence→label rule maps a bet's `alpha`/`beta` posterior onto the same `action_vocabulary` (crossing a high-confidence band moves `monitor` → `prototype`/`invest`). It is not stored — Plan 9's §4 never writes it — and the exact confidence bands are pinned at this plan's `doing/` boundary. This is distinct from the tweet's `action` above: posture reflects how strongly a bet is held; the tweet action reflects whether a given reader should act on a signal.

## Overview retirement (2026-07-05)

`overview.md` was the topic's stored landing page — themes plus top open hypotheses. It held no information of its own: both halves copied stores that already exist (`themes/`, `hypotheses.json`), which is why it was the one file left without an owner after the Plan 9 / Plan 17 split — a stored derived view needs someone to re-render it whenever either source moves. It is retired instead of assigned.

The rule it follows already exists in Plan 9: derived views are composed at read time, not stored (the same reason no global comparative ranking is stored). This plan is where the composition lives, because renderers already read current wiki state at render time — `strategic_significance` is derived exactly this way. "Themes + top open hypotheses" is one more read-time view; if a durable landing artifact is ever wanted, a renderer can emit a dated one, which nobody expects to self-update.

The seeder change and file deletion are recorded here, not in Plans 1/3, because done plans stay closed. `AGENTS.md`'s structure listing drops the `overview.md` line when this ships. Plan 9 §2 and Plan 15's verification now point here.

## Verification

- A batch of findings plus a graph/audience snapshot produces a valid `tweets/{yyyy-mm-dd}.json`
- Replication-only signals produce no candidates
- Daily output is capped at `daily_tweet_limit` (default `1`)
- The same finding can receive a different ranking and action when the graph or audience changes, without changing the stored finding
- `action` text references the finding, current graph context, and target audience rather than a stored `paper_audience`
- Contextual scores affect output priority but never change evidence weight or remove a finding from the graph
- Re-running on the same signals is idempotent (no duplicate ids)
- A second renderer can be added under `output/` without touching `daily_tweet.py`, `wiki_updater.py`, or `scoring.py`
- `overview.md` is gone: bootstrap no longer writes it, the live topic no longer contains it, and the landing view is derivable at read time from `themes/` + `hypotheses.json`
