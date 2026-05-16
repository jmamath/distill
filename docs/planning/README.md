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

## Numbering

Numbers are globally unique across all folders. Done tasks hold the lowest numbers (reflecting completion order); backlog tasks continue the sequence. When a task moves from backlog to doing to done, its number stays the same.

## Specs

Detailed test specifications live separately in `docs/specs/` as `.test.md` files and are not moved by this workflow.
