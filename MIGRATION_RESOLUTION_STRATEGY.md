# Migration Resolution Strategy

## Current State Analysis

### Migration State
- **Current Migration**: `add_trading_models` (branchpoint)
- **Migration Heads**: `c8d25c64b432`, `fb84c1febfb6`
- **Conflicts**: Multiple branches preventing upgrade

### Database State
- **Missing Schema**: `trade_id` column, `trades` table, `vouchers` table
- **Error**: `psycopg2.errors.UndefinedColumn: column transactions.trade_id does not exist`

## Root Cause Analysis

The migration conflicts are caused by:
1. **Complex Branching**: Multiple migrations branching from the same parent
2. **State Mismatch**: Migration shows as applied but schema changes not executed
3. **Circular Dependencies**: Conflicting migration dependencies

## Resolution Strategy

### Option 1: Clean Migration Reset (Recommended)

#### Step 1: Backup Current State
```bash
# Backup migration state
docker exec dwt_backend-wallet-1 alembic current > migration_state_backup.txt
docker exec dwt_backend-wallet-1 alembic history > migration_history_backup.txt

# Backup database schema
docker exec dwt_backend-wallet-1 pg_dump -U tondeka -d tondeka --schema-only > schema_backup.sql
```

#### Step 2: Reset to Clean State
```bash
# Reset to a clean migration state
docker exec dwt_backend-wallet-1 alembic stamp 23e791c49f3a
```

#### Step 3: Apply Migrations Sequentially
```bash
# Apply merge migration
docker exec dwt_backend-wallet-1 alembic upgrade 3d91640ec9e0

# Apply trading models
docker exec dwt_backend-wallet-1 alembic upgrade add_trading_models

# Apply schema fix migration
docker exec dwt_backend-wallet-1 alembic upgrade fb84c1febfb6
```

#### Step 4: Verify Schema
```bash
# Verify trade_id column exists
docker exec dwt_backend-wallet-1 python -c "
from sqlalchemy import create_engine, inspect
engine = create_engine('postgresql://tondeka:tondeka@db:5432/tondeka')
inspector = inspect(engine)
columns = [col['name'] for col in inspector.get_columns('transactions')]
print('trade_id exists:', 'trade_id' in columns)
tables = inspector.get_table_names()
print('trades table exists:', 'trades' in tables)
"
```

### Option 2: Direct Schema Fix (Quick Fix)

#### Step 1: Create Direct Migration
Create a new migration that directly adds missing schema:

```python
"""direct_schema_fix

Revision ID: direct_schema_fix
Revises: add_trading_models
Create Date: 2025-08-13 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade() -> None:
    # Add trade_id column directly
    op.add_column('transactions', sa.Column('trade_id', sa.Integer(), nullable=True))
    
    # Create trades table
    op.create_table('trades',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create foreign key
    op.create_foreign_key(
        'fk_transactions_trade_id_trades',
        'transactions', 'trades',
        ['trade_id'], ['id']
    )

def downgrade() -> None:
    op.drop_constraint('fk_transactions_trade_id_trades', 'transactions', type_='foreignkey')
    op.drop_column('transactions', 'trade_id')
    op.drop_table('trades')
```

#### Step 2: Apply Migration
```bash
docker exec dwt_backend-wallet-1 alembic upgrade head
```

### Option 3: Manual Schema Fix (Emergency)

#### Step 1: Connect to Database
```bash
docker exec -it dwt_backend-wallet-1 psql -U tondeka -d tondeka
```

#### Step 2: Add Missing Schema
```sql
-- Add trade_id column
ALTER TABLE transactions ADD COLUMN trade_id INTEGER;

-- Create trades table
CREATE TABLE trades (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Add foreign key constraint
ALTER TABLE transactions 
ADD CONSTRAINT fk_transactions_trade_id_trades 
FOREIGN KEY (trade_id) REFERENCES trades(id);
```

#### Step 3: Update Migration State
```bash
docker exec dwt_backend-wallet-1 alembic stamp fb84c1febfb6
```

## Recommended Approach

**Use Option 1 (Clean Migration Reset)** for the following reasons:
1. **Production Safe**: Proper migration history maintained
2. **Reproducible**: Can be applied to any environment
3. **Clean State**: Resolves all conflicts permanently
4. **Future Proof**: Prevents similar issues

## Success Criteria

- [ ] `trade_id` column exists in `transactions` table
- [ ] `trades` table exists with proper structure
- [ ] `vouchers` table exists (if needed)
- [ ] SOL finality checker works without errors
- [ ] All application functionality works
- [ ] Migration history is clean and linear

## Rollback Plan

If issues occur:
```bash
# Rollback to previous state
docker exec dwt_backend-wallet-1 alembic downgrade add_trading_models

# Restore from backup if needed
docker exec dwt_backend-wallet-1 psql -U tondeka -d tondeka < schema_backup.sql
```

## Next Steps

1. **Choose Resolution Option**: Select Option 1 for production safety
2. **Execute Backup**: Create all necessary backups
3. **Apply Resolution**: Execute the chosen resolution strategy
4. **Verify Results**: Test all functionality
5. **Document Changes**: Update migration documentation
