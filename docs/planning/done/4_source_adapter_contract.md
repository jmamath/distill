# Plan 4 — Source Adapter Contract For Research Inputs

**Original task id:** 15.2
**Status: passed** — 21 tests passing as of 2026-04-27. Spec: `docs/specs/15_2_source_adapter_contract.test.md`.

---

Create the normalized ingestion contract for technical research and ecosystem sources.

**Why this matters:** The product now needs arXiv, lab blogs, dataset launches, and engineering writeups to flow through a common pipeline. Without a source adapter contract, every new source becomes a bespoke integration and the wiki layer cannot operate consistently.

## Changes

| File | Action | Description |
|---|---|---|
| `src/sources.py` | **DELETE** | Flat stub (6 lines); replaced by the `sources/` package below (Python forbids a module and package with the same name) |
| `src/sources/__init__.py` | **NEW** | Source registry; maps source ids to adapter classes; used by `topics/sources.py` for topic-aware resolution |
| `src/sources/base.py` | **NEW** | `SourceAdapter` ABC with three required methods: `fetch(query_params: dict) → bytes` (returns raw payload, any format), `parse(raw: bytes) → list[NormalizedItem]` (format-specific parse + normalize), `source_id() → str` (stable string key); plus the `NormalizedItem` Pydantic model |
| `src/sources/arxiv.py` | **NEW** | Adapter for arXiv; `fetch` queries the arXiv Atom API; `parse` reads Atom XML |
| `src/sources/lab_blog.py` | **NEW** | Adapter for lab or engineering blog sources; `fetch` retrieves RSS or HTML; `parse` reads RSS XML (falling back to HTML extract) |
| `src/topics/sources.py` | **NEW** | Resolves `enabled_sources` list from `topic.md` frontmatter to registered adapter instances |
| `tests/test_source_adapters.py` | **NEW** | One fixture per adapter class (arXiv: Atom XML; lab_blog: RSS XML); each fixture tests `parse` → `NormalizedItem` independently; raw payloads written as-is to `raw/{yyyy-mm-dd}/{source_name}{.xml/.html}` (no format coercion) |

## Adapter interface (`base.py`)

```python
class SourceAdapter(ABC):
    @abstractmethod
    def source_id(self) -> str: ...

    @abstractmethod
    def fetch(self, query_params: dict) -> bytes: ...

    @abstractmethod
    def parse(self, raw: bytes) -> list[NormalizedItem]: ...
```

## Normalized item contract (`NormalizedItem`) includes

- `source_id` and `source_type`
- `title` and `url`
- `published_at` (ISO 8601)
- `authors` (list of strings) or `publisher` (org name)
- `summary` / abstract
- `metadata` — dict of source-specific fields (preserved verbatim for traceability)

## Raw archival

Adapters write the raw payload bytes to `raw/{yyyy-mm-dd}/{source_name}.{ext}` preserving the native format (`.xml` for Atom/RSS, `.html` for scraped pages). No coercion to JSON. The `metadata` field on `NormalizedItem` is the structured bridge from raw to normalized, not the archive itself.

## Topic-to-source resolution

`topic.md` frontmatter includes an `enabled_sources` list of source ids (e.g., `[arxiv, lab_blog]`). `topics/sources.py` reads this list and returns the corresponding adapter instances from the registry. An unknown id raises a clear error at load time.

## Verification

- One fixture per adapter class; each parses independently to the same `NormalizedItem` shape
- Raw payloads are archived in native format (not coerced to JSON)
- `topics/sources.py` resolves `enabled_sources` from a topic config and raises on unknown ids
- A third adapter can be added by implementing `SourceAdapter` and registering its id — no changes to `topics/sources.py` or `scoring.py`
