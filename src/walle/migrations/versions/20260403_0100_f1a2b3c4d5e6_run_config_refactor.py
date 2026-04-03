"""Move symbols/timeframe into config JSONB, drop redundant columns

Revision ID: f1a2b3c4d5e6
Revises: e7f8a9b0c1d2
Create Date: 2026-04-03 01:00:00.000000

Phase 1 of M12 spec alignment:
- Migrate symbols/timeframe values into the config JSONB column
- Drop the standalone symbols and timeframe columns
- Make config NOT NULL (default to empty object for legacy rows)
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e6"
down_revision: str | None = "e7f8a9b0c1d2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Ensure every row has a config value (backfill NULLs with {})
    op.execute("UPDATE runs SET config = '{}' WHERE config IS NULL")

    # 2. Merge symbols into config where config lacks a "symbols" key
    op.execute(
        """
        UPDATE runs
        SET config = jsonb_set(config, '{symbols}', symbols)
        WHERE symbols IS NOT NULL
          AND NOT config ? 'symbols'
        """
    )

    # 3. Merge timeframe into config where config lacks a "timeframe" key
    op.execute(
        """
        UPDATE runs
        SET config = jsonb_set(config, '{timeframe}', to_jsonb(timeframe))
        WHERE timeframe IS NOT NULL
          AND NOT config ? 'timeframe'
        """
    )

    # 4. Drop the redundant columns
    op.drop_column("runs", "symbols")
    op.drop_column("runs", "timeframe")

    # 5. Make config NOT NULL
    op.alter_column("runs", "config", nullable=False)


def downgrade() -> None:
    # 1. Make config nullable again
    op.alter_column("runs", "config", nullable=True)

    # 2. Re-add columns
    op.add_column("runs", sa.Column("timeframe", sa.String(20), nullable=True))
    op.add_column("runs", sa.Column("symbols", JSONB, nullable=True))

    # 3. Extract values back from config
    op.execute(
        """
        UPDATE runs
        SET symbols = config->'symbols'
        WHERE config ? 'symbols'
        """
    )
    op.execute(
        """
        UPDATE runs
        SET timeframe = config->>'timeframe'
        WHERE config ? 'timeframe'
        """
    )
