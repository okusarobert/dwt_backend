"""Ensure all account types exist in enum

Revision ID: d7d7cd31ffa4
Revises: ae8a195b7d01
Create Date: 2025-08-15 14:28:54.998677

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd7d7cd31ffa4'
down_revision: Union[str, None] = 'bbb8006cdaf5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE accounttype ADD VALUE IF NOT EXISTS 'ASSET'")
    op.execute("ALTER TYPE accounttype ADD VALUE IF NOT EXISTS 'LIABILITY'")
    op.execute("ALTER TYPE accounttype ADD VALUE IF NOT EXISTS 'EQUITY'")
    op.execute("ALTER TYPE accounttype ADD VALUE IF NOT EXISTS 'INCOME'")
    op.execute("ALTER TYPE accounttype ADD VALUE IF NOT EXISTS 'EXPENSE'")


def downgrade() -> None:
    pass
