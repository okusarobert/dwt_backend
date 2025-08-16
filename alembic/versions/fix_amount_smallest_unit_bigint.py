"""Fix amount_smallest_unit to BigInteger

Revision ID: fix_amount_bigint
Revises: tx_amount_smallest_unit
Create Date: 2025-08-07 23:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fix_amount_bigint'
down_revision = 'tx_amount_smallest_unit'
branch_labels = None
depends_on = None


def upgrade():
    """Change amount_smallest_unit from Integer to Numeric"""
    # Change amount_smallest_unit field from INTEGER to NUMERIC
    op.alter_column('transactions', 'amount_smallest_unit',
                    existing_type=sa.INTEGER(),
                    type_=sa.Numeric(precision=78, scale=0),
                    existing_nullable=True)
    
    # Also fix the account fields
    op.alter_column('accounts', 'crypto_balance_smallest_unit',
                    existing_type=sa.INTEGER(),
                    type_=sa.Numeric(precision=78, scale=0),
                    existing_nullable=True)
    
    op.alter_column('accounts', 'crypto_locked_amount_smallest_unit',
                    existing_type=sa.INTEGER(),
                    type_=sa.Numeric(precision=78, scale=0),
                    existing_nullable=True)


def downgrade():
    """Change amount_smallest_unit back to Integer"""
    # Change amount_smallest_unit field back to INTEGER
    op.alter_column('transactions', 'amount_smallest_unit',
                    existing_type=sa.Numeric(precision=78, scale=0),
                    type_=sa.INTEGER(),
                    existing_nullable=True)
    
    # Also revert the account fields
    op.alter_column('accounts', 'crypto_balance_smallest_unit',
                    existing_type=sa.Numeric(precision=78, scale=0),
                    type_=sa.INTEGER(),
                    existing_nullable=True)
    
    op.alter_column('accounts', 'crypto_locked_amount_smallest_unit',
                    existing_type=sa.Numeric(precision=78, scale=0),
                    type_=sa.INTEGER(),
                    existing_nullable=True) 