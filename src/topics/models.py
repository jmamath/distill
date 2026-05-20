"""Structured scoring models for the topic-aware signal pipeline.

Pass-1 produces AbstractScore from the item abstract only.
Pass-2 produces Pass2Score after full-text enrichment.

Public API:
    AbstractScore  — pass-1 relevance verdict for one NormalizedItem
    CandidateTheme — one scored theme candidate from pass-2
    Pass2Score     — full pass-2 scoring result
    make_signal_id — deterministic signal file identifier
"""

import hashlib

from pydantic import BaseModel, Field


class AbstractScore(BaseModel):
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


class OpenQuestion(BaseModel):
    text: str


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
    new_open_questions: list[OpenQuestion] = Field(default_factory=list)
    new_evidences: list[Evidence] = Field(default_factory=list)
    affiliations: list[str] = Field(default_factory=list)
    rationale: str


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
