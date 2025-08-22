"""
WebSocket Notification Handler
Consumes Kafka notifications and broadcasts them to connected users via WebSocket
"""
import json
import logging
import threading
from typing import Dict, Set
from confluent_kafka import Consumer, KafkaException
from flask_socketio import SocketIO, emit
import os

from shared.kafka_utils import create_safe_consumer, ensure_notification_topics

logger = logging.getLogger(__name__)

class NotificationHandler:
    def __init__(self, socketio: SocketIO):
        self.socketio = socketio
        self.consumer = None
        self.connected_users: Dict[int, Set[str]] = {}  # user_id -> set of session_ids
        self.user_sessions: Dict[str, int] = {}  # session_id -> user_id
        self.running = False
        self.consumer_thread = None
        
    def start_consumer(self):
        """Start the Kafka consumer in a separate thread"""
        if self.running:
            return
            
        try:
            # Ensure notification topics exist before subscribing
            bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
            if not ensure_notification_topics(bootstrap_servers):
                logger.error("Failed to ensure notification topics exist")
                return
            
            # Create safe consumer with automatic topic creation
            self.consumer = create_safe_consumer(
                topics=['crypto_notifications'],
                group_id='websocket_notifications',
                bootstrap_servers=bootstrap_servers,
                auto_offset_reset='latest'
            )
            
            if not self.consumer:
                logger.error("Failed to create Kafka consumer")
                return
            
            self.running = True
            self.consumer_thread = threading.Thread(target=self._consume_notifications, daemon=True)
            self.consumer_thread.start()
            
            logger.info("Notification consumer started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start notification consumer: {e}")
            
    def stop_consumer(self):
        """Stop the Kafka consumer"""
        self.running = False
        if self.consumer:
            self.consumer.close()
        if self.consumer_thread:
            self.consumer_thread.join(timeout=5)
        logger.info("Notification consumer stopped")
        
    def _consume_notifications(self):
        """Main consumer loop"""
        while self.running:
            try:
                msg = self.consumer.poll(timeout=1.0)
                if msg is None:
                    continue
                    
                if msg.error():
                    logger.error(f"Consumer error: {msg.error()}")
                    continue
                    
                # Parse notification message
                try:
                    notification_data = json.loads(msg.value().decode('utf-8'))
                    self._handle_notification(notification_data)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse notification message: {e}")
                    
            except KafkaException as e:
                logger.error(f"Kafka exception in consumer: {e}")
            except Exception as e:
                logger.error(f"Unexpected error in consumer: {e}")
                
    def _handle_notification(self, notification_data: dict):
        """Process and broadcast notification to specific user"""
        try:
            user_id = notification_data.get('user_id')
            if not user_id:
                logger.warning("Notification missing user_id")
                return
                
            # Check if user is connected
            if user_id not in self.connected_users or not self.connected_users[user_id]:
                logger.debug(f"User {user_id} not connected, skipping notification")
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
            for session_id in self.connected_users[user_id]:
                self.socketio.emit(
                    'notification',
                    frontend_notification,
                    room=session_id
                )
                
            logger.info(f"Broadcasted notification to user {user_id}: {notification_data['notification']['title']}")
            
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
notification_handler = None

def get_notification_handler(socketio: SocketIO = None) -> NotificationHandler:
    """Get or create notification handler instance"""
    global notification_handler
    if notification_handler is None and socketio:
        notification_handler = NotificationHandler(socketio)
    return notification_handler
