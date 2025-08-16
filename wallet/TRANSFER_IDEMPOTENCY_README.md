# Transfer Idempotency Implementation

This document describes the implementation of idempotency for the transfer functionality in the wallet service.

## Overview

Idempotency ensures that the same transfer request (identified by a unique `reference_id`) cannot be processed multiple times, preventing duplicate transfers and ensuring data consistency.

## Key Components

### 1. Database Schema

- **Unique Constraint**: Added unique constraint on `reference_id` field in the `transactions` table
- **Migration**: `add_reference_id_unique_constraint.py` adds the constraint
- **Index**: Existing index on `reference_id` for performance

### 2. Transfer Service

The `TransferService` class implements idempotency checks:

- **`_get_existing_transaction_by_reference()`**: Checks for existing transactions with the same `reference_id`
- **`_build_idempotent_response()`**: Builds response for duplicate requests
- **Idempotency Check**: Added at the beginning of `transfer_between_users()` method

### 3. API Endpoints

#### Regular Transfer (`/wallet/transfer`)
- **Required Fields**: `currency`, `to_email`, `amount`, `reference_id`
- **Idempotency**: Automatically enforced via service layer
- **Response**: Returns existing transaction details if `reference_id` already exists

#### Admin Transfer (`/admin/wallets/transfer`)
- **Required Fields**: `from_account_number`, `to_account_number`, `amount`
- **Optional Fields**: `reference_id` (for idempotency)
- **Idempotency**: Uses transfer service for consistency

## How It Works

### 1. First Request
```
POST /wallet/transfer
{
  "currency": "UGX",
  "to_email": "user@example.com",
  "amount": 100.0,
  "reference_id": "unique_ref_123",
  "description": "Payment for services"
}
```

**Response**: Transfer processed, new transaction created

### 2. Duplicate Request (Same `reference_id`)
```
POST /wallet/transfer
{
  "currency": "UGX",
  "to_email": "user@example.com",
  "amount": 100.0,
  "reference_id": "unique_ref_123",  // Same reference_id
  "description": "Payment for services"
}
```

**Response**: Idempotent response with existing transaction details
```json
{
  "success": true,
  "transaction_id": 12345,
  "reference_id": "unique_ref_123",
  "status": "idempotent",
  "message": "Transfer already processed with this reference_id",
  "original_transaction_date": "2024-01-01T12:00:00"
}
```

### 3. New Request (Different `reference_id`)
```
POST /wallet/transfer
{
  "currency": "UGX",
  "to_email": "user@example.com",
  "amount": 100.0,
  "reference_id": "unique_ref_456",  // Different reference_id
  "description": "Payment for services"
}
```

**Response**: New transfer processed, new transaction created

## Implementation Details

### Database Migration

```sql
-- Adds unique constraint on reference_id
ALTER TABLE transactions ADD CONSTRAINT uq_transaction_reference_id UNIQUE (reference_id);
```

### Service Layer Logic

```python
def transfer_between_users(self, from_user_id, to_email, amount, currency, reference_id, description):
    # 0. Check for idempotency if reference_id is provided
    if reference_id:
        existing_transaction = self._get_existing_transaction_by_reference(reference_id)
        if existing_transaction:
            logger.info(f"Idempotency: Found existing transaction with reference_id {reference_id}")
            return self._build_idempotent_response(existing_transaction, from_user_id, to_email, amount, currency)
    
    # ... rest of transfer logic
```

### Error Handling

- **Database Constraint Violation**: Handled gracefully with rollback
- **Invalid Reference ID**: Validated at API level (non-empty string)
- **Missing Reference ID**: Required field validation

## Best Practices

### 1. Reference ID Generation

- Use unique, deterministic identifiers
- Include timestamp or sequence numbers
- Avoid random UUIDs for business logic
- Examples:
  - `payment_20240101_001`
  - `transfer_user123_20240101_120000`
  - `order_12345_payment`

### 2. Client Implementation

```python
import uuid
import time

def generate_reference_id(user_id, order_id):
    """Generate unique reference ID for transfers"""
    timestamp = int(time.time())
    return f"transfer_{user_id}_{order_id}_{timestamp}"

# Usage
reference_id = generate_reference_id(123, "order_456")
```

### 3. Retry Logic

```python
def make_transfer_with_retry(payload, max_retries=3):
    """Make transfer request with retry logic"""
    for attempt in range(max_retries):
        try:
            response = requests.post("/wallet/transfer", json=payload)
            if response.status_code == 201:
                return response.json()
            elif response.status_code == 200 and response.json().get("status") == "idempotent":
                # Transfer already processed, return existing result
                return response.json()
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            time.sleep(2 ** attempt)  # Exponential backoff
```

## Testing

### Test Script

Run the test script to verify idempotency:

```bash
cd wallet
python test_transfer_idempotency.py
```

### Manual Testing

1. **Apply Migration**:
   ```bash
   alembic upgrade head
   ```

2. **Test Regular Transfer**:
   ```bash
   curl -X POST /wallet/transfer \
     -H "Authorization: Bearer <token>" \
     -H "Content-Type: application/json" \
     -d '{
       "currency": "UGX",
       "to_email": "test@example.com",
       "amount": 100.0,
       "reference_id": "test_ref_123"
     }'
   ```

3. **Test Duplicate**:
   ```bash
   # Same request again
   curl -X POST /wallet/transfer \
     -H "Authorization: Bearer <token>" \
     -H "Content-Type: application/json" \
     -d '{
       "currency": "UGX",
       "to_email": "test@example.com",
       "amount": 100.0,
       "reference_id": "test_ref_123"
     }'
   ```

## Benefits

1. **Prevents Duplicate Transfers**: Same request cannot be processed twice
2. **Improves Reliability**: Safe to retry failed requests
3. **Better User Experience**: Consistent responses for duplicate requests
4. **Data Integrity**: Maintains transaction consistency
5. **Audit Trail**: Clear tracking of original vs. duplicate requests

## Limitations

1. **Reference ID Required**: All transfers must include a `reference_id`
2. **Database Constraint**: Relies on database-level uniqueness
3. **Global Uniqueness**: Reference IDs must be unique across all transfers
4. **No Partial Updates**: Cannot modify existing transfers

## Future Enhancements

1. **Reference ID Expiration**: Add TTL for old reference IDs
2. **Batch Transfers**: Support for bulk transfer idempotency
3. **Reference ID Validation**: Custom validation rules
4. **Metrics**: Track idempotency usage and effectiveness
5. **Cleanup**: Automated cleanup of old reference IDs
