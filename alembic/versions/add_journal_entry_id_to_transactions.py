"""Add journal_entry_id to transactions table

Revision ID: add_journal_entry_id
Revises: 20250809_change_smallest_unit_to_numeric
Create Date: 2025-08-21 16:06:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_journal_entry_id'
down_revision = 'change_smallest_unit_to_numeric'
branch_labels = None
depends_on = None

def upgrade():
    # Add journal_entry_id column to transactions table
    op.add_column('transactions', sa.Column('journal_entry_id', sa.Integer(), nullable=True))
    
    # Add foreign key constraint to journal_entries table
    op.create_foreign_key(
        'fk_transactions_journal_entry_id',
        'transactions', 'journal_entries',
        ['journal_entry_id'], ['id']
    )

def downgrade():
    # Drop foreign key constraint
    op.drop_constraint('fk_transactions_journal_entry_id', 'transactions', type_='foreignkey')
    
    # Drop journal_entry_id column
    op.drop_column('transactions', 'journal_entry_id')
