"""
Ethereum-specific utility functions.

These are pure functions — no I/O, no dependencies on services.
All address handling goes through here so normalisation is consistent.
"""
import re
from decimal import Decimal

from app.core.constants import WEI_PER_ETH, ZERO_ADDRESS

_HEX_ADDRESS_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")


def is_valid_address(address: str) -> bool:
    """Return True if address matches the Ethereum address format."""
    return bool(_HEX_ADDRESS_RE.match(address))


def normalize_address(address: str) -> str:
    """Return lowercase hex address, stripping whitespace."""
    return address.strip().lower()


def is_zero_address(address: str) -> bool:
    return normalize_address(address) == ZERO_ADDRESS


def is_contract_create(to_address: str) -> bool:
    """True when a transaction creates a contract (empty 'to' field)."""
    return not to_address or is_zero_address(to_address)


def wei_to_eth(wei: int) -> Decimal:
    return Decimal(wei) / Decimal(WEI_PER_ETH)


def eth_to_usd(eth_amount: Decimal, eth_price_usd: Decimal) -> Decimal:
    return eth_amount * eth_price_usd


def short_address(address: str, chars: int = 6) -> str:
    """Return '0xAbCd…EfGh' display format."""
    addr = address.strip()
    if len(addr) <= chars * 2:
        return addr
    return f"{addr[:chars]}…{addr[-chars:]}"


def token_amount(raw_value: int, decimals: int) -> Decimal:
    """Convert a raw ERC-20 integer value to its human-readable amount."""
    if decimals < 0:
        raise ValueError(f"decimals must be non-negative, got {decimals}")
    return Decimal(raw_value) / Decimal(10**decimals)
