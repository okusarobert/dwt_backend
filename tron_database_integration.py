#!/usr/bin/env python3
"""
TRON Database Integration for transaction storage and management
Integrates with existing database models for TRON transactions
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

# Import your existing database models
from db.connection import session
from db.wallet import Transaction, TransactionType, TransactionStatus, CryptoAddress, PaymentProvider

logger = logging.getLogger(__name__)

class TronDatabaseIntegration:
    """Database integration for TRON transactions"""
    
    def __init__(self):
        """Initialize database integration"""
        self.session = session
        logger.info("🔧 Initialized TRON database integration")
    
    def save_transaction(self, address: str, tx_data: Dict[str, Any], tx_datetime: datetime) -> bool:
        """Save a TRON transaction to the database"""
        try:
            tx_hash = tx_data.get('txID', '')
            amount = tx_data.get('amount', 0)
            fee = tx_data.get('fee', 0)
            block_number = tx_data.get('block', 0)
            confirmed = tx_data.get('confirmed', False)
            
            # Determine transaction type based on amount
            if amount > 0:
                tx_type = TransactionType.INCOMING
            elif amount < 0:
                tx_type = TransactionType.OUTGOING
            else:
                tx_type = TransactionType.TRANSFER
            
            # Determine transaction status
            if confirmed:
                status = TransactionStatus.CONFIRMED
            else:
                status = TransactionStatus.PENDING
            
            # Check if transaction already exists
            existing_tx = self.session.query(Transaction).filter_by(
                tx_hash=tx_hash,
                address=address
            ).first()
            
            if existing_tx:
                logger.info(f"📝 Transaction already exists: {tx_hash[:20]}...")
                return True
            
            # Create new transaction record
            new_transaction = Transaction(
                address=address,
                tx_hash=tx_hash,
                amount=abs(amount),  # Store absolute value
                tx_type=tx_type,
                status=status,
                timestamp=tx_datetime,
                provider=PaymentProvider.CRYPTO,
                block_number=block_number,
                fee=fee,
                currency='TRX'
            )
            
            self.session.add(new_transaction)
            self.session.commit()
            
            logger.info(f"💾 Saved transaction: {tx_hash[:20]}... | "
                       f"Type: {tx_type.value} | Amount: {amount} TRX")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error saving transaction to database: {e}")
            self.session.rollback()
            return False
    
    def save_trc20_transaction(self, address: str, tx_data: Dict[str, Any], tx_datetime: datetime) -> bool:
        """Save a TRC20 token transaction to the database"""
        try:
            tx_hash = tx_data.get('transaction_id', '')
            token_name = tx_data.get('token_info', {}).get('token_name', 'Unknown')
            token_symbol = tx_data.get('token_info', {}).get('token_abbr', 'Unknown')
            amount = tx_data.get('value', 0)
            decimals = tx_data.get('token_info', {}).get('decimals', 18)
            
            # Convert amount based on decimals
            actual_amount = amount / (10 ** decimals)
            
            # Determine transaction type
            if amount > 0:
                tx_type = TransactionType.INCOMING
            else:
                tx_type = TransactionType.OUTGOING
            
            # Check if transaction already exists
            existing_tx = self.session.query(Transaction).filter_by(
                tx_hash=tx_hash,
                address=address
            ).first()
            
            if existing_tx:
                logger.info(f"📝 TRC20 transaction already exists: {tx_hash[:20]}...")
                return True
            
            # Create new transaction record
            new_transaction = Transaction(
                address=address,
                tx_hash=tx_hash,
                amount=abs(actual_amount),
                tx_type=tx_type,
                status=TransactionStatus.CONFIRMED,  # TRC20 transactions are usually confirmed
                timestamp=tx_datetime,
                provider=PaymentProvider.CRYPTO,
                currency=f"{token_symbol} ({token_name})"
            )
            
            self.session.add(new_transaction)
            self.session.commit()
            
            logger.info(f"💾 Saved TRC20 transaction: {tx_hash[:20]}... | "
                       f"Token: {token_symbol} | Amount: {actual_amount}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error saving TRC20 transaction to database: {e}")
            self.session.rollback()
            return False
    
    def get_address_transactions(self, address: str, limit: int = 50) -> list:
        """Get transactions for a specific address"""
        try:
            transactions = self.session.query(Transaction).filter_by(
                address=address
            ).order_by(Transaction.timestamp.desc()).limit(limit).all()
            
            return transactions
            
        except Exception as e:
            logger.error(f"❌ Error getting transactions for {address}: {e}")
            return []
    
    def get_pending_transactions(self) -> list:
        """Get all pending transactions"""
        try:
            pending_txs = self.session.query(Transaction).filter_by(
                status=TransactionStatus.PENDING
            ).all()
            
            return pending_txs
            
        except Exception as e:
            logger.error(f"❌ Error getting pending transactions: {e}")
            return []
    
    def update_transaction_status(self, tx_hash: str, status: TransactionStatus) -> bool:
        """Update transaction status"""
        try:
            transaction = self.session.query(Transaction).filter_by(tx_hash=tx_hash).first()
            
            if transaction:
                transaction.status = status
                self.session.commit()
                logger.info(f"✅ Updated transaction {tx_hash[:20]}... status to {status.value}")
                return True
            else:
                logger.warning(f"⚠️  Transaction not found: {tx_hash}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error updating transaction status: {e}")
            self.session.rollback()
            return False
    
    def get_transaction_statistics(self, address: str = None) -> Dict[str, Any]:
        """Get transaction statistics"""
        try:
            query = self.session.query(Transaction)
            
            if address:
                query = query.filter_by(address=address)
            
            total_transactions = query.count()
            confirmed_transactions = query.filter_by(status=TransactionStatus.CONFIRMED).count()
            pending_transactions = query.filter_by(status=TransactionStatus.PENDING).count()
            
            # Get total amounts
            incoming_amount = query.filter_by(tx_type=TransactionType.INCOMING).with_entities(
                Transaction.amount
            ).all()
            outgoing_amount = query.filter_by(tx_type=TransactionType.OUTGOING).with_entities(
                Transaction.amount
            ).all()
            
            total_incoming = sum(tx.amount for tx in incoming_amount)
            total_outgoing = sum(tx.amount for tx in outgoing_amount)
            
            return {
                'total_transactions': total_transactions,
                'confirmed_transactions': confirmed_transactions,
                'pending_transactions': pending_transactions,
                'total_incoming': total_incoming,
                'total_outgoing': total_outgoing,
                'net_amount': total_incoming - total_outgoing
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting transaction statistics: {e}")
            return {}
    
    def cleanup_old_transactions(self, days: int = 90) -> int:
        """Clean up old transactions (older than specified days)"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            old_transactions = self.session.query(Transaction).filter(
                Transaction.timestamp < cutoff_date
            ).all()
            
            count = len(old_transactions)
            
            for tx in old_transactions:
                self.session.delete(tx)
            
            self.session.commit()
            
            logger.info(f"🧹 Cleaned up {count} old transactions (older than {days} days)")
            return count
            
        except Exception as e:
            logger.error(f"❌ Error cleaning up old transactions: {e}")
            self.session.rollback()
            return 0


# Integration with the polling system
def create_database_integration() -> TronDatabaseIntegration:
    """Create database integration instance"""
    return TronDatabaseIntegration()


def main():
    """Test the database integration"""
    print("🔧 TRON Database Integration Test")
    print("=" * 50)
    
    # Create database integration
    db_integration = create_database_integration()
    
    # Test transaction saving
    test_tx_data = {
        'txID': 'test_transaction_hash_123456789',
        'amount': 1000,
        'fee': 1,
        'block': 12345,
        'confirmed': True,
        'type': 'Transfer'
    }
    
    test_datetime = datetime.now()
    
    # Save test transaction
    success = db_integration.save_transaction(
        address="TJRabPrwbZy45sbavfcjinPJC18kjpRTv8",
        tx_data=test_tx_data,
        tx_datetime=test_datetime
    )
    
    if success:
        print("✅ Test transaction saved successfully")
        
        # Get statistics
        stats = db_integration.get_transaction_statistics()
        print(f"📊 Transaction statistics: {stats}")
    else:
        print("❌ Failed to save test transaction")
    
    print("✅ Database integration test complete")


if __name__ == "__main__":
    main() 