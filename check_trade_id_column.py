#!/usr/bin/env python3
"""
Script to check if trade_id column exists in transactions table
"""
import os
import sys
from sqlalchemy import create_engine, inspect, text

# Database connection
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/dwt_backend"

def check_trade_id_column():
    """Check if trade_id column exists in transactions table"""
    try:
        engine = create_engine(DATABASE_URL)
        inspector = inspect(engine)
        
        # Get all columns in transactions table
        columns = inspector.get_columns('transactions')
        column_names = [col['name'] for col in columns]
        
        print("Columns in transactions table:")
        for col in column_names:
            print("  - {}".format(col))
        
        if 'trade_id' in column_names:
            print("\n✅ trade_id column EXISTS in transactions table")
        else:
            print("\n❌ trade_id column DOES NOT EXIST in transactions table")
            
        # Check if trades table exists
        tables = inspector.get_table_names()
        if 'trades' in tables:
            print("✅ trades table EXISTS")
        else:
            print("❌ trades table DOES NOT EXIST")
            
    except Exception as e:
        print("Error: {}".format(e))

if __name__ == "__main__":
    check_trade_id_column()
