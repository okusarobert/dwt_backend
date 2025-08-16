-- Add new columns
ALTER TABLE accounts ADD COLUMN crypto_balance_smallest_unit INTEGER;
ALTER TABLE accounts ADD COLUMN crypto_locked_amount_smallest_unit INTEGER;

-- Migrate existing data
UPDATE accounts 
SET crypto_balance_smallest_unit = balance * 100 
WHERE account_type = 'CRYPTO' AND currency IN ('USD', 'UGX');