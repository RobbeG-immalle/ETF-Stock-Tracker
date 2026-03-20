# 📈 ETF & Stock AI Tracker

An AI-powered finance agent that fetches data from Yahoo Finance, analyzes stocks and ETFs using technical indicators, fundamental scoring, and news sentiment analysis, and displays the results in an interactive Streamlit dashboard.

## 🚀 Features

- **~40 pre-loaded tickers** — 26 popular stocks + 16 ETFs
- **AI Composite Buy Score (0–100)** — combines technical, fundamental, and sentiment analysis
- **Recommendation categories** — Strong Buy / Buy / Hold / Sell / Strong Sell
- **Interactive dashboard** — Overview, Stock Analysis, ETF Analysis, and Settings pages
- **Local data caching** — avoids excessive API calls; configurable expiry
- **No API keys required** — uses free `yfinance` and public RSS feeds

## 📸 Dashboard Pages

| Page | Description |
|---|---|
| 🏠 Overview | Top picks, score bar charts, sector heatmap |
| 📊 Stock Analysis | Sortable table, price charts with indicators, fundamentals, news |
| 📈 ETF Analysis | ETF table, expense ratio comparison, detailed breakdown |
| ⚙️ Settings | Edit watchlist, adjust scoring weights, clear cache |

## 🛠️ Setup

### Prerequisites

- Python 3.10+
- pip

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/RobbeG-immalle/ETF-Stock-Tracker.git
cd ETF-Stock-Tracker

# 2. (Optional) create a virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Download NLTK VADER lexicon (one-time, ~1 MB)
python -c "import nltk; nltk.download('vader_lexicon')"
```

### Run the Dashboard

```bash
streamlit run src/dashboard/app.py
```

The dashboard opens at `http://localhost:8501`.

### Pre-fetch Data (Optional)

```bash
python main.py --fetch-only   # cache all data without launching the UI
python main.py                # fetch data AND launch the dashboard
```

## 🏗️ Architecture

```
ETF-Stock-Tracker/
├── config.py                    ← central configuration
├── main.py                      ← entry point
├── requirements.txt
├── src/
│   ├── data/
│   │   ├── yahoo_finance.py     ← yfinance wrapper (OHLCV + fundamentals)
│   │   ├── news_fetcher.py      ← RSS news via feedparser
│   │   ├── etf_data.py          ← ETF-specific metadata
│   │   └── data_manager.py      ← orchestrator + JSON cache
│   ├── analysis/
│   │   ├── technical_indicators.py  ← RSI, MACD, BB, SMAs, EMA, ATR
│   │   ├── fundamental_analysis.py  ← valuation/growth/profitability scoring
│   │   ├── sentiment_analysis.py    ← VADER NLP on headlines
│   │   └── scoring_engine.py        ← composite Buy Score engine
│   └── dashboard/
│       ├── app.py               ← Streamlit multi-page application
│       ├── charts.py            ← Plotly chart components
│       └── components.py        ← reusable UI widgets
└── .github/workflows/
    └── daily_analysis.yml       ← automated daily data fetch
```

## 🤖 How the Scoring Algorithm Works

Each ticker receives a **Buy Score** from 0 to 100 composed of three dimensions:

| Dimension | Stock Weight | ETF Weight | Description |
|---|---|---|---|
| Technical | 35% | 50% | RSI, MACD, Bollinger Bands, Moving Averages |
| Fundamental | 40% | 20% | P/E, P/B, PEG, Growth, Margin, ROE, D/E |
| Sentiment | 25% | 30% | VADER NLP score of recent news headlines |

### Score Categories

| Score | Category |
|---|---|
| ≥ 75 | 🟢 Strong Buy |
| ≥ 60 | 🟩 Buy |
| ≥ 40 | 🟡 Hold |
| ≥ 25 | 🟠 Sell |
| < 25 | 🔴 Strong Sell |

### Technical Indicators

| Indicator | Signal |
|---|---|
| RSI < 30 | Oversold → Bullish |
| RSI > 70 | Overbought → Bearish |
| MACD > Signal | Bullish crossover |
| Price > SMA 20/50/200 | Uptrend |
| SMA 50 > SMA 200 | Golden Cross |
| BB % Band < 20% | Near lower band → potential bounce |

### Fundamental Scoring (Stocks)

- **Valuation** (30%): P/E, P/B, PEG ratio
- **Growth** (25%): Revenue and earnings growth
- **Profitability** (25%): Profit margin, Return on Equity
- **Dividend** (10%): Yield and payout ratio sustainability
- **Financial Health** (10%): Debt-to-equity, current ratio

## ⚙️ Configuration

Edit `config.py` to customise:

- `STOCK_WATCHLIST` / `ETF_WATCHLIST` — default tickers
- `STOCK_SCORING_WEIGHTS` / `ETF_SCORING_WEIGHTS` — dimension weights
- `CACHE_EXPIRY_HOURS` — how long to keep cached data
- `HISTORICAL_PERIOD` — price history window (e.g. `"1y"`, `"6mo"`)
- `TOP_N_PICKS` — number of picks shown on the overview page

Weights can also be adjusted at runtime in the **⚙️ Settings** page of the dashboard.

## 🔧 Tech Stack

| Library | Purpose |
|---|---|
| `yfinance` | Yahoo Finance data (free, no API key) |
| `streamlit` | Dashboard framework |
| `plotly` | Interactive charts |
| `pandas` / `numpy` | Data manipulation |
| `ta` | Technical analysis indicators |
| `nltk` (VADER) | News sentiment analysis |
| `feedparser` | RSS news feed parsing |

## 📅 Automated Daily Analysis

A GitHub Actions workflow (`.github/workflows/daily_analysis.yml`) runs every day at 21:00 UTC to pre-fetch fresh data. The cached results are stored as workflow artifacts.

## 📄 License

MIT
