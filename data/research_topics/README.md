# Research Topics

Each subdirectory here is one **topic workspace** — a self-contained store of
everything the pipeline knows about a research area.

---

## Directory layout

```
data/research_topics/{topic_id}/
├── topic.md          ← Topic config (YAML frontmatter). The pipeline's primary input.
├── taxonomy.md       ← Human-readable subtopic schema and boundaries (15.3)
├── overview.md       ← Landing view; mix of rendered aggregates and editorial slot (15.0)
├── watchlist.md      ← Open questions and standalone watch items (15.0)
├── themes/           ← One .md per theme; body grows as signals land (15.0)
│   └── {theme_id}.md
├── entities/         ← One .md per entity (lab, dataset, method, benchmark…) (15.0)
│   └── {entity_id}.md
├── timeline/         ← One .md per notable dated event; frozen after creation (15.0)
│   └── {yyyy-mm-dd-slug}.md
├── signals/          ← One .md per scored signal, partitioned by date (15.3)
│   └── {yyyy}/{mm}/{dd}/{signal_id}.md
├── raw/              ← Original fetched source payloads for traceability (15.3)
│   └── {yyyy-mm-dd}/{source_name}.json
├── dossiers/         ← Pasted outputs from deep-research runs (15.0)
│   └── {purpose}_{yyyy-mm-dd}.md
└── briefings/        ← Generated briefs; status in frontmatter (15.6)
    └── {yyyy-mm-dd}.md
```

Numbers in parentheses indicate which task first creates each path.

---

## Topic config (`topic.md`)

`topic.md` is the primary input to every pipeline stage. Its YAML frontmatter
is loaded and validated by `topics.config.load_topic_config` into a `TopicConfig`
object. **Do not scatter topic-specific logic across the codebase** — it belongs
in `topic.md`.

Required frontmatter fields:

| Field | Type | Purpose |
|---|---|---|
| `topic_id` | string | Stable identifier (used in file paths and frontmatter) |
| `name` | string | Human-readable topic name |
| `thesis` | string | One-paragraph statement of what this brief tracks |
| `audience_ref` | string | ID of the audience profile in `data/audiences/` |

Optional fields (added incrementally as the pipeline matures):

| Field | Type | Purpose |
|---|---|---|
| `bootstrap_horizon` | string | Historical lookback for the deep-research bootstrap prompt (e.g. "2012–present") |
| `signal_horizon` | string | Recency window for live signal ingestion (e.g. "rolling 60 days") |
| `scope_in` | list of strings | Signal classes and topics that count as in-scope |
| `scope_out` | list of strings | Explicit exclusions |
| `signal_classes` | list of `SignalClass` enum values | Which signal types to accept |
| `source_priorities` | ordered list of strings | Preferred sources, most- to least-preferred |
| `taxonomy` | list of `{id, name, description}` | Subtopic areas for organising themes |
| `scoring_dimensions` | list of `{id, name, description}` | Axes used to score a signal |
| `action_vocabulary` | list of `ActionLabel` enum values | Allowed action recommendations |

See `src/topics/config.py` for the full schema.

---

## Audience profiles (`data/audiences/`)

Audience profiles live outside the topic workspace so they can be shared across
topics. A profile is a Markdown file with YAML frontmatter:

| Field | Purpose |
|---|---|
| `audience_id` | Stable ID (must match `audience_ref` in topic.md) |
| `name` | Human-readable name |
| `description` | Who this audience is |
| `persona` | Reading behaviour and decision-making style |
| `scope` | What kinds of decisions this audience makes |
| `tone` | How the brief should address them |

---

## Reference rule: forward-only links

Files only list what they point to, not what points to them. A theme declares
its `key_entity_ids`; an entity does not store a back-list of themes. Reverse
queries are answered by scanning frontmatter on demand. This keeps each fact
canonical in one place.

---

## Adding a new topic

1. Create `data/research_topics/{new_topic_id}/topic.md` with at least the four
   required frontmatter fields (`topic_id`, `name`, `thesis`, `audience_ref`).
2. Verify it loads: `python -c "from topics.config import load_topic_config; from pathlib import Path; print(load_topic_config(Path('data/research_topics/{new_topic_id}/topic.md')))"`
3. If the topic needs a new audience profile, create `data/audiences/{audience_ref}.md`.
4. Run the bootstrap prompt generator (`src/topics/bootstrap/prompt.py`) to get
   the deep-research prompt for this topic.
5. Paste the dossier output and run the seeder (`src/topics/bootstrap/seeder.py`)
   to seed the wiki.

No orchestration code changes are needed to add a new topic.
