# Distill — Agent Instructions

> **Read this first.** This file gives any AI agent the context needed to work effectively in this repo.

---

## How to work with me

**I work on this project part-time.** I am not in the code every day, and I lose the low-level details between sessions. Pitch things at the level of concepts and consequences, not implementation mechanics. Assume I have forgotten the wiring and need the shape of the situation rebuilt before any detail lands.

**Lead with the bottom line (BLUF — Bottom Line Up Front).** Open every answer with the conclusion or recommendation in one or two sentences — the "so what" — before any supporting detail. I should be able to stop reading after the first lines and still have the answer. Caveats, evidence, and specifics go *below* the bottom line, and only as deep as the decision in front of me needs.

**Stay high level by default.** When you analyse something — dependencies, trade-offs, unclear points — give me the shape and a recommended path, not an exhaustive low-level inventory. Name files and line numbers only when I ask to go deeper, or when I need them to act. If you find yourself producing a long list of fine-grained items, stop and collapse it into the two or three decisions that actually matter; that is what I can act on part-time.

---

## What is Distill?

A modular research knowledge and briefing engine. Distill monitors sources (arXiv, research lab blogs), scores incoming signals against a durable topic wiki, updates the wiki with relevant findings, and generates strategic briefings tailored to a target audience — all without a dashboard or app.

Both the research topic and the audience are configuration, not code. The first example covers **emerging data advantages in AI**, briefed for **technical decision-makers**. Swap the topic config and audience profile to cover any research domain and reader.

---

## Architecture

**Pipeline stages:**
1. **Source adapters** (`src/sources/`) — fetch and normalise items from arXiv RSS feeds and lab blogs into a uniform `NormalizedItem` schema
2. **Scoring** (`src/topics/scoring.py`) — two passes: cheap Gemini Flash for abstract-level relevance filtering, expensive Gemini Pro for full scoring
3. **Wiki update** — classify signals as replication / adjacent / new; update theme files, entities, and timeline accordingly
4. **Briefing generation** — produce strategic briefings for a target audience profile

**Storage:** File-based. Topics live under `data/research_topics/{topic_id}/`. No database.

**Key architectural choices:**
- Hybrid storage: Markdown for narrative (themes, overview), JSON for reference data and belief state (entities, timeline, hypotheses, evidence)
- Forward-only links: themes declare `key_entity_ids`; entities don't back-reference themes
- Stable `<a id="...">` anchors inside theme files for precise adjacent updates

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python ≥ 3.11 |
| Data models | Pydantic v2 |
| Config loading | python-dotenv |
| AI — filtering | Gemini Flash (cheap, abstract-level) |
| AI — scoring & generation | Gemini Pro (quality, full-text) |
| Storage | File-based: Markdown + JSON |
| Tests | pytest |

---

## Project Structure

```
src/                          ← Python package root (set PYTHONPATH=src)
  config.py                   ← Env var loading (GEMINI_API_KEY, model names)
  sources/                    ← Source adapter implementations
    base.py                   ← SourceAdapter ABC & NormalizedItem contract
    arxiv.py                  ← arXiv RSS adapter
    lab_blog.py               ← Research lab blog adapter
  topics/                     ← Topic knowledge & scoring pipeline
    config.py                 ← TopicConfig, AudienceProfile schema & loaders
    models.py                 ← Pass1Score, Pass2Score (Pydantic)
    scoring.py                ← Signal scoring pipeline
    credibility.py            ← Source credibility scoring
    frontmatter.py            ← YAML frontmatter parsing utilities
    prompts.py                ← LLM prompts for scoring/enrichment
    sources.py                ← Topic-to-source resolver
    bootstrap/                ← Initial topic seeding workflow
      parser.py               ← parse_dossier() — validates raw dossier text
      seeder.py               ← seed_topic() — writes wiki files from dossier
      prompt.py               ← LLM prompt for dossier generation

tests/                        ← pytest test suite
  fixtures/                   ← Real RSS feed payloads (arXiv, lab blogs)

data/
  audiences/                  ← Audience profile files (Markdown with frontmatter)
  credibility/                ← Source credibility data (README + generated JSON)
  research_topics/            ← Topic knowledge stores
    {topic_id}/
      topic.md                ← Topic config (frontmatter: id, thesis, scoring dims)
      overview.md             ← Landing page (themes + top open hypotheses)
      entities.json           ← Flat array of entity records
      timeline.json           ← Flat array of dated events
      hypotheses.json         ← Flat array of resolvable bets (Beta belief state)
      evidence.json           ← Flat array of evidence linked to hypotheses
      source_credibility.json ← Institution credibility scores
      themes/                 ← One .md file per theme
      dossiers/               ← Archived deep-research bootstrap inputs

docs/
  research_briefing_architecture.md  ← Core architecture (authoritative)
  planning/                     ← Task plans (backlog / doing / done)
  specs/                      ← Task specs (.test.md files)
  diagrams/                   ← Architecture flow diagrams
```

---

## Running Tests

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env  # fill in GEMINI_API_KEY
PYTHONPATH=src pytest tests/
```

Tests are offline by default — Gemini is mocked. No API key needed for `pytest`.

---

## Planning Workflow & Source of Truth

Not all docs carry equal authority. When they disagree, trust them in this order:

1. **The code and tests** — the ground truth for what exists today.
2. **Plans in `docs/planning/doing/` and `docs/planning/done/`** — authoritative and fine-grained. These reflect decisions actually made and (for `done/`) shipped. Schema examples and field semantics here are real.
3. **Plans in `docs/planning/backlog/`** — directional, not final. They are intentionally **coarser**: details (exact schemas, thresholds, constants) are deliberately deferred and get pinned down only when a plan moves into `doing/`. Do not treat backlog field names, numbers, or structures as settled.
4. **`docs/research_briefing_architecture.md`** — a **brainstorming / design document**, not a spec. It was written early while exploring ideas with other models and is explicitly **non-authoritative**. Where it conflicts with a plan, the plan wins. Use it for high-level intent and vocabulary, not for implementation contracts.

Plans flow `backlog/ → doing/ → done/`. Refinement happens at the `doing/` boundary: that is when coarse intent becomes concrete schema. Expect — and surface — inconsistencies between the architecture doc and the plans, and between backlog plans and the implemented system.

### Done plans are immutable — never reopen them

A plan in `done/` is a record of what shipped. **Do not edit or reopen it when scope changes.** If new work touches an area a done plan covered, write a **new plan** for the remaining work and place it in `doing/`. Reference the older plan from the new one — never the reverse.

This exists because reopening done plans creates **circular dependencies**. We hit exactly this: Plan 8 depended on Plans 1 and 7, while reopened revisions *inside* Plans 1 and 7 depended back on Plan 8 — an unresolvable cycle that made the whole chain hard to reason about. Keep dependencies **one-directional**: a newer plan may depend on an older, shipped one, never the other way around. If you ever spot a cycle, it means a done plan was reopened — split the new work out into its own plan instead.

## Specs System

Task specs live in `docs/specs/` as `.test.md` files. Each spec:
- Has YAML frontmatter: `name`, `plan`, `executor`, `kind`, `status`
- Includes a `> **Why:** ...` blockquote on each step explaining the user-visible or business risk if the check fails
- For `executor: script` tests, a corresponding pytest file exists in `tests/`

---

## Coding Principles

Read `CODING_PRINCIPLES.md` for the full set. The highlights:

1. **KISS** — Simplicity and readability over cleverness
2. **Design by Contract** — Every function has a docstring stating its *contract*, not its mechanics. Keep what a caller needs to use it correctly without reading the body: intent, preconditions (inputs + constraints), postconditions (observable guarantees like "returns a new object, input not mutated"), invariants, caller responsibilities, and exceptions. Cut prose that re-narrates the steps — the body is the only honest description of *how*, and narration drifts out of sync. Enumerating control-flow branches counts as mechanics even when phrased as behaviour (e.g. listing what each `if/elif` arm does just transcribes the ladder); branch *rationale* the code can't reveal goes as a terse inline comment at that branch. Don't hardcode a constant's literal value in prose — reference the named constant.
3. **Strict Type Hinting** — Full annotations everywhere; no `Any`
4. **Fail Fast** — Raise on contract breach, never swallow errors silently
5. **Isolate Side-Effects** — Separate pure logic from I/O
6. **Human Oversight Legibility** — Every agent artifact must answer "why should I care?" before asking a human to act

---

## Working Conventions

- **Commit messages** describe what changed and why, not just the task number
- **Plan tasks** open with business motivation before technical details
- **Tests** are for humans first — the Why line matters
- **File-level docstrings** are mandatory: every file states why it exists and how to run it
- **Logging:** entry points call `logging.basicConfig` with `%(asctime)s - %(name)s - %(levelname)s - %(message)s`; all other modules use `logging.getLogger(__name__)` only
- **Commits:** never commit without explicit instruction from the human; never add agent attribution lines

