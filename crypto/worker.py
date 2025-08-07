#!/usr/bin/env python3
"""
Bitcart-style worker for real-time cryptocurrency updates.
This worker connects to individual coin daemons and processes events.
"""

import asyncio
import json
import logging
import websockets
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from decimal import Decimal
from shared.logger import setup_logging
from shared.crypto.util import get_coin, coin_info
from db.wallet import CryptoAddress, Transaction, Account
from db.models import Currency
from db.connection import session
from util import handle_new_transaction_db, get_coin_txn_data

logger = setup_logging()


@dataclass
class CoinDaemon:
    """Represents a cryptocurrency daemon connection"""
    name: str
    host: str
    port: int
    websocket_url: str
    connected: bool = False
    websocket = None
    last_height: int = 0


class CryptoWorker:
    """
    Bitcart-style worker that connects to cryptocurrency daemons
    and processes real-time events.
    """
    
    def __init__(self):
        self.daemons: Dict[str, CoinDaemon] = {}
        self.running = False
        self.event_handlers: Dict[str, List[callable]] = {}
        self.websocket_clients: Set[websockets.WebSocketServerProtocol] = set()
        
    async def add_daemon(self, coin_name: str, host: str, port: int):
        """Add a cryptocurrency daemon to monitor"""
        daemon = CoinDaemon(
            name=coin_name,
            host=host,
            port=port,
            websocket_url=f"ws://{host}:{port}/ws"
        )
        self.daemons[coin_name] = daemon
        logger.info(f"[WORKER] Added daemon: {coin_name} at {host}:{port}")
    
    async def start(self, coins: List[str]):
        """Start the worker and connect to all daemons"""
        logger.info(f"[WORKER] Starting worker for coins: {coins}")
        self.running = True
        
        # Initialize daemons based on configuration
        for coin in coins:
            coin_info_data = coin_info(coin)
            host = coin_info_data.get('credentials', {}).get('rpc_url', '').replace('http://', '').split(':')[0]
            port = int(coin_info_data.get('credentials', {}).get('rpc_url', '').split(':')[-1])  # Use same port for WebSocket
            
            await self.add_daemon(coin, host, port)
        
        # Start monitoring tasks
        tasks = []
        for coin_name in self.daemons:
            tasks.append(self._monitor_daemon(coin_name))
        
        # Start WebSocket server for clients
        tasks.append(self._start_websocket_server())
        
        await asyncio.gather(*tasks)
    
    async def _monitor_daemon(self, coin_name: str):
        """Monitor a specific cryptocurrency daemon"""
        daemon = self.daemons[coin_name]
        logger.info(f"[WORKER] Starting monitoring for {coin_name}")
        
        while self.running:
            try:
                if not daemon.connected:
                    await self._connect_to_daemon(daemon)
                
                if daemon.connected:
                    await self._listen_to_daemon(daemon)
                
            except Exception as e:
                logger.error(f"[WORKER] Error monitoring {coin_name}: {e}")
                daemon.connected = False
                await asyncio.sleep(5)  # Wait before reconnecting
    
    async def _connect_to_daemon(self, daemon: CoinDaemon):
        """Connect to a cryptocurrency daemon"""
        try:
            logger.info(f"[WORKER] Connecting to {daemon.name} at {daemon.websocket_url}")
            
            # Add authentication headers
            import base64
            auth_string = "electrum:electrumz"
            auth_bytes = auth_string.encode('utf-8')
            auth_b64 = base64.b64encode(auth_bytes).decode('utf-8')
            headers = {
                'Authorization': f'Basic {auth_b64}'
            }
            
            daemon.websocket = await websockets.connect(
                daemon.websocket_url,
                extra_headers=headers
            )
            daemon.connected = True
            logger.info(f"[WORKER] Connected to {daemon.name}")
            
            # Subscribe to events
            await self._subscribe_to_events(daemon)
            
        except Exception as e:
            logger.error(f"[WORKER] Failed to connect to {daemon.name}: {e}")
            daemon.connected = False
    
    async def _subscribe_to_events(self, daemon: CoinDaemon):
        """Subscribe to events from a daemon"""
        try:
            # Subscribe to new transaction events
            subscribe_msg = {
                "method": "subscribe",
                "params": ["new_transaction", "new_block"],
                "id": 1
            }
            await daemon.websocket.send(json.dumps(subscribe_msg))
            logger.info(f"[WORKER] Subscribed to events from {daemon.name}")
            
        except Exception as e:
            logger.error(f"[WORKER] Failed to subscribe to {daemon.name}: {e}")
    
    async def _listen_to_daemon(self, daemon: CoinDaemon):
        """Listen for events from a daemon"""
        try:
            async for message in daemon.websocket:
                await self._process_daemon_message(daemon, message)
                
        except websockets.exceptions.ConnectionClosed:
            logger.warning(f"[WORKER] Connection to {daemon.name} closed")
            daemon.connected = False
        except Exception as e:
            logger.error(f"[WORKER] Error listening to {daemon.name}: {e}")
            daemon.connected = False
    
    async def _process_daemon_message(self, daemon: CoinDaemon, message: str):
        """Process a message from a daemon"""
        try:
            data = json.loads(message)
            
            # Handle different message types
            if 'method' in data:
                method = data['method']
                params = data.get('params', [])
                
                if method == 'new_transaction':
                    await self._handle_new_transaction(daemon.name, params)
                elif method == 'new_block':
                    await self._handle_new_block(daemon.name, params)
                elif method == 'new_payment':
                    await self._handle_new_payment(daemon.name, params)
                    
        except json.JSONDecodeError:
            logger.warning(f"[WORKER] Invalid JSON from {daemon.name}")
        except Exception as e:
            logger.error(f"[WORKER] Error processing message from {daemon.name}: {e}")
    
    async def _handle_new_transaction(self, coin_name: str, params: List):
        """Handle a new transaction event"""
        try:
            # Extract transaction data
            tx_hash = params[0] if params else None
            if not tx_hash:
                return
            
            logger.info(f"[WORKER] New transaction: {tx_hash} for {coin_name}")
            
            # Get transaction details
            coin = get_coin(coin_name.upper())
            tx_details = await coin.get_tx(tx_hash)
            tx_data = get_coin_txn_data(coin_name.upper(), tx_details)
            
            # Process transaction in database
            await self._process_transaction_in_db(coin_name, tx_data, tx_hash)
            
            # Broadcast to WebSocket clients
            await self._broadcast_event({
                'event': 'new_transaction',
                'coin': coin_name,
                'tx_hash': tx_hash,
                'data': tx_data
            })
            
        except Exception as e:
            logger.error(f"[WORKER] Error handling new transaction: {e}")
    
    async def _handle_new_block(self, coin_name: str, params: List):
        """Handle a new block event"""
        try:
            height = params[0] if params else None
            if height:
                logger.info(f"[WORKER] New block: {height} for {coin_name}")
                
                # Broadcast to WebSocket clients
                await self._broadcast_event({
                    'event': 'new_block',
                    'coin': coin_name,
                    'height': height
                })
                
        except Exception as e:
            logger.error(f"[WORKER] Error handling new block: {e}")
    
    async def _handle_new_payment(self, coin_name: str, params: List):
        """Handle a new payment event"""
        try:
            payment_data = params[0] if params else {}
            logger.info(f"[WORKER] New payment for {coin_name}: {payment_data}")
            
            # Broadcast to WebSocket clients
            await self._broadcast_event({
                'event': 'new_payment',
                'coin': coin_name,
                'data': payment_data
            })
            
        except Exception as e:
            logger.error(f"[WORKER] Error handling new payment: {e}")
    
    async def _process_transaction_in_db(self, coin_name: str, tx_data: dict, tx_hash: str):
        """Process transaction in the database"""
        try:
            # Check if transaction already exists
            existing_tx = session.query(Transaction).filter_by(
                blockchain_txid=tx_hash
            ).first()
            
            if existing_tx:
                logger.info(f"[WORKER] Transaction {tx_hash} already processed")
                return
            
            # Process new transaction
            handle_new_transaction_db(coin_name, tx_data, tx_hash)
            logger.info(f"[WORKER] Processed transaction {tx_hash} in database")
            
        except Exception as e:
            logger.error(f"[WORKER] Error processing transaction in DB: {e}")
    
    async def _start_websocket_server(self):
        """Start WebSocket server for client connections"""
        logger.info("[WORKER] Starting WebSocket server on ws://localhost:8082")
        
        async def websocket_handler(websocket, path):
            """Handle WebSocket client connections"""
            self.websocket_clients.add(websocket)
            logger.info(f"[WORKER] New WebSocket client connected. Total: {len(self.websocket_clients)}")
            
            try:
                async for message in websocket:
                    await self._handle_client_message(websocket, message)
            except websockets.exceptions.ConnectionClosed:
                logger.info("[WORKER] WebSocket client disconnected")
            finally:
                self.websocket_clients.discard(websocket)
        
        server = await websockets.serve(websocket_handler, "localhost", 8082)
        await server.wait_closed()
    
    async def _handle_client_message(self, websocket, message: str):
        """Handle messages from WebSocket clients"""
        try:
            data = json.loads(message)
            message_type = data.get('type')
            
            if message_type == 'subscribe':
                events = data.get('events', [])
                logger.info(f"[WORKER] Client subscribed to events: {events}")
                
                # Send confirmation
                await websocket.send(json.dumps({
                    'type': 'subscription_confirmed',
                    'events': events
                }))
            
            elif message_type == 'ping':
                await websocket.send(json.dumps({'type': 'pong'}))
            
            elif message_type == 'get_status':
                status = {
                    'running': self.running,
                    'connected_daemons': len([d for d in self.daemons.values() if d.connected]),
                    'total_daemons': len(self.daemons),
                    'connected_clients': len(self.websocket_clients)
                }
                await websocket.send(json.dumps({
                    'type': 'status',
                    'data': status
                }))
                
        except json.JSONDecodeError:
            await websocket.send(json.dumps({'error': 'Invalid JSON'}))
        except Exception as e:
            logger.error(f"[WORKER] Error handling client message: {e}")
    
    async def _broadcast_event(self, event_data: dict):
        """Broadcast event to all connected WebSocket clients"""
        if not self.websocket_clients:
            return
        
        message = {
            'type': 'event',
            'data': event_data,
            'timestamp': asyncio.get_event_loop().time()
        }
        
        # Send to all connected clients
        disconnected = set()
        for client in self.websocket_clients:
            try:
                await client.send(json.dumps(message))
            except websockets.exceptions.ConnectionClosed:
                disconnected.add(client)
            except Exception as e:
                logger.error(f"[WORKER] Error sending to client: {e}")
                disconnected.add(client)
        
        # Remove disconnected clients
        self.websocket_clients -= disconnected
    
    async def stop(self):
        """Stop the worker"""
        logger.info("[WORKER] Stopping worker...")
        self.running = False
        
        # Close daemon connections
        for daemon in self.daemons.values():
            if daemon.websocket:
                await daemon.websocket.close()
        
        # Close client connections
        for client in self.websocket_clients.copy():
            await client.close()
        
        logger.info("[WORKER] Worker stopped")


# Global worker instance
worker = CryptoWorker()


async def start_worker(coins: List[str]):
    """Start the global worker"""
    await worker.start(coins)


async def stop_worker():
    """Stop the global worker"""
    await worker.stop()


def get_worker() -> CryptoWorker:
    """Get the global worker instance"""
    return worker


if __name__ == "__main__":
    # Example usage
    coins = ["BTC"]
    
    try:
        asyncio.run(start_worker(coins))
    except KeyboardInterrupt:
        logger.info("[WORKER] Received interrupt signal")
        asyncio.run(stop_worker())
    except Exception as e:
        logger.error(f"[WORKER] Unexpected error: {e}")
        asyncio.run(stop_worker()) 