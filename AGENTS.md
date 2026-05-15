# Distill — Agent Instructions

> **Read this first.** This file gives any AI agent the context needed to work effectively in this repo.

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
- Hybrid storage: Markdown for narrative (themes, overview), JSON for reference data (entities, timeline, open questions)
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
    models.py                 ← AbstractScore, FullScore (Pydantic)
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
      overview.md             ← Landing page (themes + top open questions)
      entities.json           ← Flat array of entity records
      timeline.json           ← Flat array of dated events
      open_questions.json     ← Flat array of open research questions
      source_credibility.json ← Institution credibility scores
      themes/                 ← One .md file per theme
      dossiers/               ← Archived deep-research bootstrap inputs

docs/
  research_briefing_architecture.md  ← Core architecture (authoritative)
  15_knowledge_management_briefing_engine.md  ← Implementation plan
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

## Specs System

Task specs live in `docs/specs/` as `.test.md` files. Each spec:
- Has YAML frontmatter: `name`, `plan`, `executor`, `kind`, `status`
- Includes a `> **Why:** ...` blockquote on each step explaining the user-visible or business risk if the check fails
- For `executor: script` tests, a corresponding pytest file exists in `tests/`

---

## Coding Principles

Read `CODING_PRINCIPLES.md` for the full set. The highlights:

1. **KISS** — Simplicity and readability over cleverness
2. **Design by Contract** — Every function has a docstring with inputs, outputs, exceptions
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
