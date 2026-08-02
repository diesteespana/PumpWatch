"""Unit tests for ethereum utility functions."""
from decimal import Decimal

import pytest

from app.utils.ethereum import (
    eth_to_usd,
    is_contract_create,
    is_valid_address,
    is_zero_address,
    normalize_address,
    short_address,
    token_amount,
    wei_to_eth,
)

VALID_ADDR = "0x3f5ce5fbfe3e9af3971dd833d26ba9b5c936f0be"
ZERO_ADDR = "0x0000000000000000000000000000000000000000"


def test_valid_address():
    assert is_valid_address(VALID_ADDR)
    assert is_valid_address(VALID_ADDR.upper())
    assert not is_valid_address("0xinvalid")
    assert not is_valid_address("not-an-address")
    assert not is_valid_address("")


def test_normalize_address():
    assert normalize_address("  0xABCDEF  ") == "0xabcdef"


def test_is_zero_address():
    assert is_zero_address(ZERO_ADDR)
    assert not is_zero_address(VALID_ADDR)


def test_is_contract_create():
    assert is_contract_create("")
    assert is_contract_create(ZERO_ADDR)
    assert not is_contract_create(VALID_ADDR)


def test_wei_to_eth():
    assert wei_to_eth(10**18) == Decimal(1)
    assert wei_to_eth(5 * 10**18) == Decimal(5)
    assert wei_to_eth(0) == Decimal(0)


def test_eth_to_usd():
    assert eth_to_usd(Decimal("2"), Decimal("3000")) == Decimal("6000")


def test_token_amount():
    assert token_amount(1_000_000, 6) == Decimal(1)     # USDC style
    assert token_amount(10**18, 18) == Decimal(1)        # ETH style
    assert token_amount(0, 18) == Decimal(0)


def test_token_amount_negative_decimals_raises():
    with pytest.raises(ValueError):
        token_amount(100, -1)


def test_short_address():
    addr = VALID_ADDR
    short = short_address(addr, chars=6)
    assert short.startswith("0x3f5c")
    assert "…" in short
    assert short.endswith(addr[-6:])
