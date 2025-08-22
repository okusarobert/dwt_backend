#!/usr/bin/env python3
"""
Generate a comprehensive migration for Trade model fields.
"""

# Define all Trade model fields based on the current model definition
TRADE_MODEL_FIELDS = [
    # Core fields
    ('id', 'INTEGER', False, True),  # primary key
    ('created_at', 'TIMESTAMP WITHOUT TIME ZONE', False, False),
    ('updated_at', 'TIMESTAMP WITHOUT TIME ZONE', False, False),
    
    # Trade details
    ('trade_type', 'USER-DEFINED', False, False),  # Enum
    ('status', 'USER-DEFINED', False, False),  # Enum
    
    # User and account
    ('user_id', 'INTEGER', False, False),
    ('account_id', 'INTEGER', False, False),
    
    # Crypto details
    ('crypto_currency', 'VARCHAR(10)', False, False),
    ('crypto_amount', 'NUMERIC(20,8)', False, False),
    
    # Fiat details  
    ('fiat_currency', 'VARCHAR(3)', False, False),
    ('fiat_amount', 'NUMERIC(15,2)', False, False),
    
    # Exchange rate and fees
    ('exchange_rate', 'NUMERIC(20,8)', False, False),
    ('fee_amount', 'NUMERIC(15,2)', True, False),
    ('fee_currency', 'VARCHAR(3)', True, False),
    
    # Payment method
    ('payment_method', 'USER-DEFINED', False, False),  # Enum
    ('payment_provider', 'USER-DEFINED', True, False),  # Enum
    
    # Payment details
    ('payment_reference', 'VARCHAR(128)', True, False),
    ('payment_status', 'VARCHAR(32)', True, False),
    ('payment_metadata', 'JSON', True, False),
    
    # Voucher details
    ('voucher_id', 'INTEGER', True, False),
    
    # Missing payment detail fields that should exist
    ('mobile_money_provider', 'VARCHAR(32)', True, False),
    ('bank_name', 'VARCHAR(64)', True, False),
    ('account_name', 'VARCHAR(128)', True, False),
    ('account_number', 'VARCHAR(32)', True, False),
    ('deposit_reference', 'VARCHAR(64)', True, False),
    ('phone_number', 'VARCHAR(20)', True, False),
    
    # Transaction references
    ('crypto_transaction_id', 'INTEGER', True, False),
    ('fiat_transaction_id', 'INTEGER', True, False),
    
    # Metadata
    ('description', 'VARCHAR(255)', True, False),
    ('trade_metadata', 'JSON', True, False),
    
    # Timestamps
    ('payment_received_at', 'TIMESTAMP WITHOUT TIME ZONE', True, False),
    ('completed_at', 'TIMESTAMP WITHOUT TIME ZONE', True, False),
    ('cancelled_at', 'TIMESTAMP WITHOUT TIME ZONE', True, False),
    
    # Unified amount fields for precision
    ('crypto_amount_smallest_unit', 'NUMERIC(78,0)', True, False),
    ('fiat_amount_smallest_unit', 'NUMERIC(78,0)', True, False),
    ('fee_amount_smallest_unit', 'NUMERIC(78,0)', True, False),
    ('precision_config', 'JSON', True, False),
]

def generate_migration_code():
    """Generate the migration code to add missing columns."""
    
    print("# Generated migration code for Trade table")
    print("# Add this to your Alembic migration file")
    print()
    print("def upgrade() -> None:")
    print("    # Get database connection to check existing columns")
    print("    bind = op.get_bind()")
    print("    inspector = sa.inspect(bind)")
    print("    existing_columns = [col['name'] for col in inspector.get_columns('trades')]")
    print()
    print("    # Define all required columns")
    print("    required_columns = [")
    
    for field_name, field_type, nullable, is_pk in TRADE_MODEL_FIELDS:
        if is_pk:
            continue  # Skip primary key
        
        # Convert field type to SQLAlchemy type
        if field_type.startswith('VARCHAR'):
            size = field_type.split('(')[1].split(')')[0]
            sa_type = f"sa.String({size})"
        elif field_type.startswith('NUMERIC'):
            params = field_type.split('(')[1].split(')')[0]
            if ',' in params:
                precision, scale = params.split(',')
                sa_type = f"sa.Numeric({precision}, {scale})"
            else:
                sa_type = f"sa.Numeric({params}, 0)"
        elif field_type == 'INTEGER':
            sa_type = "sa.Integer"
        elif field_type == 'JSON':
            sa_type = "sa.JSON()"
        elif field_type == 'TIMESTAMP WITHOUT TIME ZONE':
            sa_type = "sa.DateTime"
        elif field_type == 'USER-DEFINED':
            # These are enums, skip for now as they need special handling
            continue
        else:
            sa_type = f"sa.String(255)"  # fallback
        
        print(f"        ('{field_name}', {sa_type}, {nullable}),")
    
    print("    ]")
    print()
    print("    # Add missing columns")
    print("    for column_name, column_type, nullable in required_columns:")
    print("        if column_name not in existing_columns:")
    print("            op.add_column('trades', sa.Column(column_name, column_type, nullable=nullable))")
    print("            print(f'Added column: {column_name}')")
    print("        else:")
    print("            print(f'Column already exists: {column_name}')")
    print()
    
    print("def downgrade() -> None:")
    print("    # Remove added columns (be careful with this in production)")
    print("    columns_to_remove = [")
    for field_name, _, _, is_pk in TRADE_MODEL_FIELDS:
        if is_pk or field_name in ['id', 'created_at', 'updated_at', 'trade_type', 'status', 'user_id', 'account_id']:
            continue  # Don't remove core fields
        print(f"        '{field_name}',")
    print("    ]")
    print("    for column_name in columns_to_remove:")
    print("        try:")
    print("            op.drop_column('trades', column_name)")
    print("        except:")
    print("            pass  # Column might not exist")

if __name__ == "__main__":
    generate_migration_code()
