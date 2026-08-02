"""Single source of truth for magic values used across the application."""

# ── Blockchain ────────────────────────────────────────────
ETHEREUM_CHAIN_ID = 1
ETHEREUM_CHAIN_NAME = "ethereum"
WEI_PER_ETH = 10**18
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

# ── Detection ─────────────────────────────────────────────
MIN_CONFIDENCE_SCORE = 0.0
MAX_CONFIDENCE_SCORE = 1.0
DEFAULT_WHALE_THRESHOLD_USD = 100_000.0
HIGH_CONFIDENCE_THRESHOLD = 0.8

# ── Pagination ────────────────────────────────────────────
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# ── Auth ──────────────────────────────────────────────────
PASSWORD_MIN_LENGTH = 8
BCRYPT_ROUNDS = 12

# ── Rate Limiting ─────────────────────────────────────────
RATE_LIMIT_DEFAULT_REQUESTS = 100
RATE_LIMIT_DEFAULT_WINDOW_SECONDS = 60

# ── Cache TTLs (seconds) ─────────────────────────────────
CACHE_TTL_TOKEN_PRICE = 60
CACHE_TTL_WALLET_PROFILE = 300
CACHE_TTL_RECENT_EVENTS = 15
