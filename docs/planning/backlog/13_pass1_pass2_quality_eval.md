# Plan 13 — Pass-1 and Pass-2 Quality Evaluation

**Depends on:** Plan 5 (pass-1 relevance filter), Plan 7 (pass-2 scoring pipeline), Plan 8 (hypothesis schema), Plan 1 revision (bootstrap emits hypotheses).

---

The scoring pipeline now runs end-to-end, but we have no way to tell whether a
change to a prompt or a model upgrade actually improved output quality — unit
tests check shape, not judgment. This plan introduces a small, repeatable
evaluation set so the team can A/B prompts and models against a fixed yardstick.

**Why this matters:** Every future prompt edit and model swap will silently
shift scoring behavior. Without a golden set, regressions land unnoticed and
"improvement" is anecdotal. A small eval set, runnable in a single command,
turns prompt iteration from guesswork into a measurable loop.

**Core architectural choice — predictions are generated once, evaluated many
times:**

```
golden labels   ─┐
                 ├──▶ eval-pass1 ─▶ report
predictions  ────┤
(one run dir)    ├──▶ eval-pass2-extraction ─▶ report
                 └──▶ eval-pass2-scoring    ─▶ report
```

Generating predictions is the expensive step (full-text fetches + minutes of
LLM calls per paper). Evaluating predictions is cheap (mostly deterministic
comparison). Coupling them would mean re-running pass-1 and pass-2 every time
we tweak a grading rule, and would prevent two evaluation dimensions from
sharing the same prediction set. Splitting the two means a run dir captures
*what the production pipeline produced*, and the eval scripts are pure
functions over `(golden, run_dir) → report`.

**Scope guardrails:**

- 10 papers per pass at launch — enough to surface obvious regressions, small
  enough that adding the golden labels by hand is realistic.
- Infra must accept a new paper by appending one YAML entry; no code change.
- Evals live at `evals/` at the repo root, separate from `tests/` (correctness)
  and `data/` (production state).

**Sequencing:**

- **Sub-task A — Generate Golden Values.** Build the labels we score against.
- **Sub-task B — Generate Production Predictions.** Run pass-1 and pass-2 on
  every golden paper, capture results + full provenance into a run dir.
- **Sub-task C — Evaluate Pass-1.** Score one run against the pass-1 golden.
- **Sub-task D — Evaluate Pass-2.** Score one run against the pass-2 golden,
  split into:
  - **D.1 — Extraction** (authors and affiliations; deterministic).
  - **D.2 — Scoring** (numeric buckets, theme placement, LLM-as-judge on
    free-text fields).

A is a prerequisite for B; B is a prerequisite for C, D.1, D.2. C, D.1, and D.2
are independent of each other and can land in any order.

- **Sub-task E — Evaluate Hypothesis Generation Quality.** Independent of the
  pass-1/pass-2 run-dir flow above; it evaluates the bootstrap hypothesis output
  introduced by the Plan 1 revision and reuses the LLM-as-judge infrastructure.

---

## Sub-task A — Generate Golden Values

**Depends on:** —

Golden labels are themselves a quality artifact: they must be coherent,
reproducible, and easy to regenerate when the topic config or themes change.
We hand-fill the trivially objective fields (authors, affiliations) and use a
frontier LLM in chat UI (Opus 4.7 or GPT 5.5, **not** the API) to draft the
judgment-heavy fields, then commit only after a human line-by-line review.

**Why chat UI, not API:** the chat loop gives the operator natural
follow-ups ("why did you put DPO as fail?") and lets them commit only the
final state. Wiring this into a script would hard-code judgments that should
be a human decision.

### Changes

| File | Action | Description |
|---|---|---|
| `evals/golden/pass1.yaml` | **NEW** | 10 entries: `url`, `expected_label` (`pass` \| `fail`), `notes`. Mix: 5 clear-pass, 3 clear-fail, 2 edge cases. |
| `evals/golden/pass2.yaml` | **NEW** | 10 entries with combined extraction + scoring golden labels per paper. Same on-thesis paper set (see list below). |
| `evals/golden/aliases.yaml` | **NEW** | Institution canonicalization map (e.g. `DeepMind: Google DeepMind`, `FAIR: Meta`). Consumed by D.1 when comparing affiliation sets. |
| `evals/golden/judge_prompt.md` | **NEW** | Frozen rubric prompt used by D.2 for LLM-as-judge grading of free-text fields. Lists the 1–5 scale and the criteria per field. |
| `evals/golden/GENERATE_PASS1.md` | **NEW** | Self-contained copy-paste prompt that produces `pass1.yaml`. Hand the LLM the topic thesis, scope, schema, and the 10-paper list. |
| `evals/golden/GENERATE_PASS2.md` | **NEW** | Same shape for `pass2.yaml`. Includes the theme list, bucket boundaries, schema, and the 10-paper list. Does **not** ask the LLM to fill `expected_authors` / `expected_affiliations` — those are hand-copied from the arXiv abs page (faster than an LLM round-trip + verification). |
| `evals/golden/README.md` | **NEW** | What this evals, how to add a paper, how to regenerate after the topic changes, how to extend the alias map. |

### `pass1.yaml` schema

```yaml
- url: "https://arxiv.org/abs/2404.01234"
  expected_label: "pass"          # pass | fail
  notes: "Core synthetic-data paper, should clearly clear threshold."
```

### `pass2.yaml` schema

```yaml
- url: "https://arxiv.org/abs/2306.11644"
  expected_authors:                # ordered, verbatim from the paper byline
    - "Suriya Gunasekar"
    - "Yi Zhang"
    # …
  expected_affiliations:           # set
    - "Microsoft Research"
  expected:
    applicability_bucket: "high"   # low (0–3) | medium (4–7) | high (8–10)
    strategic_significance_bucket: "high"
    expected_top_theme: "synthetic-data-generation"
    acceptable_themes:             # any of these are OK in candidate_themes
      - "synthetic-data-generation"
    rationale_must_mention:        # guidance for the judge, not regex
      - "the self-play loop"
      - "scaling beyond 70B"
  notes: "Flagship example for the synthetic-data theme."
```

Both `expected_authors` and `expected_affiliations` are sets — order is not
checked. `rationale_must_mention` is a hint to the judge in D.2; the judge
decides whether the rationale faithfully covers the paper.

### Initial paper lists

**`pass1.yaml` (10 papers — verify arXiv IDs before committing):**

| # | Title | arXiv | Label | Why |
|---|-------|-------|-------|-----|
| 1 | Textbooks Are All You Need (Phi-1) | 2306.11644 | pass | Flagship synthetic-data paper. |
| 2 | Self-Rewarding Language Models | 2401.10020 | pass | Bootstrap-data / self-play loop. |
| 3 | The FineWeb Datasets | 2406.17557 | pass | Web-scale curation pipeline. |
| 4 | DataComp-LM | 2406.11794 | pass | Open data-curation benchmark. |
| 5 | The Curse of Recursion | 2305.17493 | pass | Risks of training on generated data. |
| 6 | Mamba: Linear-Time Sequence Modeling | 2312.00752 | fail | Pure architecture. |
| 7 | FlashAttention | 2205.14135 | fail | Pure systems / inference. |
| 8 | MMLU | 2009.03300 | fail | Evaluation benchmark. |
| 9 | Direct Preference Optimization (DPO) | 2305.18290 | edge | Alignment method that relies on preference data. |
| 10 | Self-RAG | 2310.11511 | edge | Retrieval-augmented method, data-adjacent. |

For edge cases, default to `fail` if the human grader can't decide — keeps
the threshold sharp.

**`pass2.yaml` (10 papers — all on-thesis since pass-2 only sees survivors):**

| # | Title | arXiv | Primary theme tested |
|---|-------|-------|----------------------|
| 1 | Textbooks Are All You Need (Phi-1) | 2306.11644 | synthetic-data-generation |
| 2 | Self-Rewarding Language Models | 2401.10020 | synthetic-data-generation |
| 3 | The FineWeb Datasets | 2406.17557 | quality-filtering-curation |
| 4 | DataComp-LM | 2406.11794 | quality-filtering-curation |
| 5 | The Curse of Recursion | 2305.17493 | synthetic-data-generation (risks) |
| 6 | Beyond Human Data (ReST^EM) | 2312.06585 | synthetic-data-generation |
| 7 | OLMo | 2402.00838 | provenance-and-licensing |
| 8 | The False Promise of Imitating Proprietary LLMs | 2305.15717 | synthetic-data-generation (limits) |
| 9 | WRAP: Rephrasing the Web for Pretraining | 2401.16380 | quality-filtering-curation |
| 10 | Nemotron-4 340B Technical Report | 2406.11704 | synthetic-data-generation |

### `GENERATE_PASS1.md` (template)

```markdown
You are helping me build a golden evaluation set for a binary relevance
classifier. The classifier ("pass-1") scores AI/ML papers 0–10 against a
research topic and drops anything below 6. Label each paper as `pass` or
`fail` and produce a YAML file.

## Topic

**Name:** Emerging Data Advantages in AI

**Thesis:**
> A technical strategy brief tracking which new data assets, collection methods,
> and dataset-generation approaches create durable competitive advantage in AI
> systems. The reference class includes scale-unlocking corpora (ImageNet,
> Common Crawl, The Pile, LAION), quality-and-filtering advances (C4,
> RedPajama, FineWeb, Dolma), annotation-dense or diversity-expanding sets
> (MS COCO, ShareGPT, multilingual corpora), synthetic and self-generated data
> (Phi textbooks, Self-Instruct, distilled reasoning), human-preference and
> alignment data (Anthropic HH, OpenAssistant, UltraFeedback), and
> domain-specific unlocks (The Stack, Open X-Embodiment, AlphaFold/PDB,
> MATH/GSM8K).

**In scope:** scale-unlocking corpora; quality-and-filtering advances; diversity
and coverage expansion; annotation-dense datasets; synthetic and self-generated
data; human-preference/alignment data; domain-specific data unlocks;
provenance/licensing/legal shifts affecting data availability.

**Out of scope:** pure architecture papers, pure systems/inference optimization,
pure evaluation benchmarks (unless the benchmark *is* a notable data asset),
training-algorithm work that does not introduce or analyze a data asset.

## Task

For each paper in the list below:
1. Fetch the abstract (or rely on your prior knowledge if no retrieval).
2. Decide `pass` or `fail` against the thesis.
3. Write a one-sentence `notes` field. For edge cases say
   "edge — defaulting to <pass|fail> because …".
4. Verify each arXiv URL resolves; correct if not.

## Output

A single YAML document, no prose around it:

    - url: "https://arxiv.org/abs/<id>"
      expected_label: "pass"   # or "fail"
      notes: "<one sentence>"

## Paper list

[the 10 papers from pass1.yaml above]

Produce the YAML. After it, list any papers you were uncertain about and
explain the call.
```

### `GENERATE_PASS2.md` (template)

```markdown
You are helping me build a golden evaluation set for a multi-field paper
scorer ("pass-2"). For each paper produce golden labels covering applicability,
strategic significance, and theme placement.

You will NOT fill `expected_authors` or `expected_affiliations` — those are
hand-copied from the paper byline (faster than an LLM round-trip).

## Topic

[same thesis paragraph as GENERATE_PASS1.md]

## Themes

Place each paper under one or more themes. `expected_top_theme` is the single
best fit.

- `scale-unlocking-corpora` — corpora that unlock a new capability regime by
  sheer size.
- `quality-filtering-curation` — deduplication, filtering, contamination
  control, and curation pipelines.
- `diversity-coverage-expansion` — multilingual, multimodal, long-tail
  coverage.
- `annotation-dense-datasets` — dense labels, grounding, structured
  supervision.
- `synthetic-data-generation` — model-authored corpora, distillation,
  self-instruct.
- `human-preference-alignment` — RLHF, DPO-style, constitutional feedback
  datasets.
- `provenance-and-licensing` — legal-moat, open-vs-closed, licensing shifts.
- `domain-specific-unlocks` — code, math/reasoning, robotics, biology.

## Score buckets

| Bucket | Score range |
|--------|-------------|
| low    | 0–3 |
| medium | 4–7 |
| high   | 8–10 |

- `applicability_bucket` — how directly the paper advances the data-advantage
  thesis. A paper that *is* a new data asset scores high; a passing mention
  scores low.
- `strategic_significance_bucket` — how much this paper should shift a
  technical decision-maker's strategy. High = "you should change what you're
  doing"; low = "interesting but no action".

## Task

For each paper:
1. Fetch the abstract; skim the paper if accessible.
2. Decide `applicability_bucket` and `strategic_significance_bucket`.
3. Pick `expected_top_theme` and `acceptable_themes` (top + any other
   defensible matches).
4. Write 2–4 `rationale_must_mention` bullets — short phrases the rationale
   should cover (hints for an LLM judge, not regex).
5. Verify each arXiv URL resolves.

## Output

A single YAML document, no prose around it:

    - url: "https://arxiv.org/abs/<id>"
      expected_authors: []        # leave empty — hand-filled later
      expected_affiliations: []   # leave empty — hand-filled later
      expected:
        applicability_bucket: "low|medium|high"
        strategic_significance_bucket: "low|medium|high"
        expected_top_theme: "<theme_id>"
        acceptable_themes:
          - "<theme_id>"
        rationale_must_mention:
          - "<short phrase>"
      notes: "<one sentence>"

## Paper list

[the 10 papers from pass2.yaml above]

Produce the YAML. After it, list any papers where you hesitated on the bucket
or theme call.
```

### Verification

- `GENERATE_PASS1.md` and `GENERATE_PASS2.md` are self-contained — pasting
  either into a fresh chat with no prior context produces a usable YAML draft.
- Operator commits the YAML only after a manual line-by-line review.
- Hand-filling `expected_authors` / `expected_affiliations` for 10 papers
  takes ~5 minutes total.
- Re-running a prompt later (after the topic config or theme list changes)
  regenerates the golden set with the new context — keeps evals from going
  stale silently.

---

## Sub-task B — Generate Production Predictions

**Depends on:** Sub-task A.

One script invocation produces a *run directory* containing the predictions
for every paper in the golden sets, plus full provenance. C, D.1, and D.2
read from the run dir; they never call the production pipeline themselves.

### Changes

| File | Action | Description |
|---|---|---|
| `evals/generate_predictions.py` | **NEW** | Reads both golden files, runs `pass1_score` on every `pass1.yaml` paper and `pass2_score` on every `pass2.yaml` paper, writes a fresh `evals/runs/{utc-timestamp}_{label}/` dir. Operator supplies `--label` (e.g. `baseline-pro`, `new-prompt-flash`). |
| `evals/runs/.gitkeep` | **NEW** | Keeps the runs directory tracked. Individual run dirs are committed when they back a report worth keeping; otherwise they can be deleted freely. |

### Run directory layout

```
evals/runs/{utc-timestamp}_{label}/
  manifest.json
  pass1/
    {paper_id}.json
  pass2/
    {paper_id}/
      signal.md
      normalized_item.json
  reports/                          # populated later by C, D.1, D.2
```

`{paper_id}` is the deterministic `signal_id` from `make_signal_id` (e.g.
`arxiv_2026-04-29_a3f7b2c1de`), so the same paper has the same path across
runs and diffs cleanly.

### `manifest.json`

```json
{
  "label": "baseline-pro",
  "generated_at": "2026-05-23T14:22:01Z",
  "git_sha": "40d18c4",
  "pass1_scoring_threshold": 6,
  "models": {
    "pass1": "gemini-2.5-flash",
    "pass2": "gemini-2.5-pro"
  },
  "prompts": {
    "pass1_rendered_example": "<full rendered build_pass1_prompt output for paper #1>",
    "pass2_rendered_example": "<full rendered build_pass2_prompt output for paper #1>"
  },
  "papers": {
    "pass1": ["arxiv_2023-06-20_…", "…"],
    "pass2": ["arxiv_2023-06-20_…", "…"]
  }
}
```

The full rendered prompt for paper #1 is captured so any historical report
remains reproducible months later, even after `src/topics/prompts.py` has
moved on.

### `pass1/{paper_id}.json`

```json
{
  "url": "https://arxiv.org/abs/2306.11644",
  "paper_id": "arxiv_2023-06-20_c9d7a99d2c",
  "predicted_relevance": 8,
  "predicted_reason": "Phi-1 introduces a curated synthetic-data pipeline …",
  "passed_threshold": true,
  "raw_response": "{\"topical_relevance\": 8, \"reason\": \"…\"}"
}
```

### `pass2/{paper_id}/`

- `signal.md` — the exact signal file the production `pass2_score` would have
  written, but written into the run dir instead of `data/`. Production
  `signals/` is never touched.
- `normalized_item.json` — the `NormalizedItem` after `fetch_item`, captured
  before scoring. D.1 reads `authors` from here.

### Invocation

```bash
PYTHONPATH=src python evals/generate_predictions.py --label baseline-pro
# → wrote evals/runs/2026-05-23T14-22-01Z_baseline-pro/
```

Each invocation creates a new run dir; the script never merges into an
existing one. To re-score after a prompt change, just run again with a new
label.

### Verification

- The run dir contains predictions for every paper in `pass1.yaml` and every
  paper in `pass2.yaml`.
- A pass-2 fetch failure on one paper is logged and that paper is skipped, but
  every other paper still produces a prediction — partial runs are useful, not
  fatal.
- `manifest.json` lets a reader six months later answer "what produced this
  number?" from disk alone.
- Running on the same git SHA twice produces structurally identical run dirs
  (same paths, same paper IDs); LLM responses may differ by sampling but the
  shape is fixed.

---

## Sub-task C — Evaluate Pass-1

**Depends on:** Sub-task B.

Pass-1 is a binary decision: does the item clear `SCORING_THRESHOLD`? The
eval treats it that way — per paper, report `PASS` / `FAIL` against the
golden label plus the model's own one-sentence justification, then aggregate
accuracy / precision / recall.

### Changes

| File | Action | Description |
|---|---|---|
| `evals/eval_pass1.py` | **NEW** | Reads the golden file at the fixed path `evals/golden/pass1.yaml` and the predictions under `<run_dir>/pass1/`, joins by `paper_id`, compares verdicts, writes a markdown report to `<run_dir>/reports/pass1.md`. Operator supplies `--run <path-to-run-dir>`. |

### Invocation

`--run` takes the path to a run directory produced by Sub-task B. The golden
file path is not configurable — it is always `evals/golden/pass1.yaml`, so
that two reports from different runs are guaranteed to compare against the
same yardstick.

```bash
PYTHONPATH=src python evals/eval_pass1.py \
  --run evals/runs/2026-05-23T14-22-01Z_baseline-pro
# → wrote evals/runs/2026-05-23T14-22-01Z_baseline-pro/reports/pass1.md
```

### Report format

```markdown
# Pass-1 Eval Report

Run: 2026-05-23T14-22-01Z_baseline-pro
Model: {manifest.models.pass1}   Threshold: {manifest.pass1_scoring_threshold}   git SHA: {manifest.git_sha}

## Prompt used (verbatim, from manifest)

{prompt text}

## Summary

| Metric    | Value |
|-----------|-------|
| Accuracy  | 9/10  |
| Precision | 5/6   |
| Recall    | 5/5   |

Confusion matrix: TP=5  FP=1  TN=3  FN=0

## Per-paper results

| # | URL | Expected | Actual | Relevance | Verdict | Justification |
|---|-----|----------|--------|-----------|---------|---------------|
| 1 | arxiv.org/abs/… | pass | pass | 8 | ✅ | … one-sentence reason … |
| 2 | arxiv.org/abs/… | fail | pass | 7 | ❌ FP | … |
```

The prompt block comes verbatim from the run's `manifest.json`. Comparing two
runs' pass-1 reports diffs the prompt change and the score change side by
side.

### Verification

- `eval_pass1.py` makes zero LLM calls — pure file read + comparison.
- A run dir missing `pass1/` predictions exits with a clear error pointing the
  operator at Sub-task B.
- A golden entry whose paper_id is missing from the run dir is flagged in the
  report as "MISSING PREDICTION" rather than silently dropped.
- Re-running on the same run dir produces a byte-identical report (no LLM
  drift on the eval side).

---

## Sub-task D — Evaluate Pass-2

**Depends on:** Sub-task B.

Pass-2 emits many fields of different kinds. A single number would hide more
than it reveals. The eval is split into two independent dimensions:

- **D.1 — Extraction:** authors and affiliations. Deterministic
  precision/recall, no LLM judgment.
- **D.2 — Scoring:** numeric scores, theme placement, free-text rationale.
  Bucket and theme checks are deterministic; free-text fields go to an
  LLM-as-judge.

Both dimensions read from the same run dir, so they always evaluate the same
predictions.

### D.1 — Extraction (authors and affiliations)

**Why this dimension exists:** authors come from the source adapter,
affiliations from the pass-2 LLM call. Both are extraction, not judgment —
there is one objectively right answer per paper. This is the cheapest, most
catastrophic-failure-catching dimension: an adapter that starts truncating
author lists or an LLM that hallucinates affiliations corrupts every
downstream wiki and briefing artifact.

#### Changes

| File | Action | Description |
|---|---|---|
| `evals/eval_pass2_extraction.py` | **NEW** | Reads `evals/golden/pass2.yaml` (extraction fields), `evals/golden/aliases.yaml`, and `evals/runs/{run}/pass2/{paper_id}/{signal.md, normalized_item.json}`. Normalizes affiliation sets via the alias map. Computes precision/recall for author and affiliation sets (both order-insensitive). Writes `evals/runs/{run}/reports/pass2_extraction.md`. |

#### Report format

```markdown
# Pass-2 Extraction Eval Report

Run: 2026-05-23T14-22-01Z_baseline-pro
Alias map: evals/golden/aliases.yaml (sha256: …)

## Summary

| Metric                          | Value |
|---------------------------------|-------|
| Authors      precision / recall | 0.98 / 0.96 |
| Affiliations precision / recall | 1.00 / 0.92 |
| Papers with perfect extraction  | 8/10  |

## Per-paper results

| # | URL | Authors P/R | Affiliations P/R | Notes |
|---|-----|-------------|------------------|-------|
| 1 | arxiv.org/abs/2306.11644 | 1.00 / 1.00 | 1.00 / 1.00 | ✅ |
| 2 | arxiv.org/abs/2401.10020 | 1.00 / 0.92 | 1.00 / 1.00 | missing 1 author: "Jane Doe" |
| 3 | arxiv.org/abs/2406.17557 | 1.00 / 1.00 | 0.67 / 1.00 | extra affiliation: "Hugging Face Inc" — extend alias map |
```

The "Notes" column names the specific missing or extra entries so a red
number is actionable (extend alias map, file adapter bug, fix golden label).

#### Verification

- `eval_pass2_extraction.py` makes zero LLM calls.
- Extending `aliases.yaml` closes "extra affiliation" reports without code
  changes.
- Re-running on the same run dir produces a byte-identical report.

### D.2 — Scoring (buckets, themes, judge-graded text)

**Grading approach (decided up-front):**

| Field | Method |
|---|---|
| `applicability_score`, `strategic_significance` | Bucket match: `low` (0–3), `medium` (4–7), `high` (8–10). Pass = bucket matches the golden bucket. |
| `candidate_themes` | Top-1 `theme_id` must equal the golden `expected_top_theme`. Secondary themes graded as recall@3 against `acceptable_themes`. |
| `claims`, `rationale` | LLM-as-judge rubric (from `evals/golden/judge_prompt.md`) returns a 1–5 score + one-line justification per field. Pass-2 extracts plain claims; hypothesis matching and stance belong to Plan 9. |
| `paper_audience` | LLM-as-judge: same rubric, 1–5. |

Numeric / categorical checks are deterministic; only free-text fields go to
the judge. The judge prompt lives in `evals/golden/` and is frozen-by-commit
so a judge-prompt edit is its own visible diff.

**Judge calls are not cached.** Each D.2 invocation makes fresh judge calls
against the prediction. This is intentional: judge calls are cheap, and we
expect to iterate on the judge prompt itself. Re-runs may drift by ±1 — that
drift is documented signal, not a bug.

#### Changes

| File | Action | Description |
|---|---|---|
| `src/topics/eval_judge.py` | **NEW** | `judge_free_text(field_name, paper_summary, actual_text, criteria) → (score: int, justification: str)`. Wraps a single Gemini call with the rubric. Kept in `src/topics/` so future code can reuse it. |
| `evals/eval_pass2_scoring.py` | **NEW** | Reads `evals/golden/pass2.yaml` (scoring fields) and `evals/runs/{run}/pass2/{paper_id}/signal.md`. Applies bucket / theme / judge grading. Writes `evals/runs/{run}/reports/pass2_scoring.md`. |

#### Report format

```markdown
# Pass-2 Scoring Eval Report

Run: 2026-05-23T14-22-01Z_baseline-pro
Scoring model: {manifest.models.pass2}   Judge model: {JUDGE_MODEL}

## Prompts used

### Scoring prompt (verbatim, from manifest)
{scoring prompt}

### Judge prompt (verbatim, from evals/golden/judge_prompt.md)
{judge prompt}

## Roll-up

| Metric                          | Value |
|---------------------------------|-------|
| Applicability bucket match      | 8/10  |
| Strategic-sig bucket match      | 7/10  |
| Top-1 theme match               | 9/10  |
| Theme recall@3                  | 0.87  |
| Rationale judge mean            | 4.2   |
| Evidences judge mean            | 4.1   |
| Audience judge mean             | 4.4   |

## Per-paper scorecards

### 1. arxiv.org/abs/2306.11644

| Field | Expected | Actual | Verdict |
|-------|----------|--------|---------|
| applicability_bucket | high | high (8) | ✅ |
| strategic_significance_bucket | high | medium (7) | ❌ |
| top-1 theme | synthetic-data-generation | synthetic-data-generation | ✅ |
| theme recall@3 | — | 2/2 acceptable found | ✅ |
| rationale (judge) | — | 4 — covers self-play loop; misses scaling note | — |
| evidences (judge) | — | 5 — all three claims faithful, stances correct | — |
| audience (judge) | — | 5 — names "post-training infra teams" | — |
```

#### Bucket boundaries (frozen here so they don't drift)

| Bucket | Score range |
|---|---|
| low    | 0–3 |
| medium | 4–7 |
| high   | 8–10 |

#### Verification

- `eval_pass2_scoring.py` makes ~40 judge LLM calls per run (10 papers × 4
  free-text fields). The expensive pass-2 scoring calls are not repeated —
  they live in the run dir from Sub-task B.
- A run dir missing `pass2/` predictions exits with a clear error.
- Re-running on the same run dir produces a *near-identical* report; judge
  scores may drift by ±1 between invocations.

---

## Sub-task E — Evaluate Hypothesis Generation Quality

**Depends on:** Plan 8 (hypothesis schema), Plan 1 revision (bootstrap emits hypotheses).

The Plan 1 revision makes bootstrap (and, via Plan 9, the signal pipeline) emit
hypotheses as falsifiable directional bets. A *schema-valid* hypothesis can
still be a *bad bet*: a vague metric, an unfalsifiable threshold, a missing
horizon, or two claims smuggled into one record. Shape tests cannot catch any
of that — this dimension does. It is the quality gate for the betting-market
authoring constraint defined in Plan 8.

### Changes

| File | Action | Description |
|---|---|---|
| `evals/golden/hypotheses.yaml` | **NEW** | A handful of golden dossiers/inputs paired with human judgments on what a good generated hypothesis set looks like for each. |
| `evals/eval_hypotheses.py` | **NEW** | Runs bootstrap hypothesis generation over the golden inputs and judges each emitted hypothesis with an LLM-as-judge rubric; writes a markdown report. |
| `evals/golden/judge_prompt_hypotheses.md` | **NEW** | Frozen rubric scoring each hypothesis on: (1) single directional claim (atomicity); (2) **resolvability** — could two reviewers independently settle the bet the same way, given the statement plus whatever `resolution_criterion` scaffolding is present; (3) **shape recognition** — the bet's shape matches the claim (a relational "A beats B" claim is written as a comparative bet with `comparison` populated by the correct two subjects; a standalone claim is not spuriously marked comparative); (4) strategically relevant to the topic. Falsifiability is not a separate axis — a resolvable bet is by definition falsifiable. |

### Grading

| Check | Method |
|---|---|
| Atomicity (one directional claim) | LLM-as-judge, 1–5 |
| Resolvability (could two reviewers independently settle the bet the same way?) | LLM-as-judge, 1–5. The `resolution_criterion` 4-tuple is the scaffold the judge looks for *where the statement isn't already unambiguous* — not a presence check, since the field is optional |
| Shape recognition (standalone vs comparative) + subject accuracy | LLM-as-judge, 1–5. When the underlying claim is relational, is `comparison` populated with the *correct* two subjects and the statement a faithful, resolvable "A vs B"? Penalize a relational claim flattened into a standalone statement, and a standalone claim spuriously marked comparative |
| Strategic relevance | LLM-as-judge, 1–5 |

### Verification

- A hypothesis that isn't resolvable — a vague claim, or a resolution criterion
  too loose for two reviewers to settle the same way — scores low and is named
  in the report. A green run means the generated bets are actually resolvable.
- A multi-claim "hypothesis" is flagged by the atomicity check.
- A relational claim written as a standalone statement (or a standalone claim
  spuriously marked comparative) is flagged; comparative bets name the correct
  two subjects.
- Re-running on the same generated set produces a near-identical report (±1
  judge drift).

---

## Out of scope

- **Inter-rater agreement against humans.** Worth doing once the 10-paper set
  proves out, not now — would require >1 human grader and slows the loop.
- **Auto-promotion gates** (e.g., "block merge if accuracy < 0.8"). Eval is a
  measurement tool first; a CI gate is a later, separate decision.
- **Cost / latency tracking.** Easy to add later from the run-dir manifest;
  not the question this plan is answering.
- **Cross-run diff tooling.** Two reports diffed in `git diff` is good
  enough at 10 papers. A dedicated diff script is a follow-up if we scale up.
- **Eval for the wiki-update or briefing stages.** Those are separate plans on
  separate pipeline stages — the wiki-renderer evals now live in Plan 17, and the
  belief-graph evals in Plan 9 (Sub-tasks C and D), both reusing this plan's judge
  helper rather than extending it. (Bootstrap *hypothesis-generation* quality is now
  in scope — see Sub-task E — because it shares the judge infrastructure and
  gates the betting-market authoring constraint.)
