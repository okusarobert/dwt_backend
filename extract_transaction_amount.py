#!/usr/bin/env python3
"""
Script to extract transaction amounts received by a specific address
"""

import json
import requests

def extract_amount_received(transaction_data, target_address):
    """
    Extract the amount received by a specific address from transaction data
    
    Args:
        transaction_data (dict): Transaction data from the API
        target_address (str): The address to check for received amounts
    
    Returns:
        dict: Amount received information
    """
    total_received = 0
    received_outputs = []
    
    # Check if this is a single transaction or list of transactions
    if isinstance(transaction_data, list):
        transactions = transaction_data
    else:
        transactions = [transaction_data]
    
    for tx in transactions:
        if 'outputs' not in tx:
            continue
            
        for output in tx['outputs']:
            if output.get('address') == target_address:
                amount_satoshi = output.get('value', 0)
                amount_btc = amount_satoshi / 100000000  # Convert to BTC
                
                total_received += amount_satoshi
                received_outputs.append({
                    'txid': tx.get('txid', ''),
                    'output_n': output.get('output_n', 0),
                    'amount_satoshi': amount_satoshi,
                    'amount_btc': amount_btc,
                    'status': tx.get('status', 'unknown')
                })
    
    return {
        'address': target_address,
        'total_received_satoshi': total_received,
        'total_received_btc': total_received / 100000000,
        'received_outputs': received_outputs,
        'output_count': len(received_outputs)
    }

def get_transaction_amounts(address, api_url="http://localhost:5005"):
    """
    Get transaction amounts for a specific address using the SPV API
    
    Args:
        address (str): Bitcoin address to check
        api_url (str): SPV API base URL
    
    Returns:
        dict: Transaction amounts information
    """
    try:
        # Get transactions for the address
        response = requests.get(f"{api_url}/transactions/{address}")
        if response.status_code != 200:
            return {"error": f"Failed to get transactions: {response.status_code}"}
        
        transactions_data = response.json()
        transactions = transactions_data.get('transactions', [])
        
        if not transactions:
            return {
                "address": address,
                "message": "No transactions found for this address",
                "total_received_satoshi": 0,
                "total_received_btc": 0,
                "received_outputs": []
            }
        
        # Extract amounts received
        result = extract_amount_received(transactions, address)
        result['total_transactions'] = len(transactions)
        
        return result
        
    except Exception as e:
        return {"error": f"Error processing transactions: {str(e)}"}

if __name__ == "__main__":
    # Example usage
    address = "n43gfthwVPBopwaTMjmpMAT4Nqzf95NKcy"
    
    print(f"🔍 Analyzing transactions for address: {address}")
    print("=" * 60)
    
    result = get_transaction_amounts(address)
    
    if "error" in result:
        print(f"❌ Error: {result['error']}")
    else:
        print(f"📊 Results for {result['address']}:")
        print(f"   Total transactions analyzed: {result.get('total_transactions', 0)}")
        print(f"   Total received: {result['total_received_satoshi']:,} satoshis")
        print(f"   Total received: {result['total_received_btc']:.8f} BTC")
        print(f"   Received outputs: {result['output_count']}")
        
        if result['received_outputs']:
            print("\n📋 Received Outputs:")
            for i, output in enumerate(result['received_outputs'], 1):
                print(f"   {i}. TXID: {output['txid'][:16]}...")
                print(f"      Output #{output['output_n']}")
                print(f"      Amount: {output['amount_satoshi']:,} satoshis ({output['amount_btc']:.8f} BTC)")
                print(f"      Status: {output['status']}")
                print()
        else:
            print("\n❌ No funds received by this address in the analyzed transactions") 