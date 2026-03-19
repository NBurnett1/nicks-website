"""
ASX Valuation Pipeline — Orchestrator

Runs the full pipeline:
1. Fetch financial data for ASX top 100 via yfinance
2. Score and rank stocks by composite valuation metric
3. Generate AI equity research reports for top 20 stocks (via Gemini)
4. Write results as static JSON to public/data/

Usage:
    python scripts/run_pipeline.py                     # Full pipeline
    python scripts/run_pipeline.py --skip-reports       # Skip AI reports (data only)
    python scripts/run_pipeline.py --tickers BHP CBA    # Test with specific tickers
"""

import json
import os
import sys
import argparse
from datetime import datetime, timezone, timedelta

# Add scripts dir to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import ASX_TICKERS, format_market_cap
from fetch_data import fetch_stock_data
from score_stocks import score_stocks, get_top_stocks, stock_to_summary_dict


def run_pipeline(tickers=None, exchange="ASX", skip_reports=False, top_n=10):
    """Run the full valuation pipeline."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(project_root, "public", "data")
    reports_dir = os.path.join(data_dir, "reports")

    os.makedirs(reports_dir, exist_ok=True)

    aest = timezone(timedelta(hours=11))
    now = datetime.now(aest)
    timestamp = now.isoformat()

    print("=" * 60)
    print("  ASX VALUATION PIPELINE")
    print(f"  {now.strftime('%A %d %B %Y, %I:%M %p AEST')}")
    print("=" * 60)

    # ── Step 1: Fetch data ──
    print(f"\n📊 Step 1: Fetching {exchange} stock data...\n")
    df = fetch_stock_data(tickers=tickers, exchange=exchange)

    if df.empty:
        print("\n❌ No data fetched. Aborting.")
        sys.exit(1)

    # ── Step 2: Score and rank ──
    print("\n🧮 Step 2: Scoring stocks...\n")
    df = score_stocks(df)

    # Add formatted market cap
    df["marketCapFormatted"] = df["marketCap"].apply(format_market_cap)

    overvalued, undervalued = get_top_stocks(df, n=top_n)

    # ── Step 3: Write summary.json ──
    print("\n💾 Step 3: Writing summary.json...")

    summary = {
        "lastUpdated": timestamp,
        "marketName": exchange,
        "overvalued": [stock_to_summary_dict(row) for _, row in overvalued.iterrows()],
        "undervalued": [stock_to_summary_dict(row) for _, row in undervalued.iterrows()],
    }

    summary_path = os.path.join(data_dir, f"{exchange.lower()}_summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"  ✓ Written to {summary_path}")

    # ── Step 4: Write meta.json ──
    meta = {
        "lastUpdated": timestamp,
        "pipelineVersion": "1.0.0",
        "stocksAnalyzed": len(df),
        "dataSource": "yfinance",
        "aiModel": "gemini-2.5-flash",
    }

    meta_path = os.path.join(data_dir, f"{exchange.lower()}_meta.json")
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)
    print(f"  ✓ Written to {meta_path}")

    # ── Step 5: Generate AI reports ──
    if not skip_reports:
        print("\n🤖 Step 4: Generating AI equity research reports...\n")

        try:
            from generate_reports import setup_gemini, generate_all_reports

            model = setup_gemini()

            # Combine overvalued + undervalued for report generation
            import pandas as pd
            report_stocks = pd.concat([overvalued, undervalued], ignore_index=True)

            success = generate_all_reports(model, report_stocks, reports_dir, delay=10.0)
            print(f"\n  ✓ Generated {success} / {len(report_stocks)} reports")

        except ValueError as e:
            print(f"\n  ⚠ Skipping AI reports: {e}")
            print("  Set GEMINI_API_KEY environment variable to enable report generation.")

    else:
        print("\n⏭ Skipping AI reports (--skip-reports flag)")

    # ── Done ──
    print("\n" + "=" * 60)
    print("  ✅ PIPELINE COMPLETE")
    print(f"  Stocks analyzed: {len(df)}")
    print(f"  Overvalued: {len(overvalued)} | Undervalued: {len(undervalued)}")
    print(f"  Output: {data_dir}")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Valuation Pipeline")
    parser.add_argument("--exchange", type=str, default="ASX", choices=["ASX", "NYSE", "NASDAQ"], help="Exchange to analyze")
    parser.add_argument("--skip-reports", action="store_true", help="Skip AI report generation")
    parser.add_argument("--tickers", nargs="+", help="Specific tickers to analyze (for testing)")
    parser.add_argument("--top-n", type=int, default=10, help="Number of top stocks per category")
    args = parser.parse_args()

    run_pipeline(
        tickers=args.tickers,
        exchange=args.exchange,
        skip_reports=args.skip_reports,
        top_n=args.top_n,
    )
