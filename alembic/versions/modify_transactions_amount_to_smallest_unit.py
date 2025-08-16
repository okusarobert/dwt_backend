"""Modify transactions amount field to store smallest units

Revision ID: modify_transactions_amount_to_smallest_unit
Revises: fix_tx_ref_length
Create Date: 2025-01-07 22:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'tx_amount_smallest_unit'
down_revision = 'fix_tx_ref_length'
branch_labels = None
depends_on = None


def upgrade():
    """Upgrade to store amounts in smallest units as big integers"""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [c['name'] for c in inspector.get_columns('transactions')]

    # Add new amount_smallest_unit column if it doesn't exist
    if 'amount_smallest_unit' not in columns:
        op.add_column('transactions', sa.Column('amount_smallest_unit', sa.BigInteger(), nullable=True))
    
    # Add precision_config column to store conversion info if it doesn't exist
    if 'precision_config' not in columns:
        op.add_column('transactions', sa.Column('precision_config', postgresql.JSONB(), nullable=True))
    
    # Update existing transactions to convert amounts to smallest units
    # This should only run once, so we check if amount_smallest_unit is NULL
    op.execute("""
        UPDATE transactions 
        SET amount_smallest_unit = CASE 
            WHEN metadata_json->>'amount_eth' IS NOT NULL 
            THEN (metadata_json->>'amount_eth')::numeric * 1000000000000000000
            ELSE amount * 1000000000000000000
        END,
        precision_config = '{"currency": "ETH", "decimals": 18, "smallest_unit": "wei"}'
        WHERE (metadata_json->>'amount_eth' IS NOT NULL OR metadata_json->>'currency' = 'ETH') AND amount_smallest_unit IS NULL
    """)
    
    # For all other transactions, set default values where amount_smallest_unit is still NULL
    op.execute("""
        UPDATE transactions 
        SET amount_smallest_unit = COALESCE(amount, 0) * 1000000000000000000,
            precision_config = '{"currency": "UNKNOWN", "decimals": 18, "smallest_unit": "smallest_unit"}'
        WHERE amount_smallest_unit IS NULL
    """)
    
    # Make amount_smallest_unit NOT NULL after data migration
    op.alter_column('transactions', 'amount_smallest_unit', nullable=False)


def downgrade():
    """Downgrade back to decimal amounts"""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [c['name'] for c in inspector.get_columns('transactions')]

    if 'amount_smallest_unit' in columns:
        # Convert back from smallest units to decimal amounts
        op.execute("""
            UPDATE transactions 
            SET amount = CASE 
                WHEN precision_config->>'decimals' IS NOT NULL 
                THEN amount_smallest_unit::numeric / POWER(10, (precision_config->>'decimals')::integer)
                ELSE amount_smallest_unit::numeric / 1000000000000000000
            END
            WHERE amount_smallest_unit IS NOT NULL
        """)
        op.drop_column('transactions', 'amount_smallest_unit')

    if 'precision_config' in columns:
        op.drop_column('transactions', 'precision_config') 