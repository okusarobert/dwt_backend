import eventlet
eventlet.monkey_patch()
import json
import sys
import logging
import os
import time
from flask import Flask, request, jsonify, Blueprint
import requests
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS
import jwt
import os
from decouple import config
from db.connection import get_session
from db.models import User
import logging
import json
from datetime import datetime
from confluent_kafka import Producer, Consumer, KafkaException
import threading
from multiprocessing import Process
from confluent_kafka.admin import AdminClient, NewTopic
import redis
from crypto_price_service import CryptoPriceService
from redis_notification_handler import get_redis_notification_handler

# Set up logging first
logger = logging.getLogger('websocket')
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(
    '%(asctime)-15s %(levelname)-8s %(message)s'))
logger.addHandler(handler)

# Now try to import database connection
try:
    from db.connection import session
    logger.info("BOOT: Database connection imported successfully")
except ImportError as e:
    logger.warning(f"BOOT: Database connection not available: {e}")
    session = None


app = Flask(__name__)

# Set secret key with fallback
try:
    secret_key = config("APP_SECRET")
except:
    secret_key = "dev-secret-key-change-in-production"
    logger.warning("Using default secret key - change in production")

app.config['SECRET_KEY'] = secret_key
socketio = SocketIO(
    app, 
    async_mode='eventlet', 
    cors_allowed_origins="*", 
    message_queue='redis://redis:6379',
    ping_timeout=60,
    ping_interval=25,
    logger=True,
    engineio_logger=True
)

# Initialize Redis notification handler
notification_handler = get_redis_notification_handler(socketio)

@app.route('/health')
def health_check():
    """Health check endpoint"""
    crypto_status = {
        'available': crypto_price_service is not None,
        'running': crypto_price_service.is_running if crypto_price_service else False,
        'cached_prices': len(crypto_price_service.get_cached_prices()) if crypto_price_service else 0
    } if crypto_price_service else {'available': False}
    
    return {
        'status': 'healthy',
        'service': 'websocket',
        'timestamp': time.time(),
        'crypto_service': crypto_status,
        'redis_connected': True,  # We'll add actual Redis health check later
        'kafka_connected': True   # We'll add actual Kafka health check later
    }
conf = {'bootstrap.servers': "kafka:9092", 'group.id': "transaction-processor", 'session.timeout.ms': 6000,
        'enable.auto.commit': True, 'enable.auto.offset.store': False}

def create_topic_if_not_exists(admin_client, topic_name):
    """Create a Kafka topic if it doesn't exist."""
    if admin_client is None:
        logger.warning("Admin client not available, skipping topic creation")
        return
        
    try:
        cluster_metadata = admin_client.list_topics(timeout=10)
        if topic_name not in cluster_metadata.topics:
            new_topic = NewTopic(topic_name, num_partitions=1, replication_factor=1)
            admin_client.create_topics([new_topic])
            logger.info(f"Topic '{topic_name}' created.")
        else:
            logger.info(f"Topic '{topic_name}' already exists.")
    except Exception as e:
        logger.error(f"Error creating topic '{topic_name}': {e}")

def print_assignment(consumer, partitions):
    print('Assignment:', partitions)

def redis_listener(socketio):
    
    logger.info("BOOT: Starting Redis pubsub listener thread...")
    
    while True:  # Retry loop
        try:
            redis_host = os.environ.get('REDIS_HOST', 'localhost')
            redis_port = int(os.environ.get('REDIS_PORT', 6379))
            redis_username = os.environ.get('REDIS_USERNAME', None)
            redis_password = os.environ.get('REDIS_PASSWORD', None)
            redis_db = int(os.environ.get('REDIS_DB', 0))

            redis_kwargs = {
                "host": redis_host,
                "port": redis_port,
                "db": redis_db,
                "socket_connect_timeout": 5,
                "socket_timeout": 5,
                "retry_on_timeout": True,
                "health_check_interval": 30
            }
            if redis_username:
                redis_kwargs["username"] = redis_username
            if redis_password:
                redis_kwargs["password"] = redis_password

            r = redis.Redis(**redis_kwargs)
            
            # Test connection
            r.ping()
            logger.info("BOOT: Redis connection established successfully")
            
            pubsub = r.pubsub()
            pubsub.subscribe('transaction_updates')
            
            logger.info("BOOT: Redis pubsub listener started successfully")
            
            for message in pubsub.listen():
                try:
                    logger.info(f"Redis message: {message}")
                    if message['type'] == 'message':
                        try:
                            data = json.loads(message['data'])
                            transaction_id = data.get('transaction_id')
                            socketio.emit('tx_update', data, to=transaction_id)
                        except Exception as e:
                            logger.error(f"Error processing redis pubsub message: {e!r}")
                        finally:
                            # session.remove()
                            logger.info("PUBSUB: done processing message, time to close db sessions")
                except redis.ConnectionError as e:
                    logger.error(f"Redis connection lost: {e}")
                    break
                except Exception as e:
                    logger.error(f"Unexpected error in Redis listener: {e}")
                    break
                    
        except redis.ConnectionError as e:
            logger.error(f"BOOT: Redis connection failed: {e}")
            logger.info("BOOT: Retrying Redis connection in 10 seconds...")
            time.sleep(10)
            continue
        except Exception as e:
            logger.error(f"BOOT: Failed to start Redis listener: {e}")
            logger.info("BOOT: Retrying in 10 seconds...")
            time.sleep(10)
            continue

@socketio.on('join_tx')
def on_join_order(data):
    """Join a WebSocket room for a specific transaction."""
    transaction_id = data['transaction_id']
    join_room(transaction_id)
    emit('message', f'Joined room for transaction {transaction_id}', to=transaction_id)

@socketio.on('subscribe')
def on_subscribe(data):
    """Handle client subscriptions to different channels."""
    channel = data.get('channel')
    if channel == 'crypto-prices':
        # Send initial cached prices
        if crypto_price_service:
            cached_prices = crypto_price_service.get_cached_prices()
            if cached_prices:
                emit('crypto-prices', cached_prices)
            logger.info(f"Client subscribed to {channel}")
        else:
            logger.warning("Crypto price service not available")
            emit('error', {'message': 'Crypto price service not available'})
    else:
        logger.info(f"Unknown subscription channel: {channel}")

@socketio.on('connect')
def on_connect():
    """Handle client connection."""
    logger.info("Client connected to WebSocket")
    # Send welcome message with available channels
    emit('message', {
        'type': 'welcome',
        'channels': ['crypto-prices', 'transaction_updates'],
        'message': 'Connected to DWT Exchange WebSocket'
    })

@socketio.on('disconnect')
def on_disconnect():
    """Handle client disconnection."""
    logger.info("Client disconnected from WebSocket")

# def start_kafka_consumer():
#     kafka_consumer()

# Initialize Kafka admin client
try:
    logger.info("BOOT: Initializing Kafka Admin Client...")
    admin_conf = {'bootstrap.servers': "kafka:9092"}
    admin_client = AdminClient(admin_conf)
    logger.info("BOOT: Kafka Admin Client initialized.")

    logger.info("BOOT: Ensuring 'transaction' topic exists...")
    create_topic_if_not_exists(admin_client, 'transaction')
    logger.info("BOOT: 'transaction' topic check complete.")
except Exception as e:
    logger.error(f"BOOT: Failed to initialize Kafka admin client: {e}")
    logger.info("BOOT: Continuing without Kafka functionality")
    admin_client = None

# Initialize crypto price service
crypto_price_service = None
try:
    logger.info("BOOT: Initializing real crypto price service...")
    crypto_price_service = CryptoPriceService(socketio)
    logger.info("BOOT: Real crypto price service initialized successfully.")
except Exception as e:
    logger.error(f"BOOT: Failed to initialize crypto price service: {e}")
    logger.info("BOOT: Continuing without crypto price functionality")
    crypto_price_service = None


# logger.info("BOOT: Starting Kafka consumer thread...")
# threading.Thread(target=kafka_consumer, daemon=True).start()
# logger.info("BOOT: Kafka consumer thread started.")


# logger.info("BOOT: Starting heartbeat thread...")
def heartbeat():
    while True:
        logger.info("Heartbeat: Websocket service is alive.")
        socketio.sleep(10)

# logger.info("BOOT: Heartbeat thread started.")

def start_background_tasks():
    try:
        logger.info("BOOT: Starting Redis pubsub listener thread...")
        redis_thread = threading.Thread(target=redis_listener, args=(socketio,), daemon=True)
        redis_thread.start()
        logger.info("BOOT: Redis listener thread started")
    except Exception as e:
        logger.error(f"BOOT: Failed to start Redis listener thread: {e}")
    
    try:
        logger.info("BOOT: Starting Redis notification handler in background...")
        socketio.start_background_task(target=notification_handler.start_consumer)
        logger.info("BOOT: Redis notification handler background task started")
    except Exception as e:
        logger.error(f"BOOT: Failed to start Redis notification handler: {e}")
    
    try:
        socketio.start_background_task(target=heartbeat)
        logger.info("BOOT: Heartbeat task started")
    except Exception as e:
        logger.error(f"BOOT: Failed to start heartbeat task: {e}")
    
    # Start crypto price streaming
    if crypto_price_service:
        try:
            logger.info("BOOT: Starting crypto price streaming...")
            socketio.start_background_task(crypto_price_service.start_price_streaming_sync, 10)
            logger.info("BOOT: Crypto price streaming started")
        except Exception as e:
            logger.error(f"BOOT: Failed to start crypto price streaming: {e}")
    else:
        logger.warning("BOOT: Skipping crypto price streaming - service not available")
    
    logger.info("BOOT: Background tasks initialization completed.")

# Start background tasks when the module is imported (works for Gunicorn and direct run)
try:
    start_background_tasks()
    logger.info("BOOT: All background tasks started successfully")
except Exception as e:
    logger.error(f"BOOT: Error starting background tasks: {e}")
    logger.info("BOOT: Service will start with limited functionality")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_user_from_token(token):
    session = None
    try:
        payload = jwt.decode(token, config('SECRET_KEY', default='your-secret-key'), algorithms=['HS256'])
        session = get_session()
        user = session.query(User).filter(User.id == payload['user_id']).first()
        return user
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
    except Exception as e:
        logger.error(f"Error verifying token: {e}")
        return None
    finally:
        if session:
            session.close()

def verify_token(token):
    """Verify JWT token and return user"""
    return get_user_from_token(token)

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info(f"Client connected: {request.sid}")
    emit('connected', {'message': 'Connected to DT Exchange WebSocket'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info(f"Client disconnected: {request.sid}")
    # Remove user from all rooms
    for room in socketio.server.rooms(request.sid):
        if room != request.sid:
            leave_room(room)

@socketio.on('authenticate')
def handle_authentication(data):
    """Authenticate user and join user-specific room"""
    try:
        token = data.get('token')
        if not token:
            emit('auth_error', {'message': 'Token required'})
            return

        user = verify_token(token)
        if not user:
            emit('auth_error', {'message': 'Invalid token'})
            return

        # Join user-specific room
        user_room = f"user_{user.id}"
        join_room(user_room)
        
        # Join trading room for general updates
        join_room('trading')
        
        logger.info(f"User {user.id} authenticated and joined room {user_room}")
        emit('authenticated', {
            'message': 'Authentication successful',
            'user_id': user.id,
            'room': user_room
        })
        
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        emit('auth_error', {'message': 'Authentication failed'})

@socketio.on('join_trading')
def handle_join_trading():
    """Join trading room for real-time updates"""
    join_room('trading')
    emit('joined_trading', {'message': 'Joined trading room'})

@socketio.on('leave_trading')
def handle_leave_trading():
    """Leave trading room"""
    leave_room('trading')
    emit('left_trading', {'message': 'Left trading room'})

def broadcast_trade_update(trade_data):
    """Broadcast trade update to all users in trading room"""
    try:
        message = {
            'type': 'trade_update',
            'data': trade_data,
            'timestamp': datetime.utcnow().isoformat()
        }
        socketio.emit('trade_update', message, room='trading')
        logger.info(f"Broadcasted trade update: {trade_data.get('id')}")
    except Exception as e:
        logger.error(f"Error broadcasting trade update: {e}")

def send_user_notification(user_id, notification_data):
    """Send notification to specific user"""
    try:
        message = {
            'type': 'notification',
            'data': notification_data,
            'timestamp': datetime.utcnow().isoformat()
        }
        socketio.emit('notification', message, room=f"user_{user_id}")
        logger.info(f"Sent notification to user {user_id}")
    except Exception as e:
        logger.error(f"Error sending notification to user {user_id}: {e}")

def broadcast_price_update(price_data):
    """Broadcast price update to all users"""
    try:
        message = {
            'type': 'price_update',
            'data': price_data,
            'timestamp': datetime.utcnow().isoformat()
        }
        socketio.emit('price_update', message, room='trading')
        logger.info(f"Broadcasted price update for {price_data.get('crypto_currency')}")
    except Exception as e:
        logger.error(f"Error broadcasting price update: {e}")

def broadcast_system_message(message_data):
    """Broadcast system message to all users"""
    try:
        message = {
            'type': 'system_message',
            'data': message_data,
            'timestamp': datetime.utcnow().isoformat()
        }
        socketio.emit('system_message', message, room='trading')
        logger.info(f"Broadcasted system message: {message_data.get('title')}")
    except Exception as e:
        logger.error(f"Error broadcasting system message: {e}")

# HTTP endpoints for external services to trigger WebSocket events

@app.route('/api/websocket/broadcast/trade', methods=['POST'])
def broadcast_trade():
    """HTTP endpoint to broadcast trade updates"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        broadcast_trade_update(data)
        return jsonify({'success': True, 'message': 'Trade update broadcasted'})
    except Exception as e:
        logger.error(f"Error broadcasting trade: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/websocket/notify/user/<int:user_id>', methods=['POST'])
def notify_user(user_id):
    """HTTP endpoint to send notification to specific user"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        send_user_notification(user_id, data)
        return jsonify({'success': True, 'message': f'Notification sent to user {user_id}'})
    except Exception as e:
        logger.error(f"Error sending notification: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/websocket/broadcast/price', methods=['POST'])
def broadcast_price():
    """HTTP endpoint to broadcast price updates"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        broadcast_price_update(data)
        return jsonify({'success': True, 'message': 'Price update broadcasted'})
    except Exception as e:
        logger.error(f"Error broadcasting price: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/websocket/broadcast/system', methods=['POST'])
def broadcast_system():
    """HTTP endpoint to broadcast system messages"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        broadcast_system_message(data)
        return jsonify({'success': True, 'message': 'System message broadcasted'})
    except Exception as e:
        logger.error(f"Error broadcasting system message: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/websocket/status', methods=['GET'])
def websocket_status():
    """Get WebSocket server status"""
    try:
        connected_clients = len(socketio.server.manager.rooms)
        return jsonify({
            'success': True,
            'status': 'running',
            'connected_clients': connected_clients,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting WebSocket status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# WebSocket event handlers for notifications
@socketio.on('connect')
def handle_connect(auth):
    """Handle client connection"""
    try:
        # Extract user info from auth token
        if auth and 'token' in auth:
            token = auth['token']
            try:
                # Decode JWT token to get user_id
                payload = jwt.decode(token, secret_key, algorithms=['HS256'])
                user_id = payload.get('user_id')
                
                if user_id:
                    # Register user connection with notification handler
                    notification_handler.user_connected(request.sid, user_id)
                    logger.info(f"User {user_id} connected for notifications")
                    emit('connection_status', {'status': 'connected', 'user_id': user_id})
                else:
                    logger.warning("No user_id in token payload")
                    
            except jwt.InvalidTokenError:
                logger.warning("Invalid JWT token provided")
        else:
            logger.info("Client connected without authentication")
            
    except Exception as e:
        logger.error(f"Error handling connection: {e}")

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    try:
        notification_handler.user_disconnected(request.sid)
        logger.info(f"Client {request.sid} disconnected")
    except Exception as e:
        logger.error(f"Error handling disconnection: {e}")

@socketio.on('join_notifications')
def handle_join_notifications(data):
    """Handle user joining notification room"""
    try:
        logger.info(f"🔔 join_notifications event received: {data}")
        user_id = data.get('user_id')
        if user_id:
            logger.info(f"🔔 Registering user {user_id} with session {request.sid}")
            notification_handler.user_connected(request.sid, user_id)
            emit('joined_notifications', {'user_id': user_id})
            logger.info(f"🔔 User {user_id} successfully joined notifications")
        else:
            logger.warning(f"🔔 No user_id provided in join_notifications: {data}")
    except Exception as e:
        logger.error(f"🔔 Error joining notifications: {e}")
        import traceback
        logger.error(f"🔔 Full traceback: {traceback.format_exc()}")

@socketio.on('mark_notification_read')
def handle_mark_read(data):
    """Handle marking notification as read"""
    try:
        notification_id = data.get('notification_id')
        user_id = data.get('user_id')
        # Here you could update notification status in database
        logger.info(f"Notification {notification_id} marked as read by user {user_id}")
        emit('notification_read', {'notification_id': notification_id})
    except Exception as e:
        logger.error(f"Error marking notification as read: {e}")

if __name__ == '__main__':
    try:
        logger.info("BOOT: Starting Flask-SocketIO server...")
        
        # Start SocketIO server first
        # socketio.start_background_task(target=lambda: notification_handler.start_consumer())
        # logger.info("BOOT: Notification handler will start in background")
        
        socketio.run(app, host='0.0.0.0', port=5000, debug=True, use_reloader=False)
    except Exception as e:
        logger.error(f"BOOT: Failed to start server: {e}")
        sys.exit(1)
    # finally:
    #     # Clean shutdown
    #     if notification_handler:
    #         notification_handler.stop_consumer()
