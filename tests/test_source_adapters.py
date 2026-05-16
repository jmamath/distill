"""Tests for the source adapter contract (Task 15.2).

Fixtures are real RSS payloads fetched from live feeds and stored under
tests/fixtures/. They are NOT invented — running the fetch script again
will produce equivalent (though not byte-identical) files.

arXiv fixtures (ArxivAdapter):
  fixtures/arxiv_cs_ai.xml  — https://rss.arxiv.org/rss/cs.AI   (3 items)
  fixtures/arxiv_cs_lg.xml  — https://rss.arxiv.org/rss/cs.LG   (3 items)
  fixtures/arxiv_cs_cl.xml  — https://rss.arxiv.org/rss/cs.CL   (3 items)

Blog fixtures (LabBlogAdapter) — one per confirmed feed in topic.md:
  fixtures/openai_blog.xml       — https://openai.com/blog/rss.xml                            (3 items)
  fixtures/fair_blog.xml         — https://engineering.fb.com/category/ai-research/feed/      (3 items, WordPress ns)
  fixtures/huggingface_blog.xml  — https://huggingface.co/blog/feed.xml                       (3 items, no description)
  fixtures/deepmind_blog.xml     — https://deepmind.google/blog/rss.xml                       (3 items, inconsistent description)
  fixtures/bair_blog.xml         — https://bair.berkeley.edu/blog/feed.xml                    (3 items, HTML description)
  fixtures/gradient_blog.xml     — https://thegradient.pub/rss/                               (3 items, dc:creator + content:encoded)
  fixtures/vector_institute.xml  — https://vectorinstitute.ai/feed/                           (3 items, dc:creator + content:encoded)

Full-text fixtures (fetch_full_text):
  fixtures/arxiv_paper.pdf        — https://arxiv.org/pdf/2404.01230   (real PDF, offline tests)
  fixtures/lab_blog_article.html  — https://huggingface.co/blog/smollm (real HTML, offline tests)

Run from the project root with the virtualenv active:
    source .venv/bin/activate
    PYTHONPATH=src pytest tests/test_source_adapters.py
"""

import urllib.request
from pathlib import Path

import pytest

import sources  # triggers adapter self-registration
from sources import get_adapter, registered_ids
from sources.arxiv import ArxivAdapter
from sources.base import NormalizedItem, SourceAdapter
from sources.lab_blog import LabBlogAdapter
from topics.config import FeedConfig, TopicConfig, load_topic_config
from topics.sources import resolve_adapters

_REPO_ROOT = Path(__file__).parent.parent
_FIXTURES = Path(__file__).parent / "fixtures"
_TOPIC_PATH = _REPO_ROOT / "data" / "research_topics" / "data_advantage" / "topic.md"


# ---------------------------------------------------------------------------
# 1. arXiv adapter parses real Atom RSS fixture
# ---------------------------------------------------------------------------


def test_arxiv_parse_fixture():
    """arXiv adapter parses the real cs.AI RSS fixture into correct NormalizedItem fields.

    > **Why:** If the arXiv adapter cannot parse its own native format, every
    paper the system tries to ingest is dropped silently — the wiki never
    learns about new research.
    """
    raw = (_FIXTURES / "arxiv_cs_ai.xml").read_bytes()
    items = ArxivAdapter().parse(raw)

    assert len(items) == 3, "Fixture should contain exactly 3 items"

    for item in items:
        assert isinstance(item, NormalizedItem)
        assert item.source_id == "arxiv"
        assert item.source_type == "paper"
        assert item.title
        assert item.url.startswith("https://arxiv.org/abs/")
        assert item.published_at  # non-empty ISO date
        assert len(item.authors) >= 1, "Every arXiv paper has at least one author"
        assert item.summary, "Abstract must be extracted from description"
        assert "Announce Type" not in item.summary, "Preamble must be stripped"
        assert "announce_type" in item.metadata
        assert "categories" in item.metadata


# ---------------------------------------------------------------------------
# 2. arXiv adapter parses all three category fixtures
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("fixture,category", [
    ("arxiv_cs_ai.xml", "cs.AI"),
    ("arxiv_cs_lg.xml", "cs.LG"),
    ("arxiv_cs_cl.xml", "cs.CL"),
])
def test_arxiv_parse_all_category_fixtures(fixture, category):
    """arXiv adapter parses each category RSS fixture into well-formed NormalizedItems.

    > **Why:** cs.LG and cs.CL are the realistic coverage path for Chinese lab
    research (DeepSeek, Zhipu, ByteDance, BAAI) that publishes on arXiv but
    has no accessible direct RSS feed. If any category breaks, that lab's
    research is silently dropped.
    """
    raw = (_FIXTURES / fixture).read_bytes()
    items = ArxivAdapter().parse(raw)

    assert len(items) == 3, f"{fixture}: expected 3 items"
    for item in items:
        assert item.source_id == "arxiv"
        assert item.source_type == "paper"
        assert item.title
        assert item.url.startswith("https://arxiv.org/abs/")
        assert item.published_at
        assert len(item.authors) >= 1
        assert item.summary
        assert "Announce Type" not in item.summary, "Preamble must be stripped"
        assert "announce_type" in item.metadata
        assert "categories" in item.metadata


# ---------------------------------------------------------------------------
# 3. Lab blog adapter parses all seven blog fixtures
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("fixture,channel_title_fragment,url_fragment", [
    ("openai_blog.xml",       "OpenAI",        "openai.com"),
    ("fair_blog.xml",         "Engineering",   "engineering.fb.com"),   # WordPress ns
    ("huggingface_blog.xml",  "Hugging Face",  "huggingface.co"),       # no description
    ("deepmind_blog.xml",     "DeepMind",      "deepmind.google"),      # inconsistent description
    ("bair_blog.xml",         "Berkeley",      "bair.berkeley.edu"),    # HTML description
    ("gradient_blog.xml",     "Gradient",      "thegradient.pub"),      # dc:creator + content:encoded
    ("vector_institute.xml",  "Vector",        "vectorinstitute.ai"),   # dc:creator + content:encoded
])
def test_lab_blog_parse_all_fixtures(fixture, channel_title_fragment, url_fragment):
    """Lab blog adapter parses every confirmed feed fixture into well-formed NormalizedItems.

    > **Why:** Each feed has a different RSS quirk (WordPress namespace, missing
    description, HTML-only body, dc:creator). A single generic test catches
    regressions across all of them without requiring per-feed knowledge in the
    pipeline code.
    """
    raw = (_FIXTURES / fixture).read_bytes()
    items = LabBlogAdapter().parse(raw)

    assert len(items) == 3, f"{fixture}: expected 3 items"
    for item in items:
        assert isinstance(item, NormalizedItem)
        assert item.source_id == "lab_blog"
        assert item.source_type == "lab_post"
        assert item.title
        assert url_fragment in item.url, f"{fixture}: expected url to contain {url_fragment!r}"
        assert item.published_at
        assert item.publisher and channel_title_fragment in item.publisher, (
            f"{fixture}: publisher {item.publisher!r} missing {channel_title_fragment!r}"
        )
        # summary must be non-empty — fallback to title when description is absent
        assert item.summary, f"{fixture}: summary is empty (missing description fallback?)"
        assert "<" not in item.summary, f"{fixture}: HTML tags leaked into summary"


# ---------------------------------------------------------------------------
# 3. Both adapters produce the same NormalizedItem field set
# ---------------------------------------------------------------------------


def test_normalized_item_shape_matches():
    """Both adapters produce NormalizedItem — no adapter-specific subclass leaks through.

    > **Why:** Downstream stages iterate over NormalizedItem records without
    knowing which adapter produced them. Different shapes cause silent field
    drops during scoring.
    """
    arxiv_item = ArxivAdapter().parse((_FIXTURES / "arxiv_cs_ai.xml").read_bytes())[0]
    blog_item = LabBlogAdapter().parse((_FIXTURES / "openai_blog.xml").read_bytes())[0]
    # Verify with a second blog fixture to catch per-fixture subclassing too
    blog_item2 = LabBlogAdapter().parse((_FIXTURES / "gradient_blog.xml").read_bytes())[0]

    assert type(arxiv_item) is NormalizedItem
    assert type(blog_item) is NormalizedItem
    assert type(blog_item2) is NormalizedItem
    assert set(NormalizedItem.model_fields) == {
        "source_id", "source_type", "title", "url",
        "published_at", "authors", "publisher",
        "summary", "metadata", "full_text_fetched",
    }


# ---------------------------------------------------------------------------
# 4. Raw payload extension declared correctly per adapter
# ---------------------------------------------------------------------------


def test_raw_extension():
    """Each adapter declares .xml as its raw archival extension (not .json).

    > **Why:** A .json extension on an RSS payload would mislead debugging and
    break tooling that reads archived payloads by extension.
    """
    assert ArxivAdapter().raw_extension == ".xml"
    assert LabBlogAdapter().raw_extension == ".xml"
    assert ArxivAdapter().raw_extension != ".json"
    assert LabBlogAdapter().raw_extension != ".json"


# ---------------------------------------------------------------------------
# 5. Registry resolves known source ids
# ---------------------------------------------------------------------------


def test_registry_lookup():
    """Registry returns correct adapter instances for known source ids.

    > **Why:** If the registry returns the wrong adapter for an id, every
    source fetch and parse operates on the wrong format.
    """
    arxiv = get_adapter("arxiv")
    blog = get_adapter("lab_blog")

    assert isinstance(arxiv, ArxivAdapter)
    assert isinstance(blog, LabBlogAdapter)
    assert get_adapter("arxiv") is not get_adapter("arxiv")  # fresh instance each call


# ---------------------------------------------------------------------------
# 6. Registry raises for unknown source id
# ---------------------------------------------------------------------------


def test_unknown_source_raises():
    """Registry raises ValueError naming the unknown id and listing registered adapters.

    > **Why:** Without a loud failure, an unknown source id silently produces
    zero items every run — the operator has no signal that a source is
    misconfigured rather than empty.
    """
    with pytest.raises(ValueError, match="nonexistent"):
        get_adapter("nonexistent")

    with pytest.raises(ValueError, match="arxiv"):  # error must list registered ids
        get_adapter("totally_unknown_source")


# ---------------------------------------------------------------------------
# 7. resolve_adapters uses the real data_advantage topic config
# ---------------------------------------------------------------------------


def test_resolve_adapters_from_topic():
    """resolve_adapters returns adapters matching enabled_sources in order.

    > **Why:** The pipeline resolution layer is the bridge between a topic
    config and a live ingestion run. If it cannot materialise the right
    adapters, the run completes with zero items and no explanation.
    """
    config = load_topic_config(_TOPIC_PATH)
    assert "arxiv" in config.enabled_sources
    assert "lab_blog" in config.enabled_sources

    adapters = resolve_adapters(config)

    assert len(adapters) == len(config.enabled_sources)
    for adapter, sid in zip(adapters, config.enabled_sources):
        assert isinstance(adapter, SourceAdapter)
        assert adapter.source_id() == sid


# ---------------------------------------------------------------------------
# 8. topic.md feed lists validate and match confirmed URLs
# ---------------------------------------------------------------------------


def test_topic_feed_lists():
    """The real topic.md contains correctly structured arxiv_feeds and blog_feeds.

    > **Why:** If feed URLs are wrong in the config, every fetch returns a
    network error with no items — the wiki starves silently.
    """
    config = load_topic_config(_TOPIC_PATH)

    assert len(config.arxiv_feeds) >= 1
    assert len(config.blog_feeds) >= 1

    arxiv_ids = [f.id for f in config.arxiv_feeds]
    for expected in ("cs-ai", "cs-lg", "cs-cl"):
        assert expected in arxiv_ids, f"Expected arXiv feed '{expected}' not in config"

    blog_ids = [f.id for f in config.blog_feeds]
    for expected in ("openai-blog", "huggingface-blog", "deepmind-blog",
                     "bair-blog", "the-gradient", "vector-institute", "fair-blog"):
        assert expected in blog_ids, f"Expected blog feed '{expected}' not in config"

    for feed in config.arxiv_feeds + config.blog_feeds:
        assert isinstance(feed, FeedConfig)
        assert feed.id
        assert feed.name
        assert feed.url.startswith("https://")


# ---------------------------------------------------------------------------
# 9. resolve_adapters raises on unknown source id in config
# ---------------------------------------------------------------------------


def test_resolve_adapters_unknown_raises():
    """resolve_adapters raises ValueError when a config lists an unknown source.

    > **Why:** A silently skipped unknown source means the operator believes
    two sources are active when only one is, and the brief covers less ground
    than the config promised.
    """
    config = TopicConfig(
        topic_id="test",
        name="Test",
        thesis="A thesis.",
        audience_ref="test_audience",
        enabled_sources=["arxiv", "does_not_exist"],
    )
    with pytest.raises(ValueError, match="does_not_exist"):
        resolve_adapters(config)


# ---------------------------------------------------------------------------
# 10. A third adapter can be registered without touching existing files
# ---------------------------------------------------------------------------


def test_extensibility_third_adapter():
    """A new adapter registered at test time is resolvable without modifying existing files.

    > **Why:** The core promise of the adapter pattern is that adding a source
    is a local change. If existing files must be edited, every new source is a
    regression risk for arXiv and lab_blog ingestion.
    """
    import sources as _sources_module

    class TestAdapter(SourceAdapter):
        raw_extension = ".xml"

        def source_id(self) -> str:
            return "test_source"

        def fetch(self, query_params: dict) -> bytes:
            return b""

        def parse(self, raw: bytes) -> list[NormalizedItem]:
            return []

        def fetch_full_text(self, url: str) -> bytes:
            return b""

    _sources_module._REGISTRY["test_source"] = TestAdapter

    try:
        adapter = get_adapter("test_source")
        assert isinstance(adapter, TestAdapter)

        config = TopicConfig(
            topic_id="test",
            name="Test",
            thesis="A thesis.",
            audience_ref="test_audience",
            enabled_sources=["test_source"],
        )
        adapters = resolve_adapters(config)
        assert len(adapters) == 1
        assert isinstance(adapters[0], TestAdapter)
    finally:
        _sources_module._REGISTRY.pop("test_source", None)


# ---------------------------------------------------------------------------
# 11. Malformed XML raises a clear ValueError
# ---------------------------------------------------------------------------


def test_arxiv_parse_rejects_malformed_xml():
    """ArxivAdapter.parse raises ValueError with a readable message on malformed XML.

    > **Why:** A corrupted or truncated response should surface as a clear
    ValueError, not an opaque ElementTree trace the operator cannot act on.
    """
    with pytest.raises(ValueError, match="not valid XML"):
        ArxivAdapter().parse(b"this is not xml at all <<<")


def test_lab_blog_parse_rejects_malformed_xml():
    """LabBlogAdapter.parse raises ValueError on malformed XML.

    > **Why:** Same reason — operators need actionable errors when a feed
    response is corrupted or returns an error page instead of RSS.
    """
    with pytest.raises(ValueError, match="not valid XML"):
        LabBlogAdapter().parse(b"<broken>")


# ---------------------------------------------------------------------------
# 12. fetch_full_text — ArxivAdapter returns PDF bytes
# ---------------------------------------------------------------------------


def test_arxiv_fetch_full_text_returns_pdf(monkeypatch):
    """ArxivAdapter.fetch_full_text returns raw PDF bytes from the fixture.

    > **Why:** If the PDF fetch is broken, pass-2 scoring has no document to
    read — every arXiv paper is silently dropped from the signal file output.
    """
    pdf_bytes = (_FIXTURES / "arxiv_paper.pdf").read_bytes()

    def _fake_urlopen(req, timeout=60):
        import io
        class _Resp:
            def read(self):
                return pdf_bytes
            def __enter__(self):
                return self
            def __exit__(self, *_):
                pass
        return _Resp()

    monkeypatch.setattr(urllib.request, "urlopen", _fake_urlopen)

    result = ArxivAdapter().fetch_full_text("https://arxiv.org/abs/2404.01230")

    assert result[:4] == b"%PDF", "fetch_full_text must return raw PDF bytes"
    assert len(result) > 1000, "PDF should be non-trivially sized"


# ---------------------------------------------------------------------------
# 13. fetch_full_text — ArxivAdapter extracts ID from URL correctly
# ---------------------------------------------------------------------------


def test_arxiv_fetch_full_text_constructs_pdf_url(monkeypatch):
    """ArxivAdapter.fetch_full_text converts abs URL to the correct pdf URL.

    > **Why:** If the URL construction is wrong, every fetch hits a 404 and
    every paper is dropped from pass-2 without a clear error.
    """
    captured = {}

    def _fake_urlopen(req, timeout=60):
        captured["url"] = req.full_url
        import io
        class _Resp:
            def read(self):
                return b"%PDF-fake"
            def __enter__(self):
                return self
            def __exit__(self, *_):
                pass
        return _Resp()

    monkeypatch.setattr(urllib.request, "urlopen", _fake_urlopen)

    ArxivAdapter().fetch_full_text("https://arxiv.org/abs/2404.01230")

    assert captured["url"] == "https://arxiv.org/pdf/2404.01230"


# ---------------------------------------------------------------------------
# 14. fetch_full_text — ArxivAdapter raises RuntimeError on bad URL
# ---------------------------------------------------------------------------


def test_arxiv_fetch_full_text_raises_on_bad_url():
    """ArxivAdapter.fetch_full_text raises RuntimeError for unrecognised URLs.

    > **Why:** A silent failure here would produce a NormalizedItem with no
    full text, which would flow into pass-2 and produce a vacuous signal file.
    """
    with pytest.raises(RuntimeError, match="Cannot extract arXiv ID"):
        ArxivAdapter().fetch_full_text("https://example.com/not-an-arxiv-url")


# ---------------------------------------------------------------------------
# 15. fetch_full_text — LabBlogAdapter returns HTML-stripped plain text
# ---------------------------------------------------------------------------


def test_lab_blog_fetch_full_text_returns_plain_text(monkeypatch):
    """LabBlogAdapter.fetch_full_text returns HTML-stripped UTF-8 bytes.

    > **Why:** If HTML tags leak into the plain-text payload, the LLM receives
    noisy markup instead of readable prose — scoring quality degrades silently.
    """
    html_bytes = (_FIXTURES / "lab_blog_article.html").read_bytes()

    def _fake_urlopen(req, timeout=30):
        class _Resp:
            def read(self):
                return html_bytes
            def __enter__(self):
                return self
            def __exit__(self, *_):
                pass
        return _Resp()

    monkeypatch.setattr(urllib.request, "urlopen", _fake_urlopen)

    result = LabBlogAdapter().fetch_full_text("https://huggingface.co/blog/smollm")

    assert isinstance(result, bytes)
    text = result.decode("utf-8")
    assert "<" not in text, "HTML tags must be stripped from plain-text output"
    assert len(text) > 100, "Stripped text should contain meaningful content"


# ---------------------------------------------------------------------------
# 16. fetch_full_text — mime types are declared correctly
# ---------------------------------------------------------------------------


def test_full_text_mime_types():
    """Each adapter declares the correct full_text_mime_type class attribute.

    > **Why:** The wrong MIME type causes the google.genai API call in pass-2
    to reject the upload — the item is silently dropped from signal output.
    """
    assert ArxivAdapter.full_text_mime_type == "application/pdf"
    assert LabBlogAdapter.full_text_mime_type == "text/plain"


# ---------------------------------------------------------------------------
# 17. full_text_fetched defaults False on NormalizedItem
# ---------------------------------------------------------------------------


def test_normalized_item_full_text_fetched_defaults_false():
    """NormalizedItem.full_text_fetched defaults to False on construction.

    > **Why:** If the default were True, pass-2 would skip re-fetching items
    that haven't actually been fetched, and write signal files with no content.
    """
    item = ArxivAdapter().parse((_FIXTURES / "arxiv_cs_ai.xml").read_bytes())[0]
    assert item.full_text_fetched is False
