"""Add backtest_results table

Revision ID: a1b2c3d4e5f6
Revises: f1a2b3c4d5e6
Create Date: 2026-04-05 07:00:00.000000

M13-2: Dedicated table for persisted backtest results.
One-to-one relationship with runs table (run_id is PK).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "f1a2b3c4d5e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "backtest_results",
        sa.Column("run_id", sa.String(100), primary_key=True),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("timeframe", sa.String(10), nullable=False),
        sa.Column("symbols", JSONB, nullable=False),
        sa.Column("final_equity", sa.String(50), nullable=False),
        sa.Column("simulation_duration_ms", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_bars_processed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("stats", JSONB, nullable=False),
        sa.Column("equity_curve", JSONB, nullable=False),
        sa.Column("fills", JSONB, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("backtest_results")
