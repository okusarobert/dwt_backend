import asyncio
import json
import logging
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from aiohttp import web, WSMsgType
from shared.logger import setup_logging
from shared.crypto.util import get_coin, coin_info
from db.models import CryptoAddress, Transaction, Account, Currency
from db.connection import session
from util import handle_new_transaction_db, get_coin_txn_data

logger = setup_logging()


class EventType(Enum):
    NEW_TRANSACTION = "new_transaction"
    NEW_BLOCK = "new_block"
    NEW_PAYMENT = "new_payment"
    VERIFIED_TX = "verified_tx"
    ADDRESS_UPDATE = "address_update"


@dataclass
class TransactionEvent:
    tx_hash: str
    currency: str
    from_address: str
    to_address: str
    amount: Decimal
    confirmations: int
    contract: Optional[str] = None
    block_height: Optional[int] = None
    timestamp: Optional[int] = None


@dataclass
class BlockEvent:
    height: int
    currency: str
    hash: str
    timestamp: Optional[int] = None


class EventListener:
    """Bitcart-style event listener for cryptocurrency transactions"""
    
    def __init__(self):
        self.websockets: set = set()
        self.event_handlers: Dict[EventType, List[Callable]] = {
            event_type: [] for event_type in EventType
        }
        self.address_watchers: Dict[str, List[str]] = {}  # currency -> addresses
        self.coin_instances: Dict[str, Any] = {}
        self.running = False
        self.loop = None
        
    async def start(self, currencies: List[str]):
        """Start the event listener for specified currencies"""
        logger.info(f"[EVENT_LISTENER] Starting event listener for currencies: {currencies}")
        self.loop = asyncio.get_running_loop()
        self.running = True
        
        # Initialize coin instances
        for currency in currencies:
            await self._initialize_coin(currency)
        
        # Start monitoring tasks
        tasks = []
        for currency in currencies:
            tasks.append(self._monitor_currency(currency))
        
        await asyncio.gather(*tasks)
    
    async def _initialize_coin(self, currency: str):
        """Initialize coin instance and load addresses"""
        try:
            coin = get_coin(currency.upper())
            self.coin_instances[currency] = coin
            
            # Load addresses for this currency
            addresses = self._get_addresses_for_currency(currency)
            self.address_watchers[currency] = addresses
            
            logger.info(f"[EVENT_LISTENER] Initialized {currency} with {len(addresses)} addresses")
            
        except Exception as e:
            logger.error(f"[EVENT_LISTENER] Failed to initialize {currency}: {e}")
    
    def _get_addresses_for_currency(self, currency: str) -> List[str]:
        """Get all addresses for a specific currency from database"""
        try:
            addresses = session.query(CryptoAddress).filter_by(
                currency_code=currency,
                is_active=True
            ).all()
            return [addr.address for addr in addresses]
        except Exception as e:
            logger.error(f"[EVENT_LISTENER] Error getting addresses for {currency}: {e}")
            return []
    
    async def _monitor_currency(self, currency: str):
        """Monitor a specific currency for new transactions"""
        logger.info(f"[EVENT_LISTENER] Starting monitoring for {currency}")
        
        while self.running:
            try:
                await self._check_new_transactions(currency)
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"[EVENT_LISTENER] Error monitoring {currency}: {e}")
                await asyncio.sleep(30)  # Wait longer on error
    
    async def _check_new_transactions(self, currency: str):
        """Check for new transactions for a currency"""
        addresses = self.address_watchers.get(currency, [])
        if not addresses:
            return
        
        coin = self.coin_instances.get(currency)
        if not coin:
            return
        
        for address in addresses:
            try:
                await self._check_address_transactions(coin, currency, address)
                await asyncio.sleep(1)  # Rate limiting
                
            except Exception as e:
                logger.error(f"[EVENT_LISTENER] Error checking address {address}: {e}")
    
    async def _check_address_transactions(self, coin, currency: str, address: str):
        """Check transactions for a specific address"""
        try:
            # Get address history
            if hasattr(coin.server, 'getaddresshistory'):
                txns = await coin.server.getaddresshistory(address)
            else:
                # Fallback for coins without getaddresshistory
                return
            
            if not txns:
                return
            
            # Process each transaction
            for tx_data in txns:
                tx_hash = tx_data.get('txid') or tx_data.get('tx_hash')
                if not tx_hash:
                    continue
                
                # Check if transaction already processed
                if await self._is_transaction_processed(tx_hash, currency):
                    continue
                
                # Get transaction details
                tx_details = await coin.get_tx(tx_hash)
                tx_info = get_coin_txn_data(currency, tx_details)
                
                # Create transaction event
                event = TransactionEvent(
                    tx_hash=tx_hash,
                    currency=currency,
                    from_address=tx_info.get('from_address', ''),
                    to_address=tx_info.get('to_address', ''),
                    amount=Decimal(str(tx_info.get('amount', 0))),
                    confirmations=tx_info.get('confirmations', 0),
                    contract=tx_info.get('contract'),
                    block_height=tx_details.get('height'),
                    timestamp=tx_details.get('time')
                )
                
                # Trigger event
                await self._trigger_transaction_event(event)
                
        except Exception as e:
            logger.error(f"[EVENT_LISTENER] Error processing transactions for {address}: {e}")
    
    async def _is_transaction_processed(self, tx_hash: str, currency: str) -> bool:
        """Check if transaction has already been processed"""
        try:
            existing_tx = session.query(Transaction).filter_by(
                blockchain_txid=tx_hash
            ).first()
            return existing_tx is not None
        except Exception as e:
            logger.error(f"[EVENT_LISTENER] Error checking transaction {tx_hash}: {e}")
            return False
    
    async def _trigger_transaction_event(self, event: TransactionEvent):
        """Trigger a new transaction event"""
        logger.info(f"[EVENT_LISTENER] New transaction: {event.tx_hash} for {event.currency}")
        
        # Process transaction in database
        try:
            tx_data = {
                'amount': float(event.amount),
                'from_address': event.from_address,
                'to_address': event.to_address,
                'confirmations': event.confirmations,
                'contract': event.contract
            }
            
            # Handle transaction in database
            handle_new_transaction_db(event.currency, tx_data, event.tx_hash)
            
            # Notify websocket clients
            await self._notify_websockets({
                'event': EventType.NEW_TRANSACTION.value,
                'tx_hash': event.tx_hash,
                'currency': event.currency,
                'from_address': event.from_address,
                'to_address': event.to_address,
                'amount': str(event.amount),
                'confirmations': event.confirmations,
                'contract': event.contract,
                'block_height': event.block_height,
                'timestamp': event.timestamp
            })
            
        except Exception as e:
            logger.error(f"[EVENT_LISTENER] Error processing transaction event: {e}")
    
    async def _notify_websockets(self, data: dict):
        """Notify all connected websocket clients"""
        if not self.websockets:
            return
        
        notification = {
            'type': 'event',
            'data': data,
            'timestamp': asyncio.get_event_loop().time()
        }
        
        # Send to all connected websockets
        coros = []
        for ws in self.websockets.copy():
            if not ws.closed:
                try:
                    coros.append(ws.send_json(notification))
                except Exception as e:
                    logger.error(f"[EVENT_LISTENER] Error sending to websocket: {e}")
                    self.websockets.discard(ws)
        
        if coros:
            await asyncio.gather(*coros, return_exceptions=True)
    
    def add_event_handler(self, event_type: EventType, handler: Callable):
        """Add an event handler for a specific event type"""
        self.event_handlers[event_type].append(handler)
        logger.info(f"[EVENT_LISTENER] Added handler for {event_type.value}")
    
    async def handle_websocket(self, request: web.Request):
        """Handle websocket connections"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        self.websockets.add(ws)
        logger.info(f"[EVENT_LISTENER] New websocket connection. Total: {len(self.websockets)}")
        
        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        data = msg.json()
                        await self._handle_websocket_message(ws, data)
                    except json.JSONDecodeError:
                        logger.warning("[EVENT_LISTENER] Invalid JSON received")
                elif msg.type == WSMsgType.ERROR:
                    logger.error(f"[EVENT_LISTENER] Websocket error: {ws.exception()}")
        finally:
            self.websockets.discard(ws)
            logger.info(f"[EVENT_LISTENER] Websocket disconnected. Total: {len(self.websockets)}")
    
    async def _handle_websocket_message(self, ws, data: dict):
        """Handle incoming websocket messages"""
        message_type = data.get('type')
        
        if message_type == 'subscribe':
            # Handle subscription to specific events
            events = data.get('events', [])
            logger.info(f"[EVENT_LISTENER] Client subscribed to events: {events}")
            
            # Send confirmation
            await ws.send_json({
                'type': 'subscription_confirmed',
                'events': events
            })
        
        elif message_type == 'ping':
            # Handle ping/pong
            await ws.send_json({'type': 'pong'})
    
    async def stop(self):
        """Stop the event listener"""
        logger.info("[EVENT_LISTENER] Stopping event listener")
        self.running = False
        
        # Close all websocket connections
        for ws in self.websockets.copy():
            if not ws.closed:
                await ws.close()
        
        self.websockets.clear()


# Global event listener instance
event_listener = EventListener()


async def start_event_listener(currencies: List[str]):
    """Start the global event listener"""
    await event_listener.start(currencies)


async def stop_event_listener():
    """Stop the global event listener"""
    await event_listener.stop()


def get_event_listener() -> EventListener:
    """Get the global event listener instance"""
    return event_listener 