"""Domain exceptions — typed errors that cross architectural layers."""


class PumpWatchError(Exception):
    """Base exception for all domain errors."""


# ── Auth ──────────────────────────────────────────────────
class AuthenticationError(PumpWatchError):
    pass


class AuthorizationError(PumpWatchError):
    pass


class InvalidTokenError(AuthenticationError):
    pass


class ExpiredTokenError(AuthenticationError):
    pass


# ── Resources ─────────────────────────────────────────────
class NotFoundError(PumpWatchError):
    def __init__(self, resource: str, identifier: str | int) -> None:
        super().__init__(f"{resource} not found: {identifier}")
        self.resource = resource
        self.identifier = identifier


class ConflictError(PumpWatchError):
    pass


# ── Blockchain ────────────────────────────────────────────
class BlockchainProviderError(PumpWatchError):
    pass


class RateLimitedError(BlockchainProviderError):
    pass


class InvalidAddressError(BlockchainProviderError):
    pass


# ── Notifications ─────────────────────────────────────────
class NotificationDeliveryError(PumpWatchError):
    pass


# ── Validation ────────────────────────────────────────────
class ValidationError(PumpWatchError):
    pass
