import asyncio
import sys
from decimal import Decimal
from db.wallet import CryptoAddress, Transaction, Account
from db.models import Currency
from shared.crypto.util import coin_info, get_coin
from tronpy.abi import trx_abi
from tronpy.keys import to_base58check_address
from binance import Client
import traceback
import logging
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from decouple import config
# from asgiref.sync import sync_to_async
from db.connection import session
from shared.logger import setup_logging

BATCH_SIZE = 50  # Adjust as needed


# Helper: get SQLAlchemy session (to be injected or imported from your app context)
# from db.connection import session

logger = setup_logging()


def update_confirmations(transaction: Transaction):
    coin = get_coin(transaction.account.currency.code.upper())
    if not transaction.blockchain_txid:
        return False
    txn = coin.get_tx(transaction.blockchain_txid)
    txn_data = get_coin_txn_data(transaction.account.currency.code.upper(), txn)
    confirmations = txn_data.get('confirmations')
    is_eth_based = coin.is_eth_based
    if is_eth_based and confirmations >= 12:
        transaction.status = Transaction.TransactionStatus.COMPLETED
    else:
        if confirmations >= 6:
            transaction.status = Transaction.TransactionStatus.COMPLETED
        else:
            transaction.status = Transaction.TransactionStatus.AWAITING_CONFIRMATION
    transaction.confirmations = confirmations
    session.commit()
    return transaction


def process_transactions_confirmations(transactions):
    for transaction in transactions:
        update_confirmations(transaction)


def handle_new_transaction_db(currency_code, tx_data, tx_hash):
    address = tx_data.get('to_address')
    contract = tx_data.get('contract') or None
    # Find CryptoAddress by address and currency
    # currency = session.query(Currency).filter_by(code=currency_code).first()
    address_model = session.query(CryptoAddress).filter_by(address=address).first()
    if contract:
        address_model = session.query(CryptoAddress).filter_by(address=address, memo=contract).first()
    if not address_model:
        return False
    account = address_model.account
    # Check if transaction already exists
    txn_exists = session.query(Transaction).filter_by(blockchain_txid=tx_hash, account_id=account.id).first()
    if txn_exists:
        return False
    amount = tx_data.get('amount')
    from_address = tx_data.get('from_address')
    to_address = tx_data.get('to_address')
    confirmations = tx_data.get('confirmations')
    # Create Transaction
    txn = Transaction(
        account_id=account.id,
        amount=amount,
        type=Transaction.TransactionType.DEPOSIT,
        status=Transaction.TransactionStatus.AWAITING_CONFIRMATION if confirmations < 6 else Transaction.TransactionStatus.COMPLETED,
        address=address,
        blockchain_txid=tx_hash,
        confirmations=confirmations,
        required_confirmations=6,
        description=f"Deposit to {address}",
        metadata_json={"from_address": from_address, "to_address": to_address, "contract": contract}
    )
    session.add(txn)
    # Credit account if confirmed
    if confirmations >= 6:
        account.balance += Decimal(amount)
    session.commit()
    return txn


async def new_payment_handler(
    instance, event, tx
):
    logger.info(f"[NEW TRANSACTION] Received new tx: {tx}")
    currency = instance.coin_name.upper()
    logger.info(f"[NEW TRANSACTION] Processing for currency: {currency}")
    
    try:
        coin = get_coin(currency)
        txn = await coin.get_tx(tx)
        logger.info(f"[NEW TRANSACTION] Raw transaction data: {txn}")
        
        tx_data = get_coin_txn_data(currency, txn)
        logger.info(f"[NEW TRANSACTION] Processed TX DATA: {tx_data}")

        if tx_data and tx_data.get('amount', 0) > 0:
            await handle_new_transaction_db_async(session, currency, tx_data, tx)
            logger.info(f"[NEW TRANSACTION] Successfully processed transaction {tx} for {currency}")
        else:
            logger.warning(f"[NEW TRANSACTION] No valid transaction data for {tx} ({currency})")
            
    except Exception as e:
        error_msg = str(e)
        if "verbose transactions are currently unsupported" in error_msg and currency == "BTC":
            logger.info(f"[NEW TRANSACTION] Skipping BTC transaction {tx} due to verbose transaction limitation")
            logger.info(f"[NEW TRANSACTION] This transaction will be processed by the polling system instead")
        else:
            logger.error(f"[NEW TRANSACTION] Error processing transaction {tx} for {currency}: {e}")
            import traceback
            logger.error(f"[NEW TRANSACTION] Traceback: {traceback.format_exc()}")


def get_coin_txn_data(coin, tx):
    match coin:
        case "TRX":
            tx_type = tx.get('raw_data').get('contract')[0].get('type')
            to_address = ''
            from_address = ''
            amount = 0
            confirmations = tx.get('confirmations')
            contract = None
            match tx_type:
                case "TransferContract":
                    to_address = to_base58check_address(tx.get('raw_data').get('contract')[0].get('parameter').get('value').get('to_address'))
                    from_address = to_base58check_address(tx.get('raw_data').get('contract')[0].get('parameter').get('value').get('owner_address'))
                    amount = tx.get('raw_data').get('contract')[0].get('parameter').get('value').get('amount')
                    amount = amount / 1_000_000
                    price_data = get_rate(coin.upper())
                    amount = float(amount) * float(price_data.get('price'))
                    amount = float(Decimal(amount).quantize(Decimal('0.01')))

                case "TriggerSmartContract":
                    data = tx.get('raw_data').get('contract')[0].get('parameter').get('value').get('data')
                    result = trx_abi.decode_abi(['address', 'uint256'], bytes.fromhex(data)[4:])
                    to_address = result[0]
                    from_address = to_base58check_address(tx.get('raw_data').get('contract')[0].get('parameter').get('value').get('owner_address'))

                    contract = to_base58check_address(tx.get('raw_data').get('contract')[0].get('parameter').get('value').get('contract_address'))
                    amount = result[1]
                    amount = amount / 1_000_000
            return {
                "amount": amount,
                "from_address": from_address,
                "to_address": to_address,
                "confirmations": confirmations,
                "contract": contract,
                "tx_type": tx_type
            }
        
        case "BTC" | "LTC" | "BCH" | "GRS":
            # Handle Bitcoin-like cryptocurrencies
            confirmations = tx.get('confirmations', 0)
            amount = 0
            to_address = ''
            from_address = ''
            
            # Extract transaction details
            if 'vout' in tx:
                for output in tx.get('vout', []):
                    if 'scriptPubKey' in output and 'addresses' in output['scriptPubKey']:
                        addresses = output['scriptPubKey']['addresses']
                        if addresses:
                            to_address = addresses[0]
                            amount += output.get('value', 0)
            
            if 'vin' in tx:
                for input_tx in tx.get('vin', []):
                    if 'prevout' in input_tx and 'scriptPubKey' in input_tx['prevout']:
                        addresses = input_tx['prevout']['scriptPubKey'].get('addresses', [])
                        if addresses:
                            from_address = addresses[0]
            
            # Convert to USD if needed
            try:
                price_data = get_rate(coin.upper())
                amount_usd = float(amount) * float(price_data.get('price', 1))
                amount = float(Decimal(amount_usd).quantize(Decimal('0.01')))
            except:
                amount = float(amount)
            
            return {
                "amount": amount,
                "from_address": from_address,
                "to_address": to_address,
                "confirmations": confirmations,
                "contract": None,
                "tx_type": "transfer"
            }
        
        case "ETH" | "BNB" | "POL":
            # Handle Ethereum-like cryptocurrencies
            confirmations = tx.get('confirmations', 0)
            amount = 0
            to_address = ''
            from_address = ''
            
            # Extract transaction details
            if 'to' in tx:
                to_address = tx.get('to', '')
            if 'from' in tx:
                from_address = tx.get('from', '')
            if 'value' in tx:
                # Convert from wei to ether
                amount = float(tx.get('value', 0)) / (10 ** 18)
            
            # Convert to USD if needed
            try:
                price_data = get_rate(coin.upper())
                amount_usd = float(amount) * float(price_data.get('price', 1))
                amount = float(Decimal(amount_usd).quantize(Decimal('0.01')))
            except:
                amount = float(amount)
            
            return {
                "amount": amount,
                "from_address": from_address,
                "to_address": to_address,
                "confirmations": confirmations,
                "contract": None,
                "tx_type": "transfer"
            }
    
    # Default case for unsupported coins
    logger.warning(f"[TX DATA] Unsupported coin: {coin}")
    return {}


def process_deposit_txn(tx_hash, txn_raw, address, contract):
    # Find CryptoAddress by address and contract
    address_model = session.query(CryptoAddress).filter_by(address=address).first()
    if contract:
        address_model = session.query(CryptoAddress).filter_by(address=address, memo=contract).first()
    if not address_model:
        logger.warning(f"[PROCESS_TXN] No address model found for {address}")
        return

    # Find Transaction by blockchain_txid
    txn = session.query(Transaction).filter_by(blockchain_txid=tx_hash).first()
    if txn:
        logger.info(f"[PROCESS_TXN] Transaction {tx_hash} already exists in database")
        return

    # Process new transaction
    logger.info(f"[PROCESS_TXN] Processing new transaction {tx_hash} for address {address}")
    
    try:
        txn_data = get_coin_txn_data(address_model.currency_code.upper(), txn_raw)
        tx_type = txn_data.get('tx_type')
        
        logger.info(f"[PROCESS_TXN] Transaction data: {txn_data}")
        
        # Handle different transaction types
        if tx_type == "TriggerSmartContract" or tx_type == "transfer":
            amount = txn_data.get('amount', 0)
            from_address = txn_data.get('from_address', '')
            to_address = txn_data.get('to_address', '')
            
            logger.info(f"[PROCESS_TXN] Processing {tx_type} transaction: {amount} from {from_address} to {to_address}")
            
            # For BTC, check if the transaction is actually to our address
            if address_model.currency_code.upper() == "BTC":
                # Check if any output is to our address
                if 'vout' in txn_raw:
                    for output in txn_raw.get('vout', []):
                        if 'scriptPubKey' in output and 'addresses' in output['scriptPubKey']:
                            output_addresses = output['scriptPubKey']['addresses']
                            if address in output_addresses:
                                amount = output.get('value', 0)
                                logger.info(f"[PROCESS_TXN] Found BTC output to our address: {amount}")
                                break
                    else:
                        logger.info(f"[PROCESS_TXN] No output to our address {address} found in transaction")
                        return
            
            # Create new transaction record
            from db.wallet import TransactionType, TransactionStatus
            txn = Transaction(
                account_id=address_model.account.id,
                amount=amount,
                type=TransactionType.DEPOSIT,
                status=TransactionStatus.AWAITING_CONFIRMATION,
                address=address,
                blockchain_txid=tx_hash,
                confirmations=txn_data.get('confirmations', 0),
                required_confirmations=6,
                description=f"Deposit to {address}",
                metadata_json={"from_address": from_address, "to_address": to_address, "contract": contract}
            )
            session.add(txn)
            
            # Credit account if confirmed
            if txn.confirmations >= 6:
                address_model.account.balance += Decimal(amount)
                logger.info(f"[PROCESS_TXN] Credited account with {amount}")
            
            session.commit()
            logger.info(f"[PROCESS_TXN] Successfully processed transaction {tx_hash}")
            
        else:
            logger.warning(f"[PROCESS_TXN] Unsupported transaction type: {tx_type}")
            
    except Exception as e:
        logger.error(f"[PROCESS_TXN] Error processing transaction {tx_hash}: {e}")
        import traceback
        logger.error(f"[PROCESS_TXN] Traceback: {traceback.format_exc()}")


async def check_address_txns(address, currency_code, contract=None):
    wallet = {}
    wallet["xpub"] = address

    if contract:
        wallet['contract'] = contract

    coin = get_coin(currency_code.upper())
    info = coin_info(currency_code.upper())
    network = info.get('network')
    try:
        # print("Fetching address history")
        # Updated method call based on Bitcart SDK changes
        if contract:
            txns = await coin.server.getaddresshistory(address, contract)
        else:
            txns = await coin.server.getaddresshistory(address)
        logger.info(f"[TX LISTENER] TXNS: {txns}")
        
        if currency_code == "TRX":
            # TRX returns a dictionary with 'data' key
            txns_data = txns.get('data') if isinstance(txns, dict) else txns
            for tx in txns_data:
                tx_hash = tx.get('tx_hash') or tx.get('txID') or tx.get('transaction_id') or None
                txn_raw = await coin.get_tx(tx_hash)
                if tx_hash:
                    logger.info("[TX LISTENER] RUNNING TXN: {tx_hash}")
                    process_deposit_txn(tx_hash, txn_raw, address, contract)
                    logger.info("[TX LISTENER] Done process txn")
        else:
            for tx in txns:
                logger.info(f"[TX LISTENER] TX: {tx}")
                tx_hash = tx.get('txid') or tx.get('txID') or tx.get('transaction_id') or tx.get('tx_hash') or None
                await asyncio.sleep(5)
                
                # Handle BTC verbose transaction error
                if currency_code == "BTC":
                    try:
                        # Try to get transaction details without verbose mode
                        txn_raw = await coin.get_tx(tx_hash)
                        if tx_hash:
                            logger.info(f"[TX LISTENER] RUNNING TXN: {tx_hash}")
                            process_deposit_txn(tx_hash, txn_raw, address, contract)
                            logger.info("[TX LISTENER] Done process txn")
                    except Exception as tx_error:
                        if "verbose transactions are currently unsupported" in str(tx_error):
                            logger.info(f"[BTC_VERBOSE_ERROR] Skipping transaction {tx_hash} due to verbose transaction limitation")
                            # Try alternative method - create minimal transaction data
                            try:
                                logger.info(f"[BTC_VERBOSE_ERROR] Trying alternative processing for {tx_hash}")
                                # Create minimal transaction data for processing
                                minimal_txn_data = {
                                    'txid': tx_hash,
                                    'confirmations': 1,  # Assume 1 confirmation for new transactions
                                    'vout': [{'value': 0, 'scriptPubKey': {'addresses': [address]}}],  # Placeholder
                                    'vin': []
                                }
                                process_deposit_txn(tx_hash, minimal_txn_data, address, contract)
                                logger.info(f"[BTC_VERBOSE_ERROR] Alternative processing completed for {tx_hash}")
                            except Exception as alt_error:
                                logger.error(f"[BTC_VERBOSE_ERROR] Alternative processing failed for {tx_hash}: {alt_error}")
                            continue
                        else:
                            logger.info(f"[ERROR] Processing transaction {tx_hash}: {str(tx_error)}")
                            continue
                else:
                    txn_raw = await coin.get_tx(tx_hash)
                    if tx_hash:
                        logger.info("[TX LISTENER] RUNNING TXN: {tx_hash}")
                        process_deposit_txn(tx_hash, txn_raw, address, contract)
                        logger.info("[TX LISTENER] Done process txn")
            
        logger.info('[TX LISTENER] Done processing transactions')
    except Exception as e:
        logger.info(f"[ERROR] Getting address history {str(e)}")
        # If it's a rate limiting error, we can still continue
        if "excessive resource usage" in str(e) or "BestEffortRequestFailed" in str(e):
            logger.info(f"[RATE_LIMIT] Rate limited by server, but continuing...")
            return
        # If it's a verbose transaction error for BTC, we can skip the transaction processing
        elif "verbose transactions are currently unsupported" in str(e) and currency_code == "BTC":
            logger.info(f"[BTC_VERBOSE_ERROR] Skipping transaction processing for BTC due to verbose transaction limitation")
            return


def process_addresses(addresses):
    for address in addresses:
        addrs = address.address
        currency = address.currency
        contract = address.contract
        logger.info(f"Processing ... {addrs}")
        check_address_txns(addrs, currency, contract)


def get_all_addresses_for_crypto(currency_code: str) -> list:
    """
    Get all crypto addresses for a specific currency from the database.
    
    Args:
        currency_code (str): The currency code (e.g., 'BTC', 'ETH', 'TRX')
        
    Returns:
        list: List of address strings for the given currency
    """
    try:
        # Query all active crypto addresses for the given currency
        crypto_addresses = session.query(CryptoAddress).filter_by(
            currency_code=currency_code,
            is_active=True
        ).all()
        
        addresses = [addr.address for addr in crypto_addresses]
        logger.info(f"[ADDRESS LOADER] Found {len(addresses)} addresses for {currency_code}")
        return addresses
    except Exception as e:
        logger.error(f"[ADDRESS LOADER] Error getting addresses for {currency_code}: {e}")
        return []


def get_all_crypto_addresses() -> dict:
    """
    Get all crypto addresses grouped by currency from the database.
    
    Returns:
        dict: Dictionary with currency codes as keys and lists of addresses as values
    """
    try:
        # Query all active crypto addresses
        crypto_addresses = session.query(CryptoAddress).filter_by(is_active=True).all()
        
        # Group addresses by currency
        addresses_by_currency = {}
        for addr in crypto_addresses:
            currency = addr.currency_code
            if currency not in addresses_by_currency:
                addresses_by_currency[currency] = []
            addresses_by_currency[currency].append(addr.address)
        
        # Log statistics
        total_addresses = sum(len(addresses) for addresses in addresses_by_currency.values())
        logger.info(f"[ADDRESS LOADER] Found {total_addresses} total addresses across {len(addresses_by_currency)} currencies")
        
        for currency, addresses in addresses_by_currency.items():
            logger.info(f"[ADDRESS LOADER] {currency}: {len(addresses)} addresses")
        
        return addresses_by_currency
    except Exception as e:
        logger.error(f"[ADDRESS LOADER] Error getting all addresses: {e}")
        return {}


def get_address_statistics() -> dict:
    """
    Get statistics about crypto addresses in the database.
    
    Returns:
        dict: Statistics about addresses
    """
    try:
        # Total addresses
        total_addresses = session.query(CryptoAddress).filter_by(is_active=True).count()
        
        # Addresses by currency
        currency_stats = session.query(
            CryptoAddress.currency_code,
            session.query(CryptoAddress).filter(
                CryptoAddress.currency_code == CryptoAddress.currency_code,
                CryptoAddress.is_active == True
            ).count().label('count')
        ).filter(CryptoAddress.is_active == True).group_by(CryptoAddress.currency_code).all()
        
        # Convert to dictionary
        stats = {
            'total_addresses': total_addresses,
            'currencies_with_addresses': len(currency_stats),
            'addresses_by_currency': {stat.currency_code: stat.count for stat in currency_stats}
        }
        
        logger.info(f"[ADDRESS STATS] {stats}")
        return stats
    except Exception as e:
        logger.error(f"[ADDRESS STATS] Error getting address statistics: {e}")
        return {}


async def check_pending(currency_code):
    logger.info(f"[CHECK_PENDING] Function called for {currency_code}")
    logger.info(f"[CHECK_PENDING] Starting wallet transaction check for {currency_code}...")
    coros = []
    
    # Get all addresses for this cryptocurrency from the database
    addresses = get_all_addresses_for_crypto(currency_code)
    logger.info(f"[CHECK_PENDING] Found {len(addresses)} addresses for {currency_code}")
    
    if not addresses:
        logger.warning(f"[CHECK_PENDING] No addresses found for {currency_code} - check_pending will not process any transactions")
        logger.info(f"[CHECK_PENDING] To enable {currency_code} monitoring, add addresses to the database")
        return
    
    logger.info(f"[CHECK_PENDING] Processing {len(addresses)} addresses for {currency_code}")
    logger.info(f"[CHECK_PENDING] Addresses: {addresses}")
    
    # Process each address with delays to reduce rate limiting
    for i, address in enumerate(addresses):
        logger.info(f"[CHECK_PENDING] Checking address: {address}")
        coros.append(check_address_txns(address, currency_code, None))
        
        # Add delay between requests to reduce rate limiting
        if i < len(addresses) - 1:  # Don't delay after the last request
            await asyncio.sleep(2)  # 2 second delay between requests

    logger.info(f"[CHECK_PENDING] Starting {len(coros)} address checks for {currency_code}")
    await asyncio.gather(*coros)
    logger.info(f"[CHECK_PENDING] Completed processing for {currency_code}")


async def update_confirmations_async(asession: AsyncSession, transaction: Transaction):
    # This function should be adapted to be async if your coin.get_tx is async
    coin = get_coin(transaction.account.currency.code.upper())
    if not transaction.blockchain_txid:
        return False
    # If coin.get_tx is async, use: txn = await coin.get_tx(transaction.blockchain_txid)
    txn = coin.get_tx(transaction.blockchain_txid)
    txn_data = get_coin_txn_data(transaction.account.currency.code.upper(), txn)
    confirmations = txn_data.get('confirmations')
    is_eth_based = coin.is_eth_based
    if is_eth_based and confirmations >= 12:
        transaction.status = Transaction.TransactionStatus.COMPLETED
    elif confirmations >= 6:
        transaction.status = Transaction.TransactionStatus.COMPLETED
    else:
        transaction.status = Transaction.TransactionStatus.AWAITING_CONFIRMATION
    transaction.confirmations = confirmations
    await asession.commit()
    return transaction

async def process_new_block_async(session: AsyncSession, currency_code: str):
    # Get the currency object
    result = await session.execute(
        select(Currency).where(Currency.code == currency_code)
    )
    currency = result.scalar_one_or_none()
    if not currency:
        return

    offset = 0
    while True:
        # Query a batch of pending/awaiting confirmation transactions for this currency
        result = await session.execute(
            select(Transaction)
            .join(Account)
            .options(selectinload(Transaction.account).selectinload(Account.currency))
            .where(
                Account.currency_id == currency.id,
                Transaction.status.in_([
                    Transaction.TransactionStatus.PENDING,
                    Transaction.TransactionStatus.AWAITING_CONFIRMATION
                ])
            )
            .order_by(Transaction.id)
            .offset(offset)
            .limit(BATCH_SIZE)
        )
        transactions = result.scalars().all()
        if not transactions:
            break

        # Update confirmations for each transaction in the batch
        for txn in transactions:
            await update_confirmations_async(session, txn)

        offset += BATCH_SIZE


def process_new_block(currency_code: str):
    # Get the currency object
    currency = session.query(Currency).filter_by(code=currency_code).first()
    if not currency:
        return

    offset = 0
    while True:
        transactions = (
            session.query(Transaction)
            .join(Account)
            .filter(
                Account.currency_id == currency.id,
                Transaction.status.in_([
                    Transaction.TransactionStatus.PENDING,
                    Transaction.TransactionStatus.AWAITING_CONFIRMATION
                ])
            )
            .order_by(Transaction.id)
            .offset(offset)
            .limit(BATCH_SIZE)
            .all()
        )
        if not transactions:
            break
        for txn in transactions:
            update_confirmations(txn)
        offset += BATCH_SIZE


async def handle_new_block(instance, event, height):
    currency = instance.coin_name.upper()
    logger.info(f"[NEW BLOCK] Processing new block: {height}")
    process_new_block(currency_code=currency)

def to_wei(value: Decimal,coin,  precision=None) -> int:
    if precision is None:
        precision = coin.DIVISIBILITY
    if value == Decimal(0):
        return 0
    return int(Decimal(value) * Decimal(10**precision))

async def withdraw_trx():
    pass


def get_rate(currency):
    client = Client(config('BINANCE_API_KEY'), config('BINANCE_API_SECRET'))
    data = client.get_avg_price(symbol=f"{currency.upper()}USDT")
    return data

async def handle_new_transaction_db_async(session, currency_code, tx_data, tx_hash):
    # Just call the sync version for now, or refactor as needed
    return handle_new_transaction_db(currency_code, tx_data, tx_hash)
