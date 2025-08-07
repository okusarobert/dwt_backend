import requests
from blockcypher import send_faucet_coins

def get_btc_balance():
    addresses = ["msxtM27m4i3iz1jb955uKCRtvggvnF1Z1T", "mt4Vd5HFw2C8BZDbEGDxdhAGYYdsJCazoh"]
    url = f"https://api.blockcypher.com/v1/btc/test3/addrs/{';'.join(addresses)}/balance"
    response = requests.get(url)
    print(response.json())
    
def my_send_faucet_coins():
    # Use BCY chain instead of btc-testnet
    # Note: This requires a BCY testnet address, not BTC testnet
    resp = send_faucet_coins(address_to_fund='mt4Vd5HFw2C8BZDbEGDxdhAGYYdsJCazoh',
                      satoshis=10000, api_key='1d2d23342b5c47a4bd3a6fa921f61cc6', coin_symbol='bcy')
    print(resp)

def test_blockcypher_api():
    """Test the BlockCypher API for UTXOs"""
    print("=== Testing BlockCypher API ===")
    
    # Test addresses
    addresses = ["msxtM27m4i3iz1jb955uKCRtvggvnF1Z1T", "mt4Vd5HFw2C8BZDbEGDxdhAGYYdsJCazoh"]
    
    for address in addresses:
        print(f"\n--- Checking address: {address} ---")
        
        # Get balance
        try:
            balance_url = f"https://api.blockcypher.com/v1/btc/test3/addrs/{address}/balance"
            balance_response = requests.get(balance_url)
            balance_data = balance_response.json()
            print(f"Balance: {balance_data}")
        except Exception as e:
            print(f"Balance API error: {e}")
        
        # Get UTXOs
        try:
            utxo_url = f"https://api.blockcypher.com/v1/btc/test3/addrs/{address}?unspentOnly=true"
            utxo_response = requests.get(utxo_url)
            utxo_data = utxo_response.json()
            print(f"UTXOs: {utxo_data}")
        except Exception as e:
            print(f"UTXO API error: {e}")

def test_spv_api():
    """Test the SPV balance API"""
    base_url = "http://localhost:5001"
    
    # Test status
    print("=== Testing SPV API Status ===")
    response = requests.get(f"{base_url}/status")
    print(f"Status: {response.json()}")
    
    # Test balance for tracked address
    print("\n=== Testing Balance API ===")
    addresses = ["tb1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4", "msxtM27m4i3iz1jb955uKCRtvggvnF1Z1T", "mt4Vd5HFw2C8BZDbEGDxdhAGYYdsJCazoh"]
    for address in addresses:
        response = requests.get(f"{base_url}/balance/{address}")
        print(f"Balance for {address}: {response.json()}")
    
    # Test UTXOs
    print("\n=== Testing UTXOs API ===")
    for address in addresses:
        response = requests.get(f"{base_url}/utxos/{address}")
        print(f"UTXOs for {address}: {response.json()}")
    
    # Test BlockCypher API for comparison
    print("\n=== Testing BlockCypher API ===")
    try:
        btc_addresses = ["msxtM27m4i3iz1jb955uKCRtvggvnF1Z1T", "mt4Vd5HFw2C8BZDbEGDxdhAGYYdsJCazoh"]
        url = f"https://api.blockcypher.com/v1/btc/test3/addrs/{';'.join(btc_addresses)}/balance"
        response = requests.get(url)
        print(f"BlockCypher balance: {response.json()}")
    except Exception as e:
        print(f"BlockCypher API error: {e}")

if __name__ == "__main__":
    # get_btc_balance()
    # my_send_faucet_coins()
    test_blockcypher_api()
