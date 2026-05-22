"""Source adapter for arXiv papers.

Two fetch modes:

1. RSS feed (batch ingestion) — fetch() + parse()
   Fetches from https://rss.arxiv.org/rss/<category> (e.g. cs.AI) and
   normalises entries into NormalizedItem records. The feed is RSS 2.0 with
   arXiv and Dublin Core extensions. Used by the scheduled pipeline to ingest
   new papers by category.

   Feed structure:
     <item>
       <title>Paper Title</title>
       <link>https://arxiv.org/abs/...</link>
       <description>arXiv:XXXXv1 Announce Type: new \\nAbstract: ...</description>
       <dc:creator>Author One, Author Two</dc:creator>
       <arxiv:announce_type>new|cross|replace</arxiv:announce_type>
       <category>cs.AI</category>
       <pubDate>Mon, 27 Apr 2026 00:00:00 -0400</pubDate>
     </item>

2. Atom API (single-paper lookup) — fetch_item(url)
   Fetches from https://export.arxiv.org/api/query?id_list=<id> and parses
   the Atom response. Used for ad-hoc runs and smoke testing where a single
   known paper URL is the starting point rather than a category feed.
"""

import logging
import re
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

from sources import register
from sources.base import NormalizedItem, SourceAdapter

logger = logging.getLogger(__name__)

_DC_NS = "http://purl.org/dc/elements/1.1/"
_ARXIV_NS = "http://arxiv.org/schemas/atom"
_ATOM_NS = "http://www.w3.org/2005/Atom"

# Strips "arXiv:2604.21935v1 Announce Type: new \n" from description.
_PREAMBLE_RE = re.compile(r"^arXiv:\S+\s+Announce Type:\s+\w+\s*\n", re.IGNORECASE)
_ABSTRACT_LABEL_RE = re.compile(r"^Abstract:\s*", re.IGNORECASE)


@register
class ArxivAdapter(SourceAdapter):
    """Adapter for arXiv papers via the category RSS feed."""

    raw_extension = ".xml"
    full_text_mime_type = "application/pdf"

    def source_id(self) -> str:
        return "arxiv"

    def fetch_full_text(self, url: str) -> bytes:
        """Fetch the PDF for an arXiv paper by its abstract page URL.

        Converts the abstract URL (https://arxiv.org/abs/<id>) to the
        corresponding PDF URL (https://arxiv.org/pdf/<id>) and downloads it.

        Args:
            url: arXiv abstract page URL, e.g. "https://arxiv.org/abs/2404.01234"

        Returns:
            Raw PDF bytes (begins with b"%PDF").

        Raises:
            RuntimeError: if the arXiv ID cannot be extracted or the fetch fails.
        """
        match = re.search(r"arxiv\.org/(?:abs|pdf)/([^\s/?#]+)", url)
        if not match:
            raise RuntimeError(f"Cannot extract arXiv ID from URL: {url!r}")
        arxiv_id = match.group(1)
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}"
        logger.info("Fetching arXiv PDF: %s", pdf_url)
        try:
            req = urllib.request.Request(
                pdf_url, headers={"User-Agent": "SonarynResearch/1.0"}
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.read()
        except Exception as exc:
            raise RuntimeError(f"arXiv PDF fetch failed for {pdf_url!r}: {exc}") from exc

    def fetch_item(self, url: str) -> NormalizedItem:
        """Fetch metadata for a single arXiv paper via the Atom API.

        Uses export.arxiv.org/api/query rather than the RSS feed, so any paper
        can be looked up by ID without waiting for the category feed to include
        it. Useful for smoke testing and ad-hoc pipeline runs.

        Args:
            url: arXiv abstract page URL, e.g. "https://arxiv.org/abs/2306.11644"

        Returns:
            NormalizedItem with real metadata from the Atom API.

        Raises:
            RuntimeError: if the ID cannot be extracted, the request fails, or
                the API returns no entry for the given ID.
        """
        match = re.search(r"arxiv\.org/abs/([^\s/?#]+)", url)
        if not match:
            raise RuntimeError(f"Cannot extract arXiv ID from URL: {url!r}")
        arxiv_id = match.group(1)

        api_url = f"https://export.arxiv.org/api/query?id_list={arxiv_id}"
        logger.info("Fetching arXiv Atom entry: %s", api_url)
        try:
            req = urllib.request.Request(api_url, headers={"User-Agent": "SonarynResearch/1.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read()
        except Exception as exc:
            raise RuntimeError(f"arXiv Atom fetch failed for {arxiv_id!r}: {exc}") from exc

        return _parse_atom_entry(raw, arxiv_id)

    def fetch(self, query_params: dict) -> bytes:
        """Fetch RSS XML from an arXiv category feed.

        Args:
            query_params: dict with key:
                - url (str): arXiv RSS feed URL,
                  e.g. "https://rss.arxiv.org/rss/cs.AI"

        Returns:
            RSS XML bytes.

        Raises:
            RuntimeError: if the HTTP request fails.
        """
        url = query_params["url"]
        logger.info("Fetching arXiv RSS: %s", url)
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "SonarynResearch/1.0"}
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read()
        except Exception as exc:
            raise RuntimeError(f"arXiv fetch failed: {exc}") from exc

    def parse(self, raw: bytes) -> list[NormalizedItem]:
        """Parse arXiv RSS XML into NormalizedItem records.

        Args:
            raw: RSS XML bytes from an arXiv category feed or a fixture file.

        Returns:
            List of NormalizedItem, one per <item> element.

        Raises:
            ValueError: if the XML is malformed.
        """
        try:
            root = ET.fromstring(raw)
        except ET.ParseError as exc:
            raise ValueError(f"arXiv response is not valid XML: {exc}") from exc

        channel = root.find("channel")
        if channel is None:
            raise ValueError("arXiv RSS feed missing <channel> element")

        items = []
        for item in channel.findall("item"):
            title = _text(item, "title")
            link = _text(item, "link")
            pub_raw = _text(item, "pubDate")
            desc_raw = _text(item, "description")

            creator_el = item.find(f"{{{_DC_NS}}}creator")
            announce_el = item.find(f"{{{_ARXIV_NS}}}announce_type")

            authors = _split_creators(
                (creator_el.text or "").strip() if creator_el is not None else ""
            )
            announce_type = (
                (announce_el.text or "").strip() if announce_el is not None else ""
            )

            summary = _extract_abstract(desc_raw)
            categories = [c.text or "" for c in item.findall("category")]
            guid_el = item.find("guid")
            arxiv_id = (guid_el.text or "").strip() if guid_el is not None else ""

            items.append(NormalizedItem(
                source_id="arxiv",
                source_type="paper",
                title=title,
                url=link or arxiv_id,
                published_at=_iso_date(pub_raw),
                authors=authors,
                summary=summary,
                metadata={
                    "arxiv_id": arxiv_id,
                    "categories": categories,
                    "announce_type": announce_type,
                },
            ))

        return items


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_atom_entry(raw: bytes, arxiv_id: str) -> NormalizedItem:
    """Parse a single entry from an arXiv Atom API response.

    Args:
        raw: Raw bytes from the Atom API response.
        arxiv_id: The arXiv ID that was requested (used in the returned URL
            and in the error message if no entry is found).

    Returns:
        NormalizedItem populated from the Atom entry.

    Raises:
        ValueError: if the response is not valid XML.
        RuntimeError: if the response contains no entry for the given ID.
    """
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise ValueError(f"arXiv Atom response is not valid XML: {exc}") from exc

    entry = root.find(f"{{{_ATOM_NS}}}entry")
    if entry is None:
        raise RuntimeError(f"arXiv Atom API returned no entry for ID {arxiv_id!r}")

    def _atom_text(tag: str) -> str:
        el = entry.find(f"{{{_ATOM_NS}}}{tag}")
        return (el.text or "").strip() if el is not None else ""

    authors = [
        (a.find(f"{{{_ATOM_NS}}}name").text or "").strip()
        for a in entry.findall(f"{{{_ATOM_NS}}}author")
        if a.find(f"{{{_ATOM_NS}}}name") is not None
    ]

    return NormalizedItem(
        source_id="arxiv",
        source_type="research_paper",
        title=_atom_text("title").replace("\n", " "),
        url=f"https://arxiv.org/abs/{arxiv_id}",
        published_at=_atom_text("published")[:10],  # YYYY-MM-DD
        authors=authors,
        summary=_atom_text("summary").replace("\n", " "),
    )


def _text(element: ET.Element, tag: str) -> str:
    el = element.find(tag)
    return (el.text or "").strip() if el is not None else ""


def _split_creators(raw: str) -> list[str]:
    """Split 'Author One, Author Two, Author Three' into a list."""
    if not raw:
        return []
    return [name.strip() for name in raw.split(",") if name.strip()]


def _extract_abstract(description: str) -> str:
    """Strip the arXiv preamble and return the plain abstract text."""
    text = _PREAMBLE_RE.sub("", description.strip())
    text = _ABSTRACT_LABEL_RE.sub("", text)
    return text.strip()


def _iso_date(raw: str) -> str:
    """Convert RFC 2822 pubDate to ISO 8601 date (YYYY-MM-DD)."""
    if not raw:
        return ""
    try:
        return parsedate_to_datetime(raw).date().isoformat()
    except Exception:
        return raw
