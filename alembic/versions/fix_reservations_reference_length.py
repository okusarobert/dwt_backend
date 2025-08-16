"""Fix reservations reference field length

Revision ID: fix_ref_length
Revises: 8446892b2c07
Create Date: 2025-08-07 14:35:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fix_ref_length'
down_revision = '8446892b2c07'
branch_labels = None
depends_on = None


def upgrade():
    """Increase reference field length to accommodate Ethereum transaction hashes"""
    # Change reference field from VARCHAR(64) to VARCHAR(100) to accommodate Ethereum tx hashes
    op.alter_column('reservations', 'reference',
                    existing_type=sa.VARCHAR(length=64),
                    type_=sa.VARCHAR(length=100),
                    existing_nullable=True)


def downgrade():
    """Revert reference field length back to 64 characters"""
    op.alter_column('reservations', 'reference',
                    existing_type=sa.VARCHAR(length=100),
                    type_=sa.VARCHAR(length=64),
                    existing_nullable=True) 