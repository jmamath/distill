# Plan 5 — Pass-1: Topic Relevance Filter

**Original task id:** 15.3a
**Depends on:** Plan 4 source adapter contract (provides `NormalizedItem`).
**Status: passed** — 10 tests passing as of 2026-04-28. Spec: `docs/specs/15_3a_pass1_topic_relevance_filter.test.md`.

---

Reuse the goal-engine filtering pattern as a fast, abstract-only relevance gate. Every `NormalizedItem` is scored against the topic thesis and taxonomy subtopics using only its `summary` field. Items that do not clear the threshold are discarded here — no full-text fetch, no disk write.

**Why this matters:** Fetching and scoring full-text for every ingested item would be expensive and slow. A cheap abstract-level gate keeps the costly pass-2 work proportional to what is actually relevant. The pattern (numeric score 0–10, model + fallback chain, threshold gate) is replicated from Sonaryn's goal engine — research_briefing owns its own config with no import dependency on the main codebase.

## Changes

| File | Action | Description |
|---|---|---|
| `src/config.py` | **NEW** | `GEMINI_API_KEY`, `SCORING_MODEL` (default `gemini-3.1-flash-lite-preview`), `SCORING_FALLBACK_MODEL` (default `gemini-2.5-flash-lite`), `SCORING_THRESHOLD` (default `6`); all overridable via env vars |
| `src/topics/models.py` | **NEW** | `AbstractScore` Pydantic model: `relevance: int` (0–10), `reason: str` |
| `src/topics/prompts.py` | **NEW** | `build_pass1_prompt(item: NormalizedItem, topic_config: TopicConfig) → str`; includes topic thesis, `scope_in`/`scope_out` lists, and taxonomy subtopics from `topic.md` frontmatter; item `summary` only |
| `src/topics/scoring.py` | **NEW** | `pass1_filter(items, topic_config) → list[tuple[NormalizedItem, AbstractScore]]`; one LLM call per item via `SCORING_MODEL` (with `SCORING_FALLBACK_MODEL` on failure); drops items where `relevance < SCORING_THRESHOLD`; returns `(item, score)` pairs so pass-2 has the pass-1 context available |
| `tests/test_topic_scoring_pass1.py` | **NEW** | 10 tests; Gemini client mocked (no API key required); covers threshold boundary, mixed batch, empty input, scoring failure, prompt content, and multi-item ordering |

## Pass-1 mechanics

- Model: `SCORING_MODEL` with `SCORING_FALLBACK_MODEL` on failure; one retry per model before falling back
- Threshold: `SCORING_THRESHOLD` (default `6`, inclusive — items at exactly 6 are kept)
- Prompt context: topic thesis + `scope_in`/`scope_out` + taxonomy subtopics; item `summary` only — no full text
- LLM response schema: `{"relevance": int, "reason": str}`; structured output enforced via Gemini `response_mime_type`
- Items that fail on all models are dropped silently (logged at ERROR); items below threshold are dropped (logged at INFO)
- No disk writes; return type is `list[tuple[NormalizedItem, AbstractScore]]` — pass-2 receives both the item and the pass-1 verdict

## Verification

- Items with off-topic abstracts (e.g. no data-domain focus for `data_advantage`) are dropped and produce no downstream output
- Items with on-topic abstracts are returned with a populated `AbstractScore`
- The filter can run on a list of mixed items and return only the relevant subset
- An empty input returns `[]` without calling the Gemini API
