"""Fetch market data from Yahoo Finance and other providers."""

from datetime import date, datetime, timezone, timedelta
from typing import Optional

import yfinance as yf
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models.asset import Asset, HistoricalPrice, AssetType


async def get_or_create_asset(
    symbol: str,
    db: AsyncSession,
    asset_type: AssetType = AssetType.STOCK,
    currency: str = "USD",
) -> Asset:
    """Get existing asset or create new one."""
    result = await db.execute(select(Asset).where(Asset.symbol == symbol.upper()))
    asset = result.scalar_one_or_none()

    if asset:
        return asset

    # Fetch info from Yahoo Finance using fast_info (avoids rate limits)
    try:
        ticker = yf.Ticker(symbol)
        fi = ticker.fast_info
        name = getattr(fi, "exchange", None)  # fast_info has limited fields
        price = _get_current_price_fast(symbol)
        asset = Asset(
            symbol=symbol.upper(),
            name=symbol.upper(),
            asset_type=asset_type,
            currency=currency,
            current_price=price,
            last_price_update=datetime.now(timezone.utc) if price else None,
        )
    except Exception:
        asset = Asset(
            symbol=symbol.upper(),
            name=symbol.upper(),
            asset_type=asset_type,
            currency=currency,
        )

    db.add(asset)
    await db.flush()
    await db.refresh(asset)
    return asset


def _get_current_price_fast(symbol: str) -> Optional[float]:
    """Get current price via batch download (reliable, avoids quoteSummary rate limits)."""
    try:
        df = yf.download(symbol, period="2d", progress=False, auto_adjust=True)
        if not df.empty:
            return float(df["Close"].iloc[-1])
    except Exception:
        pass
    return None


def get_current_prices_batch(symbols: list[str]) -> dict[str, float]:
    """Fetch current prices for multiple symbols at once (efficient batch download)."""
    if not symbols:
        return {}
    try:
        df = yf.download(symbols, period="2d", progress=False, auto_adjust=True)
        if df.empty:
            return {}
        close = df["Close"].iloc[-1]
        if len(symbols) == 1:
            return {symbols[0]: float(close)} if not hasattr(close, "items") else {symbols[0]: float(close.iloc[0])}
        return {str(sym): float(price) for sym, price in close.items() if price and str(price) != "nan"}
    except Exception:
        return {}


def fetch_historical_prices_sync(symbol: str, start_date: date, end_date: date = None) -> list[dict]:
    """Fetch historical OHLCV data (runs in sync context for Celery workers)."""
    end = end_date or date.today()
    ticker = yf.Ticker(symbol)
    df = ticker.history(start=start_date.isoformat(), end=end.isoformat())

    if df.empty:
        return []

    prices = []
    for idx, row in df.iterrows():
        prices.append(
            {
                "price_date": idx.date(),
                "open_price": float(round(row["Open"], 4)),
                "high_price": float(round(row["High"], 4)),
                "low_price": float(round(row["Low"], 4)),
                "close_price": float(round(row["Close"], 4)),
                "volume": int(row["Volume"]) if row["Volume"] else None,
            }
        )
    return prices


async def fetch_and_store_historical_prices(
    asset_id: int,
    symbol: str,
    start_date: date,
    end_date: date,
    db: AsyncSession,
) -> int:
    """Fetch historical prices and upsert into database."""
    prices = fetch_historical_prices_sync(symbol, start_date, end_date)

    if not prices:
        return 0

    for price in prices:
        stmt = pg_insert(HistoricalPrice).values(
            asset_id=asset_id,
            **price,
        ).on_conflict_do_update(
            constraint="uq_asset_date",
            set_={
                "close_price": price["close_price"],
                "open_price": price["open_price"],
                "high_price": price["high_price"],
                "low_price": price["low_price"],
                "volume": price["volume"],
            },
        )
        await db.execute(stmt)

    await db.commit()
    return len(prices)


async def update_current_price(asset_id: int, symbol: str, db: AsyncSession) -> Optional[float]:
    """Update the current price of an asset."""
    price = _get_current_price_fast(symbol)
    if price:
        asset = await db.get(Asset, asset_id)
        if asset:
            asset.current_price = price
            asset.last_price_update = datetime.now(timezone.utc)
            await db.commit()
        return price
    return None
