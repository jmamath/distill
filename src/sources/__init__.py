"""Source registry for research adapters.

Adapters self-register via the @register decorator when their module is
imported. topics/sources.py calls get_adapter() to resolve source ids from
a topic config. Adding a new adapter only requires implementing SourceAdapter,
decorating the class with @register, and importing the module here.

Public API:
    register(cls)         — class decorator that registers an adapter
    get_adapter(sid)      — return a fresh adapter instance for a source id
    registered_ids()      — sorted list of all registered source ids
"""

import logging

from sources.base import NormalizedItem, SourceAdapter  # noqa: F401 — re-exported

logger = logging.getLogger(__name__)

_REGISTRY: dict[str, type[SourceAdapter]] = {}


def register(cls: type[SourceAdapter]) -> type[SourceAdapter]:
    """Class decorator that registers an adapter under its source_id().

    Args:
        cls: A concrete SourceAdapter subclass.

    Returns:
        cls unchanged (decorator protocol).
    """
    sid = cls().source_id()
    _REGISTRY[sid] = cls
    logger.debug("Registered source adapter: %s", sid)
    return cls


def get_adapter(source_id: str) -> SourceAdapter:
    """Return a fresh adapter instance for the given source id.

    Args:
        source_id: Stable string key (e.g. 'arxiv', 'lab_blog').

    Returns:
        A new SourceAdapter instance.

    Raises:
        ValueError: if no adapter is registered for source_id.
    """
    if source_id not in _REGISTRY:
        raise ValueError(
            f"No source adapter registered for '{source_id}'. "
            f"Registered adapters: {registered_ids()}"
        )
    return _REGISTRY[source_id]()


def registered_ids() -> list[str]:
    """Return all registered source ids in sorted order."""
    return sorted(_REGISTRY)


# Adapters self-register on import. Add new adapters here — no other file
# changes required to make them discoverable.
import sources.arxiv   # noqa: E402, F401
import sources.lab_blog  # noqa: E402, F401
