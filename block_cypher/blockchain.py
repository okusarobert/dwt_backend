from blockcypher import get_blockchain_overview

def main():
    overview = get_blockchain_overview(coin_symbol='btc-testnet')
    print(overview)


if __name__ == "__main__":
    main()