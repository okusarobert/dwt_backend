"""add_missing_trade_columns

Revision ID: eda422d07cd2
Revises: 43076c183ed9
Create Date: 2025-08-18 10:25:37.013593

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'eda422d07cd2'
down_revision: Union[str, None] = '43076c183ed9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Get database connection to check existing columns
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = [col['name'] for col in inspector.get_columns('trades')]
    
    # Add missing columns identified by audit
    columns_to_add = [
        # Missing Trade model fields
        ('cancelled_at', sa.DateTime),
        ('payment_metadata', sa.JSON()),
        ('payment_received_at', sa.DateTime),
        
        # Unified amount fields for precision system
        ('crypto_amount_smallest_unit', sa.Numeric(78, 0)),
        ('fiat_amount_smallest_unit', sa.Numeric(78, 0)),
        ('fee_amount_smallest_unit', sa.Numeric(78, 0)),
        ('precision_config', sa.JSON()),
        
        # Additional payment detail fields for comprehensive support
        ('mobile_money_provider', sa.String(32)),
        ('bank_name', sa.String(64)),
        ('account_name', sa.String(128)),
        ('account_number', sa.String(32)),
        ('deposit_reference', sa.String(64))
    ]
    
    for column_name, column_type in columns_to_add:
        if column_name not in existing_columns:
            op.add_column('trades', sa.Column(column_name, column_type, nullable=True))
            print(f"Added column: {column_name}")
        else:
            print(f"Column already exists, skipping: {column_name}")


def downgrade() -> None:
    # Remove the added columns (phone_number is not removed as it existed before this migration)
    op.drop_column('trades', 'deposit_reference')
    op.drop_column('trades', 'account_number')
    op.drop_column('trades', 'account_name')
    op.drop_column('trades', 'bank_name')
    op.drop_column('trades', 'mobile_money_provider')
    op.drop_column('trades', 'precision_config')
    op.drop_column('trades', 'fee_amount_smallest_unit')
    op.drop_column('trades', 'fiat_amount_smallest_unit')
    op.drop_column('trades', 'crypto_amount_smallest_unit')
