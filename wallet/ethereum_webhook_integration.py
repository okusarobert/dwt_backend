#!/usr/bin/env python3
"""
Ethereum Webhook Integration Service
Integrates Ethereum address creation with webhook registration
"""

import logging
from typing import Optional
from sqlalchemy.orm import Session
from db.connection import session
from db.wallet import CryptoAddress
from ethereum_webhook_manager import EthereumWebhookManager
from shared.logger import setup_logging

logger = setup_logging()

class EthereumWebhookIntegration:
    """Service to integrate Ethereum address creation with webhook registration"""
    
    def __init__(self, network: str = "mainnet"):
        self.webhook_manager = EthereumWebhookManager(network)
        self.network = network
        logger.info(f"🔧 Initialized Ethereum Webhook Integration for {network}")
    
    def register_address_for_monitoring(self, address: str, crypto_address_id: int) -> bool:
        """Register an Ethereum address for webhook monitoring"""
        try:
            logger.info(f"📝 Registering ETH address for monitoring: {address}")
            
            # Add address to webhook
            success = self.webhook_manager.add_address_to_webhook(address)
            
            if success:
                # Update database record with webhook registration status
                crypto_address = session.query(CryptoAddress).filter(
                    CryptoAddress.id == crypto_address_id
                ).first()
                
                if crypto_address:
                    if not crypto_address.metadata_json:
                        crypto_address.metadata_json = {}
                    
                    crypto_address.metadata_json.update({
                        "webhook_registered": True,
                        "webhook_id": self.webhook_manager.webhook_id,
                        "webhook_network": self.network
                    })
                    
                    session.commit()
                    logger.info(f"✅ Successfully registered ETH address {address} for webhook monitoring")
                    return True
                else:
                    logger.error(f"❌ CryptoAddress record not found for ID {crypto_address_id}")
                    return False
            else:
                logger.error(f"❌ Failed to register ETH address {address} with webhook")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error registering ETH address for monitoring: {e}")
            session.rollback()
            return False
    
    def unregister_address_from_monitoring(self, address: str, crypto_address_id: int) -> bool:
        """Unregister an Ethereum address from webhook monitoring"""
        try:
            logger.info(f"🗑️ Unregistering ETH address from monitoring: {address}")
            
            # Remove address from webhook
            success = self.webhook_manager.remove_address_from_webhook(address)
            
            if success:
                # Update database record
                crypto_address = session.query(CryptoAddress).filter(
                    CryptoAddress.id == crypto_address_id
                ).first()
                
                if crypto_address and crypto_address.metadata_json:
                    crypto_address.metadata_json.update({
                        "webhook_registered": False,
                        "webhook_unregistered_at": datetime.datetime.utcnow().isoformat()
                    })
                    
                    session.commit()
                    logger.info(f"✅ Successfully unregistered ETH address {address} from webhook monitoring")
                    return True
            
            logger.error(f"❌ Failed to unregister ETH address {address} from webhook")
            return False
            
        except Exception as e:
            logger.error(f"❌ Error unregistering ETH address from monitoring: {e}")
            session.rollback()
            return False
    
    def sync_all_addresses(self) -> bool:
        """Sync all ETH addresses from database to webhook"""
        try:
            logger.info("🔄 Syncing all ETH addresses to webhook...")
            
            success = self.webhook_manager.sync_database_addresses()
            
            if success:
                # Update all ETH addresses in database to mark as webhook registered
                eth_addresses = session.query(CryptoAddress).filter(
                    CryptoAddress.currency == 'ETH'
                ).all()
                
                for crypto_address in eth_addresses:
                    if not crypto_address.metadata_json:
                        crypto_address.metadata_json = {}
                    
                    crypto_address.metadata_json.update({
                        "webhook_registered": True,
                        "webhook_id": self.webhook_manager.webhook_id,
                        "webhook_network": self.network,
                        "synced_at": datetime.datetime.utcnow().isoformat()
                    })
                
                session.commit()
                logger.info(f"✅ Successfully synced {len(eth_addresses)} ETH addresses to webhook")
                return True
            else:
                logger.error("❌ Failed to sync addresses to webhook")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error syncing addresses to webhook: {e}")
            session.rollback()
            return False
    
    def get_webhook_status(self) -> Optional[dict]:
        """Get current webhook status and statistics"""
        try:
            webhook_info = self.webhook_manager.get_webhook_info()
            if not webhook_info:
                return None
            
            # Count addresses in database
            db_addresses_count = session.query(CryptoAddress).filter(
                CryptoAddress.currency == 'ETH'
            ).count()
            
            webhook_addresses_count = len(webhook_info.get('addresses', []))
            
            return {
                "webhook_id": webhook_info.get('id'),
                "webhook_url": webhook_info.get('url'),
                "network": webhook_info.get('network'),
                "webhook_type": webhook_info.get('webhook_type'),
                "addresses_in_webhook": webhook_addresses_count,
                "addresses_in_database": db_addresses_count,
                "addresses_synced": webhook_addresses_count == db_addresses_count,
                "status": "active" if webhook_info.get('is_active', True) else "inactive"
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting webhook status: {e}")
            return None

# Global instance for easy access
ethereum_webhook_integration = EthereumWebhookIntegration()

def register_eth_address_for_monitoring(address: str, crypto_address_id: int) -> bool:
    """Convenience function to register ETH address for monitoring"""
    return ethereum_webhook_integration.register_address_for_monitoring(address, crypto_address_id)

def unregister_eth_address_from_monitoring(address: str, crypto_address_id: int) -> bool:
    """Convenience function to unregister ETH address from monitoring"""
    return ethereum_webhook_integration.unregister_address_from_monitoring(address, crypto_address_id)

def sync_all_eth_addresses() -> bool:
    """Convenience function to sync all ETH addresses"""
    return ethereum_webhook_integration.sync_all_addresses()

def get_eth_webhook_status() -> Optional[dict]:
    """Convenience function to get webhook status"""
    return ethereum_webhook_integration.get_webhook_status()

if __name__ == "__main__":
    import sys
    import datetime
    
    if len(sys.argv) < 2:
        print("Usage: python ethereum_webhook_integration.py <command> [args]")
        print("Commands:")
        print("  sync                      - Sync all ETH addresses to webhook")
        print("  status                    - Get webhook status")
        print("  register <address> <id>   - Register address for monitoring")
        print("  unregister <address> <id> - Unregister address from monitoring")
        return
    
    command = sys.argv[1]
    
    if command == "sync":
        success = sync_all_eth_addresses()
        print(f"Sync {'successful' if success else 'failed'}")
    elif command == "status":
        status = get_eth_webhook_status()
        if status:
            print("Webhook Status:")
            for key, value in status.items():
                print(f"  {key}: {value}")
        else:
            print("Failed to get webhook status")
    elif command == "register" and len(sys.argv) > 3:
        address = sys.argv[2]
        crypto_id = int(sys.argv[3])
        success = register_eth_address_for_monitoring(address, crypto_id)
        print(f"Registration {'successful' if success else 'failed'}")
    elif command == "unregister" and len(sys.argv) > 3:
        address = sys.argv[2]
        crypto_id = int(sys.argv[3])
        success = unregister_eth_address_from_monitoring(address, crypto_id)
        print(f"Unregistration {'successful' if success else 'failed'}")
    else:
        print(f"Unknown command: {command}")
