from bitcart import BTC, APIManager
from decouple import config
from shared.crypto.util import coin_info

from shared.logger import setup_logging

logger = setup_logging()




def main():
    coin = coin_info("BTC")
    manager = APIManager(
        {"BTC": ["3afccbbc75cfbc8afd979d1508131a77ca2b649937b0ec4498326c7e1cf742d6"]},
        custom_params={"BTC": coin.get('credentials')}   )
    # btc = BTC(**coin.get('credentials'),
    #         #   xpub=["msxtM27m4i3iz1jb955uKCRtvggvnF1Z1T", "mt4Vd5HFw2C8BZDbEGDxdhAGYYdsJCazoh"]
    #           xpub="3afccbbc75cfbc8afd979d1508131a77ca2b649937b0ec4498326c7e1cf742d6"
    #           )
    
    # manager.wallets["BTC"]["mt4Vd5HFw2C8BZDbEGDxdhAGYYdsJCazoh"] = btc
    # balance = manager.BTC["mt4Vd5HFw2C8BZDbEGDxdhAGYYdsJCazoh"].balance()
    # isValid = btc.validate_key(
    #     "3afccbbc75cfbc8afd979d1508131a77ca2b649937b0ec4498326c7e1cf742d6")
    # logger.info(f"IS VALID: {isValid}")
    balance = manager.BTC["3afccbbc75cfbc8afd979d1508131a77ca2b649937b0ec4498326c7e1cf742d6"].balance()
    logger.info(f"BALANCE: {balance}")
    # @btc.on("new_block")
    # def new_block_handler(event, height):
	#     logger.info(f"{event}: Received block: {height}")

    # @btc.on("new_transaction")
    # def new_tx_handler(event, tx):
	#     logger.info(f"{event}: Received a new tx: {tx}")
     
    # # btc.add_event_handler("new_block", new_block_handler)
    # btc.start_websocket()
    # street intact pear medal agent video roof mansion surface brain cave keep

if __name__ == "__main__":
    main()