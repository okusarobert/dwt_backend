#!/usr/bin/env python3
"""
Direct Schema Fix Script

This script directly adds the missing schema elements to the database
to resolve the SOL finality checker error without dealing with migration conflicts.
"""

import sys
from sqlalchemy import create_engine, inspect, text

# Database connection
DATABASE_URL = "postgresql://tondeka:tondeka@db:5432/tondeka"

def fix_schema_directly():
    """Add missing schema elements directly to the database"""
    try:
        print("🔧 Connecting to database...")
        engine = create_engine(DATABASE_URL)
        inspector = inspect(engine)
        
        # Check current schema state
        print("📊 Checking current schema state...")
        tables = inspector.get_table_names()
        print(f"Tables: {tables}")
        
        if 'transactions' in tables:
            columns = [col['name'] for col in inspector.get_columns('transactions')]
            print(f"Transactions columns: {columns}")
            print(f"trade_id exists: {'trade_id' in columns}")
        else:
            print("❌ transactions table not found")
            return False
        
        print(f"trades table exists: {'trades' in tables}")
        
        # Add missing schema elements
        with engine.begin() as connection:
            print("\n🔧 Adding missing schema elements...")
            
            # Create trades table if it doesn't exist
            if 'trades' not in tables:
                print("  - Creating trades table...")
                connection.execute(text("""
                    CREATE TABLE trades (
                        id SERIAL PRIMARY KEY,
                        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMP NOT NULL DEFAULT NOW()
                    )
                """))
                print("  ✅ trades table created")
            else:
                print("  ✅ trades table already exists")
            
            # Add trade_id column if it doesn't exist
            if 'trade_id' not in columns:
                print("  - Adding trade_id column to transactions...")
                connection.execute(text("""
                    ALTER TABLE transactions 
                    ADD COLUMN trade_id INTEGER
                """))
                print("  ✅ trade_id column added")
                
                # Add foreign key constraint
                print("  - Adding foreign key constraint...")
                connection.execute(text("""
                    ALTER TABLE transactions 
                    ADD CONSTRAINT fk_transactions_trade_id_trades 
                    FOREIGN KEY (trade_id) REFERENCES trades(id)
                """))
                print("  ✅ foreign key constraint added")
            else:
                print("  ✅ trade_id column already exists")
        
        # Verify the changes
        print("\n🔍 Verifying schema changes...")
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        columns = [col['name'] for col in inspector.get_columns('transactions')]
        
        print(f"trades table exists: {'trades' in tables}")
        print(f"trade_id column exists: {'trade_id' in columns}")
        
        if 'trades' in tables and 'trade_id' in columns:
            print("\n✅ Schema fix completed successfully!")
            return True
        else:
            print("\n❌ Schema fix failed!")
            return False
            
    except Exception as e:
        print(f"❌ Error fixing schema: {e}")
        return False

def main():
    """Main execution function"""
    print("🚀 Starting Direct Schema Fix")
    print("=" * 50)
    
    success = fix_schema_directly()
    
    if success:
        print("\n🎯 Next Steps:")
        print("1. Test the SOL finality checker")
        print("2. Verify all application functionality")
        print("3. Address migration conflicts later")
        print("4. Consider updating migration state: docker exec dwt_backend-wallet-1 alembic stamp fb84c1febfb6")
    else:
        print("\n❌ Schema fix failed. Please check the error messages above.")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
