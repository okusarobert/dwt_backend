#!/usr/bin/env python3
"""
Example client for connecting to the cryptocurrency event WebSocket service.
This demonstrates how to receive real-time transaction notifications.
"""

import asyncio
import json
import websockets
import logging
from typing import Dict, Any

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CryptoEventClient:
    """Client for connecting to the cryptocurrency event WebSocket service"""
    
    def __init__(self, websocket_url: str = "ws://localhost:8081/ws/events"):
        self.websocket_url = websocket_url
        self.websocket = None
        self.running = False
    
    async def connect(self):
        """Connect to the WebSocket service"""
        try:
            self.websocket = await websockets.connect(self.websocket_url)
            logger.info(f"[CLIENT] Connected to {self.websocket_url}")
            return True
        except Exception as e:
            logger.error(f"[CLIENT] Failed to connect: {e}")
            return False
    
    async def subscribe_to_events(self, events: list = None):
        """Subscribe to specific events"""
        if events is None:
            events = ["new_transaction", "new_block", "new_payment"]
        
        message = {
            "type": "subscribe",
            "events": events
        }
        
        await self.websocket.send(json.dumps(message))
        logger.info(f"[CLIENT] Subscribed to events: {events}")
    
    async def get_status(self):
        """Get current system status"""
        message = {
            "type": "get_status"
        }
        
        await self.websocket.send(json.dumps(message))
        logger.info("[CLIENT] Requested system status")
    
    async def ping(self):
        """Send ping to keep connection alive"""
        message = {
            "type": "ping"
        }
        
        await self.websocket.send(json.dumps(message))
    
    async def handle_message(self, message: Dict[str, Any]):
        """Handle incoming WebSocket messages"""
        message_type = message.get('type')
        
        if message_type == 'subscription_confirmed':
            events = message.get('events', [])
            logger.info(f"[CLIENT] Subscription confirmed for events: {events}")
        
        elif message_type == 'pong':
            logger.debug("[CLIENT] Received pong")
        
        elif message_type == 'status':
            status = message.get('data', {})
            logger.info(f"[CLIENT] System status: {status}")
        
        elif message_type == 'event':
            event_data = message.get('data', {})
            await self.handle_event(event_data)
        
        else:
            logger.warning(f"[CLIENT] Unknown message type: {message_type}")
    
    async def handle_event(self, event_data: Dict[str, Any]):
        """Handle cryptocurrency events"""
        event_type = event_data.get('event')
        
        if event_type == 'new_transaction':
            await self.handle_new_transaction(event_data)
        
        elif event_type == 'new_block':
            await self.handle_new_block(event_data)
        
        elif event_type == 'new_payment':
            await self.handle_new_payment(event_data)
        
        else:
            logger.warning(f"[CLIENT] Unknown event type: {event_type}")
    
    async def handle_new_transaction(self, event_data: Dict[str, Any]):
        """Handle new transaction event"""
        tx_hash = event_data.get('tx_hash')
        currency = event_data.get('currency')
        amount = event_data.get('amount')
        from_address = event_data.get('from_address')
        to_address = event_data.get('to_address')
        confirmations = event_data.get('confirmations')
        
        logger.info(f"[CLIENT] New transaction: {tx_hash}")
        logger.info(f"  Currency: {currency}")
        logger.info(f"  Amount: {amount}")
        logger.info(f"  From: {from_address}")
        logger.info(f"  To: {to_address}")
        logger.info(f"  Confirmations: {confirmations}")
        
        # Here you can implement your business logic
        # For example, update UI, send notifications, etc.
    
    async def handle_new_block(self, event_data: Dict[str, Any]):
        """Handle new block event"""
        height = event_data.get('height')
        currency = event_data.get('currency')
        
        logger.info(f"[CLIENT] New block: {height} for {currency}")
    
    async def handle_new_payment(self, event_data: Dict[str, Any]):
        """Handle new payment event"""
        address = event_data.get('address')
        status = event_data.get('status')
        sent_amount = event_data.get('sent_amount')
        
        logger.info(f"[CLIENT] New payment: {address}")
        logger.info(f"  Status: {status}")
        logger.info(f"  Amount: {sent_amount}")
    
    async def listen(self):
        """Listen for incoming messages"""
        self.running = True
        
        try:
            while self.running:
                try:
                    message = await self.websocket.recv()
                    data = json.loads(message)
                    await self.handle_message(data)
                    
                except websockets.exceptions.ConnectionClosed:
                    logger.warning("[CLIENT] Connection closed")
                    break
                    
                except json.JSONDecodeError:
                    logger.error("[CLIENT] Invalid JSON received")
                    
        except Exception as e:
            logger.error(f"[CLIENT] Error in listen loop: {e}")
    
    async def run(self):
        """Run the client"""
        if not await self.connect():
            return
        
        try:
            # Subscribe to events
            await self.subscribe_to_events()
            
            # Get initial status
            await self.get_status()
            
            # Start listening
            await self.listen()
            
        except Exception as e:
            logger.error(f"[CLIENT] Error running client: {e}")
        
        finally:
            if self.websocket:
                await self.websocket.close()
    
    async def stop(self):
        """Stop the client"""
        self.running = False
        if self.websocket:
            await self.websocket.close()


async def main():
    """Main function to run the example client"""
    client = CryptoEventClient()
    
    try:
        await client.run()
    except KeyboardInterrupt:
        logger.info("[CLIENT] Received interrupt signal")
        await client.stop()


if __name__ == "__main__":
    asyncio.run(main()) 