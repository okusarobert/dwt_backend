"""add_provider_column_to_transactions

Revision ID: add_provider_column_to_transactions
Revises: 552d37a2babb
Create Date: 2025-08-19 12:53:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_provider_col_tx'
down_revision: Union[str, None] = '552d37a2babb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if provider column already exists in transactions table
    connection = op.get_bind()
    
    transactions_has_provider = connection.execute(sa.text("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'transactions' AND column_name = 'provider'
        );
    """)).scalar()
    
    # Only add the column if it doesn't exist
    if not transactions_has_provider:
        op.execute("ALTER TABLE transactions ADD COLUMN provider paymentprovider;")


def downgrade() -> None:
    op.execute("ALTER TABLE transactions DROP COLUMN IF EXISTS provider;")
