# Plan 12 — First End-To-End Slice: Data Advantage

**Original task id:** 15.8
**Assumes:** Plan 3 has seeded `data_advantage`; Plans 19 → 9 → 17 → 10 provide the extraction, graph, rendering, and output sequence.

---

Deliver the first narrow topic slice using the new architecture. This is the proving ground for everything built in Plans 1–5.

**Why this matters:** The architecture only matters if it can produce one real topic output end-to-end. "Data advantage" is the first proving ground, not the permanent hard-coded direction.

## Changes

| File | Action | Description |
|---|---|---|
| `data/research_topics/data_advantage/` | **UPDATE** | First live topic workspace; seeded by bootstrap, extended by Plans 1–5 |
| `docs/specs/15_8_end_to_end.test.md` | **NEW** | Human-first validation test for the first topic slice |
| `tests/test_research_topic_pipeline.py` | **NEW** | Focused automated test for config → normalize → extract experimental findings → update graph → render wiki → generate output, including a zero-finding non-experimental source |

## End-to-end slice must prove

- one topic config works
- at least two source classes ingest successfully, with eligibility determined by experimental content rather than source format
- complete pass-2 experimental findings become durable graph outcomes before any wiki rendering
- a non-experimental source is preserved with zero findings and causes no graph or wiki mutation
- wiki state updates across runs
- tweet candidates are generated and included in the daily PR

## Verification

- One end-to-end run completes locally from topic config to tweet candidates
- The topic can be changed by swapping config and taxonomy files, not rewriting orchestration
- The resulting output is useful enough to review and publish
