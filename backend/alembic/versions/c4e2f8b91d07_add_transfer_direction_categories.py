"""Add transfer_in / transfer_out categories for directional transfer tracking.

Previously all transfers (incoming from others, outgoing to others, and
inter-account moves) shared a single 'transfers' category, causing them to be
mis-counted as income or spending in analytics.  This migration:

  1. Extends the categoryname enum with 'transfer_in' and 'transfer_out'.
  2. Inserts rows in the categories table for both.
  3. Migrates existing CREDIT TRANSFERS → transfer_in and
     DEBIT TRANSFERS → transfer_out.

Revision ID: c4e2f8b91d07
Revises: b3f1d8a72c90
Create Date: 2026-03-18
"""
from alembic import op

revision = "c4e2f8b91d07"
down_revision = "b3f1d8a72c90"
branch_labels = None
depends_on = None


def upgrade():
    # ------------------------------------------------------------------
    # 1. Extend the enum (IF NOT EXISTS is safe on PG ≥ 9.3)
    # ------------------------------------------------------------------
    op.execute("ALTER TYPE categoryname ADD VALUE IF NOT EXISTS 'transfer_in'")
    op.execute("ALTER TYPE categoryname ADD VALUE IF NOT EXISTS 'transfer_out'")

    # ------------------------------------------------------------------
    # 2. Insert category rows
    # ------------------------------------------------------------------
    op.execute("""
        INSERT INTO categories (name, display_name, icon)
        VALUES
            ('transfer_in',  'Transfer In',  'arrow-down-left'),
            ('transfer_out', 'Transfer Out', 'arrow-up-right')
        ON CONFLICT (name) DO NOTHING
    """)

    # ------------------------------------------------------------------
    # 3. Migrate existing transactions that were tagged 'transfers':
    #    CREDIT  transfers → transfer_in   (money arriving in your account)
    #    DEBIT   transfers → transfer_out  (money leaving your account)
    # ------------------------------------------------------------------
    op.execute("""
        UPDATE transactions
        SET category_id = (SELECT id FROM categories WHERE name = 'transfer_in')
        WHERE transaction_type = 'credit'
          AND category_id = (SELECT id FROM categories WHERE name = 'transfers')
    """)

    op.execute("""
        UPDATE transactions
        SET category_id = (SELECT id FROM categories WHERE name = 'transfer_out')
        WHERE transaction_type = 'debit'
          AND category_id = (SELECT id FROM categories WHERE name = 'transfers')
    """)


def downgrade():
    # Reverse the data migration
    op.execute("""
        UPDATE transactions
        SET category_id = (SELECT id FROM categories WHERE name = 'transfers')
        WHERE category_id IN (
            SELECT id FROM categories WHERE name IN ('transfer_in', 'transfer_out')
        )
    """)
    # Note: PostgreSQL does not support removing enum values; the enum
    # extension is left in place on downgrade.
    op.execute("DELETE FROM categories WHERE name IN ('transfer_in', 'transfer_out')")
