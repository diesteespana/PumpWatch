"""Unit tests for Alert.matches_event — pure logic, no DB."""
import uuid

import pytest

from app.models.alert import Alert


def make_alert(**kwargs) -> Alert:
    defaults = dict(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        name="Test Alert",
        is_active=True,
        event_types=[],
        wallet_addresses=[],
        token_contracts=[],
        min_usd_value=0.0,
    )
    alert = Alert()
    for k, v in {**defaults, **kwargs}.items():
        setattr(alert, k, v)
    return alert


WALLET = "0x3f5ce5fbfe3e9af3971dd833d26ba9b5c936f0be"
CONTRACT = "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"


def test_inactive_alert_never_matches():
    alert = make_alert(is_active=False)
    assert not alert.matches_event("whale_buy", WALLET, CONTRACT, 500_000)


def test_empty_filters_match_everything():
    alert = make_alert()
    assert alert.matches_event("whale_buy", WALLET, CONTRACT, 1)


def test_min_usd_value_filters_small_events():
    alert = make_alert(min_usd_value=100_000)
    assert not alert.matches_event("whale_buy", WALLET, CONTRACT, 50_000)
    assert alert.matches_event("whale_buy", WALLET, CONTRACT, 100_000)


def test_event_type_filter():
    alert = make_alert(event_types=["whale_buy"])
    assert alert.matches_event("whale_buy", WALLET, CONTRACT, 500_000)
    assert not alert.matches_event("whale_sell", WALLET, CONTRACT, 500_000)


def test_wallet_filter_case_insensitive():
    alert = make_alert(wallet_addresses=[WALLET.upper()])
    assert alert.matches_event("whale_buy", WALLET.lower(), CONTRACT, 500_000)


def test_token_filter():
    alert = make_alert(token_contracts=[CONTRACT])
    assert alert.matches_event("whale_buy", WALLET, CONTRACT, 500_000)
    assert not alert.matches_event("whale_buy", WALLET, "0xother", 500_000)


def test_combined_filters_all_must_pass():
    alert = make_alert(
        event_types=["whale_buy"],
        min_usd_value=100_000,
        wallet_addresses=[WALLET],
    )
    assert alert.matches_event("whale_buy", WALLET, CONTRACT, 500_000)
    assert not alert.matches_event("whale_sell", WALLET, CONTRACT, 500_000)
    assert not alert.matches_event("whale_buy", "0xother", CONTRACT, 500_000)
    assert not alert.matches_event("whale_buy", WALLET, CONTRACT, 99_999)
