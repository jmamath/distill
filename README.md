# Distill

A modular research knowledge and briefing engine.

Distill watches sources — arXiv, research lab blogs — scores incoming signals against a durable topic wiki, and generates strategic briefings tailored to a target audience. Both the research topic and the audience are configuration, not code.

The first example covers **emerging data advantages in AI**, briefed for **technical decision-makers**. Swap the topic config and audience profile to cover any research domain and reader.

## How it works

1. **Source adapters** fetch and normalise items from arXiv RSS feeds and lab blogs
2. **Scoring pipeline** runs two passes: a cheap model filters on abstract relevance, an expensive model scores the full signal
3. **Wiki updater** classifies signals as replication, adjacent, or new; writes to theme files, entities, and timeline accordingly
4. **Briefing generator** produces a structured briefing for a target audience profile

Storage is file-based: Markdown for narrative (themes, overview), JSON for structured data (entities, timeline, open questions). No database.

## Setup

```bash
git clone https://github.com/your-username/distill
cd distill
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
# edit .env and add your GEMINI_API_KEY
```

## Running tests

```bash
PYTHONPATH=src pytest tests/
```

Tests are offline by default — the Gemini client is mocked. No API key required for `pytest`.

## Bootstrapping a new topic

1. Write a deep-research dossier for your topic and save it to `data/research_topics/{topic_id}/dossiers/bootstrap_{date}.md`
2. Run the seeder:

```bash
PYTHONPATH=src python -m topics.bootstrap.seeder \
    --dossier data/research_topics/{topic_id}/dossiers/bootstrap_{date}.md
```

3. Review the generated wiki under `data/research_topics/{topic_id}/`

See [docs/research_briefing_architecture.md](docs/research_briefing_architecture.md) for the full architecture and [docs/15_knowledge_management_briefing_engine.md](docs/15_knowledge_management_briefing_engine.md) for the implementation plan.

## Project layout

```
src/          Python package root (PYTHONPATH=src)
tests/        pytest suite with offline fixtures
data/         Topics, audiences, credibility data
docs/         Architecture, specs, diagrams
```

## Contributing

Read [AGENTS.md](AGENTS.md) for project conventions and [CODING_PRINCIPLES.md](CODING_PRINCIPLES.md) for code style.
