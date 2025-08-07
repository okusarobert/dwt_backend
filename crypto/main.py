import asyncio
from util import check_pending, handle_new_block, new_payment_handler, get_address_statistics, get_all_crypto_addresses
from shared.crypto.util import broadcast_tx_flow, broadcast_tx_flow_sync, coin_info, get_divisibility, prepare_tx
from shared.logger import setup_logging
from bitcart import APIManager, COINS
import logging
import datetime
import json
from worker import start_worker, stop_worker, get_worker

logger = setup_logging()

logger.info("Starting crypto worker")


async def load_cryptos(cryptos):
    # Log address statistics at startup
    logger.info("[WORKER] Loading address statistics...")
    stats = get_address_statistics()
    all_addresses = get_all_crypto_addresses()
    
    logger.info(f"[WORKER] Address Statistics: {stats}")
    logger.info(f"[WORKER] Addresses by Currency: {all_addresses}")
    
    # Log addresses for each crypto
    for crypto in cryptos:
        addresses = all_addresses.get(crypto, [])
        logger.info(f"[WORKER] {crypto}: {len(addresses)} addresses to monitor")
    
    # Use the reliable polling system (Bitcart SDK has authentication issues)
    logger.info("[WORKER] Using reliable polling system...")
    await fallback_to_old_system(cryptos)

async def start_bitcart_sdk_worker(cryptos):
    """Start the Bitcart SDK-based worker"""
    try:
        from bitcart_sdk_worker import BitcartSDKWorker
        
        worker = BitcartSDKWorker()
        await worker.start_monitoring()
        
    except ImportError as e:
        logger.error(f"[WORKER] Could not import Bitcart SDK: {e}")
        logger.info("[WORKER] Falling back to polling system...")
        await fallback_to_old_system(cryptos)
    except Exception as e:
        logger.error(f"[WORKER] Error starting Bitcart SDK worker: {e}")
        import traceback
        logger.error(f"[WORKER] Traceback: {traceback.format_exc()}")
        logger.info("[WORKER] Falling back to polling system...")
        await fallback_to_old_system(cryptos)


async def fallback_to_old_system(cryptos):
    """Fallback to the old polling system if worker fails"""
    crypto_settings = {}
    nodes = {}
    manager = APIManager({cpt.upper(): [] for cpt in cryptos})
    
    # Get addresses for monitoring
    all_addresses = get_all_crypto_addresses()
    
    for crypto in cryptos:
        env_name = crypto.upper()
        logger.info(f"[FALLBACK] Processing crypto: {crypto}, env_name: {env_name}")
        
        if env_name not in COINS:
            logger.warning(f"[FALLBACK] {env_name} not found in COINS, skipping")
            continue
            
        crypto_settings[crypto] = coin_info(crypto)
        coin = COINS[env_name]
        creds = crypto_settings[crypto]["credentials"]
        nodes[crypto] = coin(**crypto_settings[crypto]["credentials"])
        
        # Get the addresses to monitor for this crypto
        addresses = all_addresses.get(crypto, [])
        if addresses:
            # Use the first address as the wallet key for monitoring
            wallet_key = addresses[0]
            logger.info(f"[FALLBACK] Loading wallet for {crypto} with address: {wallet_key}")
            manager.wallets[env_name][wallet_key] = nodes[crypto]
        else:
            logger.warning(f"[FALLBACK] No addresses found for {crypto}, using empty key")
            manager.wallets[env_name][""] = nodes[crypto]
    
    # Set up event handlers
    manager.add_event_handler("new_transaction", new_payment_handler)
    manager.add_event_handler("new_block", handle_new_block)

    logger.info("[FALLBACK] Starting websocket connection...")
    try:
        # Add timeout to prevent hanging
        import asyncio
        await asyncio.wait_for(
            manager.start_websocket(reconnect_callback=check_pending, force_connect=True),
            timeout=30.0  # 30 second timeout
        )
        logger.info("[FALLBACK] Websocket connection started")
    except asyncio.TimeoutError:
        logger.error("[FALLBACK] WebSocket connection timed out after 30 seconds")
        logger.info("[FALLBACK] Continuing with polling system...")
    except Exception as e:
        logger.error(f"[FALLBACK] Error starting websocket connection: {e}")
        import traceback
        logger.error(f"[FALLBACK] Traceback: {traceback.format_exc()}")
        # Continue with polling even if websocket fails
        logger.info("[FALLBACK] Continuing with polling system...")


async def shutdown_crypto():
    """Gracefully shutdown the crypto service"""
    logger.info("[WORKER] Shutting down crypto service...")
    try:
        await stop_worker()
        logger.info("[WORKER] Worker stopped")
    except Exception as e:
        logger.error(f"[WORKER] Error stopping worker: {e}")


if __name__ == "__main__":
    logger.info("[WORKER] Crypto worker is running")
    cryptos = [
        "BTC",    # Bitcoin
        # "ETH",    # Ethereum
        # "BNB",    # Binance Coin
        # "BSTY",   # GlobalBoost-Y (Boosty)
        # "LTC",    # Litecoin
        # "BCH",    # Bitcoin Cash
        # "SBCH",   # Smart Bitcoin Cash
        # "GRS",    # Groestlcoin
        # "POL",    # Polygon (MATIC)
        # "TRX",    # Tron
        # "XMR",    # Monero
        # "XRG"     # Ergon
    ]
    
    try:
        asyncio.run(load_cryptos(cryptos=cryptos))
    except KeyboardInterrupt:
        logger.info("[WORKER] Received interrupt signal")
        asyncio.run(shutdown_crypto())
    except Exception as e:
        logger.error(f"[WORKER] Unexpected error: {e}")
        asyncio.run(shutdown_crypto())
