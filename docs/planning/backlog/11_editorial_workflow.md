# Plan 11 — Editorial Review Workflow

**Original task ids:** 15.7 (Editorial Review Workflow), 15.7b (Comment Loop Infrastructure)

---

Define the minimum human-in-the-loop workflow for reviewing wiki updates and tweet candidates, then build the GitHub Actions infrastructure that makes the daily PR interactive.

**Why this matters:** The differentiator is judgment, not autonomous automation. The review surface is the daily PR: one PR per topic per day opened by the ingestion agent after all sources are processed. The comment loop is what makes the PR interactive — the human can push back on a claim, request a cross-file reconciliation, or sharpen a tweet candidate, and the agent commits a corrected version to the branch before the merge decision.

---

## Sub-task A — Editorial Review Workflow

### Changes

| File | Action | Description |
|---|---|---|
| `docs/editorial_review_workflow.md` | **NEW** | Review steps for signals, wiki updates, and tweet candidates |
| `docs/data_advantage_brief.md` | **REF** | Editorial standard and audience promise |

### Workflow must define

- daily PR structure: what the PR body must contain (new/updated/overwritten claims, sources added, open questions retired, tweet candidates)
- agent overwrite policy: agent may overwrite existing wiki content; human reviews the diff and pushes back before merging if needed
- how source traceability is checked
- how false positives are corrected
- how wiki drift is repaired
- tweet approval: `tweets/{yyyy-mm-dd}.json` entries are reviewed in the same PR; status set to `approved` or `rejected` before merge

### Verification

- A single review pass can correct a bad signal and preserve the correction
- The workflow is lightweight enough for one operator
- Tweet publication is gated on human review, not raw generation

---

## Sub-task B — Comment Loop Infrastructure

Build the GitHub Actions workflow and context assembly script that let the human request targeted wiki edits from a PR comment.

### Changes

| File | Action | Description |
|---|---|---|
| `.github/workflows/pr-comment.yml` | **NEW** | Triggers on `issue_comment` events; checks for trigger phrase (`@agent`); assembles context; calls Gemini API; commits result to the PR branch |
| `scripts/pr_agent.py` | **NEW** | Context assembly + Gemini API call: always fetches the core reference JSONs (`entities.json`, `timeline.json`, `hypotheses.json`, `evidence.json`), fetches any theme files named in the comment, builds the prompt, applies the response as a file edit |
| `docs/editorial_review_workflow.md` | **UPDATE** | Document the comment convention: `@agent <instruction> — see themes/<theme_id>.md` |

### Context assembly rules

- Always include: `entities.json`, `timeline.json`, `hypotheses.json`, `evidence.json` — small, stable, always relevant
- Theme files: fetched only if named explicitly in the comment (`— see themes/filtering-and-curation.md`); not guessed, not passed wholesale
- PR diff: always included as the primary context for what the comment is responding to

### Comment convention

```
@agent reconcile this with the FineWeb claim — see themes/filtering-and-curation.md
@agent sharpen the strategic framing on tweet 3
@agent this entity description is stale — update entities.json
```

The naming convention is not extra cognitive work: the reviewer already knows which theme is relevant because they just read the diff.

### Verification

- A comment with `@agent` and no theme reference triggers the workflow and uses only the diff + reference JSONs
- A comment naming a theme file fetches that file and includes it in context
- The agent's edit is committed to the PR branch, not to main
- A comment on a non-PR issue does not trigger the workflow
