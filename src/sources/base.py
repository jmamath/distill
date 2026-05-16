"""Shared adapter interface and normalized item contract.

Every source adapter must subclass SourceAdapter and implement its three
abstract methods. 
NormalizedItem is the single output shape all downstream
stages (scoring, wiki updater, tweet generator) consume — no adapter-specific
fields leak into the top-level model.

Public API:
    NormalizedItem   — Pydantic model for one normalized research signal
    SourceAdapter    — ABC that all adapters must implement
"""

from abc import ABC, abstractmethod

from pydantic import BaseModel


class NormalizedItem(BaseModel):
    """One research signal normalized from any source adapter.

    Fields common to all sources sit at the top level. Source-specific
    fields (arxiv category, feed publisher name, etc.) are preserved in
    `metadata` so traceability is not lost without polluting the contract.
    """

    source_id: str
    source_type: str
    title: str
    url: str
    published_at: str          # ISO 8601 date, e.g. "2024-06-12"
    authors: list[str] = []    # individual author names (papers, bylined posts)
    publisher: str | None = None  # publishing org (labs, blog channels)
    summary: str
    metadata: dict = {}        # verbatim source-specific fields
    full_text_fetched: bool = False


class SourceAdapter(ABC):
    """Base class for all research source adapters.

    Subclasses declare `raw_extension` (the file extension for archived
    payloads) and implement the three abstract methods below. Adapters are
    registered automatically when imported — see sources/__init__.py.
    """

    raw_extension: str = ".bin"
    full_text_mime_type: str = "application/octet-stream"

    @abstractmethod
    def source_id(self) -> str:
        """Stable string key identifying this adapter (e.g. 'arxiv').

        Returns:
            A lowercase, hyphen-or-underscore identifier that matches the
            value used in topic.md's enabled_sources list.
        """
        ...

    @abstractmethod
    def fetch(self, query_params: dict) -> bytes:
        """Fetch a raw payload from the source.

        Args:
            query_params: Source-specific parameters (search terms, feed URL,
                date range, pagination offset, etc.).

        Returns:
            Raw bytes in the source's native format (Atom XML, RSS, HTML…).

        Raises:
            RuntimeError: if the network request fails.
        """
        ...

    @abstractmethod
    def parse(self, raw: bytes) -> list[NormalizedItem]:
        """Parse a raw payload into normalized items.

        Args:
            raw: Bytes from fetch() or a fixture file.

        Returns:
            List of NormalizedItem records. Empty list if the payload contains
            no usable items.

        Raises:
            ValueError: if the payload is malformed or cannot be parsed.
        """
        ...

    @abstractmethod
    def fetch_full_text(self, url: str) -> bytes:
        """Fetch the full text of a single item by its URL.

        Args:
            url: The canonical item URL (abstract page, blog post, etc.).

        Returns:
            Raw bytes whose MIME type matches `full_text_mime_type`.

        Raises:
            RuntimeError: if the fetch fails.
        """
        ...
