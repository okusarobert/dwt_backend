#!/bin/bash

# Crypto Amount Migration Deployment Script
# This script safely deploys the crypto smallest unit migration

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "alembic.ini" ]; then
    error "This script must be run from the wallet service directory"
    exit 1
fi

# Check if database is accessible
check_database() {
    log "Checking database connectivity..."
    
    # Try to connect to database
    python3 -c "
import os
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

db_host = os.getenv('DB_HOST', 'localhost')
db_port = os.getenv('DB_PORT', '5432')
db_name = os.getenv('DB_NAME', 'dwt_backend')
db_user = os.getenv('DB_USER', 'postgres')
db_password = os.getenv('DB_PASSWORD', 'password')

db_url = f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'

try:
    engine = create_engine(db_url)
    engine.connect()
    print('Database connection successful')
except OperationalError as e:
    print(f'Database connection failed: {e}')
    exit(1)
"
    
    if [ $? -eq 0 ]; then
        success "Database connection verified"
    else
        error "Cannot connect to database. Please check your environment variables."
        exit 1
    fi
}

# Create backup
create_backup() {
    log "Creating database backup..."
    
    db_host=${DB_HOST:-localhost}
    db_port=${DB_PORT:-5432}
    db_name=${DB_NAME:-dwt_backend}
    db_user=${DB_USER:-postgres}
    
    backup_file="crypto_migration_backup_$(date +%Y%m%d_%H%M%S).sql"
    
    pg_dump -h $db_host -p $db_port -U $db_user -d $db_name > $backup_file
    
    if [ $? -eq 0 ]; then
        success "Backup created: $backup_file"
    else
        error "Backup failed"
        exit 1
    fi
}

# Run schema migration
run_schema_migration() {
    log "Running Alembic schema migration..."
    
    # Check for multiple heads and merge if needed
    log "Checking for multiple migration heads..."
    heads_output=$(alembic heads 2>&1)
    head_count=$(echo "$heads_output" | grep -c "head)")
    
    if [ "$head_count" -gt 1 ]; then
        warning "Multiple migration heads detected. Merging heads..."
        
        # Extract head revision IDs
        head_revisions=$(echo "$heads_output" | grep "head)" | awk '{print $1}' | tr '\n' ' ')
        
        # Create merge migration
        alembic merge -m "merge heads" $head_revisions
        
        if [ $? -eq 0 ]; then
            success "Merge migration created"
        else
            error "Failed to create merge migration"
            exit 1
        fi
    fi
    
    # Run the migration
    alembic upgrade head
    
    if [ $? -eq 0 ]; then
        success "Schema migration completed"
    else
        error "Schema migration failed"
        exit 1
    fi
}

# Run data migration
run_data_migration() {
    log "Running data migration..."
    
    # Run the data migration script
    python3 migrate_crypto_amounts.py migrate
    
    if [ $? -eq 0 ]; then
        success "Data migration completed"
    else
        error "Data migration failed"
        exit 1
    fi
}

# Verify migration
verify_migration() {
    log "Verifying migration..."
    
    # Run verification
    python3 migrate_crypto_amounts.py verify
    
    if [ $? -eq 0 ]; then
        success "Migration verification passed"
    else
        error "Migration verification failed"
        exit 1
    fi
}

# Show migration summary
show_summary() {
    log "Migration Summary:"
    echo "=================="
    echo "✅ Schema migration completed"
    echo "✅ Data migration completed"
    echo "✅ Verification passed"
    echo ""
    echo "The database now supports crypto amounts in smallest units:"
    echo "  - ETH amounts stored in wei"
    echo "  - BTC amounts stored in satoshis"
    echo "  - SOL amounts stored in lamports"
    echo "  - etc."
    echo ""
    echo "Backup file: $backup_file"
    echo ""
    success "Migration completed successfully!"
}

# Main deployment function
deploy_migration() {
    log "Starting crypto amount migration deployment..."
    echo ""
    
    # Check database connectivity
    check_database

    # Establish alembic baseline if schema already has smallest-unit columns but alembic_version is empty
    log "Checking if Alembic needs baseline stamp..."
    python3 - <<'PY'
import os
from sqlalchemy import create_engine, inspect, text

db_host = os.getenv('DB_HOST', 'localhost')
db_port = os.getenv('DB_PORT', '5432')
db_name = os.getenv('DB_NAME', 'dwt_backend')
db_user = os.getenv('DB_USER', 'postgres')
db_password = os.getenv('DB_PASSWORD', 'password')

db_url = f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'
engine = create_engine(db_url)
with engine.connect() as conn:
    insp = inspect(conn)
    has_accounts = insp.has_table('accounts')
    has_versions = insp.has_table('alembic_version')
    needs_stamp = False
    if has_accounts:
        cols = {c['name'] for c in insp.get_columns('accounts')}
        if {'crypto_balance_smallest_unit','crypto_locked_amount_smallest_unit'}.issubset(cols):
            # Smallest-unit columns already exist
            if not has_versions:
                needs_stamp = True
            else:
                count = conn.execute(text('SELECT COUNT(*) FROM alembic_version')).scalar()
                if count == 0:
                    needs_stamp = True
    if needs_stamp:
        # Query current heads from alembic and stamp to a single head
        # We rely on shell to run 'alembic heads -q' next
        print('STAMP_REQUIRED')
    else:
        print('NO_STAMP')
PY

    if [ "$?" -ne 0 ]; then
        warning "Baseline detection failed; continuing without stamp"
    else
        stamp_needed=$(python3 - <<'PY'
import os
from sqlalchemy import create_engine, inspect, text
db_host = os.getenv('DB_HOST', 'localhost')
db_port = os.getenv('DB_PORT', '5432')
db_name = os.getenv('DB_NAME', 'dwt_backend')
db_user = os.getenv('DB_USER', 'postgres')
db_password = os.getenv('DB_PASSWORD', 'password')
db_url = f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'
engine = create_engine(db_url)
with engine.connect() as conn:
    insp = inspect(conn)
    has_accounts = insp.has_table('accounts')
    has_versions = insp.has_table('alembic_version')
    needs_stamp = False
    if has_accounts:
        cols = {c['name'] for c in insp.get_columns('accounts')}
        if {'crypto_balance_smallest_unit','crypto_locked_amount_smallest_unit'}.issubset(cols):
            if not has_versions:
                needs_stamp = True
            else:
                count = conn.execute(text('SELECT COUNT(*) FROM alembic_version')).scalar()
                needs_stamp = (count == 0)
    print('yes' if needs_stamp else 'no')
PY
)
        if [ "$stamp_needed" = "yes" ]; then
            log "Schema already has smallest-unit columns but alembic has no revision; stamping to current head..."
            head_rev=$(alembic heads | awk 'NR==1{print $1}')
            if [ -n "$head_rev" ]; then
                alembic stamp "$head_rev"
                success "Stamped database to revision $head_rev"
            else
                warning "Could not determine head revision; skipping stamp"
            fi
        fi
    fi
    
    # Create backup
    create_backup
    
    # Run schema migration
    run_schema_migration
    
    # Run data migration
    run_data_migration
    
    # Verify migration
    verify_migration
    
    # Show summary
    show_summary
}

# Rollback function
rollback_migration() {
    warning "This will rollback the crypto migration. Are you sure? (y/N)"
    read -r response
    
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        log "Rolling back migration..."
        
        # Run rollback
        python3 migrate_crypto_amounts.py rollback
        
        if [ $? -eq 0 ]; then
            success "Rollback completed"
        else
            error "Rollback failed"
            exit 1
        fi
    else
        log "Rollback cancelled"
    fi
}

# Show help
show_help() {
    echo "Crypto Amount Migration Deployment Script"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  deploy    - Deploy the migration (default)"
    echo "  rollback  - Rollback the migration"
    echo "  verify    - Verify the migration"
    echo "  backup    - Create database backup only"
    echo "  help      - Show this help"
    echo ""
    echo "Environment Variables:"
    echo "  DB_HOST     - Database host (default: localhost)"
    echo "  DB_PORT     - Database port (default: 5432)"
    echo "  DB_NAME     - Database name (default: dwt_backend)"
    echo "  DB_USER     - Database user (default: postgres)"
    echo "  DB_PASSWORD - Database password (default: password)"
}

# Main script logic
case "${1:-deploy}" in
    "deploy")
        deploy_migration
        ;;
    "rollback")
        rollback_migration
        ;;
    "verify")
        verify_migration
        ;;
    "backup")
        check_database
        create_backup
        ;;
    "help"|"-h"|"--help")
        show_help
        ;;
    *)
        error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac 