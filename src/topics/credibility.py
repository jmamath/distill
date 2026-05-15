"""Deterministic credibility and freshness scoring for research signals.

Both functions are pure computations — no LLM call, no disk write.
They are called in pass-2 orchestration (15.3b-iv) after affiliations are
extracted from the paper by the LLM.

Public API:
    compute_source_credibility  — average weight of matched institutions
    compute_temporal_freshness  — 0-10 linear decay over a fixed 365-day window
"""

from datetime import datetime, timezone

# Freshness decays to 0 at this age regardless of topic signal_horizon.
# Decoupled from signal_horizon intentionally: signal_horizon controls what
# gets ingested; this constant controls how freshness is scored once a signal
# is in the pipeline.  A paper just past the ingestion window should not hard-
# floor to 0 — it should still carry a meaningful (low) freshness score.
_FRESHNESS_REFERENCE_DAYS = 365


def compute_source_credibility(
    affiliations: list[str],
    table: dict,
) -> float | None:
    """Average credibility weight of institutions present in the table.

    Unmatched affiliations are excluded from the mean.  When no affiliation
    matches the table, returns None rather than 0 so callers can distinguish
    "unknown credibility" from "low credibility".

    Args:
        affiliations: Author institution strings as cited in the source.
        table: Mapping of institution name → credibility weight (0–10).

    Returns:
        Mean weight of matched institutions, or None if there are no matches.
    """
    weights = [table[a] for a in affiliations if a in table]
    if not weights:
        return None
    return sum(weights) / len(weights)


def compute_temporal_freshness(
    published_at: datetime,
    *,
    _now: datetime | None = None,
) -> int:
    """Linear freshness score from 10 (today) to 0 (at _FRESHNESS_REFERENCE_DAYS days).

    Age is measured in whole days against a fixed _FRESHNESS_REFERENCE_DAYS-day reference window.
    Items published in the future are treated as age 0 (score 10).
    The score is monotonically decreasing with age and floors at 0.

    In pass-2 ranking this score is a tiebreaker/modifier, not a primary axis.
    applicability_score × source_credibility drives the rank; freshness breaks
    ties among otherwise comparable signals.

    Args:
        published_at: Publication datetime (timezone-aware or naive, but must
            be comparable to _now).
        _now: Reference datetime for age calculation.  Defaults to
            datetime.now(timezone.utc).  Pass an explicit value in tests.

    Returns:
        Integer freshness score in [0, 10].
    """
    now = _now if _now is not None else datetime.now(timezone.utc)
    age_days = max(0, (now - published_at).days)
    return max(0, round(10 * (1 - age_days / _FRESHNESS_REFERENCE_DAYS)))
