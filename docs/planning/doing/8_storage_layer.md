# Plan 8 — Topic Storage Helpers And Layout Documentation

**Original task id:** 15.4
**Depends on:** Plan 1 (bootstrap tooling, seeds `overview.md`, `themes/`, `entities.json`, `timeline.json`, `open_questions.json`); Plan 1 pass-2 pipeline (defines the signal frontmatter schema that storage helpers must honour).

---

Add the read/merge helpers that make topic files safely accessible to downstream stages, seed the initial `hypotheses.json` and `evidence.json`, and document the full flat layout.

**Why this matters:** A strategic briefing product cannot rely on per-run summaries alone. It needs durable topic memory that persists across runs. The signal schema is already defined by the pass-2 pipeline plan; this task adds the read/merge helpers and documents the complete on-disk contract so every downstream stage builds against a stable foundation.

## Changes

| File | Action | Description |
|---|---|---|
| `src/topics/storage.py` | **NEW** | Save/load helpers for topic files and run outputs (frontmatter-aware read/write, list/merge by stable id); signal helpers conform to the pass-2 schema and support partial updates so the wiki updater can write back `classification` and `theme_id_assigned`; evidence helpers expose a credibility-weighted `strength` increment with provenance append; open-question helpers expose a `count` increment with provenance append |
| `data/research_topics/README.md` | **UPDATE** | Document the flat layout from architecture §6, including signal schema reference |
| `data/research_topics/data_advantage/hypotheses.json` | **NEW** | Durable belief store for strategic topic hypotheses; belief state is a Beta distribution parameterised by `(alpha, beta)` — a weighted accumulator over evidence strength |
| `data/research_topics/data_advantage/evidence.json` | **NEW** | Evidence records linking claims to hypotheses; `strength` is a weighted accumulator (sum of `source_credibility` from contributing signals); `provenance` is an append-only list of `{signal_id, weight_applied}` |
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

**Hypothesis authoring constraint:** each record must contain exactly one falsifiable binary directional claim — something that can, in principle, be confirmed or refuted by evidence. Multi-dimensional claims must be decomposed into separate records; relationships between them are expressed through `depends_on` edges. Continuous parameter estimates and vague trend statements are out of scope for this store.

Field notes:

- `status`: `active | watch | retired | superseded`
- `belief.alpha` / `belief.beta`: Beta distribution parameters; updated by appending evidence strength (`alpha += strength` for `for`, `beta += strength` for `against`, split 50/50 for `mixed`); initialised at `alpha = beta = 1.0` (uniform — no prior belief either way)
- All rendering derivatives (mean, confidence label, convergence label) are computed from `alpha` and `beta` at read time — none are stored
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
- `strength`: weighted accumulator — each contributing signal appends its `source_credibility` to `provenance` and adds that value to `strength`; `null` credibility falls back to a neutral weight (0.5, defined in Plan 9)
- `provenance`: append-only list of `{signal_id, weight_applied}`; grows as new signals support the same claim
- `summary`: human-readable description of the current evidence state; updated by the wiki updater as new signals arrive

## Open question schema (`open_questions.json`)

Extends the existing bootstrapped records with two new fields (backward-compatible; absent fields default to `0` / `[]`):

- `count`: integer count of distinct signals that have raised this question
- `provenance`: append-only list of `{signal_id}` references

**Explicitly out of scope:** `overview.md`, `themes/`, `entities.json`, `timeline.json` — those come from Plan 1 (bootstrap). There is **no** `wiki/` subdirectory; the wiki is the flat human-readable tree.

## Verification

- One topic folder can store a complete run end-to-end using the flat layout
- Wiki files are human-readable and editable
- The structure is reusable for another topic id
- Storage helpers preserve YAML frontmatter on partial updates (no drift)
