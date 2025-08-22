"""add_crypto_accounting_accounts

Revision ID: 63cbf539ec6d
Revises: add_provider_col_tx
Create Date: 2025-08-21 10:03:26.454887

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '63cbf539ec6d'
down_revision: Union[str, None] = 'add_provider_col_tx'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Insert required crypto accounting accounts for monitoring services
    # Use INSERT WHERE NOT EXISTS to avoid duplicates
    accounts = [
        ('Crypto Assets - ETH', 'ASSET', 'ETH'),
        ('Crypto Assets - TRX', 'ASSET', 'TRX'), 
        ('Crypto Assets - SOL', 'ASSET', 'SOL'),
        ('Crypto Assets - BTC', 'ASSET', 'BTC'),
        ('Crypto Assets - BNB', 'ASSET', 'BNB'),
        ('Pending Trade Settlements', 'LIABILITY', 'UGX'),
        ('User Liabilities - ETH', 'LIABILITY', 'ETH'),
        ('User Liabilities - TRX', 'LIABILITY', 'TRX'),
        ('User Liabilities - SOL', 'LIABILITY', 'SOL'),
        ('User Liabilities - BTC', 'LIABILITY', 'BTC'),
        ('User Liabilities - BNB', 'LIABILITY', 'BNB')
    ]
    
    for name, account_type, currency in accounts:
        op.execute(f"""
            INSERT INTO chart_of_accounts (name, type, currency, is_system_account) 
            SELECT '{name}', '{account_type}', '{currency}', true
            WHERE NOT EXISTS (
                SELECT 1 FROM chart_of_accounts WHERE name = '{name}'
            );
        """)


def downgrade() -> None:
    # Remove the crypto accounting accounts
    op.execute("""
        DELETE FROM chart_of_accounts WHERE name IN (
            'Crypto Assets - ETH',
            'Crypto Assets - TRX', 
            'Crypto Assets - SOL',
            'Crypto Assets - BTC',
            'Crypto Assets - BNB',
            'Pending Trade Settlements',
            'User Liabilities - ETH',
            'User Liabilities - TRX',
            'User Liabilities - SOL',
            'User Liabilities - BTC',
            'User Liabilities - BNB'
        );
    """)
