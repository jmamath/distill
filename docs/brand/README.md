# Brand — Twitter

## tweet.md

Central log of all published tweets, in reverse chronological order.

Each entry uses this format:

```
---
date: YYYY-MM-DD
type: decision | epistemic | tension
---
Tweet text here.
```

The `type` field gives a machine reading this file enough context to understand the intent and voice of past tweets, and to help draft new ones consistently.

Each tweet is a self-contained mini story: what Distill is doing at that layer, the problem that arose, the tradeoff, and the decision. The problem lives in the tweet body — a technical reader should be able to understand the context, challenge the tradeoff, or contribute without knowing the codebase.

---

## Tweet Types

### Decision

The most common type. One non-obvious choice made while building. The formula: what I needed to do, what the obvious answer was, why I didn't take it.

The commit is evidence, not the subject. The subject is the intellectual problem. Link the commit for people who want to go deeper — keep the code out of the tweet body.

### Epistemic update

Distill is a belief-tracking system, so use it. A signal moved confidence in a thesis claim — up or down. Post the update with the reason it matters.

Format roughly: "Signal from [source] moved my confidence in [claim] from X toward Y, because..."

This directly demonstrates the product while building the research brand.

### Tension

A design question being sat with, a tradeoff with no clean answer, something not yet resolved. These generate replies and position the author as someone thinking, not just shipping. Post when something genuinely unresolved is worth naming.

---

## Voice

Matches the blog: introspective, intellectually honest about uncertainty. Prefer "here's what I was wrong about" over "I solved X." The commit is proof of the work, not the point of the tweet.

Post when there is something genuinely interesting to share, not on a fixed cadence.
