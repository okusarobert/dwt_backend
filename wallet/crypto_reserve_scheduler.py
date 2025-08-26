#!/usr/bin/env python3
"""
Crypto Reserve Scheduler
Schedules and manages crypto sweeping operations
"""

import os
import sys
import time
import threading
import schedule
import logging
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wallet.crypto_sweeper_service import CryptoSweeperService
from shared.logger import setup_logging

# Configure logging
logger = setup_logging(__name__)

class CryptoReserveScheduler:
    """Scheduler for crypto reserve operations"""
    
    def __init__(self):
        self.sweeper = CryptoSweeperService()
        self.running = False
        self.scheduler_thread = None
    
    def start_scheduler(self):
        """Start the background scheduler"""
        if self.running:
            logger.warning("Scheduler is already running")
            return
        
        logger.info("🚀 Starting Crypto Reserve Scheduler")
        
        # Schedule sweep operations
        schedule.every(30).minutes.do(self.run_sweep_job)  # Every 30 minutes
        schedule.every().hour.at(":00").do(self.log_reserve_status)  # Every hour
        schedule.every().day.at("02:00").do(self.daily_sweep_report)  # Daily at 2 AM
        
        self.running = True
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        logger.info("✅ Crypto Reserve Scheduler started")
    
    def stop_scheduler(self):
        """Stop the background scheduler"""
        if not self.running:
            return
        
        logger.info("🛑 Stopping Crypto Reserve Scheduler")
        self.running = False
        
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        
        schedule.clear()
        logger.info("✅ Crypto Reserve Scheduler stopped")
    
    def _run_scheduler(self):
        """Internal scheduler loop"""
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                time.sleep(60)
    
    def run_sweep_job(self):
        """Run a sweep cycle"""
        try:
            logger.info("⏰ Scheduled sweep job starting")
            results = self.sweeper.run_sweep_cycle()
            
            successful = len([r for r in results if r.success])
            failed = len([r for r in results if not r.success])
            
            logger.info(f"⏰ Scheduled sweep completed: {successful} successful, {failed} failed")
            
        except Exception as e:
            logger.error(f"Error in scheduled sweep job: {e}")
    
    def log_reserve_status(self):
        """Log current reserve balances"""
        try:
            logger.info("📊 Hourly Reserve Status:")
            balances = self.sweeper.get_reserve_balances()
            
            for currency, balance in balances.items():
                logger.info(f"  {currency}: {balance}")
                
        except Exception as e:
            logger.error(f"Error logging reserve status: {e}")
    
    def daily_sweep_report(self):
        """Generate daily sweep report"""
        try:
            logger.info("📈 Daily Sweep Report:")
            
            # Get current balances
            balances = self.sweeper.get_reserve_balances()
            
            logger.info("Reserve Balances:")
            for currency, balance in balances.items():
                logger.info(f"  {currency}: {balance}")
            
            # TODO: Add more detailed reporting (transactions, volumes, etc.)
            
        except Exception as e:
            logger.error(f"Error generating daily report: {e}")

def main():
    """Main function to run the scheduler"""
    logger.info("🕐 Crypto Reserve Scheduler Starting")
    
    scheduler = CryptoReserveScheduler()
    
    try:
        scheduler.start_scheduler()
        
        # Keep the main thread alive
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception as e:
        logger.error(f"Error in scheduler main: {e}")
    finally:
        scheduler.stop_scheduler()
        logger.info("🕐 Crypto Reserve Scheduler Stopped")

if __name__ == "__main__":
    main()
