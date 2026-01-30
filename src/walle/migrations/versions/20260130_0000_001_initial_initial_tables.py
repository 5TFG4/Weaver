"""
Initial migration: outbox and consumer_offsets tables

Revision ID: 001
Revises: None
Create Date: 2026-01-30

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create outbox table for event sourcing
    op.create_table(
        "outbox",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("type", sa.String(length=100), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_outbox_type", "outbox", ["type"], unique=False)
    op.create_index("ix_outbox_created_at", "outbox", ["created_at"], unique=False)
    op.create_index("idx_outbox_type_created", "outbox", ["type", "created_at"], unique=False)

    # Create consumer_offsets table for at-least-once delivery
    op.create_table(
        "consumer_offsets",
        sa.Column("consumer_id", sa.String(length=100), nullable=False),
        sa.Column("last_offset", sa.BigInteger(), nullable=False, server_default="-1"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("consumer_id"),
    )


def downgrade() -> None:
    op.drop_table("consumer_offsets")
    op.drop_index("idx_outbox_type_created", table_name="outbox")
    op.drop_index("ix_outbox_created_at", table_name="outbox")
    op.drop_index("ix_outbox_type", table_name="outbox")
    op.drop_table("outbox")
