from confluent_kafka import Consumer, KafkaException
import sys
import getopt
import json
import logging
from pprint import pformat
from db.models import User, ForgotPassword, ForgotPasswordStatus, EmailVerify, EmailVerifyStatus
from db.connection import session
from db.utils import generate_random_digits, ensure_kafka_topic
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from decouple import config

broker = config("KAFKA_BROKERS")
group = "tondeka_auth"
topics = ["reset_password","verify_email"]
# Consumer configuration
# See https://github.com/edenhill/librdkafka/blob/master/CONFIGURATION.md
conf = {'bootstrap.servers': broker, 'group.id': group, 'session.timeout.ms': 6000,
        'auto.offset.reset': 'earliest', 'enable.auto.offset.store': False}

# Create logger for consumer (logs will be emitted when poll() is called)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(
    '%(asctime)-15s %(levelname)-8s %(message)s'))
logger.addHandler(handler)

# Create Consumer instance
# Hint: try debug='fetch' to generate some log messages
# kafka-topics.sh --create --topic verify_email --bootstrap-server kafka:9092 --partitions 1 --replication-factor 1

def handle_reset_password(payload: str):
    data = json.loads(payload)
    email = data["email"]
    SMTP_SERVER = config("SMTP_SERVER")  # Replace with your SMTP server
    SMTP_PORT = config("SMTP_PORT")  # Common port for TLS
    EMAIL_ADDRESS = config("EMAIL_ADDRESS")  # Sender email address
    EMAIL_PASSWORD = config("EMAIL_PASSWORD")  # Sender email password

    user = User.query.filter(User.email == email.lower()).first()

    # TODO: check if this user has a pre-existing code

    existingCode = ForgotPassword.query.filter(ForgotPassword.user_id == user.id).filter(
        ForgotPassword.status == ForgotPasswordStatus.PENDING).first()
    if existingCode is not None:
        logger.info(f"found a reset password code: {existingCode.code}")
        code = existingCode.code
    else:
        code = f"{user.id}{generate_random_digits(7)}"
        code_obj = ForgotPassword()
        code_obj.code = code
        code_obj.user = user
        code_obj.status = ForgotPasswordStatus.PENDING
        session.add(code_obj)
        session.commit()
    # TODO: save the code into the db

    # Email content
    recipient = email.lower()
    subject = "Tondeka: Recover Password"
    file_path = "templates/email/recover.html"
    with open(file_path, "r") as file:
        content = file.read()
    # Create a multipart message
    message = MIMEMultipart()
    message["From"] = f"Crypteller<{EMAIL_ADDRESS}>"
    message["To"] = f"{user.first_name} {user.last_name}<{recipient}>"
    message["Subject"] = subject
    html_content = content.replace("{code}", code)

    # Attach the HTML content
    message.attach(MIMEText(html_content, "html"))

    # Send the email
    try:
        with smtplib.SMTP(str(SMTP_SERVER), SMTP_PORT) as server:
            server.starttls()  # Upgrade the connection to secure
            server.login(str(EMAIL_ADDRESS), str(EMAIL_PASSWORD))
            server.sendmail(str(EMAIL_ADDRESS), recipient, message.as_string())
    except Exception as e:
        logger.error(e)

def handle_email_verification(payload: str):
    logger.info(f"Handling email verification for {payload}")
    data = json.loads(payload)
    email = data["email"]
    SMTP_SERVER = config("SMTP_SERVER")  # Replace with your SMTP server
    SMTP_PORT = config("SMTP_PORT")  # Common port for TLS
    EMAIL_ADDRESS = config("EMAIL_ADDRESS")  # Sender email address
    EMAIL_PASSWORD = config("EMAIL_PASSWORD")  # Sender email password

    user = session.query(User).filter(User.email == email.lower()).first()

    if user:
    # TODO: check if this user has a pre-existing code

        existingCode = session.query(EmailVerify).filter(EmailVerify.user_id == user.id).filter(
            EmailVerify.status == EmailVerifyStatus.PENDING).first()
        if existingCode is not None:
            logger.info(f"found email verify code: {existingCode.code}")
            code = existingCode.code
        else:
            code = f"{user.id}{generate_random_digits(7)}"
            code_obj = EmailVerify()
            code_obj.code = code
            code_obj.user = user
            code_obj.status = EmailVerifyStatus.PENDING
            session.add(code_obj)
            session.commit()
        # TODO: save the code into the db

        # Email content
        recipient = email.lower()
        subject = "Digital Tondeka: Account Verification"
        file_path = "templates/email/verify.html"
        with open(file_path, "r") as file:
            content = file.read()
        # Create a multipart message
        message = MIMEMultipart()
        message["From"] = f"Digital Tondeka<{EMAIL_ADDRESS}>"
        message["To"] = f"{user.first_name} {user.last_name}<{recipient}>"
        message["Subject"] = subject
        html_content = content.replace("{code}", code)

        # Attach the HTML content
        message.attach(MIMEText(html_content, "html"))

        # Send the email
        try:
            with smtplib.SMTP(str(SMTP_SERVER), SMTP_PORT) as server:
                server.starttls()  # Upgrade the connection to secure
                server.login(str(EMAIL_ADDRESS), str(EMAIL_PASSWORD))
                server.sendmail(str(EMAIL_ADDRESS), recipient, message.as_string())
        except Exception as e:
            logger.error(e)
    else:
        logger.error(f"User {email} not found")

def print_assignment(consumer, partitions):
    logger.info(f"Assignment: {partitions}")

def auth_consumer():
    c = Consumer(conf, logger=logger)

    for topic in topics:
        logger.info(f"Ensuring kafka topic {topic} exists")
        ensure_kafka_topic(topic, 1, 1, logger)
    # Subscribe to topics
    c.subscribe(topics, on_assign=print_assignment)

    # Read messages from Kafka, print to stdout
    try:
        while True:
            msg = c.poll(timeout=0.0)
            if msg is None:
                continue
            if msg.error():
                raise KafkaException(msg.error())
            else:
                # Proper message
                sys.stderr.write('%% %s [%d] at offset %d with key %s:\n' %
                                (msg.topic(), msg.partition(), msg.offset(),
                                str(msg.key())))
                logger.info(f"{msg.topic()}: {msg.value()}")
                topic = msg.topic()
                match topic:
                    case "reset_password":
                        handle_reset_password(msg.value().decode())
                    case "verify_email":
                        handle_email_verification(msg.value().decode())
                # Store the offset associated with msg to a local cache.
                # Stored offsets are committed to Kafka by a background thread every 'auto.commit.interval.ms'.
                # Explicitly storing offsets after processing gives at-least once semantics.
                c.store_offsets(msg)

    except KeyboardInterrupt:
        sys.stderr.write('%% Aborted by user\n')

    finally:
        # Close down consumer to commit final offsets.
        c.close()
