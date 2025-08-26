#!/usr/bin/env python3
"""
Ethereum Webhook Manager for Alchemy webhooks.
Manages webhook subscriptions for Ethereum addresses.
"""

import requests
import json
import logging
from typing import List, Optional, Dict, Set
from decouple import config
from shared.logger import setup_logging

logger = setup_logging()

class EthereumWebhookManager:
    """Manages Alchemy webhook subscriptions for Ethereum addresses."""
    
    def __init__(self):
        self.auth_key = config('ALCHEMY_AUTH_KEY', default=None)
        self.webhook_id = config('ALCHEMY_ETH_WEBHOOK_ID', default=None)
        self.api_base = "https://dashboard.alchemy.com/api"
        
        if not self.auth_key:
            logger.warning("⚠️ ALCHEMY_AUTH_KEY not configured - webhook sync disabled")
    
    def get_webhook_addresses(self) -> List[str]:
        """Get current addresses configured in the webhook"""
        if not self.auth_key:
            logger.info("ℹ️ ALCHEMY_AUTH_KEY not configured - webhook sync disabled")
            return []
        
        if not self.webhook_id:
            logger.info("ℹ️ ALCHEMY_ETH_WEBHOOK_ID not configured - webhook sync disabled")
            return []
        
        try:
            headers = {
                "X-Alchemy-Token": self.auth_key
            }
            
            url = "https://dashboard.alchemy.com/api/webhook-addresses"
            params = {"webhook_id": self.webhook_id}
            
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code == 200:
                result = response.json()
                addresses = result.get('data', [])
                logger.info(f"📋 Retrieved {len(addresses)} addresses from webhook")
                return addresses
            elif response.status_code == 404:
                logger.warning(f"⚠️ Webhook {self.webhook_id} not found - webhook may not exist yet")
                return []
            else:
                logger.error(f"❌ Failed to get webhook addresses: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Error getting webhook addresses: {e}")
            return []
    
    def add_address_to_webhook(self, address: str) -> bool:
        """Add a single address to the webhook"""
        if not self.auth_key or not self.webhook_id:
            logger.info(f"ℹ️ Webhook not configured - skipping address {address}")
            return True  # Return True to not fail the sync process
        
        try:
            headers = {
                "X-Alchemy-Token": self.auth_key,
                "Content-Type": "application/json"
            }
            
            # Use the correct Alchemy API endpoint for updating webhook addresses
            url = "https://dashboard.alchemy.com/api/update-webhook-addresses"
            payload = {
                "webhook_id": self.webhook_id,
                "addresses_to_add": [address],
                "addresses_to_remove": []  # Required field even if empty
            }
            
            response = requests.patch(url, json=payload, headers=headers)
            
            if response.status_code == 200:
                logger.info(f"✅ Successfully added address {address} to webhook")
                return True
            else:
                logger.error(f"❌ Failed to add address {address}: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error adding address {address} to webhook: {e}")
            return False
    
    def add_addresses_to_webhook(self, addresses: List[str]) -> bool:
        """Add multiple addresses to the webhook in batch"""
        if not self.auth_key or not self.webhook_id:
            logger.info(f"ℹ️ Webhook not configured - skipping {len(addresses)} addresses")
            return True  # Return True to not fail the sync process
        
        if not addresses:
            return True
        
        try:
            headers = {
                "X-Alchemy-Token": self.auth_key,
                "Content-Type": "application/json"
            }
            
            # Use the correct Alchemy API endpoint for updating webhook addresses in batch
            url = "https://dashboard.alchemy.com/api/update-webhook-addresses"
            payload = {
                "webhook_id": self.webhook_id,
                "addresses_to_add": addresses,
                "addresses_to_remove": []  # Required field even if empty
            }
            
            response = requests.patch(url, json=payload, headers=headers)
            
            if response.status_code == 200:
                logger.info(f"✅ Successfully added {len(addresses)} addresses to webhook")
                return True
            else:
                logger.error(f"❌ Failed to add addresses: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error adding addresses to webhook: {e}")
            return False
    
    def remove_address_from_webhook(self, address: str) -> bool:
        """Remove an address from the webhook"""
        if not self.auth_key or not self.webhook_id:
            logger.warning(f"⚠️ Webhook not configured - cannot remove address {address}")
            return False
        
        try:
            headers = {
                "X-Alchemy-Token": self.auth_key,
                "Content-Type": "application/json"
            }
            
            # Get current webhook configuration
            webhook_url = f"{self.api_base}/webhook/{self.webhook_id}"
            response = requests.get(webhook_url, headers=headers)
            
            if response.status_code != 200:
                logger.error(f"❌ Failed to get webhook config: {response.status_code}")
                return False
            
            webhook_data = response.json()
            current_addresses = webhook_data.get('addresses', [])
            
            # Remove the address (case-insensitive)
            updated_addresses = [addr for addr in current_addresses if addr.lower() != address.lower()]
            
            if len(updated_addresses) == len(current_addresses):
                logger.info(f"ℹ️ Address {address} not found in webhook")
                return True
            
            # Update webhook with new address list
            update_payload = {
                "addresses": updated_addresses
            }
            
            update_url = f"{self.api_base}/update-webhook"
            update_response = requests.patch(update_url, json={
                "webhook_id": self.webhook_id,
                **update_payload
            }, headers=headers)
            
            if update_response.status_code == 200:
                logger.info(f"✅ Successfully removed address {address} from webhook")
                return True
            else:
                logger.error(f"❌ Failed to remove address {address}: {update_response.status_code}")
                logger.error(f"Response: {update_response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error removing address {address} from webhook: {e}")
            return False
    
    def get_webhook_info(self) -> Optional[Dict]:
        """Get webhook information"""
        if not self.auth_key or not self.webhook_id:
            return None
        
        try:
            headers = {
                "X-Alchemy-Token": self.auth_key,
                "Content-Type": "application/json"
            }
            
            url = f"{self.api_base}/webhook/{self.webhook_id}"
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"❌ Failed to get webhook info: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error getting webhook info: {e}")
            return None

# Global instance
eth_webhook_manager = EthereumWebhookManager()
