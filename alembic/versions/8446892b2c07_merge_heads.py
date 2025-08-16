"""merge heads

Revision ID: 8446892b2c07
Revises: 60cafc119eef, add_crypto_smallest_unit_support
Create Date: 2025-08-07 12:57:30.529694

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8446892b2c07'
down_revision: Union[str, None] = ('60cafc119eef', 'add_crypto_smallest_unit_support')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
