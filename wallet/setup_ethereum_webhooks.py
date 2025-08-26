#!/usr/bin/env python3
"""
Setup script for Ethereum webhook monitoring system
Initializes Alchemy webhooks and configures the monitoring system
"""

import os
import sys
import json
from decouple import config
from shared.logger import setup_logging

# Add paths for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shared'))

from ethereum_webhook_manager import EthereumWebhookManager
from ethereum_webhook_integration import EthereumWebhookIntegration

logger = setup_logging()

def check_environment_variables():
    """Check if required environment variables are set"""
    required_vars = [
        'ALCHEMY_AUTH_KEY',
        'APP_HOST'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not config(var, default=None):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        logger.info("📝 Please set the following environment variables:")
        logger.info("   ALCHEMY_AUTH_KEY=<your_alchemy_auth_key>")
        logger.info("   APP_HOST=<your_app_host_url>")
        return False
    
    logger.info("✅ All required environment variables are set")
    return True

def create_ethereum_webhook():
    """Create a new Ethereum webhook"""
    try:
        logger.info("🔧 Creating Ethereum webhook...")
        
        manager = EthereumWebhookManager()
        result = manager.create_webhook()
        
        if result:
            webhook_id = result.get('id')
            signing_key = result.get('signing_key')
            
            logger.info("✅ Ethereum webhook created successfully!")
            logger.info(f"📝 Please add these to your environment variables:")
            logger.info(f"ALCHEMY_ETH_WEBHOOK_ID={webhook_id}")
            logger.info(f"ALCHEMY_WEBHOOK_SIGNING_KEY={signing_key}")
            
            return True
        else:
            logger.error("❌ Failed to create Ethereum webhook")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error creating webhook: {e}")
        return False

def sync_existing_addresses():
    """Sync all existing ETH addresses to the webhook"""
    try:
        logger.info("🔄 Syncing existing ETH addresses to webhook...")
        
        integration = EthereumWebhookIntegration()
        success = integration.sync_all_addresses()
        
        if success:
            logger.info("✅ Successfully synced all ETH addresses to webhook")
            return True
        else:
            logger.error("❌ Failed to sync addresses to webhook")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error syncing addresses: {e}")
        return False

def verify_webhook_setup():
    """Verify that the webhook is properly configured"""
    try:
        logger.info("🔍 Verifying webhook setup...")
        
        integration = EthereumWebhookIntegration()
        status = integration.get_webhook_status()
        
        if status:
            logger.info("📊 Webhook Status:")
            logger.info(f"   Webhook ID: {status.get('webhook_id')}")
            logger.info(f"   Network: {status.get('network')}")
            logger.info(f"   Status: {status.get('status')}")
            logger.info(f"   Addresses in webhook: {status.get('addresses_in_webhook')}")
            logger.info(f"   Addresses in database: {status.get('addresses_in_database')}")
            logger.info(f"   Synced: {status.get('addresses_synced')}")
            
            if status.get('status') == 'active' and status.get('addresses_synced'):
                logger.info("✅ Webhook setup verification successful")
                return True
            else:
                logger.warning("⚠️ Webhook setup has issues")
                return False
        else:
            logger.error("❌ Failed to get webhook status")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error verifying webhook setup: {e}")
        return False

def list_existing_webhooks():
    """List all existing webhooks"""
    try:
        logger.info("📋 Listing existing webhooks...")
        
        manager = EthereumWebhookManager()
        webhooks = manager.list_all_webhooks()
        
        if webhooks:
            logger.info(f"Found {len(webhooks)} existing webhooks")
            return webhooks
        else:
            logger.info("No existing webhooks found")
            return []
            
    except Exception as e:
        logger.error(f"❌ Error listing webhooks: {e}")
        return []

def setup_ethereum_webhooks(force_create=False):
    """Complete setup of Ethereum webhook monitoring system"""
    logger.info("🚀 Setting up Ethereum webhook monitoring system...")
    
    # Check environment variables
    if not check_environment_variables():
        return False
    
    # Check if webhook already exists
    webhook_id = config('ALCHEMY_ETH_WEBHOOK_ID', default=None)
    signing_key = config('ALCHEMY_WEBHOOK_SIGNING_KEY', default=None)
    
    if webhook_id and signing_key and not force_create:
        logger.info(f"✅ Webhook already configured (ID: {webhook_id})")
    else:
        # List existing webhooks
        existing_webhooks = list_existing_webhooks()
        
        # Create new webhook if needed
        if force_create or not webhook_id:
            if not create_ethereum_webhook():
                return False
    
    # Sync existing addresses
    if not sync_existing_addresses():
        logger.warning("⚠️ Address sync failed, but continuing...")
    
    # Verify setup
    if verify_webhook_setup():
        logger.info("🎉 Ethereum webhook monitoring system setup completed successfully!")
        logger.info("📝 Next steps:")
        logger.info("   1. Update your environment variables with the webhook credentials")
        logger.info("   2. Restart your wallet service to load the new configuration")
        logger.info("   3. Start the webhook monitor service")
        logger.info("   4. Test the webhook by creating a new ETH address")
        return True
    else:
        logger.error("❌ Webhook setup verification failed")
        return False

def main():
    """CLI interface for webhook setup"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Setup Ethereum webhook monitoring system')
    parser.add_argument('command', choices=['setup', 'create', 'sync', 'verify', 'list'], 
                       help='Command to execute')
    parser.add_argument('--force', action='store_true', 
                       help='Force create new webhook even if one exists')
    
    args = parser.parse_args()
    
    if args.command == 'setup':
        success = setup_ethereum_webhooks(force_create=args.force)
        sys.exit(0 if success else 1)
    elif args.command == 'create':
        success = create_ethereum_webhook()
        sys.exit(0 if success else 1)
    elif args.command == 'sync':
        success = sync_existing_addresses()
        sys.exit(0 if success else 1)
    elif args.command == 'verify':
        success = verify_webhook_setup()
        sys.exit(0 if success else 1)
    elif args.command == 'list':
        list_existing_webhooks()
        sys.exit(0)

if __name__ == "__main__":
    main()
