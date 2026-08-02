"""
Known address registry for Ethereum.

Classifying a wallet as "Binance hot wallet" vs "unknown" determines which
event types the detection engine assigns (ExchangeDeposit vs WhaleBuy).

Design:
- `AddressLabel` is the canonical record for a labelled address
- `AddressRegistry` is loaded at startup and kept in memory (< 1 MB)
- Future: sync from community DB (Etherscan labels, Arkham, etc.)
"""
from dataclasses import dataclass
from enum import StrEnum


class AddressCategory(StrEnum):
    EXCHANGE_CEX = "exchange_cex"
    EXCHANGE_DEX = "exchange_dex"
    BRIDGE = "bridge"
    LENDING_PROTOCOL = "lending_protocol"
    STAKING = "staking"
    NFT_MARKETPLACE = "nft_marketplace"
    MINER = "miner"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class AddressLabel:
    address: str
    name: str
    category: AddressCategory
    chain: str = "ethereum"


# fmt: off
_SEED_LABELS: list[AddressLabel] = [
    # ── Centralised Exchanges ─────────────────────────────────────────────
    AddressLabel("0x3f5ce5fbfe3e9af3971dd833d26ba9b5c936f0be", "Binance Hot Wallet 1", AddressCategory.EXCHANGE_CEX),
    AddressLabel("0xd551234ae421e3bcba99a0da6d736074f22192ff", "Binance Hot Wallet 2", AddressCategory.EXCHANGE_CEX),
    AddressLabel("0x564286362092d8e7936f0549571a803b203aaced", "Binance Hot Wallet 3", AddressCategory.EXCHANGE_CEX),
    AddressLabel("0x0681d8db095565fe8a346fa0277bffde9c0edbbf", "Binance Hot Wallet 4", AddressCategory.EXCHANGE_CEX),
    AddressLabel("0xfe9e8709d3215310075d67e3ed32a380ccf451c8", "Binance Hot Wallet 5", AddressCategory.EXCHANGE_CEX),
    AddressLabel("0xa910f92acdaf488fa6ef02174fb86208ad7ea957", "Binance Hot Wallet 6", AddressCategory.EXCHANGE_CEX),
    AddressLabel("0x1522900b6dafac587d499a862861c0869be6e428", "Binance Cold Wallet",  AddressCategory.EXCHANGE_CEX),
    AddressLabel("0x71660c4005ba85c37ccec55d0c4493e66fe775d3", "Coinbase 1",           AddressCategory.EXCHANGE_CEX),
    AddressLabel("0x503828976d22510aad0201ac7ec88293211d23da", "Coinbase 2",           AddressCategory.EXCHANGE_CEX),
    AddressLabel("0xddfabcdc4d8ffc6d5beaf154f18b778f892a0740", "Coinbase 3",           AddressCategory.EXCHANGE_CEX),
    AddressLabel("0x3cd751e6b0078be393132286c442345e5dc49699", "Coinbase 4",           AddressCategory.EXCHANGE_CEX),
    AddressLabel("0xb5d85cbf7cb3ee0d56b3bb207d5fc4b82f43f511", "Coinbase 5",           AddressCategory.EXCHANGE_CEX),
    AddressLabel("0xeb2629a2734e272bcc07bda959863f316f4bd4cf", "Coinbase 6",           AddressCategory.EXCHANGE_CEX),
    AddressLabel("0x2b5634c42055806a59e9107ed44d43c426e58258", "KuCoin Hot Wallet 1",  AddressCategory.EXCHANGE_CEX),
    AddressLabel("0xa1d8d972560c2f8144af871db508f0b0b10a3fbf", "KuCoin Hot Wallet 2",  AddressCategory.EXCHANGE_CEX),
    AddressLabel("0xe93381fb4c4f14bda253907b18fad305d799241a", "Kraken 1",             AddressCategory.EXCHANGE_CEX),
    AddressLabel("0x267be1c1d684f78cb4f6a176c4911b741e4ffdc0", "Kraken 2",             AddressCategory.EXCHANGE_CEX),
    AddressLabel("0xfa52274dd61e1643d2205169732f29114bc240b3", "Kraken 3",             AddressCategory.EXCHANGE_CEX),
    AddressLabel("0x53d284357ec70ce289d6d64134dfac8e511c8a3d", "Gemini 1",             AddressCategory.EXCHANGE_CEX),
    AddressLabel("0xd24400ae8bfebb18ca49be86258a3c749cf46853", "Gemini 2",             AddressCategory.EXCHANGE_CEX),
    AddressLabel("0x742d35cc6634c0532925a3b844bc454e4438f44e", "Bitfinex 1",           AddressCategory.EXCHANGE_CEX),
    AddressLabel("0x876eabf441b2ee5b5b0554fd502a8e0600950cfa", "Bitfinex 2",           AddressCategory.EXCHANGE_CEX),
    AddressLabel("0x876eabf441b2ee5b5b0554fd502a8e0600950cfa", "OKX Hot Wallet",       AddressCategory.EXCHANGE_CEX),
    AddressLabel("0x6cc5f688a315f3dc28a7781717a9a798a59fda7b", "OKX 2",               AddressCategory.EXCHANGE_CEX),

    # ── Decentralised Exchanges ───────────────────────────────────────────
    AddressLabel("0x7a250d5630b4cf539739df2c5dacb4c659f2488d", "Uniswap V2: Router",  AddressCategory.EXCHANGE_DEX),
    AddressLabel("0xe592427a0aece92de3edee1f18e0157c05861564", "Uniswap V3: Router 1",AddressCategory.EXCHANGE_DEX),
    AddressLabel("0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45", "Uniswap V3: Router 2",AddressCategory.EXCHANGE_DEX),
    AddressLabel("0xd9e1ce17f2641f24ae83637ab66a2cca9c378b9f", "Sushiswap: Router",   AddressCategory.EXCHANGE_DEX),
    AddressLabel("0xdef1c0ded9bec7f1a1670819833240f027b25eff", "0x Exchange Proxy",    AddressCategory.EXCHANGE_DEX),
    AddressLabel("0x1111111254eeb25477b68fb85ed929f73a960582", "1inch V5: Aggregator", AddressCategory.EXCHANGE_DEX),

    # ── Bridges ──────────────────────────────────────────────────────────
    AddressLabel("0x3ee18b2214aff97000d974cf647e7c347e8fa585", "Wormhole Bridge",      AddressCategory.BRIDGE),
    AddressLabel("0x40ec5b33f54e0e8a33a975908c5ba1c14e5bbbdf", "Polygon Bridge",       AddressCategory.BRIDGE),
    AddressLabel("0x8eb8a3b98659cce290402893d0123abb75e3ab28", "Avalanche Bridge",     AddressCategory.BRIDGE),

    # ── Lending Protocols ─────────────────────────────────────────────────
    AddressLabel("0x7d2768de32b0b80b7a3454c06bdac94a69ddc7a9", "Aave V2: Lending Pool",     AddressCategory.LENDING_PROTOCOL),
    AddressLabel("0x87870bca3f3fd6335c3f4ce8392d69350b4fa4e2", "Aave V3: Pool",              AddressCategory.LENDING_PROTOCOL),
    AddressLabel("0x3d9819210a31b4961b30ef54be2aed79b9c9cd3b", "Compound: Comptroller",      AddressCategory.LENDING_PROTOCOL),
    AddressLabel("0xc11b1268c1a384e55c48c2391d8d480264a3a7f4", "Compound: cWBTC",            AddressCategory.LENDING_PROTOCOL),
]
# fmt: on


class AddressRegistry:
    """
    In-memory registry of labelled addresses.

    Lookup is O(1). Thread-safe for reads (dict is immutable after init).
    """

    def __init__(self, labels: list[AddressLabel] | None = None) -> None:
        seed = labels if labels is not None else _SEED_LABELS
        self._by_address: dict[str, AddressLabel] = {
            label.address.lower(): label for label in seed
        }

    def get(self, address: str) -> AddressLabel | None:
        return self._by_address.get(address.lower())

    def is_exchange(self, address: str) -> bool:
        label = self.get(address)
        return label is not None and label.category in (
            AddressCategory.EXCHANGE_CEX,
            AddressCategory.EXCHANGE_DEX,
        )

    def is_cex(self, address: str) -> bool:
        label = self.get(address)
        return label is not None and label.category == AddressCategory.EXCHANGE_CEX

    def is_dex(self, address: str) -> bool:
        label = self.get(address)
        return label is not None and label.category == AddressCategory.EXCHANGE_DEX

    def get_name(self, address: str) -> str:
        label = self.get(address)
        return label.name if label else "Unknown"

    def register(self, label: AddressLabel) -> None:
        """Add or overwrite a label at runtime (e.g. from DB on startup)."""
        self._by_address[label.address.lower()] = label

    def __len__(self) -> int:
        return len(self._by_address)
