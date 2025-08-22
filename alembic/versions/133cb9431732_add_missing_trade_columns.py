"""add_missing_trade_columns

Revision ID: 133cb9431732
Revises: eda422d07cd2
Create Date: 2025-08-18 10:49:03.649154

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '133cb9431732'
down_revision: Union[str, None] = 'eda422d07cd2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
