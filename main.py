#!/usr/bin/env python3
"""Entry point: fetch data, run analysis, and launch the dashboard.

Usage:
    python main.py              # fetch data + launch Streamlit
    python main.py --fetch-only # only fetch and cache data
"""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from pathlib import Path

# Ensure project root is on path
ROOT = Path(__file__).parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data.data_manager import DataManager
from src.analysis.scoring_engine import run_full_analysis

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def prefetch_data() -> None:
    """Pre-fetch and cache all data."""
    logger.info("Starting data fetch for all tickers…")
    dm = DataManager()
    data = dm.fetch_all_data(verbose=True)
    logger.info("Running AI analysis…")
    results = run_full_analysis(data)

    # Print top picks
    print("\n" + "=" * 60)
    print("TOP STOCK PICKS")
    print("=" * 60)
    for r in [x for x in results if not x.get("is_etf")][:10]:
        print(f"  {r['ticker']:6s}  Score: {r['buy_score']:5.1f}  {r['category']:12s}  ${r.get('price') or 0:.2f}")

    print("\n" + "=" * 60)
    print("TOP ETF PICKS")
    print("=" * 60)
    for r in [x for x in results if x.get("is_etf")][:10]:
        print(f"  {r['ticker']:6s}  Score: {r['buy_score']:5.1f}  {r['category']:12s}  ${r.get('price') or 0:.2f}")

    print("=" * 60)
    logger.info("Data fetch complete.")


def launch_dashboard() -> None:
    """Launch the Streamlit dashboard."""
    dashboard_path = ROOT / "src" / "dashboard" / "app.py"
    logger.info("Launching Streamlit dashboard: %s", dashboard_path)
    subprocess.run(  # noqa: S603
        [sys.executable, "-m", "streamlit", "run", str(dashboard_path)],
        check=False,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="ETF & Stock AI Tracker")
    parser.add_argument(
        "--fetch-only",
        action="store_true",
        help="Only fetch and cache data, do not launch the dashboard.",
    )
    args = parser.parse_args()

    prefetch_data()

    if not args.fetch_only:
        launch_dashboard()


if __name__ == "__main__":
    main()
