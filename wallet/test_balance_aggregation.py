#!/usr/bin/env python3
"""
Test Balance Aggregation System

This script tests the multi-chain balance aggregation functionality,
including USDT/USDC aggregation across different blockchains and
total portfolio value calculations.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db.connection import get_session
from db.wallet import Account, AccountType, CryptoAddress
from shared.balance_aggregation import BalanceAggregationService
from shared.currency_precision import AmountConverter
from db.models import User, UserRole
import json

def create_test_user(session, user_id=1):
    """Create a test user if it doesn't exist"""
    
    print(f"🔧 Creating test user with ID {user_id}...")
    
    # Check if user already exists by email (more reliable than ID)
    existing_user = session.query(User).filter_by(email=f"test{user_id}@example.com").first()
    if existing_user:
        print(f"   ⏭️  User {existing_user.id} already exists with email {existing_user.email}")
        return existing_user
    
    # Create new test user
    test_user = User(
        first_name="Test",
        last_name="User",
        email=f"test{user_id}@example.com",
        phone_number="+1234567890",
        encrypted_pwd="test_hash_123",
        ref_code=f"TEST{user_id:03d}",
        role=UserRole.USER,
        country="US"
    )
    
    session.add(test_user)
    session.flush()  # Flush to get the ID without committing
    
    print(f"   ✅ Created test user {test_user.id} with email {test_user.email}")
    return test_user

def create_test_accounts(session, test_user):
    """Create test accounts for multi-chain balance aggregation testing"""
    
    print("🔧 Creating test accounts for balance aggregation...")
    
    # Test accounts to create
    test_accounts = [
        # Native currencies
        {'currency': 'ETH', 'balance_eth': 2.5, 'parent_currency': None},
        {'currency': 'BTC', 'balance_btc': 0.1, 'parent_currency': None},
        {'currency': 'TRX', 'balance_trx': 1000.0, 'parent_currency': None},
        {'currency': 'BNB', 'balance_bnb': 5.0, 'parent_currency': None},
        
        # USDT on different chains
        {'currency': 'USDT', 'balance_usdt': 500.0, 'parent_currency': 'ETH'},  # USDT-ERC20
        {'currency': 'USDT', 'balance_usdt': 300.0, 'parent_currency': 'TRX'},  # USDT-TRC20
        {'currency': 'USDT', 'balance_usdt': 200.0, 'parent_currency': 'BNB'},  # USDT-BEP20
        
        # USDC on different chains
        {'currency': 'USDC', 'balance_usdc': 400.0, 'parent_currency': 'ETH'},  # USDC-ERC20
        {'currency': 'USDC', 'balance_usdc': 100.0, 'parent_currency': 'TRX'},  # USDC-TRC20
    ]
    
    created_accounts = []
    
    # Get the highest existing account number to avoid duplicates
    import re
    max_account_num = 0
    existing_accounts = session.query(Account).filter(Account.account_number.like('TEST%')).all()
    for acc in existing_accounts:
        match = re.search(r'TEST(\d+)', acc.account_number)
        if match:
            max_account_num = max(max_account_num, int(match.group(1)))
    
    account_counter = max_account_num + 1
    
    for account_data in test_accounts:
        currency = account_data['currency']
        parent_currency = account_data['parent_currency']
        
        # Check if account already exists for this specific combination
        query = session.query(Account).filter(
            Account.user_id == test_user.id,
            Account.currency == currency,
            Account.account_type == AccountType.CRYPTO
        )
        
        if parent_currency:
            # For tokens, we need to check if an account with this parent currency exists
            existing_accounts = query.all()
            account_exists = False
            for acc in existing_accounts:
                if acc.precision_config and acc.precision_config.get('parent_currency') == parent_currency:
                    print(f"   ⏭️  Account for {currency} on {parent_currency} already exists (ID: {acc.id})")
                    account_exists = True
                    break
            if account_exists:
                continue
        else:
            # For native currencies, check if any account exists
            existing_account = query.first()
            if existing_account:
                print(f"   ⏭️  Account for {currency} already exists (ID: {existing_account.id})")
                continue
        
        # Create new account
        precision_config = None
        if parent_currency:
            precision_config = {
                'parent_currency': parent_currency,
                'decimals': 6 if currency in ['USDT', 'USDC'] else 18
            }
        
        account = Account(
            user_id=test_user.id,  # Use the actual user ID from the created user
            currency=currency,
            account_type=AccountType.CRYPTO,
            account_number=f"TEST{account_counter:06d}",
            label=f"{currency} Account" + (f" ({parent_currency})" if parent_currency else ""),
            balance=0.0,
            locked_amount=0.0,
            precision_config=precision_config
        )
        
        account_counter += 1
        
        # Set balance in smallest units
        balance_key = f"balance_{currency.lower()}"
        if balance_key in account_data:
            balance_standard = account_data[balance_key]
            
            # Convert to smallest units
            if currency in ['USDT', 'USDC']:
                decimals = precision_config.get('decimals', 6) if precision_config else 6
                balance_smallest = int(balance_standard * (10 ** decimals))
            elif currency == 'ETH':
                balance_smallest = int(balance_standard * 10**18)
            elif currency == 'BTC':
                balance_smallest = int(balance_standard * 10**8)
            elif currency == 'TRX':
                balance_smallest = int(balance_standard * 10**6)
            elif currency == 'BNB':
                balance_smallest = int(balance_standard * 10**18)
            else:
                balance_smallest = int(balance_standard * 10**8)
            
            account.crypto_balance_smallest_unit = balance_smallest
        
        session.add(account)
        created_accounts.append(account)
        
        chain_info = f" on {parent_currency}" if parent_currency else ""
        balance_info = f" with {account_data.get(balance_key, 0)} {currency}"
        print(f"   ✅ Created {currency} account{chain_info}{balance_info}")
    
    session.commit()
    print(f"✅ Created {len(created_accounts)} test accounts")
    return created_accounts

def test_balance_aggregation(user_id=1):
    """Test the balance aggregation functionality"""
    
    print("\n🧪 Testing Balance Aggregation System")
    print("=" * 50)
    
    session = get_session()
    
    try:
        # Create test user first
        test_user = create_test_user(session, user_id)
        
        # Create test accounts
        create_test_accounts(session, test_user)
        
        # Initialize balance aggregation service
        balance_service = BalanceAggregationService(session)
        
        print("\n📊 Testing Aggregated Balances...")
        
        # Get aggregated balances using the actual user ID
        aggregated_balances = balance_service.get_user_aggregated_balances(test_user.id)
        
        print(f"\n🔍 Found {len(aggregated_balances)} currencies with balances:")
        
        for currency, balance_info in aggregated_balances.items():
            total_balance = balance_info['total_balance']
            chains = balance_info['chains']
            
            print(f"\n💰 {currency}: {total_balance:.6f}")
            
            if len(chains) > 1:
                print(f"   📡 Multi-chain token across {len(chains)} chains:")
                for chain, chain_info in chains.items():
                    print(f"      • {chain}: {chain_info['balance']:.6f}")
            else:
                chain_name = list(chains.keys())[0] if chains else currency
                print(f"   🔗 Single chain: {chain_name}")
            
            # Show addresses
            if balance_info['addresses']:
                print(f"   📍 Addresses: {len(balance_info['addresses'])}")
                for addr in balance_info['addresses']:
                    print(f"      • {addr['chain']}: {addr['address'][:10]}...")
        
        print("\n💼 Testing Portfolio Value Calculation...")
        
        # Mock prices for testing
        mock_prices = {
            'BTC': 45000.0,
            'ETH': 2500.0,
            'BNB': 300.0,
            'TRX': 0.08,
            'USDT': 1.0,
            'USDC': 1.0,
            'SOL': 100.0,
            'LTC': 70.0
        }
        
        portfolio_value = balance_service.get_portfolio_value(test_user.id, mock_prices, 'UGX')
        
        print(f"\n💵 Portfolio Value:")
        print(f"   Total USD: ${portfolio_value['total_value_usd']:,.2f}")
        print(f"   Total UGX: UGX {portfolio_value['total_value_target']:,.0f}")
        
        print(f"\n📈 Currency Breakdown:")
        for currency, value_info in portfolio_value['currencies'].items():
            balance = value_info['balance']
            value_usd = value_info['value_usd']
            print(f"   {currency}: {balance:.6f} = ${value_usd:,.2f}")
            
            # Show chain breakdown for multi-chain tokens
            if 'chains' in value_info and len(value_info['chains']) > 1:
                for chain, chain_info in value_info['chains'].items():
                    chain_balance = chain_info['balance']
                    chain_value = chain_balance * value_info['price_usd']
                    print(f"      └─ {chain}: {chain_balance:.6f} = ${chain_value:,.2f}")
        
        print("\n📋 Testing Balance Summary...")
        
        balance_summary = balance_service.get_balance_summary(test_user.id)
        
        print(f"\n📊 Balance Summary:")
        print(f"   Total currencies: {balance_summary['total_currencies']}")
        print(f"   Multi-chain tokens: {len(balance_summary['multi_chain_tokens'])}")
        
        if balance_summary['multi_chain_tokens']:
            print(f"\n🔗 Multi-chain Token Details:")
            for currency, token_info in balance_summary['multi_chain_tokens'].items():
                total = token_info['total_balance']
                chains = token_info['chains']
                print(f"   {currency}: {total:.6f} across {len(chains)} chains")
                for chain, balance in chains.items():
                    percentage = (balance / total) * 100
                    print(f"      • {chain}: {balance:.6f} ({percentage:.1f}%)")
        
        print("\n✅ Balance aggregation test completed successfully!")
        
        return {
            'aggregated_balances': aggregated_balances,
            'portfolio_value': portfolio_value,
            'balance_summary': balance_summary
        }
        
    except Exception as e:
        print(f"\n❌ Error during balance aggregation test: {e}")
        import traceback
        traceback.print_exc()
        return None
        
    finally:
        session.close()

def test_api_response_format():
    """Test the API response format"""
    
    print("\n🌐 Testing API Response Format")
    print("=" * 40)
    
    # This would typically be done with actual API calls
    # For now, we'll simulate the response structure
    
    test_result = test_balance_aggregation(user_id=1)
    
    if test_result:
        print("\n📤 Simulated API Response Structure:")
        
        api_response = {
            "success": True,
            "balances": {},
            "total_value_usd": test_result['portfolio_value']['total_value_usd'],
            "total_value_ugx": test_result['portfolio_value']['total_value_target'],
            "portfolio_breakdown": test_result['portfolio_value']['currencies'],
            "aggregation_summary": test_result['balance_summary']
        }
        
        # Format balances for API response
        for currency, balance_info in test_result['aggregated_balances'].items():
            api_response['balances'][currency] = {
                'balance': balance_info['total_balance'],
                'chains': balance_info['chains'],
                'all_addresses': balance_info['addresses']
            }
        
        print(json.dumps(api_response, indent=2, default=str))

if __name__ == "__main__":
    print("🚀 Starting Balance Aggregation System Test")
    
    # Test with user ID 1 (adjust as needed)
    test_user_id = 1
    
    try:
        # Run balance aggregation test
        test_balance_aggregation(test_user_id)
        
        # Test API response format
        test_api_response_format()
        
        print("\n🎉 All tests completed!")
        
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
