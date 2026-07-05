# Plan 9 — Hypothesis Update Loop (Belief Graph)

**Original task ids:** 15.5 (Hypothesis Update Loop — belief half), 15.5b (Hypothesis Revision And Propagation Evaluation)

**Split note (2026-06-29):** This plan was originally "Hypothesis And Wiki Update Loop" and covered both the belief graph and the wiki renderer. It was split so each subsystem can be built and proven on its own. This plan owns the **belief graph**. The **wiki renderer** — the old §5 wiki-novelty decision, theme growth, and anchors — is now **Plan 17**. The two are parallel siblings: they consume the same pass-2 signals through the shared signal contract and never call each other.

**Timeline note (2026-07-05):** `timeline.json` writes also live in Plan 17, not here. A dated fact earns a timeline entry only when it grows a theme, and that verdict — the novelty call — is the renderer's. This plan's route branch writes `entities.json` only.

---

Build the mechanism that turns newly scored signals into updated topic beliefs, then prove that those updates propagate coherently.

**Why this matters:** The system should not only store new evidence — it must let that evidence move what it believes. Without a hypothesis update loop, the system stays a feed summarizer: it can file a new result but still reasons as though the old world holds. So this plan tests ripple effects directly — that a new claim moves the right belief, and that the move propagates to everything depending on it — to keep the product from quietly degrading into an append-only log of unconnected results.

---

## §1 · What this plan does

Each signal is exploded into the claims it carries. The belief graph makes **two decisions per claim, plus the mechanics they trigger** — all *below* the paper level:

- Decision 1 (**triage**, §2) asks *where does this claim go?* — attach to an existing hypothesis, open a new one, or route out as a non-evidence fact (a dataset, benchmark, or model release).
- Decision 2 (**resolve stance**, §3) asks *which way does it cut?* — support, oppose, or mixed — and runs only when Decision 1 said attach or open.

Everything else is **mechanics, not decisions** — deterministic logic that fires on its own once a decision is made: the belief update, the routed-fact writes, and propagation (§4). The mechanics call the shared `storage` module, which owns load/save, merge-by-id, the credibility-weighted `strength` increment, and the Beta update. **This plan owns the decisions and orchestrates the mechanics; `storage` owns the merge/Beta machinery.** That split is stated here once and not repeated below.

A signal carries one further decision — *is each claim new to the theme it touches?* — but that is the **wiki renderer's** job, now **Plan 17**. The renderer reads the same signals independently and never reads this plan's `hypotheses.json`; the two stay decoupled through the signal contract.

```mermaid
flowchart TB
    sig[("signals/*.md<br/>(pass-2 output)")]:::data

    subgraph perclaim["Per claim"]
        direction TB
        d1{{"§2 · Decision 1 — Triage<br/>where does this claim go?<br/>attach · open new · route out"}}:::llm
        d2{{"§3 · Decision 2 — Resolve stance<br/>support · oppose · mixed<br/>(attach / open only)"}}:::llm
        belief["§4 · Update belief (mechanics)<br/>strength × credibility · Beta(α,β)"]:::det
        prop["§4 · Propagate (mechanics)<br/>re-evaluate dependents · CI-weight"]:::det
        route["§4 · Route non-evidence (mechanics)<br/>dataset / benchmark / model release"]:::det
    end

    store["shared storage module<br/>load / save · merge by id · strength increment · Beta update · neutral fallback weight"]:::store
    done["write belief_processed_at<br/>(once all the signal's claims are done)"]:::det

    sig --> d1
    d1 -->|attach / open| d2
    d1 -->|route| route
    d2 --> belief --> prop
    belief --> store
    prop --> store
    store --> hyp[("hypotheses.json")]:::data
    store --> ev[("evidence.json")]:::data
    route --> ent[("entities.json")]:::data
    perclaim --> done
    done -. "stamps signal done<br/>for this subsystem" .-> sig

    renderer["Plan 17 · wiki renderer<br/>(parallel sibling — reads the same signals,<br/>never reads hypotheses.json)"]:::ext
    sig -.-> renderer

    classDef llm fill:#fdeecf,stroke:#b9821f,color:#5c3d00;
    classDef det fill:#d9f2e6,stroke:#1a7f52,color:#0b3d26;
    classDef store fill:#dbe9fb,stroke:#2b6cb0,color:#0b2d52;
    classDef data fill:#eeeeec,stroke:#9a9a96,color:#333333;
    classDef ext fill:#f3e8fd,stroke:#7c3aed,color:#3b0764;
```

*Amber = a model call (a judgment) · green = deterministic mechanics this plan owns · blue = the shared `storage` module · grey = files on disk · purple = the parallel renderer (Plan 17).*

---

## Sub-task A — Hypothesis Update Loop

One entry-point module drives the loop. `hypothesis_updater.py` reads pass-2 signals and runs the two per-claim decisions (§2, §3), then the mechanics they trigger (§4). The shared `storage` module owns the merge/Beta mechanics that §4 calls.

**Reading and stamping signals is shared with the renderer.** Both this plan and Plan 17 read pass-2 signals and write a small "done" stamp back to the signal frontmatter — this plan writes `belief_processed_at`, the renderer writes `classification`. So the `SignalFrontmatter` model and the signal read/write helper are **shared infrastructure**, owned by neither subsystem: they live in a neutral module both import (the Plan 8 `storage` module, or a small new `signals.py` — pinned at the `doing/` boundary), and each subsystem writes only its own stamp field. A run of this plan consumes the signals missing `belief_processed_at`; writing that stamp is the **last** step for a signal, so a crash mid-signal leaves it unstamped and the next run safely re-opens it. The per-claim dedup keyed on `claim hash + hypothesis_id` is what stops an already-attached claim from counting twice on that re-open — so the stamp can stay one mark for the whole signal rather than one per claim. The two subsystems run in either order but never concurrently: both read-modify-write the same signal frontmatter for their stamps, and interleaved runs could silently drop each other's stamp.

Each section below opens with the new files it introduces, so a file's responsibility is read where it is explained.

### §2 · Decision 1 — Triage: where does this claim go? (per claim)

**Every claim runs through triage first.** Pass-2 hands over each claim as `{claim, stance}` with **no hypothesis attached** (see Plan 7's `Pass2Score`), so triage classifies the claim into exactly one branch.

| File | Action | Description |
|---|---|---|
| `src/topics/hypothesis_updater.py` | **NEW** | The updater entry point; reads pass-2 signals and runs Decision 1 and Decision 2, then the mechanics in §4 |
| `tests/test_hypothesis_updater.py` | **NEW** | Triage branches; stance cases; `strength` scales with source credibility; a new uncertainty creates a uniform-prior hypothesis |

The branches:

- **Attach** — the claim bears on an existing hypothesis. Match it against `hypotheses.json` and pick the one it speaks to. The signal's `candidate_themes` are a natural prefilter: a claim most plausibly bears on hypotheses sharing its theme. Dedup by stable id (`claim hash + hypothesis_id`) so the same claim re-matched to the same hypothesis attaches once. → resolve stance (§3), then the belief update (§4).
- **Open a new hypothesis** — nothing matches, but the claim is worth its own bet. Open a uniform-prior `Beta(1, 1)` hypothesis. **This is also how a genuinely new uncertainty enters the store** — there is no separate `open_questions.json`; an "open question" is just a low-evidence hypothesis near its prior, and surfacing one as such is Plan 10's read-time composition (`overview.md` is retired — no stored landing page gets updated). → resolve stance (§3), then the belief update (§4).
- **Route out** — nothing matches and the claim is not worth a bet, but it is a fact worth keeping: a new dataset, benchmark, or model release. It is not evidence. → the routed-fact write (§4). If it is not even that, drop it.

*How finely* to split the questions the system tracks — open a new hypothesis, or attach to an existing one — is the granularity question, resolved in **§6**.

- **Open —** the **matching mechanism** is the hinge of the whole loop and is undecided (LLM judgment over candidate hypotheses, embedding similarity, or theme-prefiltered LLM). The dedup id depends on the matched `hypothesis_id`, so this must be settled first. The rule that separates a "belief-irrelevant fact worth keeping" from a "drop," and the `entities.json` record schema (seeded by Plan 1, not restated anywhere this plan can build against), are open alongside it. Decide at the `doing/` boundary. The model-contract side of this judgment lives in "The model-judgment surface" below.

**Verify.** *(`[det]` = deterministic, asserts exact behavior; `[llm]` = model judgment, verified by eval cases and blocked until the model-judgment gate closes.)*
- **`[det]`** An unmatched, bet-worthy claim opens a uniform-prior `Beta(1, 1)` hypothesis — the same path by which a genuinely new uncertainty enters the store.
- **`[det]`** Claim-level dedup is keyed on `claim hash + hypothesis_id`: the same claim re-matched to the same hypothesis attaches once, not twice (signal-level no-double-count is a loop invariant — see the end).
- **`[llm]`** A non-evidence fact (dataset / benchmark / model release) is routed out, not attached as evidence; a bet-worthy unmatched claim opens a hypothesis rather than being routed or dropped.

### §3 · Decision 2 — Resolve stance: which way does it cut? (per claim, attach / open only)

**Once a claim is evidence — attached or opening a new bet — resolve its stance against *that* hypothesis.** The pass-2 `stance` describes the claim's own framing, not its bearing on the matched hypothesis, so it must be re-read once the hypothesis is named: a claim emitted `for` its own framing can be `against` the bet it attaches to.

A `neutral` verdict is **never stored as inert evidence**. Surfacing a claim against a *specific* hypothesis already implies a direction, so each "neutral" candidate is really one of — directional once the bet is named (`for`/`against`), a null / "no difference" result (`against` a directional bet), or conflicting (`mixed`). A claim that is genuinely belief-irrelevant was not evidence in the first place and should have routed out in Decision 1, not arrived here. So this step always collapses to `for | against | mixed`; the updater never writes a `neutral` row in `evidence.json` and never calls the belief-update helper for one. (Plan 8 keeps a `neutral` → no-op branch as defensive insurance against a stray value; the pass-2 `Evidence` enum is a shipped contract and stays unchanged — the filtering lives here, where the hypothesis is known.)

**Wrinkle on the open branch.** When a claim *opens* a new hypothesis, the new bet is framed so its founding claim supports it, so stance here is almost always `for` by construction. The interesting re-resolution happens on the **attach** branch, where the claim meets a hypothesis it did not create.

- **Open —** re-resolution is a model judgment; its prompt/model contract is specified in "The model-judgment surface" below.

**Verify.**
- **`[llm]`** Stance is re-resolved against the *matched* hypothesis, not copied from pass-2: a claim emitted `for` its own framing can resolve `against` the bet it attaches to, and a `neutral` candidate collapses to `for`/`against`/`mixed` — no `neutral` row is ever written to `evidence.json`.

### §4 · Mechanics — update belief, route the fact, propagate (deterministic)

**These are consequences, not decisions.** Once Decision 1 picks a branch and Decision 2 resolves stance, the following run as deterministic code — no model calls.

| File | Action | Description |
|---|---|---|
| `src/topics/entities.py` | **NEW** | Entity extraction / normalization for routed facts |
| `src/topics/propagation.py` | **NEW** | Re-evaluates dependents when belief moves; derives each edge weight as the credible-interval lower bound (multi-step tests live in Sub-task B) |

**Update belief** (attach / open branches). Increment `strength` weighted by the signal's `source_credibility` (`weight_applied = source_credibility / 10`; `null` credibility → `NEUTRAL_CREDIBILITY_WEIGHT`), append `{signal_id, weight_applied}` to provenance, and apply the Beta update through `storage` (`alpha += strength` for `for`, `beta += strength` for `against`, split for `mixed`). Updates are bounded and Bayesian-style: stronger credible evidence moves the posterior more, and negative evidence lowers belief rather than spawning a separate contradiction object.

- **Open —** the plan says to "revise action posture based on accumulated evidence" but gives no belief→`action_posture` mapping. Decide whether posture is recomputed here or is a read-time rendering, and on what rule.
- **Open —** convergence (whether recent evidence agrees or conflicts) is unreconciled with Plan 8, which treats the convergence *label* as a read-time derivative of `alpha`/`beta` and stores nothing. Before building, settle three axes: is convergence **stored or derived at read time**, computed **from `alpha`/`beta` or from provenance**, and over what "recent" window? Its behavioral case lives in Sub-task B.

**Route the non-evidence fact** (route branch). Append to `entities.json` (by id). The timeline is not written here: a dated fact earns a `timeline.json` entry only when it grows a theme, and that verdict is the renderer's — timeline writes live in Plan 17 (see the timeline note at the top).

**Propagate** (after a belief move). When a hypothesis moves meaningfully, re-evaluate its dependents, discounting weak dependencies automatically. `depends_on` is the canonical first-pass edge field. The weight on each edge is derived at propagation time as the lower bound of the dependency's credible interval — `scipy.stats.beta.ppf(DEPENDENCY_WEIGHT_PERCENTILE, α, β)`, with `DEPENDENCY_WEIGHT_PERCENTILE = 0.05` a named constant (raise for more conservative propagation, lower for more aggressive). A dependency with mean 0.71 but only 3.5 units of accumulated evidence yields ≈0.30 rather than 0.71 — fragile beliefs are discounted without any hand-authored weight.

Comparative hypotheses are handled as **pairwise edges**: a hypothesis naming two subjects (`comparison: {subject_a, subject_b}`, see Plan 8) accumulates its own Beta over observed head-to-heads. A new contender adds new edges rather than rebuilding anything, and **no global ranking is stored** — a "who leads" view is *derived* at read time. Cycles among comparisons (A>B, B>C, C>A) are valid data (conditional dominance), not contradictions to resolve.

- **Open —** the edge *weight* is fully specified but the *operation* is not: how the parent's change, the `supports`/`weakens` sign, and that weight actually modify the dependent's `alpha`/`beta`; what counts as a "meaningful" change worth propagating; and whether propagation recurses transitively (and if so, how it terminates, since `depends_on` can cycle). Pin these down before building.

**Verify.**
- **`[det]`** A high-`source_credibility` increment moves the posterior more than the same claim from a low-credibility paper (`weight_applied = source_credibility / 10`; `null` → `NEUTRAL_CREDIBILITY_WEIGHT`).
- **`[det]`** An `against` claim lowers posterior belief (raises `beta`) rather than only being mentioned in prose.
- **`[det]`** A routed fact lands in `entities.json` (by id) instead of being dropped. (Timeline appends are Plan 17's mechanics — a dated fact enters the timeline only by growing a theme.)
- **`[det]`** A meaningful belief move updates at least one dependent hypothesis or briefing-facing conclusion; the edge weight is the credible-interval lower bound (mean 0.71 with 3.5 units of evidence → ≈0.30, not 0.71). Multi-step ripple, convergence, and comparative cases live in Sub-task B (`tests/test_hypothesis_propagation.py`).
- **`[det]`** Convergence reflects agreement vs conflict in recent evidence — **blocked** on the stored-vs-derived decision (Open, above).

### §6 · Granularity — how finely to split the questions the system tracks

§6 settles one thing: **how finely the system splits the questions it keeps an opinion on.** A topic is never one question. For deduplication, "does dedup help at all?" is one bet; "is fuzzy matching better than exact?" is a different bet; "is per-dump dedup better than global?" is a third. Every question the system opens as a hypothesis is one it can hold an opinion on. Every question it never opens is one it can never answer — even after reading the paper that settles it.

**The resolution: separate a result from a question, then open freely and link.** Setting aside the non-evidence facts that route out (§2 — a dataset or benchmark release), each *evidential* claim is one of two things.

- A **result** — a measurement the paper reports, e.g. "exact dedup of C4 raised accuracy 2%". A result is *evidence*: it attaches to the hypothesis whose question it speaks to and moves that opinion. It does not become a hypothesis of its own. A hypothesis named after a single measurement is a dead end — nothing else will ever attach to it.
- A **standing question** — something the field genuinely disagrees on, e.g. "is fuzzy better than exact?". This is worth its own hypothesis, even when only one claim speaks to it so far. "A standing question the field disagrees on" is the plain-language form of Plan 8's **betting-market test** (resolvable + strategically significant); the per-claim call below applies that same bar at ingestion time that Plan 8 applies when authoring the seed hypotheses.

Two rules stop this from spiralling:

- **A thinly-evidenced hypothesis is fine.** A bet with one piece of evidence is just a weakly-held opinion sitting near its starting point — which is exactly what §2 already calls an "open question." A store full of many weakly-held opinions is honest, not broken. Sparsity is expected here, not a failure.
- **A narrow hypothesis links to the broader one it sits under** (`depends_on`). "Fuzzy beats exact" sits under "dedup helps." That link does real work: if the broad premise ever collapses — strong evidence that dedup actually hurts — §4 propagation discounts the narrow bets automatically, instead of leaving them standing as live questions about a dead premise. The link is also what keeps a narrow hypothesis from being an orphan: it hangs off a parent.

The rule, in one line: open a hypothesis whenever a claim names a real question, keep results as evidence, let the store be sparse, and link narrow bets to the broad ones above them. A complementary lever from Plan 1: seeding more parent hypotheses up front gives narrow claims something to attach to, so the updater opens fewer brand-new bets.

**The two failure modes this avoids** — most visible when Plan 14 backfill replays a dossier's references as one large batch (~200–300 claims across ~100 papers against ~10 seeded hypotheses):

- **Too coarse:** every claim piles onto the same few broad hypotheses. "Does dedup help" climbs, but "fuzzy vs exact" and "per-dump vs global" — the specific questions — vanish into it. Well-evidenced, but unable to answer anything specific. *Avoided by* giving a real question its own hypothesis.
- **Too fine:** a hypothesis is opened for every measurement. The store fills with dead one-liners ("exact dedup of C4 gives 2%") that no later claim will ever join. *Avoided by* keeping results as evidence, not bets.

**Still open — two judgments to specify before building.**

1. **The per-claim call.** For each claim: is this a result (evidence) or a standing question (a new bet)? And if it bears on a bet that already exists, which one? This is the matching judgment §2 and the model-judgment surface below already flag — the loop's largest gap to close.
2. **Cleaning up duplicates.** Opening freely will sometimes open two hypotheses for the same question under different wording ("fuzzy beats exact" and "shard-local beats corpus-wide"). The plan accepts this on the way in and folds duplicates together in a later batch pass, rather than trying to prevent it on every claim. That pass is not yet specified: what flags two hypotheses as candidates to merge, how a merge is confirmed, and its safety rules — never merge two hypotheses that *disagree* (same subjects, opposite finding), and keep every merge reversible.

**Acceptance gate (not a test).** Both judgments above are recorded in this plan (or its `doing/` spec) before implementation, and the result demonstrably avoids both failure modes on the Plan 14 backfill batch — checked by Sub-task D: specific questions keep their own hypotheses (no flattening), and the store does not fill with one-measurement hypotheses (no dead one-liners).

### The model-judgment surface (cross-cutting)

Two of the loop's steps are model calls, not deterministic code — the amber nodes:

1. **Triage / matching** (§2) — which hypothesis a claim bears on, or whether it routes out. (Whether matching and route-out are one model call or two is itself an implementation detail to settle.)
2. **Stance re-resolution** (§3) — the claim's bearing on the named hypothesis.

(The wiki-novelty judgment that used to be the third call now lives in Plan 17, with its own model-judgment surface.)

**Unlike Plan 7, this plan does not yet specify their model machinery** — prompt contract, model + fallback selection, and the parse/validation path — for either of them. That is the single largest gap to close at the `doing/` boundary; treat it as a prerequisite for §2–§3, not an afterthought. Its quality gate is Sub-task C.

**Acceptance gate (not a test).** Before `doing/`, each of the two model calls needs a recorded prompt contract, model + fallback selection, and parse/validation path. This gate blocks every `[llm]` check above: until it closes, the amber behaviors have no harness to verify against.

### Verification — loop-level invariants

Per-step checks sit with the step they test (§2–§4). What remains here is what no single step owns — the whole-loop invariants.

- A second run updates existing belief state instead of recreating it from scratch.
- Re-processing a signal already recorded in provenance does **not** double-count it (provenance is keyed by `signal_id` — distinct from §2's claim-level dedup).
- A run consumes the signals missing this plan's `belief_processed_at` stamp; the stamp is written **last**, after all of a signal's claims are processed (resolves the previously-open "which signals does a run consume?" question, now answered per subsystem).
- Auto-updated surfaces this plan writes — the entity records from routed facts — remain legible after a run. (Theme and timeline legibility are Plan 17's concern.)

---

## Sub-task B — Hypothesis Revision And Propagation Evaluation

Build a focused evaluation suite for the hardest part of the system: whether knowledge updates actually propagate coherently. This is the **per-mechanic** eval — multi-step fixtures over the deterministic §4 machinery. The **per-judgment** eval (the §2–§3 model calls) is Sub-task C; the **at-scale** eval (the whole loop over a large batch) is Sub-task D.

### Changes

| File | Action | Description |
|---|---|---|
| `tests/test_hypothesis_propagation.py` | **NEW** | Multi-step fixtures that verify support, weakening, opposition, convergence, downstream propagation, and comparative (pairwise-edge) updates |
| `docs/specs/15_5b_hypothesis_revision_propagation.test.md` | **NEW** | Human-readable spec describing why ripple-effect failures matter to briefing quality |

### Evaluation cases

- a support case where new evidence strengthens an existing hypothesis
- a weakening case where new evidence lowers confidence without full replacement
- an opposition case where evidence against a current hypothesis lowers posterior belief
- a propagation case where changing one hypothesis updates a dependent hypothesis or briefing conclusion
- a convergence case where multiple weak signals together change belief state
- a comparative-update case where head-to-head evidence moves the belief on the *correct* pairwise edge; a new contender adds a fresh edge without disturbing existing ones; and a cycle (A>B, B>C, C>A) is preserved as conditional dominance rather than forced into a total order

### Verification

- belief state changes are visible in durable files, not only theme prose
- downstream derived outputs change when upstream beliefs change
- opposing evidence remains visible in the hypothesis history and affects posterior belief
- head-to-head evidence moves the belief on the correct pairwise edge; a new contender adds edges rather than rebuilding, and cycles are not "resolved" away into a fabricated global ranking

---

## Sub-task C — Triage And Stance Judgment Evaluation

**Depends on:** Plan 13 (reuses its LLM-as-judge helper, `eval_judge.py`).

The two model calls in §2–§3 are judgments, not deterministic code, so the shape tests in Sub-task A cannot tell whether they are *correct*. This sub-task is their quality gate, built the way Plan 13 gates pass-1/pass-2: a small golden set scored with an LLM-as-judge. It is the belief-graph analogue of Plan 13's scoring eval — and the tie to Plan 13 is narrow, just the judge helper, so this needs that one module to exist, not all of Plan 13.

### Changes

| File | Action | Description |
|---|---|---|
| `evals/golden/update_loop.yaml` | **NEW** | A handful of claims, each paired with a human judgment: which hypothesis it should attach to (or `open new` / `route out`), and its resolved stance against that hypothesis, against a fixed seed hypothesis store |
| `evals/eval_update_loop.py` | **NEW** | Runs triage + stance over the golden claims against the fixed store and judges each call with the rubric; writes a markdown report. Reuses Plan 13's `eval_judge.py`; does not modify Plan 13 |

### Verification

- **Matching is the call to prioritise** — §6 names it the loop's largest gap.
- A claim attached to the wrong hypothesis, routed when it should have opened a bet, or whose stance was copied from pass-2 instead of re-resolved against the matched hypothesis, scores low and is named in the report.
- Re-running on the same predictions is near-identical (±1 judge drift), matching Plan 13's eval contract.

---

## Sub-task D — At-Scale Belief Health (after backfill)

**Depends on:** Plan 14 (produces the backfilled signal batch) and Sub-task A (moves beliefs over it).

The evals above check one mechanic or one judgment at a time. They cannot see the property that only emerges when the whole loop runs over a large batch: does the **store keep its shape?** This sub-task checks that on the Plan 14 backfill (~200–300 claims across ~100 papers against ~10 seeded hypotheses) — the same batch §6's acceptance gate calls out.

What it must demonstrate, measured on the real backfilled store:

- Specific questions keep their own hypotheses — no flattening into a few broad ones (the §6 "too coarse" failure).
- The store does not fill with one-evidence dead-ends (the §6 "too fine" failure).
- Hypotheses the literature supports carry visibly more evidence mass than genuinely open ones, with every unit of mass traceable to a `signal_id` in provenance. *(Moved here from Plan 14, where it could not be verified without this plan's updater.)*

**How is left open.** Whether this is a deterministic measurement over `hypotheses.json` (mass distribution, count of one-evidence bets), an LLM-as-judge over the resulting store, or a human read — and what threshold counts as "flattening" or "dead-end" — is pinned at the `doing/` boundary. This sub-task names *what* it checks and *why*; the method is a later decision.
