# Plan 7 — Pass-2 Scoring Pipeline

**Original task ids:** 15.3b-ii (Full-Text Adapter Extension), 15.3b-iii (Pass-2 Prompt And Signal Schema), 15.3b-iv (Pass-2 Orchestration And Signal Writing)
**Depends on:** Plan 4 source adapter contract; Plan 3 seeded `themes/`; Plan 6 credibility functions.

---

Three tightly sequential sub-tasks that together deliver one complete deliverable: turn a pass-1-filtered `NormalizedItem` into a written signal file on disk. They are kept in one plan because each feeds directly into the next with no other consumers in between.

**Why this matters:** Reading the source is the most expensive step in the pipeline. Once read, every downstream judgment — theme placement, evidence integration, briefing copy — draws from the same shared context captured in the signal file. Gating the full-text fetch behind pass-1 keeps this cost proportional to genuinely relevant items.

---

## Sub-task A — Full-Text Adapter Extension

**Status: passed** — 27 tests passing as of 2026-05-16.

**Depends on:** Plan 4 source adapter contract. Self-contained extension with no dependency on scoring or credibility.

### Changes

| File | Action | Description |
|---|---|---|
| `src/sources/base.py` | **UPDATE** | Add `fetch_full_text(url: str) → bytes` abstract method and `full_text_mime_type: str` class attribute to `SourceAdapter`; add `full_text_fetched: bool` (default `False`) to `NormalizedItem` |
| `src/sources/arxiv.py` | **UPDATE** | Set `full_text_mime_type = "application/pdf"`; implement `fetch_full_text`: fetches the PDF for the arXiv id extracted from the item URL; returns raw PDF bytes |
| `src/sources/lab_blog.py` | **UPDATE** | Set `full_text_mime_type = "text/plain"`; implement `fetch_full_text`: fetches the article HTML at the item URL, strips tags via `_strip_html`, and returns UTF-8 encoded plain text bytes |
| `tests/fixtures/arxiv_paper.pdf` | **NEW** | One real arXiv PDF fetched and stored as a fixture for offline tests |
| `tests/fixtures/lab_blog_article.html` | **NEW** | One real blog article HTML fetched and stored as a fixture for offline tests |
| `tests/test_source_adapters.py` | **UPDATE** | Add `fetch_full_text` fixture-backed tests for both adapters |
| `scripts/smoke_full_text.py` | **NEW** | Operator smoke script: loads the two fixtures, sends each to the `google.genai` API with the correct `full_text_mime_type`, prompts for a summary, and prints the response |

### Verification

- `ArxivAdapter.fetch_full_text` returns raw PDF bytes (`%PDF` header present)
- `LabBlogAdapter.fetch_full_text` returns HTML-stripped UTF-8 plain text bytes (no `<` characters)
- `full_text_mime_type` is `"application/pdf"` for arXiv and `"text/plain"` for lab_blog
- A failed fetch raises a clear exception (not swallowed)
- `full_text_fetched` defaults `False` on `NormalizedItem` construction
- Operator runs `scripts/smoke_full_text.py --model <model>` and confirms both summaries are coherent

---

## Sub-task B — Pass-2 Prompt And Signal Schema

**Status: passed** — 95 tests passing as of 2026-05-21.

**Depends on:** Sub-task A; Plan 5 (`Pass1Score`, `NormalizedItem`); Plan 2 (`TopicConfig`, theme definitions); Plan 6 (credibility and freshness field definitions).

Defines the `Pass2Score` model and the pass-2 prompt contract. Fixes the schema that sub-task C, Plan 2 (storage), Plan 3 (knowledge update), and Plan 4 (output) all depend on.

**Why this matters:** The signal schema is a shared contract between scoring, storage, wiki update, and output generation. Settling it before those layers are built avoids cascading schema migrations later.

### Changes

| File | Action | Description |
|---|---|---|
| `src/topics/models.py` | **UPDATE** | Add `CandidateTheme` model (`theme_id: str`, `confidence: int`, `rationale: str`); add `Pass2Score` Pydantic model; add `signal_id` generation helper |
| `src/topics/prompts.py` | **UPDATE** | Add `build_pass2_prompt(item: NormalizedItem, topic_config: TopicConfig, theme_definitions: dict[str, str]) → str`; provides theme definitions only (no bodies, no existing questions, no existing evidences) |
| `tests/test_pass2_schema.py` | **NEW** | `Pass2Score` roundtrips through JSON; `signal_id` is deterministic for the same URL; `CandidateTheme` requires `rationale`; prompt includes theme definitions and excludes theme bodies and existing evidences |

### `Pass2Score` schema

```yaml
applicability_score: int           # 0–10
applicability_rationale: str       # one sentence: why this applicability score
strategic_significance: int        # 0–10
strategic_significance_rationale: str  # one sentence: why this strategic significance score
paper_audience: str                # free text
candidate_themes:                  # up to 3, sorted desc by confidence
  - theme_id: str
    confidence: int                # 0–10
    rationale: str                 # one sentence: why this confidence level
new_open_questions:
  - text: str
new_evidences:
  - claim: str
    stance: str                    # for | against | mixed | neutral
affiliations: [str]                # author organizations as cited in the source
rationale: str                     # markdown body, written to the signal body (not frontmatter)
```

### `signal_id` generation

```
{source_id}_{published_date}_{sha256(url)[:10]}
```

Example: `arxiv_2026-04-29_a3f7b2c1de`. Deterministic: same URL always produces the same `signal_id` and the same file path.

### Signal file format (`signals/{yyyy}/{mm}/{dd}/{signal_id}.md`)

```yaml
---
signal_id: "arxiv_2026-04-29_a3f7b2c1de"
source_id: "arxiv"
source_type: "research_paper"
url: "https://arxiv.org/abs/2404.01234"
published_at: "2026-04-29T00:00:00Z"
title: "..."
authors: ["Author A", "Author B"]
affiliations: ["MIT", "Google DeepMind"]
ingested_at: "2026-04-29T14:23:11Z"
full_text_fetched: true
applicability_score: 8
applicability_rationale: "Directly advances the synthetic data theme with a novel self-play loop."
strategic_significance: 7
strategic_significance_rationale: "Could shift best practice for instruction-tuning data at scale."
paper_audience: "industry practitioners building post-training pipelines"
source_credibility: 9
temporal_freshness: 9
candidate_themes:
  - theme_id: "synthetic-data-generation"
    confidence: 9
    rationale: "Core contribution is a scalable synthetic pipeline directly implementing this theme."
new_open_questions:
  - text: "How does this approach scale beyond 70B parameters?"
new_evidences:
  - claim: "Synthetic data generated by … achieves parity with human-curated data on benchmark X."
    stance: "for"
---

## Rationale

[Markdown body from the model.]
```

### Verification

- `Pass2Score` parses from a JSON string without error
- `signal_id` is identical for two calls with the same URL
- Prompt includes theme definitions but not theme bodies or existing evidences
- `candidate_themes` entries each carry a `rationale` field

---

## Sub-task C — Pass-2 Orchestration And Signal Writing

**Status: passed** — 115 tests passing as of 2026-05-21.

**Depends on:** Sub-tasks A and B; Plan 3 seeded `themes/`; Plan 6 `credibility.py` and `source_credibility.json`.

Wire together full-text fetch, LLM scoring, deterministic credibility and freshness, and signal file writing into the `pass2_score` function.

### Changes

| File | Action | Description |
|---|---|---|
| `src/topics/scoring.py` | **UPDATE** | Add `load_theme_definitions(themes_dir: Path) → dict[str, str]` helper; add `pass2_score(items: list[tuple[NormalizedItem, Pass1Score]], topic_config: TopicConfig, topic_dir: Path, adapter: SourceAdapter) → list[Path]`; fetches full text, scores via LLM, computes credibility and freshness deterministically, writes signal files |
| `tests/test_topic_scoring_pass2.py` | **NEW** | Fixture pass-1 items → written signal files; verify schema; verify `full_text_fetched: true`; verify idempotency on re-run; verify `fetch_full_text` failure drops the item; verify credibility and freshness values in written frontmatter |

### Theme definitions loader

`load_theme_definitions(themes_dir: Path) → dict[str, str]`

Reads every `*.md` file in `themes_dir`, parses its frontmatter via `ThemeFrontmatter`, and returns `{theme_id: description}`. This dict is passed as-is to `build_pass2_prompt` — descriptions only, no bodies. Called once per `pass2_score` invocation before the per-item loop.

### Pass-2 mechanics

For each item passed in from pass-1:

1. Call `adapter.fetch_full_text(item.url)` → capture returned bytes; set `item.full_text_fetched = True`. If the fetch fails, drop the item — no disk write, failure logged.
2. Build the prompt via `build_pass2_prompt`, passing theme definitions (not bodies).
3. Call `SCORING_MODEL` (with `SCORING_FALLBACK_MODEL` on failure) passing the bytes with `adapter.full_text_mime_type`. Parse the response as `Pass2Score`.
4. Compute `source_credibility` via `credibility.compute_source_credibility`.
5. Compute `temporal_freshness` via `credibility.compute_temporal_freshness` (fixed 365-day window).
6. Write signal file to `signals/{yyyy}/{mm}/{dd}/{signal_id}.md`. If the file already exists (same `signal_id`), skip — idempotent.

### Verification

- A `fetch_full_text` failure drops the item silently — no partial signal file is written
- Every written signal file has `full_text_fetched: true` in frontmatter
- Re-running on the same items is a no-op (same `signal_id` → same path → file already exists)
- `candidate_themes` contains at most three entries, sorted by descending confidence, each with a `rationale`
- `source_credibility` is `null` when no affiliations match the table
- `temporal_freshness` reflects a 365-day linear decay — not the topic `signal_horizon`
- A batch of pass-1 items can be scored end-to-end and produce valid signal files
