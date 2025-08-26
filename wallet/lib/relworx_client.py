import os
import requests
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class RelworxApiClient:
    """
    API client for Relworx Mobile Money and Payment API.
    Configuration is loaded from environment variables:
      - RELWORX_API_KEY
      - RELWORX_BASE_URL
      - RELWORX_ACCOUNT
    """
    def __init__(self):
        self.api_key = os.environ["RELWORX_API_KEY"]
        self.base_url = os.environ.get("RELWORX_BASE_URL", "https://payments.relworx.com/api")
        self.account_no = os.environ["RELWORX_ACCOUNT"]
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/vnd.relworx.v2"
        }

    def validate_msisdn(self, msisdn: str) -> Dict[str, Any]:
        """Validate a mobile number (MSISDN) for mobile money."""
        url = f"{self.base_url}/mobile-money/validate"
        data = {"msisdn": msisdn}
        res = requests.post(url, headers=self.headers, json=data)
        res.raise_for_status()
        return res.json()

    def get_balance(self) -> Dict[str, Any]:
        """Get the wallet balance for the configured account."""
        url = f"{self.base_url}/mobile-money/check-wallet-balance?account_no={self.account_no}&currency=UGX"
        res = requests.get(url, headers=self.headers)
        res.raise_for_status()
        return res.json()

    def check_request_status(self, reference: str) -> Dict[str, Any]:
        """Check the status of a payment request by internal reference."""
        url = f"{self.base_url}/mobile-money/check-request-status?internal_reference={reference}&account_no={self.account_no}"
        res = requests.get(url, headers=self.headers)
        res.raise_for_status()
        return res.json()

    def get_history(self) -> Dict[str, Any]:
        """Get the transaction history for the configured account."""
        url = f"{self.base_url}/payment-requests/transactions?account_no={self.account_no}"
        res = requests.get(url, headers=self.headers)
        res.raise_for_status()
        return res.json()

    def request_payment(self, reference: str, msisdn: str, amount: float, description: str = "Deposit to TOI BETS", currency: str = "UGX") -> Dict[str, Any]:
        """
        Request a mobile money payment from a user.
        Args:
            reference: Unique reference for the payment
            msisdn: Mobile number to request payment from
            amount: Amount to request
            description: Description for the payment
            currency: Currency code (default UGX)
        """
        # Ensure MSISDN starts with + for Relworx API
        if not msisdn.startswith('+'):
            msisdn = f"+{msisdn}"
            
        url = f"{self.base_url}/mobile-money/request-payment"
        data = {
            "account_no": self.account_no,
            "reference": reference,
            "msisdn": msisdn,
            "currency": currency,
            "amount": amount,
            "description": description
        }
        logger.info(f"[Wallet] Relworx request payment data: {data}")
        res = requests.post(url, headers=self.headers, json=data)
        try:
            response_data = res.json()
            logger.info(f"[Wallet] Relworx request payment response: {response_data}")
            res.raise_for_status()
            return response_data
        except requests.exceptions.HTTPError:
            logger.error(f"[Wallet] Relworx request payment failed with status {res.status_code}")
            logger.error(f"[Wallet] Response body: {res.text}")
            raise

    def send_payment(self, reference: str, msisdn: str, amount: float, description: str = "Withdrawal from TOI BETS", currency: str = "UGX") -> Dict[str, Any]:
        """
        Send a mobile money payment to a user (withdrawal).
        Args:
            reference: Unique reference for the payment
            msisdn: Mobile number to send payment to
            amount: Amount to send
            description: Description for the payment (default: 'Withdrawal from TOI BETS')
            currency: Currency code (default UGX)
        """
        # Ensure MSISDN starts with + for Relworx API
        if not msisdn.startswith('+'):
            msisdn = f"+{msisdn}"
            
        url = f"{self.base_url}/mobile-money/send-payment"
        data = {
            "account_no": self.account_no,
            "reference": reference,
            "msisdn": msisdn,
            "currency": currency,
            "amount": amount,
            "description": description
        }
        res = requests.post(url, headers=self.headers, json=data)
        try:
            response_data = res.json()
            logger.info(f"[Wallet] Relworx send payment response: {response_data}")
            res.raise_for_status()
            return response_data
        except requests.exceptions.HTTPError:
            logger.error(f"[Wallet] Relworx send payment failed with status {res.status_code}")
            logger.error(f"[Wallet] Response body: {res.text}")
            raise 