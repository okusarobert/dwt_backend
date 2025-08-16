# Migration Cleanup Plan

## Current State Analysis

### Database State
- **Current Migration**: `add_trading_models` (applied)
- **Migration Head**: `c8d25c64b432` (not applied)
- **Missing Schema**: `trade_id` column, `trades` table, `vouchers` table

### Migration Conflicts Identified
1. **Branch Conflicts**: Multiple migrations trying to branch from same parent
2. **State Mismatch**: Migration shows as applied but schema changes not executed
3. **Complex Dependencies**: Circular or conflicting migration dependencies

## Phase 1: Backup and Safety Measures

### 1.1 Database Backup
```bash
# Create full database backup
pg_dump -h localhost -U tondeka -d tondeka > backup_before_cleanup_$(date +%Y%m%d_%H%M%S).sql

# Create schema-only backup
pg_dump -h localhost -U tondeka -d tondeka --schema-only > schema_backup_$(date +%Y%m%d_%H%M%S).sql
```

### 1.2 Migration State Backup
```bash
# Backup current migration state
docker exec dwt_backend-wallet-1 alembic current > migration_state_backup.txt
docker exec dwt_backend-wallet-1 alembic history > migration_history_backup.txt
```

## Phase 2: Migration Audit and Documentation

### 2.1 Current Migration Files Analysis
- `1d661194d41e` - Base migration (custodial wallet, currency, swap)
- `add_unique_constraint_transactions` - Unique constraint branch
- `add_reference_id_unique_constraint` - Reference constraint branch
- `add_ledger_portfolio_models` - Ledger models branch
- `add_trading_models` - Trading models (applied but not executed)
- `c8d25c64b432` - Trade ID column (not applied)

### 2.2 Conflict Resolution Strategy
1. **Resolve Branch Conflicts**: Create proper merge migrations
2. **Fix State Mismatch**: Ensure migrations actually execute
3. **Clean Dependencies**: Remove circular dependencies

## Phase 3: Migration Cleanup Implementation

### 3.1 Create Clean Migration Sequence
1. **Base Migration**: `1d661194d41e` (already applied)
2. **Merge Branches**: Create proper merge for conflicting branches
3. **Apply Missing Schema**: Add trade_id column and related tables
4. **Verify State**: Ensure database matches migration state

### 3.2 Step-by-Step Implementation

#### Step 1: Reset to Clean State
```bash
# Reset migration state to before conflicts
docker exec dwt_backend-wallet-1 alembic stamp 23e791c49f3a
```

#### Step 2: Apply Migrations Sequentially
```bash
# Apply merge migration
docker exec dwt_backend-wallet-1 alembic upgrade 3d91640ec9e0

# Apply trading models
docker exec dwt_backend-wallet-1 alembic upgrade add_trading_models

# Apply trade_id column
docker exec dwt_backend-wallet-1 alembic upgrade c8d25c64b432
```

#### Step 3: Verify Schema
```bash
# Verify trade_id column exists
docker exec dwt_backend-wallet-1 python -c "
from sqlalchemy import create_engine, inspect
engine = create_engine('postgresql://tondeka:tondeka@db:5432/tondeka')
inspector = inspect(engine)
columns = [col['name'] for col in inspector.get_columns('transactions')]
print('trade_id exists:', 'trade_id' in columns)
"
```

## Phase 4: Testing and Validation

### 4.1 Schema Validation
- [ ] Verify all tables exist
- [ ] Verify all columns exist
- [ ] Verify all constraints exist
- [ ] Verify all indexes exist

### 4.2 Application Testing
- [ ] Test SOL finality checker
- [ ] Test trading functionality
- [ ] Test database connections
- [ ] Test migration rollback

## Phase 5: Production Deployment

### 5.1 Pre-deployment Checklist
- [ ] All tests pass
- [ ] Migration rollback tested
- [ ] Backup verified
- [ ] Rollback plan documented

### 5.2 Deployment Steps
1. **Staging Deployment**: Apply to staging environment first
2. **Production Backup**: Create production backup
3. **Production Deployment**: Apply migration cleanup
4. **Verification**: Verify all systems working
5. **Monitoring**: Monitor for any issues

## Phase 6: Prevention Measures

### 6.1 Migration Best Practices
- Always test migrations in staging
- Use proper migration dependencies
- Avoid complex branching
- Document migration purposes

### 6.2 Monitoring and Alerts
- Monitor migration state vs database state
- Alert on migration failures
- Regular migration audits

## Rollback Plan

### Emergency Rollback
```bash
# If issues occur, rollback to previous state
docker exec dwt_backend-wallet-1 alembic downgrade add_trading_models

# Restore from backup if needed
psql -h localhost -U tondeka -d tondeka < backup_before_cleanup_*.sql
```

## Success Criteria

- [ ] All migration conflicts resolved
- [ ] Database schema matches migration state
- [ ] SOL finality checker works without errors
- [ ] All application functionality works
- [ ] Migration history is clean and linear
- [ ] Rollback procedures tested and documented
