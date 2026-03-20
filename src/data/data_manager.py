"""Central data orchestrator with local JSON caching.

DataManager coordinates fetching of prices, fundamentals, ETF data, and
news while caching results to disk to avoid excessive API calls.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from config import (
    ALL_TICKERS,
    CACHE_DIR,
    CACHE_EXPIRY_HOURS,
    ETF_WATCHLIST,
    HISTORICAL_INTERVAL,
    HISTORICAL_PERIOD,
    NEWS_CACHE_EXPIRY_HOURS,
    STOCK_WATCHLIST,
)
from src.data.etf_data import get_etf_info
from src.data.news_fetcher import fetch_news_for_ticker
from src.data.yahoo_finance import get_fundamentals, get_historical_prices

logger = logging.getLogger(__name__)


class DataManager:
    """Manages data fetching and caching for the finance agent."""

    def __init__(
        self,
        cache_dir: str = CACHE_DIR,
        stock_watchlist: list[str] | None = None,
        etf_watchlist: list[str] | None = None,
    ) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.stock_watchlist: list[str] = stock_watchlist or list(STOCK_WATCHLIST)
        self.etf_watchlist: list[str] = etf_watchlist or list(ETF_WATCHLIST)

    # ------------------------------------------------------------------
    # Internal caching helpers
    # ------------------------------------------------------------------

    def _cache_path(self, key: str) -> Path:
        safe_key = key.replace("/", "_").replace(":", "_")
        return self.cache_dir / f"{safe_key}.json"

    def _is_cache_valid(self, path: Path, expiry_hours: int) -> bool:
        if not path.exists():
            return False
        mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        age_hours = (datetime.now(tz=timezone.utc) - mtime).total_seconds() / 3600
        return age_hours < expiry_hours

    def _load_cache(self, key: str) -> Any | None:
        path = self._cache_path(key)
        try:
            with open(path, encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:  # noqa: BLE001
            return None

    def _save_cache(self, key: str, data: Any) -> None:
        path = self._cache_path(key)
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(data, fh, default=str)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not write cache for %s: %s", key, exc)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_historical_prices(self, ticker: str) -> pd.DataFrame:
        """Return cached or freshly fetched OHLCV DataFrame."""
        key = f"prices_{ticker}_{HISTORICAL_PERIOD}"
        path = self._cache_path(key)
        if self._is_cache_valid(path, CACHE_EXPIRY_HOURS):
            cached = self._load_cache(key)
            if cached:
                try:
                    df = pd.DataFrame(cached)
                    df.index = pd.to_datetime(df.index)
                    return df
                except Exception:  # noqa: BLE001
                    pass

        df = get_historical_prices(ticker, HISTORICAL_PERIOD, HISTORICAL_INTERVAL)
        if not df.empty:
            cache_df = df.loc[:, ~df.columns.duplicated()]
            cache_df.index = cache_df.index.astype(str)
            self._save_cache(key, cache_df.to_dict())
        return df

    def get_fundamentals(self, ticker: str) -> dict[str, Any]:
        """Return cached or freshly fetched fundamental data."""
        key = f"fundamentals_{ticker}"
        path = self._cache_path(key)
        if self._is_cache_valid(path, CACHE_EXPIRY_HOURS):
            cached = self._load_cache(key)
            if cached:
                return cached

        data = get_fundamentals(ticker)
        self._save_cache(key, data)
        return data

    def get_etf_info(self, ticker: str) -> dict[str, Any]:
        """Return cached or freshly fetched ETF metadata."""
        key = f"etf_{ticker}"
        path = self._cache_path(key)
        if self._is_cache_valid(path, CACHE_EXPIRY_HOURS):
            cached = self._load_cache(key)
            if cached:
                return cached

        data = get_etf_info(ticker)
        self._save_cache(key, data)
        return data

    def get_news(self, ticker: str) -> list[dict[str, Any]]:
        """Return cached or freshly fetched news articles."""
        key = f"news_{ticker}"
        path = self._cache_path(key)
        if self._is_cache_valid(path, NEWS_CACHE_EXPIRY_HOURS):
            cached = self._load_cache(key)
            if cached is not None:
                return cached  # type: ignore[return-value]

        articles = fetch_news_for_ticker(ticker)
        self._save_cache(key, articles)
        return articles

    def fetch_all_data(
        self, tickers: list[str] | None = None, verbose: bool = True
    ) -> dict[str, dict[str, Any]]:
        """Fetch prices, fundamentals/ETF info, and news for all tickers.

        Returns a mapping ``{ticker: {prices, fundamentals, news}}``.
        """
        if tickers is None:
            tickers = self.stock_watchlist + self.etf_watchlist

        results: dict[str, dict[str, Any]] = {}
        total = len(tickers)
        for i, ticker in enumerate(tickers, 1):
            if verbose:
                print(f"  [{i}/{total}] Fetching data for {ticker}...")
            try:
                prices = self.get_historical_prices(ticker)
                if ticker in self.etf_watchlist:
                    meta = self.get_etf_info(ticker)
                else:
                    meta = self.get_fundamentals(ticker)
                news = self.get_news(ticker)
                results[ticker] = {
                    "prices": prices,
                    "meta": meta,
                    "news": news,
                    "is_etf": ticker in self.etf_watchlist,
                }
            except Exception as exc:  # noqa: BLE001
                logger.error("Error fetching data for %s: %s", ticker, exc)
                results[ticker] = {
                    "prices": pd.DataFrame(),
                    "meta": {"ticker": ticker},
                    "news": [],
                    "is_etf": ticker in self.etf_watchlist,
                }
        return results

    def invalidate_cache(self, ticker: str | None = None) -> None:
        """Delete cached files for *ticker* (or all tickers if None)."""
        if ticker:
            patterns = [f"prices_{ticker}_*", f"fundamentals_{ticker}", f"etf_{ticker}", f"news_{ticker}"]
            for p in patterns:
                for f in self.cache_dir.glob(p + ".json"):
                    f.unlink(missing_ok=True)
        else:
            for f in self.cache_dir.glob("*.json"):
                f.unlink(missing_ok=True)
