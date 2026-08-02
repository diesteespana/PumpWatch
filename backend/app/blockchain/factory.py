from app.blockchain.interfaces import BlockchainProvider
from app.core.config import BlockchainProvider as ProviderEnum, get_settings


def create_blockchain_provider() -> BlockchainProvider:
    """
    Factory that returns the configured provider implementation.

    To add a new provider: implement BlockchainProvider, register it here.
    No other file needs to change.
    """
    settings = get_settings()

    match settings.active_blockchain_provider:
        case ProviderEnum.ETHERSCAN:
            from app.blockchain.providers.etherscan import EtherscanProvider
            return EtherscanProvider(api_key=settings.etherscan_api_key)
        case ProviderEnum.ALCHEMY:
            raise NotImplementedError("Alchemy provider — Milestone 2+")
        case ProviderEnum.INFURA:
            raise NotImplementedError("Infura provider — Milestone 2+")
        case ProviderEnum.MORALIS:
            raise NotImplementedError("Moralis provider — Milestone 2+")
        case _:
            raise ValueError(f"Unknown provider: {settings.active_blockchain_provider}")
