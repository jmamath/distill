# Plan 9 — Hypothesis And Wiki Update Loop

**Original task ids:** 15.5 (Hypothesis And Wiki Update Loop), 15.5b (Hypothesis Revision And Propagation Evaluation)

---

Build the mechanism that turns newly scored signals into updated topic beliefs and an evolving thematic wiki, then prove that knowledge updates actually propagate coherently.

**Why this matters:** The wiki layer is the human-readable product surface, but it should not be the only place where the system stores what it believes. Without a hypothesis update loop, the system remains a feed summarizer with nicer prose. A system has not really updated its knowledge if it can store new evidence but still briefs as though the old world is true — this plan tests ripple effects directly so the product does not quietly degrade into a prose append-only log.

---

## Sub-task A — Hypothesis And Wiki Update Loop

### Changes

| File | Action | Description |
|---|---|---|
| `src/topics/wiki_updater.py` | **NEW** | Reads pass-2 signals; for each top-confidence `candidate_theme`, classifies the contribution as `replication` / `adjacent` / `wholly_new` against the theme body; appends to themes (Markdown, anchor-stable); writes the resolved `classification` and `theme_id_assigned` back to the signal frontmatter |
| `src/topics/hypothesis_updater.py` | **NEW** | Reads pass-2 signals; dedups `new_evidences` against `evidence.json` and increments `strength` (weighted by signal `source_credibility`; `null` credibility uses a configured neutral weight); attaches evidence to existing hypotheses or creates new ones; updates posterior belief state and per-hypothesis `convergence` from recent provenance |
| `src/topics/open_question_updater.py` | **NEW** | Dedups `new_open_questions` from pass-2 signals against `open_questions.json`; increments `count`; appends `signal_id` to provenance |
| `src/topics/entities.py` | **NEW** | Entity extraction or normalization helpers |
| `src/topics/timeline.py` | **NEW** | Append/update notable changes over time (substantive shifts only; replication does not append) |
| `src/topics/propagation.py` | **NEW** | Re-evaluates dependent hypotheses, theme sections, and briefing conclusions when hypothesis belief changes |
| `src/topics/anchors.py` | **NEW** | Stable `<a id="..."></a>` generation and resolution for adjacent-block linking (architecture §12) |
| `tests/test_wiki_updater.py` | **NEW** | Theme updates remain idempotent across replication, adjacent, and wholly_new cases; classification is written back to signal frontmatter |
| `tests/test_hypothesis_updater.py` | **NEW** | Support, weakening, opposing, and new-hypothesis cases update durable belief state correctly; strength increments scale with source credibility |
| `tests/test_open_question_updater.py` | **NEW** | The same question raised by two signals shows `count: 2` with both `signal_id`s in provenance |

### Update logic must support

- recurring themes (continuous update): appends to `themes/*.md` (Markdown, anchor-stable)
- classification of signal-to-theme contribution: `replication` (no body growth), `adjacent` (append block + Markdown link to prior block's stable anchor), or `wholly_new` (standalone section + fresh anchor); write the resolved `classification` and `theme_id_assigned` back to the signal frontmatter
- evidence integration: dedup by stable id (claim hash + hypothesis_id); increment `strength` weighted by signal `source_credibility` (null → configured neutral weight); append `{signal_id, weight_applied}` to provenance
- hypothesis maintenance: attach new evidences to existing hypotheses; create new hypotheses when no match exists; update priors/posteriors; revise action posture based on accumulated evidence
- open questions maintenance: dedup by stable id; increment per-question `count`; append `signal_id` to provenance; surfaced through `overview.md`
- convergence computation: derive `convergence` from recent supporting-signal density and stance alignment in evidence provenance
- entity and timeline updates: appends new entries by id (timeline only on substantive shifts; replication does not append)
- bounded Bayesian-style updates: stronger credible evidence moves posterior more; negative evidence lowers belief rather than spawning a separate contradiction object
- propagation rules: when a hypothesis changes meaningfully, re-evaluate dependent hypotheses and any briefing-facing conclusions they feed

The updater should treat `depends_on` as the canonical first-pass edge field.

### Landscape fit and technical novelty axes

The `replication / adjacent / wholly_new` classification produced by `wiki_updater.py` is the operational form of two scoring concepts:

**Landscape fit** answers "how does this signal relate to what we already know?" Replication confirms an existing theme body with no new information; adjacent extends it in a direction already framed by the topic; wholly new represents something the topic has no prior frame for. This classification is written back to the signal frontmatter as `classification` and drives both theme growth rules (replication → no body growth; adjacent → append block with stable anchor; wholly_new → standalone section) and the output filter in Plan 10 (replication signals are not surfaced as tweet candidates).

**Technical novelty** answers "is this genuinely new — a new method, corpus, or result — or is it incremental over prior work?" This judgment requires the full theme body as context and cannot be made reliably from the abstract alone or without knowing what the topic already knows. The wiki updater is therefore the right place to assess it: the `replication / adjacent / wholly_new` classification already encodes this — replication is incremental, adjacent is a meaningful extension, wholly_new is a genuine advance. Incremental signals may still be worth monitoring but should rank lower in the output filter than genuine advances.

### Verification

- A second run updates existing belief and wiki state instead of recreating it from scratch
- New items can extend an existing theme (`adjacent`) or create a new one (`wholly_new`); replication is reflected as no theme growth
- The resolved `classification` and `theme_id_assigned` are written back to the signal frontmatter
- The same open question raised by two signals shows `count: 2` with both `signal_id`s in provenance
- An evidence increment from a high-credibility paper moves posterior more than the same claim from a low-credibility paper
- Evidence against an existing hypothesis lowers posterior belief instead of only being mentioned in prose
- A changed hypothesis can update at least one dependent hypothesis or briefing-facing conclusion
- Timeline and watchlist are updated automatically and remain legible

---

## Sub-task B — Hypothesis Revision And Propagation Evaluation

Build a focused evaluation suite for the hardest part of the system: whether knowledge updates actually propagate coherently.

### Changes

| File | Action | Description |
|---|---|---|
| `tests/test_hypothesis_propagation.py` | **NEW** | Multi-step fixtures that verify support, weakening, opposition, convergence, and downstream propagation |
| `docs/specs/15_5b_hypothesis_revision_propagation.test.md` | **NEW** | Human-readable spec describing why ripple-effect failures matter to briefing quality |

### Evaluation cases

- a support case where new evidence strengthens an existing hypothesis
- a weakening case where new evidence lowers confidence without full replacement
- an opposition case where evidence against a current hypothesis lowers posterior belief
- a propagation case where changing one hypothesis updates a dependent hypothesis or briefing conclusion
- a convergence case where multiple weak signals together change belief state

### Verification

- belief state changes are visible in durable files, not only theme prose
- downstream derived outputs change when upstream beliefs change
- opposing evidence remains visible in the hypothesis history and affects posterior belief
