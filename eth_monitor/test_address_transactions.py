#!/usr/bin/env python3
"""
Custom script to search for transactions for a specific address
Tests the Alchemy API directly to verify transaction detection
"""

import os
import sys
import json
from typing import Dict, Any, List

# Add paths for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shared'))

from shared.crypto.clients.eth import ETHWallet, EthereumConfig
from shared.logger import setup_logging
from db.connection import get_session

logger = setup_logging()

def test_address_transactions():
    """Test transaction detection for specific address"""
    
    # Target address and transaction
    target_address = "0x918cc5f65be2e0407412e86a4de96ee92de4ee8e"
    target_tx_hash = "0x7260259e12d73878c29544e84354f8fc9dac8f24441ef41e4f383d9263b8c102"
    
    logger.info(f"🔍 Testing transaction detection for address: {target_address}")
    logger.info(f"🎯 Looking for transaction: {target_tx_hash}")
    
    try:
        # Create ETH client
        api_key = os.getenv('ALCHEMY_API_KEY', 'EbcNdRQag_4Ep75VtLuPLV3-MMfLKMvH')
        eth_config = EthereumConfig.testnet(api_key)
        
        session = get_session()
        eth_client = ETHWallet(user_id=0, eth_config=eth_config, session=session, logger=logger)
        
        # Get current block number
        current_block = eth_client.get_latest_block_number()
        logger.info(f"📊 Current block: {current_block}")
        
        # Test different block ranges
        test_ranges = [
            (current_block - 100, current_block),      # Last 100 blocks
            (current_block - 1000, current_block),     # Last 1000 blocks  
            (current_block - 5000, current_block),     # Last 5000 blocks
        ]
        
        for from_block, to_block in test_ranges:
            logger.info(f"\n🔍 Testing range: {from_block} to {to_block} ({to_block - from_block} blocks)")
            
            # Test incoming transfers
            logger.info("📥 Checking incoming transfers...")
            transfers_to = eth_client.get_asset_transfers({
                "fromBlock": hex(from_block),
                "toBlock": hex(to_block),
                "toAddress": target_address,
                "category": ["external", "internal"],
                "withMetadata": True
            })
            
            logger.info(f"Found {len(transfers_to)} incoming transfers")
            for i, transfer in enumerate(transfers_to):
                tx_hash = transfer.get('hash', '').lower()
                logger.info(f"  {i+1}. Hash: {tx_hash}")
                logger.info(f"      From: {transfer.get('from', 'N/A')}")
                logger.info(f"      Value: {transfer.get('value', 0)} ETH")
                logger.info(f"      Block: {transfer.get('blockNum', 'N/A')}")
                
                if tx_hash == target_tx_hash.lower():
                    logger.info(f"🎉 FOUND TARGET TRANSACTION!")
                    logger.info(f"📝 Full transfer data: {json.dumps(transfer, indent=2)}")
            
            # Test outgoing transfers
            logger.info("📤 Checking outgoing transfers...")
            transfers_from = eth_client.get_asset_transfers({
                "fromBlock": hex(from_block),
                "toBlock": hex(to_block),
                "fromAddress": target_address,
                "category": ["external", "internal"],
                "withMetadata": True
            })
            
            logger.info(f"Found {len(transfers_from)} outgoing transfers")
            for i, transfer in enumerate(transfers_from):
                tx_hash = transfer.get('hash', '').lower()
                logger.info(f"  {i+1}. Hash: {tx_hash}")
                logger.info(f"      To: {transfer.get('to', 'N/A')}")
                logger.info(f"      Value: {transfer.get('value', 0)} ETH")
                logger.info(f"      Block: {transfer.get('blockNum', 'N/A')}")
                
                if tx_hash == target_tx_hash.lower():
                    logger.info(f"🎉 FOUND TARGET TRANSACTION!")
                    logger.info(f"📝 Full transfer data: {json.dumps(transfer, indent=2)}")
            
            total_transfers = len(transfers_to) + len(transfers_from)
            if total_transfers > 0:
                logger.info(f"✅ Range {from_block}-{to_block}: Found {total_transfers} total transfers")
                break
            else:
                logger.info(f"❌ Range {from_block}-{to_block}: No transfers found")
        
        # Test ERC-20 transfers as well
        logger.info(f"\n🪙 Testing ERC-20 transfers...")
        erc20_transfers_to = eth_client.get_asset_transfers({
            "fromBlock": hex(current_block - 1000),
            "toBlock": hex(current_block),
            "toAddress": target_address,
            "category": ["erc20"],
            "withMetadata": True
        })
        
        erc20_transfers_from = eth_client.get_asset_transfers({
            "fromBlock": hex(current_block - 1000),
            "toBlock": hex(current_block),
            "fromAddress": target_address,
            "category": ["erc20"],
            "withMetadata": True
        })
        
        logger.info(f"Found {len(erc20_transfers_to)} incoming ERC-20 transfers")
        logger.info(f"Found {len(erc20_transfers_from)} outgoing ERC-20 transfers")
        
        # Test specific transaction lookup
        logger.info(f"\n🔍 Testing direct transaction lookup...")
        try:
            tx_receipt = eth_client.get_transaction_receipt(target_tx_hash)
            if tx_receipt:
                logger.info(f"✅ Transaction receipt found!")
                logger.info(f"📝 Receipt: {json.dumps(tx_receipt, indent=2)}")
            else:
                logger.info(f"❌ Transaction receipt not found")
        except Exception as e:
            logger.error(f"❌ Error getting transaction receipt: {e}")
        
        session.close()
        
    except Exception as e:
        logger.error(f"❌ Error testing address transactions: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_address_transactions()
