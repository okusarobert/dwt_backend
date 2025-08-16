"""add trading models

Revision ID: add_trading_models
Revises: 3d91640ec9e0
Create Date: 2025-08-13 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_trading_models'
down_revision: Union[str, None] = '23e791c49f3a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    # Enum types creation
    enum_types = {
        'paymentmethod': "('mobile_money', 'bank_deposit', 'voucher')",
        'paymentprovider': "('relworx', 'stripe', 'paypal', 'voucher')",
        'vouchertype': "('ugx', 'usd')",
        'voucherstatus': "('active', 'used', 'expired')",
        'tradetype': "('buy', 'sell')",
        'tradestatus': "('pending', 'payment_pending', 'processing', 'completed', 'failed', 'cancelled')"
    }
    for name, values in enum_types.items():
        res = bind.execute(sa.text(f"SELECT 1 FROM pg_type WHERE typname = '{name}'")).scalar()
        if not res:
            op.execute(f"CREATE TYPE {name} AS ENUM {values}")

    # Add new values to existing enum types
    def add_enum_value(type_name, value):
        res = bind.execute(sa.text(f"SELECT 1 FROM pg_enum WHERE enumlabel = '{value}' AND enumtypid = (SELECT oid FROM pg_type WHERE typname = '{type_name}')")).scalar()
        if not res:
            op.execute(f"ALTER TYPE {type_name} ADD VALUE '{value}'")

    add_enum_value('transactiontype', 'BUY_CRYPTO')
    add_enum_value('transactiontype', 'SELL_CRYPTO')
    add_enum_value('transactionstatus', 'PROCESSING')
    add_enum_value('transactionstatus', 'CANCELLED')

    # Vouchers table
    if 'vouchers' not in tables:
        op.create_table('vouchers',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('code', sa.String(length=50), nullable=False),
            sa.Column('voucher_type', postgresql.ENUM('ugx', 'usd', name='vouchertype', create_type=False), nullable=False),
            sa.Column('amount', sa.Numeric(precision=15, scale=2), nullable=False),
            sa.Column('status', postgresql.ENUM('active', 'used', 'expired', name='voucherstatus', create_type=False), nullable=False),
            sa.Column('used_by', sa.Integer(), nullable=True),
            sa.Column('used_at', sa.DateTime(), nullable=True),
            sa.Column('expires_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['used_by'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('code')
        )
        op.create_index(op.f('ix_vouchers_code'), 'vouchers', ['code'], unique=True)
        op.create_index(op.f('ix_vouchers_status'), 'vouchers', ['status'], unique=False)

    # Trades table
    if 'trades' not in tables:
        op.create_table('trades',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('trade_type', postgresql.ENUM('buy', 'sell', name='tradetype', create_type=False), nullable=False),
            sa.Column('status', postgresql.ENUM('pending', 'payment_pending', 'processing', 'completed', 'failed', 'cancelled', name='tradestatus', create_type=False), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('account_id', sa.Integer(), nullable=False),
            sa.Column('crypto_currency', sa.String(length=10), nullable=False),
            sa.Column('crypto_amount', sa.Numeric(precision=20, scale=8), nullable=False),
            sa.Column('fiat_currency', sa.String(length=10), nullable=False),
            sa.Column('fiat_amount', sa.Numeric(precision=15, scale=2), nullable=False),
            sa.Column('exchange_rate', sa.Numeric(precision=20, scale=8), nullable=False),
            sa.Column('fee_amount', sa.Numeric(precision=15, scale=2), nullable=False),
            sa.Column('fee_currency', sa.String(length=10), nullable=False),
            sa.Column('payment_method', postgresql.ENUM('mobile_money', 'bank_deposit', 'voucher', name='paymentmethod', create_type=False), nullable=False),
            sa.Column('payment_provider', postgresql.ENUM('relworx', 'stripe', 'paypal', 'voucher', name='paymentprovider', create_type=False), nullable=False),
            sa.Column('payment_reference', sa.String(length=255), nullable=True),
            sa.Column('payment_status', sa.String(length=50), nullable=True),
            sa.Column('phone_number', sa.String(length=20), nullable=True),
            sa.Column('voucher_id', sa.Integer(), nullable=True),
            sa.Column('crypto_transaction_id', sa.Integer(), nullable=True),
            sa.Column('fiat_transaction_id', sa.Integer(), nullable=True),
            sa.Column('description', sa.String(length=255), nullable=True),
            sa.Column('trade_metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
            sa.Column('completed_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ),
            sa.ForeignKeyConstraint(['crypto_transaction_id'], ['transactions.id'], ),
            sa.ForeignKeyConstraint(['fiat_transaction_id'], ['transactions.id'], ),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.ForeignKeyConstraint(['voucher_id'], ['vouchers.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('idx_trade_user_status'), 'trades', ['user_id', 'status'], unique=False)
        op.create_index(op.f('idx_trade_status'), 'trades', ['status'], unique=False)
        op.create_index(op.f('idx_trade_payment_reference'), 'trades', ['payment_reference'], unique=False)

    # Add trade_id column to transactions table
    columns = [col['name'] for col in inspector.get_columns('transactions')]
    if 'trade_id' not in columns:
        op.add_column('transactions', sa.Column('trade_id', sa.Integer(), nullable=True))
    
    fks = [fk['name'] for fk in inspector.get_foreign_keys('transactions')]
    if 'fk_transactions_trade_id_trades' not in fks:
        op.create_foreign_key('fk_transactions_trade_id_trades', 'transactions', 'trades', ['trade_id'], ['id'])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    # Remove trade_id column from transactions
    if 'transactions' in tables:
        fks = [fk['name'] for fk in inspector.get_foreign_keys('transactions')]
        if 'fk_transactions_trade_id_trades' in fks:
            op.drop_constraint('fk_transactions_trade_id_trades', 'transactions', type_='foreignkey')
        columns = [col['name'] for col in inspector.get_columns('transactions')]
        if 'trade_id' in columns:
            op.drop_column('transactions', 'trade_id')
    
    # Drop tables
    if 'trades' in tables:
        op.drop_table('trades')
    if 'vouchers' in tables:
        op.drop_table('vouchers')
    
    # Drop enum types
    enum_types = ['tradestatus', 'tradetype', 'voucherstatus', 'vouchertype', 'paymentprovider', 'paymentmethod']
    for name in enum_types:
        res = bind.execute(sa.text(f"SELECT 1 FROM pg_type WHERE typname = '{name}'")).scalar()
        if res:
            op.execute(f"DROP TYPE {name}")
