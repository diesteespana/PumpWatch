"""
ChainService — the single orchestrator for one blockchain's polling cycle.

Responsibilities:
1. Determine which blocks haven't been processed yet (via BlockTracker)
2. Fetch transactions and token transfers from BlockchainProvider
3. Enrich each transfer with a USD value from PriceOracle
4. Return enriched, normalised data ready for the DetectionEngine
5. Advance the BlockTracker on success

This class deliberately knows nothing about event classification or
notifications — those are downstream concerns.
"""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.blockchain.address_registry import AddressLabel, AddressRegistry
from app.blockchain.block_tracker import BlockTracker
from app.blockchain.interfaces import BlockchainProvider, RawTransaction, TokenTransfer
from app.blockchain.price_oracle import PriceOracle
from app.core.constants import ETHEREUM_CHAIN_NAME
from app.core.logging import get_logger
from app.utils.ethereum import is_contract_create, normalize_address, wei_to_eth

logger = get_logger(__name__)

# Never fetch more than this many blocks in one cycle — protects against
# runaway memory usage after a long downtime.
_MAX_BLOCKS_PER_CYCLE = 200


@dataclass(frozen=True)
class EnrichedTransfer:
    """
    A single token or ETH transfer enriched with metadata.

    This is the unit of work passed to the DetectionEngine.
    It intentionally duplicates some fields from RawTransaction /
    TokenTransfer so the DetectionEngine has one cohesive object.
    """

    tx_hash: str
    block_number: int
    timestamp: datetime
    chain: str

    from_address: str
    to_address: str
    from_label: AddressLabel | None
    to_label: AddressLabel | None

    # Token info (for ETH: symbol="ETH", contract=ZERO_ADDRESS)
    token_symbol: str
    token_contract: str
    token_decimals: int
    raw_value: int
    token_amount: Decimal

    usd_value: Decimal
    is_contract_creation: bool
    input_data: str


class EthereumChainService:
    """
    Polling service for the Ethereum chain.

    Designed to be called once per scheduler interval.
    Stateless between calls; all state lives in BlockTracker (Redis).
    """

    def __init__(
        self,
        provider: BlockchainProvider,
        price_oracle: PriceOracle,
        block_tracker: BlockTracker,
        address_registry: AddressRegistry,
        chain: str = ETHEREUM_CHAIN_NAME,
    ) -> None:
        self._provider = provider
        self._price_oracle = price_oracle
        self._tracker = block_tracker
        self._registry = address_registry
        self._chain = chain

    async def poll_cycle(self, watched_addresses: list[str]) -> list[EnrichedTransfer]:
        """
        Fetch and enrich all new blockchain activity for `watched_addresses`.

        Called by APScheduler every BLOCKCHAIN_POLL_INTERVAL_SECONDS.
        Returns an empty list (never raises) so a transient API error
        doesn't crash the scheduler.
        """
        if not watched_addresses:
            return []

        try:
            return await self._run_cycle(watched_addresses)
        except Exception as exc:
            logger.error("poll_cycle_failed", chain=self._chain, error=str(exc), exc_info=True)
            return []

    async def _run_cycle(self, watched_addresses: list[str]) -> list[EnrichedTransfer]:
        current_block = await self._provider.get_latest_block_number()
        start_block = await self._tracker.get_last_processed_block(current_block)

        if start_block >= current_block:
            logger.debug("poll_cycle_no_new_blocks", chain=self._chain, block=current_block)
            return []

        # Guard against processing huge gaps after downtime
        end_block = min(current_block, start_block + _MAX_BLOCKS_PER_CYCLE)

        logger.info(
            "poll_cycle_start",
            chain=self._chain,
            start_block=start_block,
            end_block=end_block,
            addresses=len(watched_addresses),
        )

        all_transfers: list[EnrichedTransfer] = []

        for address in watched_addresses:
            address = normalize_address(address)
            transfers = await self._fetch_address(address, start_block, end_block)
            all_transfers.extend(transfers)

        # Deduplicate by tx_hash + address (same tx can appear for multiple watched addrs)
        seen: set[tuple[str, str]] = set()
        unique: list[EnrichedTransfer] = []
        for t in all_transfers:
            key = (t.tx_hash, t.from_address)
            if key not in seen:
                seen.add(key)
                unique.append(t)

        await self._tracker.set_last_processed_block(end_block)

        logger.info(
            "poll_cycle_complete",
            chain=self._chain,
            end_block=end_block,
            transfers_found=len(unique),
        )
        return unique

    async def _fetch_address(
        self, address: str, start_block: int, end_block: int
    ) -> list[EnrichedTransfer]:
        txs, token_transfers = await self._fetch_raw(address, start_block, end_block)

        # Collect all token contracts for batch price lookup
        contracts = {t.contract_address for t in token_transfers}
        eth_pseudo = "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
        if txs:
            contracts.add(eth_pseudo)

        prices = await self._price_oracle.get_prices_usd(list(contracts), self._chain)

        result: list[EnrichedTransfer] = []

        for tx in txs:
            eth_price = prices.get(eth_pseudo, Decimal(0))
            eth_amount = wei_to_eth(tx.value_wei)
            usd_value = eth_amount * eth_price

            result.append(
                EnrichedTransfer(
                    tx_hash=tx.tx_hash,
                    block_number=tx.block_number,
                    timestamp=tx.timestamp,
                    chain=self._chain,
                    from_address=tx.from_address,
                    to_address=tx.to_address,
                    from_label=self._registry.get(tx.from_address),
                    to_label=self._registry.get(tx.to_address),
                    token_symbol="ETH",
                    token_contract=eth_pseudo,
                    token_decimals=18,
                    raw_value=tx.value_wei,
                    token_amount=eth_amount,
                    usd_value=usd_value,
                    is_contract_creation=is_contract_create(tx.to_address),
                    input_data=tx.input_data,
                )
            )

        for transfer in token_transfers:
            price = prices.get(transfer.contract_address, Decimal(0))
            usd_value = transfer.value * price

            result.append(
                EnrichedTransfer(
                    tx_hash=transfer.tx_hash,
                    block_number=transfer.block_number,
                    timestamp=transfer.timestamp,
                    chain=self._chain,
                    from_address=transfer.from_address,
                    to_address=transfer.to_address,
                    from_label=self._registry.get(transfer.from_address),
                    to_label=self._registry.get(transfer.to_address),
                    token_symbol=transfer.token_symbol,
                    token_contract=transfer.contract_address,
                    token_decimals=transfer.token_decimals,
                    raw_value=transfer.raw_value,
                    token_amount=transfer.value,
                    usd_value=usd_value,
                    is_contract_creation=False,
                    input_data="",
                )
            )

        return result

    async def _fetch_raw(
        self, address: str, start_block: int, end_block: int
    ) -> tuple[list[RawTransaction], list[TokenTransfer]]:
        import asyncio

        txs_task = asyncio.create_task(
            self._provider.get_transactions(address, start_block, end_block)
        )
        transfers_task = asyncio.create_task(
            self._provider.get_token_transfers(address, None, start_block, end_block)
        )
        txs, transfers = await asyncio.gather(txs_task, transfers_task)
        return txs, transfers
