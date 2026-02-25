"""Add runs and fills tables for persistence and audit trail

Revision ID: d4e5f6a7b8c9
Revises: c3b4a5d6e7f8
Create Date: 2026-02-25 10:00:00.000000

D-2: Runs table for restart recovery.
D-3: Fills table for audit trail.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c3b4a5d6e7f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Runs table (D-2) ---
    op.create_table(
        "runs",
        sa.Column("id", sa.String(100), nullable=False),
        sa.Column("strategy_id", sa.String(100), nullable=False),
        sa.Column("mode", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("symbols", JSONB, nullable=True),
        sa.Column("timeframe", sa.String(20), nullable=True),
        sa.Column("config", JSONB, nullable=True),
        sa.Column("error", sa.String(2000), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stopped_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_runs_status_created", "runs", ["status", "created_at"])

    # --- Fills table (D-3) ---
    op.create_table(
        "fills",
        sa.Column("id", sa.String(100), nullable=False),
        sa.Column("order_id", sa.String(100), nullable=False),
        sa.Column("price", sa.Numeric(18, 8), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 8), nullable=False),
        sa.Column("side", sa.String(10), nullable=False),
        sa.Column("filled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("exchange_fill_id", sa.String(100), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_fills_order_id", "fills", ["order_id"])
    op.create_index("idx_fills_order_filled", "fills", ["order_id", "filled_at"])


def downgrade() -> None:
    op.drop_index("idx_fills_order_filled", table_name="fills")
    op.drop_index("ix_fills_order_id", table_name="fills")
    op.drop_table("fills")

    op.drop_index("idx_runs_status_created", table_name="runs")
    op.drop_table("runs")
