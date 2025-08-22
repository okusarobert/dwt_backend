"""add_missing_trade_columns

Revision ID: e03575394979
Revises: 133cb9431732
Create Date: 2025-08-18 10:59:33.867844

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e03575394979'
down_revision: Union[str, None] = '133cb9431732'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
