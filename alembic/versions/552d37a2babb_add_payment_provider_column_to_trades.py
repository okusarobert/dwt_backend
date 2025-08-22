"""add_payment_provider_column_to_trades

Revision ID: 552d37a2babb
Revises: ad16d0327ead
Create Date: 2025-08-18 16:43:04.914937

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '552d37a2babb'
down_revision: Union[str, None] = 'ad16d0327ead'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add payment_provider column to trades table
    # Use IF NOT EXISTS to avoid errors if column already exists
    op.execute("ALTER TABLE trades ADD COLUMN IF NOT EXISTS payment_provider paymentprovider;")


def downgrade() -> None:
    op.execute("ALTER TABLE trades DROP COLUMN IF EXISTS payment_provider;")
