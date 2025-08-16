"""Consolidate migration branches for services

Revision ID: a66240c1c794
Revises: a4a44f63d612, e5e326049c4f
Create Date: 2025-08-15 12:01:38.423787

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a66240c1c794'
down_revision: Union[str, None] = ('a4a44f63d612', 'e5e326049c4f')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
