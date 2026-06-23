# Research Topics

Each subdirectory here is one **topic workspace** — a self-contained store of
everything the pipeline knows about a research area.

---

## Directory layout

```
data/research_topics/{topic_id}/
├── topic.md          ← Topic config (YAML frontmatter). The pipeline's primary input.
├── overview.md       ← Landing view; mix of rendered aggregates and editorial slot (15.0)
├── hypotheses.json   ← Durable belief records, including low-evidence open hypotheses
├── evidence.json     ← Evidence records linked to hypotheses and signal provenance
├── entities.json     ← Flat array of entities (lab, dataset, method, benchmark…)
├── timeline.json     ← Flat array of notable dated events
├── themes/           ← One .md per theme; body grows as signals land (15.0)
│   └── {theme_id}.md
├── signals/          ← One .md per scored signal, partitioned by date (15.3)
│   └── {yyyy}/{mm}/{dd}/{signal_id}.md
├── raw/              ← Original fetched source payloads for traceability (15.3)
│   └── {yyyy-mm-dd}/{source_name}{.xml/.html}
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
| `scope_in` | list of strings | Signal classes and topics that count as in-scope |
| `scope_out` | list of strings | Explicit exclusions |
| `signal_classes` | list of `SignalClass` enum values | Which signal types to accept |
| `source_priorities` | ordered list of strings | Preferred sources, most- to least-preferred |
| `taxonomy` | list of `{id, name, theme_ref}` | Subtopic areas; `theme_ref` links each entry to its theme file (e.g. `themes/synthetic-data-generation.md`) |
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

## Storage access: `src/topics/storage.py`

`storage.py` is the **canonical storage front door**. Downstream stages import
their storage operations from there rather than re-deriving file logic, so the
on-disk contract has one owner. It layers:

- **File primitives** — frontmatter read/write/update (re-exported from
  `frontmatter.py`) and flat JSON-array `load` / `save` / `merge_by_id`.
- **Belief-graph accessors** — `load`/`save` for `hypotheses.json` and
  `evidence.json`, the credibility-weighted `strength` increment with provenance
  append, and the Beta `alpha`/`beta` belief update. These are pure storage
  *mechanics*; *which* hypothesis a signal touches is decided by the updater
  (Plan 9), not here.
- **Raw payloads** — `save_raw_payload` persists fetched bytes under `raw/` in
  native format.

`merge_by_id` keeps existing records unchanged and appends only unseen ids, so
re-running the seeder or replaying a batch is idempotent — it never duplicates or
silently rewrites a row. Updating an existing record is a deliberate load → edit
→ save, not a side effect of merging.

## Belief graph: `hypotheses.json` and `evidence.json`

The belief graph is stored as two flat JSON arrays (no graph database):

- **`hypotheses.json`** — node state. Each record is a single *directional,
  resolvable bet*; belief is a Beta distribution `(alpha, beta)` initialised at
  the uniform prior `(1.0, 1.0)`. All rendering derivatives (mean, confidence,
  convergence) are computed at read time, never stored. Read belief as **both**
  its mean and its evidence mass (`alpha + beta`) — a `(1,1)` tie means
  ignorance, a `(40,40)` tie means entrenched conflict. Dependency edges live on
  the record under `depends_on`.
- **`evidence.json`** — evidence updates linked to hypotheses. `stance` is
  `for | against | mixed` (a `neutral` verdict is filtered at link time and never
  stored — belief-irrelevant facts route to `entities.json`/`timeline.json`).
  `strength` is a weighted accumulator (sum of `weight_applied = source_credibility / 10`
  across contributing signals; null credibility falls back to a fixed neutral
  weight, `storage.NEUTRAL_CREDIBILITY_WEIGHT`); `provenance` is an append-only
  list of `{signal_id, weight_applied}`.

Open questions are **not** a separate store: an open question is simply a
low-evidence hypothesis sitting near its uniform prior. The full field-level
schema and authoring rules live in the storage plan
(`docs/planning/.../8_storage_layer.md`).

## Signal files: `signals/{yyyy}/{mm}/{dd}/{signal_id}.md`

Scored signals are Markdown with YAML frontmatter, written by the pass-2 scorer
(`src/topics/scoring.py`). Frontmatter carries the scoring outputs the belief
graph consumes — `source_credibility`, `new_evidences` (each `{claim, stance}`),
`candidate_themes`, and applicability/significance scores. Signal-specific
read/update helpers (the `classification` and `theme_id_assigned` write-back)
live with the wiki updater in Plan 9, not in `storage.py`.

## Reference rule: forward-only links

Files only list what they point to, not what points to them. A theme declares
its `key_entity_ids`; an entity does not store a back-list of themes. Reverse
queries are answered by scanning frontmatter on demand. This keeps each fact
canonical in one place.

Open questions are not stored in a separate `open_questions.json` file. They
are low-evidence hypotheses in `hypotheses.json`; rendered views such as
`overview.md` derive their "open" sections from that belief state.

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
