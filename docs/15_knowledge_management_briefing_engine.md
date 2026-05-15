# Plan 15 — Knowledge Management Briefing Engine

## Task 15.0 — Bootstrap Tooling ✅

Build the code that can parse a deep-research dossier and seed the topic wiki from it. No actual research run happens here — the goal is a working, tested pipeline ready for 15.0b to use.

**Why this matters:** Without a parser and seeder, 15.0b's operator run has no way to turn a pasted dossier into structured Markdown. Building and testing the tooling first also validates the dossier contract before committing to a real research pass.

**Changes:**

| File | Action | Description |
|---|---|---|
| `src/topics/frontmatter.py` | **NEW** | Pydantic models per file type + safe load/update/write for YAML frontmatter |
| `src/topics/bootstrap/prompt.py` | **NEW** | Builds the bootstrap deep research prompt from minimal `topic.md` fields |
| `src/topics/bootstrap/parser.py` | **NEW** | Extracts and validates the JSON block; maps records to typed structures |
| `src/topics/bootstrap/seeder.py` | **NEW** | Writes `themes/*.md` (frontmatter + prose body), `entities.json`, `timeline.json`, `open_questions.json`, `overview.md` (rendered from intro prose + theme list + top open questions); archives raw dossier under `dossiers/` |
| `tests/test_bootstrap_parser.py` | **NEW** | Fixture dossier → expected records; idempotent re-parse |

**Contract:**

- **Dossier format:** human-readable Markdown with a `## Theme: {kebab-id}` heading per theme **and** one trailing fenced `json` block. The parser uses both: prose sections feed theme bodies, JSON feeds metadata and reference data. Parser rejects mismatches between heading ids and JSON theme ids before any disk write.
- **Seeded theme defaults:** `origin: “bootstrap”` in frontmatter; `novelty_status: “globally_novel”` for bootstrap (literature-grounded); body = full prose section from the dossier.
- **Reference data defaults:** entities, timeline entries, and open questions written as flat JSON arrays at the topic root; merged by stable id on subsequent seeds.
- **Forward-only links** between files; **stable `<a id=”...”>` anchors** inside theme bodies for adjacent updates (see `research_briefing_architecture.md` §6, §11, §12).
- **Idempotency:** same dossier re-seeded is a no-op; second dossier merges into JSON arrays by stable id, appends only new theme files.
- **No partial writes** on failure — parser rejects invalid JSON and id mismatches before the seeder touches disk.

**Verification:**

- Parser rejects invalid JSON with a clear error; no partial writes on failure.
- Re-running the seeder on the same fixture dossier is a no-op (idempotent).
- A second fixture dossier merges correctly without duplicates.

**Explicitly out of scope:** the actual deep-research run and real data files (15.1b). Source adapters (15.2), live scoring (15.4), wiki updater for signals (15.5), brief generation (15.7).

**Status: passed** — 13 tests passing as of 2026-04-25. Spec: `docs/specs/15_0_bootstrap_tooling.test.md`.

---

## Task 15.1 — Topic Configuration Contract ✅

**Depends on:** Task 15.0 bootstrap tooling must be complete and tests passing.

Define the first-class configuration model for a reusable research topic.

**Why this matters:** The system must support topic shifts every 1-3 months without rewriting orchestration code. If topic definitions remain implicit in prompts or scattered config, the first implementation will hard-code the initial topic and make future pivots expensive.

**Changes:**

| File | Action | Description |
|---|---|---|
| `research_briefing/docs/data_advantage_brief.md` | **REF** | Use as the first topic/business context input |
| `research_briefing/docs/research_briefing_architecture.md` | **REF** | Use as the target system design |
| `src/config.py` | **DELETE** | Flat stub (6 lines); replaced by the `topics/` package (avoids name collision with `topics/config.py`'s role) |
| `src/pipeline.py` | **DELETE** | Flat stub (6 lines); orchestration will live alongside the topic modules once the real pipeline lands |
| `src/topics/config.py` | **NEW** | Topic config schema, validation helpers, and shared contracts |
| `data/research_topics/README.md` | **NEW** | File layout and topic lifecycle notes |
| `data/research_topics/data_advantage/topic.md` | **UPDATE** | Extends minimal `topic.md` from 15.0 with full validated config (frontmatter) |
| `data/audiences/technical_decision_makers.md` | **NEW** | First audience profile referenced by `topic.md.audience_ref` (persona, scope, tone) |
| `tests/test_topic_config.py` | **NEW** | Schema validates the first topic; rejects missing required fields with clear errors |

**Contract must define:**

- topic id and thesis
- target audience profile
- separate time horizons: `bootstrap_horizon` (historical depth for deep-research prompt) and `signal_horizon` (recency window for live ingestion)
- included and excluded signal classes
- source priorities
- taxonomy / subtopics
- scoring dimensions
- action vocabulary (`ignore`, `monitor`, `prototype`, `invest`, etc.)

**Verification:**

- A topic can be represented without touching orchestration code
- The first topic config is valid against the schema
- The contract is generic enough to support a different topic later

**Status: passed** — 11 tests passing as of 2026-04-21. Spec: `docs/specs/15_1_topic_config.test.md`.

---

## Task 15.1b — First Bootstrap Run (Data Advantage) ✅

**Depends on:** Task 15.1 topic configuration contract must be complete — the full `topic.md` (audience profile, source priorities, taxonomy, scoring dimensions, action vocabulary) is the input to the deep-research prompt.

Run the first real deep-research pass and use 15.0's tooling to seed the `data_advantage` wiki. This is the operator task, not a code task — the output is real data files, not new source code.

**Why this matters:** Without seeded themes and entities, "novelty" and "landscape fit" in later tasks have nothing to attach to. The seeded wiki also proves the dossier contract and on-disk layout before any live ingestion exists.

**Changes:**

| File | Action | Description |
|---|---|---|
| `data/research_topics/data_advantage/topic.md` | **UPDATE** | Already exists from 15.1; used as-is to generate the bootstrap prompt |
| `data/research_topics/data_advantage/dossiers/bootstrap_<date>.md` | **NEW** | Pasted output from the deep research run |
| `data/research_topics/data_advantage/themes/` | **NEW** | One `.md` per theme; frontmatter + full prose section from dossier |
| `data/research_topics/data_advantage/entities.json` | **NEW** | Flat JSON array of entity records |
| `data/research_topics/data_advantage/timeline.json` | **NEW** | Flat JSON array of timeline entries |
| `data/research_topics/data_advantage/open_questions.json` | **NEW** | Flat JSON array of open questions with `theme_ids` and `priority` |
| `data/research_topics/data_advantage/overview.md` | **NEW** | Rendered: intro prose + theme list with links + top open questions |

**Operator workflow:**

1. Run `prompt.py` against the completed `data_advantage/topic.md` → paste output into external deep research tool.
2. Paste full response into `dossiers/bootstrap_<date>.md`.
3. Run the seeder (from the project root, venv active):
   ```bash
   source sonaryn_env/bin/activate
   PYTHONPATH=research_briefing/src python -m topics.bootstrap.seeder \
       --dossier research_briefing/data/research_topics/data_advantage/dossiers/bootstrap_<date>.md
   ```
   `--topic-dir` and `--date` are optional; both default to sensible values (grandparent of the dossier file, and today's date respectively).
4. Inspect the generated files: `themes/`, `entities.json`, `timeline.json`, `open_questions.json`, `overview.md`.

**Verification:**

- One bootstrap run produces a complete seeded tree from one dossier paste.
- Operator judges the seeded wiki **useful enough** to read in one sitting and truer than an empty folder.
- No code changes needed — any needed fixes go back to 15.0.

**Explicitly out of scope:** source adapters (15.2), live scoring (15.4), wiki updater (15.5), brief generation (15.7).

**Status: passed** — First bootstrap run completed 2026-04-22: `data/research_topics/data_advantage/dossiers/bootstrap_2026_04_22.md` seeded `themes/`, `entities.json`, `timeline.json`, `open_questions.json`, and `overview.md`.

---

## Task 15.2 — Source Adapter Contract For Research Inputs ✅

Create the normalized ingestion contract for technical research and ecosystem sources.

**Why this matters:** The product now needs arXiv, lab blogs, dataset launches, and engineering writeups to flow through a common pipeline. Without a source adapter contract, every new source becomes a bespoke integration and the wiki layer cannot operate consistently.

**Changes:**

| File | Action | Description |
|---|---|---|
| `src/sources.py` | **DELETE** | Flat stub (6 lines); replaced by the `sources/` package below (Python forbids a module and package with the same name) |
| `src/sources/__init__.py` | **NEW** | Source registry; maps source ids to adapter classes; used by `topics/sources.py` for topic-aware resolution |
| `src/sources/base.py` | **NEW** | `SourceAdapter` ABC with three required methods: `fetch(query_params: dict) → bytes` (returns raw payload, any format), `parse(raw: bytes) → list[NormalizedItem]` (format-specific parse + normalize), `source_id() → str` (stable string key); plus the `NormalizedItem` Pydantic model |
| `src/sources/arxiv.py` | **NEW** | Adapter for arXiv; `fetch` queries the arXiv Atom API; `parse` reads Atom XML |
| `src/sources/lab_blog.py` | **NEW** | Adapter for lab or engineering blog sources; `fetch` retrieves RSS or HTML; `parse` reads RSS XML (falling back to HTML extract) |
| `src/topics/sources.py` | **NEW** | Resolves `enabled_sources` list from `topic.md` frontmatter to registered adapter instances |
| `tests/test_source_adapters.py` | **NEW** | One fixture per adapter class (arXiv: Atom XML; lab_blog: RSS XML); each fixture tests `parse` → `NormalizedItem` independently; raw payloads written as-is to `raw/{yyyy-mm-dd}/{source_name}{.xml/.html}` (no format coercion) |

**Adapter interface (`base.py`):**

```python
class SourceAdapter(ABC):
    @abstractmethod
    def source_id(self) -> str: ...

    @abstractmethod
    def fetch(self, query_params: dict) -> bytes: ...

    @abstractmethod
    def parse(self, raw: bytes) -> list[NormalizedItem]: ...
```

**Normalized item contract (`NormalizedItem`) should include:**

- `source_id` and `source_type`
- `title` and `url`
- `published_at` (ISO 8601)
- `authors` (list of strings) or `publisher` (org name)
- `summary` / abstract
- `metadata` — dict of source-specific fields (preserved verbatim for traceability)

**Raw archival:**

Adapters write the raw payload bytes to `raw/{yyyy-mm-dd}/{source_name}.{ext}` preserving the native format (`.xml` for Atom/RSS, `.html` for scraped pages). No coercion to JSON. The `metadata` field on `NormalizedItem` is the structured bridge from raw to normalized, not the archive itself.

**Topic-to-source resolution:**

`topic.md` frontmatter includes an `enabled_sources` list of source ids (e.g., `[arxiv, lab_blog]`). `topics/sources.py` reads this list and returns the corresponding adapter instances from the registry. An unknown id raises a clear error at load time.

**Verification:**

- One fixture per adapter class; each parses independently to the same `NormalizedItem` shape
- Raw payloads are archived in native format (not coerced to JSON)
- `topics/sources.py` resolves `enabled_sources` from a topic config and raises on unknown ids
- A third adapter can be added by implementing `SourceAdapter` and registering its id — no changes to `topics/sources.py` or `scoring.py`

**Status: passed** — 21 tests passing as of 2026-04-27. Spec: `docs/specs/15_2_source_adapter_contract.test.md`.

---

## Task 15.3a — Pass-1: Topic Relevance Filter ✅

**Depends on:** Task 15.2 source adapter contract (provides `NormalizedItem`).

Reuse the goal-engine filtering pattern as a fast, abstract-only relevance gate. Every `NormalizedItem` is scored against the topic thesis and taxonomy subtopics using only its `summary` field. Items that do not clear the threshold are discarded here — no full-text fetch, no disk write.

**Why this matters:** Fetching and scoring full-text for every ingested item would be expensive and slow. A cheap abstract-level gate keeps the costly pass-2 work proportional to what is actually relevant. The pattern (numeric score 0–10, model + fallback chain, threshold gate) is replicated from Sonaryn's goal engine — research_briefing owns its own config with no import dependency on the main codebase.

**Changes:**

| File | Action | Description |
|---|---|---|
| `src/config.py` | **NEW** | `GEMINI_API_KEY`, `SCORING_MODEL` (default `gemini-3.1-flash-lite-preview`), `SCORING_FALLBACK_MODEL` (default `gemini-2.5-flash-lite`), `SCORING_THRESHOLD` (default `6`); all overridable via env vars |
| `src/topics/models.py` | **NEW** | `AbstractScore` Pydantic model: `relevance: int` (0–10), `reason: str` |
| `src/topics/prompts.py` | **NEW** | `build_pass1_prompt(item: NormalizedItem, topic_config: TopicConfig) → str`; includes topic thesis, `scope_in`/`scope_out` lists, and taxonomy subtopics from `topic.md` frontmatter; item `summary` only |
| `src/topics/scoring.py` | **NEW** | `pass1_filter(items, topic_config) → list[tuple[NormalizedItem, AbstractScore]]`; one LLM call per item via `SCORING_MODEL` (with `SCORING_FALLBACK_MODEL` on failure); drops items where `relevance < SCORING_THRESHOLD`; returns `(item, score)` pairs so pass-2 has the pass-1 context available |
| `tests/test_topic_scoring_pass1.py` | **NEW** | 10 tests; Gemini client mocked (no API key required); covers threshold boundary, mixed batch, empty input, scoring failure, prompt content, and multi-item ordering |

**Pass-1 mechanics:**

- Model: `SCORING_MODEL` with `SCORING_FALLBACK_MODEL` on failure; one retry per model before falling back
- Threshold: `SCORING_THRESHOLD` (default `6`, inclusive — items at exactly 6 are kept)
- Prompt context: topic thesis + `scope_in`/`scope_out` + taxonomy subtopics; item `summary` only — no full text
- LLM response schema: `{"relevance": int, "reason": str}`; structured output enforced via Gemini `response_mime_type`
- Items that fail on all models are dropped silently (logged at ERROR); items below threshold are dropped (logged at INFO)
- No disk writes; return type is `list[tuple[NormalizedItem, AbstractScore]]` — pass-2 receives both the item and the pass-1 verdict

**Status: passed** — 10 tests passing as of 2026-04-28. Spec: `docs/specs/15_3a_pass1_topic_relevance_filter.test.md`.

**Verification:**

- Items with off-topic abstracts (e.g. no data-domain focus for `data_advantage`) are dropped and produce no downstream output
- Items with on-topic abstracts are returned with a populated `AbstractScore`
- The filter can run on a list of mixed items and return only the relevant subset
- An empty input returns `[]` without calling the Gemini API

---

## Task 15.3b-i — Source Credibility And Temporal Freshness ✅

**Depends on:** Task 15.2 (`NormalizedItem.affiliations`).

Define and implement the two deterministic scoring functions used downstream by pass-2 orchestration. Both are pure computations — no LLM call, no disk write beyond the operator-seeded JSON table.

**Why this matters:** Credibility and freshness need to be settled before the signal schema is designed (15.3b-iii) so the schema can reference them as first-class fields with a clear derivation. Seeding the institution table is also an operator task that cannot be automated — the right credibility proxy depends on the topic. Separating these pure functions from the LLM pass means they can be updated or recomputed without re-running the expensive model step.

**Changes:**

| File | Action | Description |
|---|---|---|
| `data/research_topics/data_advantage/source_credibility.json` | **NEW** | Topic-scoped institution weight table on a 0–10 log scale; seeded from ICLR 2026 fractional affiliation rankings (2050 institutions) |
| `data/iclr2026_institutions_ranked_fractional.csv` | **NEW** | Source data: ICLR 2026 accepted papers with fractional institution counts (1/N credit per paper); used to derive `source_credibility.json` |
| `src/topics/credibility.py` | **NEW** | `compute_source_credibility(affiliations: list[str], table: dict) → float | None`: averages weights of matched institutions; unmatched excluded; zero matches → `None`. `compute_temporal_freshness(published_at: datetime) → int`: 0–10 linear decay over a fixed 365-day window, independent of `signal_horizon` |
| `tests/test_credibility.py` | **NEW** | Credibility: matched orgs averaged, unmatched excluded, all unmatched → `None`, empty affiliations → `None`. Freshness: today → 10, 180 days → 5, 365 days → 0, beyond 365 → 0 |

**Source credibility table:**

Topic-scoped — the proxy depends on the topic, so the table travels with the topic rather than living globally. Seeded from ICLR 2026 fractional rankings using a log scale: `max(1, round(10 * log(count+1) / log(max_count+1)))`. Pivoting to a different topic means swapping the table. The table is static and editable; updating weights does not require re-running pass-2 since `affiliations` is preserved on the signal.

**Temporal freshness:**

Uses a fixed 365-day reference window, deliberately decoupled from `signal_horizon`. `signal_horizon` is an ingestion filter — it controls what enters the pipeline. Freshness scoring is separate: a paper just past the ingestion window (e.g. day 61 with a 60-day horizon) should not hard-floor to 0; it should still carry a low but meaningful score.

```
score = max(0, round(10 * (1 - age_days / 365)))
```

At 36 days → 9, at 180 days → 5, at 365 days → 0. No cliff, no dependency on topic config. In pass-2 ranking, `temporal_freshness` is a **tiebreaker/modifier**, not a primary axis — `applicability_score × source_credibility` drives the rank; freshness breaks ties among otherwise comparable signals.

**Verification:**

- Matched institutions are averaged; unmatched are excluded from the mean
- Zero matched institutions → `None` (not `0`)
- An item published today scores 10; at 180 days scores 5; at or beyond 365 days scores 0
- Both functions are importable and testable with no external dependencies

**Status: passed** — 16 tests passing as of 2026-05-14. Raw ranking data gitignored under `data/credibility/`; regeneration script in `data/credibility/README.md`.

---

## Task 15.3b-ii — Full-Text Adapter Extension

**Depends on:** Task 15.2 source adapter contract.

Extend the `SourceAdapter` ABC and both existing implementations with a `fetch_full_text` method and a `full_text_mime_type` class attribute, and add `full_text_fetched: bool` to `NormalizedItem`. Self-contained extension of the 15.2 contract with no dependency on scoring or credibility.

**Changes:**

| File | Action | Description |
|---|---|---|
| `src/sources/base.py` | **UPDATE** | Add `fetch_full_text(url: str) → bytes` abstract method and `full_text_mime_type: str` class attribute to `SourceAdapter`; add `full_text_fetched: bool` (default `False`) to `NormalizedItem` |
| `src/sources/arxiv.py` | **UPDATE** | Set `full_text_mime_type = "application/pdf"`; implement `fetch_full_text`: fetches the PDF for the arXiv id extracted from the item URL; returns raw PDF bytes |
| `src/sources/lab_blog.py` | **UPDATE** | Set `full_text_mime_type = "text/plain"`; implement `fetch_full_text`: fetches the article HTML at the item URL, strips tags via `_strip_html`, and returns UTF-8 encoded plain text bytes — markup is noise for the model and `_strip_html` already exists in this file |
| `tests/fixtures/arxiv_paper.pdf` | **NEW** | One real arXiv PDF fetched and stored as a fixture for offline tests |
| `tests/fixtures/lab_blog_article.html` | **NEW** | One real blog article HTML fetched and stored as a fixture for offline tests |
| `tests/test_source_adapters.py` | **UPDATE** | Add `fetch_full_text` fixture-backed tests for both adapters: arXiv bytes start with `%PDF` and are non-trivially sized; lab_blog bytes decode to plain text with no `<` characters; verify `full_text_fetched` defaults `False`; verify `full_text_mime_type` is declared correctly on each adapter |
| `scripts/smoke_full_text.py` | **NEW** | Operator smoke script: loads the two fixtures, sends each to the `google.genai` API (model passed via `--model` flag) with the correct `full_text_mime_type`, prompts for a summary, and prints the response. Exits cleanly if the API accepts the content; operator reads the output to judge quality. Run instructions in the file docstring. |

**Verification:**

- `fetch_full_text` returns bytes for a valid URL
- `ArxivAdapter.fetch_full_text` returns raw PDF bytes (`%PDF` header present); `LabBlogAdapter.fetch_full_text` returns HTML-stripped UTF-8 plain text bytes (no `<` characters)
- `full_text_mime_type` is `"application/pdf"` for arXiv and `"text/plain"` for lab_blog
- A failed fetch raises a clear exception (not swallowed); the caller (15.3b-iv) decides whether to drop the item
- `full_text_fetched` defaults `False` on `NormalizedItem` construction
- A third adapter can be added by declaring `full_text_mime_type` and implementing `fetch_full_text` — no changes elsewhere
- Operator runs `scripts/smoke_full_text.py --model <model>` and confirms both summaries are coherent before marking this task complete

---

## Task 15.3b-iii — Pass-2 Prompt And Signal Schema

**Depends on:** Task 15.3a (`AbstractScore`, `NormalizedItem`); Task 15.1 (`TopicConfig`, theme definitions); Task 15.3b-i (credibility and freshness field definitions).

Define the `Pass2Score` model and the pass-2 prompt contract. This task fixes the schema that 15.3b-iv, 15.4, 15.5, and 15.6 all depend on.

**Why this matters:** The signal schema is a shared contract between scoring, storage, wiki update, and output generation. Settling it before those layers are built avoids cascading schema migrations later.

**Changes:**

| File | Action | Description |
|---|---|---|
| `src/topics/models.py` | **UPDATE** | Add `CandidateTheme` model (`theme_id: str`, `confidence: int`, `rationale: str`); add `Pass2Score` Pydantic model (see schema below); add `signal_id` generation helper |
| `src/topics/prompts.py` | **UPDATE** | Add `build_pass2_prompt(item: NormalizedItem, topic_config: TopicConfig, theme_definitions: dict[str, str]) → str`; instructs the model to read like a scientist; provides theme definitions only (no bodies, no existing questions, no existing evidences) |
| `tests/test_pass2_schema.py` | **NEW** | `Pass2Score` roundtrips through JSON; `signal_id` is deterministic for the same URL; `CandidateTheme` requires `rationale`; prompt includes theme definitions and excludes theme bodies and existing evidences |

**Pass-2 prompt instructions (high-level):**

The prompt directs the model to act as a research scientist reviewing the paper:

- Read abstract, introduction, and conclusion to form a general understanding.
- Read methodology in depth to score `applicability_score` — is this a scalable approach, a clever-but-niche trick, a theoretical curiosity? The bias is toward methods that scale (Sutton's bitter lesson), not methods that are intellectually elegant.
- Identify the paper's own target audience as free text (e.g., `industry practitioners building post-training pipelines`, `mechanistic interpretability researchers`).
- For each provided theme (definition only, not body), assess connection strength and write a one-sentence rationale for the assigned confidence; return up to 3, sorted by descending confidence.
- Surface new open questions raised by the paper as self-contained text. The model is not given existing open questions; 15.5 will dedup against the wiki and increment per-question counts.
- Surface new evidence claims with stance. The model is not given existing evidences; 15.5 will dedup against `evidence.json`, increment per-evidence strength counters (weighted by `source_credibility`), and link to hypotheses.
- Extract author affiliations as a list of organization strings as cited in the source (paper title block, blog publisher, etc.).

**`Pass2Score` schema:**

```yaml
applicability_score: int           # 0–10
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

**`signal_id` generation:**

```
{source_id}_{published_date}_{sha256(url)[:10]}
```

Example: `arxiv_2026-04-29_a3f7b2c1de`. Deterministic: same URL always produces the same `signal_id` and the same file path.

**Signal file format (`signals/{yyyy}/{mm}/{dd}/{signal_id}.md`):**

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
paper_audience: "industry practitioners building post-training pipelines"
source_credibility: 9
temporal_freshness: 9
candidate_themes:
  - theme_id: "synthetic-data-generation"
    confidence: 9
    rationale: "Core contribution is a scalable synthetic pipeline directly implementing this theme."
  - theme_id: "filtering-and-curation"
    confidence: 6
    rationale: "Secondary result evaluates quality filters, but this is not the paper's focus."
  - theme_id: "scalable-training-recipes"
    confidence: 4
    rationale: "Training setup is standard; the paper does not advance this theme."
new_open_questions:
  - text: "How does this approach scale beyond 70B parameters?"
new_evidences:
  - claim: "Synthetic data generated by … achieves parity with human-curated data on benchmark X."
    stance: "for"
---

## Rationale

[Markdown body from the model: how the paper connects to current knowledge, what it changes, what questions it raises, who should care.]
```

**Provenance:** every `new_open_question` and `new_evidence` is anchored to its parent `signal_id` by virtue of living inside the signal file. 15.5 reads them with that anchor when incrementing question counts and weighting evidence by `source_credibility`.

**Notes for adjacent tasks:**

- **15.4:** the signal frontmatter schema above is the authoritative contract; `storage.py` builds its read/merge helpers against this schema. `evidence.json` schema gains a `strength` counter and a per-update audit trail capturing the contributing `signal_id` and the credibility weight applied at the time of the increment.
- **15.5:** owns classification (`replication` / `adjacent` / `wholly_new`) and writes the resolved `classification` and `theme_id_assigned` back to the signal frontmatter so 15.6 can filter on them; hypothesis impact resolution; dedup of `new_open_questions` and `new_evidences` against the existing wiki; per-question count increments (with provenance back to `signal_id`); per-evidence strength increments (weighted by `source_credibility`; `null` credibility falls back to a neutral weight defined in 15.5 config); `convergence` computation from signal history.
- **15.6:** owns `strategic_significance`, `action` text generation, top-N daily filtering, and audience-match logic between `paper_audience` and `topic.md.audience`.

**Verification:**

- `Pass2Score` parses from a JSON string without error
- `signal_id` is identical for two calls with the same URL
- Prompt includes theme definitions but not theme bodies or existing evidences
- `candidate_themes` entries each carry a `rationale` field

---

## Task 15.3b-iv — Pass-2 Orchestration And Signal Writing

**Depends on:** Task 15.3a (pass-1 filtered items and `AbstractScore`); Task 15.1b (seeded `themes/` with definitions in frontmatter); Task 15.3b-i (`credibility.py`, `source_credibility.json`); Task 15.3b-ii (`fetch_full_text`); Task 15.3b-iii (`Pass2Score`, `build_pass2_prompt`, signal file schema).

Wire together full-text fetch, LLM scoring, deterministic credibility and freshness, and signal file writing into the `pass2_score` function.

**Why this matters:** Reading the source is the expensive step. Once read, every downstream judgment (theme placement, evidence integration, briefing copy) draws from the same shared context. Splitting comprehension from wiki-mutation means the wiki updater (15.5) can re-resolve classifications without re-paying the model cost. Gating the full-PDF fetch behind pass-1 keeps this expensive step proportional to genuinely relevant items.

**Changes:**

| File | Action | Description |
|---|---|---|
| `src/topics/scoring.py` | **UPDATE** | Add `pass2_score(items: list[tuple[NormalizedItem, AbstractScore]], topic_config: TopicConfig, topic_dir: Path, adapter: SourceAdapter) → list[Path]`; fetches full text, scores via LLM, computes credibility and freshness deterministically, writes signal files |
| `tests/test_topic_scoring_pass2.py` | **NEW** | Fixture pass-1 items → written signal files; verify schema; verify `full_text_fetched: true`; verify idempotency on re-run; verify `fetch_full_text` failure drops the item; verify credibility and freshness values in written frontmatter |

**Pass-2 mechanics:**

For each item passed in from 15.3a:

1. Call `adapter.fetch_full_text(item.url)` → capture the returned bytes as a local variable; set `item.full_text_fetched = True`. If the fetch fails, drop the item — no disk write, failure logged.
2. Build the prompt via `build_pass2_prompt`, passing theme definitions (not bodies). The prompt does **not** include current open questions or evidences — those are output-only at this stage; integration into the wiki happens in 15.5.
3. Call `SCORING_MODEL` (with `SCORING_FALLBACK_MODEL` on failure) passing the bytes with `adapter.full_text_mime_type` — Gemini receives PDF bytes natively for arXiv (`application/pdf`) and plain text for blog posts (`text/plain`). Parse the response as `Pass2Score`.
4. Compute `source_credibility` via `credibility.compute_source_credibility`.
5. Compute `temporal_freshness` via `credibility.compute_temporal_freshness` (no `signal_horizon` argument — fixed 365-day window).
6. Write signal file to `signals/{yyyy}/{mm}/{dd}/{signal_id}.md`. If the file already exists (same `signal_id`), skip — idempotent.

**Verification:**

- A `fetch_full_text` failure drops the item silently — no partial signal file is written.
- Every written signal file has `full_text_fetched: true` in frontmatter.
- Re-running on the same items is a no-op (same `signal_id` → same path → file already exists).
- `candidate_themes` contains at most three entries, sorted by descending confidence, each with a `rationale`.
- `source_credibility` is `null` when no affiliations match the table.
- `temporal_freshness` reflects a 365-day linear decay — not the topic `signal_horizon`.
- Pass-2 ranking uses `applicability_score × source_credibility` as the primary axis; `temporal_freshness` is a tiebreaker/modifier only.
- A batch of pass-1 items can be scored end-to-end and produce valid signal files.

---

## Task 15.4 — Topic Storage Helpers And Layout Documentation

**Depends on:** Task 15.0 (seeds `overview.md`, `themes/`, `entities.json`, `timeline.json`, `open_questions.json`); Task 15.3b (defines the signal frontmatter schema that `storage.py` read/merge helpers must honour).

**Why this matters:** A strategic briefing product cannot rely on per-run summaries alone. It needs durable topic memory that persists across runs. The signal schema is already defined by 15.3b; this task adds the read/merge helpers that make it safely accessible to downstream stages, seeds the initial `hypotheses.json` and `evidence.json`, and documents the full flat layout.

**Changes:**

| File | Action | Description |
|---|---|---|
| `src/topics/storage.py` | **NEW** | Save/load helpers for topic files and run outputs (frontmatter-aware read/write, list/merge by stable id); signal helpers conform to the schema defined in 15.3b and support partial updates so 15.5 can write back `classification` and `theme_id_assigned`; evidence helpers expose a credibility-weighted `strength` increment with provenance append; open-question helpers expose a `count` increment with provenance append |
| `data/research_topics/README.md` | **UPDATE** | Document the flat layout from architecture §6, including signal schema reference to 15.3b |
| `data/research_topics/data_advantage/taxonomy.md` | **NEW** | First topic taxonomy |
| `data/research_topics/data_advantage/hypotheses.json` | **NEW** | Durable belief store for strategic topic hypotheses with prior/posterior state and a derived `convergence` score updated by 15.5 |
| `data/research_topics/data_advantage/evidence.json` | **NEW** | Evidence records linking claims to hypotheses; each record holds `id`, `claim`, `stance`, a `strength` counter (incremented per supporting signal, weighted by `source_credibility`), and a `provenance` list of `{signal_id, weight_applied}` entries |
| `data/research_topics/data_advantage/raw/` | **NEW** | Original fetched payloads, partitioned `{yyyy-mm-dd}/{source_name}{.xml/.html}` (native format, not coerced to JSON) |
| `tests/test_topic_storage.py` | **NEW** | Round-trip read/write for each file type; frontmatter preserved on update |

**Explicit non-goals:** This task does **not** create `overview.md`, `themes/`, `entities.json`, `timeline.json`, or `open_questions.json` — those come from 15.0. There is **no** `wiki/` subdirectory; the wiki is the flat human-readable tree, not a nested folder.

**Storage layout must support:**

- raw ingested items (`raw/`)
- scored signals (`signals/`)
- durable belief graph state (`hypotheses.json`, `evidence.json`)
- wiki state (flat: `themes/*.md`, `entities.json`, `timeline.json`, `open_questions.json`, `overview.md`); storage helpers now also do JSON load/merge by id (in addition to YAML frontmatter for themes/overview)
- generated briefings (`briefings/`)
- dossiers (`dossiers/`)

**The initial schema should make explicit:**

- hypothesis node fields for belief state, action posture, strategic rationale, dependency edges, linked evidence ids, and a derived `convergence` score updated by 15.5
- evidence record fields for `id`, `claim`, `stance`, a `strength` counter incremented per supporting signal (weighted by signal `source_credibility`; `null` credibility falls back to a neutral weight defined in 15.5 config), and a `provenance` list of `{signal_id, weight_applied}` entries
- open question record fields extended from 15.0 with a `count` of distinct signals that raised it and a `provenance` list of `{signal_id}` references
- dependency edges stored on hypothesis records rather than in a separate edge file

**Verification:**

- One topic folder can store a complete run end-to-end using the flat layout
- Wiki files are human-readable and editable
- The structure is reusable for another topic id
- Storage helpers preserve YAML frontmatter on partial updates (no drift)

---

## Task 15.5 — Hypothesis And Wiki Update Loop

Build the mechanism that turns newly scored signals into updated topic beliefs and an evolving thematic wiki.

**Why this matters:** The wiki layer is the human-readable product surface, but it should not be the only place where the system stores what it believes. Without a hypothesis update loop, the system remains a feed summarizer with nicer prose. With it, the system gains an explicit belief graph, evidence-weighted updates, and the ability to propagate changes into the briefing layer.

**Changes:**

| File | Action | Description |
|---|---|---|
| `src/topics/wiki_updater.py` | **NEW** | Reads pass-2 signals; for each top-confidence `candidate_theme`, classifies the contribution as `replication` / `adjacent` / `wholly_new` against the theme body; appends to themes (Markdown, anchor-stable); writes the resolved `classification` and `theme_id_assigned` back to the signal frontmatter so 15.6 can filter |
| `src/topics/hypothesis_updater.py` | **NEW** | Reads pass-2 signals; dedups `new_evidences` against `evidence.json` and increments `strength` (weighted by signal `source_credibility`; `null` credibility uses a configured neutral weight); attaches evidence to existing hypotheses or creates new ones; updates posterior belief state and per-hypothesis `convergence` from recent provenance |
| `src/topics/open_question_updater.py` | **NEW** | Dedups `new_open_questions` from pass-2 signals against `open_questions.json`; increments `count`; appends `signal_id` to provenance |
| `src/topics/entities.py` | **NEW** | Entity extraction or normalization helpers |
| `src/topics/timeline.py` | **NEW** | Append/update notable changes over time (substantive shifts only; replication does not append) |
| `src/topics/propagation.py` | **NEW** | Re-evaluates dependent hypotheses, theme sections, and briefing conclusions when hypothesis belief changes |
| `src/topics/anchors.py` | **NEW** | Stable `<a id="..."></a>` generation and resolution for adjacent-block linking (architecture §12) |
| `tests/test_wiki_updater.py` | **NEW** | Theme updates remain idempotent across replication, adjacent, and wholly_new cases; classification is written back to signal frontmatter |
| `tests/test_hypothesis_updater.py` | **NEW** | Support, weakening, opposing, and new-hypothesis cases update durable belief state correctly; strength increments scale with source credibility |
| `tests/test_open_question_updater.py` | **NEW** | The same question raised by two signals shows `count: 2` with both `signal_id`s in provenance |

**Hypothesis and wiki update logic should support:**

- recurring themes (continuous update, no "stale" concept per architecture §11); appends to `themes/*.md` (Markdown, anchor-stable)
- classification of signal-to-theme contribution: read each pass-2 signal's top `candidate_theme`; compare against the theme body; assign `replication` (no body growth), `adjacent` (append block + Markdown link to prior block's stable anchor), or `wholly_new` (standalone section + fresh anchor); write the resolved `classification` and `theme_id_assigned` back to the signal frontmatter
- evidence integration from `new_evidences`: dedup by stable id (e.g., claim hash + hypothesis_id); increment `strength` counter weighted by signal `source_credibility` (null → configured neutral weight); append `{signal_id, weight_applied}` to provenance
- hypothesis maintenance: attach new evidences to existing hypotheses; create new hypotheses when no match exists; update priors/posteriors; revise action posture based on accumulated evidence
- open questions maintenance: dedup `new_open_questions` against `open_questions.json` by stable id; increment per-question `count`; append `signal_id` to provenance; surfaced through `overview.md`
- convergence computation: for each updated hypothesis, derive `convergence` from recent supporting-signal density and stance alignment in evidence provenance
- entity and timeline updates: appends new entries by id to `entities.json` and `timeline.json` (timeline only on substantive shifts; replication does not append)
- belief graph maintenance: preserve dependency edges between supporting and dependent hypotheses
- bounded Bayesian-style updates: stronger credible evidence moves posterior more than weak anecdotal evidence; repeated independent confirmation matters; negative evidence lowers belief rather than spawning a separate contradiction object
- propagation rules: when a hypothesis changes meaningfully, re-evaluate dependent hypotheses and any briefing-facing conclusions they feed

The updater should treat `depends_on` as the canonical first-pass edge field unless the contract changes later.

**Verification:**

- A second run updates existing belief and wiki state instead of recreating it from scratch
- New items can extend an existing theme (`adjacent`) or create a new one (`wholly_new`); replication is reflected as no theme growth
- The resolved `classification` and `theme_id_assigned` are written back to the signal frontmatter
- The same open question raised by two signals shows `count: 2` with both `signal_id`s in provenance
- An evidence increment from a high-credibility paper moves posterior more than the same claim from a low-credibility paper
- Evidence against an existing hypothesis lowers posterior belief instead of only being mentioned in prose
- A changed hypothesis can update at least one dependent hypothesis or briefing-facing conclusion
- Timeline and watchlist are updated automatically and remain legible

---

## Task 15.5b — Hypothesis Revision And Propagation Evaluation

Build a focused evaluation suite for the hardest part of the system: whether knowledge updates actually propagate coherently.

**Why this matters:** A system has not really updated its knowledge if it can store new evidence but still briefs as though the old world is true. This task tests ripple effects directly so the product does not quietly degrade into a prose append-only log.

**Changes:**

| File | Action | Description |
|---|---|---|
| `tests/test_hypothesis_propagation.py` | **NEW** | Multi-step fixtures that verify support, weakening, opposition, convergence, and downstream propagation |
| `research_briefing/docs/specs/15_5b_hypothesis_revision_propagation.test.md` | **NEW** | Human-readable spec describing why ripple-effect failures matter to briefing quality |

**Evaluation cases should include:**

- a support case where new evidence strengthens an existing hypothesis
- a weakening case where new evidence lowers confidence without full replacement
- an opposition case where evidence against a current hypothesis lowers posterior belief
- a propagation case where changing one hypothesis updates a dependent hypothesis or briefing conclusion
- a convergence case where multiple weak signals together change belief state

**Verification:**

- belief state changes are visible in durable files, not only theme prose
- downstream derived outputs change when upstream beliefs change
- opposing evidence remains visible in the hypothesis history and affects posterior belief

---

## Task 15.6 — Output Generation: Daily Tweet

Build the `output/` package and implement the first renderer: daily tweet candidates from each day's wiki changes, included in the daily PR.

**Why this matters:** The system's purpose is to help technical decision-makers allocate attention and investment — combining fresh signals with accumulated topic memory to produce a strategically framed take, not a paper summary. The tweet is the current output format for that take; the `output/` package is designed so future formats (weekly tweet, monthly Substack post) can be added by implementing one interface, with no changes to the wiki or scoring layers.

**Changes:**

| File | Action | Description |
|---|---|---|
| `src/output/__init__.py` | **NEW** | Output package |
| `src/output/base.py` | **NEW** | `OutputRenderer` interface: `render(signals, wiki_state, topic_config) → OutputArtifact`; defines the contract all renderers must satisfy |
| `src/output/daily_tweet.py` | **NEW** | First renderer: generates tweet candidates from signals classified by 15.5 (`adjacent` / `wholly_new` only); derives `strategic_significance` from current wiki state; derives `action` from audience match between `paper_audience` and `topic.md.audience`; applies `daily_tweet_limit` top-N filter; writes `tweets/{yyyy-mm-dd}.json` |
| `data/research_topics/data_advantage/tweets/` | **NEW** | Per-day tweet candidate files |
| `tests/test_output_daily_tweet.py` | **NEW** | Fixture scored signals → expected tweet JSON shape; only `adjacent` and `wholly_new` signals produce candidates; `replication` signals are skipped; idempotent on re-run |

**Output contract (`tweets/{yyyy-mm-dd}.json`):**

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

**Generation rules:**

- Only signals with `classification: adjacent` or `classification: wholly_new` (written back by 15.5) generate candidates — replication is not worth surfacing
- Daily top-N filter: at most `daily_tweet_limit` candidates per day (configurable in `topic.md`, default `1`); ranked by `applicability_score` × `source_credibility` × audience match between `paper_audience` and `topic.md.audience`
- One candidate per signal at most; the renderer may skip a signal if the underlying hypothesis update is not independently worth a tweet
- `strategic_significance` is derived at render time from current wiki state (e.g., did the signal flip a hypothesis posterior, retire an open question, or extend a high-priority theme)
- `action` text is derived from `paper_audience` × `topic.md.audience` match — phrased as a direct hook to the reader (e.g., "if you've been on the lookout for high-quality non-verifiable reward data, this is worth a look"), not a generic verb
- Text must be derivable from the signal and the relevant theme — no hallucinated context
- Each candidate must address: what changed, how it fits the landscape, why it matters for the audience

**Verification:**

- A batch of scored signals produces a valid `tweets/{yyyy-mm-dd}.json`
- Replication-only signals produce no candidates
- Daily output is capped at `daily_tweet_limit` (default `1`)
- `action` text references audience interest derived from `paper_audience` × `topic.md.audience` match
- Re-running on the same signals is idempotent (no duplicate ids)
- A second renderer can be added under `output/` without touching `daily_tweet.py`, `wiki_updater.py`, or `scoring.py`

---

## Task 15.7 — Editorial Review Workflow

Define the minimum human-in-the-loop workflow for reviewing wiki updates and tweet candidates.

**Why this matters:** The differentiator is judgment, not autonomous automation. The review surface is the daily PR: one PR per topic per day opened by the ingestion agent after all sources are processed. The human reviews wiki diffs and tweet candidates in a single pass; merging = approval.

**Changes:**

| File | Action | Description |
|---|---|---|
| `research_briefing/docs/editorial_review_workflow.md` | **NEW** | Review steps for signals, wiki updates, and tweet candidates |
| `research_briefing/docs/data_advantage_brief.md` | **REF** | Editorial standard and audience promise |

**Workflow should define:**

- daily PR structure: what the PR body must contain (new/updated/overwritten claims, sources added, open questions retired, tweet candidates)
- agent overwrite policy: agent may overwrite existing wiki content; human reviews the diff and pushes back before merging if needed
- how source traceability is checked
- how false positives are corrected
- how wiki drift is repaired
- tweet approval: `tweets/{yyyy-mm-dd}.json` entries are reviewed in the same PR; status set to `approved` or `rejected` before merge

**Verification:**

- A single review pass can correct a bad signal and preserve the correction
- The workflow is lightweight enough for one operator
- Tweet publication is gated on human review, not raw generation

---

## Task 15.7b — Comment Loop Infrastructure

Build the GitHub Actions workflow and context assembly script that let the human request targeted wiki edits from a PR comment.

**Why this matters:** The daily PR is the review surface, but it is not always enough to merge as-is. The comment loop is what makes the PR interactive — the human can push back on a claim, request a cross-file reconciliation, or sharpen a tweet candidate, and the agent commits a corrected version to the branch before the merge decision.

**Changes:**

| File | Action | Description |
|---|---|---|
| `.github/workflows/pr-comment.yml` | **NEW** | Triggers on `issue_comment` events; checks for trigger phrase (`@agent`); assembles context; calls Gemini API; commits result to the PR branch |
| `scripts/pr_agent.py` | **NEW** | Context assembly + Gemini API call: always fetches the three reference JSONs (`entities.json`, `open_questions.json`, `timeline.json`), fetches any theme files named in the comment, builds the prompt, applies the response as a file edit |
| `research_briefing/docs/editorial_review_workflow.md` | **UPDATE** | Document the comment convention: `@agent <instruction> — see themes/<theme_id>.md` |

**Context assembly rules:**

- Always include: `entities.json`, `open_questions.json`, `timeline.json` — small, stable, always relevant
- Theme files: fetched only if named explicitly in the comment (`— see themes/filtering-and-curation.md`); not guessed, not passed wholesale
- PR diff: always included as the primary context for what the comment is responding to

**Comment convention:**

```
@agent reconcile this with the FineWeb claim — see themes/filtering-and-curation.md
@agent sharpen the strategic framing on tweet 3
@agent this entity description is stale — update entities.json
```

The naming convention is not extra cognitive work: the reviewer already knows which theme is relevant because they just read the diff.

**Verification:**

- A comment with `@agent` and no theme reference triggers the workflow and uses only the diff + reference JSONs
- A comment naming a theme file fetches that file and includes it in context
- The agent's edit is committed to the PR branch, not to main
- A comment on a non-PR issue does not trigger the workflow

---

## Task 15.8 — First End-To-End Slice: Data Advantage

Deliver the first narrow topic slice using the new architecture. **Assumes Task 15.1b** has already seeded `data_advantage` from a dossier so the graph is not cold.

**Why this matters:** The architecture only matters if it can produce one real topic output end-to-end. "Data advantage" is the first proving ground, not the permanent hard-coded direction.

**Changes:**

| File | Action | Description |
|---|---|---|
| `data/research_topics/data_advantage/` | **UPDATE** | First live topic workspace; seeded by 15.0, extended by 15.1–15.6 |
| `docs/specs/15_knowledge_management_briefing_engine.test.md` | **NEW** | Human-first validation test for the first topic slice |
| `tests/test_research_topic_pipeline.py` | **NEW** | Focused automated test for config → normalize → score → wiki → tweets flow |

**End-to-end slice should prove:**

- one topic config works
- at least two source classes ingest successfully
- wiki state updates across runs
- tweet candidates are generated and included in the daily PR

**Verification:**

- One end-to-end run completes locally from topic config to tweet candidates
- The topic can be changed by swapping config and taxonomy files, not rewriting orchestration
- The resulting output is useful enough to review and publish

---
