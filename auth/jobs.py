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
import resend
from datetime import datetime, timedelta

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

# Initialize Resend client
try:
    resend.api_key = config("RESEND_API_KEY")
    RESEND_FROM_EMAIL = config("RESEND_FROM_EMAIL", default="no-reply@badix.io")
    logger.info("Resend client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Resend client: {e}")
    resend.api_key = None

# Create Consumer instance
# Hint: try debug='fetch' to generate some log messages
# kafka-topics.sh --create --topic verify_email --bootstrap-server kafka:9092 --partitions 1 --replication-factor 1

def generate_otp_code():
    """Generate a 6-digit OTP code"""
    return generate_random_digits(6)

def send_email_with_resend(to_email: str, subject: str, html_content: str, user_name: str = None):
    """Send email using Resend API"""
    if not resend.api_key:
        logger.error("Resend API key not configured")
        return False
    
    try:
        params = {
            "from": RESEND_FROM_EMAIL,
            "to": to_email,
            "subject": subject,
            "html": html_content
        }
        
        # Add reply-to if user name is provided
        if user_name:
            params["reply_to"] = f"support@badix.io"
        
        response = resend.Emails.send(params)
        logger.info(f"Email sent successfully via Resend: {response}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email via Resend: {e}")
        return False

def send_email_with_smtp_fallback(to_email: str, subject: str, html_content: str, user_name: str = None):
    """Fallback to SMTP if Resend fails"""
    try:
        SMTP_SERVER = config("SMTP_SERVER")
        SMTP_PORT = config("SMTP_PORT")
        EMAIL_ADDRESS = config("EMAIL_ADDRESS")
        EMAIL_PASSWORD = config("EMAIL_PASSWORD")
        
        message = MIMEMultipart()
        message["From"] = f"DT Exchange<{EMAIL_ADDRESS}>"
        message["To"] = f"{user_name or 'User'}<{to_email}>" if user_name else to_email
        message["Subject"] = subject
        message.attach(MIMEText(html_content, "html"))
        
        with smtplib.SMTP(str(SMTP_SERVER), SMTP_PORT) as server:
            server.starttls()
            server.login(str(EMAIL_ADDRESS), str(EMAIL_PASSWORD))
            server.sendmail(str(EMAIL_ADDRESS), to_email, message.as_string())
        
        logger.info(f"Email sent successfully via SMTP fallback to {to_email}")
        return True
    except Exception as e:
        logger.error(f"SMTP fallback also failed: {e}")
        return False

def handle_reset_password(payload: str):
    data = json.loads(payload)
    email = data["email"]
    
    user = User.query.filter(User.email == email.lower()).first()
    if not user:
        logger.error(f"User not found for email: {email}")
        return

    # Check for existing pending code
    existing_code = ForgotPassword.query.filter(
        ForgotPassword.user_id == user.id,
        ForgotPassword.status == ForgotPasswordStatus.PENDING
    ).first()
    
    if existing_code:
        logger.info(f"Found existing reset password code: {existing_code.code}")
        code = existing_code.code
    else:
        # Generate new 6-digit code
        code = generate_otp_code()
        code_obj = ForgotPassword()
        code_obj.code = code
        code_obj.user = user
        code_obj.status = ForgotPasswordStatus.PENDING
        session.add(code_obj)
        session.commit()
        logger.info(f"Generated new reset password code: {code}")

    # Email content
    recipient = email.lower()
    subject = "DT Exchange: Reset Your Password"
    file_path = "templates/email/recover.html"
    
    try:
        with open(file_path, "r") as file:
            content = file.read()
        
        html_content = content.replace("{code}", code)
        
        # Try Resend first, fallback to SMTP
        success = send_email_with_resend(recipient, subject, html_content, user.first_name)
        if not success:
            success = send_email_with_smtp_fallback(recipient, subject, html_content, user.first_name)
        
        if success:
            logger.info(f"Password reset email sent successfully to {email}")
        else:
            logger.error(f"Failed to send password reset email to {email}")
            
    except Exception as e:
        logger.error(f"Error in password reset email process: {e}")

def handle_email_verification(payload: str):
    logger.info(f"Handling email verification for {payload}")
    data = json.loads(payload)
    email = data["email"]
    
    user = session.query(User).filter(User.email == email.lower()).first()
    if not user:
        logger.error(f"User {email} not found")
        return

    # Check for existing pending code
    existing_code = session.query(EmailVerify).filter(
        EmailVerify.user_id == user.id,
        EmailVerify.status == EmailVerifyStatus.PENDING
    ).first()
    
    if existing_code:
        # Check if code is still valid (10 minutes)
        code_age = datetime.utcnow() - existing_code.created_at
        if code_age < timedelta(minutes=10):
            logger.info(f"Found valid email verify code: {existing_code.code}")
            code = existing_code.code
        else:
            # Code expired, mark as expired and generate new one
            existing_code.status = EmailVerifyStatus.EXPIRED
            session.commit()
            code = None
    else:
        code = None
    
    if not code:
        # Generate new 6-digit OTP code
        code = generate_otp_code()
        code_obj = EmailVerify()
        code_obj.code = code
        code_obj.user = user
        code_obj.status = EmailVerifyStatus.PENDING
        session.add(code_obj)
        session.commit()
        logger.info(f"Generated new email verification code: {code}")

    # Email content
    recipient = email.lower()
    subject = "DT Exchange: Verify Your Email Address"
    file_path = "templates/email/verify.html"
    
    try:
        with open(file_path, "r") as file:
            content = file.read()
        
        html_content = content.replace("{code}", code)
        
        # Try Resend first, fallback to SMTP
        success = send_email_with_resend(recipient, subject, html_content, user.first_name)
        if not success:
            success = send_email_with_smtp_fallback(recipient, subject, html_content, user.first_name)
        
        if success:
            logger.info(f"Email verification sent successfully to {email}")
        else:
            logger.error(f"Failed to send email verification to {email}")
            
    except Exception as e:
        logger.error(f"Error in email verification process: {e}")

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
