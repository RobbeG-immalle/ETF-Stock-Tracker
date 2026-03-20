"""Technical indicator calculations.

Computes RSI, MACD, Bollinger Bands, SMAs, EMAs, ATR, and volume
analysis from OHLCV DataFrames using the *ta* library and pandas.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd
import ta

from config import (
    ATR_PERIOD,
    BB_PERIOD,
    BB_STD,
    EMA_LONG,
    EMA_SHORT,
    MACD_FAST,
    MACD_SIGNAL,
    MACD_SLOW,
    RSI_PERIOD,
    SMA_LONG,
    SMA_MID,
    SMA_SHORT,
    VOLUME_AVG_PERIOD,
)

logger = logging.getLogger(__name__)


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add technical indicator columns to *df* (OHLCV) and return it.

    Input columns expected: Open, High, Low, Close, Volume.
    """
    if df.empty or len(df) < 30:
        return df

    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"]

    # RSI
    df[f"RSI_{RSI_PERIOD}"] = ta.momentum.RSIIndicator(close, window=RSI_PERIOD).rsi()

    # MACD
    macd_ind = ta.trend.MACD(close, window_slow=MACD_SLOW, window_fast=MACD_FAST, window_sign=MACD_SIGNAL)
    df["MACD"] = macd_ind.macd()
    df["MACD_signal"] = macd_ind.macd_signal()
    df["MACD_hist"] = macd_ind.macd_diff()

    # Bollinger Bands
    bb = ta.volatility.BollingerBands(close, window=BB_PERIOD, window_dev=BB_STD)
    df["BB_upper"] = bb.bollinger_hband()
    df["BB_middle"] = bb.bollinger_mavg()
    df["BB_lower"] = bb.bollinger_lband()
    df["BB_pband"] = bb.bollinger_pband()  # % position within bands (0-1)

    # SMAs
    df[f"SMA_{SMA_SHORT}"] = ta.trend.SMAIndicator(close, window=SMA_SHORT).sma_indicator()
    df[f"SMA_{SMA_MID}"] = ta.trend.SMAIndicator(close, window=SMA_MID).sma_indicator()
    if len(df) >= SMA_LONG:
        df[f"SMA_{SMA_LONG}"] = ta.trend.SMAIndicator(close, window=SMA_LONG).sma_indicator()

    # EMAs
    df[f"EMA_{EMA_SHORT}"] = ta.trend.EMAIndicator(close, window=EMA_SHORT).ema_indicator()
    df[f"EMA_{EMA_LONG}"] = ta.trend.EMAIndicator(close, window=EMA_LONG).ema_indicator()

    # ATR
    df[f"ATR_{ATR_PERIOD}"] = ta.volatility.AverageTrueRange(high, low, close, window=ATR_PERIOD).average_true_range()

    # Volume: rolling average and relative volume
    df[f"Volume_SMA_{VOLUME_AVG_PERIOD}"] = volume.rolling(VOLUME_AVG_PERIOD).mean()
    vol_avg = df[f"Volume_SMA_{VOLUME_AVG_PERIOD}"]
    df["Relative_Volume"] = volume / vol_avg.replace(0, np.nan)

    return df


def get_latest_signals(df: pd.DataFrame) -> dict[str, Any]:
    """Extract the most recent indicator values and derive signals.

    Returns a dict with scalar values and categorical signals used by
    the scoring engine.
    """
    if df.empty:
        return {}

    row = df.iloc[-1]

    def safe(key: str) -> float | None:
        val = row.get(key)
        if val is None or (isinstance(val, float) and np.isnan(val)):
            return None
        return float(val)

    rsi = safe(f"RSI_{RSI_PERIOD}")
    macd = safe("MACD")
    macd_sig = safe("MACD_signal")
    macd_hist = safe("MACD_hist")
    bb_pband = safe("BB_pband")
    close = safe("Close")
    sma20 = safe(f"SMA_{SMA_SHORT}")
    sma50 = safe(f"SMA_{SMA_MID}")
    sma200 = safe(f"SMA_{SMA_LONG}")
    ema12 = safe(f"EMA_{EMA_SHORT}")
    ema26 = safe(f"EMA_{EMA_LONG}")
    rel_vol = safe("Relative_Volume")

    signals: dict[str, Any] = {
        "rsi": rsi,
        "macd": macd,
        "macd_signal": macd_sig,
        "macd_hist": macd_hist,
        "bb_pband": bb_pband,
        "close": close,
        "sma20": sma20,
        "sma50": sma50,
        "sma200": sma200,
        "ema12": ema12,
        "ema26": ema26,
        "relative_volume": rel_vol,
    }

    # --- Derived signals ---

    # RSI: oversold (<30) bullish, overbought (>70) bearish
    if rsi is not None:
        if rsi < 30:
            signals["rsi_signal"] = "oversold"
        elif rsi > 70:
            signals["rsi_signal"] = "overbought"
        else:
            signals["rsi_signal"] = "neutral"
    else:
        signals["rsi_signal"] = "unknown"

    # MACD crossover
    if macd is not None and macd_sig is not None:
        signals["macd_crossover"] = "bullish" if macd > macd_sig else "bearish"
    else:
        signals["macd_crossover"] = "unknown"

    # Price vs MAs
    if close is not None and sma20 is not None:
        signals["above_sma20"] = close > sma20
    if close is not None and sma50 is not None:
        signals["above_sma50"] = close > sma50
    if close is not None and sma200 is not None:
        signals["above_sma200"] = close > sma200

    # Golden/Death cross (SMA50 vs SMA200)
    if sma50 is not None and sma200 is not None:
        signals["golden_cross"] = sma50 > sma200

    # High volume
    if rel_vol is not None:
        signals["high_volume"] = rel_vol > 1.5

    return signals


def calculate_technical_score(signals: dict[str, Any]) -> float:
    """Convert *signals* dict into a technical score in [0, 100]."""
    if not signals:
        return 50.0

    score = 50.0  # neutral baseline

    rsi = signals.get("rsi")
    if rsi is not None:
        # Oversold is bullish, score closer to 50-65 range
        if rsi < 30:
            score += 10
        elif rsi < 40:
            score += 5
        elif rsi > 70:
            score -= 10
        elif rsi > 60:
            score -= 3

    if signals.get("macd_crossover") == "bullish":
        score += 8
    elif signals.get("macd_crossover") == "bearish":
        score -= 8

    if signals.get("macd_hist") is not None:
        hist = signals["macd_hist"]
        score += min(5, max(-5, hist * 100))  # small adjustment

    if signals.get("above_sma20"):
        score += 4
    else:
        score -= 4

    if signals.get("above_sma50"):
        score += 5
    else:
        score -= 5

    if signals.get("above_sma200"):
        score += 6
    else:
        score -= 6

    if signals.get("golden_cross"):
        score += 5
    else:
        score -= 3

    bb_pband = signals.get("bb_pband")
    if bb_pband is not None:
        if bb_pband < 0.2:
            score += 5   # near lower band → potential bounce
        elif bb_pband > 0.8:
            score -= 5   # near upper band → potential pullback

    if signals.get("high_volume"):
        score += 3  # volume confirmation is positive

    return max(0.0, min(100.0, score))
