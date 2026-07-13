"""Bootstrap prompt builder.

Generates the deep-research prompt from a minimal topic.md configuration.
The operator pastes this prompt into an external research agent (e.g. Gemini
Deep Research, Perplexity, or similar) and pastes the full response back as a
dossier file.

The prompt instructs the external agent to return its response as Markdown prose
with one `## Theme: {kebab-id}` heading per theme, followed by exactly one
trailing fenced JSON block.  The seeder uses both: prose sections feed theme
bodies, the JSON block feeds metadata and reference data.

Usage (operator CLI):
    python -m topics.bootstrap.prompt \
        --topic path/to/data_advantage/topic.md
"""

import argparse
import logging
import sys
from pathlib import Path

from topics.config import AudienceProfile, TopicConfig, load_audience_profile, load_topic_config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# JSON schema that the external agent must produce (embedded in the prompt)
# ---------------------------------------------------------------------------

_JSON_SCHEMA = """\
{
  "themes": [
    {
      "id": "<kebab-case-stable-id matching the ## Theme: heading above>",
      "name": "<human-readable name>",
      "description": "<one-sentence summary>",
      "taxonomy_ref": "<taxonomy id from the topic taxonomy, or null>",
      "key_entity_ids": ["<entity-id>", "..."]
    }
  ],
  "entities": [
    {
      "id": "<kebab-case-stable-id>",
      "name": "<canonical name>",
      "entity_type": "<lab|company|dataset|method|benchmark|person|product>",
      "description": "<one-sentence summary>"
    }
  ],
  "timeline": [
    {
      "id": "<YYYY-MM-DD-kebab-slug>",
      "date": "<YYYY-MM-DD>",
      "title": "<short event title>",
      "theme_ids": ["<theme-id>"],
      "entity_ids": ["<entity-id>"],
      "body": "<1-2 sentences: what happened and why it mattered>"
    }
  ],
  "hypotheses": [
    {
      "id": "<kebab-case-stable-id>",
      "statement": "<single directional, resolvable bet>",
      "theme_ids": ["<theme-id>"],
      "action_posture": "<ignore|monitor|prototype|invest>",
      "why_it_matters": "<one sentence explaining the strategic implication>",
      "resolution_criterion": {
        "metric": "<what would be measured, or null if implicit>",
        "threshold": "<yes/no cut, or null if implicit>",
        "scope": "<population/domain this claim ranges over>",
        "horizon": "<YYYY-MM-DD resolution horizon>"
      },
      "comparison": null
    }
  ]
}"""

_PROMPT_TEMPLATE = """\
# Deep Research Request — {name}

## Task

You are a senior ML researcher deeply familiar with the literature on this topic.
You are writing a literature-grounded landscape briefing for other technical readers
who will extend this knowledge base over time. Accuracy about actual contributions,
mechanisms, and trajectories matters more than strategic framing — strategic takes
happen downstream, on top of this substrate. Prefer naming the specific methodological
or empirical contribution over restating what a paper claims for itself.

Your output will seed a durable knowledge base that is updated continuously as new
signals arrive, so structural consistency matters more than exhaustiveness.

## Topic

**Name:** {name}
**Thesis:** {thesis}
{audience_section}\
{horizon_section}\
{scope_in_section}\
{scope_out_section}\
{taxonomy_section}\
## Research questions to address

1. What are the major recurring themes in this topic across the full date horizon?
   Cover all modalities — text, vision, multimodal, code, math, robotics, biology —
   not just LLM pretraining.
2. Which entities (labs, companies, datasets, methods, benchmarks, people, products)
   appear most frequently and matter most? Prioritise highly cited work and
   demonstrably influential releases over exhaustive coverage — depth over breadth.
3. What are the most significant dated milestones across the full date horizon?
   Anchor the timeline at the start of the deep learning era and trace the arc
   forward; do not restrict the timeline to recent years.
4. What unresolved, strategically relevant hypotheses is the field actively debating?

## Output format

Write your response as readable Markdown prose. For **each theme**, write a
`## Theme: {{kebab-id}}` heading (using the same kebab-case id that appears in the
JSON `themes[*].id` field below) followed by 2–4 paragraphs of prose for that theme.

Then — and this is required — **end your response with exactly one fenced JSON
block** that follows the schema below precisely. The JSON block must:
- be the last thing in your response
- use the fence ` ```json ` (opening) and ` ``` ` (closing)
- be valid JSON (no trailing commas, no comments)
- use stable kebab-case IDs for all `id` fields (e.g. `synthetic-data-generation`,
  not `Synthetic Data Generation`)
- include at least 3 themes, 5 entities, 3 timeline entries, and 3 hypotheses
- have every `themes[*].id` in the JSON match a `## Theme: {{id}}` heading in the prose
- write each hypothesis as one directional, resolvable bet: two reviewers should be
  able to settle it the same way once enough evidence arrives
- use `resolution_criterion` wherever the statement is not already unambiguous;
  for comparative bets, populate `comparison` with `subject_a` and `subject_b`

### Required JSON schema

```json
{json_schema}
```

Do not add any text after the closing ` ``` ` of the JSON block.
"""


def build_bootstrap_prompt(topic: TopicConfig, audience_profile: AudienceProfile | None = None) -> str:
    """Build the deep-research prompt from a validated TopicConfig.

    Args:
        topic: Validated TopicConfig loaded from topic.md.
        audience_profile: Optional loaded AudienceProfile. When provided, the
            prompt includes persona, scope, and tone so the research agent can
            pitch its output at the right reader. Falls back to the bare
            audience_ref string when absent.

    Returns:
        A prompt string ready to paste into an external research agent.
    """
    if audience_profile:
        audience = (
            f"**Audience:** {audience_profile.name}\n"
            f"**Persona:** {audience_profile.persona.strip()}\n"
            f"**Scope:** {audience_profile.scope.strip()}\n"
            f"**Tone:** {audience_profile.tone.strip()}\n"
        )
    else:
        audience = f"**Audience:** {topic.audience_ref}\n"
    horizon = (
        f"**Date horizon:** {topic.bootstrap_horizon}\n"
        if topic.bootstrap_horizon
        else ""
    )
    scope_in = (
        "**In scope:** " + ", ".join(topic.scope_in) + "\n"
        if topic.scope_in
        else ""
    )
    scope_out = (
        "**Out of scope:** " + ", ".join(topic.scope_out) + "\n"
        if topic.scope_out
        else ""
    )
    if topic.taxonomy:
        taxonomy_lines = "\n".join(
            f"- **{e.id}** — {e.name}: {e.description.strip()}"
            for e in topic.taxonomy
        )
        taxonomy = (
            "**Taxonomy (existing subtopic areas — organise themes into these "
            "categories where possible; add new ones if significant material "
            "does not fit):**\n\n"
            + taxonomy_lines
            + "\n"
        )
    else:
        taxonomy = ""

    return _PROMPT_TEMPLATE.format(
        name=topic.name,
        thesis=topic.thesis,
        audience_section=audience,
        horizon_section=horizon,
        scope_in_section=scope_in,
        scope_out_section=scope_out,
        taxonomy_section=taxonomy,
        json_schema=_JSON_SCHEMA,
    )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _main() -> None:
    parser = argparse.ArgumentParser(
        description="Print the bootstrap deep-research prompt for a topic."
    )
    parser.add_argument("--topic", required=True, help="Path to topic.md")
    args = parser.parse_args()

    topic_path = Path(args.topic)
    if not topic_path.exists():
        logger.error("topic.md not found: %s", topic_path)
        sys.exit(1)

    try:
        topic = load_topic_config(topic_path)
    except (FileNotFoundError, ValueError) as exc:
        logger.error("Invalid topic.md: %s", exc)
        sys.exit(1)

    audience_profile = None
    data_root = topic_path.parent.parent.parent
    audience_path = data_root / "audiences" / f"{topic.audience_ref}.md"
    if audience_path.exists():
        try:
            audience_profile = load_audience_profile(audience_path)
        except ValueError as exc:
            logger.warning("Could not load audience profile, falling back to ref: %s", exc)

    print(build_bootstrap_prompt(topic, audience_profile))


if __name__ == "__main__":
    _main()
