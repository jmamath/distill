# Plan 8 — Topic Storage Helpers And Layout Documentation

**Original task id:** 15.4
**Depends on:** Plan 1 (bootstrap tooling, seeds `overview.md`, `themes/`, `entities.json`, `timeline.json`, `open_questions.json`); Plan 1 pass-2 pipeline (defines the signal frontmatter schema that storage helpers must honour).

---

Add the read/merge helpers that make topic files safely accessible to downstream stages, seed the initial `hypotheses.json` and `evidence.json`, and document the full flat layout.

**Why this matters:** A strategic briefing product cannot rely on per-run summaries alone. It needs durable topic memory that persists across runs. The signal schema is already defined by the pass-2 pipeline plan; this task adds the read/merge helpers and documents the complete on-disk contract so every downstream stage builds against a stable foundation.

## Changes

| File | Action | Description |
|---|---|---|
| `src/topics/storage.py` | **NEW** | Save/load helpers for topic files and run outputs (frontmatter-aware read/write, list/merge by stable id); signal helpers conform to the pass-2 schema and support partial updates so the wiki updater can write back `classification` and `theme_id_assigned`; evidence helpers expose a credibility-weighted `strength` increment with provenance append |
| `data/research_topics/README.md` | **UPDATE** | Document the flat layout from architecture §6, including signal schema reference |
| `data/research_topics/data_advantage/hypotheses.json` | **NEW** | Durable belief store for strategic topic hypotheses; belief state is a Beta distribution parameterised by `(alpha, beta)` — a weighted accumulator over evidence strength. Each record is a single directional, resolvable bet (resolvability is required; the `resolution_criterion` 4-tuple is optional scaffolding); open questions are represented here as uniform-prior records (there is no separate open-questions claim store) |
| `data/research_topics/data_advantage/evidence.json` | **NEW** | Evidence records linking claims to hypotheses; `strength` is a weighted accumulator (sum of `weight_applied` across contributing signals, where `weight_applied = source_credibility / 10`); `provenance` is an append-only list of `{signal_id, weight_applied}` |
| `data/research_topics/data_advantage/raw/` | **NEW** | Original fetched payloads, partitioned `{yyyy-mm-dd}/{source_name}{.xml/.html}` (native format, not coerced to JSON) |
| `tests/test_topic_storage.py` | **NEW** | Round-trip read/write for each file type; frontmatter preserved on update |

## Storage layout must support

- raw ingested items (`raw/`)
- scored signals (`signals/`)
- durable belief graph state (`hypotheses.json`, `evidence.json`)
- wiki state (flat: `themes/*.md`, `entities.json`, `timeline.json`, `open_questions.json`, `overview.md`); storage helpers do JSON load/merge by id (in addition to YAML frontmatter for themes/overview)
- generated briefings (`briefings/`)
- dossiers (`dossiers/`)

## Hypothesis schema (`hypotheses.json`)

`hypotheses.json` is a flat JSON array. Each record:

```json
{
  "id": "data_scarcity_moat_weakening",
  "statement": "Data scarcity is becoming a weaker moat in benchmark-saturated AI markets.",
  "theme_ids": ["synthetic-data-generation", "quality-filtering-curation"],
  "status": "active",
  "belief": {
    "alpha": 8.7,
    "beta": 3.6
  },
  "action_posture": "monitor",
  "why_it_matters": "If true, durable advantage shifts toward workflow integration and proprietary usage loops rather than static dataset ownership.",
  "resolution_criterion": {
    "metric": "fraction of new frontier-class model releases trained primarily on synthetic or public-curated data rather than proprietary scraped corpora",
    "threshold": "> 50%",
    "scope": "publicly documented frontier-class releases",
    "horizon": "2027-06-30"
  },
  "depends_on": [
    {
      "hypothesis_id": "synthetic_data_quality_rising",
      "relationship": "supports",
    }
  ],
  "created_at": "2026-04-26",
  "last_updated_at": "2026-04-26"
}
```

**Hypothesis authoring constraint (the betting-market test):** each record must be a single *directional, resolvable bet* — a claim concrete enough that two reviewers could independently settle it the same way once evidence arrives. **Resolvability is the requirement.** The optional **resolution criterion** (metric + threshold + scope + horizon) is *scaffolding that helps achieve resolvability*, not a mandatory four-field literal: for an already-crisp binary event claim the metric and threshold are often implicit in the statement, while scope and horizon are usually still worth pinning (scope prevents one Beta from fusing different contexts; horizon makes "against" reachable and keeps the claim an actual bet). Multi-dimensional claims must be decomposed into separate records; relationships between them are expressed through `depends_on` edges.

This single rule subsumes what used to be modelled as separate "open questions":

- An open question is just a hypothesis whose belief still sits near the uniform prior with little accumulated evidence. **"Open" is a belief-state (high entropy, low evidence mass), not a separate object type.**
- **Magnitude questions** ("how far / how much?") become **threshold bets** ("metric exceeds X by horizon Y"). A single threshold is enough when only clearing one bar matters; a ladder of thresholds approximates the full curve when the magnitude itself is decision-relevant.
- **Unframed questions** ("which approach will win?") reduce to **scoped binary bets**. Because incoming signals (papers) arrive with experiments, the framing almost always comes bundled with the evidence, so genuinely unframed uncertainty is a transient. The only residue is the open-world catch-all ("some approach nobody has proposed yet wins") — itself a valid bet that self-liquidates into named bets as evidence arrives.

Continuous parameter estimates that cannot be reduced to a threshold bet, and vague trend statements with no resolution criterion, remain out of scope for this store.

Field notes:

- `status`: `active | watch | retired | superseded`
- `belief.alpha` / `belief.beta`: Beta distribution parameters; updated by appending evidence strength (`alpha += strength` for `for`, `beta += strength` for `against`, split 50/50 for `mixed`); initialised at `alpha = beta = 1.0` (uniform — no prior belief either way)
- All rendering derivatives (mean, confidence label, convergence label) are computed from `alpha` and `beta` at read time — none are stored
- `resolution_criterion`: **optional** scaffolding for resolvability — `metric` (what is measured), `threshold` (the yes/no cut), `scope` (the population/domain the claim ranges over), `horizon` (the date by which it should resolve). Populate the parts that the `statement` does not already make unambiguous. What is *required* is that the hypothesis be resolvable; a record that is not resolvable (no shared rule for what counts as for/against) is not a valid hypothesis, with or without this field
- `action_posture`: one of the topic's `action_vocabulary` values (`ignore | monitor | prototype | invest`)
- `depends_on.relationship`: `supports | weakens`; `weight` is 0.0–1.0; edges live on the hypothesis node (no separate edge store)
- Evidence pointers are not stored on the hypothesis — query `evidence.json` filtered by `hypothesis_id` to retrieve supporting and opposing evidence

## Evidence schema (`evidence.json`)

`evidence.json` is a flat JSON array. Each record represents one claim linked to one hypothesis, backed by one or more signals over time:

```json
{
  "id": "ev_001",
  "hypothesis_id": "data_scarcity_moat_weakening",
  "claim": "Synthetic eval sets match human-labeled baselines in narrow domains.",
  "stance": "for",
  "strength": 1.7,
  "provenance": [
    {"signal_id": "arxiv_2026-04-26_a3f7b2c1de", "weight_applied": 0.8},
    {"signal_id": "arxiv_2026-05-01_b9c3d4e2fa", "weight_applied": 0.9}
  ],
  "summary": "Two independent synthetic-evaluation papers in April–May 2026 showed benchmark parity with human annotation in code and reasoning domains.",
  "created_at": "2026-04-26",
  "last_updated_at": "2026-05-01"
}
```

Field notes:

- `stance`: `for | against | mixed | neutral`
- `strength`: weighted accumulator on a 0–1-per-signal scale. Each contributing signal normalises its `source_credibility` (0–10, see Plan 6/7) to `weight_applied = source_credibility / 10`, appends `{signal_id, weight_applied}` to `provenance`, and adds `weight_applied` to `strength`. `null` credibility (no affiliation matched the table) falls back to a neutral `weight_applied = 0.5` (the neutral-weight constant is defined in Plan 9). Thus a single maximally-credible signal contributes `1.0`; `strength` reads as an effective count of fully-credible confirmations and never recomputes from scratch.
- `provenance`: append-only list of `{signal_id, weight_applied}`; grows as new signals support the same claim. `weight_applied` is stored per entry so the contribution of each signal stays auditable even if the credibility table changes later
- `summary`: human-readable description of the current evidence state; updated by the wiki updater as new signals arrive

## Open questions are hypotheses (no separate claim store)

There is **no** separate open-question *claim* schema. Per the authoring constraint above, an open question is a hypothesis sitting near its uniform prior — so open questions are stored as records in `hypotheses.json`, not as a parallel store. This removes the duplicated authoring discipline and the question→hypothesis "graduation" sync problem: a question simply *is* a low-evidence hypothesis that concentrates as evidence lands.

Consequences left for downstream plans (out of scope here):

- The `open_questions.json` seeded by Plan 1 bootstrap must be migrated into uniform-prior hypotheses; bootstrap should seed `hypotheses.json` directly (bootstrap / Plan 9).
- Whether a thin, **non-authoritative rendering** of low-confidence, high-priority hypotheses survives in `overview.md` as an "open questions" view is a rendering decision, not a storage one.

**Explicitly out of scope:** `overview.md`, `themes/`, `entities.json`, `timeline.json` — those come from Plan 1 (bootstrap). There is **no** `wiki/` subdirectory; the wiki is the flat human-readable tree.

## Verification

- One topic folder can store a complete run end-to-end using the flat layout
- Wiki files are human-readable and editable
- The structure is reusable for another topic id
- Storage helpers preserve YAML frontmatter on partial updates (no drift)
- Every hypothesis is resolvable — two reviewers could independently settle the bet the same way; the `resolution_criterion` (metric/threshold/scope/horizon) is the recommended scaffold for that, not a required four-field literal
- Open questions are stored as uniform-prior hypotheses — there is no separate open-questions claim store
