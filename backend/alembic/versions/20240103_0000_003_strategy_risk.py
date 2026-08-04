"""strategy and risk management tables

Revision ID: 003
Revises: 002
Create Date: 2024-01-03 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "risk_profiles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "portfolio_id",
            UUID(as_uuid=True),
            sa.ForeignKey("paper_portfolios.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("stop_loss_pct", sa.Numeric(6, 2), nullable=False, server_default="10.0"),
        sa.Column("take_profit_pct", sa.Numeric(6, 2), nullable=False, server_default="50.0"),
        sa.Column("max_position_pct", sa.Numeric(6, 2), nullable=False, server_default="25.0"),
        sa.Column("max_drawdown_pct", sa.Numeric(6, 2), nullable=False, server_default="30.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_risk_profiles_portfolio_id", "risk_profiles", ["portfolio_id"])

    op.create_table(
        "strategies",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "portfolio_id",
            UUID(as_uuid=True),
            sa.ForeignKey("paper_portfolios.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("token_contract", sa.String(42), nullable=False),
        sa.Column("token_symbol", sa.String(20), nullable=False),
        sa.Column("chain", sa.String(30), nullable=False, server_default="ethereum"),
        sa.Column("signal_direction", sa.String(10), nullable=False),
        sa.Column("min_confidence", sa.Numeric(4, 2), nullable=False, server_default="0.60"),
        sa.Column("action", sa.String(10), nullable=False),
        sa.Column("size_pct", sa.Numeric(5, 2), nullable=False, server_default="10.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_strategies_portfolio_id", "strategies", ["portfolio_id"])
    op.create_index("ix_strategies_is_active", "strategies", ["is_active"])

    op.create_table(
        "strategy_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "strategy_id",
            UUID(as_uuid=True),
            sa.ForeignKey("strategies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("triggered", sa.Boolean(), nullable=False),
        sa.Column("signal_direction", sa.String(10), nullable=True),
        sa.Column("signal_confidence", sa.Numeric(4, 2), nullable=True),
        sa.Column(
            "trade_id",
            UUID(as_uuid=True),
            sa.ForeignKey("paper_trades.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("reason", sa.String(200), nullable=True),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_strategy_runs_strategy_id", "strategy_runs", ["strategy_id"])
    op.create_index("ix_strategy_runs_evaluated_at", "strategy_runs", ["evaluated_at"])


def downgrade() -> None:
    op.drop_table("strategy_runs")
    op.drop_table("strategies")
    op.drop_table("risk_profiles")
