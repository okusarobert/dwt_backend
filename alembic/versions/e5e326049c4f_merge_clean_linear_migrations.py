"""merge_clean_linear_migrations

Revision ID: e5e326049c4f
Revises: change_smallest_unit_to_numeric, 23f2a6ea0956
Create Date: 2025-08-13 15:03:28.037382

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5e326049c4f'
down_revision: Union[str, None] = ('change_smallest_unit_to_numeric', '23f2a6ea0956')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
