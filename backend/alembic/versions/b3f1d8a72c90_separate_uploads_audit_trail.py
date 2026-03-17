"""separate uploads audit trail

Revision ID: b3f1d8a72c90
Revises: a9c6ccff1803
Create Date: 2026-03-17 10:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "b3f1d8a72c90"
down_revision: Union[str, None] = "a9c6ccff1803"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add 'credit_card' to statementtype enum
    op.execute("ALTER TYPE statementtype ADD VALUE IF NOT EXISTS 'CREDIT_CARD'")

    # Add 'credit_card_payment' to categoryname enum
    op.execute("ALTER TYPE categoryname ADD VALUE IF NOT EXISTS 'CREDIT_CARD_PAYMENT'")

    # Add audit_log column to statements table
    op.add_column(
        "statements",
        sa.Column("audit_log", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("statements", "audit_log")
    # Note: PostgreSQL does not support removing enum values directly.
    # To fully downgrade, recreate the enum types without these values.
