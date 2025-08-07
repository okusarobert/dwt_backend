#!/usr/bin/env python3
"""
Bitcoin Polling Monitor - Works during Initial Block Download
Monitors for new blocks and transactions using RPC polling
"""

import time
import json
import logging
import signal
import sys
import subprocess
from typing import Dict, Any, Optional
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BitcoinPollingMonitor:
    """Bitcoin monitor using RPC polling (works during IBD)"""
    
    def __init__(self, poll_interval: int = 10):
        """Initialize the polling monitor"""
        self.poll_interval = poll_interval
        self.is_running = False
        self.last_block_hash = None
        self.last_block_height = None
        self.stats = {
            'blocks_processed': 0,
            'transactions_processed': 0,
            'errors': 0,
            'start_time': None
        }
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"📡 Received signal {signum}, shutting down gracefully...")
        self.stop_monitoring()
        sys.exit(0)
    
    def _run_bitcoin_cli(self, command: str) -> Optional[Dict[str, Any]]:
        """Run a Bitcoin CLI command"""
        try:
            result = subprocess.run([
                'docker', 'exec', 'bitcoin', 'bitcoin-cli',
                '-conf=/home/bitcoin/.bitcoin/bitcoin.conf',
                '-rpcuser=bitcoin', '-rpcpassword=bitcoinpassword'
            ] + command.split(), capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                # Handle different return types
                output = result.stdout.strip()
                
                # Try to parse as JSON first
                try:
                    return json.loads(output)
                except json.JSONDecodeError:
                    # If not JSON, return as string for simple commands
                    return output
            else:
                logger.error(f"❌ Bitcoin CLI error: {result.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error running Bitcoin CLI: {e}")
            return None
    
    def _get_blockchain_info(self) -> Optional[Dict[str, Any]]:
        """Get blockchain info"""
        return self._run_bitcoin_cli('getblockchaininfo')
    
    def _get_best_block_hash(self) -> Optional[str]:
        """Get the best block hash"""
        result = self._run_bitcoin_cli('getbestblockhash')
        return result if isinstance(result, str) else None
    
    def _get_block_count(self) -> Optional[int]:
        """Get the current block count"""
        result = self._run_bitcoin_cli('getblockcount')
        return result if isinstance(result, int) else None
    
    def _get_block_info(self, block_hash: str) -> Optional[Dict[str, Any]]:
        """Get block information"""
        return self._run_bitcoin_cli(f'getblock {block_hash}')
    
    def _process_new_block(self, block_hash: str, block_height: int):
        """Process a new block"""
        try:
            logger.info(f"📦 New block detected: {block_hash[:16]}... (height: {block_height})")
            
            # Get detailed block info
            block_info = self._get_block_info(block_hash)
            if block_info:
                tx_count = len(block_info.get('tx', []))
                logger.info(f"   📊 Block contains {tx_count} transactions")
                
                # Process transactions in the block
                for tx_hash in block_info.get('tx', []):
                    self._process_transaction(tx_hash, block_hash, block_height)
            
            self.stats['blocks_processed'] += 1
            
        except Exception as e:
            logger.error(f"❌ Error processing block: {e}")
            self.stats['errors'] += 1
    
    def _process_transaction(self, tx_hash: str, block_hash: str, block_height: int):
        """Process a transaction"""
        try:
            logger.info(f"   💰 Transaction: {tx_hash[:16]}... in block {block_height}")
            self.stats['transactions_processed'] += 1
            
        except Exception as e:
            logger.error(f"❌ Error processing transaction: {e}")
            self.stats['errors'] += 1
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        logger.info("🔍 Starting Bitcoin polling monitor...")
        
        while self.is_running:
            try:
                # Get current blockchain info
                blockchain_info = self._get_blockchain_info()
                if not blockchain_info:
                    time.sleep(self.poll_interval)
                    continue
                
                # Get current best block
                current_block_hash = self._get_best_block_hash()
                current_block_height = self._get_block_count()
                
                if not current_block_hash or current_block_height is None:
                    time.sleep(self.poll_interval)
                    continue
                
                # Check if we have a new block
                if (self.last_block_hash and 
                    self.last_block_hash != current_block_hash):
                    
                    # Process the new block
                    self._process_new_block(current_block_hash, current_block_height)
                
                # Update our last known block
                self.last_block_hash = current_block_hash
                self.last_block_height = current_block_height
                
                # Log sync progress if in IBD
                if blockchain_info.get('initialblockdownload', False):
                    progress = blockchain_info.get('verificationprogress', 0) * 100
                    logger.info(f"📊 Sync progress: {progress:.2f}% | "
                              f"Blocks: {current_block_height} | "
                              f"Headers: {blockchain_info.get('headers', 0)}")
                
                # Wait before next poll
                time.sleep(self.poll_interval)
                
            except Exception as e:
                logger.error(f"❌ Error in monitoring loop: {e}")
                self.stats['errors'] += 1
                time.sleep(self.poll_interval)
    
    def start_monitoring(self):
        """Start monitoring"""
        if self.is_running:
            logger.warning("⚠️  Monitoring is already running")
            return
        
        self.is_running = True
        self.stats['start_time'] = datetime.now()
        logger.info("🚀 Starting Bitcoin polling monitoring...")
        
        # Get initial block info
        blockchain_info = self._get_blockchain_info()
        if blockchain_info:
            self.last_block_hash = blockchain_info.get('bestblockhash')
            self.last_block_height = blockchain_info.get('blocks', 0)
            logger.info(f"📋 Starting from block: {self.last_block_hash[:16]}... "
                       f"(height: {self.last_block_height})")
        
        # Start monitoring
        self._monitor_loop()
    
    def stop_monitoring(self):
        """Stop monitoring"""
        if not self.is_running:
            logger.warning("⚠️  Monitoring is not running")
            return
        
        self.is_running = False
        logger.info("⏹️  Stopping Bitcoin polling monitoring...")
        
        # Print final statistics
        runtime = None
        if self.stats['start_time']:
            runtime = datetime.now() - self.stats['start_time']
        
        logger.info(f"📊 Final stats: {self.stats}")
        if runtime:
            logger.info(f"⏱️  Runtime: {runtime}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get monitoring statistics"""
        runtime = None
        if self.stats['start_time']:
            runtime = datetime.now() - self.stats['start_time']
        
        return {
            **self.stats,
            'runtime': runtime,
            'is_running': self.is_running,
            'last_block_hash': self.last_block_hash,
            'last_block_height': self.last_block_height
        }


def main():
    """Run the polling monitor"""
    print("🔔 Bitcoin Polling Monitor (Works during IBD)")
    print("=" * 50)
    print("📡 Starting continuous monitoring...")
    print("💡 Press Ctrl+C to stop")
    print()
    
    # Create monitor
    monitor = BitcoinPollingMonitor(poll_interval=5)  # Poll every 5 seconds
    
    try:
        # Start monitoring
        monitor.start_monitoring()
        
    except KeyboardInterrupt:
        logger.info("⏹️  Received interrupt signal, shutting down...")
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
    finally:
        monitor.stop_monitoring()
        logger.info("✅ Monitoring stopped")


if __name__ == "__main__":
    main() 