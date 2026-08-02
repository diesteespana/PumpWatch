from enum import StrEnum
from functools import lru_cache

from pydantic import Field, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class BlockchainProvider(StrEnum):
    ETHERSCAN = "etherscan"
    ALCHEMY = "alchemy"
    INFURA = "infura"
    MORALIS = "moralis"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ── Application ───────────────────────────────────────
    app_env: Environment = Environment.DEVELOPMENT
    app_secret_key: str = Field(min_length=32)
    app_debug: bool = False
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    # ── Database ──────────────────────────────────────────
    database_url: PostgresDsn

    # ── JWT ───────────────────────────────────────────────
    jwt_secret_key: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 30

    # ── Blockchain Providers ──────────────────────────────
    active_blockchain_provider: BlockchainProvider = BlockchainProvider.ETHERSCAN
    etherscan_api_key: str = ""
    alchemy_api_key: str = ""
    infura_project_id: str = ""
    moralis_api_key: str = ""

    # ── Detection Thresholds ──────────────────────────────
    whale_threshold_usd: float = 100_000.0
    blockchain_poll_interval_seconds: int = 30

    # ── Redis ─────────────────────────────────────────────
    redis_url: RedisDsn = "redis://localhost:6379/0"  # type: ignore[assignment]

    # ── Notifications ─────────────────────────────────────
    telegram_bot_token: str = ""
    discord_webhook_url: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@pumpwat.ch"

    # ── CORS ──────────────────────────────────────────────
    allowed_origins: list[str] = ["http://localhost:3000"]

    @property
    def is_production(self) -> bool:
        return self.app_env == Environment.PRODUCTION

    @property
    def database_url_str(self) -> str:
        return str(self.database_url)


@lru_cache
def get_settings() -> Settings:
    return Settings()
