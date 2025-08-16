"""merge ledger portfolio models with existing head

Revision ID: 23e791c49f3a
Revises: add_ledger_portfolio_models, d86094e47237
Create Date: 2025-08-11 08:49:55.723457

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '23e791c49f3a'
down_revision: Union[str, None] = 'add_ledger_portfolio_models'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
