from decouple import config
import os
import logging
import sys
from flask import Flask, request, jsonify, g
from db.connection import session
from db import User, UserRole, EmailVerify, EmailVerifyStatus, ForgotPassword, ForgotPasswordStatus
from pydantic import BaseModel, Field
from typing import Optional
import re
from db.utils import generate_password_hash, produce_message, token_required, verify_password, generate_random_digits
from db.dto import LoginDto, ForgotPasswordDto, VerifyEmailDto, VerifyResetPasswordDto, ResetPasswordDto, RegisterDto, validate_login, validate_registration, validate_reset_pwd, validate_forgot_password
import jwt
import datetime
import json
from jobs import auth_consumer
import threading
from shared.kafka_producer import get_kafka_producer
import uuid



# from flask_sqlalchemy import SQLAlchemy

# db = SQLAlchemy()

# 216000 - iterations
app = Flask(__name__)
# db.init_app(app)

# def start_consumer():
#     logger.info("Starting auth consumer")
#     threading.Thread(target=auth_consumer, daemon=True).start()


# @app.before_first_request
# def before_first_request_func():
#     start_consumer()

logging.basicConfig(
    level=logging.DEBUG,  # Set the logging level
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler()  # Logs to console
    ]
)

logger = logging.getLogger(__name__)

producer = get_kafka_producer()
USER_REGISTERED_TOPIC = os.getenv("USER_REGISTERED_TOPIC", "user.registered")


# In-memory store for demo (optional, can be removed later)
transaction_refs = {}

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    data = LoginDto(**data)
    errors = validate_login(data, session)
    if not errors:
        # login is successful
        secret = config("JWT_SECRET")
        user = session.query(User).filter(User.email == data.email.lower()).first()
        payload = {"user_id": user.id, "exp": datetime.datetime.utcnow(
        ) + datetime.timedelta(hours=24*30)}
        encoded = jwt.encode(payload, secret, algorithm="HS256")
        return jsonify({"token": encoded}), 200
    else:
        return jsonify(errors), 401


@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    data = RegisterDto(**data)
    errors = validate_registration(data, session, logger)
    if not errors:
        try:
            user = User()
            user.first_name = data.first_name
            user.last_name = data.last_name
            user.email = data.email.lower()
            user.phone_number = data.phone_number
            user.encrypted_pwd = generate_password_hash(data.password, 216000)
            user.sponsor_code = data.sponsor_code
            user.role = UserRole.USER
            ref_code = generate_random_digits(8)
            user.ref_code = f"{ref_code}"
            user.country = "UG"
            session.add(user)
            account = Account()
            account.user_id = user.id
            account.currency_code = "UGX"
            account.balance = 0
            account.locked_amount = 0
            account.status = AccountStatus.ACTIVE
            session.add(account)
            session.commit()
            topic = "verify_email"
            # send a verification code
            key = f"{generate_random_digits(20)}"
            payload = {"email": data.email}
            produce_message(topic, key, payload, logger)
            producer.send(USER_REGISTERED_TOPIC, {"user_id": user.id})
            res = {"message": "User registered successfully"}
            return jsonify(res), 201
        except Exception as e:
            logger.error("Error registering user: %r", e)
            session.rollback()
            return jsonify({"message":"Error registering user"}), 500
    else:
        return jsonify(errors), 400


@app.route('/verify-email', methods=['POST'])
def verify_email():
    data = request.get_json()
    data = VerifyEmailDto(**data)
    if len(data.code) < 9:
        payload = {"code": "Invalid verification code"}
        return jsonify(payload), 400
    code = EmailVerify.query.filter(EmailVerify.code == data.code).filter(
        EmailVerify.status == EmailVerifyStatus.PENDING).first()
    logger.info("CODE: %s", code)
    if code is None:
        payload = {"code": "Invalid verification code"}
        return jsonify(payload), 400
    user = code.user
    user.email_verified = True
    code.status = EmailVerifyStatus.USED
    session.commit()
    payload = {"message": "Email verified successfully"}
    return jsonify(payload), 200


@app.route('/ping-forgot-pwd', methods=['POST'])
def ping_forgot_pwd():
    data = request.get_json()
    data = VerifyResetPasswordDto(**data)
    if len(data.code) < 8:
        payload = {"code": "Invalid verification code"}
        return jsonify(payload), 400
    code = ForgotPassword.query.filter(ForgotPassword.code == data.code).filter(
        ForgotPassword.status == ForgotPasswordStatus.PENDING).first()
    if code is None:
        payload = {"code": "Invalid verification code"}
        return jsonify(payload), 400
    payload = {"message": "code is valid"}
    return jsonify(payload), 200


@app.route('/reset-pwd', methods=['POST'])
def reset_pwd():
    data = request.get_json()
    data = ResetPasswordDto(**data)
    errors = validate_reset_pwd(data)
    if not errors:
        code = ForgotPassword.query.filter(ForgotPassword.code == data.code).filter(
            ForgotPassword.status == ForgotPasswordStatus.PENDING).first()
        user = code.user
        user.encrypted_pwd = generate_password_hash(data.password)
        code.status = ForgotPasswordStatus.USED
        session.commit()
        payload = {"message": "Password successfully changed"}
        return jsonify(payload), 200
    else:
        return jsonify(errors), 400


# forgot password


@app.route('/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json()
    data = ForgotPasswordDto(**data)
    errors = validate_forgot_password(data)
    key = f"{generate_random_digits(20)}"
    if not errors:
        # SMTP configuration
        topic = "reset_password"
        payload = {"email": data.email}
        produce_message(topic, key, payload)
        res = {
            "message": "If account matching the email address is found, a six digit code has been sent to your email address"}
        return jsonify(res), 200
    else:
        if "message" in errors:
            return jsonify({"message": errors["message"]})
        return jsonify(errors), 400


@app.route('/transaction-reference', methods=['GET'])
@token_required
def transaction_reference():
    ref = str(uuid.uuid4())
    # Optionally store with a TTL (not implemented here)
    transaction_refs[ref] = True
    return jsonify({"reference": ref}), 200


@app.route('/user-config', methods=['GET'])
@token_required
def user_config():
    # Static deposit limits
    min_deposit = 500
    max_deposit = 5_000_000

    # Determine user's default currency (fallback to 'UGX')
    default_currency = getattr(g.user, 'default_currency', None) or 'UGX'

    # Fetch the user's account for their default currency
    from db import Account  # Ensure Account is imported
    account = (
        session.query(Account)
        .filter(Account.user_id == g.user.id)
        .filter(Account.currency == default_currency)
        .first()
    )

    balance = float(account.balance) if account else 0.0
    locked_amount = float(account.locked_amount) if account else 0.0
    currency = account.currency if account and account.currency else default_currency

    payload = {
        "id": g.user.id,
        "first_name": g.user.first_name,
        "last_name": g.user.last_name,
        "email": g.user.email,
        "role": g.user.role.value,
        "currency": currency,
        "balance": balance,
        "locked_amount": locked_amount,
        "min_deposit": min_deposit,
        "max_deposit": max_deposit,
    }
    return jsonify(payload), 200


@app.route('/refresh-token', methods=['GET'])
@token_required
def refresh_token():
    secret = config("JWT_SECRET")
    user = g.user
    payload = {"user_id": user.id, "exp": datetime.datetime.utcnow(
    ) + datetime.timedelta(hours=24*30)}
    encoded = jwt.encode(payload, secret, algorithm="HS256")
    return jsonify({"token": encoded}), 200

def bootstrap():
    logger.info("Starting auth consumer")
    print("Starting auth consumer (print)")
    for handler in logger.handlers:
	    handler.flush()
    sys.stdout.flush()
    threading.Thread(target=auth_consumer, daemon=True).start()
    logger.info("Starting auth consumer (after thread)")

bootstrap()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True)
