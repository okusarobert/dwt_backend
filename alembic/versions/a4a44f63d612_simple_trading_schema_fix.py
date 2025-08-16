"""simple_trading_schema_fix

Revision ID: a4a44f63d612
Revises: 1d661194d41e
Create Date: 2025-08-13 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a4a44f63d612'
down_revision: Union[str, None] = '1d661194d41e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add missing trading schema elements"""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()
    
    # Only create trades table if it doesn't exist
    if 'trades' not in tables:
        op.create_table('trades',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint('id')
        )
    
    # Add trade_id column to transactions table if it doesn't exist
    if 'transactions' in tables:
        columns = [col['name'] for col in inspector.get_columns('transactions')]
        if 'trade_id' not in columns:
            op.add_column('transactions', sa.Column('trade_id', sa.Integer(), nullable=True))
        
        # Create foreign key constraint if it doesn't exist
        fks = [fk['name'] for fk in inspector.get_foreign_keys('transactions')]
        if 'fk_transactions_trade_id_trades' not in fks:
            op.create_foreign_key(
                'fk_transactions_trade_id_trades',
                'transactions', 'trades',
                ['trade_id'], ['id']
            )


def downgrade() -> None:
    """Remove added schema elements"""
    # Drop foreign key constraint
    op.drop_constraint('fk_transactions_trade_id_trades', 'transactions', type_='foreignkey')
    
    # Drop trade_id column
    op.drop_column('transactions', 'trade_id')
    
    # Drop trades table
    op.drop_table('trades')
