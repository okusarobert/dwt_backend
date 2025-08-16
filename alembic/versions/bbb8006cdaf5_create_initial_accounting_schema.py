"""Create initial accounting schema

Revision ID: bbb8006cdaf5
Revises: a66240c1c794
Create Date: 2025-08-15 13:27:54.993408

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'bbb8006cdaf5'
down_revision: Union[str, None] = 'add_crypto_smallest_unit_support'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    # Idempotent ENUM creation
    account_type_enum = postgresql.ENUM('ASSET', 'LIABILITY', 'EQUITY', 'INCOME', 'EXPENSE', name='accounttype', create_type=False)
    account_type_enum.create(bind, checkfirst=True)

    if 'chart_of_accounts' not in tables:
        op.create_table('chart_of_accounts',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('name', sa.String(length=255), nullable=False),
            sa.Column('type', account_type_enum, nullable=False),
            sa.Column('currency', sa.String(length=16), nullable=False),
            sa.Column('parent_id', sa.Integer(), nullable=True),
            sa.Column('is_system_account', sa.Boolean(), nullable=False),
            sa.Column('balance', sa.Numeric(precision=20, scale=8), nullable=False, server_default=sa.text('0')),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=True),
            sa.ForeignKeyConstraint(['parent_id'], ['chart_of_accounts.id'], ),
            sa.PrimaryKeyConstraint('id')
        )

    if 'journal_entries' not in tables:
        op.create_table('journal_entries',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('description', sa.String(length=255), nullable=False),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )

    if 'ledger_transactions' not in tables:
        op.create_table('ledger_transactions',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('journal_entry_id', sa.Integer(), nullable=False),
            sa.Column('account_id', sa.Integer(), nullable=False),
            sa.Column('debit', sa.Numeric(precision=20, scale=8), nullable=False),
            sa.Column('credit', sa.Numeric(precision=20, scale=8), nullable=False),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=True),
            sa.ForeignKeyConstraint(['account_id'], ['chart_of_accounts.id'], ),
            sa.ForeignKeyConstraint(['journal_entry_id'], ['journal_entries.id'], ),
            sa.PrimaryKeyConstraint('id')
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if 'ledger_transactions' in tables:
        op.drop_table('ledger_transactions')
    if 'journal_entries' in tables:
        op.drop_table('journal_entries')
    if 'chart_of_accounts' in tables:
        op.drop_table('chart_of_accounts')

    account_type_enum = postgresql.ENUM('ASSET', 'LIABILITY', 'EQUITY', 'INCOME', 'EXPENSE', name='accounttype', create_type=False)
    account_type_enum.drop(bind, checkfirst=True)
