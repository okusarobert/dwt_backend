#!/usr/bin/env python3
"""
Test client for the Bitcart-style worker system.
This demonstrates how to connect and receive real-time cryptocurrency updates.
"""

import asyncio
import json
import websockets
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WorkerTestClient:
    """Test client for connecting to the worker"""
    
    def __init__(self, websocket_url: str = "ws://localhost:8082"):
        self.websocket_url = websocket_url
        self.websocket = None
        self.running = False
    
    async def connect(self):
        """Connect to the worker"""
        try:
            self.websocket = await websockets.connect(self.websocket_url)
            logger.info(f"[TEST_CLIENT] Connected to worker at {self.websocket_url}")
            return True
        except Exception as e:
            logger.error(f"[TEST_CLIENT] Failed to connect: {e}")
            return False
    
    async def subscribe_to_events(self):
        """Subscribe to all events"""
        message = {
            "type": "subscribe",
            "events": ["new_transaction", "new_block", "new_payment"]
        }
        
        await self.websocket.send(json.dumps(message))
        logger.info("[TEST_CLIENT] Subscribed to all events")
    
    async def get_status(self):
        """Get worker status"""
        message = {
            "type": "get_status"
        }
        
        await self.websocket.send(json.dumps(message))
        logger.info("[TEST_CLIENT] Requested worker status")
    
    async def listen_for_events(self):
        """Listen for events from the worker"""
        self.running = True
        
        try:
            while self.running:
                try:
                    message = await self.websocket.recv()
                    data = json.loads(message)
                    await self.handle_message(data)
                    
                except websockets.exceptions.ConnectionClosed:
                    logger.warning("[TEST_CLIENT] Connection to worker closed")
                    break
                    
                except json.JSONDecodeError:
                    logger.error("[TEST_CLIENT] Invalid JSON received")
                    
        except Exception as e:
            logger.error(f"[TEST_CLIENT] Error in listen loop: {e}")
    
    async def handle_message(self, data: dict):
        """Handle messages from the worker"""
        message_type = data.get('type')
        
        if message_type == 'subscription_confirmed':
            events = data.get('events', [])
            logger.info(f"[TEST_CLIENT] Subscription confirmed for events: {events}")
        
        elif message_type == 'pong':
            logger.debug("[TEST_CLIENT] Received pong")
        
        elif message_type == 'status':
            status = data.get('data', {})
            logger.info(f"[TEST_CLIENT] Worker status: {status}")
        
        elif message_type == 'event':
            event_data = data.get('data', {})
            await self.handle_event(event_data)
        
        else:
            logger.warning(f"[TEST_CLIENT] Unknown message type: {message_type}")
    
    async def handle_event(self, event_data: dict):
        """Handle cryptocurrency events"""
        event_type = event_data.get('event')
        coin = event_data.get('coin', 'Unknown')
        
        if event_type == 'new_transaction':
            tx_hash = event_data.get('tx_hash')
            tx_data = event_data.get('data', {})
            
            logger.info(f"[TEST_CLIENT] New {coin} transaction: {tx_hash}")
            logger.info(f"  Amount: {tx_data.get('amount', 'N/A')}")
            logger.info(f"  From: {tx_data.get('from_address', 'N/A')}")
            logger.info(f"  To: {tx_data.get('to_address', 'N/A')}")
            logger.info(f"  Confirmations: {tx_data.get('confirmations', 'N/A')}")
        
        elif event_type == 'new_block':
            height = event_data.get('height')
            logger.info(f"[TEST_CLIENT] New {coin} block: {height}")
        
        elif event_type == 'new_payment':
            payment_data = event_data.get('data', {})
            logger.info(f"[TEST_CLIENT] New {coin} payment: {payment_data}")
        
        else:
            logger.warning(f"[TEST_CLIENT] Unknown event type: {event_type}")
    
    async def run(self):
        """Run the test client"""
        if not await self.connect():
            return
        
        try:
            # Subscribe to events
            await self.subscribe_to_events()
            
            # Get initial status
            await self.get_status()
            
            # Start listening
            await self.listen_for_events()
            
        except Exception as e:
            logger.error(f"[TEST_CLIENT] Error running client: {e}")
        
        finally:
            if self.websocket:
                await self.websocket.close()
    
    async def stop(self):
        """Stop the test client"""
        self.running = False
        if self.websocket:
            await self.websocket.close()


async def main():
    """Main function to run the test client"""
    client = WorkerTestClient()
    
    try:
        await client.run()
    except KeyboardInterrupt:
        logger.info("[TEST_CLIENT] Received interrupt signal")
        await client.stop()


if __name__ == "__main__":
    asyncio.run(main()) 