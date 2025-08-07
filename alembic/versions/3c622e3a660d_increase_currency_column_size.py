"""increase_currency_column_size

Revision ID: 3c622e3a660d
Revises: f0a7dbda0a09
Create Date: 2025-08-01 16:35:17.138143

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3c622e3a660d'
down_revision: Union[str, None] = 'f0a7dbda0a09'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Increase currency column size from 8 to 16 characters
    op.alter_column('accounts', 'currency',
                    existing_type=sa.String(length=8),
                    type_=sa.String(length=16),
                    existing_nullable=True)


def downgrade() -> None:
    # Revert currency column size back to 8 characters
    op.alter_column('accounts', 'currency',
                    existing_type=sa.String(length=16),
                    type_=sa.String(length=8),
                    existing_nullable=True)
