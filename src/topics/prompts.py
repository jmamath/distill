"""Prompt builders for the topic-aware signal scoring pipeline.

Pass-1 and pass-2 prompts are kept here so scoring.py stays focused on
orchestration and the prompt text is independently readable and testable.

Public API:
    build_pass1_prompt(item, topic_config) → str
    build_pass2_prompt(item, topic_config, theme_definitions) → str
"""

from sources.base import NormalizedItem
from topics.config import TopicConfig


def build_pass1_prompt(
    item: NormalizedItem,
    topic_config: TopicConfig,
    theme_definitions: dict[str, str],
) -> str:
    """Build the pass-1 relevance scoring prompt.

    Context included: topic thesis, scope_in/out lists, taxonomy subtopics,
    and the item's title + abstract. Full text is intentionally excluded —
    that is pass-2's input.

    Args:
        item: The normalized signal to evaluate.
        topic_config: The active topic configuration.
        theme_definitions: Mapping of theme_id → description (single source of
            truth, loaded from themes/*.md frontmatter).

    Returns:
        A prompt string ready for the scoring LLM.
    """
    subtopics = "\n".join(
        f"  - {name}: {desc}" for name, desc in theme_definitions.items()
    )
    scope_in = "\n".join(f"  - {s}" for s in topic_config.scope_in)
    scope_out = "\n".join(f"  - {s}" for s in topic_config.scope_out)
    rubric = "\n".join(
        f"  - {d.id} (0–10): {d.description}" for d in topic_config.pass1_dimensions
    )

    return (
        f"Topic: {topic_config.name}\n"
        f"Thesis: {topic_config.thesis}\n\n"
        f"In scope:\n{scope_in}\n\n"
        f"Out of scope:\n{scope_out}\n\n"
        f"Taxonomy subtopics:\n{subtopics}\n\n"
        f"Signal to evaluate:\n"
        f"Title: {item.title}\n"
        f"Source type: {item.source_type}\n"
        f"Abstract: {item.summary}\n\n"
        f"Scoring rubric:\n{rubric}\n\n"
        'Respond strictly as JSON: {"topical_relevance": <integer 0-10>, "reason": "<one sentence>"}'
    )


def build_pass2_prompt(
    item: NormalizedItem,
    topic_config: TopicConfig,
    theme_definitions: dict[str, str],
) -> str:
    """Build the pass-2 full-text scoring prompt.

    The full text bytes are passed separately as a multimodal part — this
    prompt provides topic context and theme definitions only.  Theme bodies
    and existing wiki evidences are intentionally excluded to avoid anchoring
    the model on current knowledge state.

    Args:
        item: The normalized signal whose full text will be scored.
        topic_config: The active topic configuration.
        theme_definitions: Mapping of theme_id → description (no bodies).

    Returns:
        A prompt string ready for the scoring LLM.
    """
    themes_block = "\n".join(
        f"  - {tid}: {desc}" for tid, desc in theme_definitions.items()
    )
    authors = ", ".join(item.authors) if item.authors else "unknown"
    rubric = "\n".join(
        f"  - {d.id} (0–10): {d.description}" for d in topic_config.pass2_dimensions
    )

    return (
        f"Topic: {topic_config.name}\n"
        f"Thesis: {topic_config.thesis}\n\n"
        f"Available themes (id: description):\n{themes_block}\n\n"
        f"Signal metadata:\n"
        f"  Title: {item.title}\n"
        f"  Source type: {item.source_type}\n"
        f"  Authors: {authors}\n"
        f"  URL: {item.url}\n\n"
        "The full text of this signal is attached. Score each dimension in the rubric "
        "and identify up to three themes it best supports.\n\n"
        f"Scoring rubric:\n{rubric}\n\n"
        "Respond strictly as JSON with this exact schema:\n"
        "{\n"
        '  "applicability_score": <integer 0-10>,\n'
        '  "strategic_significance": <integer 0-10>,\n'
        '  "paper_audience": "<free text: who would benefit most from reading this>",\n'
        '  "candidate_themes": [\n'
        '    {"theme_id": "<id from the list above>", "confidence": <0-10>, '
        '"rationale": "<one sentence: why this confidence level>"}\n'
        "  ],\n"
        '  "new_open_questions": [{"text": "<question text>"}],\n'
        '  "new_evidences": [{"claim": "<claim text>", "stance": "<for|against|mixed|neutral>"}],\n'
        '  "affiliations": ["<author organization as cited in the source>"],\n'
        '  "rationale": "<markdown paragraph explaining the applicability score>"\n'
        "}\n\n"
        "Rules:\n"
        "- candidate_themes: at most 3 entries, sorted by descending confidence.\n"
        "- Only use theme_ids from the list above; omit themes with confidence < 4.\n"
        "- affiliations: list author organizations exactly as cited — do not infer or expand.\n"
        "- rationale: written for a research analyst; focus on what is novel and why it matters."
    )
