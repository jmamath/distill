"""Tests for deterministic credibility and freshness scoring (Task 15.3b-i).

Covers: institution weight averaging, unmatched-affiliation exclusion, None
on zero matches, linear freshness decay over the fixed 365-day window,
monotonicity, and edge cases (future dates, empty inputs).

> **Why:** Credibility and freshness are settled before the signal schema is
> designed (15.3b-iii) so those scores can be treated as first-class fields
> with a known derivation.  Separating pure functions from the LLM pass means
> they can be updated or recomputed without re-running the expensive model step.

Run from the project root with the virtualenv active:
    source .venv/bin/activate
    PYTHONPATH=src pytest tests/test_credibility.py
"""

from datetime import datetime, timedelta, timezone

import pytest

from topics.credibility import compute_source_credibility, compute_temporal_freshness

TABLE = {
    "MIT": 9,
    "Stanford University": 9,
    "Carnegie Mellon University": 10,
    "Google DeepMind": 6,
}


# ---------------------------------------------------------------------------
# compute_source_credibility
# ---------------------------------------------------------------------------


def test_single_matched_institution():
    result = compute_source_credibility(["MIT"], TABLE)
    assert result == 9.0


def test_multiple_matched_institutions_averaged():
    result = compute_source_credibility(["MIT", "Carnegie Mellon University"], TABLE)
    assert result == pytest.approx(9.5)


def test_unmatched_institutions_excluded_from_mean():
    # "Unknown Lab" is not in TABLE; only MIT contributes
    result = compute_source_credibility(["MIT", "Unknown Lab"], TABLE)
    assert result == 9.0


def test_all_unmatched_returns_none():
    result = compute_source_credibility(["Unknown Lab", "Another Lab"], TABLE)
    assert result is None


def test_empty_affiliations_returns_none():
    result = compute_source_credibility([], TABLE)
    assert result is None


def test_empty_table_returns_none():
    result = compute_source_credibility(["MIT"], {})
    assert result is None


def test_result_is_float_not_int():
    result = compute_source_credibility(["MIT"], TABLE)
    assert isinstance(result, float)


def test_all_matched_institutions_contribute():
    # All four institutions in TABLE; expected mean = (9+9+10+6)/4
    affiliations = list(TABLE.keys())
    result = compute_source_credibility(affiliations, TABLE)
    assert result == pytest.approx((9 + 9 + 10 + 6) / 4)


# ---------------------------------------------------------------------------
# compute_temporal_freshness
# ---------------------------------------------------------------------------
# Reference window is fixed at 365 days, independent of topic signal_horizon.
# score = max(0, round(10 * (1 - age_days / 365)))
# At 36 days → 9, at 180 days → 5, at 365 days → 0.

NOW = datetime(2026, 5, 13, 12, 0, 0, tzinfo=timezone.utc)


def test_published_today_scores_ten():
    result = compute_temporal_freshness(NOW, _now=NOW)
    assert result == 10


def test_published_one_month_ago_scores_nine():
    # 36 days: round(10 * (1 - 36/365)) = round(10 * 0.901) = round(9.01) = 9
    result = compute_temporal_freshness(NOW - timedelta(days=36), _now=NOW)
    assert result == 9


def test_published_six_months_ago_scores_five():
    # 180 days: round(10 * (1 - 180/365)) = round(10 * 0.507) = round(5.07) = 5
    result = compute_temporal_freshness(NOW - timedelta(days=180), _now=NOW)
    assert result == 5


def test_published_at_365_days_scores_zero():
    result = compute_temporal_freshness(NOW - timedelta(days=365), _now=NOW)
    assert result == 0


def test_published_beyond_365_days_scores_zero():
    result = compute_temporal_freshness(NOW - timedelta(days=500), _now=NOW)
    assert result == 0


def test_score_is_monotonically_decreasing():
    # Step through the full 365-day window in 30-day increments
    scores = [
        compute_temporal_freshness(NOW - timedelta(days=d), _now=NOW)
        for d in range(0, 366, 30)
    ]
    for earlier, later in zip(scores, scores[1:]):
        assert earlier >= later


def test_future_dated_item_scores_ten():
    result = compute_temporal_freshness(NOW + timedelta(days=5), _now=NOW)
    assert result == 10


def test_score_is_integer():
    result = compute_temporal_freshness(NOW - timedelta(days=90), _now=NOW)
    assert isinstance(result, int)
