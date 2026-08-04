# Import all models here so Alembic's autogenerate and the session can discover them.
from app.models.alert import Alert
from app.models.audit_log import AuditLog
from app.models.event import OnChainEvent
from app.models.notification import NotificationSetting
from app.models.token import Token, UserTrackedToken
from app.models.user import User
from app.models.wallet import UserTrackedWallet, Wallet
from app.models.wallet_score import WalletScore

__all__ = [
    "User",
    "Wallet",
    "UserTrackedWallet",
    "Token",
    "UserTrackedToken",
    "OnChainEvent",
    "Alert",
    "NotificationSetting",
    "WalletScore",
    "AuditLog",
]
