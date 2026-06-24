---
date: TBD
type: decision
---
Pass-1 is a relevance filter: it reads abstracts and drops anything not on-topic. Pass-2 goes further — full text, extracting evidences, scoring applicability and strategic significance, placing each signal in the thematic landscape.

Both run on cheaper models in production. But how do you know a cheaper model is making good calls?

The plan: golden labels from a frontier model — GPT 5.5 or Opus 4.7, reviewed line by line before committing. Those become the fixed yardstick. Run pass-1 or pass-2 with any model and score it against them.

It lets you answer a real question: is the cheaper model close enough to the frontier, or is it cutting corners you'll pay for later?

---
date: TBD
type: decision
---
A topic contains themes. Each theme carries hypotheses about what's true in the research landscape. Each hypothesis accumulates evidences — supporting, opposing, or mixed — from every signal that arrives.

The question is how to encode belief at the hypothesis level so it actually updates.

I landed on Beta(α, β), where α accumulates supporting signals and β opposing ones. Each new paper increments one side, weighted by source credibility. A hypothesis with α=20, β=2 looks nothing like α=2, β=0. Same direction, very different confidence.

This is a bet. Beta distributions assume belief can be modeled as a probability — a strong simplification for claims about complex research landscapes. But it gives you something prose can't: a belief that updates predictably, degrades under opposition, and propagates to dependent hypotheses with a well-defined weight.

Whether it's the right abstraction is still an open question.

---
date: TBD
type: decision
---
When new papers arrive, Distill updates its research hypotheses — not just the prose, but actual belief state. The question is: by how much should a given paper move the needle?

Source credibility is one of the weights. A paper from a highly cited institution shifts the posterior more than one from an unknown lab.

But credible according to what? A global table seems clean — MIT scores X, Google scores Y, everywhere. The problem: credibility is domain-specific. ICLR acceptance counts are a meaningful proxy for AI research. For biology or economics they'd be noise.

So the table travels with the topic config. Different research area, different ranking. The proxy depends on the question, not just the institution.

---
date: TBD
type: decision
---
The topic I'm tracking will change. Maybe in 3 months, maybe 6.

So the topic definition — thesis, scoring dimensions, source priorities, audience profile — lives in a single config file instead. The orchestration code knows nothing about what it's tracking. Pivoting to a new research area means swapping the file.

Zero code changes to go from "data advantages in AI" to any other domain.

---
date: TBD
type: decision
---
Distill continuously ingests papers and scores each one for relevance. Scoring with a full-text model on every item would be too slow and expensive.

The obvious answer: fetch everything, then decide. But that means paying to read every paper you'll throw away.

Instead, a cheap model runs on abstracts only — no full-text fetch. Anything below the relevance threshold gets dropped there. Full-text scoring only runs on what cleared the gate.

Reading is the most expensive step in the pipeline. Every architectural decision around it should treat it that way.

---
date: TBD
type: decision
---
Every research effort starts with a literature review. Before you can track what's changing, you need to understand the current landscape.

Distill is organized around that structure. A topic defines the thesis. A literature review surfaces themes — the major clusters in the landscape. Themes carry hypotheses about what's actually true. Hypotheses accumulate evidences from every new signal that arrives.

None of that exists on day one. The wiki starts empty.

To seed it, Distill generates a deep research prompt automatically from the topic config — a standardized form encoding the thesis, scope, and the questions worth investigating. You run it through a frontier research tool. What comes back becomes the initial wiki.

Every topic starts the same way: a structured question, a literature review, a knowledge base ready to update.

---
date: 2026-05-28
type: decision
---
Reading more wasn't my problem. Remembering and compounding insight was.
I wrote about why I kept restarting—and why I'm building Distill: a system that continuously tracks papers, remembers what matters, and updates conclusions as new evidence arrives.
This is the first post on why I'm building it in public.
LINK

---
date: 2026-06-24
type: decision
---
In your agentic coding workflow, have you ever opened a plan written by your agent or a colleague's agent and felt this was written in robot language?

The usual output is a long bullet list. "Must support: A, B, C." It looks complete. But read it cold and you have no idea what's going on.

Two things helped me fix this.

A responsibility diagram at the top: each branch of the work mapped to the part of the system it touches. You understand the whole before reading any detail.

The pyramid structure: each section opens with its main claim, details underneath. When you apply this, long bullet lists collapse into 2-3 ideas and the missing decisions become visible.
