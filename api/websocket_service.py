import asyncio
import json
import logging
from aiohttp import web, WSMsgType
from crypto.event_system import get_event_listener
from shared.logger import setup_logging

logger = setup_logging()


class WebSocketService:
    """WebSocket service for real-time cryptocurrency events"""
    
    def __init__(self, host='0.0.0.0', port=8081):
        self.host = host
        self.port = port
        self.app = web.Application()
        self.setup_routes()
    
    def setup_routes(self):
        """Setup WebSocket routes"""
        self.app.router.add_get('/ws/events', self.websocket_handler)
        self.app.router.add_get('/health', self.health_check)
    
    async def websocket_handler(self, request):
        """WebSocket endpoint for real-time cryptocurrency events"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        logger.info("[WEBSOCKET] New WebSocket connection for events")
        
        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        data = msg.json()
                        await self.handle_websocket_message(ws, data)
                    except json.JSONDecodeError:
                        await ws.send_json({
                            'error': 'Invalid JSON format'
                        })
                elif msg.type == WSMsgType.ERROR:
                    logger.error(f"[WEBSOCKET] WebSocket error: {ws.exception()}")
        finally:
            logger.info("[WEBSOCKET] WebSocket connection closed")
    
    async def handle_websocket_message(self, ws, data):
        """Handle incoming WebSocket messages"""
        message_type = data.get('type')
        
        if message_type == 'subscribe':
            events = data.get('events', [])
            logger.info(f"[WEBSOCKET] Client subscribed to events: {events}")
            
            # Send confirmation
            await ws.send_json({
                'type': 'subscription_confirmed',
                'events': events
            })
        
        elif message_type == 'ping':
            await ws.send_json({'type': 'pong'})
        
        elif message_type == 'get_status':
            # Return current system status
            event_listener = get_event_listener()
            status = {
                'running': event_listener.running,
                'connected_websockets': len(event_listener.websockets),
                'monitored_currencies': list(event_listener.address_watchers.keys()),
                'total_addresses': sum(len(addresses) for addresses in event_listener.address_watchers.values())
            }
            await ws.send_json({
                'type': 'status',
                'data': status
            })
        
        else:
            await ws.send_json({
                'error': f'Unknown message type: {message_type}'
            })
    
    async def health_check(self, request):
        """Health check endpoint"""
        event_listener = get_event_listener()
        return web.json_response({
            'status': 'healthy',
            'event_listener_running': event_listener.running,
            'connected_websockets': len(event_listener.websockets)
        })
    
    async def start(self):
        """Start the WebSocket service"""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        logger.info(f"[WEBSOCKET] WebSocket service started on {self.host}:{self.port}")
        return runner
    
    async def stop(self, runner):
        """Stop the WebSocket service"""
        await runner.cleanup()
        logger.info("[WEBSOCKET] WebSocket service stopped")


async def start_websocket_service():
    """Start the WebSocket service"""
    service = WebSocketService()
    runner = await service.start()
    return service, runner


if __name__ == "__main__":
    async def main():
        service, runner = await start_websocket_service()
        try:
            # Keep the service running
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("[WEBSOCKET] Shutting down...")
            await service.stop(runner)
    
    asyncio.run(main()) 