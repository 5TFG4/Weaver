"""Drop legacy fills(order_id) index if present

Revision ID: e7f8a9b0c1d2
Revises: d4e5f6a7b8c9
Create Date: 2026-03-02 12:00:00.000000

Cleanup migration for legacy environments that may contain an extra
single-column index on fills(order_id).

Important: canonical schema at down_revision (d4e5f6a7b8c9) does not
define ix_fills_order_id, so downgrade is intentionally a no-op.
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
    # Intentionally no-op.
    #
    # Alembic downgrade should return schema to the state defined by
    # down_revision (d4e5f6a7b8c9). That canonical state never included
    # ix_fills_order_id, so re-creating it here would introduce drift.
    return
