# Planning

Task plans for Distill, organized by status.

```
done/     ← completed tasks, kept for reference and traceability
doing/    ← the task actively being worked on (one at a time)
backlog/  ← upcoming tasks in dependency order, ready to be started
```

## Workflow

1. Pick the lowest-numbered file in `backlog/`.
2. Move it to `doing/` when work starts.
3. Move it to `done/` (and update its status line) when tests pass.

## Dependencies

Plans are numbered in rough build order, but some dependencies run against it — Plan 9's evaluation sub-tasks, for instance, need the higher-numbered Plans 13 and 14. The graph below shows the real edges.

```mermaid
%%{init: {'flowchart': {'nodeSpacing': 55, 'rankSpacing': 80}}}%%
flowchart TB
    p1["1 · bootstrap tooling"]:::done
    p2["2 · topic config"]:::done
    p3["3 · bootstrap run"]:::done
    p4["4 · source adapters"]:::done
    p5["5 · pass-1 filter"]:::done
    p6["6 · credibility"]:::done
    p7["7 · pass-2 pipeline"]:::done
    p8["8 · storage layer"]:::done
    p16["16 · pass-2 cleanup"]:::done
    p15["15 · hypotheses migration"]:::doing
    p9["9 · belief graph"]:::backlog
    p10["10 · output generation"]:::backlog
    p11["11 · editorial workflow"]:::backlog
    p12["12 · end-to-end slice"]:::backlog
    p13["13 · scoring eval"]:::backlog
    p14["14 · references backfill"]:::backlog
    p17["17 · wiki renderer"]:::backlog
    p18["18 · duplicate cleanup"]:::backlog

    p1 --> p2
    p2 --> p3
    p3 --> p7
    p3 --> p12
    p4 --> p5
    p4 --> p6
    p6 --> p7
    p5 --> p13
    p7 --> p8
    p7 --> p16
    p8 --> p9
    p8 --> p13
    p8 --> p15
    p8 --> p17
    p9 --> p10
    p9 --> p18
    p9 -->|updater| p14
    p17 --> p10
    p10 --> p11

    p13 -.->|Sub-task C| p9
    p14 -.->|Sub-task D| p9
    p13 -.-> p17
    p14 -.-> p17

    classDef done fill:#d9f2e6,stroke:#1a7f52,color:#0b3d26;
    classDef doing fill:#fdeecf,stroke:#b9821f,color:#5c3d00;
    classDef backlog fill:#eeeeec,stroke:#9a9a96,color:#333333;
```

**Reading it.** Arrows run from a plan to the one that builds on it. A **solid** arrow means the target needs the source built first; a **dashed** arrow means the source only gates one of the target's *evaluation* sub-tasks, so the target's core work can start before it exists. Where several plans feed one, only the nearest link is drawn — each plan's own file lists its full `Depends on` set. Node colour marks status: green = done, amber = in progress, grey = backlog.

Plan 9 and Plan 17 are **parallel siblings** — they read the same pass-2 signals through a shared contract and never call each other, so no edge joins them.

## Numbering

Numbers are globally unique across all folders. Done tasks hold the lowest numbers (reflecting completion order); backlog tasks continue the sequence. When a task moves from backlog to doing to done, its number stays the same — and its colour in the graph above moves green.

## Specs

Detailed test specifications live separately in `docs/specs/` as `.test.md` files and are not moved by this workflow.
