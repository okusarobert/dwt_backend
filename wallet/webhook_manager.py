#!/usr/bin/env python3
"""
Webhook Manager for BlockCypher subscriptions.
Manages webhook subscriptions for crypto addresses.
"""

import logging
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from decouple import config
from blockcypher import subscribe_to_address_webhook, delete_webhook, get_webhook_info
from db.connection import session
from db.wallet import CryptoAddress
from shared.logger import setup_logging

logger = setup_logging()

class WebhookManager:
    """Manages BlockCypher webhook subscriptions for crypto addresses."""
    
    def __init__(self):
        self.api_key = config('BLOCKCYPHER_API_KEY')
        self.callback_url = f"{config('APP_HOST')}/api/v1/wallet/btc/callbacks/address-webhook"
        self.events = ["unconfirmed-tx", "confirmed-tx", "tx-confirmation", "tx-confidence", "double-spend-tx"]
    
    def create_webhook_subscription(self, address: str, event: str) -> Optional[str]:
        """Create a webhook subscription for an address and event."""
        try:
            response = subscribe_to_address_webhook(
                callback_url=self.callback_url,
                subscription_address=address,
                event=event,
                api_key=self.api_key
            )
            
            if response and hasattr(response, 'id'):
                logger.info(f"Created webhook for {event} on {address}: {response.id}")
                return response.id
            else:
                logger.error(f"Failed to create webhook for {event} on {address}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating webhook for {event} on {address}: {e}")
            return None
    
    def delete_webhook_subscription(self, webhook_id: str) -> bool:
        """Delete a webhook subscription by ID."""
        try:
            response = delete_webhook(webhook_id, api_key=self.api_key)
            logger.info(f"Deleted webhook {webhook_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting webhook {webhook_id}: {e}")
            return False
    
    def get_webhook_info(self, webhook_id: str) -> Optional[Dict]:
        """Get information about a webhook subscription."""
        try:
            response = get_webhook_info(webhook_id, api_key=self.api_key)
            return response
        except Exception as e:
            logger.error(f"Error getting webhook info for {webhook_id}: {e}")
            return None
    
    def create_all_webhooks_for_address(self, address: str) -> List[str]:
        """Create all webhook subscriptions for an address."""
        webhook_ids = []
        
        for event in self.events:
            webhook_id = self.create_webhook_subscription(address, event)
            if webhook_id:
                webhook_ids.append(webhook_id)
        
        return webhook_ids
    
    def delete_all_webhooks_for_address(self, webhook_ids: List[str]) -> bool:
        """Delete all webhook subscriptions for an address."""
        success = True
        
        for webhook_id in webhook_ids:
            if not self.delete_webhook_subscription(webhook_id):
                success = False
        
        return success
    
    def update_address_webhooks(self, crypto_address: CryptoAddress) -> bool:
        """Update webhook subscriptions for a crypto address."""
        try:
            # Delete existing webhooks if any
            if crypto_address.webhook_ids:
                existing_webhook_ids = crypto_address.webhook_ids
                self.delete_all_webhooks_for_address(existing_webhook_ids)
            
            # Create new webhooks
            new_webhook_ids = self.create_all_webhooks_for_address(crypto_address.address)
            
            if new_webhook_ids:
                crypto_address.webhook_ids = new_webhook_ids
                session.commit()
                logger.info(f"Updated webhooks for address {crypto_address.address}: {crypto_address.webhook_ids}")
                return True
            else:
                logger.error(f"Failed to create webhooks for address {crypto_address.address}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating webhooks for address {crypto_address.address}: {e}")
            session.rollback()
            return False
    
    def cleanup_inactive_webhooks(self) -> int:
        """Clean up webhooks for inactive addresses."""
        try:
            # Get all crypto addresses with webhook IDs
            addresses_with_webhooks = session.query(CryptoAddress).filter(
                CryptoAddress.webhook_ids.isnot(None),
                CryptoAddress.is_active == False
            ).all()
            
            cleaned_count = 0
            
            for address in addresses_with_webhooks:
                webhook_ids = address.webhook_ids
                if self.delete_all_webhooks_for_address(webhook_ids):
                    address.webhook_ids = None
                    cleaned_count += 1
            
            session.commit()
            logger.info(f"Cleaned up webhooks for {cleaned_count} inactive addresses")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error cleaning up inactive webhooks: {e}")
            session.rollback()
            return 0
    
    def list_all_webhooks(self) -> List[Dict]:
        """List all webhook subscriptions with their details."""
        try:
            addresses_with_webhooks = session.query(CryptoAddress).filter(
                CryptoAddress.webhook_ids.isnot(None)
            ).all()
            
            webhook_details = []
            
            for address in addresses_with_webhooks:
                webhook_ids = address.webhook_ids or []
                address_info = {
                    'address': address.address,
                    'currency': address.currency_code,
                    'is_active': address.is_active,
                    'webhook_ids': webhook_ids,
                    'webhook_details': []
                }
                
                for webhook_id in webhook_ids:
                    webhook_info = self.get_webhook_info(webhook_id)
                    if webhook_info:
                        address_info['webhook_details'].append(webhook_info)
                
                webhook_details.append(address_info)
            
            return webhook_details
            
        except Exception as e:
            logger.error(f"Error listing webhooks: {e}")
            return []

def main():
    """Main function for webhook management."""
    manager = WebhookManager()
    
    print("🔗 BlockCypher Webhook Manager")
    print("=" * 40)
    
    # List all webhooks
    print("\n📋 Current Webhook Subscriptions:")
    webhooks = manager.list_all_webhooks()
    
    if webhooks:
        for webhook in webhooks:
            print(f"  Address: {webhook['address']}")
            print(f"  Currency: {webhook['currency']}")
            print(f"  Active: {webhook['is_active']}")
            print(f"  Webhook IDs: {webhook['webhook_ids']}")
            print()
    else:
        print("  No webhook subscriptions found.")
    
    # Clean up inactive webhooks
    print("🧹 Cleaning up inactive webhooks...")
    cleaned = manager.cleanup_inactive_webhooks()
    print(f"  Cleaned up {cleaned} inactive webhooks.")

if __name__ == "__main__":
    main() 