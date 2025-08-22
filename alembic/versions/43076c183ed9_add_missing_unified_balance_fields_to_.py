"""Add missing unified balance fields to accounts table

Revision ID: 43076c183ed9
Revises: unify_amount_balance_fields
Create Date: 2025-08-16 12:14:50.717602

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '43076c183ed9'
down_revision: Union[str, None] = 'unify_amount_balance_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if columns exist before adding them
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [col['name'] for col in inspector.get_columns('accounts')]
    
    # Add missing unified balance fields to accounts table
    if 'balance_smallest_unit' not in columns:
        op.add_column('accounts', sa.Column('balance_smallest_unit', sa.Numeric(78, 0), nullable=False, default=0))
        op.create_index('ix_accounts_balance_smallest_unit', 'accounts', ['balance_smallest_unit'])
    
    if 'locked_amount_smallest_unit' not in columns:
        op.add_column('accounts', sa.Column('locked_amount_smallest_unit', sa.Numeric(78, 0), nullable=False, default=0))
        op.create_index('ix_accounts_locked_amount_smallest_unit', 'accounts', ['locked_amount_smallest_unit'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_accounts_balance_smallest_unit', 'accounts')
    op.drop_index('ix_accounts_locked_amount_smallest_unit', 'accounts')
    
    # Drop columns
    op.drop_column('accounts', 'balance_smallest_unit')
    op.drop_column('accounts', 'locked_amount_smallest_unit')
