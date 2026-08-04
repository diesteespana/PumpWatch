"""paper trading tables

Revision ID: 002
Revises: 001
Create Date: 2024-01-02 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "paper_portfolios",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("starting_balance", sa.Numeric(20, 4), nullable=False),
        sa.Column("current_cash", sa.Numeric(20, 4), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_paper_portfolios_user_id", "paper_portfolios", ["user_id"])

    op.create_table(
        "paper_positions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("portfolio_id", UUID(as_uuid=True), sa.ForeignKey("paper_portfolios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_symbol", sa.String(20), nullable=False),
        sa.Column("token_contract", sa.String(42), nullable=False),
        sa.Column("chain", sa.String(30), nullable=False, server_default="ethereum"),
        sa.Column("quantity", sa.Numeric(28, 10), nullable=False),
        sa.Column("avg_entry_price", sa.Numeric(20, 6), nullable=False),
        sa.UniqueConstraint("portfolio_id", "token_contract", "chain", name="uq_position_portfolio_token_chain"),
    )
    op.create_index("ix_paper_positions_portfolio_id", "paper_positions", ["portfolio_id"])

    op.create_table(
        "paper_trades",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("portfolio_id", UUID(as_uuid=True), sa.ForeignKey("paper_portfolios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("trade_type", sa.String(10), nullable=False),
        sa.Column("token_symbol", sa.String(20), nullable=False),
        sa.Column("token_contract", sa.String(42), nullable=False),
        sa.Column("chain", sa.String(30), nullable=False, server_default="ethereum"),
        sa.Column("quantity", sa.Numeric(28, 10), nullable=False),
        sa.Column("price_at_execution", sa.Numeric(20, 6), nullable=False),
        sa.Column("total_value", sa.Numeric(20, 4), nullable=False),
        sa.Column("realized_pnl", sa.Numeric(20, 4), nullable=True),
        sa.Column("trigger", sa.String(20), nullable=False, server_default="manual"),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_paper_trades_portfolio_id", "paper_trades", ["portfolio_id"])
    op.create_index("ix_paper_trades_executed_at", "paper_trades", ["executed_at"])


def downgrade() -> None:
    op.drop_table("paper_trades")
    op.drop_table("paper_positions")
    op.drop_table("paper_portfolios")
