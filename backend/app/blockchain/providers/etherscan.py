"""
Etherscan implementation of BlockchainProvider.

Milestone 2 will flesh out every method fully.
This file defines the structure, types, and error handling patterns
so Milestone 3+ can depend on this interface confidently.
"""
from datetime import datetime, timezone
from decimal import Decimal

import httpx

from app.blockchain.interfaces import (
    BlockchainProvider,
    RawTransaction,
    TokenTransfer,
    WalletBalance,
)
from app.core.constants import WEI_PER_ETH
from app.core.exceptions import BlockchainProviderError, RateLimitedError
from app.core.logging import get_logger

logger = get_logger(__name__)

ETHERSCAN_API_BASE = "https://api.etherscan.io/api"
ETHERSCAN_RATE_LIMIT_MSG = "Max rate limit reached"


class EtherscanProvider(BlockchainProvider):
    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ValueError("Etherscan API key is required")
        self._api_key = api_key
        self._client = httpx.AsyncClient(
            base_url=ETHERSCAN_API_BASE,
            timeout=httpx.Timeout(15.0),
        )

    async def _get(self, params: dict) -> dict:
        params["apikey"] = self._api_key
        try:
            resp = await self._client.get("", params=params)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as exc:
            raise BlockchainProviderError(f"HTTP {exc.response.status_code}") from exc
        except httpx.RequestError as exc:
            raise BlockchainProviderError(f"Network error: {exc}") from exc

        if data.get("message") == ETHERSCAN_RATE_LIMIT_MSG:
            raise RateLimitedError("Etherscan rate limit exceeded")

        if data.get("status") == "0" and data.get("result") not in ("", [], None):
            logger.warning("etherscan_api_error", message=data.get("message"))

        return data

    async def get_transactions(
        self,
        address: str,
        start_block: int = 0,
        end_block: int = 99_999_999,
    ) -> list[RawTransaction]:
        data = await self._get(
            {
                "module": "account",
                "action": "txlist",
                "address": address,
                "startblock": start_block,
                "endblock": end_block,
                "sort": "desc",
            }
        )
        return [self._parse_transaction(tx) for tx in (data.get("result") or [])]

    async def get_token_transfers(
        self,
        address: str,
        contract_address: str | None = None,
        start_block: int = 0,
        end_block: int = 99_999_999,
    ) -> list[TokenTransfer]:
        params: dict = {
            "module": "account",
            "action": "tokentx",
            "address": address,
            "startblock": start_block,
            "endblock": end_block,
            "sort": "desc",
        }
        if contract_address:
            params["contractaddress"] = contract_address

        data = await self._get(params)
        return [self._parse_token_transfer(tx) for tx in (data.get("result") or [])]

    async def get_wallet_balance(self, address: str) -> WalletBalance:
        data = await self._get(
            {"module": "account", "action": "balance", "address": address, "tag": "latest"}
        )
        eth_wei = int(data.get("result", 0))
        return WalletBalance(address=address, eth_balance_wei=eth_wei, token_balances={})

    async def get_latest_block_number(self) -> int:
        data = await self._get({"module": "proxy", "action": "eth_blockNumber"})
        return int(data["result"], 16)

    async def get_token_price_usd(self, contract_address: str) -> Decimal:
        # Etherscan does not expose a price API; callers should use a price oracle.
        # Returning 0 until a price oracle integration is added in Milestone 2.
        logger.warning("token_price_not_implemented", contract=contract_address)
        return Decimal(0)

    async def health_check(self) -> bool:
        try:
            block = await self.get_latest_block_number()
            return block > 0
        except Exception:
            return False

    @staticmethod
    def _parse_transaction(raw: dict) -> RawTransaction:
        return RawTransaction(
            tx_hash=raw["hash"],
            block_number=int(raw["blockNumber"]),
            timestamp=datetime.fromtimestamp(int(raw["timeStamp"]), tz=timezone.utc),
            from_address=raw["from"].lower(),
            to_address=raw.get("to", "").lower(),
            value_wei=int(raw["value"]),
            gas_used=int(raw.get("gasUsed", 0)),
            gas_price_wei=int(raw.get("gasPrice", 0)),
            is_error=raw.get("isError") == "1",
            input_data=raw.get("input", "0x"),
        )

    @staticmethod
    def _parse_token_transfer(raw: dict) -> TokenTransfer:
        decimals = int(raw.get("tokenDecimal", 18))
        return TokenTransfer(
            tx_hash=raw["hash"],
            block_number=int(raw["blockNumber"]),
            timestamp=datetime.fromtimestamp(int(raw["timeStamp"]), tz=timezone.utc),
            from_address=raw["from"].lower(),
            to_address=raw["to"].lower(),
            contract_address=raw["contractAddress"].lower(),
            token_name=raw.get("tokenName", ""),
            token_symbol=raw.get("tokenSymbol", ""),
            token_decimals=decimals,
            raw_value=int(raw.get("value", 0)),
        )
