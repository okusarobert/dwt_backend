import requests
from requests.exceptions import RequestException
import time
import logging
from flask import current_app

logger = logging.getLogger(__name__)

class WalletServiceClient:
    def __init__(self, base_url, timeout=5, max_retries=3):
        current_app.logger.info(f"WalletServiceClient: {base_url}")
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries

    def _make_request(self, method, endpoint, token, data=None):
        url = f"{self.base_url}{endpoint}"
        retries = 0
        headers = {"Authorization": token} if token else {}

        current_app.logger.info(f"WalletServiceClient: {method} {url} {data}")
        while retries < self.max_retries:
            try:
                if method == 'GET':
                    response = requests.get(url, headers=headers, timeout=self.timeout)
                elif method == 'POST':
                    response = requests.post(url, json=data, headers=headers, timeout=self.timeout)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                response.raise_for_status()
                resp = response.json()
                current_app.logger.info(f"WalletServiceClient: {resp}")
                return resp
            except RequestException as e:
                retries += 1
                logger.warning(f"WalletServiceClient: {method} {url} failed (attempt {retries}): {e}")
                if retries >= self.max_retries:
                    logger.error(f"WalletServiceClient: {method} {url} failed after {retries} attempts: {e}")
                    raise
                time.sleep(0.5 * (2 ** retries))

    def check_balance(self, user_id, token):
        # Assumes wallet service expects user_id as a query param
        return self._make_request('GET', f"/wallet/balance?user_id={user_id}", token)

    def reserve_funds(self, user_id, amount, reference, token):
        data = {"user_id": user_id, "amount": amount, "reference": reference}
        return self._make_request('POST', "/wallet/reserve", token, data)

    def release_funds(self, user_id, amount, reference, token):
        data = {"user_id": user_id, "amount": amount, "reference": reference}
        return self._make_request('POST', "/wallet/release", token, data) 