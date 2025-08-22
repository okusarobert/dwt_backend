#!/usr/bin/env python3
"""
Schema audit script to compare Trade model definition with actual database schema.
This helps identify missing columns that need to be added via migration.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import inspect, create_engine
from db.wallet import Trade
from db.connection import engine

def audit_trade_schema():
    """Compare Trade model fields with actual database columns."""
    
    # Get database connection
    inspector = inspect(engine)
    
    # Get actual database columns
    try:
        db_columns = {col['name']: col for col in inspector.get_columns('trades')}
    except Exception as e:
        print(f"Error getting database columns: {e}")
        return
    
    # Get model fields from Trade class
    model_columns = {}
    for attr_name in dir(Trade):
        attr = getattr(Trade, attr_name)
        if hasattr(attr, 'property') and hasattr(attr.property, 'columns'):
            column = attr.property.columns[0]
            model_columns[attr_name] = {
                'name': attr_name,
                'type': str(column.type),
                'nullable': column.nullable,
                'default': column.default
            }
    
    # Add inherited timestamp fields
    model_columns.update({
        'created_at': {'name': 'created_at', 'type': 'TIMESTAMP', 'nullable': False},
        'updated_at': {'name': 'updated_at', 'type': 'TIMESTAMP', 'nullable': False}
    })
    
    print("=== TRADE SCHEMA AUDIT ===\n")
    
    # Find missing columns (in model but not in database)
    missing_in_db = []
    for field_name, field_info in model_columns.items():
        if field_name not in db_columns:
            missing_in_db.append(field_name)
    
    # Find extra columns (in database but not in model)
    extra_in_db = []
    for col_name in db_columns:
        if col_name not in model_columns:
            extra_in_db.append(col_name)
    
    print("📊 SUMMARY:")
    print(f"  Model fields: {len(model_columns)}")
    print(f"  Database columns: {len(db_columns)}")
    print(f"  Missing in DB: {len(missing_in_db)}")
    print(f"  Extra in DB: {len(extra_in_db)}")
    
    if missing_in_db:
        print("\n❌ MISSING IN DATABASE:")
        for field in missing_in_db:
            field_info = model_columns[field]
            print(f"  - {field} ({field_info['type']}, nullable={field_info['nullable']})")
    
    if extra_in_db:
        print("\n➕ EXTRA IN DATABASE (not in model):")
        for col in extra_in_db:
            col_info = db_columns[col]
            print(f"  - {col} ({col_info['type']})")
    
    print("\n📋 ALL MODEL FIELDS:")
    for field_name in sorted(model_columns.keys()):
        field_info = model_columns[field_name]
        status = "✅" if field_name in db_columns else "❌"
        print(f"  {status} {field_name} ({field_info['type']})")
    
    print("\n📋 ALL DATABASE COLUMNS:")
    for col_name in sorted(db_columns.keys()):
        col_info = db_columns[col_name]
        status = "✅" if col_name in model_columns else "➕"
        print(f"  {status} {col_name} ({col_info['type']})")
    
    return missing_in_db, extra_in_db, model_columns, db_columns

if __name__ == "__main__":
    audit_trade_schema()
