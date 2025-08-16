"""Widen smallest-unit columns to NUMERIC(78, 0)

Revision ID: change_smallest_unit_to_numeric
Revises: fix_amount_bigint
Create Date: 2025-08-09 10:45:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'change_smallest_unit_to_numeric'
down_revision = 'fix_amount_bigint'
branch_labels = None
depends_on = None


def upgrade():
    # Accounts: crypto_balance_smallest_unit -> NUMERIC(78, 0)
    op.alter_column(
        'accounts',
        'crypto_balance_smallest_unit',
        existing_type=sa.BIGINT(),
        type_=sa.Numeric(78, 0),
        existing_nullable=True,
    )

    # Accounts: crypto_locked_amount_smallest_unit -> NUMERIC(78, 0)
    op.alter_column(
        'accounts',
        'crypto_locked_amount_smallest_unit',
        existing_type=sa.BIGINT(),
        type_=sa.Numeric(78, 0),
        existing_nullable=True,
    )

    # Transactions: amount_smallest_unit -> NUMERIC(78, 0)
    op.alter_column(
        'transactions',
        'amount_smallest_unit',
        existing_type=sa.BIGINT(),
        type_=sa.Numeric(78, 0),
        existing_nullable=True,
    )


def downgrade():
    # Revert to BIGINT (may fail if values exceed BIGINT range)
    op.alter_column(
        'transactions',
        'amount_smallest_unit',
        existing_type=sa.Numeric(78, 0),
        type_=sa.BIGINT(),
        existing_nullable=True,
    )

    op.alter_column(
        'accounts',
        'crypto_locked_amount_smallest_unit',
        existing_type=sa.Numeric(78, 0),
        type_=sa.BIGINT(),
        existing_nullable=True,
    )

    op.alter_column(
        'accounts',
        'crypto_balance_smallest_unit',
        existing_type=sa.Numeric(78, 0),
        type_=sa.BIGINT(),
        existing_nullable=True,
    )


