"""Structured scoring models for the topic-aware signal pipeline.

Pass-1 produces AbstractScore from the item abstract only.
Pass-2 produces FullScore (defined in 15.3b) after full-text enrichment.

Public API:
    AbstractScore  — pass-1 relevance verdict for one NormalizedItem
"""

from pydantic import BaseModel, Field


class AbstractScore(BaseModel):
    """Pass-1 relevance verdict produced from a signal's abstract/summary.

    Items with relevance < SCORING_THRESHOLD are dropped before pass-2.
    Items at or above the threshold proceed to full-text enrichment.
    """

    relevance: int = Field(..., ge=0, le=10)
    reason: str
