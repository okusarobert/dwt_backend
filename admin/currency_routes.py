from flask import Blueprint, request, jsonify
from db.currency import Currency, CurrencyNetwork, Base
from db.connection import session
import os
import logging
import redis
import json
import time
from shared.currency_utils import clear_currency_cache

logger = logging.getLogger(__name__)

currency_bp = Blueprint('currency', __name__)

@currency_bp.route('/currencies', methods=['GET'])
def get_currencies():
    """Get all currencies with their network configurations"""
    try:
        currencies = session.query(Currency).all()
        
        result = {
            'success': True,
            'currencies': [currency.to_dict() for currency in currencies]
        }
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error getting currencies: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve currencies'
        }), 500
    finally:
        session.close()

@currency_bp.route('/currencies', methods=['POST'])
def create_currency():
    """Create a new currency"""
    try:
        data = request.get_json()
        
        # Validation
        if not data.get('symbol') or not data.get('name'):
            return jsonify({
                'success': False,
                'error': 'Symbol and name are required'
            }), 400
        
        
        # Check if currency already exists
        existing = session.query(Currency).filter_by(symbol=data['symbol'].upper()).first()
        if existing:
            session.close()
            return jsonify({
                'success': False,
                'error': f'Currency with symbol {data["symbol"]} already exists'
            }), 400
        
        # Create currency
        currency = Currency(
            symbol=data['symbol'].upper(),
            name=data['name'],
            is_enabled=data.get('is_enabled', True),
            is_multi_network=data.get('is_multi_network', False),
            contract_address=data.get('contract_address'),
            decimals=data.get('decimals', 18)
        )
        
        session.add(currency)
        session.flush()  # Get the currency ID
        
        # Add networks if multi-network
        if data.get('is_multi_network') and data.get('networks'):
            for network_data in data['networks']:
                network = CurrencyNetwork(
                    currency_id=currency.id,
                    network_type=network_data['network_type'],
                    network_name=network_data['network_name'],
                    display_name=network_data['display_name'],
                    is_enabled=network_data.get('is_enabled', True),
                    contract_address=network_data.get('contract_address'),
                    confirmation_blocks=network_data.get('confirmation_blocks', 12),
                    explorer_url=network_data['explorer_url'],
                    is_testnet=network_data.get('is_testnet', False)
                )
                session.add(network)
        
        session.commit()
        
        result = {
            'success': True,
            'currency': currency.to_dict()
        }
        
        session.close()
        return jsonify(result), 201
        
    except Exception as e:
        logger.error(f"Error creating currency: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to create currency'
        }), 500

@currency_bp.route('/currencies/<currency_id>', methods=['PUT'])
def update_currency(currency_id):
    """Update an existing currency"""
    try:
        data = request.get_json()
        
        currency = session.query(Currency).filter_by(id=currency_id).first()
        if not currency:
            session.close()
            return jsonify({
                'success': False,
                'error': 'Currency not found'
            }), 404
        
        # Update currency fields
        if 'symbol' in data:
            # Check if new symbol conflicts with existing currency
            existing = session.query(Currency).filter_by(symbol=data['symbol'].upper()).first()
            if existing and existing.id != currency_id:
                session.close()
                return jsonify({
                    'success': False,
                    'error': f'Currency with symbol {data["symbol"]} already exists'
                }), 400
            currency.symbol = data['symbol'].upper()
        
        if 'name' in data:
            currency.name = data['name']
        if 'is_enabled' in data:
            currency.is_enabled = data['is_enabled']
        if 'is_multi_network' in data:
            currency.is_multi_network = data['is_multi_network']
        if 'contract_address' in data:
            currency.contract_address = data['contract_address']
        if 'decimals' in data:
            currency.decimals = data['decimals']
        
        # Update networks
        if 'networks' in data:
            # Remove existing networks
            session.query(CurrencyNetwork).filter_by(currency_id=currency_id).delete()
            
            # Add new networks
            for network_data in data['networks']:
                network = CurrencyNetwork(
                    currency_id=currency.id,
                    network_type=network_data['network_type'],
                    network_name=network_data['network_name'],
                    display_name=network_data['display_name'],
                    is_enabled=network_data.get('is_enabled', True),
                    contract_address=network_data.get('contract_address'),
                    confirmation_blocks=network_data.get('confirmation_blocks', 12),
                    explorer_url=network_data['explorer_url'],
                    is_testnet=network_data.get('is_testnet', False)
                )
                session.add(network)
        
        session.commit()
        
        # Clear currency cache and notify services
        clear_currency_cache()
        notify_currency_change(currency.symbol, 'updated')
        
        result = {
            'success': True,
            'currency': currency.to_dict()
        }
        
        session.close()
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error updating currency: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to update currency'
        }), 500

@currency_bp.route('/currencies/<currency_id>/status', methods=['PATCH'])
def update_currency_status(currency_id):
    """Update currency enabled/disabled status"""
    try:
        data = request.get_json()
        
        currency = session.query(Currency).filter_by(id=currency_id).first()
        if not currency:
            session.close()
            return jsonify({
                'success': False,
                'error': 'Currency not found'
            }), 404
        
        old_status = currency.is_enabled
        currency.is_enabled = data.get('is_enabled', currency.is_enabled)
        session.commit()
        
        # Clear currency cache and notify services if status changed
        if old_status != currency.is_enabled:
            clear_currency_cache()
            action = 'enabled' if currency.is_enabled else 'disabled'
            notify_currency_change(currency.symbol, action)
        
        result = {
            'success': True,
            'currency': currency.to_dict()
        }
        
        session.close()
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error updating currency status: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to update currency status'
        }), 500

def notify_currency_change(symbol: str, action: str):
    """Notify all services about currency changes via Redis"""
    try:
        redis_host = os.environ.get('REDIS_HOST', 'redis')
        redis_port = int(os.environ.get('REDIS_PORT', 6379))
        r = redis.Redis(host=redis_host, port=redis_port, db=0)
        
        message = {
            'type': 'currency_change',
            'symbol': symbol,
            'action': action,
            'timestamp': int(time.time())
        }
        
        # Publish to Redis channel
        r.publish('currency_updates', json.dumps(message))
        logger.info(f"Published currency change notification: {symbol} {action}")
    except Exception as e:
        logger.error(f"Failed to publish currency change notification: {e}")

@currency_bp.route('/currencies/<currency_id>', methods=['DELETE'])
def delete_currency(currency_id):
    """Delete a currency and all its networks"""
    try:
        
        currency = session.query(Currency).filter_by(id=currency_id).first()
        if not currency:
            session.close()
            return jsonify({
                'success': False,
                'error': 'Currency not found'
            }), 404
        
        # Delete currency (networks will be deleted via cascade)
        session.delete(currency)
        session.commit()
        
        result = {
            'success': True,
            'message': f'Currency {currency.symbol} deleted successfully'
        }
        
        session.close()
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error deleting currency: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to delete currency'
        }), 500

@currency_bp.route('/currencies/<currency_id>', methods=['GET'])
def get_currency(currency_id):
    """Get a specific currency by ID"""
    try:
        
        currency = session.query(Currency).filter_by(id=currency_id).first()
        if not currency:
            session.close()
            return jsonify({
                'success': False,
                'error': 'Currency not found'
            }), 404
        
        result = {
            'success': True,
            'currency': currency.to_dict()
        }
        
        session.close()
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error getting currency: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve currency'
        }), 500
