"""Add crypto smallest unit support

Revision ID: add_crypto_smallest_unit_support
Revises: # Update this to the previous migration ID
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_crypto_smallest_unit_support'
down_revision = '1d661194d41e'  # Must run after wallet tables are created
depends_on = None


def _table_exists(table_name):
    inspector = inspect(op.get_bind())
    return table_name in inspector.get_table_names()

def _column_exists(table_name, column_name):
    if not _table_exists(table_name):
        return False
    inspector = inspect(op.get_bind())
    columns = [c['name'] for c in inspector.get_columns(table_name)]
    return column_name in columns

def _index_exists(table_name, index_name):
    if not _table_exists(table_name):
        return False
    inspector = inspect(op.get_bind())
    indexes = [i['name'] for i in inspector.get_indexes(table_name)]
    return index_name in indexes

def upgrade():
    """Upgrade database to support crypto smallest units"""
    print("Upgrading database to support crypto smallest units")

    if not _column_exists('accounts', 'crypto_balance_smallest_unit'):
        op.add_column('accounts', sa.Column('crypto_balance_smallest_unit', sa.BigInteger(), nullable=True))

    if not _column_exists('accounts', 'crypto_locked_amount_smallest_unit'):
        op.add_column('accounts', sa.Column('crypto_locked_amount_smallest_unit', sa.BigInteger(), nullable=True))

    if not _column_exists('accounts', 'precision_config'):
        op.add_column('accounts', sa.Column('precision_config', sa.JSON(), nullable=True))

    if not _index_exists('accounts', 'ix_accounts_crypto_balance_smallest_unit'):
        op.create_index('ix_accounts_crypto_balance_smallest_unit', 'accounts', ['crypto_balance_smallest_unit'])

    if not _index_exists('accounts', 'ix_accounts_crypto_locked_amount_smallest_unit'):
        op.create_index('ix_accounts_crypto_locked_amount_smallest_unit', 'accounts', ['crypto_locked_amount_smallest_unit'])

    if not _column_exists('currencies', 'precision_config'):
        op.add_column('currencies', sa.Column('precision_config', sa.JSON(), nullable=True))

    print("Database schema updated for crypto smallest units.")


def downgrade():
    """Downgrade database to remove crypto smallest unit support"""
    
    # Remove indexes if they exist
    if _index_exists('accounts', 'ix_accounts_crypto_balance_smallest_unit'):
        op.drop_index('ix_accounts_crypto_balance_smallest_unit', 'accounts')
    if _index_exists('accounts', 'ix_accounts_crypto_locked_amount_smallest_unit'):
        op.drop_index('ix_accounts_crypto_locked_amount_smallest_unit', 'accounts')
    
    # Remove columns from accounts table if they exist
    if _column_exists('accounts', 'crypto_balance_smallest_unit'):
        op.drop_column('accounts', 'crypto_balance_smallest_unit')
    if _column_exists('accounts', 'crypto_locked_amount_smallest_unit'):
        op.drop_column('accounts', 'crypto_locked_amount_smallest_unit')
    if _column_exists('accounts', 'precision_config'):
        op.drop_column('accounts', 'precision_config')
    
    # Remove columns from currencies table if they exist
    if _column_exists('currencies', 'precision_config'):
        op.drop_column('currencies', 'precision_config')


def data_migration():
    """Data migration to populate smallest unit amounts for existing crypto accounts"""
    connection = op.get_bind()
    
    print("Starting data migration for smallest unit support...")

    # Batch update accounts table
    print("Updating accounts table in batches...")
    batch_size = 500
    offset = 0
    while True:
        print(f"Processing accounts batch starting at offset {offset}...")
        result = connection.execute(f"""
            UPDATE accounts
            SET crypto_balance_smallest_unit = 0, crypto_locked_amount_smallest_unit = 0
            WHERE id IN (
                SELECT id FROM accounts
                WHERE account_type = 'CRYPTO' AND crypto_balance_smallest_unit IS NULL
                LIMIT {batch_size} OFFSET {offset}
            )
        """)
        if result.rowcount == 0:
            print("Finished processing all account batches.")
            break
        offset += batch_size

    # Update precision config for common cryptocurrencies
    precision_configs = {
        'ETH': {'smallest_unit': 'wei', 'decimal_places': 18, 'display_decimals': 18},
        'BTC': {'smallest_unit': 'satoshis', 'decimal_places': 8, 'display_decimals': 8},
        'LTC': {'smallest_unit': 'litoshis', 'decimal_places': 8, 'display_decimals': 8},
        'SOL': {'smallest_unit': 'lamports', 'decimal_places': 9, 'display_decimals': 9},
        'XRP': {'smallest_unit': 'drops', 'decimal_places': 6, 'display_decimals': 6},
        'TRX': {'smallest_unit': 'sun', 'decimal_places': 6, 'display_decimals': 6},
        'BNB': {'smallest_unit': 'wei', 'decimal_places': 18, 'display_decimals': 18},
        'AVAX': {'smallest_unit': 'nAVAX', 'decimal_places': 18, 'display_decimals': 18},
        'WORLD': {'smallest_unit': 'wei', 'decimal_places': 18, 'display_decimals': 18},
        'OPTIMISM': {'smallest_unit': 'wei', 'decimal_places': 18, 'display_decimals': 18},
        'POLYGON': {'smallest_unit': 'wei', 'decimal_places': 18, 'display_decimals': 18}
    }

    # Efficiently update currencies table
    print("Updating currencies table with precision configurations...")
    for currency_code, config in precision_configs.items():
        config_json = postgresql.json.dumps(config)
        connection.execute(
            sa.text("UPDATE currencies SET precision_config = :config WHERE code = :code"),
            {'config': config_json, 'code': currency_code}
        )
    
    print("Data migration completed successfully.") 