"""Topic-to-source resolution for the research briefing pipeline.

Reads the enabled_sources list from a TopicConfig and returns the corresponding
registered SourceAdapter instances. Fails loudly if a source id has no registered
adapter so misconfigured topics are caught at startup, not mid-run.

Public API:
    resolve_adapters(config) — return adapter instances for a topic config
"""

import logging

from sources import get_adapter
from sources.base import SourceAdapter
from topics.config import TopicConfig

logger = logging.getLogger(__name__)


def resolve_adapters(config: TopicConfig) -> list[SourceAdapter]:
    """Return one adapter instance per enabled source in the topic config.

    Adapters are returned in the order they appear in enabled_sources so
    caller-side priority ordering is preserved without extra sorting.

    Args:
        config: A validated TopicConfig with an enabled_sources list.

    Returns:
        List of SourceAdapter instances, one per enabled source id.

    Raises:
        ValueError: if any source id in enabled_sources has no registered adapter.
    """
    adapters = []
    for sid in config.enabled_sources:
        adapter = get_adapter(sid)   # raises ValueError on unknown id
        logger.debug("Resolved adapter: %s", sid)
        adapters.append(adapter)
    return adapters
