"""Unify amount and balance fields for crypto smallest units and fiat

Revision ID: unify_amount_balance_fields
Revises: align_trading_with_accounting
Create Date: 2025-08-15 19:51:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'unify_amount_balance_fields'
down_revision: Union[str, None] = 'align_trading_with_accounting'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Unify all amount/balance fields to use smallest units with currency precision metadata"""
    
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    
    # 1. Update accounts table to use unified amount fields
    if 'accounts' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('accounts')]
        
        # Add new unified fields
        if 'balance_smallest_unit' not in columns:
            op.add_column('accounts', sa.Column('balance_smallest_unit', sa.Numeric(78, 0), nullable=True, default=0))
        if 'locked_amount_smallest_unit' not in columns:
            op.add_column('accounts', sa.Column('locked_amount_smallest_unit', sa.Numeric(78, 0), nullable=True, default=0))
        
        # Migrate existing data from old balance fields
        bind.execute(sa.text("""
            UPDATE accounts 
            SET balance_smallest_unit = COALESCE(
                CASE 
                    WHEN crypto_balance_smallest_unit IS NOT NULL THEN crypto_balance_smallest_unit
                    ELSE (balance * 100)::NUMERIC(78,0)  -- Convert fiat to cents
                END, 0
            ),
            locked_amount_smallest_unit = COALESCE(
                CASE 
                    WHEN crypto_locked_amount_smallest_unit IS NOT NULL THEN crypto_locked_amount_smallest_unit
                    ELSE (locked_amount * 100)::NUMERIC(78,0)  -- Convert fiat to cents
                END, 0
            )
            WHERE balance_smallest_unit IS NULL OR locked_amount_smallest_unit IS NULL
        """))
        
        # Make fields non-nullable after migration
        op.alter_column('accounts', 'balance_smallest_unit', nullable=False)
        op.alter_column('accounts', 'locked_amount_smallest_unit', nullable=False)
        
        # Create indexes for performance
        op.create_index('ix_accounts_balance_smallest_unit', 'accounts', ['balance_smallest_unit'])
        op.create_index('ix_accounts_locked_amount_smallest_unit', 'accounts', ['locked_amount_smallest_unit'])
    
    # 2. Update transactions table
    if 'transactions' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('transactions')]
        
        if 'amount_smallest_unit' not in columns:
            op.add_column('transactions', sa.Column('amount_smallest_unit', sa.Numeric(78, 0), nullable=True))
        if 'fee_amount_smallest_unit' not in columns:
            op.add_column('transactions', sa.Column('fee_amount_smallest_unit', sa.Numeric(78, 0), nullable=True))
        
        # Migrate existing transaction amounts
        bind.execute(sa.text("""
            UPDATE transactions 
            SET amount_smallest_unit = COALESCE(
                amount_smallest_unit,
                (amount * 100)::NUMERIC(78,0)  -- Default to cents for fiat
            ),
            fee_amount_smallest_unit = COALESCE(
                fee_amount_smallest_unit,
                (COALESCE(fee_amount, 0) * 100)::NUMERIC(78,0)
            )
            WHERE amount_smallest_unit IS NULL
        """))
        
        op.alter_column('transactions', 'amount_smallest_unit', nullable=False)
        op.create_index('ix_transactions_amount_smallest_unit', 'transactions', ['amount_smallest_unit'])
    
    # 3. Update trades table
    if 'trades' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('trades')]
        
        if 'crypto_amount_smallest_unit' not in columns:
            op.add_column('trades', sa.Column('crypto_amount_smallest_unit', sa.Numeric(78, 0), nullable=True))
        if 'fiat_amount_smallest_unit' not in columns:
            op.add_column('trades', sa.Column('fiat_amount_smallest_unit', sa.Numeric(78, 0), nullable=True))
        if 'fee_amount_smallest_unit' not in columns:
            op.add_column('trades', sa.Column('fee_amount_smallest_unit', sa.Numeric(78, 0), nullable=True))
        
        # Migrate existing trade amounts (will need currency-specific conversion in production)
        bind.execute(sa.text("""
            UPDATE trades 
            SET crypto_amount_smallest_unit = COALESCE(
                crypto_amount_smallest_unit,
                (crypto_amount * 100000000)::NUMERIC(78,0)  -- Default to satoshis (8 decimals)
            ),
            fiat_amount_smallest_unit = COALESCE(
                fiat_amount_smallest_unit,
                (fiat_amount * 100)::NUMERIC(78,0)  -- Convert to cents
            ),
            fee_amount_smallest_unit = COALESCE(
                fee_amount_smallest_unit,
                (fee_amount * 100)::NUMERIC(78,0)  -- Convert to cents
            )
            WHERE crypto_amount_smallest_unit IS NULL
        """))
    
    # 4. Update accounting ledger to use smallest units
    if 'ledger_transactions' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('ledger_transactions')]
        
        if 'debit_smallest_unit' not in columns:
            op.add_column('ledger_transactions', sa.Column('debit_smallest_unit', sa.Numeric(78, 0), nullable=True))
        if 'credit_smallest_unit' not in columns:
            op.add_column('ledger_transactions', sa.Column('credit_smallest_unit', sa.Numeric(78, 0), nullable=True))
        
        # Migrate existing ledger amounts
        bind.execute(sa.text("""
            UPDATE ledger_transactions 
            SET debit_smallest_unit = COALESCE(
                debit_smallest_unit,
                (debit * 100)::NUMERIC(78,0)  -- Default to cents
            ),
            credit_smallest_unit = COALESCE(
                credit_smallest_unit,
                (credit * 100)::NUMERIC(78,0)  -- Default to cents
            )
            WHERE debit_smallest_unit IS NULL
        """))
        
        op.alter_column('ledger_transactions', 'debit_smallest_unit', nullable=False)
        op.alter_column('ledger_transactions', 'credit_smallest_unit', nullable=False)
    
    # 5. Update chart_of_accounts balance field
    if 'chart_of_accounts' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('chart_of_accounts')]
        
        if 'balance_smallest_unit' not in columns:
            op.add_column('chart_of_accounts', sa.Column('balance_smallest_unit', sa.Numeric(78, 0), nullable=True, default=0))
        
        # Migrate existing balances
        bind.execute(sa.text("""
            UPDATE chart_of_accounts 
            SET balance_smallest_unit = COALESCE(
                balance_smallest_unit,
                (balance * 100)::NUMERIC(78,0)  -- Default to cents
            )
            WHERE balance_smallest_unit IS NULL
        """))
        
        op.alter_column('chart_of_accounts', 'balance_smallest_unit', nullable=False)
        op.create_index('ix_chart_of_accounts_balance_smallest_unit', 'chart_of_accounts', ['balance_smallest_unit'])
    
    # 6. Add currency precision metadata to currencies table
    if 'currencies' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('currencies')]
        
        if 'smallest_unit_name' not in columns:
            op.add_column('currencies', sa.Column('smallest_unit_name', sa.String(50), nullable=True))
        if 'smallest_unit_per_base' not in columns:
            op.add_column('currencies', sa.Column('smallest_unit_per_base', sa.BigInteger(), nullable=True))
        if 'display_decimals' not in columns:
            op.add_column('currencies', sa.Column('display_decimals', sa.Integer(), nullable=True))
        
        # Populate currency precision data
        currency_data = [
            ('BTC', 'satoshis', 100000000, 8),
            ('ETH', 'wei', 10**18, 18),
            ('SOL', 'lamports', 10**9, 9),
            ('TRX', 'sun', 10**6, 6),
            ('BNB', 'wei', 10**18, 18),
            ('USD', 'cents', 100, 2),
            ('UGX', 'cents', 100, 0),
        ]
        
        for code, unit_name, unit_per_base, decimals in currency_data:
            bind.execute(sa.text("""
                UPDATE currencies 
                SET smallest_unit_name = :unit_name,
                    smallest_unit_per_base = :unit_per_base,
                    display_decimals = :decimals
                WHERE code = :code
            """), {
                'code': code,
                'unit_name': unit_name,
                'unit_per_base': unit_per_base,
                'decimals': decimals
            })


def downgrade() -> None:
    """Remove unified amount fields and revert to old structure"""
    
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    
    # Remove new fields from all tables
    tables_and_columns = [
        ('accounts', ['balance_smallest_unit', 'locked_amount_smallest_unit']),
        ('transactions', ['amount_smallest_unit', 'fee_amount_smallest_unit']),
        ('trades', ['crypto_amount_smallest_unit', 'fiat_amount_smallest_unit', 'fee_amount_smallest_unit']),
        ('ledger_transactions', ['debit_smallest_unit', 'credit_smallest_unit']),
        ('chart_of_accounts', ['balance_smallest_unit']),
        ('currencies', ['smallest_unit_name', 'smallest_unit_per_base', 'display_decimals'])
    ]
    
    for table_name, columns in tables_and_columns:
        if table_name in inspector.get_table_names():
            existing_columns = [col['name'] for col in inspector.get_columns(table_name)]
            for column in columns:
                if column in existing_columns:
                    op.drop_column(table_name, column)
    
    # Drop indexes
    indexes_to_drop = [
        ('accounts', 'ix_accounts_balance_smallest_unit'),
        ('accounts', 'ix_accounts_locked_amount_smallest_unit'),
        ('transactions', 'ix_transactions_amount_smallest_unit'),
        ('chart_of_accounts', 'ix_chart_of_accounts_balance_smallest_unit')
    ]
    
    for table_name, index_name in indexes_to_drop:
        if table_name in inspector.get_table_names():
            try:
                op.drop_index(index_name, table_name)
            except:
                pass  # Index might not exist
