"""Drop redundant fills(order_id) index

Revision ID: e7f8a9b0c1d2
Revises: d4e5f6a7b8c9
Create Date: 2026-03-02 12:00:00.000000

Cleanup migration for environments that already ran the original
runs/fills migration with the redundant single-column index.
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "e7f8a9b0c1d2"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_fills_order_id")


def downgrade() -> None:
    op.create_index("ix_fills_order_id", "fills", ["order_id"])
