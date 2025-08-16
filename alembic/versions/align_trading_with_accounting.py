"""Align trading models with double-entry accounting system

Revision ID: align_trading_with_accounting
Revises: 93c6bb02a0d3
Create Date: 2025-08-15 19:42:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'align_trading_with_accounting'
down_revision: Union[str, None] = '93c6bb02a0d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Align trading system with double-entry accounting"""
    
    # Add journal_entry_id to trades table to link trades with accounting entries
    op.add_column('trades', sa.Column('journal_entry_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_trades_journal_entry_id', 
        'trades', 'journal_entries',
        ['journal_entry_id'], ['id']
    )
    
    # Create index for efficient lookups
    op.create_index('ix_trades_journal_entry_id', 'trades', ['journal_entry_id'])
    
    # Add accounting metadata to trades for audit trail
    op.add_column('trades', sa.Column('accounting_processed', sa.Boolean(), default=False))
    op.add_column('trades', sa.Column('accounting_processed_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Remove trading-accounting alignment"""
    
    # Remove foreign key and columns
    op.drop_constraint('fk_trades_journal_entry_id', 'trades', type_='foreignkey')
    op.drop_index('ix_trades_journal_entry_id', 'trades')
    op.drop_column('trades', 'journal_entry_id')
    op.drop_column('trades', 'accounting_processed')
    op.drop_column('trades', 'accounting_processed_at')
