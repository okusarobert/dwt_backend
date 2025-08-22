"""
Redis-based Notification Handler
Subscribes to Redis pub/sub for notifications and broadcasts them to connected users via WebSocket
"""
import json
import logging
import threading
from typing import Dict, Set
import redis
import os
from flask_socketio import SocketIO

logger = logging.getLogger(__name__)

class RedisNotificationHandler:
    def __init__(self, socketio: SocketIO):
        self.socketio = socketio
        self.redis_client = None
        self.pubsub = None
        self.connected_users: Dict[int, Set[str]] = {}  # user_id -> set of session_ids
        self.user_sessions: Dict[str, int] = {}  # session_id -> user_id
        self.running = False
        self.consumer_thread = None
        self.notification_channel = "crypto_notifications"
        
    def start_consumer(self):
        """Start the Redis subscriber in a separate thread"""
        if self.running:
            return
            
        try:
            # Initialize Redis connection
            redis_host = os.getenv('REDIS_HOST', 'redis')
            redis_port = int(os.getenv('REDIS_PORT', 6379))
            self.redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
            
            # Test connection
            self.redis_client.ping()
            logger.info("Redis connection established")
            
            # Create pubsub instance
            self.pubsub = self.redis_client.pubsub()
            self.pubsub.subscribe(self.notification_channel)
            
            self.running = True
            self.consumer_thread = threading.Thread(target=self._consume_notifications, daemon=True)
            self.consumer_thread.start()
            
            logger.info("Redis notification consumer started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start Redis notification consumer: {e}")
            
    def stop_consumer(self):
        """Stop the Redis subscriber"""
        self.running = False
        if self.pubsub:
            self.pubsub.unsubscribe(self.notification_channel)
            self.pubsub.close()
        if self.redis_client:
            self.redis_client.close()
        if self.consumer_thread:
            self.consumer_thread.join(timeout=5)
        logger.info("Redis notification consumer stopped")
        
    def _consume_notifications(self):
        """Main consumer loop"""
        logger.info(f"🔔 Redis notification consumer loop started, listening on '{self.notification_channel}'")
        while self.running:
            try:
                message = self.pubsub.get_message(timeout=1.0)
                if message is None:
                    continue
                    
                logger.info(f"🔔 Received Redis message: type={message['type']}, channel={message.get('channel')}")
                    
                if message['type'] != 'message':
                    continue
                    
                # Parse notification message
                try:
                    logger.info(f"🔔 Raw message data: {message['data']}")
                    notification_data = json.loads(message['data'])
                    logger.info(f"🔔 Parsed notification data for user {notification_data.get('user_id')}")
                    self._handle_notification(notification_data)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse notification message: {e}")
                    
            except Exception as e:
                logger.error(f"Error in Redis consumer: {e}")
                
    def _handle_notification(self, notification_data: dict):
        """Process and broadcast notification to specific user"""
        try:
            user_id = notification_data.get('user_id')
            if not user_id:
                logger.warning("Notification missing user_id")
                return
                
            logger.info(f"🔔 Processing notification for user {user_id}")
            logger.info(f"🔔 Connected users: {list(self.connected_users.keys())}")
                
            # Check if user is connected
            if user_id not in self.connected_users or not self.connected_users[user_id]:
                logger.warning(f"🔔 User {user_id} not connected, skipping notification. Connected users: {list(self.connected_users.keys())}")
                return
                
            # Prepare notification for frontend
            frontend_notification = {
                'id': notification_data.get('message_id'),
                'type': notification_data.get('type'),
                'title': notification_data['notification']['title'],
                'message': notification_data['notification']['message'],
                'priority': notification_data['notification']['priority'],
                'category': notification_data['notification']['category'],
                'action_url': notification_data['notification'].get('action_url'),
                'transaction': notification_data.get('transaction', {}),
                'timestamp': notification_data.get('timestamp'),
                'read': False
            }
            
            # Broadcast to all user's sessions
            session_count = 0
            for session_id in self.connected_users[user_id]:
                logger.info(f"🔔 Sending notification to session {session_id}")
                self.socketio.emit(
                    'notification',
                    frontend_notification,
                    room=session_id
                )
                session_count += 1
                
            logger.info(f"🔔 Broadcasted notification to user {user_id} ({session_count} sessions): {notification_data['notification']['title']}")
            
        except Exception as e:
            logger.error(f"Failed to handle notification: {e}")
            
    def user_connected(self, session_id: str, user_id: int):
        """Register a user connection"""
        if user_id not in self.connected_users:
            self.connected_users[user_id] = set()
            
        self.connected_users[user_id].add(session_id)
        self.user_sessions[session_id] = user_id
        
        logger.info(f"User {user_id} connected with session {session_id}")
        
    def user_disconnected(self, session_id: str):
        """Handle user disconnection"""
        if session_id in self.user_sessions:
            user_id = self.user_sessions[session_id]
            
            # Remove session from user's sessions
            if user_id in self.connected_users:
                self.connected_users[user_id].discard(session_id)
                
                # Clean up empty user entries
                if not self.connected_users[user_id]:
                    del self.connected_users[user_id]
                    
            del self.user_sessions[session_id]
            logger.info(f"User {user_id} disconnected session {session_id}")
            
    def get_connected_users(self) -> Dict[int, int]:
        """Get count of connected sessions per user"""
        return {user_id: len(sessions) for user_id, sessions in self.connected_users.items()}

# Global notification handler instance
redis_notification_handler = None

def get_redis_notification_handler(socketio: SocketIO = None) -> RedisNotificationHandler:
    """Get or create Redis notification handler instance"""
    global redis_notification_handler
    if redis_notification_handler is None and socketio:
        redis_notification_handler = RedisNotificationHandler(socketio)
    return redis_notification_handler
