"""
Fiat FX Service: convert fiat currencies to USD.

- Uses environment-provided static rates when available.
- Falls back to hardcoded sane defaults if not configured.
- Designed to be easily swapped with a live FX provider.
"""
from __future__ import annotations

import os
import json
from typing import Dict, Optional


class FiatFxService:
    def __init__(self, rates: Optional[Dict[str, float]] = None):
        # Load from env JSON if provided, e.g. {"UGX": 0.00027, "KES": 0.0077, "TZS": 0.00038, "USD": 1}
        env_rates_json = os.environ.get("FIAT_USD_RATES_JSON", "")
        from_env: Dict[str, float] = {}
        if env_rates_json:
            try:
                from_env = json.loads(env_rates_json)
            except Exception:
                from_env = {}
        # Hardcoded fallbacks (approximate; override via env in production)
        defaults = {
            "USD": 1.0,
            "UGX": 0.00027,
            "KES": 0.0077,
            "TZS": 0.00038,
        }
        self.rates: Dict[str, float] = {
            **defaults,
            **(rates or {}),
            **{k.upper(): float(v) for k, v in from_env.items() if isinstance(v, (int, float, str))},
        }

    def get_rate_to_usd(self, code: str) -> float:
        if not code:
            return 0.0
        return float(self.rates.get(code.upper(), 0.0))

    def convert_to_usd(self, amount: float, code: str) -> float:
        rate = self.get_rate_to_usd(code)
        return float(amount) * rate if rate else 0.0


# Simple singleton accessor
_fiat_fx_singleton: Optional[FiatFxService] = None

def get_fiat_fx_service() -> FiatFxService:
    global _fiat_fx_singleton
    if _fiat_fx_singleton is None:
        _fiat_fx_singleton = FiatFxService()
    return _fiat_fx_singleton
