import os
import socket
from flask import Flask, Blueprint, request, jsonify, Response
from flasgger import Swagger
import requests
import logging
import datetime
import json
from grpc_client import qr_login, complete_profile, email_login, register as grpc_register
import uuid
from decouple import config
import requests

app = Flask(__name__)
swagger = Swagger(app)
api = Blueprint('api', __name__, url_prefix='/api/v1')
wallet = Blueprint('wallet', __name__, url_prefix='/api/v1/wallet')
mobile = Blueprint('mobile', __name__, url_prefix='/api/v1/mobile')

AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth:8000")
ADMIN_SERVICE_URL = os.getenv("ADMIN_SERVICE_URL", "http://admin:8000")
WALLET_SERVICE_URL = os.getenv("WALLET_SERVICE_URL", "http://wallet:8000")


class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        if record.exc_info:
            log_record["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info)
            }
        if hasattr(record, "extra"):
            log_record.update(record.extra)
        return json.dumps(log_record)

def setup_logging():
    logger = logging.getLogger("betting_service")
    logger.setLevel(logging.INFO)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(JSONFormatter())
    logger.handlers = []  # Remove any existing handlers
    logger.addHandler(console_handler)
    return logger

app.logger = setup_logging()

# ------- AUTHENTICATION PROXY ENDPOINTS -----------
@api.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok"}), 200


@api.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    response = grpc_register(
        email=data.get('email'),
        phone_number=data.get('phone_number'),
        first_name=data.get('first_name'),
        last_name=data.get('last_name'),
        password=data.get('password'),
        password_confirm=data.get('password_confirm'),
        sponsor_code=data.get('sponsor_code'),
        country=data.get('country')
    )
    if response.status == "success":
        return jsonify({"status": response.status, "user_id": response.user_id}), 201
    else:
        return jsonify({"status": response.status, "error": response.error}), 400


@api.route('/login', methods=['POST'])
def login():
    headers = {"Content-Type": "application/json", "Accept": "*/*"}
    data = request.get_json()
    res = requests.post(f"{AUTH_SERVICE_URL}/login",
                        json=data, headers=headers)
    app.logger.info(f"LOGIN: response data: {res.json()}")
    return jsonify(res.json()), res.status_code


@api.route('/forgot-password', methods=['POST'])
def forgot_password():
    headers = {"Content-Type": "application/json", "Accept": "*/*"}
    data = request.get_json()
    res = requests.post(f"{AUTH_SERVICE_URL}/forgot-password",
                        json=data, headers=headers)
    app.logger.info(f"LOGIN: response data: {res.json()}")
    return jsonify(res.json()), res.status_code


@api.route('/verify-email', methods=["POST"])
def verify_email():
    headers = {"Content-Type": "application/json", "Accept": "*/*"}
    data = request.get_json()
    res = requests.post(f"{AUTH_SERVICE_URL}/verify-email",
                        json=data, headers=headers)
    app.logger.info(f"LOGIN: response data: {res.json()}")
    return jsonify(res.json()), res.status_code


@api.route('/ping-forgot-pwd', methods=["POST"])
def ping_forgot_pwd():
    headers = {"Content-Type": "application/json", "Accept": "*/*"}
    data = request.get_json()
    res = requests.post(f"{AUTH_SERVICE_URL}/ping-forgot-pwd",
                        json=data, headers=headers)
    app.logger.info(f"LOGIN: response data: {res.json()}")
    return jsonify(res.json()), res.status_code


@api.route('/reset-pwd', methods=["POST"])
def reset_pwd():
    headers = {"Content-Type": "application/json", "Accept": "*/*"}
    data = request.get_json()
    res = requests.post(f"{AUTH_SERVICE_URL}/reset-pwd",
                        json=data, headers=headers)
    app.logger.info(f"LOGIN: response data: {res.json()}")
    return jsonify(res.json()), res.status_code


@api.route('/user-config', methods=["GET"])
def user_config():
    headers = {"Accept": "*/*",
               "Authorization": request.headers.get("Authorization")}
    res = requests.get(f"{AUTH_SERVICE_URL}/user-config",
                       headers=headers)
    app.logger.info(f"LOGIN: response data: {res.json()}")
    return jsonify(res.json()), res.status_code




class QRLoginRequest:
    account_ref: str

class CompleteProfileRequest:
    user_id: str
    first_name: str
    last_name: str
    email: str
    phone_number: str
    country: str

@mobile.route('/qr-login', methods=['POST'])
def mobile_qr_login():
    data = request.get_json()
    account_ref = data.get('account_ref')
    response = qr_login(account_ref)
    if response.status == "error":
        return jsonify({"error": "Account not found"}), 404
    return jsonify({
        "status": response.status,
        "user_id": response.user_id,
        "token": response.token
    })

@mobile.route('/complete-profile', methods=['POST'])
def mobile_complete_profile():
    data = request.get_json()
    response = complete_profile(
        data.get('user_id'),
        data.get('first_name'),
        data.get('last_name'),
        data.get('email'),
        data.get('phone_number'),
        data.get('country')
    )
    if response.status == "error":
        return jsonify({"error": "User not found"}), 404
    return jsonify({"status": response.status})

@mobile.route('/login', methods=['POST'])
def mobile_login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400
    token = email_login(email, password)
    if not token:
        return jsonify({'error': 'Invalid credentials'}), 401
    return jsonify({'token': token})

@mobile.route('/signup', methods=['POST'])
def mobile_signup():
    data = request.get_json()
    response = grpc_register(
        email=data.get('email'),
        phone_number=data.get('phone_number'),
        first_name=data.get('first_name'),
        last_name=data.get('last_name'),
        password=data.get('password'),
        password_confirm=data.get('password_confirm'),
        sponsor_code=data.get('sponsor_code'),
        country=data.get('country')
    )
    if response.status == "success":
        return jsonify({"status": response.status, "user_id": response.user_id, "uri": getattr(response, 'uri', None)}), 201
    else:
        return jsonify({"status": response.status, "error": response.error}), 400

# BlockCypher webhook proxy endpoint
@api.route('/wallet/btc/callbacks/address-webhook', methods=['POST'])
def blockcypher_webhook_proxy():
    """
    Proxy endpoint for BlockCypher webhooks.
    Forwards requests to the wallet service for processing.
    """
    try:
        # Forward the request to wallet service
        wallet_url = f"{WALLET_SERVICE_URL}/btc/callbacks/address-webhook"
        
        # Forward headers and body
        headers = dict(request.headers)
        # Remove host header to avoid conflicts
        headers.pop('Host', None)

        print(request.headers)
        
        response = requests.post(
            wallet_url,
            json=request.get_json(),
            headers=headers,
            timeout=30
        )
        
        # Return the response from wallet service
        return jsonify(response.json()), response.status_code
        
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Error forwarding webhook to wallet service: {e}")
        return jsonify({"error": "Wallet service unavailable"}), 503
    except Exception as e:
        app.logger.error(f"Error processing webhook proxy: {e}")
        return jsonify({"error": "Internal server error"}), 500

# BlockCypher forward webhook proxy endpoint
@api.route('/wallet/btc/callbacks/forward-webhook', methods=['POST'])
def blockcypher_forward_webhook_proxy():
    """
    Proxy endpoint for BlockCypher forward webhooks.
    Forwards requests to the wallet service for processing.
    """
    try:
        # Forward the request to wallet service
        wallet_url = f"{WALLET_SERVICE_URL}/btc/callbacks/forward-webhook"
        
        # Forward headers and body
        headers = dict(request.headers)
        # Remove host header to avoid conflicts
        headers.pop('Host', None)
        
        response = requests.post(
            wallet_url,
            json=request.get_json(),
            headers=headers,
            timeout=30
        )
        
        # Return the response from wallet service
        return jsonify(response.json()), response.status_code
        
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Error forwarding webhook to wallet service: {e}")
        return jsonify({"error": "Wallet service unavailable"}), 503
    except Exception as e:
        app.logger.error(f"Error processing webhook proxy: {e}")
        return jsonify({"error": "Internal server error"}), 500

app.register_blueprint(api)
app.register_blueprint(mobile)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=True)
