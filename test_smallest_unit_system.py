#!/usr/bin/env python3
"""
Test script for the Smallest Unit Crypto Amount System

This demonstrates how crypto amounts are stored in smallest units (wei, satoshis, etc.)
to avoid precision issues.
"""

from decimal import Decimal
from db.crypto_precision import (
    CryptoPrecisionManager, 
    CryptoAmountConverter,
    to_smallest_unit,
    from_smallest_unit,
    format_smallest_unit_amount,
    validate_smallest_unit_amount,
    get_smallest_unit_name
)

def test_ethereum_amounts():
    """Test Ethereum amounts in wei"""
    print("🔵 Testing Ethereum (ETH) Amounts")
    print("=" * 50)
    
    # Test amounts
    test_amounts = [0.000000000000000001, 0.000001, 0.001, 0.1, 1.0, 10.0, 100.0]
    
    for amount in test_amounts:
        # Convert to wei
        wei_amount = to_smallest_unit(amount, "ETH")
        
        # Convert back to ETH
        eth_amount = from_smallest_unit(wei_amount, "ETH")
        
        # Format for display
        display_amount = format_smallest_unit_amount(wei_amount, "ETH")
        
        print(f"💰 {amount} ETH = {wei_amount:,} wei")
        print(f"   Converted back: {eth_amount} ETH")
        print(f"   Display format: {display_amount} ETH")
        print()

def test_bitcoin_amounts():
    """Test Bitcoin amounts in satoshis"""
    print("🟡 Testing Bitcoin (BTC) Amounts")
    print("=" * 50)
    
    # Test amounts
    test_amounts = [0.00000001, 0.000001, 0.001, 0.1, 1.0, 10.0, 100.0]
    
    for amount in test_amounts:
        # Convert to satoshis
        satoshi_amount = to_smallest_unit(amount, "BTC")
        
        # Convert back to BTC
        btc_amount = from_smallest_unit(satoshi_amount, "BTC")
        
        # Format for display
        display_amount = format_smallest_unit_amount(satoshi_amount, "BTC")
        
        print(f"💰 {amount} BTC = {satoshi_amount:,} satoshis")
        print(f"   Converted back: {btc_amount} BTC")
        print(f"   Display format: {display_amount} BTC")
        print()

def test_solana_amounts():
    """Test Solana amounts in lamports"""
    print("🟣 Testing Solana (SOL) Amounts")
    print("=" * 50)
    
    # Test amounts
    test_amounts = [0.000000001, 0.000001, 0.001, 0.1, 1.0, 10.0, 100.0]
    
    for amount in test_amounts:
        # Convert to lamports
        lamport_amount = to_smallest_unit(amount, "SOL")
        
        # Convert back to SOL
        sol_amount = from_smallest_unit(lamport_amount, "SOL")
        
        # Format for display
        display_amount = format_smallest_unit_amount(lamport_amount, "SOL")
        
        print(f"💰 {amount} SOL = {lamport_amount:,} lamports")
        print(f"   Converted back: {sol_amount} SOL")
        print(f"   Display format: {display_amount} SOL")
        print()

def test_precision_accuracy():
    """Test precision accuracy with very small amounts"""
    print("🎯 Testing Precision Accuracy")
    print("=" * 50)
    
    # Test very small amounts that would cause precision issues
    test_cases = [
        ("ETH", 0.000000000000000001),  # 1 wei
        ("BTC", 0.00000001),            # 1 satoshi
        ("SOL", 0.000000001),           # 1 lamport
        ("XRP", 0.000001),              # 1 drop
    ]
    
    for currency, amount in test_cases:
        smallest_unit_name = get_smallest_unit_name(currency)
        smallest_unit_amount = to_smallest_unit(amount, currency)
        converted_back = from_smallest_unit(smallest_unit_amount, currency)
        
        print(f"💰 {amount} {currency} = {smallest_unit_amount:,} {smallest_unit_name}")
        print(f"   Converted back: {converted_back} {currency}")
        print(f"   Precision maintained: {converted_back == Decimal(str(amount))}")
        print()

def test_validation():
    """Test amount validation"""
    print("✅ Testing Amount Validation")
    print("=" * 50)
    
    # Test valid amounts
    valid_amounts = [
        ("ETH", 1000000000000000000),  # 1 ETH in wei
        ("BTC", 100000000),            # 1 BTC in satoshis
        ("SOL", 1000000000),           # 1 SOL in lamports
    ]
    
    for currency, amount in valid_amounts:
        is_valid = validate_smallest_unit_amount(amount, currency)
        display_amount = format_smallest_unit_amount(amount, currency)
        print(f"✅ {amount:,} {get_smallest_unit_name(currency)} = {display_amount} {currency} (Valid: {is_valid})")
    
    print()
    
    # Test invalid amounts
    invalid_amounts = [
        ("ETH", -1),                   # Negative amount
        ("BTC", 2**256),               # Too large
    ]
    
    for currency, amount in invalid_amounts:
        is_valid = validate_smallest_unit_amount(amount, currency)
        print(f"❌ {amount} {get_smallest_unit_name(currency)} (Valid: {is_valid})")

def test_database_simulation():
    """Simulate how amounts would be stored in database"""
    print("🗄️ Database Storage Simulation")
    print("=" * 50)
    
    # Simulate account balances stored in smallest units
    account_data = [
        {"currency": "ETH", "balance_wei": 1500000000000000000, "locked_wei": 50000000000000000},
        {"currency": "BTC", "balance_satoshis": 250000000, "locked_satoshis": 10000000},
        {"currency": "SOL", "balance_lamports": 5000000000, "locked_lamports": 100000000},
    ]
    
    for account in account_data:
        currency = account["currency"]
        balance_smallest = account[f"balance_{get_smallest_unit_name(currency).lower()}"]
        locked_smallest = account[f"locked_{get_smallest_unit_name(currency).lower()}"]
        
        # Convert to standard units for display
        balance_standard = from_smallest_unit(balance_smallest, currency)
        locked_standard = from_smallest_unit(locked_smallest, currency)
        available_standard = balance_standard - locked_standard
        
        print(f"💰 {currency} Account:")
        print(f"   Balance: {balance_smallest:,} {get_smallest_unit_name(currency)} ({balance_standard} {currency})")
        print(f"   Locked: {locked_smallest:,} {get_smallest_unit_name(currency)} ({locked_standard} {currency})")
        print(f"   Available: {available_standard} {currency}")
        print()

def test_gas_fee_handling():
    """Test handling of gas fees in wei"""
    print("⛽ Gas Fee Handling")
    print("=" * 50)
    
    # Common gas prices and limits
    gas_scenarios = [
        {"gas_price_gwei": 20, "gas_limit": 21000, "description": "Standard ETH transfer"},
        {"gas_price_gwei": 50, "gas_limit": 21000, "description": "High gas ETH transfer"},
        {"gas_price_gwei": 100, "gas_limit": 100000, "description": "Smart contract interaction"},
    ]
    
    for scenario in gas_scenarios:
        gas_price_gwei = scenario["gas_price_gwei"]
        gas_limit = scenario["gas_limit"]
        
        # Convert gas price from Gwei to Wei
        gas_price_wei = to_smallest_unit(gas_price_gwei / 1_000_000_000, "ETH")  # Convert Gwei to ETH first
        
        # Calculate total gas cost in wei
        total_gas_cost_wei = gas_price_wei * gas_limit
        
        # Convert to ETH for display
        total_gas_cost_eth = from_smallest_unit(total_gas_cost_wei, "ETH")
        
        print(f"⛽ {scenario['description']}:")
        print(f"   Gas Price: {gas_price_gwei} Gwei = {gas_price_wei:,} Wei")
        print(f"   Gas Limit: {gas_limit:,}")
        print(f"   Total Cost: {total_gas_cost_wei:,} Wei = {total_gas_cost_eth} ETH")
        print()

def main():
    """Main test function"""
    print("🧪 Smallest Unit Crypto Amount System Test Suite")
    print("=" * 60)
    print()
    
    # Run all tests
    test_ethereum_amounts()
    test_bitcoin_amounts()
    test_solana_amounts()
    test_precision_accuracy()
    test_validation()
    test_database_simulation()
    test_gas_fee_handling()
    
    print("✅ All tests completed!")

if __name__ == "__main__":
    main() 