"""Binance Global API client — fetches spot, earn, and staking balances."""

import hashlib
import hmac
import time
import urllib.parse
from typing import Optional

import httpx


BINANCE_BASE = "https://api.binance.com"

# Minimum USD equivalent to include (filter dust)
_DUST_THRESHOLD_USDT = 0.5


def _sign(secret: str, query_string: str) -> str:
    return hmac.new(secret.encode(), query_string.encode(), hashlib.sha256).hexdigest()


def _headers(api_key: str) -> dict:
    return {"X-MBX-APIKEY": api_key}


def _signed_get(path: str, api_key: str, secret: str, params: dict | None = None) -> dict | list:
    params = params or {}
    params["timestamp"] = int(time.time() * 1000)
    query_string = urllib.parse.urlencode(params)
    params["signature"] = _sign(secret, query_string)
    url = f"{BINANCE_BASE}{path}"
    resp = httpx.get(url, params=params, headers=_headers(api_key), timeout=15)
    resp.raise_for_status()
    return resp.json()


def fetch_spot_balances(api_key: str, secret: str) -> dict[str, float]:
    """Returns {symbol: free+locked quantity} for non-dust spot balances."""
    data = _signed_get("/api/v3/account", api_key, secret)
    result = {}
    for bal in data.get("balances", []):
        asset = bal["asset"]
        total = float(bal["free"]) + float(bal["locked"])
        if total > 0:
            result[asset] = result.get(asset, 0) + total
    return result


def fetch_flexible_earn_balances(api_key: str, secret: str) -> dict[str, float]:
    """Returns {symbol: total_amount} for Simple Earn flexible positions (includes rewards)."""
    result = {}
    try:
        page = 1
        while True:
            data = _signed_get(
                "/sapi/v1/simple-earn/flexible/position",
                api_key, secret,
                {"size": 100, "current": page},
            )
            rows = data.get("rows", [])
            if not rows:
                break
            for row in rows:
                asset = row.get("asset", "")
                amount = float(row.get("totalAmount", 0))
                if asset and amount > 0:
                    result[asset] = result.get(asset, 0) + amount
            if not data.get("total", 0) > page * 100:
                break
            page += 1
    except Exception:
        # Endpoint may not be enabled or user has no positions
        pass
    return result


def fetch_locked_staking_balances(api_key: str, secret: str) -> dict[str, float]:
    """Returns {symbol: total_amount} for Simple Earn locked (staking) positions."""
    result = {}
    try:
        page = 1
        while True:
            data = _signed_get(
                "/sapi/v1/simple-earn/locked/position",
                api_key, secret,
                {"size": 100, "current": page},
            )
            rows = data.get("rows", [])
            if not rows:
                break
            for row in rows:
                asset = row.get("asset", "")
                amount = float(row.get("amount", 0))
                if asset and amount > 0:
                    result[asset] = result.get(asset, 0) + amount
            if not data.get("total", 0) > page * 100:
                break
            page += 1
    except Exception:
        pass
    return result


def aggregate_balances(api_key: str, secret: str) -> dict[str, float]:
    """Aggregate spot + earn + staking into total quantity per asset."""
    spot = fetch_spot_balances(api_key, secret)
    earn = fetch_flexible_earn_balances(api_key, secret)
    staking = fetch_locked_staking_balances(api_key, secret)

    totals: dict[str, float] = {}
    for src in (spot, earn, staking):
        for asset, qty in src.items():
            totals[asset] = totals.get(asset, 0) + qty

    # Filter stablecoins that are basically USD (USDT, BUSD, USDC, etc.) — still include them
    # Filter absolute dust (< 0.000001)
    return {k: v for k, v in totals.items() if v >= 0.000001}
