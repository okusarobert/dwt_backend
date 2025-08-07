"""add_webhook_id_to_crypto_addresses

Revision ID: e2f84217a6be
Revises: 3c622e3a660d
Create Date: 2025-08-03 13:05:32.269967

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e2f84217a6be'
down_revision: Union[str, None] = '3c622e3a660d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add webhook_ids column to crypto_addresses table
    op.add_column('crypto_addresses', sa.Column('webhook_ids', sa.JSON(), nullable=True))


def downgrade() -> None:
    # Remove webhook_ids column from crypto_addresses table
    op.drop_column('crypto_addresses', 'webhook_ids')
