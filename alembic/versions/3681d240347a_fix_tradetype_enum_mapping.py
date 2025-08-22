"""fix_tradetype_enum_mapping

Revision ID: 3681d240347a
Revises: d57ed0c3f961
Create Date: 2025-08-18 16:10:02.786621

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3681d240347a'
down_revision: Union[str, None] = 'd57ed0c3f961'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop and recreate the tradetype enum to ensure clean mapping
    # First, update any existing trades to use a temporary column
    op.execute("ALTER TABLE trades ADD COLUMN trade_type_temp VARCHAR(10);")
    op.execute("UPDATE trades SET trade_type_temp = trade_type::text;")
    op.execute("ALTER TABLE trades DROP COLUMN trade_type;")
    
    # Drop the old enum type
    op.execute("DROP TYPE IF EXISTS tradetype;")
    
    # Create new enum type with correct lowercase values
    op.execute("CREATE TYPE tradetype AS ENUM ('buy', 'sell');")
    
    # Add the column back with the new enum type
    op.execute("ALTER TABLE trades ADD COLUMN trade_type tradetype;")
    op.execute("UPDATE trades SET trade_type = trade_type_temp::tradetype;")
    op.execute("ALTER TABLE trades DROP COLUMN trade_type_temp;")
    op.execute("ALTER TABLE trades ALTER COLUMN trade_type SET NOT NULL;")


def downgrade() -> None:
    # This is a destructive migration, downgrade would require recreating the old state
    pass
