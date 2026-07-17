# North Star — Who Distill Is For

**Status:** hypotheses, not findings. Update this document whenever new information arrives. Last substantive update: 2026-07-17.

---

## §0 · How to read this document

This document records what we believe about Distill's potential users, and how strongly. Most claims here are bets, not facts. Each carries an evidence label:

- `published` — supported by peer-reviewed or formally published work.
- `forum` — supported by first-person complaints in public discussion threads.
- `indirect` — inferred from statistics or from the existence of tools, not from users saying it themselves.
- `speculation` — our reasoning only.

A persona counts as **validated** only when we have first-person evidence: people who fit the persona saying, in their own words, that they have the problem Distill solves. Until then, the persona is a bet, and the document says so.

---

## §1 · The bet behind the project

Research-assistant tools today are session-based: each run re-derives the state of a field from scratch, presents its output with uniform confidence, and forgets everything when it ends. Users cannot verify individual claims without redoing the work, and they cannot keep the output current without re-running everything.

Distill's bet is that the missing product is **durable, auditable, forkable belief state**: a claim-level record of what the literature says, with per-claim provenance, calibrated confidence, and a wiki that grows as evidence arrives. The evidence gathered so far (§4) says users complain loudest about *trust* and only implicitly about *memory*. So the pitch leads with auditability; durable state is the mechanism that delivers it.

---

## §2 · The landscape (as of July 2026)

Governing claim: **every component of Distill exists somewhere; the composition exists nowhere.**

- **Deep research tools** (OpenAI, Gemini, Perplexity, [Elicit](https://elicit.com/blog/introducing-elicit-alerts)) — one-shot synthesis, session-based, no durable state. Elicit has alerts, but alerts feed a library, not an evolving belief store.
- **[WikiCrow / PaperQA2](https://www.futurehouse.org/research-announcements/wikicrow)** (FutureHouse) — auto-generated wiki articles judged more accurate than human Wikipedia. Batch regeneration per entity; no incremental novelty-gated growth, no belief state. Closest analogue to the theme wiki.
- **[scite](https://scite.ai)** — citation stance classification (supporting / contrasting) at scale. Claim-level stances, but no accumulation into a posterior.
- **Living systematic reviews** (medicine) — the strongest demand signal. The community is actively adopting LLMs ([JMIR 2026](https://www.jmir.org/2026/1/e76130), [Research Square 2026](https://www.researchsquare.com/article/rs-9308492/v1)), but tools are per-review and domain-specific; none maintain a propagating belief graph.
- **[Nanopublications](https://nanopub.net/) / [ORKG](https://www.researchgate.net/publication/380664373_Open_Research_Knowledge_Graph)** — the 15-year-old academic tradition of machine-readable, shareable scientific claims. Adoption stalled because authoring was manual and the format heavy. Distill emits the same kind of artifact automatically, as a by-product of monitoring.

---

## §3 · Personas as hypotheses

Each persona follows the same skeleton. An empty or weak field is information: it shows where we are guessing.

### P1 — Evidence-synthesis teams maintaining living reviews

**Who.** Teams producing systematic reviews and meta-analyses, mostly in medicine and public health.

**Current workflow.** Search, screen, extract, synthesize, publish. Then the review ages. Updating means reassembling a team and redoing most of the pipeline.

**Bottleneck.** Updates are so expensive that most reviews are simply never updated. When updates happen, the original team's context is gone.

**What Distill changes.** The belief store *is* the institutional memory: claims, stances, provenance, and posteriors persist between updates, so an update is an increment, not a restart.

**Evidence today.** `published` — the strongest of the three personas, but none of it is about Distill specifically:

- Elliott et al., [Living systematic review: 1. Introduction — the why, what, when, and how](https://www.jclinepi.com/article/S0895-4356(17)30636-4/fulltext) (J Clin Epi, 2017). The foundational paper of the living-review movement; its authors built Cochrane's living evidence program.
- [Living Systematic Reviews and Other Approaches for Updating Evidence](https://pmc.ncbi.nlm.nih.gov/articles/PMC7542271/) — source of the update-lag figures cited in §4.
- [Living systematic reviews in rehabilitation science](https://link.springer.com/article/10.1186/s13643-021-01857-5) (Systematic Reviews, 2021) — source of the "starting from scratch" and lost-institutional-memory points.
- [Cochrane's COVID-19 living systematic reviews: a mixed-methods study](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12245076/) — documents why living reviews stall in practice: screening burden, waning commitment, funding loss.
- [The Phases of Living Evidence Synthesis Using AI](https://www.jmir.org/2026/1/e76130) (JMIR, 2026) — a team formalizing exactly this workflow with LLMs.
- [A Living Systematic Review Engine: LLM-Automated Evidence Surveillance](https://www.researchsquare.com/article/rs-9308492/v1) (Research Square, 2026) — a team building an adjacent tool, validated against a published meta-analysis.

**People to talk to.** The authors of the last two papers are the strongest interview candidates: they are building adjacent tools right now and have already hit the problems Distill will hit. The Elliott et al. author group (Cochrane living evidence) knows the organizational failure modes better than anyone.

**Cheapest next validation.** Email the corresponding authors of the JMIR and Research Square papers. Ask what broke in their pipelines, not whether they like the idea.

**What kills this bet.** The rigor bar. This community validates tools against published meta-analyses and may reject LLM judgment calls (triage, stance, novelty) outright, regardless of provenance quality.

### P2 — ML researchers tracking a fast-moving subfield

**Who.** Researchers and research engineers who need to stay current on a subfield (e.g., data curation, RLHF, retrieval) while doing their own work.

**Current workflow.** Ad-hoc: arXiv scanning, Twitter/X, newsletters, journal clubs, recommendation tools. Discovery is over-served; synthesis is unserved. Nothing tells them what the accumulating results *mean* for the questions they care about.

**Bottleneck.** Reading volume, and the absence of any durable record of "what do we currently believe about question X, and what moved it."

**What Distill changes.** A living wiki plus hypothesis store for their subfield: new papers land as evidence on standing questions instead of items in a feed.

**Evidence today.** `indirect` only — the weakest of the three. The pain is inferred from reading-load statistics and from the density of half-solutions, not from first-person complaints:

- [Paper Copilot](https://arxiv.org/pdf/2409.04593), [PaperWeaver](https://arxiv.org/pdf/2403.02939), [Intelligent Arxiv](https://arxiv.org/pdf/2002.02460) — each of these papers opens by documenting the paper-overload problem before proposing a recommender-style fix.
- [arXiv@25 user survey](https://arxiv.org/pdf/1607.08212) — background on how researchers actually use arXiv.
- The tool landscape itself: arXiv Sanity (Karpathy), [Scholar Inbox](https://www.scholar-inbox.com/) (Geiger lab, Tübingen), [Emergent Mind](https://www.emergentmind.com/about). All discovery, none synthesis.

**People to talk to.** Maintainers of the tools above — they see usage data and churn reasons. The authors of Paper Copilot and PaperWeaver studied user needs directly.

**Cheapest next validation.** The Reddit/HN lurking pass that web search could not reach: r/MachineLearning threads on keeping up with papers, read directly. This is the doc's most urgent missing evidence.

**What kills this bet.** The discovery layer is saturated with free tools, and this audience may not trust LLM synthesis enough to read a machine-maintained wiki over skimming abstracts themselves.

### P3 — Analysts and "state of X" briefing writers

**Who.** People whose job output is a recurring synthesis for someone else: technology analysts, science journalists, strategy and policy staff, newsletter authors. This is the persona the current demo config (data advantages in AI, briefed for technical decision-makers) implicitly targets.

**Current workflow.** Deep research runs plus manual verification plus manual re-runs as the field moves.

**Bottleneck.** Verification cost. The tools produce confident output whose errors are invisible without redoing the work (see §4, finding 1).

**What Distill changes.** Every briefing claim traces to a signal, a source, and a credibility weight. Confidence is calibrated (a posterior, not a tone). Re-runs are increments.

**Evidence today.** `forum` — real first-person complaints, but from generalist tool users, not confirmed members of this persona:

- [Hacker News: The Deep Research problem](https://news.ycombinator.com/item?id=43133207) — the richest single complaint thread found so far.
- [LessWrong: AI Deep Research Tools Reviewed](https://www.lesswrong.com/posts/chPKoAoR2NfWjuik4/ai-deep-research-tools-reviewed) — a hands-on comparative review; the author's workflow (manual follow-up rounds) is itself evidence.
- [Exploring the Dilemma of AI Use in Medical Research and Knowledge Synthesis](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12288101/) — a published perspective on deep-research-tool limitations.

**People to talk to.** The LessWrong review author (reachable via the post) did exactly the comparative evaluation work this document needs more of.

**Cheapest next validation.** Reply in those threads, or interview two or three newsletter authors who cover a research area.

**What kills this bet.** Deep research plus manual spot-checking may already be good enough for people whose reputation, not their methodology, carries the trust.

---

## §4 · What the evidence says so far

Two findings hold across personas. Statements below are close paraphrases of the sources, each linked so the exact wording can be checked; one is quoted verbatim.

**Finding 1 — the complaint users voice unprompted is trust, not memory.**

- A commenter in the [HN thread](https://news.ycombinator.com/item?id=43133207) described a Deep Research run on compensation data that completed roughly 60% of the work while presenting itself as complete, forcing manual verification of every figure. *(paraphrase)*
- Another commenter in the same thread made the point that the errors are invisible unless you already know the material — you only notice the floor was rotten after your foot goes through. *(paraphrase)*
- A third summarized the economics: if checking the output takes hours, doing the research yourself is faster. *(paraphrase)*
- The [LessWrong reviewer](https://www.lesswrong.com/posts/chPKoAoR2NfWjuik4/ai-deep-research-tools-reviewed) reported that one tool's claims were not linked to individual sources, which made checking them difficult, and that coverage was capped at roughly 40 sources. *(paraphrase)*
- The wishes expressed in these threads — per-claim citations, confidence levels instead of uniform authoritative tone, curated source lists — map directly onto Distill's evidence provenance, Beta posteriors, and source-credibility scoring. *(our interpretation, not theirs)*

**Implication:** the pitch leads with auditability. "Every claim traces to its source and carries a calibrated confidence" answers the complaint people actually make.

**Finding 2 — the demand for durable state is real but latent; people route around it instead of naming it.**

- The LessWrong reviewer ran separate manual follow-up rounds to catch what the tools missed and to stay current — compensating for absent persistence without asking for persistence. *(paraphrase)*
- Evidence-synthesis teams describe updating a review as "just like starting a review from scratch" ([Systematic Reviews, 2021](https://link.springer.com/article/10.1186/s13643-021-01857-5)). *(verbatim)*
- Median time to update is roughly 3 years for Cochrane reviews and 5 years for others ([PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC7542271/)). *(published figures)*

**Implication:** latent demand must be shown, not claimed. The demo has to let someone *see* durable state working — for example, the diff of a topic's belief store across one week of papers — because no user will ask for a feature they have never seen.

---

## §5 · Decisions this document must earn

A north star that never forces a decision is a mood board. These are the forks, with what would settle each.

1. **Which persona picks the demo topic.** P1 implies a medical question and a validation bar we cannot yet meet. P2 implies a hot ML subfield. P3 implies keeping the current topic (data advantages in AI). **Current state:** leaning P2 or P3; blocked on P2 first-person evidence (the lurking pass) and on any direct conversation with a P3 member. Do not commit demo effort before this is settled.
2. **What the README leads with.** Finding 1 says: auditability and calibrated confidence first, living wiki second, belief graph as the mechanism. **Current state:** tentatively decided; reverse only if interviews contradict Finding 1.
3. **What is out of scope for a part-time solo project.** Medical-grade validation (until P1 evidence demands it and a collaborator appears), any dashboard or app, multi-topic hosting. The artifact is files in a git repo; distribution is people cloning it. **Current state:** decided by capacity, not evidence; revisit only if capacity changes.
