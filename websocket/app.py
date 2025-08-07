import eventlet
eventlet.monkey_patch()
import json
import sys
from flask import Flask, request, jsonify, Blueprint
from db.connection import session
import requests
import logging, io
from flask_socketio import SocketIO, emit, join_room
from confluent_kafka import Producer, Consumer, KafkaException
import threading
from decouple import config
from multiprocessing import Process
from confluent_kafka.admin import AdminClient, NewTopic
import redis
import os


logger = logging.getLogger('websocket')
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(
    '%(asctime)-15s %(levelname)-8s %(message)s'))
logger.addHandler(handler)


app = Flask(__name__)
app.config['SECRET_KEY'] = config("APP_SECRET")
socketio = SocketIO(app, async_mode='eventlet', cors_allowed_origins="*", message_queue='redis://redis:6379')
conf = {'bootstrap.servers': "kafka:9092", 'group.id': "transaction-processor", 'session.timeout.ms': 6000,
        'enable.auto.commit': True, 'enable.auto.offset.store': False}

def create_topic_if_not_exists(admin_client, topic_name):
    """Create a Kafka topic if it doesn't exist."""
    cluster_metadata = admin_client.list_topics(timeout=10)
    if topic_name not in cluster_metadata.topics:
        new_topic = NewTopic(topic_name, num_partitions=1, replication_factor=1)
        admin_client.create_topics([new_topic])
        logger.info(f"Topic '{topic_name}' created.")
    else:
        logger.info(f"Topic '{topic_name}' already exists.")

def print_assignment(consumer, partitions):
    print('Assignment:', partitions)

def redis_listener(socketio):
    
    logger.info("BOOT: Starting Redis pubsub listener thread...")
    redis_host = os.environ.get('REDIS_HOST', 'localhost')
    redis_port = int(os.environ.get('REDIS_PORT', 6379))
    redis_username = os.environ.get('REDIS_USERNAME', None)
    redis_password = os.environ.get('REDIS_PASSWORD', None)
    redis_db = int(os.environ.get('REDIS_DB', 0))

    redis_kwargs = {
        "host": redis_host,
        "port": redis_port,
        "db": redis_db
    }
    if redis_username:
        redis_kwargs["username"] = redis_username
    if redis_password:
        redis_kwargs["password"] = redis_password

    r = redis.Redis(**redis_kwargs)
    pubsub = r.pubsub()
    pubsub.subscribe('transaction_updates')
    for message in pubsub.listen():
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

@socketio.on('join_tx')
def on_join_order(data):
    """Join a WebSocket room for a specific transaction."""
    transaction_id = data['transaction_id']
    join_room(transaction_id)
    emit('message', f'Joined room for transaction {transaction_id}', to=transaction_id)

# def start_kafka_consumer():
#     kafka_consumer()

logger.info("BOOT: Initializing Kafka Admin Client...")
admin_conf = {'bootstrap.servers': "kafka:9092"}
admin_client = AdminClient(admin_conf)
logger.info("BOOT: Kafka Admin Client initialized.")

logger.info("BOOT: Ensuring 'transaction' topic exists...")
create_topic_if_not_exists(admin_client, 'transaction')
logger.info("BOOT: 'transaction' topic check complete.")


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
    logger.info("BOOT: Starting Redis pubsub listener thread...")
    threading.Thread(target=redis_listener, args=(socketio,), daemon=True).start()
    socketio.start_background_task(target=heartbeat)
    logger.info("BOOT: Background tasks started.")

# Start background tasks when the module is imported (works for Gunicorn and direct run)
start_background_tasks()

if __name__ == '__main__':
    logger.info("BOOT: Starting Flask-SocketIO server...")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, use_reloader=False)
