# Plan 2 — Topic Configuration Contract

**Original task id:** 15.1
**Depends on:** Plan 1 (bootstrap tooling) must be complete and tests passing.
**Status: passed** — 11 tests passing as of 2026-04-21. Spec: `docs/specs/15_1_topic_config.test.md`.

---

Define the first-class configuration model for a reusable research topic.

**Why this matters:** The system must support topic shifts every 1-3 months without rewriting orchestration code. If topic definitions remain implicit in prompts or scattered config, the first implementation will hard-code the initial topic and make future pivots expensive.

## Changes

| File | Action | Description |
|---|---|---|
| `research_briefing/docs/data_advantage_brief.md` | **REF** | Use as the first topic/business context input |
| `research_briefing/docs/research_briefing_architecture.md` | **REF** | Use as the target system design |
| `src/config.py` | **DELETE** | Flat stub (6 lines); replaced by the `topics/` package (avoids name collision with `topics/config.py`'s role) |
| `src/pipeline.py` | **DELETE** | Flat stub (6 lines); orchestration will live alongside the topic modules once the real pipeline lands |
| `src/topics/config.py` | **NEW** | Topic config schema, validation helpers, and shared contracts |
| `data/research_topics/README.md` | **NEW** | File layout and topic lifecycle notes |
| `data/research_topics/data_advantage/topic.md` | **UPDATE** | Extends minimal `topic.md` from Plan 1 with full validated config (frontmatter) |
| `data/audiences/technical_decision_makers.md` | **NEW** | First audience profile referenced by `topic.md.audience_ref` (persona, scope, tone) |
| `tests/test_topic_config.py` | **NEW** | Schema validates the first topic; rejects missing required fields with clear errors |

## Contract must define

- topic id and thesis
- target audience profile
- separate time horizons: `bootstrap_horizon` (historical depth for deep-research prompt) and `signal_horizon` (recency window for live ingestion)
- included and excluded signal classes
- source priorities
- taxonomy / subtopics
- scoring dimensions
- action vocabulary (`ignore`, `monitor`, `prototype`, `invest`, etc.)

## Verification

- A topic can be represented without touching orchestration code
- The first topic config is valid against the schema
- The contract is generic enough to support a different topic later
