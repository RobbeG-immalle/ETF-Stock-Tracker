"""Yahoo Finance data fetcher using the yfinance library.

Provides historical OHLCV data, company fundamentals, sector/industry
information, and current quote data for both stocks and ETFs.
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)


def get_historical_prices(
    ticker: str,
    period: str = "1y",
    interval: str = "1d",
) -> pd.DataFrame:
    """Return OHLCV DataFrame for *ticker* over the given *period*.

    Columns: Open, High, Low, Close, Volume
    Index: DatetimeIndex (UTC-normalised)

    Returns an empty DataFrame on failure.
    """
    try:
        data = yf.download(
            ticker,
            period=period,
            interval=interval,
            auto_adjust=True,
            progress=False,
        )
        if data.empty:
            logger.warning("No historical data returned for %s", ticker)
        # Flatten MultiIndex columns that yfinance sometimes returns
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        return data
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to fetch historical prices for %s: %s", ticker, exc)
        return pd.DataFrame()


def get_fundamentals(ticker: str) -> dict[str, Any]:
    """Return a dictionary of key fundamental metrics for *ticker*.

    Keys include: pe_ratio, pb_ratio, peg_ratio, market_cap, revenue,
    eps, dividend_yield, debt_to_equity, profit_margin, roe,
    current_ratio, beta, sector, industry, name.
    """
    result: dict[str, Any] = {
        "ticker": ticker,
        "name": ticker,
        "sector": "N/A",
        "industry": "N/A",
        "market_cap": None,
        "pe_ratio": None,
        "pb_ratio": None,
        "peg_ratio": None,
        "eps": None,
        "revenue": None,
        "revenue_growth": None,
        "earnings_growth": None,
        "dividend_yield": None,
        "payout_ratio": None,
        "debt_to_equity": None,
        "current_ratio": None,
        "profit_margin": None,
        "roe": None,
        "beta": None,
        "52w_high": None,
        "52w_low": None,
        "avg_volume": None,
    }
    try:
        t = yf.Ticker(ticker)
        info = t.info or {}

        result["name"] = info.get("longName") or info.get("shortName") or ticker
        result["sector"] = info.get("sector") or info.get("category") or "N/A"
        result["industry"] = info.get("industry") or "N/A"
        result["market_cap"] = info.get("marketCap")
        result["pe_ratio"] = info.get("trailingPE") or info.get("forwardPE")
        result["pb_ratio"] = info.get("priceToBook")
        result["peg_ratio"] = info.get("pegRatio")
        result["eps"] = info.get("trailingEps") or info.get("forwardEps")
        result["revenue"] = info.get("totalRevenue")
        result["revenue_growth"] = info.get("revenueGrowth")
        result["earnings_growth"] = info.get("earningsGrowth")
        result["dividend_yield"] = info.get("dividendYield")
        result["payout_ratio"] = info.get("payoutRatio")
        result["debt_to_equity"] = info.get("debtToEquity")
        result["current_ratio"] = info.get("currentRatio")
        result["profit_margin"] = info.get("profitMargins")
        result["roe"] = info.get("returnOnEquity")
        result["beta"] = info.get("beta")
        result["52w_high"] = info.get("fiftyTwoWeekHigh")
        result["52w_low"] = info.get("fiftyTwoWeekLow")
        result["avg_volume"] = info.get("averageVolume")
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to fetch fundamentals for %s: %s", ticker, exc)

    return result


def get_current_quote(ticker: str) -> dict[str, Any]:
    """Return the latest price and basic quote data for *ticker*."""
    result: dict[str, Any] = {
        "ticker": ticker,
        "price": None,
        "change": None,
        "change_pct": None,
        "volume": None,
        "market_cap": None,
    }
    try:
        t = yf.Ticker(ticker)
        info = t.info or {}
        price = (
            info.get("currentPrice")
            or info.get("regularMarketPrice")
            or info.get("navPrice")
        )
        prev_close = info.get("previousClose") or info.get("regularMarketPreviousClose")
        result["price"] = price
        result["volume"] = info.get("regularMarketVolume") or info.get("volume")
        result["market_cap"] = info.get("marketCap")
        if price is not None and prev_close:
            result["change"] = round(price - prev_close, 4)
            result["change_pct"] = round((price - prev_close) / prev_close * 100, 2)
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to fetch current quote for %s: %s", ticker, exc)

    return result
