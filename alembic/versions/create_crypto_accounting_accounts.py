"""Create crypto accounting accounts

Revision ID: create_crypto_accounts
Revises: add_journal_entry_id
Create Date: 2025-08-21 16:06:30.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
from sqlalchemy import String, Integer

# revision identifiers, used by Alembic.
revision = 'create_crypto_accounts'
down_revision = 'add_journal_entry_id'
branch_labels = None
depends_on = None

def upgrade():
    # The accounts table uses 'label' for account names, not 'name'
    # Create accounts table reference for bulk insert
    accounts_table = table('accounts',
        column('balance', sa.Numeric),
        column('locked_amount', sa.Numeric),
        column('user_id', Integer),
        column('account_number', String),
        column('label', String),
        column('currency', String),
        column('account_type', String)
    )
    
    # Insert crypto asset accounts using label field
    # Use user_id = 1 for system accounts (NOT NULL constraint)
    op.bulk_insert(accounts_table, [
        {
            'account_type': 'ASSET',
            'balance': 0,
            'locked_amount': 0,
            'user_id': 2,
            'account_number': 'ETH_ASSET',
            'label': 'Crypto Assets - ETH',
            'currency': 'ETH'
        },
        {
            'account_type': 'ASSET',
            'balance': 0,
            'locked_amount': 0,
            'user_id': 2,
            'account_number': 'TRX_ASSET',
            'label': 'Crypto Assets - TRX',
            'currency': 'TRX'
        },
        {
            'account_type': 'LIABILITY', 
            'balance': 0,
            'locked_amount': 0,
            'user_id': 2,
            'account_number': 'ETH_LIAB',
            'label': 'User Liabilities - ETH',
            'currency': 'ETH'
        },
        {
            'account_type': 'LIABILITY',
            'balance': 0, 
            'locked_amount': 0,
            'user_id': 2,
            'account_number': 'TRX_LIAB',
            'label': 'User Liabilities - TRX',
            'currency': 'TRX'
        }
    ])

def downgrade():
    # Remove the created accounts using label field
    op.execute("DELETE FROM accounts WHERE label IN ('Crypto Assets - ETH', 'Crypto Assets - TRX', 'User Liabilities - ETH', 'User Liabilities - TRX')")
