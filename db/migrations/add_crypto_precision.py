"""
Migration: Add Crypto Precision Support

This migration adds support for higher precision amounts for cryptocurrencies.
It creates new columns for crypto amounts and updates the existing structure.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_crypto_precision_support'
down_revision = None  # Update this to the previous migration
depends_on = None

def upgrade():
    """Upgrade database to support crypto precision"""
    
    # Add new columns for crypto amounts with higher precision
    op.add_column('accounts', sa.Column('crypto_balance', sa.Numeric(38, 18), nullable=True))
    op.add_column('accounts', sa.Column('crypto_locked_amount', sa.Numeric(38, 18), nullable=True))
    
    # Add precision configuration column
    op.add_column('accounts', sa.Column('precision_config', sa.JSON, nullable=True))
    
    # Add index for crypto amounts
    op.create_index('ix_accounts_crypto_balance', 'accounts', ['crypto_balance'])
    op.create_index('ix_accounts_crypto_locked_amount', 'accounts', ['crypto_locked_amount'])
    
    # Add precision configuration to currencies table
    op.add_column('currencies', sa.Column('precision_config', sa.JSON, nullable=True))
    
    # Update existing crypto accounts to use new precision
    # This will be handled by application logic during migration

def downgrade():
    """Downgrade database to remove crypto precision support"""
    
    # Remove crypto amount columns
    op.drop_column('accounts', 'crypto_balance')
    op.drop_column('accounts', 'crypto_locked_amount')
    op.drop_column('accounts', 'precision_config')
    
    # Remove precision config from currencies
    op.drop_column('currencies', 'precision_config')
    
    # Remove indexes
    op.drop_index('ix_accounts_crypto_balance', 'accounts')
    op.drop_index('ix_accounts_crypto_locked_amount', 'accounts') 