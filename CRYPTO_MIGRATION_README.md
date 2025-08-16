# Crypto Amount Migration Guide

This guide explains how to migrate your database to support crypto amounts in smallest units (wei, satoshis, etc.) to avoid precision issues.

## 🎯 Overview

The migration adds support for storing crypto amounts in their smallest units:
- **ETH**: Stored in wei (18 decimal places)
- **BTC**: Stored in satoshis (8 decimal places)
- **SOL**: Stored in lamports (9 decimal places)
- **XRP**: Stored in drops (6 decimal places)
- And more...

## 📁 Migration Files

### Schema Migration
- **File**: `alembic/versions/add_crypto_smallest_unit_support.py`
- **Purpose**: Adds new database columns for smallest unit amounts
- **Columns Added**:
  - `crypto_balance_smallest_unit` (BigInteger)
  - `crypto_locked_amount_smallest_unit` (BigInteger)
  - `precision_config` (JSON)

### Data Migration
- **File**: `migrate_crypto_amounts.py`
- **Purpose**: Converts existing crypto amounts to smallest units
- **Commands**:
  - `python3 migrate_crypto_amounts.py migrate` - Run migration
  - `python3 migrate_crypto_amounts.py verify` - Verify migration
  - `python3 migrate_crypto_amounts.py rollback` - Rollback migration

### Deployment Script
- **File**: `deploy_crypto_migration.sh`
- **Purpose**: Automated deployment with backup and verification
- **Commands**:
  - `./deploy_crypto_migration.sh deploy` - Deploy migration
  - `./deploy_crypto_migration.sh rollback` - Rollback migration
  - `./deploy_crypto_migration.sh verify` - Verify migration
  - `./deploy_crypto_migration.sh backup` - Create backup only

## 🚀 Deployment Steps

### 1. Prerequisites
```bash
# Ensure you're in the project root
cd /path/to/dwt_backend

# Check database connectivity
python3 -c "
from sqlalchemy import create_engine
import os

db_url = f'postgresql://{os.getenv(\"DB_USER\", \"postgres\")}:{os.getenv(\"DB_PASSWORD\", \"password\")}@{os.getenv(\"DB_HOST\", \"localhost\")}:{os.getenv(\"DB_PORT\", \"5432\")}/{os.getenv(\"DB_NAME\", \"dwt_backend\")}'
engine = create_engine(db_url)
engine.connect()
print('Database connection successful')
"
```

### 2. Create Backup (Optional)
```bash
# Create manual backup
pg_dump -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME > backup_$(date +%Y%m%d_%H%M%S).sql
```

### 3. Run Migration

#### Option A: Automated Deployment (Recommended)
```bash
# Make script executable
chmod +x deploy_crypto_migration.sh

# Run deployment
./deploy_crypto_migration.sh deploy
```

#### Option B: Manual Deployment
```bash
# 1. Run schema migration
alembic upgrade head

# 2. Run data migration
python3 migrate_crypto_amounts.py migrate

# 3. Verify migration
python3 migrate_crypto_amounts.py verify
```

## 🔍 Verification

### Check Migration Status
```bash
# Verify all accounts migrated
python3 migrate_crypto_amounts.py verify
```

### Sample Output
```
🔍 Verifying migration...
✅ All crypto accounts have been migrated!
📋 Sample of migrated accounts:
   Account 1 (ETH):
     Balance: 1.5 ETH → 1,500,000,000,000,000,000 wei
     Locked: 0.05 ETH → 50,000,000,000,000,000 wei
```

## 🔄 Rollback (If Needed)

### Automated Rollback
```bash
./deploy_crypto_migration.sh rollback
```

### Manual Rollback
```bash
# Reset smallest unit amounts
python3 migrate_crypto_amounts.py rollback

# Downgrade schema (if needed)
alembic downgrade -1
```

## 📊 Database Schema Changes

### Before Migration
```sql
-- Old schema with limited precision
balance: Numeric(15, 2)  -- Only 2 decimal places
locked_amount: Numeric(15, 2)
```

### After Migration
```sql
-- New schema with smallest units
crypto_balance_smallest_unit: BigInteger  -- ETH in wei, BTC in satoshis, etc.
crypto_locked_amount_smallest_unit: BigInteger
precision_config: JSON  -- Currency-specific precision settings
```

## 💡 Benefits

### ✅ Precision Accuracy
- **No floating-point errors**
- **Exact representation of smallest units**
- **Perfect for micro-transactions**

### ✅ Storage Efficiency
- **Integer storage** (no decimal precision issues)
- **Smaller storage footprint**
- **Faster calculations**

### ✅ Blockchain Compatibility
- **Native blockchain units** (wei, satoshis, lamports)
- **Direct blockchain integration**
- **No conversion errors**

## 🛠️ Application Updates

### Updated Account Model
```python
# New methods for smallest units
account.get_balance_smallest_unit("ETH")  # Returns wei amount
account.get_locked_amount_smallest_unit("BTC")  # Returns satoshi amount
```

### Updated Utility Functions
```python
from db.crypto_precision import to_smallest_unit, from_smallest_unit

# Convert to smallest units
wei_amount = to_smallest_unit(0.001, "ETH")  # 1000000000000000 wei

# Convert from smallest units
eth_amount = from_smallest_unit(wei_amount, "ETH")  # 0.001 ETH
```

## 🚨 Important Notes

### ⚠️ Breaking Changes
- **API responses** may change format
- **Database queries** need updates
- **Application code** needs updates

### 🔒 Safety Measures
- **Automatic backup** before migration
- **Verification step** after migration
- **Rollback capability** if issues occur

### 📈 Performance Impact
- **Minimal impact** on existing operations
- **Improved precision** for crypto operations
- **Better scalability** for micro-transactions

## 🆘 Troubleshooting

### Common Issues

#### 1. Database Connection Failed
```bash
# Check environment variables
echo $DB_HOST $DB_PORT $DB_NAME $DB_USER

# Test connection manually
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME
```

#### 2. Migration Failed
```bash
# Check logs
tail -f migration.log

# Verify database state
python3 migrate_crypto_amounts.py verify
```

#### 3. Rollback Needed
```bash
# Run rollback
./deploy_crypto_migration.sh rollback

# Restore from backup if needed
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME < backup_file.sql
```

## 📞 Support

If you encounter issues during migration:

1. **Check logs** for detailed error messages
2. **Verify database connectivity**
3. **Review environment variables**
4. **Test with small dataset first**
5. **Contact development team** if issues persist

---

**Migration completed successfully! 🎉**

Your database now supports crypto amounts in smallest units with perfect precision. 