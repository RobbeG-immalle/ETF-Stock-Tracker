"""Central configuration for the ETF-Stock-Tracker AI Finance Agent."""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Watchlist
# ---------------------------------------------------------------------------

STOCK_WATCHLIST: list[str] = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA",
    "JPM", "V", "JNJ", "UNH", "PG", "HD", "MA", "XOM",
    "CVX", "ABBV", "KO", "PEP", "MRK", "COST", "CRM",
    "AMD", "NFLX", "LLY", "AVGO",
]

ETF_WATCHLIST: list[str] = [
    "SPY", "QQQ", "VTI", "VOO", "IWM", "VGT", "VHT",
    "SCHD", "VYM", "ARKK", "XLF", "XLE", "XLK", "BND", "TLT", "GLD",
]

ALL_TICKERS: list[str] = STOCK_WATCHLIST + ETF_WATCHLIST

# ---------------------------------------------------------------------------
# Scoring weights (must sum to 1.0 within each profile)
# ---------------------------------------------------------------------------

STOCK_SCORING_WEIGHTS: dict[str, float] = {
    "technical": 0.35,
    "fundamental": 0.40,
    "sentiment": 0.25,
}

ETF_SCORING_WEIGHTS: dict[str, float] = {
    "technical": 0.50,
    "fundamental": 0.20,   # limited fundamental data for ETFs
    "sentiment": 0.30,
}

# ---------------------------------------------------------------------------
# Score thresholds → recommendation categories
# ---------------------------------------------------------------------------

SCORE_THRESHOLDS: dict[str, float] = {
    "Strong Buy": 75,
    "Buy": 60,
    "Hold": 40,
    "Sell": 25,
    # below 25 → Strong Sell
}

# ---------------------------------------------------------------------------
# Cache settings
# ---------------------------------------------------------------------------

CACHE_DIR: str = "data_cache"
CACHE_EXPIRY_HOURS: int = 6       # refresh after N hours
NEWS_CACHE_EXPIRY_HOURS: int = 2  # news is more time-sensitive

# ---------------------------------------------------------------------------
# Data fetch settings
# ---------------------------------------------------------------------------

HISTORICAL_PERIOD: str = "1y"    # passed to yfinance
HISTORICAL_INTERVAL: str = "1d"

NEWS_FEED_URLS: list[str] = [
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US",
    "https://finance.yahoo.com/rss/headline?s={ticker}",
]

# Fallback generic financial news feeds (no ticker substitution)
GENERIC_NEWS_FEEDS: list[str] = [
    "https://feeds.finance.yahoo.com/rss/2.0/headline?region=US&lang=en-US",
]

# ---------------------------------------------------------------------------
# Technical indicator parameters
# ---------------------------------------------------------------------------

RSI_PERIOD: int = 14
MACD_FAST: int = 12
MACD_SLOW: int = 26
MACD_SIGNAL: int = 9
BB_PERIOD: int = 20
BB_STD: float = 2.0
ATR_PERIOD: int = 14
SMA_SHORT: int = 20
SMA_MID: int = 50
SMA_LONG: int = 200
EMA_SHORT: int = 12
EMA_LONG: int = 26
VOLUME_AVG_PERIOD: int = 20

# ---------------------------------------------------------------------------
# Dashboard settings
# ---------------------------------------------------------------------------

DASHBOARD_TITLE: str = "📈 ETF & Stock AI Tracker"
TOP_N_PICKS: int = 10
THEME_PRIMARY_COLOR: str = "#00d4aa"
REFRESH_INTERVAL_MINUTES: int = 60
