"""Prompt builders for the topic-aware signal scoring pipeline.

Pass-1 and pass-2 prompts are kept here so scoring.py stays focused on
orchestration and the prompt text is independently readable and testable.

Public API:
    build_pass1_prompt(item, topic_config) → str
"""

from sources.base import NormalizedItem
from topics.config import TopicConfig


def build_pass1_prompt(item: NormalizedItem, topic_config: TopicConfig) -> str:
    """Build the pass-1 relevance scoring prompt.

    Context included: topic thesis, scope_in/out lists, taxonomy subtopics,
    and the item's title + abstract. Full text is intentionally excluded —
    that is pass-2's input.

    Args:
        item: The normalized signal to evaluate.
        topic_config: The active topic configuration.

    Returns:
        A prompt string ready for the scoring LLM.
    """
    subtopics = "\n".join(
        f"  - {t.name}: {t.description}" for t in topic_config.taxonomy
    )
    scope_in = "\n".join(f"  - {s}" for s in topic_config.scope_in)
    scope_out = "\n".join(f"  - {s}" for s in topic_config.scope_out)

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
        "Rate the relevance of this signal to the topic on a scale of 0 to 10, "
        "where 0 is completely irrelevant and 10 is directly on-topic. "
        "A score of 6 or above means the signal is relevant enough for full-text scoring. "
        "Score below 6 if the signal concerns AI/ML generally but has no clear data insight "
        "that fits the topic thesis.\n"
        'Respond strictly as JSON: {"relevance": <integer 0-10>, "reason": "<one sentence>"}'
    )
