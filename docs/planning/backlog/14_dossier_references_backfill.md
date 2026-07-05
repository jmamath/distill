# Plan 14 — Dossier References And Historical Backfill

**Introduced:** 2026-06-09 — newly created; not part of the original 15.x task breakdown. Surfaced by the open-questions→hypotheses refactor: bootstrap now seeds hypotheses at a uniform `Beta(1, 1)`, which discards the literature the deep-research dossier was synthesized from.

**Depends on:** Plan 7 pass-2 pipeline (the backfill driver reuses `pass2_score` and the full-text fetch paths); Plan 1 bootstrap dossier contract (`prompt.py`, `parser.py` — this plan extends it); Plan 9 `hypothesis_updater` (turns backfilled signals into evidence; backfill can write signals before Plan 9 lands, but the belief graph only moves once the updater consumes them).

---

Make the dossier carry a machine-addressable bibliography, then replay those references through the existing pass-2 pipeline as dated signals — so the belief graph starts from provenanced, credibility-weighted evidence instead of pretending we know nothing.

**Why this matters:** The bootstrap deep-research pass reads hundreds of references and then collapses all of it into uniform-prior hypotheses that assert *we know nothing*. That is both false and mechanically harmful: from `Beta(1, 1)`, the first few live signals swing a posterior violently, so the belief graph is biased toward whatever arrives first — and live ingestion delivers recent items first. Backfill closes that window with the machinery we already have: replayed references become ordinary signals, the updater attaches ordinary evidence, and the hypotheses start with real mass before live ingestion begins.

## Sequencing

For a fresh topic: bootstrap → backfill → enable live ingestion. This ordering is what eliminates the first-arrival bias: by the time live signals land, well-supported hypotheses already carry enough mass that one new paper nudges rather than swings them — while genuinely open questions stay near-uniform because the literature gave them no one-sided support.

`hypotheses.json` and `evidence.json` schemas are unchanged from Plan 8: bootstrap still seeds `Beta(1, 1)` and never writes evidence. Backfill produces evidence the same way live ingestion does — through signals — so there is no separate belief contract and no double-counting path.

---

## Sub-task A — Dossier references contract

Extend the dossier JSON so every bootstrap carries a replayable bibliography by construction.

### Changes

| File | Action | Description |
|---|---|---|
| `src/topics/bootstrap/prompt.py` | **UPDATE** | Add a `references` array to the dossier JSON schema: per entry an identifier (arXiv id or URL), title, and a publication date; instruct the agent to list the works its themes and hypotheses actually draw on. arXiv ids preferred, but other PDFs and article URLs are welcome — anything that resolves to a fetchable document |
| `src/topics/bootstrap/parser.py` | **UPDATE** | `DossierReference` model; `DossierPayload.references` (default empty so existing dossiers still parse); validate shape, dedup by id/URL |
| `tests/test_bootstrap_parser.py` | **UPDATE** | A dossier with `references` parses and dedups; a dossier without `references` still parses (backward compatibility) |

The seeder is untouched: references live in the dossier JSON, and the dossier is already archived under `dossiers/` — the backfill driver reads them from there. No new storage file, no schema change to `hypotheses.json` or `evidence.json`.

Exact reference fields are pinned at the `doing/` boundary. The minimum the driver needs is an identifier, a title (the verification anchor — see sub-task B), and a `published_at` date (signals partition by it and freshness derives from it).

---

## Sub-task B — Backfill driver (replay)

Replay the dossier's references through the existing full-text + pass-2 machinery as dated signals.

### Changes

| File | Action | Description |
|---|---|---|
| `src/topics/backfill.py` | **NEW** | Backfill driver: takes a parsed dossier, routes each reference to a fetch path by identifier, builds a `NormalizedItem`, and feeds it to `pass2_score` with a synthetic `Pass1Score` — no pass-1 gate. Verifies each fetch against the reference title. References that resolve to no document route are skipped and counted |
| `scripts/backfill_references.py` | **NEW** | Operator CLI: `--topic` + `--dossier`; prints written/skipped/already-present/title-mismatch counts; supports `--limit` for a cheap first run |
| `tests/test_backfill.py` | **NEW** | Route selection per identifier; synthetic pass-1 bypass; title-mismatch is flagged not written; unfetchable references skipped-and-counted; idempotency on re-run (existing `signal_id` → skip) |

### Mechanics

- **Pass-1 is bypassed.** Pass-1 is a cheap relevance gate for unsolicited feed items; dossier references were hand-picked by the research agent for this exact topic. The driver constructs a synthetic `Pass1Score` (the `smoke_pass2.py --pass 2` path already demonstrates this) so `pass2_score`'s signature is reused unchanged.
- **Not arXiv-only.** Most non-arXiv references are still fetchable documents — PDFs (Nature/CVPR/NeurIPS papers) or HTML articles (lab and company blogs) — and the full-text machinery from Plan 7 already handles both: a PDF goes to Gemini with `application/pdf`, an article is fetched and stripped to text. The driver routes each reference by its identifier: arXiv id → arXiv PDF path; PDF URL → PDF path; article URL → HTML-strip path. Only references that are genuinely not documents — court dockets, code repositories, bare dataset releases — are skipped, counted, and reported. (Routing a generic PDF/article through the existing source-specific adapters may need a thin generalization of their fetch methods; pinned at `doing/`.)
- **Title-match is the verification gate.** Because the driver fetches by identifier and recovers the real title, a hallucinated or transposed id either 404s or returns a title that does not match the reference — both flagged and reported, never silently written as a wrong signal. This is what makes a recovered (model-supplied) bibliography safe to replay without hand-verifying every id.
- **Old papers accrue full evidence mass.** `signals/` partitions by `published_at`, and evidence `strength` is credibility-weighted, not freshness-weighted; `temporal_freshness` will read near 0 for old papers, which is correct and affects ranking, not belief.
- **Idempotent and dedup-safe against live ingestion.** `signal_id` is deterministic from the URL, so re-running backfill skips existing signals — and a backfilled paper that later arrives via RSS is the same signal, not a double count.
- **Evidence attachment is Plan 9's job.** Backfill stops at written signal files. The `hypothesis_updater` consumes them exactly as it consumes live signals; no backfill-specific path exists in the updater.

---

## Sub-task C — Migrate the recovered references into the existing dossier

The current data-advantage dossier predates the references contract and retained no bibliography. We recovered one by asking the deep-research model for its reference list — saved as `data/research_topics/data_advantage/dossiers/references.md` (themed Markdown tables of `arXiv id | title`, plus explicit non-arXiv entries, with low-confidence ids prefixed `~`). This sub-task folds that recovery into the dossier so it replays through sub-task B — and is the first real exercise of sub-task A's contract.

### Changes

| File | Action | Description |
|---|---|---|
| `data/research_topics/data_advantage/dossiers/bootstrap_2026_04_22.md` | **UPDATE** | Add a `references` array to the dossier's trailing JSON block, converted from `references.md`; re-validate the whole dossier through `parse_dossier` |
| `scripts/migrate_references.py` | **NEW** (optional) | One-shot converter: parses `references.md` tables into reference records and emits the JSON array. May be a throwaway if done by hand |

### Conversion rules

- Strip the `~` confidence markers — the title-match gate in sub-task B is what verifies an id, so per-id manual confidence is unnecessary; a wrong id surfaces as a mismatch at fetch time.
- Carry `title` through verbatim — it is the verification anchor.
- Drop the per-theme grouping into a flat array; the theme attribution is not needed for replay (evidence-to-hypothesis attachment is Plan 9's job, driven by the signal's own scored content, not by the reference's source theme).
- Cross-theme duplicates (COCO, Visual Genome, Segment Anything, PRM800K, OpenThoughts appear under two themes) collapse to one record — and would dedup to a single `signal_id` even if they did not.
- `non-arxiv` entries that are documents (the AlphaFold *Nature* papers, blog posts) become URL-identified references so they replay; entries that are not documents (the court cases, GitHub repos, bare dataset releases) are recorded for auditability but will skip at replay. Each needs a `published_at` — recover it from the dossier `timeline` where the work appears, else the known publication year.

### Verification (sub-task C)

- The updated `bootstrap_2026_04_22.md` re-validates through `parse_dossier` with a populated `references` array.
- Running the sub-task B driver over it writes signal files for the arXiv and other-document references and reports the non-document ones as skipped — with a title-mismatch count that flags any bad recovered id.

---

## Downstream: from backfilled signals to beliefs

Backfill stops at signal files. Two existing consumers turn those signals into durable belief and wiki state, and neither is part of this plan — they run identically over backfilled and live signals:

```
backfill → signals/{yyyy}/{mm}/{dd}/*.md   (claims already scored into `new_evidences` frontmatter)
   → hypothesis_updater (Plan 9): for each claim, dedup against evidence.json, increment
     strength + append provenance (via the Plan 8 storage helpers), attach to a matching
     hypothesis and move its Beta — or mint a new uniform-prior hypothesis when nothing
     matches; routes non-evidence facts to entities.json / timeline.json
     → writes evidence.json AND hypotheses.json in one pass
   → wiki_updater (Plan 17, parallel sibling): folds the same signals into themes
     (with an append-only decision log)
```

Note this is two conceptual stages, not three: the storage layer (Plan 8) is **not** a separate step that produces `evidence.json` on its own. It is the frontmatter-aware read/merge/write helper library the updater *calls*; the updater is what reads signals and writes both `evidence.json` and `hypotheses.json`.

Backfill produces *evidence claims*, not hypotheses — ~200–300 `new_evidences` across 100 papers, not 200 hypotheses. Whether a backfilled claim thickens an existing bet or spawns a new one is the updater's call; the resulting hypothesis granularity is governed in Plan 9 (see §6 · Granularity there), not here.

## Verification (plan-level)

- The bootstrap prompt instructs the agent to emit `references`; `parse_dossier` accepts a dossier with them and (for backward compatibility) without them.
- Running the backfill driver on a dossier with N fetchable references writes up to N signal files under the correct `published_at` partitions, with no pass-1 calls made.
- A reference whose fetched title does not match the listed title is flagged and not written; non-document references are reported as skipped — neither is silently dropped.
- Re-running the driver is a no-op (same `signal_id` → same path → skip); subsequently ingesting one of the same papers live creates no duplicate signal.
- *(The post-backfill belief-health check — that hypotheses supported by the literature carry visibly more evidence mass than genuinely open ones, every unit traceable to a `signal_id` in provenance — moved to Plan 9 Sub-task D, which owns the belief-graph evals. It cannot be verified without Plan 9's updater, so it does not belong here.)*
- `hypotheses.json` and `evidence.json` schemas are unchanged from Plan 8; bootstrap still seeds `Beta(1, 1)` and never writes evidence.
