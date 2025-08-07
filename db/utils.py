import random
import hashlib
import os
import json
import base64
from flask import request, jsonify, g, current_app
from functools import wraps
from decouple import config
import jwt
from .models import User, UserRole
from .connection import session
from confluent_kafka.admin import AdminClient, NewTopic
from confluent_kafka import Producer, KafkaException
import redis
from typing import Tuple
from pydantic import BaseModel, Field
import enum
import logging
from db.wallet import Account


def generate_password_hash(plain_password, iterations=216000) -> str:
    """
    Generates a password hash similar to Django's format without using Django.

    Args:
        plain_password (str): The plain text password to hash.
        iterations (int): The number of PBKDF2 iterations (default: 260,000).

    Returns:
        str: The hashed password in the format `algorithm$iterations$salt$hash`.
    """
    # Generate a random salt
    salt = base64.b64encode(os.urandom(16)).decode('utf-8')

    # Hash the password using PBKDF2 with SHA-256
    hash_bytes = hashlib.pbkdf2_hmac(
        'sha256',  # Hash algorithm
        plain_password.encode('utf-8'),  # Password as bytes
        salt.encode('utf-8'),  # Salt as bytes
        iterations  # Number of iterations
    )

    # Encode the resulting hash in base64
    password_hash = base64.b64encode(hash_bytes).decode('utf-8')

    # Return the formatted string
    return f"pbkdf2_sha256${iterations}${salt}${password_hash}"


def verify_password(plain_password, stored_hash) -> bool:
    """
    Verifies a plain text password against a stored hash.

    Args:
        plain_password (str): The plain text password to verify.
        stored_hash (str): The stored password hash in the format `algorithm$iterations$salt$hash`.

    Returns:
        bool: True if the password matches, False otherwise.
    """
    try:
        # Split the stored hash into components
        algorithm, iterations, salt, stored_password_hash = stored_hash.split(
            '$')

        if algorithm != 'pbkdf2_sha256':
            raise ValueError("Unsupported hash algorithm")

        # Recompute the hash using the same salt and iterations
        iterations = int(iterations)
        hash_bytes = hashlib.pbkdf2_hmac(
            'sha256',
            plain_password.encode('utf-8'),
            salt.encode('utf-8'),
            iterations
        )

        # Encode the recomputed hash in base64
        recomputed_hash = base64.b64encode(hash_bytes).decode('utf-8')

        # Compare the recomputed hash with the stored hash
        return recomputed_hash == stored_password_hash
    except Exception as e:
        print("Error verifying password:", e)
        return False


def generate_random_digits(n: int) -> int:
    random_number = random.randint(10**(n-1), 10**n - 1)
    return random_number


def generate_random_alpha(n: int) -> str:
    import string
    return ''.join(random.choices(string.ascii_letters, k=n))


def decode_token(token):
    """Decode a JWT and return the payload."""
    try:
        secret = config("JWT_SECRET")
        return jwt.decode(token, secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return {"error": "Token has expired"}
    except jwt.InvalidTokenError:
        return {"error": "Invalid token"}

# Middleware decorator


def token_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            current_app.logger.info("Missing token")
            return jsonify({"msg": "Missing token"}), 401

        # Extract the token
        parts = auth_header.split(" ")
        if len(parts) != 2 or parts[0].lower() != "bearer":
            current_app.logger.info("Invalid token format")
            return jsonify({"msg": "Invalid token format"}), 401

        token = parts[1]
        decoded = decode_token(token)

        if "error" in decoded:
            current_app.logger.info(f"Invalid token: {decoded['error']}")
            return jsonify({"msg": decoded["error"]}), 401

        # Attach user to request context
        user = session.query(User).filter(User.id == decoded["user_id"]).first()
        g.user = user
        current_app.logger.info(f"user: {user}: {decoded['user_id']}")
        return f(*args, **kwargs)

    return decorated_function


def is_admin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = g.user
        current_app.logger.info("is_admin is accessed")
        if user is None:
            current_app.logger.info("user is None")
            current_app.logger.info(f"Unauthorized: {user}")
            return jsonify({"general": "Unauthorized"}), 401
        if user.role != UserRole.ADMIN:
            current_app.logger.info(f"user is not admin: {user.role}")
            return jsonify({"general": "Unauthorized"}), 401
        current_app.logger.info(f"user is admin: {user.role}")
        return f(*args, **kwargs)

    return decorated_function


def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions


# Example query for a table named "users"
def paginate(query, page, per_page):
    """
    Custom pagination for SQLAlchemy queries.

    Args:
        query: SQLAlchemy query object.
        page: Current page number (1-based index).
        per_page: Number of items per page.

    Returns:
        A tuple containing the paginated items and the total count.
    """
    total_count = query.count()  # Total number of items
    offset = (page - 1) * per_page
    total_pages = (total_count + per_page - 1) // per_page
    # Paginate with LIMIT and OFFSET
    items = query.offset(offset).limit(per_page).all()
    return items, total_count, total_pages


def model_to_dict(obj):
    result = {}
    for c in obj.__table__.columns:
        value = getattr(obj, c.name)
        if isinstance(value, enum.Enum):
            value = value.value
        result[c.name] = value
    return result


def delivery_report(err, msg):
    """Callback to report delivery status of a message."""
    if err:
        current_app.logger.info(f"Message delivery failed: {err}")
    else:
        current_app.logger.info(
            f"Message delivered to {msg.topic()} [{msg.partition()}] at offset {msg.offset()}")


def produce_message(topic: str, key: str, payload: dict, logger=None):
    # Configuration for the Kafka producer
    if logger is not None:
        logger.info(f"Producing message to topic {topic} with key {key} and payload {payload}")
    
    brokers = config("KAFKA_BROKERS")
    producer_config = {
        "bootstrap.servers": brokers
    }
    # Create a Kafka producer instance
    producer = Producer(producer_config)

    producer.produce(
        topic,
        key=key,
        value=json.dumps(payload),
        callback=delivery_report,
    )
    # Poll for delivery reports (non-blocking)
    producer.poll(0)
    producer.flush()


def ensure_kafka_topic(topic_name, num_partitions=1, replication_factor=1, logger=None):
    if logger is None:
        logger = logging.getLogger(__name__)
    logger.info(f"Ensuring kafka topic '{topic_name}' exists")
    brokers = config("KAFKA_BROKERS")
    admin_client = AdminClient({"bootstrap.servers": brokers})

    # Check if topic exists
    topic_metadata = admin_client.list_topics(timeout=10)
    if topic_name in topic_metadata.topics:
        logger.info(f"Kafka topic '{topic_name}' already exists.")
        return

    # Create topic if it does not exist
    new_topic = NewTopic(topic_name, num_partitions=num_partitions,
                         replication_factor=replication_factor)
    fs = admin_client.create_topics([new_topic])

    for topic, f in fs.items():
        try:
            f.result()  # The result itself is None
            logger.info(f"Kafka topic '{topic}' created.")
        except Exception as e:
            logger.error(f"Failed to create topic '{topic}': {e!r}")


def generate_unique_account_number(session, length=10):
    """
    Generate a unique random account number of specified length (8-10 digits).
    Ensures uniqueness in the Account table.
    """
    min_value = 10**(length-1)
    max_value = 10**length - 1
    while True:
        account_number = str(random.randint(min_value, max_value))
        exists = session.query(Account).filter_by(account_number=account_number).first()
        if not exists:
            return account_number
