"""Add ledger and portfolio models

Revision ID: add_ledger_portfolio_models
Revises: 3c622e3a660d
Create Date: 2024-12-19 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_ledger_portfolio_models'
down_revision = '3c622e3a660d'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if 'ledger_entries' not in tables:
        op.create_table('ledger_entries',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('transaction_id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('account_id', sa.Integer(), nullable=False),
            sa.Column('amount', sa.Numeric(precision=20, scale=8), nullable=False),
            sa.Column('amount_smallest_unit', sa.Numeric(precision=78, scale=0), nullable=True),
            sa.Column('currency', sa.String(length=16), nullable=False),
            sa.Column('entry_type', sa.String(length=32), nullable=False),
            sa.Column('transaction_type', sa.String(length=32), nullable=False),
            sa.Column('balance_before', sa.Numeric(precision=20, scale=8), nullable=False),
            sa.Column('balance_after', sa.Numeric(precision=20, scale=8), nullable=False),
            sa.Column('price_usd', sa.Numeric(precision=20, scale=8), nullable=True),
            sa.Column('price_timestamp', sa.DateTime(), nullable=True),
            sa.Column('description', sa.String(length=255), nullable=True),
            sa.Column('reference_id', sa.String(length=64), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ),
            sa.ForeignKeyConstraint(['transaction_id'], ['transactions.id'], ),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )

    ledger_indexes = [idx['name'] for idx in inspector.get_indexes('ledger_entries')]
    if 'idx_ledger_user_currency_created' not in ledger_indexes:
        op.create_index('idx_ledger_user_currency_created', 'ledger_entries', ['user_id', 'currency', 'created_at'], unique=False)
    if 'idx_ledger_transaction_type' not in ledger_indexes:
        op.create_index('idx_ledger_transaction_type', 'ledger_entries', ['transaction_type', 'created_at'], unique=False)
    if 'ix_ledger_entries_id' not in ledger_indexes:
        op.create_index(op.f('ix_ledger_entries_id'), 'ledger_entries', ['id'], unique=False)
    if 'ix_ledger_entries_transaction_id' not in ledger_indexes:
        op.create_index(op.f('ix_ledger_entries_transaction_id'), 'ledger_entries', ['transaction_id'], unique=False)
    if 'ix_ledger_entries_user_id' not in ledger_indexes:
        op.create_index(op.f('ix_ledger_entries_user_id'), 'ledger_entries', ['user_id'], unique=False)
    if 'ix_ledger_entries_account_id' not in ledger_indexes:
        op.create_index(op.f('ix_ledger_entries_account_id'), 'ledger_entries', ['account_id'], unique=False)
    if 'ix_ledger_entries_currency' not in ledger_indexes:
        op.create_index(op.f('ix_ledger_entries_currency'), 'ledger_entries', ['currency'], unique=False)
    if 'ix_ledger_entries_reference_id' not in ledger_indexes:
        op.create_index(op.f('ix_ledger_entries_reference_id'), 'ledger_entries', ['reference_id'], unique=False)

    if 'portfolio_snapshots' not in tables:
        op.create_table('portfolio_snapshots',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('snapshot_type', sa.String(length=16), nullable=False),
            sa.Column('snapshot_date', sa.DateTime(), nullable=False),
            sa.Column('total_value_usd', sa.Numeric(precision=20, scale=2), nullable=False),
            sa.Column('total_change_24h', sa.Numeric(precision=20, scale=2), nullable=True),
            sa.Column('total_change_7d', sa.Numeric(precision=20, scale=2), nullable=True),
            sa.Column('total_change_30d', sa.Numeric(precision=20, scale=2), nullable=True),
            sa.Column('change_percent_24h', sa.Numeric(precision=10, scale=4), nullable=True),
            sa.Column('change_percent_7d', sa.Numeric(precision=10, scale=4), nullable=True),
            sa.Column('change_percent_30d', sa.Numeric(precision=10, scale=4), nullable=True),
            sa.Column('currency_count', sa.Integer(), nullable=False),
            sa.Column('asset_details', postgresql.JSON(astext_type=sa.Text()), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
    
    portfolio_constraints = [c['name'] for c in inspector.get_unique_constraints('portfolio_snapshots')]
    if 'uq_portfolio_snapshot' not in portfolio_constraints:
        op.create_unique_constraint('uq_portfolio_snapshot', 'portfolio_snapshots', ['user_id', 'snapshot_type', 'snapshot_date'])
    
    portfolio_indexes = [idx['name'] for idx in inspector.get_indexes('portfolio_snapshots')]
    if 'idx_portfolio_user_type_date' not in portfolio_indexes:
        op.create_index('idx_portfolio_user_type_date', 'portfolio_snapshots', ['user_id', 'snapshot_type', 'snapshot_date'], unique=False)
    if 'ix_portfolio_snapshots_id' not in portfolio_indexes:
        op.create_index(op.f('ix_portfolio_snapshots_id'), 'portfolio_snapshots', ['id'], unique=False)
    if 'ix_portfolio_snapshots_user_id' not in portfolio_indexes:
        op.create_index(op.f('ix_portfolio_snapshots_user_id'), 'portfolio_snapshots', ['user_id'], unique=False)
    if 'ix_portfolio_snapshots_snapshot_date' not in portfolio_indexes:
        op.create_index(op.f('ix_portfolio_snapshots_snapshot_date'), 'portfolio_snapshots', ['snapshot_date'], unique=False)

    if 'crypto_price_history' not in tables:
        op.create_table('crypto_price_history',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('currency', sa.String(length=16), nullable=False),
            sa.Column('price_usd', sa.Numeric(precision=20, scale=8), nullable=False),
            sa.Column('source', sa.String(length=32), nullable=False),
            sa.Column('price_timestamp', sa.DateTime(), nullable=False),
            sa.Column('volume_24h', sa.Numeric(precision=20, scale=2), nullable=True),
            sa.Column('market_cap', sa.Numeric(precision=20, scale=2), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint('id')
        )
    
    price_history_indexes = [idx['name'] for idx in inspector.get_indexes('crypto_price_history')]
    if 'idx_price_currency_timestamp' not in price_history_indexes:
        op.create_index('idx_price_currency_timestamp', 'crypto_price_history', ['currency', 'price_timestamp'], unique=False)
    if 'idx_price_timestamp' not in price_history_indexes:
        op.create_index('idx_price_timestamp', 'crypto_price_history', ['price_timestamp'], unique=False)
    if 'ix_crypto_price_history_id' not in price_history_indexes:
        op.create_index(op.f('ix_crypto_price_history_id'), 'crypto_price_history', ['id'], unique=False)
    if 'ix_crypto_price_history_currency' not in price_history_indexes:
        op.create_index(op.f('ix_crypto_price_history_currency'), 'crypto_price_history', ['currency'], unique=False)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if 'crypto_price_history' in tables:
        op.drop_table('crypto_price_history')
    
    if 'portfolio_snapshots' in tables:
        op.drop_table('portfolio_snapshots')
        
    if 'ledger_entries' in tables:
        op.drop_table('ledger_entries')
