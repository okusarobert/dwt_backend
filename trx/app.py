#!/usr/bin/env python3
"""
Tron (TRX) Deposit and Confirmation Monitor
- Polls TronGrid for transactions to monitored addresses
- Saves incoming deposits and tracks confirmations
- Tracks confirmations for TRX withdrawals created by wallet API
"""

import os
import time
import logging
from dataclasses import dataclass
from typing import Dict, Optional, List, Tuple
from decimal import Decimal

from decouple import config
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func

from shared.logger import setup_logging
from db.connection import get_session
from db.wallet import CryptoAddress, Transaction, Account, AccountType, PaymentProvider, TransactionType, TransactionStatus, Reservation, ReservationType
from shared.currency_precision import AmountConverter
from shared.trading_accounting import TradingAccountingService
from db.accounting import JournalEntry, LedgerTransaction, AccountingAccount
from shared.crypto.clients.tron import TronWallet, TronWalletConfig
from tronpy import tron as tron_utils
# tron_utils.to_base58check_address(bytes.fromhex(hex_str))

logger = setup_logging()


@dataclass
class TrxTx:
    tx_hash: str
    from_address: str
    to_address: str
    value_trx: Decimal
    block_number: int


class TronMonitor:
    def __init__(self):
        api_key = config('TRON_API_KEY', default=None)
        network = config('TRX_NETWORK', default='testnet')
        if not api_key:
            raise ValueError("TRON_API_KEY is required")
        self.cfg = TronWalletConfig.testnet(api_key) if network != 'mainnet' else TronWalletConfig.mainnet(api_key)
        # Dummy user 0; wallet methods that need user_id won't be used except helpers
        session = get_session()
        self.client = TronWallet(user_id=0, tron_config=self.cfg, session=session, logger=logger)
        self.poll_secs = int(os.getenv('TRX_POLL_SECS', '20'))
        self.required_confirmations = int(os.getenv('TRX_REQUIRED_CONFIRMATIONS', '20'))
        # Comma-separated list of TRC20 USDT contract addresses to track (base58)
        usdt_env = os.getenv('TRX_TRC20_USDT_CONTRACTS', '')
        self.usdt_contracts = [addr.strip() for addr in usdt_env.split(',') if addr.strip()]

    def load_monitored_addresses(self) -> List[str]:
        session = get_session()
        try:
            addrs = session.query(CryptoAddress).filter_by(currency_code="TRX", is_active=True).all()
            return [a.address for a in addrs]
        finally:
            session.close()

    def parse_tx(self, raw: Dict) -> Optional[TrxTx]:
        try:
            tx_hash = raw.get('txID') or raw.get('txid') or raw.get('hash') or raw.get('transaction_id')
            if not tx_hash:
                return None

            from_addr = raw.get('from') or raw.get('ownerAddress') or raw.get('owner_address')
            to_addr = raw.get('to') or raw.get('toAddress') or raw.get('to_address')
            amount_sun = raw.get('amount') or raw.get('value')
            block_number = raw.get('blockNumber') or raw.get('block') or 0

            # Try raw_data.contract path
            if not (from_addr and to_addr and amount_sun):
                rd = raw.get('raw_data') or {}
                contracts = rd.get('contract') or []
                if contracts:
                    c0 = contracts[0]
                    pv = ((c0.get('parameter') or {}).get('value') or {})
                    from_addr = from_addr or pv.get('owner_address') or pv.get('from')
                    to_addr = to_addr or pv.get('to_address') or pv.get('to')
                    amount_sun = amount_sun or pv.get('amount')
                if not block_number:
                    header = raw.get('block_header') or {}
                    rd2 = header.get('raw_data') or {}
                    block_number = rd2.get('number', 0)

            # Some APIs return base58 addresses already (starting with T). If hex, we won't convert here.
            if not (to_addr and amount_sun is not None):
                return None

            # Normalize addresses to base58 (convert 41-hex to base58 if needed)
            try:
                from shared.crypto.clients.tron import TronWallet as _TW
                from_addr_norm = TronWallet._to_base58_address(from_addr)
                to_addr_norm = TronWallet._to_base58_address(to_addr)
            except Exception as e:
                logger.error(f"Failed to normalize addresses: {from_addr} {to_addr} : {e!r}")
                from_addr_norm = from_addr
                to_addr_norm = to_addr

            value_trx = AmountConverter.from_smallest_units(int(amount_sun), "TRX")
            return TrxTx(
                tx_hash=str(tx_hash),
                from_address=str(from_addr_norm) if from_addr_norm else "",
                to_address=str(to_addr_norm),
                value_trx=value_trx,
                block_number=int(block_number or 0),
            )
        except Exception as e:
            logger.error("Failed to parse TRX tx: %s", e)
            return None

    def fetch_recent_for(self, address: str, limit: int = 20) -> List[TrxTx]:
        try:
            raws = self.client.get_transactions_by_address(address, limit=limit) or []
            # Normalize comparison address to base58 just in case
            try:
                addr_b58 = TronWallet._to_base58_address(address)
            except Exception:
                addr_b58 = address
            txs: List[TrxTx] = []
            if address == addr_b58:
                logger.info(f"Address: {address} base58: {addr_b58} are the same")
            for raw in raws:
                tx: Optional[TrxTx] = None
                # If client returned normalized dicts: {txid, from, to, value(sun), blockNumber}
                if isinstance(raw, dict) and all(k in raw for k in ("txid", "to", "value")):
                    try:
                        to_b58 = TronWallet._to_base58_address(raw.get("to"))
                        from_b58 = TronWallet._to_base58_address(raw.get("from")) or ""
                        logger.info(f"TX info from inside: {to_b58} {from_b58}")
                        value_sun = int(raw.get("value") or 0)
                        block_num = int(raw.get("blockNumber") or 0)
                        value_trx = AmountConverter.from_smallest_units(value_sun, "TRX")
                        tx = TrxTx(
                            tx_hash=str(raw.get("txid")),
                            from_address=str(from_b58),
                            to_address=str(to_b58),
                            value_trx=value_trx,
                            block_number=block_num,
                        )
                        logger.info(f"TX info from inside: {tx}")
                    except Exception as e:
                        logger.error("Failed to build normalized TRX tx: %s", e)
                        tx = None
                else:
                    # Fallback: parse raw TronGrid/fullnode shape
                    tx = self.parse_tx(raw)

                if tx and tx.to_address == addr_b58:
                    txs.append(tx)
            logger.info(f"TRX txs for {address}: {txs}")
            return txs
        except Exception as e:
            logger.error("Error fetching TRX txs for %s: %s", address, e)
            return []

    def _address_record(self, address: str) -> Optional[CryptoAddress]:
        session = get_session()
        try:
            return session.query(CryptoAddress).filter(
                CryptoAddress.address == address,
                CryptoAddress.currency_code == "TRX",
                CryptoAddress.is_active == True
            ).first()
        except Exception as e:
            logger.error("DB error fetching address %s: %s", address, e)
            return None
        finally:
            session.close()

    def _get_parent_trx_account_by_address(self, address: str) -> Optional[Account]:
        """Resolve the TRX parent Account using the on-chain address."""
        session = get_session()
        try:
            return (
                session.query(Account)
                .join(CryptoAddress, CryptoAddress.account_id == Account.id)
                .filter(
                    CryptoAddress.address == address,
                    CryptoAddress.currency_code == "TRX",
                    CryptoAddress.is_active == True,
                )
                .first()
            )
        except Exception as e:
            logger.error("DB error resolving parent account for %s: %s", address, e)
            return None
        finally:
            session.close()

    def _is_tx_recorded(self, tx_hash: str, address: str, tx_type: TransactionType) -> bool:
        session = get_session()
        try:
            existing = session.query(Transaction).filter_by(
                blockchain_txid=tx_hash,
                address=address,
                type=tx_type
            ).first()
            return existing is not None
        finally:
            session.close()

    def _create_reservation(self, account_id: int, amount_sun: int, tx_hash: str):
        session = get_session()
        try:
            account = session.query(Account).filter_by(id=account_id).first()
            if not account:
                raise ValueError(f"Account {account_id} not found")
            current_locked = account.crypto_locked_amount_smallest_unit or 0
            account.crypto_locked_amount_smallest_unit = current_locked + amount_sun
            ref = f"trx_monitor_{int(time.time()*1000)}_{tx_hash[:8]}"
            reservation = Reservation(
                user_id=account.user_id,
                reference=ref,
                amount=float(AmountConverter.from_smallest_units(amount_sun, "TRX")),
                type=ReservationType.RESERVE,
                status="active"
            )
            session.add(reservation)
            session.commit()
            return ref
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def _record_incoming(self, tx: TrxTx, addr: CryptoAddress):
        # Already recorded?
        if self._is_tx_recorded(tx.tx_hash, addr.address, TransactionType.DEPOSIT):
            logger.info("⏭️ TRX deposit already recorded: %s", tx.tx_hash)
            return

        amount_sun = AmountConverter.to_smallest_units(tx.value_trx, "TRX")
        # Create reservation and transaction
        res_ref = self._create_reservation(addr.account_id, amount_sun, tx.tx_hash)
        
        session = get_session()
        try:
            t = Transaction(
                account_id=addr.account_id,
                reference_id=tx.tx_hash,
                amount=float(tx.value_trx),
                amount_smallest_unit=amount_sun,
                type=TransactionType.DEPOSIT,
                status=TransactionStatus.AWAITING_CONFIRMATION,
                description=f"Tron transaction {tx.tx_hash[:8]}...",
                blockchain_txid=tx.tx_hash,
                confirmations=0,
                required_confirmations=self.required_confirmations,
                address=addr.address,
                provider=PaymentProvider.CRYPTO,
                metadata_json={
                    "from_address": tx.from_address,
                    "to_address": tx.to_address,
                    "block_number": tx.block_number,
                    "amount_sun": str(amount_sun),
                    "amount_trx": str(tx.value_trx),
                    "currency": "TRX",
                    "unified_system": True,
                    "reservation_reference": res_ref,
                }
            )
            session.add(t)
            
            # Create accounting journal entry
            try:
                accounting_service = TradingAccountingService(session)
                self._create_accounting_entry(t, tx, addr, accounting_service, False)  # False = deposit
            except Exception as e:
                logger.error(f"⚠️ Failed to create TRX accounting entry: {e}")
            
            session.commit()
            logger.info("💾 Recorded TRX deposit with unified system %s -> %s: %s", tx.from_address, tx.to_address, AmountConverter.format_display_amount(amount_sun, "TRX"))
        except Exception as e:
            session.rollback()
            # Ignore duplicate unique constraint errors
            logger.error("DB error saving TRX deposit: %s", e)
        finally:
            session.close()

    def _create_accounting_entry(self, transaction: Transaction, tx: TrxTx, crypto_address: CryptoAddress, accounting_service: TradingAccountingService, is_withdrawal: bool):
        """Create accounting journal entry for the TRX transaction"""
        try:
            # Get or create crypto asset account
            crypto_account_name = f"Crypto Assets - TRX"
            crypto_account = accounting_service.get_account_by_name(crypto_account_name)
            
            if not crypto_account:
                logger.warning(f"⚠️ Crypto asset account not found: {crypto_account_name}")
                return
            
            # Create journal entry description
            direction = "withdrawal" if is_withdrawal else "deposit"
            amount_display = AmountConverter.format_display_amount(transaction.amount_smallest_unit, "TRX")
            description = f"TRX {direction} - {amount_display} (TX: {tx.tx_hash[:8]}...)"
            
            # Create journal entry
            journal_entry = JournalEntry(description=description)
            session = get_session()
            session.add(journal_entry)
            session.flush()  # Get ID
            
            # Create ledger transactions based on direction
            if is_withdrawal:
                # Debit: Pending settlements (liability), Credit: Crypto assets
                pending_account = accounting_service.get_account_by_name("Pending Trade Settlements")
                if pending_account:
                    # Debit pending settlements
                    debit_tx = LedgerTransaction(
                        journal_entry_id=journal_entry.id,
                        account_id=pending_account.id,
                        debit_smallest_unit=transaction.amount_smallest_unit,
                        credit_smallest_unit=0
                    )
                    session.add(debit_tx)
                    
                    # Credit crypto assets
                    credit_tx = LedgerTransaction(
                        journal_entry_id=journal_entry.id,
                        account_id=crypto_account.id,
                        debit_smallest_unit=0,
                        credit_smallest_unit=transaction.amount_smallest_unit
                    )
                    session.add(credit_tx)
            else:
                # Deposit: Debit crypto assets, Credit pending settlements
                pending_account = accounting_service.get_account_by_name("Pending Trade Settlements")
                if pending_account:
                    # Debit crypto assets
                    debit_tx = LedgerTransaction(
                        journal_entry_id=journal_entry.id,
                        account_id=crypto_account.id,
                        debit_smallest_unit=transaction.amount_smallest_unit,
                        credit_smallest_unit=0
                    )
                    session.add(debit_tx)
                    
                    # Credit pending settlements
                    credit_tx = LedgerTransaction(
                        journal_entry_id=journal_entry.id,
                        account_id=pending_account.id,
                        debit_smallest_unit=0,
                        credit_smallest_unit=transaction.amount_smallest_unit
                    )
                    session.add(credit_tx)
            
            # Link transaction to journal entry
            transaction.journal_entry_id = journal_entry.id
            
            logger.info(f"📊 Created TRX accounting entry: {description}")
            session.close()
            
        except Exception as e:
            logger.error(f"❌ Error creating TRX accounting entry: {e}")
            raise

    def fetch_trc20_for(self, address: str, limit: int = 20) -> List[Dict]:
        """Fetch normalized TRC-20 transfers to the address, optionally filtered by configured contracts."""
        try:
            return self.client.get_trc20_transactions_by_address(
                address, limit=limit, only_to=True, contract_addresses=self.usdt_contracts or None
            ) or []
        except Exception as e:
            logger.error("Error fetching TRC20 txs for %s: %s", address, e)
            return []

    def _get_token_account_for_user(self, user_id: int, token_symbol: str) -> Optional[Account]:
        """
        Find user's token Account with symbol (e.g., USDT) and parent_currency == 'TRX'.
        Falls back to None if not found.
        """
        session = get_session()
        try:
            accounts = (
                session.query(Account)
                .filter(
                    Account.user_id == user_id,
                    Account.account_type == AccountType.CRYPTO,
                    Account.currency == token_symbol.upper(),
                )
                .all()
            )
            for acc in accounts:
                cfg = acc.precision_config or {}
                if str(cfg.get("parent_currency", "")).upper() == "TRX":
                    return acc
            return None
        except Exception as e:
            logger.error("Error fetching token account for user %s %s: %s", user_id, token_symbol, e)
            return None
        finally:
            session.close()

    def _is_token_tx_recorded(self, tx_hash: str, address: str) -> bool:
        session = get_session()
        try:
            existing = session.query(Transaction).filter_by(
                blockchain_txid=tx_hash,
                address=address,
                type=TransactionType.DEPOSIT,
            ).first()
            return existing is not None
        finally:
            session.close()

    def _record_trc20_incoming(self, item: Dict, recipient_addr: str, parent_trx_account: Account):
        """Record a TRC-20 incoming transfer to the appropriate token account."""
        session = get_session()
        try:
            txid = item.get("txid") or item.get("transaction_id")
            to_addr = item.get("to")
            from_addr = item.get("from") or ""
            token_symbol = (item.get("token_symbol") or "").upper()
            token_address = item.get("token_address")
            decimals = int(item.get("decimals", 0))
            value_smallest = int(item.get("value_smallest") or item.get("value") or 0)
            block_ts = int(item.get("block_timestamp") or 0)

            if not (txid and to_addr and token_symbol):
                return

            # Avoid duplicates
            if self._is_token_tx_recorded(txid, to_addr):
                logger.info("⏭️ TRC20 deposit already recorded: %s", txid)
                return

            # Resolve token account for the same user on TRX
            token_account = self._get_token_account_for_user(parent_trx_account.user_id, token_symbol)
            if not token_account:
                logger.warning("No %s token account for user %s (TRX parent). Skipping.", token_symbol, parent_trx_account.user_id)
                return

            # Align decimals with the token account precision to avoid wrong standard amounts
            acc_cfg = token_account.precision_config or {}
            decimals_to_use = int(acc_cfg.get("decimals", decimals or 6) or 6)

            # Lock on token account (store in smallest units). Column is NUMERIC(78,0) so very large values are allowed.
            current_locked = token_account.crypto_locked_amount_smallest_unit or 0
            token_account.crypto_locked_amount_smallest_unit = current_locked + value_smallest

            # Create reservation
            ref = f"trx_trc20_{int(time.time()*1000)}_{txid[:8]}"
            reservation = Reservation(
                user_id=token_account.user_id,
                reference=ref,
                amount=float(value_smallest / (10 ** (decimals or 6))),
                type=ReservationType.RESERVE,
                status="active",
            )
            session.add(reservation)

            # Create transaction record
            # Compute standard amount precisely and clamp to fit transactions.amount Numeric(15,2)
            from decimal import Decimal, ROUND_DOWN
            standard_amount_dec = (Decimal(value_smallest) / (Decimal(10) ** Decimal(decimals_to_use))) if value_smallest else Decimal(0)
            max_amount_dec = Decimal('999999999999999.99')
            amount_for_column = standard_amount_dec if standard_amount_dec <= max_amount_dec else max_amount_dec
            if amount_for_column != standard_amount_dec:
                logger.warning("Clamped TRC20 %s amount for tx %s to %s to fit Numeric(15,2)", token_symbol, txid, amount_for_column)
            t = Transaction(
                account_id=token_account.id,
                reference_id=txid,
                amount=float(amount_for_column.quantize(Decimal('0.01'), rounding=ROUND_DOWN)),
                amount_smallest_unit=value_smallest,
                precision_config={
                    "currency": token_symbol,
                    "decimals": decimals_to_use,
                    "smallest_unit": "units",
                    "parent_currency": "TRX",
                },
                type=TransactionType.DEPOSIT,
                status=TransactionStatus.AWAITING_CONFIRMATION,
                description=f"TRC20 {token_symbol} transfer {txid[:8]}...",
                blockchain_txid=txid,
                confirmations=0,
                required_confirmations=self.required_confirmations,
                address=to_addr,
                provider=PaymentProvider.CRYPTO,
                metadata_json={
                    "from_address": from_addr,
                    "to_address": to_addr,
                    "token_symbol": token_symbol,
                    "token_address": token_address,
                    "decimals": decimals,
                    "value_smallest": str(value_smallest),
                    "block_timestamp": block_ts,
                    "reservation_reference": ref,
                },
            )
            session.add(t)
            session.commit()
            logger.info("💾 Recorded TRC20 %s deposit %s -> %s: %s (smallest=%s)", token_symbol, from_addr, to_addr, t.amount, value_smallest)
        except Exception as e:
            session.rollback()
            logger.error("DB error saving TRC20 deposit: %s", e)
        finally:
            session.close()

    def _current_block(self) -> Optional[int]:
        try:
            block_number = self.client.get_latest_block_number()
            logger.info(f"TRX latest block: {block_number}")
            return block_number
        except Exception as e:
            logger.error("Failed to get TRX latest block: %s", e)
            return None

    def _maybe_update_confirmations(self, current_block: int):
        """Update confirmations for TRX and TRC-20 (parent TRX) transactions."""
        session = get_session()
        try:
            # Process TRX native and any token accounts whose parent_currency is TRX
            try:
                # Fetch broadly; filter in Python to avoid dialect-specific JSON operators
                pending = (
                    session.query(Transaction)
                    .join(Account, Transaction.account_id == Account.id)
                    .filter(
                        Transaction.status == TransactionStatus.AWAITING_CONFIRMATION,
                        Transaction.blockchain_txid.isnot(None),
                    )
                    .all()
                )
                logger.info("Fetched %s pending txs for possible TRX/TRC20 confirmations", len(pending))
            except Exception as e:
                logger.error("Error querying pending TRX/TRC20 confirmations: %s", e)
                return
            for t in pending:
                try:
                    # Filter to TRX or token accounts whose parent_currency is TRX
                    acc = session.query(Account).filter_by(id=t.account_id).first()
                    if not acc:
                        continue
                    parent_cur = str((acc.precision_config or {}).get("parent_currency", "")).upper()
                    if not (acc.currency == "TRX" or parent_cur == "TRX"):
                        continue
                    # Ensure we have tx block
                    tx_block = 0
                    if t.metadata_json and 'block_number' in t.metadata_json:
                        try:
                            tx_block = int(t.metadata_json.get('block_number') or 0)
                        except Exception:
                            tx_block = 0
                    if not tx_block:
                        # Fetch tx info to obtain block number
                        info = self.client.get_transaction_info(t.blockchain_txid)
                        tx_block = self.client.extract_block_number_from_tx(info) or 0
                        meta = t.metadata_json or {}
                        meta['block_number'] = tx_block
                        t.metadata_json = meta
                        session.commit()
                    if not tx_block:
                        logger.info("TRX tx %s has no block yet", t.blockchain_txid)
                        continue
                    confirmations = max(0, current_block - tx_block)
                    t.confirmations = confirmations
                    if confirmations >= (t.required_confirmations or self.required_confirmations):
                        self._finalize_confirmed_transaction(t)
                    session.commit()
                except Exception as e:
                    session.rollback()
                    logger.error("Error updating TRX confirmations for %s: %s", t.blockchain_txid, e)
        finally:
            session.close()

    def _finalize_confirmed_transaction(self, t: Transaction):
        session = get_session()
        try:
            account = session.query(Account).filter_by(id=t.account_id).first()
            if not account:
                logger.error("Account %s not found for trx %s", t.account_id, t.blockchain_txid)
                return
            amount_sun = int(t.amount_smallest_unit or 0)
            if t.type == TransactionType.DEPOSIT:
                # Credit balance and release reservation
                account.crypto_balance_smallest_unit = (account.crypto_balance_smallest_unit or 0) + amount_sun
                account.crypto_locked_amount_smallest_unit = max(0, (account.crypto_locked_amount_smallest_unit or 0) - amount_sun)
            elif t.type == TransactionType.WITHDRAWAL:
                # Release reservation only (amount already deducted on send)
                account.crypto_locked_amount_smallest_unit = max(0, (account.crypto_locked_amount_smallest_unit or 0) - amount_sun)
            else:
                # Generic release
                account.crypto_locked_amount_smallest_unit = max(0, (account.crypto_locked_amount_smallest_unit or 0) - amount_sun)

            # Mark transaction completed and add release reservation record
            t.status = TransactionStatus.COMPLETED
            release_ref = f"trx_monitor_release_{int(time.time()*1000)}_{t.blockchain_txid[:8]}"
            # Compute standard amount using account precision (TRX or token with parent TRX)
            try:
                if account.currency == "TRX":
                    amount_std = AmountConverter.from_smallest_units(amount_sun, "TRX")
                else:
                    # For TRC20 tokens, use the token symbol from precision config
                    token_symbol = account.currency or "TRX"
                    try:
                        amount_std = AmountConverter.from_smallest_units(amount_sun, token_symbol)
                    except Exception:
                        # Fallback to manual calculation
                        decimals = int((account.precision_config or {}).get("decimals", 6))
                        amount_std = Decimal(amount_sun) / (Decimal(10) ** Decimal(decimals))
            except Exception:
                # Fallback safe conversion assuming 6 decimals
                amount_std = Decimal(amount_sun) / Decimal(1_000_000)
            release_res = Reservation(
                user_id=account.user_id,
                reference=release_ref,
                amount=float(amount_std),
                type=ReservationType.RELEASE,
                status="completed",
            )
            session.add(release_res)
            session.commit()
            logger.info("✅ TRX tx confirmed %s; type=%s", t.blockchain_txid, t.type)
        except Exception as e:
            session.rollback()
            logger.error("Error finalizing TRX transaction %s: %s", t.blockchain_txid, e)
        finally:
            session.close()

    def run_once(self):
        # Detect deposits
        addresses = self.load_monitored_addresses()
        for addr in addresses:
            try:
                logger.info(f"Detecting transactions for {addr}")
                transactions = self.fetch_recent_for(addr, limit=20)
                logger.info(f"Found {len(transactions)} transactions for {addr}")
                for tx in transactions:
                    addr_row = self._address_record(addr)
                    if not addr_row:
                        continue
                    self._record_incoming(tx, addr_row)
                logger.info(f"Starting to monitor TRC20 tokens")
                parent_account = self._get_parent_trx_account_by_address(addr)
                trc20_transactions = self.fetch_trc20_for(addr, limit=20)
                if parent_account and trc20_transactions:
                    logger.info(f"Found {len(trc20_transactions)} TRC20 transfers for {addr}")
                    for item in trc20_transactions:
                        self._record_trc20_incoming(item, addr, parent_account)
                
            except Exception as e:
                logger.error("Error in TRX deposit detection for %s: %s", addr, e)

        # Update confirmations
        current_block = self._current_block()
        if current_block:
            self._maybe_update_confirmations(current_block)
        # Ensure DB session does not linger and lock tables
        # Session management is now handled by get_session() and close()

    def start(self):
        logger.info("🚀 Starting TRX monitor (poll=%ss, confirmations=%s)", self.poll_secs, self.required_confirmations)
        while True:
            try:
                self.run_once()
            except Exception as e:
                logger.error("TRX monitor iteration error: %s", e)
            time.sleep(self.poll_secs)


def main():
    monitor = TronMonitor()
    monitor.start()


if __name__ == "__main__":
    main()


