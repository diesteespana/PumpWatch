"""
Blockchain provider abstraction layer.

All blockchain data access goes through these interfaces.
Business logic never imports provider-specific code directly.
New providers (Alchemy, Infura, Moralis) implement BlockchainProvider and
are wired up in the factory — zero changes elsewhere.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class RawTransaction:
    tx_hash: str
    block_number: int
    timestamp: datetime
    from_address: str
    to_address: str
    value_wei: int
    gas_used: int
    gas_price_wei: int
    is_error: bool
    input_data: str


@dataclass(frozen=True)
class TokenTransfer:
    tx_hash: str
    block_number: int
    timestamp: datetime
    from_address: str
    to_address: str
    contract_address: str
    token_name: str
    token_symbol: str
    token_decimals: int
    raw_value: int

    @property
    def value(self) -> Decimal:
        return Decimal(self.raw_value) / Decimal(10**self.token_decimals)


@dataclass(frozen=True)
class WalletBalance:
    address: str
    eth_balance_wei: int
    token_balances: dict[str, Decimal]  # contract_address -> balance


class BlockchainProvider(ABC):
    """
    Abstract interface for all blockchain data providers.

    Implementations must be stateless and thread-safe.
    All methods are async to accommodate network I/O.
    """

    @abstractmethod
    async def get_transactions(
        self,
        address: str,
        start_block: int = 0,
        end_block: int = 99_999_999,
    ) -> list[RawTransaction]:
        """Return normal ETH transactions for an address."""

    @abstractmethod
    async def get_token_transfers(
        self,
        address: str,
        contract_address: str | None = None,
        start_block: int = 0,
        end_block: int = 99_999_999,
    ) -> list[TokenTransfer]:
        """Return ERC-20 token transfer events for an address."""

    @abstractmethod
    async def get_wallet_balance(self, address: str) -> WalletBalance:
        """Return ETH + token balances for an address."""

    @abstractmethod
    async def get_latest_block_number(self) -> int:
        """Return the most recent block number on the chain."""

    @abstractmethod
    async def get_token_price_usd(self, contract_address: str) -> Decimal:
        """Return the current USD price of a token."""

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if the provider is reachable and operational."""
