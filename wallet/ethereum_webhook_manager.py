#!/usr/bin/env python3
"""
Ethereum Webhook Manager for Alchemy webhooks.
Manages webhook subscriptions for Ethereum addresses.
"""

import logging
import requests
import json
from typing import List, Optional, Dict, Set
from sqlalchemy.orm import Session
from decouple import config
from db.connection import session
from db.wallet import CryptoAddress
from shared.logger import setup_logging

logger = setup_logging()

class EthereumWebhookManager:
    """Manages Alchemy webhook subscriptions for Ethereum addresses."""
    
    def __init__(self, network: str = "mainnet"):
        self.network = network
        self.auth_key = config('ALCHEMY_AUTH_KEY')
        self.signing_key = config('ALCHEMY_WEBHOOK_SIGNING_KEY', default=None)
        self.webhook_id = config('ALCHEMY_ETH_WEBHOOK_ID', default=None)
        
        # Webhook endpoint URLs
        base_url = config('APP_HOST', default='http://localhost:3030')
        self.webhook_url = f"{base_url}/api/v1/wallet/eth/callbacks/address-webhook"
        
        # Alchemy API endpoints
        self.api_base = "https://dashboard.alchemy.com/api"
        self.headers = {
            "X-Alchemy-Token": self.auth_key,
            "Content-Type": "application/json"
        }
        
        logger.info(f"🔧 Initialized Ethereum Webhook Manager for {network}")
        logger.info(f"📡 Webhook URL: {self.webhook_url}")
        logger.info(f"🆔 Webhook ID: {self.webhook_id or 'Not configured'}")
    
    def create_webhook(self) -> Optional[Dict]:
        """Create a new Alchemy webhook for Ethereum address activity"""
        try:
            network_name = "ETH_MAINNET" if self.network == "mainnet" else "ETH_SEPOLIA"
            
            payload = {
                "network": network_name,
                "webhook_type": "ADDRESS_ACTIVITY",
                "webhook_url": self.webhook_url,
                "addresses": [],  # Will be populated when addresses are added
                "app_id": config('ALCHEMY_APP_ID', default="dwt-backend")
            }
            
            url = f"{self.api_base}/create-webhook"
            
            logger.info(f"🔧 Creating Ethereum webhook...")
            logger.info(f"   URL: {self.webhook_url}")
            logger.info(f"   Network: {network_name}")
            logger.info(f"   Type: ADDRESS_ACTIVITY")
            
            response = requests.post(url, json=payload, headers=self.headers)
            
            if response.status_code == 200:
                result = response.json()
                webhook_id = result.get('id')
                signing_key = result.get('signing_key')
                
                logger.info(f"✅ Webhook created successfully!")
                logger.info(f"   Webhook ID: {webhook_id}")
                logger.info(f"   Signing Key: {signing_key}")
                
                # Store webhook configuration
                self.webhook_id = webhook_id
                self.signing_key = signing_key
                
                logger.info(f"\n📝 Add these to your environment:")
                logger.info(f"ALCHEMY_ETH_WEBHOOK_ID={webhook_id}")
                logger.info(f"ALCHEMY_WEBHOOK_SIGNING_KEY={signing_key}")
                
                return result
            else:
                logger.error(f"❌ Failed to create webhook: {response.status_code}")
                logger.error(f"   Response: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error creating webhook: {e}")
            return None
    
    def get_webhook_info(self, webhook_id: str = None) -> Optional[Dict]:
        """Get information about a webhook"""
        try:
            webhook_id = webhook_id or self.webhook_id
            if not webhook_id:
                logger.error("❌ No webhook ID provided")
                return None
            
            url = f"{self.api_base}/webhook/{webhook_id}"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"❌ Failed to get webhook info: {response.status_code}")
                logger.error(f"   Response: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error getting webhook info: {e}")
            return None
    
    def update_webhook_addresses(self, addresses: List[str], webhook_id: str = None) -> bool:
        """Update the list of addresses monitored by the webhook"""
        try:
            webhook_id = webhook_id or self.webhook_id
            if not webhook_id:
                logger.error("❌ No webhook ID provided")
                return False
            
            # Normalize addresses to lowercase
            normalized_addresses = [addr.lower() for addr in addresses]
            
            payload = {
                "addresses": normalized_addresses
            }
            
            url = f"{self.api_base}/update-webhook-addresses"
            
            logger.info(f"🔄 Updating webhook addresses...")
            logger.info(f"   Webhook ID: {webhook_id}")
            logger.info(f"   Addresses: {len(normalized_addresses)}")
            
            # Include webhook ID in payload
            payload["webhook_id"] = webhook_id
            
            response = requests.patch(url, json=payload, headers=self.headers)
            
            if response.status_code == 200:
                logger.info(f"✅ Successfully updated {len(normalized_addresses)} addresses")
                return True
            else:
                logger.error(f"❌ Failed to update addresses: {response.status_code}")
                logger.error(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error updating webhook addresses: {e}")
            return False
    
    def add_address_to_webhook(self, address: str, webhook_id: str = None) -> bool:
        """Add a single address to the webhook"""
        try:
            webhook_id = webhook_id or self.webhook_id
            if not webhook_id:
                logger.error("❌ No webhook ID provided")
                return False
            
            # Get current addresses
            webhook_info = self.get_webhook_info(webhook_id)
            if not webhook_info:
                logger.error("❌ Failed to get current webhook info")
                return False
            
            current_addresses = webhook_info.get('addresses', [])
            normalized_address = address.lower()
            
            # Check if address is already monitored
            if normalized_address in [addr.lower() for addr in current_addresses]:
                logger.info(f"⏭️ Address {normalized_address} already monitored")
                return True
            
            # Add new address
            updated_addresses = current_addresses + [normalized_address]
            return self.update_webhook_addresses(updated_addresses, webhook_id)
            
        except Exception as e:
            logger.error(f"❌ Error adding address to webhook: {e}")
            return False
    
    def remove_address_from_webhook(self, address: str, webhook_id: str = None) -> bool:
        """Remove a single address from the webhook"""
        try:
            webhook_id = webhook_id or self.webhook_id
            if not webhook_id:
                logger.error("❌ No webhook ID provided")
                return False
            
            # Get current addresses
            webhook_info = self.get_webhook_info(webhook_id)
            if not webhook_info:
                logger.error("❌ Failed to get current webhook info")
                return False
            
            current_addresses = webhook_info.get('addresses', [])
            normalized_address = address.lower()
            
            # Remove address (case-insensitive)
            updated_addresses = [addr for addr in current_addresses if addr.lower() != normalized_address]
            
            if len(updated_addresses) == len(current_addresses):
                logger.info(f"⏭️ Address {normalized_address} not found in webhook")
                return True
            
            return self.update_webhook_addresses(updated_addresses, webhook_id)
            
        except Exception as e:
            logger.error(f"❌ Error removing address from webhook: {e}")
            return False
    
    def sync_database_addresses(self, webhook_id: str = None) -> bool:
        """Sync all ETH addresses from database to webhook"""
        try:
            webhook_id = webhook_id or self.webhook_id
            if not webhook_id:
                logger.error("❌ No webhook ID provided")
                return False
            
            # Get all ETH addresses from database
            eth_addresses = session.query(CryptoAddress).filter(
                CryptoAddress.currency == 'ETH'
            ).all()
            
            addresses = [addr.address.lower() for addr in eth_addresses]
            
            logger.info(f"🔄 Syncing {len(addresses)} ETH addresses from database to webhook")
            
            return self.update_webhook_addresses(addresses, webhook_id)
            
        except Exception as e:
            logger.error(f"❌ Error syncing database addresses: {e}")
            return False
    
    def delete_webhook(self, webhook_id: str = None) -> bool:
        """Delete a webhook"""
        try:
            webhook_id = webhook_id or self.webhook_id
            if not webhook_id:
                logger.error("❌ No webhook ID provided")
                return False
            
            url = f"{self.api_base}/delete-webhook"
            payload = {"webhook_id": webhook_id}
            
            response = requests.delete(url, json=payload, headers=self.headers)
            
            if response.status_code == 200:
                logger.info(f"✅ Successfully deleted webhook {webhook_id}")
                return True
            else:
                logger.error(f"❌ Failed to delete webhook: {response.status_code}")
                logger.error(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error deleting webhook: {e}")
            return False
    
    def list_all_webhooks(self) -> Optional[List[Dict]]:
        """List all webhooks for the account"""
        try:
            url = f"{self.api_base}/webhooks"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                webhooks = response.json()
                logger.info(f"📋 Found {len(webhooks)} webhooks:")
                
                for webhook in webhooks:
                    logger.info(f"   ID: {webhook.get('id', 'N/A')}")
                    logger.info(f"   URL: {webhook.get('url', 'N/A')}")
                    logger.info(f"   Network: {webhook.get('network', 'N/A')}")
                    logger.info(f"   Type: {webhook.get('webhook_type', 'N/A')}")
                    logger.info(f"   Addresses: {len(webhook.get('addresses', []))}")
                    logger.info(f"   ---")
                
                return webhooks
            else:
                logger.error(f"❌ Failed to list webhooks: {response.status_code}")
                logger.error(f"   Response: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error listing webhooks: {e}")
            return None

def main():
    """CLI interface for webhook management"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python ethereum_webhook_manager.py <command> [args]")
        print("Commands:")
        print("  create                    - Create new webhook")
        print("  info [webhook_id]         - Get webhook info")
        print("  list                      - List all webhooks")
        print("  sync                      - Sync database addresses to webhook")
        print("  add <address>             - Add address to webhook")
        print("  remove <address>          - Remove address from webhook")
        print("  delete [webhook_id]       - Delete webhook")
        return
    
    command = sys.argv[1]
    manager = EthereumWebhookManager()
    
    if command == "create":
        manager.create_webhook()
    elif command == "info":
        webhook_id = sys.argv[2] if len(sys.argv) > 2 else None
        info = manager.get_webhook_info(webhook_id)
        if info:
            print(json.dumps(info, indent=2))
    elif command == "list":
        manager.list_all_webhooks()
    elif command == "sync":
        manager.sync_database_addresses()
    elif command == "add" and len(sys.argv) > 2:
        address = sys.argv[2]
        manager.add_address_to_webhook(address)
    elif command == "remove" and len(sys.argv) > 2:
        address = sys.argv[2]
        manager.remove_address_from_webhook(address)
    elif command == "delete":
        webhook_id = sys.argv[2] if len(sys.argv) > 2 else None
        manager.delete_webhook(webhook_id)
    else:
        print(f"Unknown command: {command}")

if __name__ == "__main__":
    main()
