---
name: Source Adapter Contract
plan: "15_2"
executor: script
kind: regression
status: passed
last_run: 2026-04-27
notes: >
  arXiv adapter uses category RSS (rss.arxiv.org) not the Atom search API.
  Blog feeds are explicitly listed in topic.md; all 6 feeds verified reachable.
  Fixtures are real fetched payloads (3 items each), not invented bytes.
script: tests/test_source_adapters.py
---

## Preconditions

- Virtual environment is active: `source sonaryn_env/bin/activate`
- Working directory is the project root
- `research_briefing/src/` is on `PYTHONPATH`
- `research_briefing/src/sources/` package exists (replaces the old `sources.py` stub)
- `research_briefing/data/research_topics/data_advantage/topic.md` contains `enabled_sources: [arxiv, lab_blog]`

## Steps

1. **arXiv adapter parses an Atom XML fixture into NormalizedItem records**
   - Run `pytest research_briefing/tests/test_source_adapters.py::test_arxiv_parse_fixture`
   - Expect: test passes; returned list contains at least one `NormalizedItem` with non-empty `title`, `url`, `published_at`, `summary`, and at least one author; `source_id == "arxiv"`, `source_type == "paper"`
   > **Why:** If the arXiv adapter cannot parse its own native format, every paper the system tries to ingest is dropped silently — the wiki never learns about new research and the briefing degrades to its bootstrap state indefinitely.

2. **Lab blog adapter parses an RSS XML fixture into NormalizedItem records**
   - Run `pytest research_briefing/tests/test_source_adapters.py::test_lab_blog_parse_rss_fixture`
   - Expect: test passes; returned list contains at least one `NormalizedItem` with non-empty `title`, `url`, `published_at`, `summary`, and a non-None `publisher`; `source_id == "lab_blog"`, `source_type == "lab_post"`
   > **Why:** Lab and engineering blogs are the fastest signal source for practitioner-grade data insights. If the RSS parser is broken, the most timely signals never reach scoring and the brief trails the real conversation by weeks.

3. **Both adapters produce the same NormalizedItem field set**
   - Run `pytest research_briefing/tests/test_source_adapters.py::test_normalized_item_shape_matches`
   - Expect: test passes; `NormalizedItem` instances from both adapters have identical field names; no adapter-specific keys leak into the top-level model
   > **Why:** Downstream stages (scoring, wiki updater, tweet generator) iterate over `NormalizedItem` records without knowing which adapter produced them. If adapters emit different shapes, scoring silently skips fields and the output is wrong with no error.

4. **Raw payload extension is declared correctly per adapter**
   - Run `pytest research_briefing/tests/test_source_adapters.py::test_raw_extension`
   - Expect: test passes; `ArxivAdapter().raw_extension == ".xml"` and `LabBlogAdapter().raw_extension == ".xml"`; neither returns `.json`
   > **Why:** The archival layer writes raw bytes with the declared extension. A `.json` extension on an Atom or RSS payload would mislead future debugging and break any tooling that reads archived payloads by extension.

5. **Registry resolves a known source id to a fresh adapter instance**
   - Run `pytest research_briefing/tests/test_source_adapters.py::test_registry_lookup`
   - Expect: test passes; `get_adapter("arxiv")` returns an `ArxivAdapter` instance; `get_adapter("lab_blog")` returns a `LabBlogAdapter` instance; each call returns a distinct object
   > **Why:** If the registry returns the wrong adapter for an id, every source fetch and parse operates on the wrong format — the failure is silent and the operator sees garbled items rather than an error.

6. **Registry raises a clear error for an unknown source id**
   - Run `pytest research_briefing/tests/test_source_adapters.py::test_unknown_source_raises`
   - Expect: test passes; `get_adapter("nonexistent")` raises `ValueError` with a message that names the unknown id and lists the registered adapters
   > **Why:** Without a loud failure, an unknown source id in `enabled_sources` would silently produce zero items for that source on every run — the operator has no signal that a source is misconfigured rather than empty.

7. **topics/sources.py resolves enabled_sources from the real topic config**
   - Run `pytest research_briefing/tests/test_source_adapters.py::test_resolve_adapters_from_topic`
   - Expect: test passes; `resolve_adapters(data_advantage_config)` returns a list of two adapters matching `["arxiv", "lab_blog"]` in order; each is a `SourceAdapter` instance
   > **Why:** The pipeline resolution layer is the bridge between a topic config and a live ingestion run. If it cannot materialise the right adapters from a config, the pipeline has no sources to fetch from — the run completes with zero items and no explanation.

8. **resolve_adapters raises on an unknown source id in the config**
   - Run `pytest research_briefing/tests/test_source_adapters.py::test_resolve_adapters_unknown_raises`
   - Expect: test passes; a `TopicConfig` with `enabled_sources=["arxiv", "does_not_exist"]` causes `resolve_adapters` to raise `ValueError` naming the unknown id
   > **Why:** A silently skipped unknown source means the operator believes two sources are active when only one is. The brief appears complete but covers less ground than the config promised.

9. **A third adapter can be registered without changing existing source files**
   - Run `pytest research_briefing/tests/test_source_adapters.py::test_extensibility_third_adapter`
   - Expect: test passes; a `TestAdapter` registered at test time is resolvable via `get_adapter("test_source")` and via `resolve_adapters` on a config with `enabled_sources=["test_source"]`, with no modifications to `arxiv.py`, `lab_blog.py`, or `topics/sources.py`
   > **Why:** The core promise of the adapter pattern is that adding a source is a local change. If adding an adapter requires touching existing files, every new source is a regression risk for arXiv and lab_blog ingestion.

## Teardown

No disk writes. All tests operate on in-memory fixture bytes and in-process registry state. Tests that register a `TestAdapter` must clean up the registry entry after the test to avoid cross-test contamination.
