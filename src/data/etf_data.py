"""ETF-specific data fetcher.

Retrieves ETF metadata such as top holdings, expense ratio, performance
metrics, and category/sector allocation using yfinance.
"""

from __future__ import annotations

import logging
from typing import Any

import yfinance as yf

logger = logging.getLogger(__name__)


def get_etf_info(ticker: str) -> dict[str, Any]:
    """Return ETF-specific metadata for *ticker*.

    Keys: name, category, expense_ratio, ytd_return, 3y_return, 5y_return,
    nav, total_assets, holdings_count, top_holdings, sector_weights.
    """
    result: dict[str, Any] = {
        "ticker": ticker,
        "name": ticker,
        "category": "N/A",
        "expense_ratio": None,
        "ytd_return": None,
        "3y_return": None,
        "5y_return": None,
        "nav": None,
        "total_assets": None,
        "holdings_count": None,
        "top_holdings": [],
        "sector_weights": {},
    }
    try:
        t = yf.Ticker(ticker)
        info = t.info or {}

        result["name"] = info.get("longName") or info.get("shortName") or ticker
        result["category"] = info.get("category") or info.get("fundFamily") or "N/A"
        result["expense_ratio"] = info.get("annualReportExpenseRatio") or info.get("expenseRatio")
        result["ytd_return"] = info.get("ytdReturn")
        result["3y_return"] = info.get("threeYearAverageReturn")
        result["5y_return"] = info.get("fiveYearAverageReturn")
        result["nav"] = info.get("navPrice") or info.get("regularMarketPrice")
        result["total_assets"] = info.get("totalAssets")
        result["holdings_count"] = info.get("holdings")

        # Try to fetch top holdings
        try:
            holdings_df = t.funds_data.top_holdings if hasattr(t, "funds_data") and t.funds_data is not None else None
            if holdings_df is not None and not holdings_df.empty:
                result["top_holdings"] = holdings_df.head(10).reset_index().to_dict(orient="records")
        except Exception:  # noqa: BLE001
            pass

        # Sector weights
        try:
            if hasattr(t, "funds_data") and t.funds_data is not None:
                sector_df = t.funds_data.sector_weightings
                if sector_df is not None:
                    result["sector_weights"] = sector_df.to_dict() if hasattr(sector_df, "to_dict") else {}
        except Exception:  # noqa: BLE001
            pass

    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to fetch ETF info for %s: %s", ticker, exc)

    return result


def is_etf(ticker: str) -> bool:
    """Return True if *ticker* appears to be an ETF rather than a stock."""
    try:
        t = yf.Ticker(ticker)
        info = t.info or {}
        quote_type = info.get("quoteType", "").upper()
        return quote_type in ("ETF", "MUTUALFUND")
    except Exception:  # noqa: BLE001
        return False
