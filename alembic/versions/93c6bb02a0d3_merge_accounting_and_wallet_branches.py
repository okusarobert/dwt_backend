"""merge_accounting_and_wallet_branches

Revision ID: 93c6bb02a0d3
Revises: a66240c1c794, ae8a195b7d01
Create Date: 2025-08-15 16:36:20.758586

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '93c6bb02a0d3'
down_revision: Union[str, None] = ('a66240c1c794', 'ae8a195b7d01')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
