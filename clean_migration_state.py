#!/usr/bin/env python3
"""
Clean Migration State Script

This script cleans the migration state in the database and resets it to a clean point
so we can apply migrations sequentially from a clean state.
"""

import sys
from sqlalchemy import create_engine, text

# Database connection
DATABASE_URL = "postgresql://tondeka:tondeka@db:5432/tondeka"

def clean_migration_state():
    """Clean the migration state in the database"""
    try:
        print("🔧 Connecting to database...")
        engine = create_engine(DATABASE_URL)
        
        with engine.begin() as connection:
            print("🧹 Cleaning migration state...")
            
            # Delete all migration records from alembic_version table
            connection.execute(text("DELETE FROM alembic_version"))
            print("  ✅ Cleared alembic_version table")
            
            # Insert the base migration
            connection.execute(text("INSERT INTO alembic_version (version_num) VALUES ('1d661194d41e')"))
            print("  ✅ Set base migration: 1d661194d41e")
        
        print("\n✅ Migration state cleaned successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error cleaning migration state: {e}")
        return False

def main():
    """Main execution function"""
    print("🚀 Starting Migration State Cleanup")
    print("=" * 50)
    
    success = clean_migration_state()
    
    if success:
        print("\n🎯 Next Steps:")
        print("1. Run: docker exec dwt_backend-wallet-1 alembic upgrade head")
        print("2. Verify schema changes")
        print("3. Test application functionality")
    else:
        print("\n❌ Migration state cleanup failed.")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
