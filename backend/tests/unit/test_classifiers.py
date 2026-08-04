"""
Unit tests for all event classifiers.

EnrichedTransfer fixtures are built inline — no DB, no HTTP.
"""
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.blockchain.address_registry import AddressCategory, AddressLabel, AddressRegistry
from app.blockchain.chain_service import EnrichedTransfer
from app.events.classifiers.contract import ContractDeploymentClassifier
from app.events.classifiers.exchange import (
    ExchangeDepositClassifier,
    ExchangeWithdrawalClassifier,
)
from app.events.classifiers.swap import LargeSwapClassifier, LiquidityAddedClassifier
from app.events.classifiers.token_ops import TokenBurnClassifier, TokenMintClassifier
from app.events.classifiers.wallet import (
    AccumulationDistributionClassifier,
    SmartMoneyClassifier,
)
from app.events.classifiers.whale import WhaleBuyClassifier, WhaleSellClassifier
from app.events.threshold import ThresholdConfig
from app.events.types import EventType

_CONFIG = ThresholdConfig(
    whale_threshold_usd=100_000,
    large_swap_threshold_usd=50_000,
    liquidity_threshold_usd=25_000,
    accumulation_min_transfers=3,
)

WHALE = "0xaaaa000000000000000000000000000000000001"
EXCHANGE = "0x3f5ce5fbfe3e9af3971dd833d26ba9b5c936f0be"
DEX = "0xe592427a0aece92de3edee1f18e0157c05861564"
ZERO = "0x0000000000000000000000000000000000000000"
USDC = "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"


def _registry() -> AddressRegistry:
    r = AddressRegistry()
    return r


def make_transfer(
    from_address: str = WHALE,
    to_address: str = "0xbbbb000000000000000000000000000000000002",
    usd_value: float = 500_000,
    token_symbol: str = "USDC",
    token_contract: str = USDC,
    is_contract_creation: bool = False,
    input_data: str = "0x",
    registry: AddressRegistry | None = None,
) -> EnrichedTransfer:
    reg = registry or _registry()
    return EnrichedTransfer(
        tx_hash="0xdeadbeef",
        block_number=18_000_000,
        timestamp=datetime.now(tz=timezone.utc),
        chain="ethereum",
        from_address=from_address,
        to_address=to_address,
        from_label=reg.get(from_address),
        to_label=reg.get(to_address),
        token_symbol=token_symbol,
        token_contract=token_contract,
        token_decimals=6,
        raw_value=500_000 * 10**6,
        token_amount=Decimal("500000"),
        usd_value=Decimal(str(usd_value)),
        is_contract_creation=is_contract_creation,
        input_data=input_data,
    )


# ── Whale classifiers ──────────────────────────────────────────────────────────

def test_whale_buy_fires_above_threshold():
    t = make_transfer(usd_value=500_000)
    event = WhaleBuyClassifier(_CONFIG).classify(t)
    assert event is not None
    assert event.event_type == EventType.WHALE_BUY


def test_whale_buy_skips_below_threshold():
    t = make_transfer(usd_value=50_000)
    assert WhaleBuyClassifier(_CONFIG).classify(t) is None


def test_whale_buy_skips_exchange_destination():
    t = make_transfer(to_address=EXCHANGE)
    event = WhaleBuyClassifier(_CONFIG).classify(t)
    assert event is None


def test_whale_sell_fires():
    t = make_transfer(from_address=WHALE, usd_value=200_000)
    event = WhaleSellClassifier(_CONFIG).classify(t)
    assert event is not None
    assert event.event_type == EventType.WHALE_SELL


def test_whale_sell_skips_exchange_source():
    t = make_transfer(from_address=EXCHANGE)
    assert WhaleSellClassifier(_CONFIG).classify(t) is None


# ── Exchange classifiers ───────────────────────────────────────────────────────

def test_exchange_deposit_fires():
    t = make_transfer(to_address=EXCHANGE, usd_value=500_000)
    event = ExchangeDepositClassifier(_CONFIG).classify(t)
    assert event is not None
    assert event.event_type == EventType.EXCHANGE_DEPOSIT
    assert "Binance" in event.explanation


def test_exchange_deposit_skips_dex():
    t = make_transfer(to_address=DEX, usd_value=500_000)
    assert ExchangeDepositClassifier(_CONFIG).classify(t) is None


def test_exchange_withdrawal_fires():
    t = make_transfer(from_address=EXCHANGE, usd_value=500_000)
    event = ExchangeWithdrawalClassifier(_CONFIG).classify(t)
    assert event is not None
    assert event.event_type == EventType.EXCHANGE_WITHDRAWAL


# ── Contract / token ops ───────────────────────────────────────────────────────

def test_contract_deployment_fires():
    t = make_transfer(is_contract_creation=True, input_data="0x" + "60" * 100)
    event = ContractDeploymentClassifier().classify(t)
    assert event is not None
    assert event.event_type == EventType.CONTRACT_DEPLOYMENT
    assert event.confidence_score == 1.0


def test_contract_deployment_skips_normal_tx():
    t = make_transfer(is_contract_creation=False)
    assert ContractDeploymentClassifier().classify(t) is None


def test_token_mint_fires():
    t = make_transfer(from_address=ZERO, usd_value=500_000)
    event = TokenMintClassifier(_CONFIG).classify(t)
    assert event is not None
    assert event.event_type == EventType.TOKEN_MINT
    assert event.confidence_score == 1.0


def test_token_burn_fires():
    t = make_transfer(to_address=ZERO, usd_value=500_000)
    event = TokenBurnClassifier(_CONFIG).classify(t)
    assert event is not None
    assert event.event_type == EventType.TOKEN_BURN


def test_token_mint_skips_below_threshold():
    t = make_transfer(from_address=ZERO, usd_value=100)
    assert TokenMintClassifier(_CONFIG).classify(t) is None


# ── Swap classifiers ───────────────────────────────────────────────────────────

def test_large_swap_fires_for_dex():
    t = make_transfer(to_address=DEX, usd_value=100_000)
    event = LargeSwapClassifier(_CONFIG).classify(t)
    assert event is not None
    assert event.event_type == EventType.LARGE_SWAP


def test_large_swap_skips_non_dex():
    t = make_transfer(to_address=WHALE, usd_value=100_000)
    assert LargeSwapClassifier(_CONFIG).classify(t) is None


def test_liquidity_added_fires():
    t = make_transfer(to_address=DEX, usd_value=50_000)
    event = LiquidityAddedClassifier(_CONFIG).classify(t)
    assert event is not None
    assert event.event_type == EventType.LIQUIDITY_ADDED


# ── Smart money ───────────────────────────────────────────────────────────────

def test_smart_money_fires_with_score():
    clf = SmartMoneyClassifier(_CONFIG, min_score=0.75)
    clf.load_scores({WHALE: 0.85})
    t = make_transfer(from_address=WHALE, usd_value=500_000)
    event = clf.classify(t)
    assert event is not None
    assert event.event_type == EventType.SMART_MONEY_ACTIVITY


def test_smart_money_skips_low_score():
    clf = SmartMoneyClassifier(_CONFIG)
    clf.load_scores({WHALE: 0.40})
    t = make_transfer(from_address=WHALE, usd_value=500_000)
    assert clf.classify(t) is None


# ── Accumulation / distribution ───────────────────────────────────────────────

def test_accumulation_detected():
    clf = AccumulationDistributionClassifier(_CONFIG)
    receiver = "0xrecvrecvrecvrecvrecvrecvrecvrecvrecvrecv"
    transfers = [
        make_transfer(from_address=WHALE, to_address=receiver, usd_value=150_000)
        for _ in range(3)
    ]
    events = clf.classify_batch(transfers)
    types = [e.event_type for e in events]
    assert EventType.WALLET_ACCUMULATION in types


def test_accumulation_not_detected_below_min_transfers():
    clf = AccumulationDistributionClassifier(_CONFIG)
    receiver = "0xrecvrecvrecvrecvrecvrecvrecvrecvrecvrecv"
    transfers = [
        make_transfer(from_address=WHALE, to_address=receiver, usd_value=150_000)
        for _ in range(2)  # one below the min of 3
    ]
    events = clf.classify_batch(transfers)
    assert not any(e.event_type == EventType.WALLET_ACCUMULATION for e in events)


# ── Confidence score bounds ───────────────────────────────────────────────────

def test_confidence_within_valid_range():
    classifiers_to_test = [
        WhaleBuyClassifier(_CONFIG),
        WhaleSellClassifier(_CONFIG),
        ExchangeDepositClassifier(_CONFIG),
        ExchangeWithdrawalClassifier(_CONFIG),
        LargeSwapClassifier(_CONFIG),
    ]
    t = make_transfer(to_address=EXCHANGE if True else DEX, usd_value=1_000_000)
    for clf in classifiers_to_test:
        event = clf.classify(make_transfer(to_address=EXCHANGE, usd_value=1_000_000))
        if event:
            assert 0.0 <= event.confidence_score <= 1.0
