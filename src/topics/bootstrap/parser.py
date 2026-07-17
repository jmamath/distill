"""Dossier parser — extracts and validates the JSON payload from a dossier file.

A dossier is a Markdown file produced by an external deep-research agent. It
contains Markdown prose with `## Theme: {kebab-id}` headings (one per theme),
followed by exactly one trailing fenced JSON block.  This module:

  1. Locates and extracts that trailing JSON block.
  2. Validates it against the DossierPayload Pydantic schema.
  3. Splits the prose into per-theme sections by `## Theme: {id}` headings.
  4. Validates that JSON theme ids and prose section ids match exactly.
  5. Returns a ParsedDossier ready for the seeder.

The parser rejects invalid or missing JSON, and any mismatch between JSON theme
ids and prose headings, before the seeder ever touches disk — no partial writes
on failure.

Public API:
    DossierTheme, DossierEntity, DossierTimelineEntry, DossierHypothesis,
    DossierPayload — typed structures for dossier records.
    ParsedDossier      — wrapper returned by parse_dossier().
    extract_json_block(text) — returns the raw JSON string.
    extract_theme_sections(text) — returns (intro, {theme_id: prose}).
    parse_dossier(text)      — returns a validated ParsedDossier.
"""

import json
import logging
import re
from dataclasses import dataclass

from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger(__name__)

# Matches the last ```json ... ``` fence in a document (non-greedy on content).
_JSON_FENCE_RE = re.compile(
    r"```json\s*\n(.*?)```\s*$",
    re.DOTALL,
)

# Matches ## Theme: {kebab-id} headings.
_THEME_HEADING_RE = re.compile(r"^## Theme:\s+(\S+)", re.MULTILINE)


# ---------------------------------------------------------------------------
# Dossier record models
# ---------------------------------------------------------------------------


class DossierTheme(BaseModel):
    """A single theme record from the dossier JSON."""

    id: str
    name: str
    description: str
    taxonomy_ref: str | None = None
    key_entity_ids: list[str] = Field(default_factory=list)


class DossierEntity(BaseModel):
    """A single entity record from the dossier JSON.

    entity_type is drawn from a controlled vocabulary: lab, company, dataset,
    method, benchmark, product.
    """

    id: str
    name: str
    entity_type: str
    description: str


class DossierTimelineEntry(BaseModel):
    """A single timeline entry from the dossier JSON."""

    id: str
    date: str
    title: str
    theme_ids: list[str] = Field(default_factory=list)
    entity_ids: list[str] = Field(default_factory=list)
    body: str = ""


class DossierResolutionCriterion(BaseModel):
    """Optional scaffolding that makes a hypothesis easier to resolve."""

    metric: str | None = None
    threshold: str | None = None
    scope: str | None = None
    horizon: str | None = None


class DossierComparison(BaseModel):
    """Pairwise comparison subjects for a comparative hypothesis."""

    subject_a: str
    subject_b: str


class DossierHypothesis(BaseModel):
    """A resolvable directional bet from the dossier JSON."""

    id: str
    statement: str
    theme_ids: list[str] = Field(default_factory=list)
    action_posture: str = "monitor"
    why_it_matters: str = ""
    resolution_criterion: DossierResolutionCriterion | None = None
    comparison: DossierComparison | None = None


class DossierPayload(BaseModel):
    """The complete validated payload extracted from one dossier."""

    themes: list[DossierTheme]
    entities: list[DossierEntity]
    timeline: list[DossierTimelineEntry] = Field(default_factory=list)
    hypotheses: list[DossierHypothesis] = Field(default_factory=list)


@dataclass
class ParsedDossier:
    """Full parse result: validated payload + extracted prose parts."""

    payload: DossierPayload
    theme_sections: dict[str, str]  # theme_id -> prose body
    intro: str = ""  # prose before the first ## Theme: heading


# ---------------------------------------------------------------------------
# Parser functions
# ---------------------------------------------------------------------------


def extract_json_block(text: str) -> str:
    """Find and return the raw JSON string from the last fenced JSON block.

    Args:
        text: Full text of a dossier Markdown file.

    Returns:
        The raw JSON string (the content inside the fence, not the fence itself).

    Raises:
        ValueError: if no fenced JSON block is found.
    """
    match = _JSON_FENCE_RE.search(text)
    if match is None:
        raise ValueError(
            "No fenced JSON block found in dossier. "
            "The dossier must end with a ```json ... ``` block."
        )
    return match.group(1).strip()


def extract_theme_sections(text: str) -> tuple[str, dict[str, str]]:
    """Split dossier prose into intro and per-theme sections.

    Only considers text before the trailing fenced JSON block so that the
    JSON fence is never included in a theme body.

    Args:
        text: Full text of a dossier Markdown file.

    Returns:
        A (intro, sections) tuple where intro is the prose before the first
        ``## Theme:`` heading and sections maps each theme kebab-id to its
        prose body.
    """
    fence_match = re.search(r"```json", text)
    prose = text[: fence_match.start()].rstrip() if fence_match else text

    matches = list(_THEME_HEADING_RE.finditer(prose))
    if not matches:
        return prose.strip(), {}

    intro = prose[: matches[0].start()].strip()
    sections: dict[str, str] = {}
    for i, m in enumerate(matches):
        theme_id = m.group(1)
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(prose)
        sections[theme_id] = prose[start:end].strip()
    return intro, sections


def parse_dossier(dossier_text: str) -> ParsedDossier:
    """Parse a dossier Markdown file and return a validated ParsedDossier.

    Extraction, validation, and prose-section matching all happen in memory
    before any file is written, so a failure here guarantees no partial writes.

    Args:
        dossier_text: Full text of the dossier Markdown file.

    Returns:
        A ParsedDossier containing the validated payload and extracted prose.

    Raises:
        ValueError: if no fenced JSON block is found.
        ValueError: if the JSON block is not valid JSON.
        ValueError: if the JSON does not match the DossierPayload schema.
        ValueError: if JSON theme ids and ## Theme: prose sections do not match.
    """
    raw_json = extract_json_block(dossier_text)

    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Dossier JSON block is not valid JSON: {exc}") from exc

    try:
        payload = DossierPayload(**data)
    except ValidationError as exc:
        raise ValueError(f"Dossier JSON does not match expected schema: {exc}") from exc

    intro, theme_sections = extract_theme_sections(dossier_text)

    json_ids = {t.id for t in payload.themes}
    prose_ids = set(theme_sections.keys())

    missing_prose = json_ids - prose_ids
    missing_json = prose_ids - json_ids
    if missing_prose:
        raise ValueError(
            f"JSON themes have no matching ## Theme: prose section: {sorted(missing_prose)}"
        )
    if missing_json:
        raise ValueError(
            f"## Theme: prose sections have no matching JSON theme id: {sorted(missing_json)}"
        )

    logger.info(
        "Parsed dossier: %d themes, %d entities, %d timeline entries, %d hypotheses",
        len(payload.themes),
        len(payload.entities),
        len(payload.timeline),
        len(payload.hypotheses),
    )
    return ParsedDossier(payload=payload, theme_sections=theme_sections, intro=intro)
