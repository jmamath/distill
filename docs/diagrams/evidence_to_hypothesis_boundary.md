# Pass-2 Claim → Hypothesis Boundary

This diagram shows where signal authoring stops and belief synthesis begins. A pass-2 signal emits plain `claims`; it neither assigns stance nor authors hypotheses. Matching a claim, synthesizing a new resolvable hypothesis, and resolving stance are owned by Plan 9's `hypothesis_updater`, because those decisions need a named hypothesis and the current store — context pass-2 does not have.

```mermaid
flowchart TD
    subgraph P7["Plan 7 — Pass-2 (signal authoring)"]
        A[Pass-2 scoring<br/>scoring.py] --> B[Signal frontmatter<br/>claims:<br/>plain claim text]
    end

    subgraph P9["Plan 9 — hypothesis_updater (belief synthesis)"]
        C[Read signal claims] --> D{Triage against current<br/>hypothesis store}
        D -->|Attach| E[Resolve stance against<br/>matched hypothesis]
        D -->|Open| F[Synthesize uniform-prior<br/>hypothesis<br/>alpha = beta = 1.0]
        F --> E
        E --> G[Attach evidence:<br/>dedup vs evidence.json,<br/>increment strength + Beta belief]
    end

    B --> C
    HS[(hypotheses.json<br/>current belief store)] -. read .-> D
    G --> HS
    F --> HS
    G --> EV[(evidence.json)]
```

The dashed read edge is the whole point: both matching and stance are functions of a **named hypothesis**, not properties of claim text in isolation. Pushing either into `Pass2Score` would force the signal to answer a question whose inputs it cannot see.
