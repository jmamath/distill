"""Source adapter for lab and engineering blog RSS feeds.

Two fetch modes:

1. RSS feed (batch ingestion) — fetch() + parse()
   Fetches RSS 2.0 feeds from AI labs and engineering blogs. Handles the
   three main field variations found across the tracked feeds:
     - Standard RSS 2.0: <description>, <author>, <pubDate>
     - Dublin Core extension: <dc:creator> for author (The Gradient, Vector Institute)
     - content:encoded extension: present in some feeds but not consumed
   Raw payloads are preserved as .xml files without format coercion.

2. HTML scrape (single-post lookup) — fetch_item(url)
   Fetches a single post URL and extracts metadata from HTML meta tags
   (og:title, og:description, article:published_time, etc.). Best-effort:
   blog HTML varies widely and not all fields will be populated for every
   post. Used for ad-hoc runs and smoke testing.
"""

import logging
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date
from email.utils import parsedate_to_datetime

from sources import register
from sources.base import NormalizedItem, SourceAdapter

logger = logging.getLogger(__name__)

_DC_NS = "http://purl.org/dc/elements/1.1/"


@register
class LabBlogAdapter(SourceAdapter):
    """Adapter for lab and engineering blog sources via RSS 2.0."""

    raw_extension = ".xml"
    full_text_mime_type = "text/plain"

    def source_id(self) -> str:
        return "lab_blog"

    def fetch_item(self, url: str) -> NormalizedItem:
        """Fetch metadata for a single blog post by its URL.

        Fetches the article HTML and extracts title, summary, author, and
        publication date from meta tags (og:title, og:description,
        article:published_time, meta name=author). Best-effort: not all
        fields will be populated for every post.

        Args:
            url: Direct URL to the blog post.

        Returns:
            NormalizedItem with metadata extracted from the page HTML.

        Raises:
            RuntimeError: if the HTTP request fails.
        """
        logger.info("Fetching lab blog item metadata: %s", url)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SonarynResearch/1.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                html = resp.read().decode("utf-8", errors="replace")
        except Exception as exc:
            raise RuntimeError(f"Lab blog fetch failed for {url!r}: {exc}") from exc
        return _parse_html_item(html, url)

    def fetch_full_text(self, url: str) -> bytes:
        """Fetch the full text of a blog article by its URL.

        Fetches the article HTML, strips all tags via `_strip_html`, and
        returns the result as UTF-8 encoded plain text.

        Args:
            url: The canonical blog post URL.

        Returns:
            UTF-8 encoded plain text bytes with no HTML tags.

        Raises:
            RuntimeError: if the HTTP request fails.
        """
        logger.info("Fetching lab blog article: %s", url)
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "SonarynResearch/1.0"}
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                html = resp.read().decode("utf-8", errors="replace")
        except Exception as exc:
            raise RuntimeError(f"Lab blog full-text fetch failed for {url!r}: {exc}") from exc
        return _strip_html(html).encode("utf-8")

    def fetch(self, query_params: dict) -> bytes:
        """Fetch RSS XML from a blog feed URL.

        Args:
            query_params: dict with key:
                - url (str): RSS feed URL to fetch

        Returns:
            RSS XML bytes.

        Raises:
            RuntimeError: if the HTTP request fails.
        """
        url = query_params["url"]
        logger.info("Fetching lab blog RSS: %s", url)
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "SonarynResearch/1.0"}
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read()
        except Exception as exc:
            raise RuntimeError(f"Lab blog fetch failed: {exc}") from exc

    def parse(self, raw: bytes) -> list[NormalizedItem]:
        """Parse RSS 2.0 XML into NormalizedItem records.

        Handles dc:creator for author fields (The Gradient, Vector Institute, etc.).
        Summary is derived from <description> (HTML-stripped), falling back to title.

        Args:
            raw: RSS XML bytes from a feed URL or a fixture file.

        Returns:
            List of NormalizedItem, one per <item> element.

        Raises:
            ValueError: if the XML is malformed or <channel> is missing.
        """
        # Some WordPress feeds declare a default namespace on <rss> (e.g.
        # xmlns="com-wordpress:feed-additions:1"), which namespaces every plain
        # element and breaks xpath lookups. Strip it before parsing.
        raw = re.sub(rb'\s+xmlns="[^"]*"', b"", raw)

        try:
            root = ET.fromstring(raw)
        except ET.ParseError as exc:
            raise ValueError(f"Lab blog response is not valid XML: {exc}") from exc

        channel = root.find("channel")
        if channel is None:
            raise ValueError("RSS feed missing <channel> element")

        publisher_el = channel.find("title")
        publisher = (publisher_el.text or "").strip() if publisher_el is not None else ""

        items = []
        for item in channel.findall("item"):
            title = _text(item, "title")
            link = _text(item, "link")
            guid_el = item.find("guid")
            url = link or ((guid_el.text or "").strip() if guid_el is not None else "")

            pub_raw = _text(item, "pubDate")

            # Author: prefer dc:creator over <author>
            dc_creator = item.find(f"{{{_DC_NS}}}creator")
            author_el = item.find("author")
            author_raw = (
                (dc_creator.text or "").strip()
                if dc_creator is not None
                else (author_el.text or "").strip() if author_el is not None else ""
            )

            # Summary: plain-text stripped <description>
            desc_raw = _text(item, "description")
            summary = _strip_html(desc_raw) if desc_raw else title

            items.append(NormalizedItem(
                source_id="lab_blog",
                source_type="lab_post",
                title=title,
                url=url,
                published_at=_iso_date(pub_raw),
                authors=[author_raw] if author_raw else [],
                publisher=publisher or None,
                summary=summary,
                metadata={"feed_publisher": publisher},
            ))

        return items


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_html_item(html: str, url: str) -> NormalizedItem:
    """Extract a NormalizedItem from blog post HTML via meta tags.

    Tries og: properties first (most reliable across modern blogs), then
    falls back to standard meta name= attributes, then degrades gracefully
    to the page title or raw URL when nothing is found.

    Args:
        html: Full HTML source of the blog post page.
        url: Canonical URL of the post (used as fallback title and item URL).

    Returns:
        NormalizedItem populated from whatever metadata could be extracted.
    """
    def _meta(*names: str) -> str:
        """Return the content of the first matching meta tag."""
        for name in names:
            for attr in ("property", "name"):
                m = re.search(
                    rf'<meta[^>]+{attr}=["\'](?:og:)?{re.escape(name)}["\'][^>]+content=["\']([^"\']+)["\']',
                    html, re.IGNORECASE,
                )
                if not m:
                    m = re.search(
                        rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+{attr}=["\'](?:og:)?{re.escape(name)}["\']',
                        html, re.IGNORECASE,
                    )
                if m:
                    return m.group(1).strip()
        return ""

    title = _meta("title")
    if not title:
        m = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
        title = m.group(1).strip() if m else url

    summary = _meta("description") or _strip_html(html)[:500]

    # article:published_time is the most reliable publication date signal.
    # Fall back to today when no date is found — better than an empty string
    # that would break downstream date-dependent logic (signal path, freshness).
    published_raw = _meta("article:published_time", "published_time")
    published_at = published_raw[:10] if published_raw else date.today().isoformat()

    author = _meta("author")

    return NormalizedItem(
        source_id="lab_blog",
        source_type="lab_post",
        title=title,
        url=url,
        published_at=published_at,
        authors=[author] if author else [],
        summary=summary,
    )


def _text(element: ET.Element, tag: str) -> str:
    el = element.find(tag)
    return (el.text or "").strip() if el is not None else ""


def _strip_html(text: str) -> str:
    """Remove HTML tags and collapse whitespace."""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", text)).strip()


def _iso_date(raw: str) -> str:
    """Convert RFC 2822 pubDate to ISO 8601 date (YYYY-MM-DD)."""
    if not raw:
        return ""
    try:
        return parsedate_to_datetime(raw).date().isoformat()
    except Exception:
        return raw
