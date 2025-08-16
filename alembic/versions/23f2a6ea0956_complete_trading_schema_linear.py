"""complete_trading_schema_linear

Revision ID: 23f2a6ea0956
Revises: fb84c1febfb6
Create Date: 2025-08-13 15:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '23f2a6ea0956'
down_revision: Union[str, None] = 'add_trading_models'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Complete trading schema with all necessary elements"""
    # Get database connection and inspector
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    
    # Check if enum types exist, create them if they don't
    existing_types = [t[0] for t in connection.execute(sa.text("SELECT typname FROM pg_type WHERE typtype = 'e'")).fetchall()]
    
    # Create ENUM types if they don't exist
    if 'paymentmethod' not in existing_types:
        op.execute("CREATE TYPE paymentmethod AS ENUM ('mobile_money', 'bank_deposit', 'voucher')")
    
    if 'paymentprovider' not in existing_types:
        op.execute("CREATE TYPE paymentprovider AS ENUM ('relworx', 'stripe', 'paypal', 'voucher')")
    
    if 'vouchertype' not in existing_types:
        op.execute("CREATE TYPE vouchertype AS ENUM ('ugx', 'usd')")
    
    if 'voucherstatus' not in existing_types:
        op.execute("CREATE TYPE voucherstatus AS ENUM ('active', 'used', 'expired')")
    
    if 'tradetype' not in existing_types:
        op.execute("CREATE TYPE tradetype AS ENUM ('buy', 'sell')")
    
    if 'tradestatus' not in existing_types:
        op.execute("CREATE TYPE tradestatus AS ENUM ('pending', 'payment_pending', 'processing', 'completed', 'failed', 'cancelled')")
    
    def add_enum_value(type_name, value):
        res = connection.execute(sa.text(f"SELECT 1 FROM pg_enum WHERE enumlabel = '{value}' AND enumtypid = (SELECT oid FROM pg_type WHERE typname = '{type_name}')")).scalar()
        if not res:
            op.execute(f"ALTER TYPE {type_name} ADD VALUE '{value}'")

    add_enum_value('transactiontype', 'BUY_CRYPTO')
    add_enum_value('transactiontype', 'SELL_CRYPTO')
    add_enum_value('transactionstatus', 'PROCESSING')
    add_enum_value('transactionstatus', 'CANCELLED')
    
    # Check if vouchers table exists, create it if it doesn't
    tables = inspector.get_table_names()
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
    
    # Check if trades table exists, create it if it doesn't
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
    
    # Check if trade_id column exists in transactions table, add it if it doesn't
    columns = [col['name'] for col in inspector.get_columns('transactions')]
    if 'trade_id' not in columns:
        op.add_column('transactions', sa.Column('trade_id', sa.Integer(), nullable=True))
    
    fks = [fk['name'] for fk in inspector.get_foreign_keys('transactions')]
    if 'fk_transactions_trade_id_trades' not in fks:
        op.create_foreign_key(
            'fk_transactions_trade_id_trades',
            'transactions', 'trades',
            ['trade_id'], ['id']
        )


def downgrade() -> None:
    """Remove added schema elements safely"""
    # Get database connection and inspector
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    
    # Remove trade_id column from transactions if it exists
    columns = [col['name'] for col in inspector.get_columns('transactions')]
    if 'trade_id' in columns:
        op.drop_constraint('fk_transactions_trade_id_trades', 'transactions', type_='foreignkey')
        op.drop_column('transactions', 'trade_id')
    
    # Drop trades table if it exists
    tables = inspector.get_table_names()
    if 'trades' in tables:
        op.drop_index(op.f('idx_trade_payment_reference'), table_name='trades')
        op.drop_index(op.f('idx_trade_status'), table_name='trades')
        op.drop_index(op.f('idx_trade_user_status'), table_name='trades')
        op.drop_table('trades')
    
    # Drop vouchers table if it exists
    if 'vouchers' in tables:
        op.drop_index(op.f('ix_vouchers_status'), table_name='vouchers')
        op.drop_index(op.f('ix_vouchers_code'), table_name='vouchers')
        op.drop_table('vouchers')
    
    # Note: We don't drop the enum types as they might be used by other parts of the system
