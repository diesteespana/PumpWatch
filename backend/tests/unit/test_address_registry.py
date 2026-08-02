"""Unit tests for AddressRegistry."""
import pytest

from app.blockchain.address_registry import AddressCategory, AddressLabel, AddressRegistry

BINANCE_1 = "0x3f5ce5fbfe3e9af3971dd833d26ba9b5c936f0be"
UNISWAP_V3 = "0xe592427a0aece92de3edee1f18e0157c05861564"
UNKNOWN = "0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef"


@pytest.fixture
def registry():
    return AddressRegistry()


def test_known_cex_is_classified(registry):
    label = registry.get(BINANCE_1)
    assert label is not None
    assert label.category == AddressCategory.EXCHANGE_CEX
    assert "Binance" in label.name


def test_known_dex_is_classified(registry):
    label = registry.get(UNISWAP_V3)
    assert label is not None
    assert label.category == AddressCategory.EXCHANGE_DEX


def test_unknown_address_returns_none(registry):
    assert registry.get(UNKNOWN) is None


def test_is_exchange_true_for_cex(registry):
    assert registry.is_exchange(BINANCE_1) is True


def test_is_exchange_true_for_dex(registry):
    assert registry.is_exchange(UNISWAP_V3) is True


def test_is_cex_false_for_dex(registry):
    assert registry.is_cex(UNISWAP_V3) is False


def test_is_dex_false_for_cex(registry):
    assert registry.is_dex(BINANCE_1) is False


def test_lookup_is_case_insensitive(registry):
    upper = BINANCE_1.upper()
    assert registry.get(upper) is not None


def test_get_name_unknown(registry):
    assert registry.get_name(UNKNOWN) == "Unknown"


def test_register_new_label(registry):
    label = AddressLabel(
        address="0xaaaa000000000000000000000000000000000001",
        name="Test Wallet",
        category=AddressCategory.EXCHANGE_CEX,
    )
    registry.register(label)
    assert registry.get(label.address) == label


def test_registry_has_expected_size(registry):
    assert len(registry) >= 20
