"""Fix transactions reference_id field length

Revision ID: fix_tx_ref_length
Revises: fix_ref_length
Create Date: 2025-08-07 14:38:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fix_tx_ref_length'
down_revision = 'fix_ref_length'
branch_labels = None
depends_on = None


def upgrade():
    """Increase reference_id field length to accommodate Ethereum transaction hashes"""
    # Change reference_id field from VARCHAR(64) to VARCHAR(100) to accommodate Ethereum tx hashes
    op.alter_column('transactions', 'reference_id',
                    existing_type=sa.VARCHAR(length=64),
                    type_=sa.VARCHAR(length=100),
                    existing_nullable=True)


def downgrade():
    """Revert reference_id field length back to 64 characters"""
    op.alter_column('transactions', 'reference_id',
                    existing_type=sa.VARCHAR(length=100),
                    type_=sa.VARCHAR(length=64),
                    existing_nullable=True) 