import logging
from typing import Dict, Optional, Tuple
from decimal import Decimal, ROUND_DOWN
from sqlalchemy.orm import Session
from db.wallet import Transaction, Account, Swap, TransactionType, TransactionStatus, AccountType
from reserve_service import ReserveService
import requests
import time

logger = logging.getLogger(__name__)

class SwapService:
    """
    Service for handling crypto-to-crypto swaps with real-time pricing
    """
    
    def __init__(self, session: Session):
        self.session = session
        self.price_cache = {}
        self.price_cache_ttl = 30  # 30 seconds cache
        self.reserve_service = ReserveService(session)
        
    def get_exchange_rate(self, from_currency: str, to_currency: str) -> Tuple[float, float]:
        """
        Get real-time exchange rate from CoinGecko API
        Returns: (rate, price_change_24h)
        """
        cache_key = f"{from_currency.lower()}_{to_currency.lower()}"
        
        # Check cache first
        if cache_key in self.price_cache:
            cache_time, rate, price_change = self.price_cache[cache_key]
            if time.time() - cache_time < self.price_cache_ttl:
                return rate, price_change
        
        try:
            # Use CoinGecko API for real-time rates
            url = f"https://api.coingecko.com/api/v3/simple/price"
            params = {
                "ids": f"{from_currency.lower()},usd",
                "vs_currencies": "usd",
                "include_24hr_change": "true"
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Calculate cross-rate through USD
            from_price_usd = data.get(from_currency.lower(), {}).get("usd", 0)
            to_price_usd = data.get(to_currency.lower(), {}).get("usd", 0)
            
            if from_price_usd and to_price_usd:
                rate = to_price_usd / from_price_usd
                price_change = data.get(to_currency.lower(), {}).get("usd_24h_change", 0)
                
                # Cache the result
                self.price_cache[cache_key] = (time.time(), rate, price_change)
                return rate, price_change
            else:
                raise ValueError(f"Unable to get prices for {from_currency} or {to_currency}")
                
        except Exception as e:
            logger.error(f"Error fetching exchange rate: {e}")
            # Fallback to cached rate or default
            if cache_key in self.price_cache:
                _, rate, price_change = self.price_cache[cache_key]
                return rate, price_change
            raise ValueError(f"Unable to get exchange rate for {from_currency} to {to_currency}")
    
    def calculate_swap_amounts(
        self, 
        from_currency: str, 
        to_currency: str, 
        from_amount: float,
        slippage_tolerance: float = 0.01  # 1% default slippage
    ) -> Dict:
        """
        Calculate swap amounts with slippage protection
        """
        try:
            # Get current exchange rate
            rate, price_change = self.get_exchange_rate(from_currency, to_currency)
            
            # Calculate expected output
            expected_output = from_amount * rate
            
            # Apply slippage tolerance
            min_output = expected_output * (1 - slippage_tolerance)
            max_output = expected_output * (1 + slippage_tolerance)
            
            # Calculate fees (0.3% swap fee)
            swap_fee_rate = 0.003
            swap_fee = from_amount * swap_fee_rate
            net_from_amount = from_amount - swap_fee
            
            # Final calculation
            final_output = net_from_amount * rate
            
            return {
                "from_amount": from_amount,
                "to_amount": final_output,
                "rate": rate,
                "swap_fee": swap_fee,
                "slippage_tolerance": slippage_tolerance,
                "min_output": min_output,
                "max_output": max_output,
                "price_change_24h": price_change,
                "estimated_usd_value": from_amount * self._get_usd_price(from_currency)
            }
            
        except Exception as e:
            logger.error(f"Error calculating swap amounts: {e}")
            raise
    
    def execute_swap(
        self,
        user_id: int,
        from_currency: str,
        to_currency: str,
        from_amount: float,
        reference_id: str,
        slippage_tolerance: float = 0.01
    ) -> Dict:
        """
        Execute a crypto-to-crypto swap with reserve management
        """
        try:
            # Validate currencies
            if from_currency == to_currency:
                raise ValueError("Cannot swap the same currency")
            
            # Get user accounts
            from_account = self._get_user_account(user_id, from_currency)
            to_account = self._get_user_account(user_id, to_currency)
            
            if not from_account or not to_account:
                raise ValueError("One or both accounts not found")
            
            # Check sufficient balance
            if from_account.available_balance() < from_amount:
                raise ValueError(f"Insufficient {from_currency} balance")
            
            # Calculate swap amounts
            swap_calculation = self.calculate_swap_amounts(
                from_currency, to_currency, from_amount, slippage_tolerance
            )
            
            # Check idempotency
            existing_swap = self._get_existing_swap_by_reference(reference_id)
            if existing_swap:
                logger.info(f"Swap idempotency: Found existing swap with reference_id {reference_id}")
                return self._build_idempotent_swap_response(existing_swap, swap_calculation)
            
            # Check and reserve from currency in system reserve
            from_reserve_check = self.reserve_service.check_reserve_sufficiency(
                from_currency, from_amount, AccountType.CRYPTO, "swap"
            )
            
            if not from_reserve_check["is_sufficient"]:
                return {
                    "success": False,
                    "error": f"Insufficient system reserve for {from_currency}. Required: {from_reserve_check['required_amount']}, Available: {from_reserve_check['available_amount']}",
                    "reserve_status": from_reserve_check
                }
            
            # Check and reserve to currency in system reserve
            to_reserve_check = self.reserve_service.check_reserve_sufficiency(
                to_currency, swap_calculation["to_amount"], AccountType.CRYPTO, "swap"
            )
            
            if not to_reserve_check["is_sufficient"]:
                return {
                    "success": False,
                    "error": f"Insufficient system reserve for {to_currency}. Required: {to_reserve_check['required_amount']}, Available: {to_reserve_check['available_amount']}",
                    "reserve_status": to_reserve_check
                }
            
            # Reserve amounts from system reserves
            from_reserve_result = self.reserve_service.reserve_amount(
                from_currency, from_amount, AccountType.CRYPTO, f"{reference_id}_from", "swap"
            )
            
            if not from_reserve_result["success"]:
                return {
                    "success": False,
                    "error": f"Failed to reserve {from_currency} from system reserve: {from_reserve_result['error']}"
                }
            
            to_reserve_result = self.reserve_service.reserve_amount(
                to_currency, swap_calculation["to_amount"], AccountType.CRYPTO, f"{reference_id}_to", "swap"
            )
            
            if not to_reserve_result["success"]:
                # Release the first reservation
                self.reserve_service.release_reserve(from_currency, from_amount, AccountType.CRYPTO, f"{reference_id}_from")
                return {
                    "success": False,
                    "error": f"Failed to reserve {to_currency} from system reserve: {to_reserve_result['error']}"
                }
            
            try:
                # Create swap record
                swap = Swap(
                    user_id=user_id,
                    from_account_id=from_account.id,
                    to_account_id=to_account.id,
                    from_amount=swap_calculation["from_amount"],
                    to_amount=swap_calculation["to_amount"],
                    rate=swap_calculation["rate"],
                    fee_amount=swap_calculation["swap_fee"],
                    status="pending"
                )
                
                self.session.add(swap)
                self.session.flush()  # Get the swap ID
                
                # Create transactions
                from_transaction = Transaction(
                    account_id=from_account.id,
                    reference_id=reference_id,
                    amount=swap_calculation["from_amount"],
                    type=TransactionType.SWAP,
                    status=TransactionStatus.PENDING,
                    description=f"Swap {from_currency} to {to_currency}",
                    metadata_json={
                        "swap_id": swap.id,
                        "to_currency": to_currency,
                        "rate": swap_calculation["rate"],
                        "swap_fee": swap_calculation["swap_fee"],
                        "reserve_references": {
                            "from": f"{reference_id}_from",
                            "to": f"{reference_id}_to"
                        }
                    }
                )
                
                to_transaction = Transaction(
                    account_id=to_account.id,
                    reference_id=reference_id,
                    amount=swap_calculation["to_amount"],
                    type=TransactionType.SWAP,
                    status=TransactionStatus.PENDING,
                    description=f"Swap {from_currency} to {to_currency}",
                    metadata_json={
                        "swap_id": swap.id,
                        "from_currency": from_currency,
                        "rate": swap_calculation["rate"],
                        "swap_fee": swap_calculation["swap_fee"],
                        "reserve_references": {
                            "from": f"{reference_id}_from",
                            "to": f"{reference_id}_to"
                        }
                    }
                )
                
                self.session.add(from_transaction)
                self.session.add(to_transaction)
                self.session.flush()
                
                # Update swap with transaction IDs
                swap.transaction_id = from_transaction.id
                
                # Update account balances
                self._update_account_balances(
                    from_account, to_account, 
                    swap_calculation["from_amount"], 
                    swap_calculation["to_amount"],
                    from_currency, to_currency
                )
                
                # Mark transactions as completed
                from_transaction.status = TransactionStatus.COMPLETED
                to_transaction.status = TransactionStatus.COMPLETED
                swap.status = "completed"
                
                # Commit all changes
                self.session.commit()
                
                logger.info(f"Swap completed: {from_amount} {from_currency} to {swap_calculation['to_amount']} {to_currency}")
                
                return {
                    "success": True,
                    "swap_id": swap.id,
                    "reference_id": reference_id,
                    "from_currency": from_currency,
                    "to_currency": to_currency,
                    "from_amount": swap_calculation["from_amount"],
                    "to_amount": swap_calculation["to_amount"],
                    "rate": swap_calculation["rate"],
                    "swap_fee": swap_calculation["swap_fee"],
                    "status": "completed",
                    "transaction_ids": [from_transaction.id, to_transaction.id],
                    "reserve_status": {
                        "from_currency": from_reserve_result,
                        "to_currency": to_reserve_result
                    }
                }
                
            except Exception as e:
                # Release both reservations on error
                self.reserve_service.release_reserve(from_currency, from_amount, AccountType.CRYPTO, f"{reference_id}_from")
                self.reserve_service.release_reserve(to_currency, swap_calculation["to_amount"], AccountType.CRYPTO, f"{reference_id}_to")
                raise
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error executing swap: {e}")
            raise
    
    def _get_user_account(self, user_id: int, currency: str) -> Optional[Account]:
        """Get user account for specific currency"""
        return self.session.query(Account).filter(
            Account.user_id == user_id,
            Account.currency == currency.upper()
        ).first()
    
    def _get_existing_swap_by_reference(self, reference_id: str) -> Optional[Swap]:
        """Check if a swap with the given reference_id already exists"""
        return self.session.query(Swap).filter(
            Swap.transaction_id.has(Transaction.reference_id == reference_id)
        ).first()
    
    def _build_idempotent_swap_response(self, existing_swap: Swap, swap_calculation: Dict) -> Dict:
        """Build response for idempotent swap request"""
        return {
            "success": True,
            "swap_id": existing_swap.id,
            "reference_id": existing_swap.transaction_id,
            "from_currency": existing_swap.from_account.currency,
            "to_currency": existing_swap.to_account.currency,
            "from_amount": float(existing_swap.from_amount),
            "to_amount": float(existing_swap.to_amount),
            "rate": existing_swap.rate,
            "swap_fee": float(existing_swap.fee_amount) if existing_swap.fee_amount else 0,
            "status": "idempotent",
            "message": "Swap already processed with this reference_id"
        }
    
    def _update_account_balances(
        self, 
        from_account: Account, 
        to_account: Account,
        from_amount: float,
        to_amount: float,
        from_currency: str,
        to_currency: str
    ):
        """Update account balances after swap"""
        if from_account.account_type == AccountType.CRYPTO:
            # Update crypto balance in smallest units
            from_smallest_unit = self._convert_to_smallest_unit(from_amount, from_currency)
            from_account.crypto_balance_smallest_unit -= from_smallest_unit
        else:
            from_account.balance -= from_amount
            
        if to_account.account_type == AccountType.CRYPTO:
            # Update crypto balance in smallest units
            to_smallest_unit = self._convert_to_smallest_unit(to_amount, to_currency)
            to_account.crypto_balance_smallest_unit += to_smallest_unit
        else:
            to_account.balance += to_amount
    
    def _get_usd_price(self, currency: str) -> float:
        """Get USD price for a currency"""
        try:
            rate, _ = self.get_exchange_rate(currency, "USD")
            return rate
        except:
            return 0.0
    
    def _convert_to_smallest_unit(self, amount: float, currency: str) -> int:
        """Convert amount to smallest unit (wei, satoshis, etc.)"""
        precision_map = {
            "BTC": 8,   # satoshis
            "ETH": 18,  # wei
            "USDC": 6,  # 6 decimals
            "USDT": 6,  # 6 decimals
            "SOL": 9,   # lamports
        }
        
        precision = precision_map.get(currency.upper(), 8)
        return int(amount * (10 ** precision))
    
    def get_swap_history(self, user_id: int, limit: int = 50) -> list:
        """Get user's swap history"""
        swaps = self.session.query(Swap).filter(
            Swap.user_id == user_id
        ).order_by(Swap.created_at.desc()).limit(limit).all()
        
        return [
            {
                "id": swap.id,
                "from_currency": swap.from_account.currency,
                "to_currency": swap.to_account.currency,
                "from_amount": float(swap.from_amount),
                "to_amount": float(swap.to_amount),
                "rate": swap.rate,
                "fee_amount": float(swap.fee_amount) if swap.fee_amount else 0,
                "status": swap.status,
                "created_at": swap.created_at.isoformat() if swap.created_at else None
            }
            for swap in swaps
        ]
