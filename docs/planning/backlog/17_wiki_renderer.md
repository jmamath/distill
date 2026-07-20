# Plan 17 — Wiki Renderer: Theme Novelty And Growth

**Original task id:** 15.5 (wiki-update half).

**Depends on:** Plan 19 (source-grounded finding contract); Plan 9 (durable graph-update outcomes and authoritative theme placement); Plan 13 (LLM-as-judge helper for the quality gate).

---

Render the belief graph's durable updates into a coherent thematic wiki without re-interpreting raw pass-2 findings.

**Why this matters:** The graph is Distill's canonical knowledge model; the wiki is its readable projection. If the renderer independently rereads source signals, it can disagree with the graph about what a finding means or where it belongs. If it appends every graph update verbatim, themes degrade into an undifferentiated pile. Plan 17 therefore starts only after Plan 9 has interpreted the source, then makes the one presentation judgment the graph does not own: whether that update is replication, adjacent, or wholly new relative to existing theme prose.

---

## §1 · What this plan does

Plan 17 is **sequential in data and decoupled in code**. It never calls Plan 9, but it only consumes the stable outcomes Plan 9 writes.

```mermaid
flowchart TB
    signal[("Plan 19 signal<br/>source-grounded findings")]:::data
    graph["Plan 9 · interpret finding<br/>attach · open · route · drop"]:::upstream
    outcome[("Durable graph outcome<br/>evidence · hypothesis · entity<br/>theme placement + source provenance")]:::data
    novelty{{"Plan 17 · narrative novelty<br/>replication · adjacent · wholly new"}}:::llm
    grow["Grow theme<br/>or leave prose unchanged"]:::det
    themes[("themes/*.md")]:::data
    timeline[("timeline.json<br/>dated routed facts that grew a theme")]:::data
    decisions[("renderer decision trail<br/>and processing progress")]:::data
    output["Plan 10 · contextual assessment<br/>and output generation"]:::downstream

    signal --> graph --> outcome
    outcome --> novelty --> grow
    grow --> themes
    grow --> timeline
    novelty --> decisions --> output

    classDef llm fill:#fdeecf,stroke:#b9821f,color:#5c3d00;
    classDef det fill:#d9f2e6,stroke:#1a7f52,color:#0b3d26;
    classDef data fill:#eeeeec,stroke:#9a9a96,color:#333333;
    classDef upstream fill:#dbe9fb,stroke:#2b6cb0,color:#0b2d52;
    classDef downstream fill:#f3e8fd,stroke:#7c3aed,color:#3b0764;
```

The handoff contains only render-worthy graph outcomes:

- **Attached evidence** references its matched hypothesis and inherits that hypothesis's `theme_ids`.
- **A new hypothesis** already carries the `theme_ids` Plan 9 assigned when opening it, plus its founding evidence.
- **A routed entity** carries the theme placement Plan 9 decided for the non-belief fact.
- **A drop** produces no renderer input.

Plan 17 does not match evidence to hypotheses, assign themes, reopen source signals, or reconsider Plan 9's disposition. Those are graph decisions. It may read the evidence, hypothesis, entity, and source provenance referenced by an outcome to write accurate prose.

---

## §2 · Decide whether the graph update changes theme prose

**The renderer makes one judgment: how new is this update to the destination theme?** Theme placement is already settled. Novelty is judged against the current theme body because only the renderer knows what the human-readable narrative already says.

- **Replication** — confirms what the theme already communicates; preserve the graph evidence but add no prose.
- **Adjacent** — extends a direction the theme already frames; append a concise block linked to what it extends.
- **Wholly new** — introduces a direction the theme does not frame; open a new anchored section.

A graph update may target more than one theme through its hypothesis. Novelty is judged separately for each destination, but the renderer must not copy the same contribution into several themes. A second theme grows only when the update adds something distinct to that narrative.

The renderer records its verdict and reasoning against the stable graph-outcome id. That decision trail is also its progress marker: a processed outcome is not reconsidered on the next run, and Plan 17 never writes a competing stamp into source signal frontmatter. The exact storage shape is pinned when this plan moves to `doing`.

Whether an update deserves audience attention is not Plan 17's decision. Plan 10 reads graph state and renderer outcomes to derive current applicability, strategic significance, audience fit, and recency.

### Model-judgment surface

The novelty call receives the graph outcome's durable object and source provenance, the destination theme body, and any earlier contribution the same outcome made to another theme. It returns `replication | adjacent | wholly_new`, reasoning, and—when adjacent—the prior narrative block it extends.

The prompt, model/fallback, strict parse contract, and evaluation rubric are pinned at the `doing/` boundary. Theme selection is not part of this model call.

---

## §3 · Apply the verdict deterministically

Once novelty is decided, mechanics are simple:

- replication changes no theme prose;
- adjacent appends one linked block;
- wholly new creates one anchored section; and
- a dated routed entity that grows a theme appends one timeline event.

Writes are idempotent by graph-outcome id plus destination theme. Replaying Plan 9 or restarting Plan 17 cannot duplicate prose, anchors, decision rows, or timeline events.

Likely implementation areas—exact files pinned at `doing`—are the renderer entry point, stable-anchor helpers, timeline merge mechanics, the renderer decision/progress store, and focused tests.

---

## §4 · Evaluation

### Per-decision quality

A small golden set pairs graph outcomes and theme bodies with human novelty verdicts. It must cover attached evidence, a newly opened hypothesis, a routed entity, a mixed-paper sequence, and a multi-theme non-redundancy case. The eval reuses Plan 13's judge helper and names incorrect verdicts in a readable report.

### At-scale theme legibility

After Plan 14 backfills the graph, render the resulting outcome batch and check the property that single-case evals cannot see: themes still read as coherent narratives rather than append-sludge. The exact combination of human review, LLM judge, and structural checks is pinned at `doing`.

---

## Verification

- Plan 17 processes Plan 9 graph outcomes and never reads pass-2 signals directly.
- Evidence is rendered under the matched hypothesis's themes; a new hypothesis uses the themes assigned at creation; routed entities use Plan 9's placement.
- Replication preserves graph evidence without growing prose.
- Adjacent and wholly-new outcomes grow themes according to their verdicts with stable anchors.
- A multi-theme outcome never copies the same contribution into several themes.
- A dated routed entity enters the timeline only when it grows a theme.
- Reprocessing an outcome is idempotent across prose, decisions, and timeline writes.
- Renderer progress never modifies source signal frontmatter, eliminating the old Plan 9/Plan 17 stamp race.
- Plan 10 can trace an output candidate through the renderer decision to the graph outcome and source provenance.

## Non-goals

- Matching raw findings to hypotheses or themes.
- Reconsidering Plan 9's attach / open / route / drop or stance decisions.
- Deriving applicability, strategic significance, recency, or audience action; Plan 10 owns those.
- Changing hypothesis belief state.
