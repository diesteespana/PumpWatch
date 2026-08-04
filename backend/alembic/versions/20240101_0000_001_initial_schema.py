"""initial schema

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── users ─────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("username", sa.String(50), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_superuser", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("subscription_tier", sa.String(20), nullable=False, server_default="free"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    # ── wallets ───────────────────────────────────────────
    op.create_table(
        "wallets",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("address", sa.String(42), nullable=False),
        sa.Column("chain", sa.String(30), nullable=False, server_default="ethereum"),
        sa.Column("label", sa.String(100), nullable=False, server_default=""),
        sa.Column("is_exchange", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("exchange_name", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("address", "chain", name="uq_wallet_address_chain"),
    )
    op.create_index("ix_wallets_address", "wallets", ["address"])

    # ── user_tracked_wallets ──────────────────────────────
    op.create_table(
        "user_tracked_wallets",
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("wallet_id", UUID(as_uuid=True), sa.ForeignKey("wallets.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("custom_label", sa.String(100), nullable=True),
        sa.Column("threshold_usd", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # ── tokens ────────────────────────────────────────────
    op.create_table(
        "tokens",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("contract_address", sa.String(42), nullable=False),
        sa.Column("chain", sa.String(30), nullable=False, server_default="ethereum"),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("decimals", sa.Integer(), nullable=False, server_default="18"),
        sa.Column("coingecko_id", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("contract_address", "chain", name="uq_token_contract_chain"),
    )
    op.create_index("ix_tokens_contract_address", "tokens", ["contract_address"])
    op.create_index("ix_tokens_symbol", "tokens", ["symbol"])

    # ── user_tracked_tokens ───────────────────────────────
    op.create_table(
        "user_tracked_tokens",
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("token_id", UUID(as_uuid=True), sa.ForeignKey("tokens.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("threshold_usd", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # ── on_chain_events ───────────────────────────────────
    op.create_table(
        "on_chain_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("blockchain", sa.String(30), nullable=False),
        sa.Column("tx_hash", sa.String(66), nullable=False),
        sa.Column("block_number", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("wallet_address", sa.String(42), nullable=False),
        sa.Column("token_symbol", sa.String(20), nullable=False),
        sa.Column("token_contract", sa.String(42), nullable=False),
        sa.Column("usd_value", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("raw_metadata", JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_on_chain_events_event_type", "on_chain_events", ["event_type"])
    op.create_index("ix_on_chain_events_tx_hash", "on_chain_events", ["tx_hash"])
    op.create_index("ix_on_chain_events_timestamp", "on_chain_events", ["timestamp"])
    op.create_index("ix_on_chain_events_wallet_address", "on_chain_events", ["wallet_address"])
    op.create_index("ix_on_chain_events_token_contract", "on_chain_events", ["token_contract"])
    op.create_index(
        "ix_events_chain_type_timestamp", "on_chain_events",
        ["blockchain", "event_type", "timestamp"]
    )
    op.create_index(
        "ix_events_wallet_timestamp", "on_chain_events",
        ["wallet_address", "timestamp"]
    )

    # ── alerts ────────────────────────────────────────────
    op.create_table(
        "alerts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("event_types", JSONB(), nullable=False, server_default="[]"),
        sa.Column("wallet_addresses", JSONB(), nullable=False, server_default="[]"),
        sa.Column("token_contracts", JSONB(), nullable=False, server_default="[]"),
        sa.Column("min_usd_value", sa.Float(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_alerts_user_id", "alerts", ["user_id"])

    # ── notification_settings ─────────────────────────────
    op.create_table(
        "notification_settings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("channel", sa.String(30), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("config", JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_notification_settings_user_id", "notification_settings", ["user_id"])

    # ── wallet_scores ─────────────────────────────────────
    op.create_table(
        "wallet_scores",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("wallet_id", UUID(as_uuid=True), sa.ForeignKey("wallets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("win_rate", sa.Float(), nullable=True),
        sa.Column("trade_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("insights", JSONB(), nullable=False, server_default="[]"),
        sa.Column("scored_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("wallet_id", name="uq_wallet_scores_wallet_id"),
    )
    op.create_index("ix_wallet_scores_wallet_id", "wallet_scores", ["wallet_id"])

    # ── audit_logs ────────────────────────────────────────
    op.create_table(
        "audit_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=False),
        sa.Column("resource_id", sa.String(100), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("details", JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("wallet_scores")
    op.drop_table("notification_settings")
    op.drop_table("alerts")
    op.drop_table("on_chain_events")
    op.drop_table("user_tracked_tokens")
    op.drop_table("tokens")
    op.drop_table("user_tracked_wallets")
    op.drop_table("wallets")
    op.drop_table("users")
