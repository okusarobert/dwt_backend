import os
import socket
from flask import Flask, Blueprint, request, jsonify, Response, make_response
from flask_cors import CORS
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

# Enable CORS for all routes
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:3001"],
        "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "Accept", "X-Requested-With"],
        "supports_credentials": True,
        "max_age": 86400,
    }
})

swagger = Swagger(app)
api = Blueprint('api', __name__, url_prefix='/api/v1')
wallet = Blueprint('wallet', __name__, url_prefix='/api/v1/wallet')
mobile = Blueprint('mobile', __name__, url_prefix='/api/v1/mobile')

AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth:8000")
ADMIN_SERVICE_URL = os.getenv("ADMIN_SERVICE_URL", "http://admin:3000")
WALLET_SERVICE_URL = os.getenv("WALLET_SERVICE_URL", "http://wallet:3000")
TRADING_SERVICE_URL = os.getenv("WALLET_SERVICE_URL", "http://wallet:3000")  # Trading routes are in wallet service


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

# ------- TRADING PROXY ENDPOINTS -----------
@api.route('/api/trading/prices', methods=['GET'])
def trading_prices():
    """Proxy trading prices endpoint"""
    try:
        headers = {"Content-Type": "application/json", "Accept": "*/*"}
        if 'Authorization' in request.headers:
            headers['Authorization'] = request.headers['Authorization']
        
        # Forward cookies for authentication
        cookies = request.cookies
        
        # Forward query parameters
        query_string = request.query_string.decode('utf-8')
        url = f"{TRADING_SERVICE_URL}/api/trading/prices"
        if query_string:
            url += f"?{query_string}"
        
        res = requests.get(url, headers=headers, cookies=cookies)
        return jsonify(res.json()), res.status_code
        
    except Exception as e:
        app.logger.error(f"Error in trading prices proxy: {e}")
        return jsonify({"error": "Failed to fetch prices"}), 500

@api.route('/api/trading/calculate', methods=['POST'])
def trading_calculate():
    """Proxy trading calculation endpoint"""
    # Handle CORS preflight request
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        headers = {"Content-Type": "application/json", "Accept": "*/*"}
        if 'Authorization' in request.headers:
            headers['Authorization'] = request.headers['Authorization']
        
        # Forward cookies for authentication
        cookies = request.cookies
        
        data = request.get_json()
        res = requests.post(f"{TRADING_SERVICE_URL}/api/trading/calculate", 
                           json=data, headers=headers, cookies=cookies)
        return jsonify(res.json()), res.status_code
        
    except Exception as e:
        app.logger.error(f"Error in trading calculate proxy: {e}")
        return jsonify({"error": "Failed to calculate trade"}), 500

@api.route('/trading/quote', methods=['POST', 'OPTIONS'])
def trading_quote():
    """Proxy trading quote endpoint"""
    # Handle CORS preflight request
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        headers = {"Content-Type": "application/json", "Accept": "*/*"}
        if 'Authorization' in request.headers:
            headers['Authorization'] = request.headers['Authorization']
        
        # Forward cookies for authentication
        cookies = request.cookies
        
        data = request.get_json()
        res = requests.post(f"{TRADING_SERVICE_URL}/api/trading/quote", 
                           json=data, headers=headers, cookies=cookies)
        return jsonify(res.json()), res.status_code
        
    except Exception as e:
        app.logger.error(f"Error in trading quote proxy: {e}")
        return jsonify({"error": "Failed to get quote"}), 500

@api.route('/trading/buy', methods=['POST', 'OPTIONS'])
def trading_buy():
    """Proxy trading buy endpoint"""
    # Handle CORS preflight request
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        headers = {"Content-Type": "application/json", "Accept": "*/*"}
        if 'Authorization' in request.headers:
            headers['Authorization'] = request.headers['Authorization']
        
        # Forward cookies for authentication
        cookies = request.cookies
        
        data = request.get_json()
        res = requests.post(f"{TRADING_SERVICE_URL}/api/trading/buy", 
                           json=data, headers=headers, cookies=cookies)
        return jsonify(res.json()), res.status_code
        
    except Exception as e:
        app.logger.error(f"Error in trading buy proxy: {e}")
        return jsonify({"error": "Failed to execute buy order"}), 500

@api.route('/trading/sell', methods=['POST', 'OPTIONS'])
def trading_sell():
    """Proxy trading sell endpoint"""
    # Handle CORS preflight request
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        headers = {"Content-Type": "application/json", "Accept": "*/*"}
        if 'Authorization' in request.headers:
            headers['Authorization'] = request.headers['Authorization']
        
        # Forward cookies for authentication
        cookies = request.cookies
        
        data = request.get_json()
        res = requests.post(f"{TRADING_SERVICE_URL}/api/trading/sell", 
                           json=data, headers=headers, cookies=cookies)
        return jsonify(res.json()), res.status_code
        
    except Exception as e:
        app.logger.error(f"Error in trading sell proxy: {e}")
        return jsonify({"error": "Failed to execute sell order"}), 500

@api.route('/trading/trades', methods=['GET'])
def trading_trades():
    """Proxy trading history endpoint"""
    try:
        headers = {"Content-Type": "application/json", "Accept": "*/*"}
        if 'Authorization' in request.headers:
            headers['Authorization'] = request.headers['Authorization']
        
        # Forward query parameters
        query_string = request.query_string.decode('utf-8')
        url = f"{TRADING_SERVICE_URL}/api/trading/trades"
        if query_string:
            url += f"?{query_string}"
        # Forward cookies for authentication
        cookies = request.cookies
        
        res = requests.get(url, headers=headers, cookies=cookies)
        return jsonify(res.json()), res.status_code
        
    except Exception as e:
        app.logger.error(f"Error in trading history proxy: {e}")
        return jsonify({"error": "Failed to fetch trade history"}), 500

@api.route('/trading/trades/<int:trade_id>', methods=['GET'])
def trading_trade_details(trade_id):
    """Proxy trading trade details endpoint"""
    try:
        headers = {"Content-Type": "application/json", "Accept": "*/*"}
        if 'Authorization' in request.headers:
            headers['Authorization'] = request.headers['Authorization']
        
        # Forward cookies for authentication
        cookies = request.cookies
        
        res = requests.get(f"{TRADING_SERVICE_URL}/api/trading/trades/{trade_id}", 
                          headers=headers, cookies=cookies)
        return jsonify(res.json()), res.status_code
        
    except Exception as e:
        app.logger.error(f"Error in trading details proxy: {e}")
        return jsonify({"error": "Failed to fetch trade details"}), 500

@api.route('/trading/trades/<int:trade_id>/cancel', methods=['POST'])
def trading_cancel_trade(trade_id):
    """Proxy trading cancel endpoint"""
    try:
        headers = {"Content-Type": "application/json", "Accept": "*/*"}
        if 'Authorization' in request.headers:
            headers['Authorization'] = request.headers['Authorization']
        
        # Forward cookies for authentication
        cookies = request.cookies
        
        res = requests.post(f"{TRADING_SERVICE_URL}/api/trading/trades/{trade_id}/cancel", 
                           headers=headers, cookies=cookies)
        return jsonify(res.json()), res.status_code
        
    except Exception as e:
        app.logger.error(f"Error in trading cancel proxy: {e}")
        return jsonify({"error": "Failed to cancel trade"}), 500

@api.route('/trading/vouchers/validate', methods=['POST'])
def trading_validate_voucher():
    """Proxy voucher validation endpoint"""
    try:
        headers = {"Content-Type": "application/json", "Accept": "*/*"}
        if 'Authorization' in request.headers:
            headers['Authorization'] = request.headers['Authorization']
        
        data = request.get_json()
        res = requests.post(f"{TRADING_SERVICE_URL}/api/trading/vouchers/validate", 
                           json=data, headers=headers)
        return jsonify(res.json()), res.status_code
        
    except Exception as e:
        app.logger.error(f"Error in voucher validation proxy: {e}")
        return jsonify({"error": "Failed to validate voucher"}), 500

@api.route('/trading/payment-methods', methods=['GET'])
def trading_payment_methods():
    """Proxy payment methods endpoint"""
    try:
        headers = {"Content-Type": "application/json", "Accept": "*/*"}
        if 'Authorization' in request.headers:
            headers['Authorization'] = request.headers['Authorization']
        
        res = requests.get(f"{TRADING_SERVICE_URL}/api/trading/payment-methods", 
                          headers=headers)
        return jsonify(res.json()), res.status_code
        
    except Exception as e:
        app.logger.error(f"Error in payment methods proxy: {e}")
        return jsonify({"error": "Failed to fetch payment methods"}), 500

# Missing exchange rate endpoint
@api.route('/api/trading/exchange-rate/<from_currency>/<to_currency>', methods=['GET'])
def trading_exchange_rate(from_currency, to_currency):
    """Proxy exchange rate endpoint"""
    try:
        headers = {"Content-Type": "application/json", "Accept": "*/*"}
        if 'Authorization' in request.headers:
            headers['Authorization'] = request.headers['Authorization']
        
        # Forward cookies for authentication
        cookies = request.cookies
        
        res = requests.get(f"{TRADING_SERVICE_URL}/api/trading/exchange-rate/{from_currency}/{to_currency}", 
                          headers=headers, cookies=cookies)
        return jsonify(res.json()), res.status_code
        
    except Exception as e:
        app.logger.error(f"Error in exchange rate proxy: {e}")
        return jsonify({"error": "Failed to fetch exchange rate"}), 500

# Missing trade history endpoint
@api.route('/api/trading/history', methods=['GET'])
def trading_history():
    """Proxy trading history endpoint"""
    try:
        headers = {"Content-Type": "application/json", "Accept": "*/*"}
        if 'Authorization' in request.headers:
            headers['Authorization'] = request.headers['Authorization']
        
        # Forward cookies for authentication
        cookies = request.cookies
        
        # Forward query parameters
        query_string = request.query_string.decode('utf-8')
        url = f"{TRADING_SERVICE_URL}/api/trading/history"
        if query_string:
            url += f"?{query_string}"
        
        res = requests.get(url, headers=headers, cookies=cookies)
        return jsonify(res.json()), res.status_code
        
    except Exception as e:
        app.logger.error(f"Error in trading history proxy: {e}")
        return jsonify({"error": "Failed to fetch trading history"}), 500

# ------- TRADING WEBHOOK PROXY ENDPOINTS -----------
@api.route('/webhooks/buy-complete', methods=['POST'])
def buy_complete_webhook_proxy():
    """Proxy buy completion webhook"""
    try:
        headers = {"Content-Type": "application/json", "Accept": "*/*"}
        # Forward webhook signature headers
        for header in ['X-Buy-Webhook-Signature', 'X-Trade-Webhook-Signature']:
            if header in request.headers:
                headers[header] = request.headers[header]
        
        data = request.get_json()
        res = requests.post(f"{TRADING_SERVICE_URL}/api/webhooks/buy-complete", 
                           json=data, headers=headers)
        return jsonify(res.json()), res.status_code
        
    except Exception as e:
        app.logger.error(f"Error in buy completion webhook proxy: {e}")
        return jsonify({"error": "Failed to process buy completion webhook"}), 500

@api.route('/webhooks/sell-complete', methods=['POST'])
def sell_complete_webhook_proxy():
    """Proxy sell completion webhook"""
    try:
        headers = {"Content-Type": "application/json", "Accept": "*/*"}
        # Forward webhook signature headers
        for header in ['X-Sell-Webhook-Signature', 'X-Trade-Webhook-Signature']:
            if header in request.headers:
                headers[header] = request.headers[header]
        
        data = request.get_json()
        res = requests.post(f"{TRADING_SERVICE_URL}/api/webhooks/sell-complete", 
                           json=data, headers=headers)
        return jsonify(res.json()), res.status_code
        
    except Exception as e:
        app.logger.error(f"Error in sell completion webhook proxy: {e}")
        return jsonify({"error": "Failed to process sell completion webhook"}), 500

@api.route('/webhooks/trade-status', methods=['POST'])
def trade_status_webhook_proxy():
    """Proxy trade status webhook"""
    try:
        headers = {"Content-Type": "application/json", "Accept": "*/*"}
        # Forward webhook signature headers
        for header in ['X-Trade-Webhook-Signature', 'X-Buy-Webhook-Signature', 'X-Sell-Webhook-Signature']:
            if header in request.headers:
                headers[header] = request.headers[header]
        
        data = request.get_json()
        res = requests.post(f"{TRADING_SERVICE_URL}/api/webhooks/trade-status", 
                           json=data, headers=headers)
        return jsonify(res.json()), res.status_code
        
    except Exception as e:
        app.logger.error(f"Error in trade status webhook proxy: {e}")
        return jsonify({"error": "Failed to process trade status webhook"}), 500

@api.route('/webhooks/relworx', methods=['POST'])
def relworx_webhook_proxy():
    """Proxy Relworx webhook"""
    try:
        headers = {"Content-Type": "application/json", "Accept": "*/*"}
        
        res = requests.post(f"{WALLET_SERVICE_URL}/webhooks/relworx", 
                          json=request.get_json(), headers=headers)
        
        return jsonify(res.json()), res.status_code
        
    except Exception as e:
        app.logger.error(f"Error in Relworx webhook proxy: {e}")
        return jsonify({"error": "Failed to process Relworx webhook"}), 500

@api.route('/wallet/eth/callbacks/address-webhook', methods=['POST'])
def ethereum_webhook_proxy():
    """Proxy Ethereum address webhook"""
    try:
        headers = {"Content-Type": "application/json", "Accept": "*/*"}
        
        res = requests.post(f"{WALLET_SERVICE_URL}/wallet/eth/callbacks/address-webhook", 
                          json=request.get_json(), headers=headers)
        
        return jsonify(res.json()), res.status_code
        
    except Exception as e:
        app.logger.error(f"Error in Ethereum webhook proxy: {e}")
        return jsonify({"error": "Failed to process Ethereum webhook"}), 500

@api.route('/wallet/eth/callbacks/health', methods=['GET'])
def ethereum_webhook_health_proxy():
    """Proxy Ethereum webhook health check"""
    try:
        res = requests.get(f"{WALLET_SERVICE_URL}/api/v1/wallet/eth/callbacks/health")
        
        return jsonify(res.json()), res.status_code
        
    except Exception as e:
        app.logger.error(f"Error in Ethereum webhook health proxy: {e}")
        return jsonify({"error": "Failed to check Ethereum webhook health"}), 500

@api.route('/wallet/bnb/callbacks/address-webhook', methods=['POST'])
def bnb_webhook_proxy():
    """Proxy BNB address webhook"""
    try:
        headers = {"Content-Type": "application/json", "Accept": "*/*"}
        
        res = requests.post(f"{WALLET_SERVICE_URL}/wallet/bnb/callbacks/address-webhook", 
                          json=request.get_json(), headers=headers)
        
        return jsonify(res.json()), res.status_code
        
    except Exception as e:
        app.logger.error(f"Error in BNB webhook proxy: {e}")
        return jsonify({"error": "Failed to process BNB webhook"}), 500

@api.route('/wallet/bnb/callbacks/health', methods=['GET'])
def bnb_webhook_health_proxy():
    """Proxy BNB webhook health check"""
    try:
        res = requests.get(f"{WALLET_SERVICE_URL}/api/v1/wallet/bnb/callbacks/health")
        
        return jsonify(res.json()), res.status_code
        
    except Exception as e:
        app.logger.error(f"Error in BNB webhook health proxy: {e}")
        return jsonify({"error": "Failed to check BNB webhook health"}), 500


@api.route('/register', methods=['POST'])
def register():
    """Register endpoint that forwards to auth service"""
    try:
        headers = {"Content-Type": "application/json", "Accept": "*/*"}
        data = request.get_json()
        app.logger.info(f"REGISTER: data: {data}")
        
        res = requests.post(f"{AUTH_SERVICE_URL}/register",
                           json=data, headers=headers)
        
        app.logger.info(f"REGISTER: response data: {res.json()}")
        
        # Create response with the auth service data
        response = jsonify(res.json())
        
        # Forward cookies from auth service response if any
        if 'Set-Cookie' in res.headers:
            app.logger.info(f"Forwarding register cookies: {res.headers['Set-Cookie']}")
            response.headers['Set-Cookie'] = res.headers['Set-Cookie']
        
        return response, res.status_code
        
    except Exception as e:
        app.logger.error(f"Error in register proxy: {e}")
        return jsonify({"error": "Registration failed"}), 500


@api.route('/login', methods=['POST'])
def login():
    headers = {"Content-Type": "application/json", "Accept": "*/*"}
    data = request.get_json()
    app.logger.info(f"LOGIN: data: {data}")
    res = requests.post(f"{AUTH_SERVICE_URL}/login",
                        json=data, headers=headers)
    app.logger.info(f"LOGIN: response data: {res.json()}")
    
    # Create response with the auth service data
    response = jsonify(res.json())
    
    # Forward cookies from auth service response
    if 'Set-Cookie' in res.headers:
        app.logger.info(f"Forwarding cookies: {res.headers['Set-Cookie']}")
        response.headers['Set-Cookie'] = res.headers['Set-Cookie']
    
    return response, res.status_code


@api.route('/logout', methods=['POST'])
def logout():
    """Logout endpoint that forwards to auth service and clears cookies"""
    try:
        headers = {"Content-Type": "application/json", "Accept": "*/*"}
        
        # Forward cookies from the client request to the auth service
        cookies = request.cookies
        
        res = requests.post(f"{AUTH_SERVICE_URL}/logout",
                           headers=headers, cookies=cookies)
        
        app.logger.info(f"LOGOUT: response data: {res.json()}")
        
        # Create response with the auth service data
        response = jsonify(res.json())
        
        # Forward cookies from auth service response (this will clear the cookie)
        if 'Set-Cookie' in res.headers:
            app.logger.info(f"Forwarding logout cookies: {res.headers['Set-Cookie']}")
            response.headers['Set-Cookie'] = res.headers['Set-Cookie']
        
        return response, res.status_code
        
    except Exception as e:
        app.logger.error(f"Error in logout proxy: {e}")
        return jsonify({"error": "Logout failed"}), 500


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
    # Forward cookies from the client request
    cookies = request.cookies
    data = request.get_json()
    res = requests.post(f"{AUTH_SERVICE_URL}/verify-email",
                        json=data, headers=headers, cookies=cookies)
    app.logger.info(f"VERIFY-EMAIL: response data: {res.json()}")
    
    # Forward response cookies back to client
    response = make_response(jsonify(res.json()), res.status_code)
    for cookie in res.cookies:
        if cookie.value == '' and cookie.expires and cookie.expires < 0:
            # This is a cookie deletion - forward it properly
            response.delete_cookie(cookie.name, path=cookie.path, domain=cookie.domain)
        else:
            response.set_cookie(cookie.name, cookie.value, 
                              max_age=cookie.expires, path=cookie.path,
                              domain=cookie.domain, secure=cookie.secure,
                              httponly=cookie.get('HttpOnly', False))
    return response


@api.route('/resend-verification', methods=["POST"])
def resend_verification():
    headers = {"Content-Type": "application/json", "Accept": "*/*"}
    # Forward cookies from the client request
    cookies = request.cookies
    data = request.get_json()
    res = requests.post(f"{AUTH_SERVICE_URL}/resend-verification",
                        json=data, headers=headers, cookies=cookies)
    app.logger.info(f"RESEND-VERIFICATION: response data: {res.json()}")
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
    # Forward cookies from the client request to the auth service
    cookies = request.cookies
    headers = {"Accept": "*/*"}
    
    # Also include Authorization header as fallback
    if request.headers.get("Authorization"):
        headers["Authorization"] = request.headers.get("Authorization")
    
    res = requests.get(f"{AUTH_SERVICE_URL}/user-config",
                       headers=headers, cookies=cookies)
    app.logger.info(f"USER-CONFIG: response data: {res.json()}")
    return jsonify(res.json()), res.status_code


# --- WALLET PROXY ROUTES ---
WALLET_BASE_URL = WALLET_SERVICE_URL


@api.route('/wallet/account', methods=['POST'])
def proxy_wallet_create_account():
    headers = {"Authorization": request.headers.get("Authorization")}
    cookies = request.cookies
    resp = requests.post(f"{WALLET_SERVICE_URL}/wallet/account", headers=headers, cookies=cookies)
    return jsonify(resp.json()), resp.status_code


@api.route('/wallet/balance', methods=['GET'])
def proxy_wallet_get_balance():
    headers = {"Authorization": request.headers.get("Authorization")}
    cookies = request.cookies
    resp = requests.get(f"{WALLET_SERVICE_URL}/wallet/balance", headers=headers, cookies=cookies)
    return jsonify(resp.json()), resp.status_code


@api.route('/wallet/deposit', methods=['POST'])
def proxy_wallet_deposit():
    headers = {"Authorization": request.headers.get("Authorization")}
    cookies = request.cookies
    resp = requests.post(f"{WALLET_SERVICE_URL}/wallet/deposit",
                         json=request.get_json(), headers=headers, cookies=cookies)
    return jsonify(resp.json()), resp.status_code


@api.route('/wallet/withdraw', methods=['POST'])
def proxy_wallet_withdraw():
    headers = {"Authorization": request.headers.get("Authorization")}
    cookies = request.cookies
    resp = requests.post(f"{WALLET_SERVICE_URL}/wallet/withdraw",
                         json=request.get_json(), headers=headers, cookies=cookies)
    return jsonify(resp.json()), resp.status_code


@api.route('/wallet/transfer', methods=['POST'])
def proxy_wallet_transfer():
    headers = {"Authorization": request.headers.get("Authorization")}
    cookies = request.cookies
    resp = requests.post(f"{WALLET_SERVICE_URL}/wallet/transfer",
                         json=request.get_json(), headers=headers, cookies=cookies)
    return jsonify(resp.json()), resp.status_code


@api.route('/wallet/transactions', methods=['GET'])
def proxy_wallet_transactions():
    headers = {"Authorization": request.headers.get("Authorization")}
    cookies = request.cookies
    resp = requests.get(f"{WALLET_SERVICE_URL}/wallet/transactions",
                        headers=headers, cookies=cookies, params=request.args)
    return jsonify(resp.json()), resp.status_code

@api.route('/wallet/transactions/<int:transaction_id>', methods=['GET'])
def proxy_wallet_transaction_details(transaction_id):
    headers = {"Authorization": request.headers.get("Authorization")}
    cookies = request.cookies
    resp = requests.get(f"{WALLET_SERVICE_URL}/wallet/transactions/{transaction_id}",
                        headers=headers, cookies=cookies)
    return jsonify(resp.json()), resp.status_code

@api.route('/wallet/dashboard/summary', methods=['GET'])
def proxy_dashboard_summary():
    """Proxy dashboard summary endpoint to wallet service"""
    try:
        headers = {"Content-Type": "application/json", "Accept": "*/*"}
        if 'Authorization' in request.headers:
            headers['Authorization'] = request.headers['Authorization']
        
        cookies = request.cookies
        app.logger.info(f"Forwarding dashboard summary cookies: {cookies}")

        res = requests.get(
            f"{WALLET_SERVICE_URL}/api/v1/wallet/dashboard/summary", 
            headers=headers, 
            cookies=cookies
        )
        
        return jsonify(res.json()), res.status_code
        
    except Exception as e:
        app.logger.error(f"Error in dashboard summary proxy: {e}")
        return jsonify({"error": "Failed to fetch dashboard summary"}), 500

@api.route('/wallet/pnl', methods=['GET'])
def proxy_wallet_pnl():
    """Proxy PnL endpoint to wallet service"""
    headers = {"Authorization": request.headers.get("Authorization")}
    cookies = request.cookies
    resp = requests.get(f"{WALLET_SERVICE_URL}/wallet/pnl",
                        headers=headers, cookies=cookies, params=request.args)
    return jsonify(resp.json()), resp.status_code

@api.route('/verification-info', methods=['GET'])
def verification_info():
    """Proxy verification info endpoint to auth service"""
    try:
        headers = {"Authorization": request.headers.get("Authorization")}
        cookies = request.cookies
        app.logger.info(f"AUTH SERVICE URL: {AUTH_SERVICE_URL}")
        resp = requests.get(f"{AUTH_SERVICE_URL}/api/verification-info", 
                           headers=headers, cookies=cookies, timeout=10)
        return jsonify(resp.json()), resp.status_code
    except requests.exceptions.RequestException as e:
        # Fallback if auth service unavailable
        return jsonify({
            "success": False,
            "verification_status": None,
            "verification_level": None,
            "kyc_status": None, 
            "documents_uploaded": False,
            "phone_verified": False,
            "email_verified": False
        }), 401

@api.route('/wallet/portfolio-summary', methods=['GET'])
def proxy_wallet_portfolio_summary():
    """Proxy portfolio summary endpoint to wallet service"""
    headers = {"Authorization": request.headers.get("Authorization")}
    cookies = request.cookies
    resp = requests.get(f"{WALLET_SERVICE_URL}/wallet/portfolio-summary",
                        headers=headers, cookies=cookies)
    return jsonify(resp.json()), resp.status_code

# --- RESERVE MANAGEMENT PROXY ROUTES (ADMIN) ---
@api.route('/wallet/reserves/status', methods=['GET'])
def proxy_reserve_status():
     # Forward cookies from the client request to the auth service
    cookies = request.cookies
    headers = {"Accept": "*/*"}
    
    # Also include Authorization header as fallback
    if request.headers.get("Authorization"):
        headers["Authorization"] = request.headers.get("Authorization")
    resp = requests.get(f"{WALLET_SERVICE_URL}/wallet/reserves/status",
                        headers=headers, cookies=cookies)
    return jsonify(resp.json()), resp.status_code


@api.route('/wallet/reserves/<currency>/<account_type>/balance', methods=['GET'])
def proxy_reserve_balance(currency, account_type):
    # Forward cookies and include Authorization as fallback
    cookies = request.cookies
    headers = {"Accept": "*/*"}
    if request.headers.get("Authorization"):
        headers["Authorization"] = request.headers.get("Authorization")
    resp = requests.get(
        f"{WALLET_SERVICE_URL}/wallet/reserves/{currency}/{account_type}/balance",
        headers=headers,
        cookies=cookies,
    )
    return jsonify(resp.json()), resp.status_code


@api.route('/wallet/reserves/<currency>/<account_type>/topup', methods=['POST'])
def proxy_reserve_topup(currency, account_type):
    cookies = request.cookies
    headers = {"Accept": "*/*"}
    if request.headers.get("Authorization"):
        headers["Authorization"] = request.headers.get("Authorization")
    resp = requests.post(
        f"{WALLET_SERVICE_URL}/wallet/reserves/{currency}/{account_type}/topup",
        json=request.get_json(),
        headers=headers,
        cookies=cookies,
    )
    return jsonify(resp.json()), resp.status_code


@api.route('/wallet/reserves/<currency>/<account_type>/withdraw', methods=['POST'])
def proxy_reserve_withdraw(currency, account_type):
    cookies = request.cookies
    headers = {"Accept": "*/*"}
    if request.headers.get("Authorization"):
        headers["Authorization"] = request.headers.get("Authorization")
    resp = requests.post(
        f"{WALLET_SERVICE_URL}/wallet/reserves/{currency}/{account_type}/withdraw",
        json=request.get_json(),
        headers=headers,
        cookies=cookies,
    )
    return jsonify(resp.json()), resp.status_code


@api.route('/wallet/reserves/analytics', methods=['GET'])
def proxy_reserve_analytics():
    cookies = request.cookies
    headers = {"Accept": "*/*"}
    if request.headers.get("Authorization"):
        headers["Authorization"] = request.headers.get("Authorization")
    resp = requests.get(
        f"{WALLET_SERVICE_URL}/wallet/reserves/analytics",
        headers=headers,
        params=request.args,
        cookies=cookies,
    )
    return jsonify(resp.json()), resp.status_code


@api.route('/wallet/reserves/cache/clear', methods=['POST'])
def proxy_reserve_cache_clear():
    cookies = request.cookies
    headers = {"Accept": "*/*"}
    if request.headers.get("Authorization"):
        headers["Authorization"] = request.headers.get("Authorization")
    resp = requests.post(
        f"{WALLET_SERVICE_URL}/wallet/reserves/cache/clear",
        headers=headers,
        cookies=cookies,
    )
    return jsonify(resp.json()), resp.status_code


# --- END WALLET PROXY ROUTES ---


# --- CRYPTO PRICE PROXY ROUTES ---
@api.route('/wallet/prices', methods=['GET'])
def proxy_crypto_prices():
    """Proxy endpoint for getting cached crypto prices."""
    headers = {"Authorization": request.headers.get("Authorization")}
    cookies = request.cookies
    resp = requests.get(f"{WALLET_SERVICE_URL}/wallet/prices",
                        headers=headers, cookies=cookies, params=request.args)
    return jsonify(resp.json()), resp.status_code


@api.route('/wallet/prices/<symbol>', methods=['GET'])
def proxy_crypto_price(symbol):
    """Proxy endpoint for getting cached price for a specific symbol."""
    headers = {"Authorization": request.headers.get("Authorization")}
    cookies = request.cookies
    resp = requests.get(
        f"{WALLET_SERVICE_URL}/wallet/prices/{symbol}",
        headers=headers,
        cookies=cookies,
        params=request.args,
    )
    return jsonify(resp.json()), resp.status_code

@api.route('/wallet/prices/refresh', methods=['POST'])
def proxy_refresh_crypto_prices():
    """Proxy endpoint for refreshing crypto prices."""
    headers = {"Authorization": request.headers.get("Authorization")}
    cookies = request.cookies
    resp = requests.post(f"{WALLET_SERVICE_URL}/wallet/prices/refresh",
                         headers=headers, cookies=cookies, params=request.args)
    return jsonify(resp.json()), resp.status_code

@api.route('/wallet/prices/refresh-expired', methods=['POST'])
def proxy_refresh_expired_crypto_prices():
    """Proxy endpoint for refreshing only expired crypto prices."""
    headers = {"Authorization": request.headers.get("Authorization")}
    cookies = request.cookies
    resp = requests.post(f"{WALLET_SERVICE_URL}/wallet/prices/refresh-expired",
                         headers=headers, cookies=cookies)
    return jsonify(resp.json()), resp.status_code


@api.route('/wallet/prices/status', methods=['GET'])
def proxy_price_cache_status():
    """Proxy endpoint for getting price cache status."""
    headers = {"Authorization": request.headers.get("Authorization")}
    cookies = request.cookies
    resp = requests.get(f"{WALLET_SERVICE_URL}/wallet/prices/status",
                        headers=headers, cookies=cookies)
    return jsonify(resp.json()), resp.status_code


@api.route('/wallet/prices/symbols', methods=['POST'])
def proxy_manage_price_symbols():
    """Proxy endpoint for managing price symbols."""
    headers = {"Authorization": request.headers.get("Authorization")}
    cookies = request.cookies
    resp = requests.post(f"{WALLET_SERVICE_URL}/wallet/prices/symbols",
                         json=request.get_json(), headers=headers, cookies=cookies)
    return jsonify(resp.json()), resp.status_code

@api.route('/wallet/prices/background-service', methods=['POST'])
def proxy_background_price_service():
    """Proxy endpoint for controlling the background price refresh service."""
    headers = {"Authorization": request.headers.get("Authorization")}
    cookies = request.cookies
    resp = requests.post(f"{WALLET_SERVICE_URL}/wallet/prices/background-service",
                         json=request.get_json(), headers=headers, cookies=cookies)
    return jsonify(resp.json()), resp.status_code

# Missing crypto balances endpoint
@api.route('/wallet/crypto/balances', methods=['GET'])
def proxy_crypto_balances():
    """Proxy crypto balances endpoint"""
    try:
        headers = {"Content-Type": "application/json", "Accept": "*/*"}
        if 'Authorization' in request.headers:
            headers['Authorization'] = request.headers['Authorization']
        
        # Forward cookies for authentication
        cookies = request.cookies
        
        # Forward query parameters
        query_string = request.query_string.decode('utf-8')
        url = f"{WALLET_SERVICE_URL}/api/wallet/crypto/balances"
        if query_string:
            url += f"?{query_string}"
        
        res = requests.get(url, headers=headers, cookies=cookies)
        return jsonify(res.json()), res.status_code
        
    except Exception as e:
        app.logger.error(f"Error in crypto balances proxy: {e}")
        return jsonify({"error": "Failed to fetch crypto balances"}), 500

# Missing detailed crypto balances endpoint
@api.route('/wallet/crypto/balances/detailed', methods=['GET'])
def proxy_detailed_crypto_balances():
    """Proxy detailed crypto balances endpoint with multi-chain aggregation"""
    try:
        headers = {"Content-Type": "application/json", "Accept": "*/*"}
        if 'Authorization' in request.headers:
            headers['Authorization'] = request.headers['Authorization']
        
        # Forward cookies for authentication
        cookies = request.cookies
        
        # Forward query parameters
        query_string = request.query_string.decode('utf-8')
        url = f"{WALLET_SERVICE_URL}/api/wallet/crypto/balances/detailed"
        if query_string:
            url += f"?{query_string}"
        
        res = requests.get(url, headers=headers, cookies=cookies)
        return jsonify(res.json()), res.status_code
        
    except Exception as e:
        app.logger.error(f"Error in detailed crypto balances proxy: {e}")
        return jsonify({"error": "Failed to fetch detailed crypto balances"}), 500

# --- END CRYPTO PRICE PROXY ROUTES ---


# --- ADMIN PROXY ROUTES ---
@api.route('/admin/users', methods=['GET'])
def admin_list_users_proxy():
    """Proxy admin list users to admin service"""
    try:
        headers = {"Accept": "*/*"}
        if 'Authorization' in request.headers:
            headers['Authorization'] = request.headers['Authorization']
        resp = requests.get(
            f"{ADMIN_SERVICE_URL}/admin/users",
            headers=headers,
            params=request.args,
        )
        return jsonify(resp.json()), resp.status_code
    except Exception as e:
        app.logger.error(f"Error proxying admin list users: {e}")
        return jsonify({"error": "Internal server error"}), 500


@api.route('/admin/users/<int:user_id>', methods=['GET'])
def admin_get_user_proxy(user_id):
    """Proxy admin get user to admin service"""
    try:
        headers = {"Accept": "*/*"}
        if 'Authorization' in request.headers:
            headers['Authorization'] = request.headers['Authorization']
        resp = requests.get(
            f"{ADMIN_SERVICE_URL}/admin/users/{user_id}",
            headers=headers,
            params=request.args,
        )
        return jsonify(resp.json()), resp.status_code
    except Exception as e:
        app.logger.error(f"Error proxying admin get user: {e}")
        return jsonify({"error": "Internal server error"}), 500


@api.route('/admin/users/<int:user_id>', methods=['PATCH'])
def proxy_admin_update_user(user_id):
    """Proxy admin update user to admin service"""
    headers = {
        'Content-Type': 'application/json',
    }
    if 'Authorization' in request.headers:
        headers['Authorization'] = request.headers['Authorization']
    resp = requests.patch(
        f"{ADMIN_SERVICE_URL}/admin/users/{user_id}",
        json=request.get_json(silent=True) or {},
        headers=headers,
    )
    return jsonify(resp.json()), resp.status_code


# --- ADMIN CURRENCY ROUTES ---
@api.route('/admin/currencies', methods=['GET'])
def proxy_admin_get_currencies():
    headers = {'Content-Type': 'application/json'}
    cookies = request.cookies
    if 'Authorization' in request.headers:
        headers['Authorization'] = request.headers['Authorization']
    
    resp = requests.get(
        f"{ADMIN_SERVICE_URL}/admin/currencies",
        headers=headers,
        cookies=cookies,
        params=request.args
    )
    return jsonify(resp.json()), resp.status_code


@api.route('/admin/currencies', methods=['POST'])
def proxy_admin_create_currency():
    headers = {'Content-Type': 'application/json'}
    cookies = request.cookies
    if 'Authorization' in request.headers:
        headers['Authorization'] = request.headers['Authorization']
    
    resp = requests.post(
        f"{ADMIN_SERVICE_URL}/admin/currencies",
        json=request.get_json(silent=True) or {},
        headers=headers,
        cookies=cookies
    )
    return jsonify(resp.json()), resp.status_code


@api.route('/admin/currencies/<currency_id>', methods=['GET'])
def proxy_admin_get_currency(currency_id):
    headers = {'Content-Type': 'application/json'}
    cookies = request.cookies
    if 'Authorization' in request.headers:
        headers['Authorization'] = request.headers['Authorization']
    
    resp = requests.get(
        f"{ADMIN_SERVICE_URL}/admin/currencies/{currency_id}",
        headers=headers,
        cookies=cookies
    )
    return jsonify(resp.json()), resp.status_code


@api.route('/admin/currencies/<currency_id>', methods=['PUT'])
def proxy_admin_update_currency(currency_id):
    headers = {'Content-Type': 'application/json'}
    cookies = request.cookies
    if 'Authorization' in request.headers:
        headers['Authorization'] = request.headers['Authorization']
    
    resp = requests.put(
        f"{ADMIN_SERVICE_URL}/admin/currencies/{currency_id}",
        json=request.get_json(silent=True) or {},
        headers=headers,
        cookies=cookies
    )
    return jsonify(resp.json()), resp.status_code


@api.route('/admin/currencies/<currency_id>/status', methods=['PATCH'])
def proxy_admin_update_currency_status(currency_id):
    headers = {'Content-Type': 'application/json'}
    cookies = request.cookies
    if 'Authorization' in request.headers:
        headers['Authorization'] = request.headers['Authorization']
    
    resp = requests.patch(
        f"{ADMIN_SERVICE_URL}/admin/currencies/{currency_id}/status",
        json=request.get_json(silent=True) or {},
        headers=headers,
        cookies=cookies
    )
    return jsonify(resp.json()), resp.status_code


@api.route('/admin/currencies/<currency_id>', methods=['DELETE'])
def proxy_admin_delete_currency(currency_id):
    headers = {'Content-Type': 'application/json'}
    cookies = request.cookies
    if 'Authorization' in request.headers:
        headers['Authorization'] = request.headers['Authorization']
    
    resp = requests.delete(
        f"{ADMIN_SERVICE_URL}/admin/currencies/{currency_id}",
        headers=headers,
        cookies=cookies
    )
    return jsonify(resp.json()), resp.status_code


# Portfolio and Ledger Endpoints
@api.route('/wallet/portfolio/summary', methods=['GET'])
def proxy_portfolio_summary():
    """Proxy to wallet service portfolio summary endpoint"""
    headers = {"Content-Type": "application/json", "Accept": "*/*"}
    if 'Authorization' in request.headers:
        headers['Authorization'] = request.headers['Authorization']    
    cookies = request.cookies

    try:
        response = requests.get(f"{WALLET_SERVICE_URL}/wallet/portfolio/summary", headers=headers, cookies=cookies)
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({"error": f"Failed to fetch portfolio summary: {str(e)}"}), 500


@api.route('/wallet/portfolio/analysis/<period>', methods=['GET'])
def proxy_portfolio_analysis(period):
    """Proxy to wallet service portfolio analysis endpoint"""
    try:
        response = requests.get(f"{WALLET_SERVICE_URL}/wallet/portfolio/analysis/{period}")
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({"error": f"Failed to fetch portfolio analysis: {str(e)}"}), 500


@api.route('/wallet/portfolio/ledger', methods=['GET'])
def proxy_portfolio_ledger():
    """Proxy to wallet service portfolio ledger endpoint"""
    try:
        # Forward query parameters
        params = request.args.to_dict()
        response = requests.get(f"{WALLET_SERVICE_URL}/wallet/portfolio/ledger", params=params)
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({"error": f"Failed to fetch portfolio ledger: {str(e)}"}), 500


@api.route('/wallet/portfolio/snapshot/<snapshot_type>', methods=['GET'])
def proxy_portfolio_snapshot(snapshot_type):
    """Proxy to wallet service portfolio snapshot endpoint"""
    try:
        response = requests.get(f"{WALLET_SERVICE_URL}/wallet/portfolio/snapshot/{snapshot_type}")
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({"error": f"Failed to fetch portfolio snapshot: {str(e)}"}), 500


# --- END PORTFOLIO PROXY ROUTES ---


# --- WALLET WEBHOOK PROXY ROUTES ---
@api.route('/webhook/relworx/request-payment', methods=['POST'])
def proxy_relworx_request_payment_webhook():
    """
    Proxy endpoint that forwards Relworx request-payment webhooks to the wallet service.
    """
    wallet_url = f"{WALLET_SERVICE_URL}/webhook/relworx/request-payment"
    headers = {key: value for key,
               value in request.headers if key.lower() != "host"}
    try:
        resp = requests.post(wallet_url, data=request.data, headers=headers)
        excluded_headers = ["content-encoding",
                            "content-length", "transfer-encoding", "connection"]
        response_headers = [(name, value) for (
            name, value) in resp.raw.headers.items() if name.lower() not in excluded_headers]
        return Response(resp.content, resp.status_code, response_headers)
    except Exception as e:
        app.logger.error(
            f"Error proxying Relworx request-payment webhook: {e!r}")
        return jsonify({"error": "Wallet service unavailable"}), 502


@api.route('/webhook/relworx/send-payment', methods=['POST'])
def proxy_relworx_send_payment_webhook():
    """
    Proxy endpoint that forwards Relworx send-payment webhooks to the wallet service.
    """
    wallet_url = f"{WALLET_SERVICE_URL}/webhook/relworx/send-payment"
    headers = {key: value for key,
               value in request.headers if key.lower() != "host"}
    try:
        resp = requests.post(wallet_url, data=request.data, headers=headers)
        excluded_headers = ["content-encoding",
                            "content-length", "transfer-encoding", "connection"]
        response_headers = [(name, value) for (
            name, value) in resp.raw.headers.items() if name.lower() not in excluded_headers]
        return Response(resp.content, resp.status_code, response_headers)
    except Exception as e:
        app.logger.error(f"Error proxying Relworx send-payment webhook: {e!r}")
        return jsonify({"error": "Wallet service unavailable"}), 502
# --- END WALLET WEBHOOK PROXY ROUTES ---




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

# Solana webhook proxy endpoint
@api.route('/wallet/sol/callbacks/address-webhook', methods=['POST'])
def solana_webhook_proxy():
    """
    Proxy endpoint for Solana webhooks from Alchemy.
    Forwards requests to the wallet service for processing.
    """
    try:
        # Forward the request to wallet service
        wallet_url = f"{WALLET_SERVICE_URL}/sol/callbacks/address-webhook"

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
        app.logger.error(f"Error forwarding Solana webhook to wallet service: {e}")
        return jsonify({"error": "Wallet service unavailable"}), 503
    except Exception as e:
        app.logger.error(f"Error processing Solana webhook proxy: {e}")
        return jsonify({"error": "Internal server error"}), 500

# Ethereum withdrawal proxy endpoints
@api.route('/wallet/withdraw/ethereum', methods=['POST'])
def ethereum_withdraw_proxy():
    """
    Proxy endpoint for Ethereum withdrawals.
    Forwards requests to the wallet service for processing.
    """
    try:
        # Forward the request to wallet service
        wallet_url = f"{WALLET_SERVICE_URL}/wallet/withdraw/ethereum"

        app.logger.info(wallet_url)

        # Forward headers and body
        headers = dict(request.headers)
        # Remove host header to avoid conflicts
        headers.pop('Host', None)

        app.logger.info(f"Proxying Ethereum withdrawal request to wallet service")

        response = requests.post(
            wallet_url,
            json=request.get_json(),
            headers=headers,
            timeout=60  # Longer timeout for blockchain operations
        )

        # Return the response from wallet service
        return jsonify(response.json()), response.status_code

    except requests.exceptions.RequestException as e:
        app.logger.error(f"Error forwarding Ethereum withdrawal to wallet service: {e}")
        return jsonify({"error": "Wallet service unavailable"}), 503
    except Exception as e:
        app.logger.error(f"Error processing Ethereum withdrawal proxy: {e}")
        return jsonify({"error": "Internal server error"}), 500

@api.route('/wallet/withdraw/ethereum/status/<reference_id>', methods=['GET'])
def ethereum_withdraw_status_proxy(reference_id):
    """Proxy Ethereum withdrawal status requests to wallet service"""
    try:
        # Forward the request to wallet service
        headers = {"Content-Type": "application/json", "Accept": "*/*"}

        # Forward authentication headers
        auth_headers = {}
        if 'Authorization' in request.headers:
            auth_headers['Authorization'] = request.headers['Authorization']

        # Forward query parameters
        params = request.args.to_dict()

        response = requests.get(
            f"{WALLET_SERVICE_URL}/wallet/withdraw/ethereum/status/{reference_id}",
            headers={**headers, **auth_headers},
            params=params
        )

        app.logger.info(f"Ethereum withdrawal status proxy: {response.status_code}")
        return jsonify(response.json()), response.status_code

    except Exception as e:
        app.logger.error(f"Error proxying Ethereum withdrawal status: {e}")
        return jsonify({"error": "Internal server error"}), 500

# Tron withdrawal proxy endpoints (TRX and TRC20)
@api.route('/wallet/withdraw/tron', methods=['POST'])
def tron_withdraw_proxy():
    """Proxy Tron withdrawals (native TRX and TRC20) to wallet service"""
    try:
        headers = {"Content-Type": "application/json", "Accept": "*/*"}
        # Forward auth header if present
        if 'Authorization' in request.headers:
            headers['Authorization'] = request.headers['Authorization']

        response = requests.post(
            f"{WALLET_SERVICE_URL}/wallet/withdraw/tron",
            json=request.get_json(),
            headers=headers,
            timeout=60,
        )
        app.logger.info(f"Tron withdrawal proxy: {response.status_code}")
        return jsonify(response.json()), response.status_code
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Error forwarding Tron withdrawal to wallet: {e}")
        return jsonify({"error": "Wallet service unavailable"}), 503
    except Exception as e:
        app.logger.error(f"Error processing Tron withdrawal proxy: {e}")
        return jsonify({"error": "Internal server error"}), 500

@api.route('/wallet/withdraw/solana', methods=['POST'])
def solana_withdraw_proxy():
    """Proxy Solana withdrawal requests to wallet service"""
    try:
        # Forward the request to wallet service
        headers = {"Content-Type": "application/json", "Accept": "*/*"}

        # Forward authentication headers
        auth_headers = {}
        if 'Authorization' in request.headers:
            auth_headers['Authorization'] = request.headers['Authorization']

        response = requests.post(
            f"{WALLET_SERVICE_URL}/wallet/withdraw/solana",
            json=request.get_json(),
            headers={**headers, **auth_headers}
        )

        app.logger.info(f"Solana withdrawal proxy: {response.status_code}")
        return jsonify(response.json()), response.status_code

    except Exception as e:
        app.logger.error(f"Error proxying Solana withdrawal: {e}")
        return jsonify({"error": "Internal server error"}), 500

@api.route('/wallet/withdraw/solana/status/<reference_id>', methods=['GET'])
def solana_withdraw_status_proxy(reference_id):
    """Proxy Solana withdrawal status requests to wallet service"""
    try:
        # Forward the request to wallet service
        headers = {"Content-Type": "application/json", "Accept": "*/*"}

        # Forward authentication headers
        auth_headers = {}
        if 'Authorization' in request.headers:
            auth_headers['Authorization'] = request.headers['Authorization']

        # Forward query parameters
        params = request.args.to_dict()

        response = requests.get(
            f"{WALLET_SERVICE_URL}/wallet/withdraw/solana/status/{reference_id}",
            headers={**headers, **auth_headers},
            params=params
        )

        app.logger.info(f"Solana withdrawal status proxy: {response.status_code}")
        return jsonify(response.json()), response.status_code

    except Exception as e:
        app.logger.error(f"Error proxying Solana withdrawal status: {e}")
        return jsonify({"error": "Internal server error"}), 500

# Trading endpoints proxy
@api.route('/api/trading/buy/calculate', methods=['POST'])
def trading_buy_calculate_proxy():
    """Proxy trading buy calculation requests to wallet service"""
    try:
        # Forward the request to wallet service
        headers = {"Content-Type": "application/json", "Accept": "*/*"}
        
        # Forward authentication headers
        auth_headers = {}
        if 'Authorization' in request.headers:
            auth_headers['Authorization'] = request.headers['Authorization']
        
        # Forward cookies
        cookies = request.cookies
        
        response = requests.post(
            f"{TRADING_SERVICE_URL}/api/trading/buy/calculate",
            json=request.get_json(),
            headers={**headers, **auth_headers},
            cookies=cookies
        )
        
        app.logger.info(f"Trading buy calculate proxy: {response.status_code}")
        return jsonify(response.json()), response.status_code
        
    except Exception as e:
        app.logger.error(f"Error proxying trading buy calculate: {e}")
        return jsonify({"error": "Internal server error"}), 500

@api.route('/api/trading/sell/calculate', methods=['POST'])
def trading_sell_calculate_proxy():
    """Proxy trading sell calculation requests to wallet service"""
    try:
        # Forward the request to wallet service
        headers = {"Content-Type": "application/json", "Accept": "*/*"}
        
        # Forward authentication headers
        auth_headers = {}
        if 'Authorization' in request.headers:
            auth_headers['Authorization'] = request.headers['Authorization']
        
        # Forward cookies
        cookies = request.cookies
        
        response = requests.post(
            f"{TRADING_SERVICE_URL}/api/trading/sell/calculate",
            json=request.get_json(),
            headers={**headers, **auth_headers},
            cookies=cookies
        )
        
        app.logger.info(f"Trading sell calculate proxy: {response.status_code}")
        return jsonify(response.json()), response.status_code
        
    except Exception as e:
        app.logger.error(f"Error proxying trading sell calculate: {e}")
        return jsonify({"error": "Internal server error"}), 500

@api.route('/api/trading/buy', methods=['POST'])
def trading_buy_proxy():
    """Proxy trading buy execution requests to wallet service"""
    try:
        # Forward the request to wallet service
        headers = {"Content-Type": "application/json", "Accept": "*/*"}
        
        # Forward authentication headers
        auth_headers = {}
        if 'Authorization' in request.headers:
            auth_headers['Authorization'] = request.headers['Authorization']
        
        # Forward cookies
        cookies = request.cookies
        
        response = requests.post(
            f"{TRADING_SERVICE_URL}/api/trading/buy",
            json=request.get_json(),
            headers={**headers, **auth_headers},
            cookies=cookies
        )
        
        app.logger.info(f"Trading buy proxy: {response.status_code}")
        return jsonify(response.json()), response.status_code
        
    except Exception as e:
        app.logger.error(f"Error proxying trading buy: {e}")
        return jsonify({"error": "Internal server error"}), 500

@api.route('/api/trading/sell', methods=['POST'])
def trading_sell_proxy():
    """Proxy trading sell execution requests to wallet service"""
    try:
        # Forward the request to wallet service
        headers = {"Content-Type": "application/json", "Accept": "*/*"}
        
        # Forward authentication headers
        auth_headers = {}
        if 'Authorization' in request.headers:
            auth_headers['Authorization'] = request.headers['Authorization']
        
        # Forward cookies
        cookies = request.cookies
        
        response = requests.post(
            f"{TRADING_SERVICE_URL}/api/trading/sell",
            json=request.get_json(),
            headers={**headers, **auth_headers},
            cookies=cookies
        )
        
        app.logger.info(f"Trading sell proxy: {response.status_code}")
        return jsonify(response.json()), response.status_code
        
    except Exception as e:
        app.logger.error(f"Error proxying trading sell: {e}")
        return jsonify({"error": "Internal server error"}), 500

@api.route('/api/trading/history', methods=['GET'])
def trading_history_proxy():
    """Proxy trading history requests to wallet service"""
    try:
        # Forward the request to wallet service
        headers = {"Content-Type": "application/json", "Accept": "*/*"}
        
        # Forward authentication headers
        auth_headers = {}
        if 'Authorization' in request.headers:
            auth_headers['Authorization'] = request.headers['Authorization']
        
        # Forward cookies
        cookies = request.cookies
        
        # Forward query parameters
        params = request.args.to_dict()
        
        response = requests.get(
            f"{TRADING_SERVICE_URL}/api/trading/history",
            headers={**headers, **auth_headers},
            cookies=cookies,
            params=params
        )
        
        app.logger.info(f"Trading history proxy: {response.status_code}")
        return jsonify(response.json()), response.status_code
        
    except Exception as e:
        app.logger.error(f"Error proxying trading history: {e}")
        return jsonify({"error": "Internal server error"}), 500

# Multi-network deposit proxy endpoints
@api.route('/wallet/deposit/networks/<token_symbol>', methods=['GET'])
def proxy_deposit_networks(token_symbol):
    """Proxy multi-network deposit networks request to wallet service"""
    try:
        headers = {"Authorization": request.headers.get("Authorization")}
        cookies = request.cookies
        
        # Forward query parameters (include_testnets)
        params = request.args.to_dict()
        
        resp = requests.get(
            f"{WALLET_SERVICE_URL}/deposit/networks/{token_symbol}",
            headers=headers, 
            cookies=cookies,
            params=params
        )
        
        app.logger.info(f"Multi-network deposit networks proxy: {resp.status_code}")
        return jsonify(resp.json()), resp.status_code
        
    except Exception as e:
        app.logger.error(f"Error proxying deposit networks for {token_symbol}: {e}")
        return jsonify({"error": "Internal server error"}), 500

@api.route('/wallet/deposit/address/<token_symbol>/<network_type>', methods=['GET'])
def proxy_deposit_address(token_symbol, network_type):
    """Proxy multi-network deposit address request to wallet service"""
    try:
        headers = {"Authorization": request.headers.get("Authorization")}
        cookies = request.cookies
        
        resp = requests.get(
            f"{WALLET_SERVICE_URL}/api/v1/wallet/deposit/address/{token_symbol}/{network_type}",
            headers=headers, 
            cookies=cookies
        )
        
        app.logger.info(f"Multi-network deposit address proxy: {resp.status_code}")
        return jsonify(resp.json()), resp.status_code
        
    except Exception as e:
        app.logger.error(f"Error proxying deposit address for {token_symbol}/{network_type}: {e}")
        return jsonify({"error": "Internal server error"}), 500


app.register_blueprint(api)
app.register_blueprint(mobile)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=True)
