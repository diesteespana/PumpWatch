"""
Price oracle abstraction layer.

Etherscan does not expose token prices. All USD enrichment goes through
a PriceOracle implementation so we can swap providers (CoinGecko →
CoinMarketCap → on-chain Chainlink) without touching business logic.

Results are cached in Redis to avoid hammering rate limits.
"""
from abc import ABC, abstractmethod
from decimal import Decimal

import httpx
import redis.asyncio as aioredis

from app.core.constants import CACHE_TTL_TOKEN_PRICE
from app.core.exceptions import BlockchainProviderError
from app.core.logging import get_logger

logger = get_logger(__name__)

# Well-known token aliases — CoinGecko uses IDs, not addresses, for these
_COINGECKO_ID_OVERRIDES: dict[str, str] = {
    "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee": "ethereum",  # ETH pseudo-address
    "0x0000000000000000000000000000000000000000": "ethereum",
}

COINGECKO_API_BASE = "https://api.coingecko.com/api/v3"
_REDIS_KEY_PREFIX = "pumpwatch:price:"


class PriceOracle(ABC):
    """Abstract price feed. All implementations must be safe for concurrent use."""

    @abstractmethod
    async def get_price_usd(self, token_address: str, chain: str = "ethereum") -> Decimal:
        """
        Return the current USD price of a token.
        Returns Decimal(0) when price is unavailable rather than raising,
        so a single missing price never breaks a batch.
        """

    @abstractmethod
    async def get_prices_usd(
        self, token_addresses: list[str], chain: str = "ethereum"
    ) -> dict[str, Decimal]:
        """
        Batch price lookup. More efficient than repeated single calls.
        Missing tokens map to Decimal(0).
        """

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if the price feed is reachable."""


class CoinGeckoPriceOracle(PriceOracle):
    """
    CoinGecko free-tier price oracle with Redis caching.

    Free tier: 30 req/min. Caching at CACHE_TTL_TOKEN_PRICE keeps
    us well under the limit even at high event volumes.

    Pro API key support: set COINGECKO_API_KEY in env and pass here.
    """

    _CHAIN_PLATFORM = {
        "ethereum": "ethereum",
        "bsc": "binance-smart-chain",
        "polygon": "polygon-pos",
        "arbitrum": "arbitrum-one",
        "optimism": "optimistic-ethereum",
    }

    def __init__(
        self,
        redis_client: aioredis.Redis,
        api_key: str = "",
    ) -> None:
        self._redis = redis_client
        headers = {"accept": "application/json"}
        if api_key:
            headers["x-cg-pro-api-key"] = api_key
        self._client = httpx.AsyncClient(
            base_url=COINGECKO_API_BASE,
            headers=headers,
            timeout=httpx.Timeout(10.0),
        )

    async def get_price_usd(self, token_address: str, chain: str = "ethereum") -> Decimal:
        prices = await self.get_prices_usd([token_address], chain)
        return prices.get(token_address.lower(), Decimal(0))

    async def get_prices_usd(
        self, token_addresses: list[str], chain: str = "ethereum"
    ) -> dict[str, Decimal]:
        if not token_addresses:
            return {}

        addresses = [a.lower() for a in token_addresses]
        result: dict[str, Decimal] = {}
        uncached: list[str] = []

        # 1. Check cache first
        for addr in addresses:
            override_id = _COINGECKO_ID_OVERRIDES.get(addr)
            cache_key = f"{_REDIS_KEY_PREFIX}{chain}:{override_id or addr}"
            cached = await self._redis.get(cache_key)
            if cached is not None:
                result[addr] = Decimal(cached)
            else:
                uncached.append(addr)

        if not uncached:
            return result

        # 2. Separate ETH/native from ERC-20s
        eth_addresses = [a for a in uncached if a in _COINGECKO_ID_OVERRIDES]
        erc20_addresses = [a for a in uncached if a not in _COINGECKO_ID_OVERRIDES]

        # 3. Fetch native currency prices
        if eth_addresses:
            eth_price = await self._fetch_native_price(chain)
            for addr in eth_addresses:
                result[addr] = eth_price
                await self._cache_price(chain, addr, eth_price)

        # 4. Fetch ERC-20 prices in one batch call
        if erc20_addresses:
            platform = self._CHAIN_PLATFORM.get(chain, "ethereum")
            fetched = await self._fetch_token_prices(platform, erc20_addresses)
            for addr, price in fetched.items():
                result[addr] = price
                await self._cache_price(chain, addr, price)
            for addr in erc20_addresses:
                if addr not in result:
                    result[addr] = Decimal(0)

        return result

    async def health_check(self) -> bool:
        try:
            resp = await self._client.get("/ping")
            return resp.status_code == 200
        except Exception:
            return False

    async def _fetch_native_price(self, chain: str) -> Decimal:
        coin_id = "ethereum" if chain == "ethereum" else chain
        try:
            resp = await self._client.get(
                "/simple/price", params={"ids": coin_id, "vs_currencies": "usd"}
            )
            resp.raise_for_status()
            data = resp.json()
            price = data.get(coin_id, {}).get("usd", 0)
            return Decimal(str(price))
        except Exception as exc:
            logger.warning("native_price_fetch_failed", chain=chain, error=str(exc))
            return Decimal(0)

    async def _fetch_token_prices(
        self, platform: str, addresses: list[str]
    ) -> dict[str, Decimal]:
        contract_addresses = ",".join(addresses)
        try:
            resp = await self._client.get(
                f"/simple/token_price/{platform}",
                params={
                    "contract_addresses": contract_addresses,
                    "vs_currencies": "usd",
                },
            )
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as exc:
            logger.warning("token_price_fetch_failed", status=exc.response.status_code)
            return {}
        except Exception as exc:
            logger.warning("token_price_fetch_failed", error=str(exc))
            return {}

        prices: dict[str, Decimal] = {}
        for addr, info in data.items():
            usd = info.get("usd")
            if usd is not None:
                prices[addr.lower()] = Decimal(str(usd))
        return prices

    async def _cache_price(self, chain: str, address: str, price: Decimal) -> None:
        key = f"{_REDIS_KEY_PREFIX}{chain}:{address}"
        await self._redis.setex(key, CACHE_TTL_TOKEN_PRICE, str(price))
