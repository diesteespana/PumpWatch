"""Unit tests for the heuristic wallet scoring function."""
from datetime import datetime, timedelta, timezone

import pytest

from app.services.analytics_service import _compute_score


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── Score range ───────────────────────────────────────────────────────────────

def test_score_in_range():
    score, _, _ = _compute_score(1_000_000, 50, 5, _now())
    assert 0.0 <= score <= 1.0


def test_zero_activity_scores_low():
    score, _, _ = _compute_score(0, 0, 0, None)
    assert score < 0.05


def test_max_activity_scores_high():
    score, _, _ = _compute_score(10_000_000, 200, 13, _now())
    # All components near max — should be close to 1.0
    assert score >= 0.90


# ── Individual components ─────────────────────────────────────────────────────

def test_volume_increases_score():
    low, _, _ = _compute_score(10_000, 10, 3, None)
    high, _, _ = _compute_score(5_000_000, 10, 3, None)
    assert high > low


def test_event_count_increases_score():
    few, _, _ = _compute_score(100_000, 1, 2, None)
    many, _, _ = _compute_score(100_000, 100, 2, None)
    assert many > few


def test_recency_decays_with_time():
    recent, _, _ = _compute_score(100_000, 20, 4, _now())
    old, _, _ = _compute_score(100_000, 20, 4, _now() - timedelta(days=40))
    assert recent > old


def test_stale_wallet_recency_zero():
    """Wallet inactive for 30+ days gets 0 recency points."""
    _, breakdown, _ = _compute_score(100_000, 20, 4, _now() - timedelta(days=35))
    assert breakdown["recency"] == 0.0


def test_active_wallet_has_positive_recency():
    _, breakdown, _ = _compute_score(100_000, 20, 4, _now())
    assert breakdown["recency"] > 0.0


# ── Insights ──────────────────────────────────────────────────────────────────

def test_high_volume_insight():
    _, _, insights = _compute_score(5_000_000, 50, 5, _now())
    assert any("M+" in i for i in insights)


def test_no_history_insight():
    _, _, insights = _compute_score(0, 0, 0, None)
    assert any("Limited" in i for i in insights)


def test_diverse_wallet_insight():
    _, _, insights = _compute_score(500_000, 80, 10, _now())
    assert any("Diverse" in i for i in insights)


# ── Breakdown dict ────────────────────────────────────────────────────────────

def test_breakdown_keys_present():
    _, breakdown, _ = _compute_score(100_000, 20, 4, _now())
    assert set(breakdown.keys()) == {"volume", "activity", "diversity", "recency"}


def test_breakdown_values_non_negative():
    _, breakdown, _ = _compute_score(50_000, 5, 2, _now() - timedelta(days=5))
    assert all(v >= 0 for v in breakdown.values())
