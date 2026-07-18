"""Structured scoring models for the topic-aware signal pipeline.

Pass-1 produces Pass1Score from the item abstract only.
Pass-2 produces Pass2Score after full-text enrichment.
Triage (Plan 9, Decision 1) produces TriageDecision per claim.

Public API:
    Pass1Score  — pass-1 relevance verdict for one NormalizedItem
    CandidateTheme — one scored theme candidate from pass-2
    Pass2Score     — full pass-2 scoring result
    TriageComparison — the two subjects of a comparative (head-to-head) bet
    TriageEntity     — a routed non-evidence artifact record
    TriageDecision   — validated triage verdict for one claim
    make_signal_id — deterministic signal file identifier
"""

import hashlib
from typing import Literal

from pydantic import BaseModel, Field, ValidationInfo, model_validator


class Pass1Score(BaseModel):
    """Pass-1 relevance verdict produced from a signal's abstract/summary.

    Items with relevance < SCORING_THRESHOLD are dropped before pass-2.
    Items at or above the threshold proceed to full-text enrichment.
    """

    relevance: int = Field(..., ge=0, le=10)
    reason: str


class CandidateTheme(BaseModel):
    """One theme candidate produced by pass-2 LLM scoring."""

    theme_id: str
    confidence: int = Field(..., ge=0, le=10)
    rationale: str


class Evidence(BaseModel):
    claim: str
    stance: str  # for | against | mixed | neutral


class Pass2Score(BaseModel):
    """Full pass-2 scoring result produced from the item's full text."""

    applicability_score: int = Field(..., ge=0, le=10)
    applicability_rationale: str
    strategic_significance: int = Field(..., ge=0, le=10)
    strategic_significance_rationale: str
    paper_audience: str
    candidate_themes: list[CandidateTheme] = Field(default_factory=list)
    new_evidences: list[Evidence] = Field(default_factory=list)
    affiliations: list[str] = Field(default_factory=list)
    rationale: str


class TriageComparison(BaseModel):
    """The two named subjects of a comparative (head-to-head) bet.

    A populated comparison marks the opened hypothesis as a pairwise edge in
    the belief graph (same shape Plan 8 infers from `comparison`).
    """

    subject_a: str
    subject_b: str


class TriageEntity(BaseModel):
    """A non-evidence artifact worth registering in entities.json.

    Mirrors the bootstrap DossierEntity shape minus the id, which is derived
    deterministically by the updater, never authored by the model.
    """

    name: str
    entity_type: Literal["lab", "company", "dataset", "method", "benchmark", "product"]
    description: str


class TriageDecision(BaseModel):
    """Validated triage verdict for one claim (Plan 9, Decision 1).

    Contract: each decision branch carries exactly the payload it needs —
    `attach` a `hypothesis_id`, `open` a `new_statement`, `route` an `entity` —
    and a branch given a payload it must not carry fails validation rather
    than being coerced. `comparison` is only valid on `open`; `entity` may
    co-fire on `attach`/`open` (a claim that both moves a belief and names a
    central artifact) but is invalid on `drop`.

    When validated with a context dict containing `candidate_ids`
    (`model_validate(data, context={"candidate_ids": {...}})`), an `attach`
    whose `hypothesis_id` is not in that set is rejected; without context the
    membership check is skipped.
    """

    decision: Literal["attach", "open", "route", "drop"]
    hypothesis_id: str | None = None
    new_statement: str | None = None
    comparison: TriageComparison | None = None
    entity: TriageEntity | None = None
    rationale: str

    @model_validator(mode="after")
    def _enforce_branch_payload(self, info: ValidationInfo) -> "TriageDecision":
        if self.decision == "attach":
            if not self.hypothesis_id:
                raise ValueError("attach requires a hypothesis_id")
            candidate_ids = (info.context or {}).get("candidate_ids")
            if candidate_ids is not None and self.hypothesis_id not in candidate_ids:
                raise ValueError(
                    f"attach hypothesis_id {self.hypothesis_id!r} is not a candidate"
                )
            if self.new_statement:
                raise ValueError("attach must not carry a new_statement")
        elif self.decision == "open":
            if not self.new_statement:
                raise ValueError("open requires a new_statement")
            if self.hypothesis_id:
                raise ValueError("open must not carry a hypothesis_id")
        elif self.decision == "route":
            if self.entity is None:
                raise ValueError("route requires an entity")
            if self.hypothesis_id or self.new_statement:
                raise ValueError("route must not carry a hypothesis_id or new_statement")
        else:  # drop
            if self.hypothesis_id or self.new_statement or self.entity is not None:
                raise ValueError("drop must not carry any payload")
        if self.comparison is not None and self.decision != "open":
            raise ValueError("comparison is only valid on open")
        return self


def make_signal_id(source_id: str, published_at: str, url: str) -> str:
    """Return a deterministic signal identifier for the given item.

    Format: {source_id}_{date}_{sha256(url)[:10]}
    Example: arxiv_2026-04-29_a3f7b2c1de

    Args:
        source_id: Adapter identifier (e.g. "arxiv").
        published_at: ISO 8601 date string; only the date portion is used.
        url: Canonical item URL; hashed to produce the suffix.

    Returns:
        A stable, filesystem-safe signal identifier.
    """
    date_part = published_at[:10]
    url_hash = hashlib.sha256(url.encode()).hexdigest()[:10]
    return f"{source_id}_{date_part}_{url_hash}"
