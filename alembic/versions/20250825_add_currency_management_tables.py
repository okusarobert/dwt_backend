"""Add currency management tables

Revision ID: 20250825_add_currency_management_tables
Revises: 20250809_change_smallest_unit_to_numeric
Create Date: 2025-08-25 22:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_currency_mgmt_tables'
down_revision = 'change_smallest_unit_to_numeric'
branch_labels = None
depends_on = None


def upgrade():
    # Create admin_currencies table
    op.create_table('admin_currencies',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('symbol', sa.String(10), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_multi_network', sa.Boolean(), nullable=False, default=False),
        sa.Column('contract_address', sa.String(255), nullable=True),
        sa.Column('decimals', sa.Integer(), nullable=False, default=18),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('ix_admin_currencies_symbol', 'admin_currencies', ['symbol'], unique=True)
    
    # Create admin_currency_networks table
    op.create_table('admin_currency_networks',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('currency_id', sa.String(36), nullable=False),
        sa.Column('network_type', sa.String(50), nullable=False),
        sa.Column('network_name', sa.String(100), nullable=False),
        sa.Column('display_name', sa.String(100), nullable=False),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, default=True),
        sa.Column('contract_address', sa.String(255), nullable=True),
        sa.Column('confirmation_blocks', sa.Integer(), nullable=False, default=12),
        sa.Column('explorer_url', sa.String(255), nullable=False),
        sa.Column('is_testnet', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['currency_id'], ['admin_currencies.id'], ondelete='CASCADE')
    )
    
    # Create indexes for currency networks
    op.create_index('ix_admin_currency_networks_currency_id', 'admin_currency_networks', ['currency_id'])
    op.create_index('ix_admin_currency_networks_network_type', 'admin_currency_networks', ['network_type'])


def downgrade():
    # Drop tables in reverse order
    op.drop_index('ix_admin_currency_networks_network_type', table_name='admin_currency_networks')
    op.drop_index('ix_admin_currency_networks_currency_id', table_name='admin_currency_networks')
    op.drop_table('admin_currency_networks')
    
    op.drop_index('ix_admin_currencies_symbol', table_name='admin_currencies')
    op.drop_table('admin_currencies')
