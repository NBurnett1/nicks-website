"""
N Valuations Pipeline — Orchestrator (v2: Static API Architecture)

Outputs:
  - {exchange}_index.json  → lightweight list for dashboard search (ticker, name, score, price, domain)
  - {exchange}/details/{TICKER}.json → individual heavy files (chartData, full metrics, AI report)
  - {exchange}_meta.json → pipeline metadata

Usage:
    python scripts/run_pipeline.py --exchange ASX                           # Full pipeline  
    python scripts/run_pipeline.py --exchange NYSE --skip-reports           # Skip AI reports
    python scripts/run_pipeline.py --exchange NASDAQ --limit 50            # Pilot test
"""

import json
import os
import sys
import argparse
from datetime import datetime, timezone, timedelta

# Add scripts dir to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import format_market_cap
from fetch_data import fetch_stock_data
from score_stocks import score_stocks, get_top_stocks, stock_to_summary_dict, run_valuation_tests, conviction_grade
from discover_tickers import get_all_tickers


def run_pipeline(exchange="ASX", skip_reports=False, top_n=None, limit=None, tickers=None):
    """Run the full valuation pipeline with Static API output."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(project_root, "public", "data")
    details_dir = os.path.join(data_dir, exchange.lower(), "details")
    reports_dir = os.path.join(data_dir, "reports")

    os.makedirs(details_dir, exist_ok=True)
    os.makedirs(reports_dir, exist_ok=True)

    aest = timezone(timedelta(hours=11))
    now = datetime.now(aest)
    timestamp = now.isoformat()

    print("=" * 60)
    print(f"  N VALUATIONS PIPELINE — {exchange}")
    print(f"  {now.strftime('%A %d %B %Y, %I:%M %p AEST')}")
    print("=" * 60)

    # ── Step 1: Discover tickers ──
    if tickers is None:
        print(f"\n🔍 Step 1: Discovering {exchange} tickers...")
        tickers = get_all_tickers(exchange, limit=limit)
    else:
        print(f"\n📋 Step 1: Using {len(tickers)} provided tickers...")

    print(f"  → {len(tickers)} tickers queued for analysis")

    # ── Step 2: Fetch data ──
    print(f"\n📊 Step 2: Fetching financial data...\n")
    df = fetch_stock_data(tickers=tickers, exchange=exchange)

    if df.empty:
        print("\n❌ No data fetched. Aborting.")
        sys.exit(1)

    # ── Step 3: Score and rank ──
    print("\n🧮 Step 3: Scoring stocks...\n")
    df = score_stocks(df)
    df["marketCapFormatted"] = df["marketCap"].apply(format_market_cap)

    # Run the 8 valuation tests on every stock
    print("\n🧪 Step 3b: Running valuation tests...\n")
    test_results = []
    for _, row in df.iterrows():
        tests = run_valuation_tests(row)
        passed_count = sum(1 for t in tests.values() if t["passed"] is True)
        grade = conviction_grade(passed_count)
        test_results.append({
            "tests": tests,
            "testsPassed": passed_count,
            "grade": grade,
        })
    df["valuationTests"] = [tr["tests"] for tr in test_results]
    df["testsPassed"] = [tr["testsPassed"] for tr in test_results]
    df["grade"] = [tr["grade"] for tr in test_results]
    print(f"  Tests complete. Grade distribution: A={sum(1 for g in df['grade'] if g=='A')}, B={sum(1 for g in df['grade'] if g=='B')}, C={sum(1 for g in df['grade'] if g=='C')}, D={sum(1 for g in df['grade'] if g=='D')}, F={sum(1 for g in df['grade'] if g=='F')}")

    # If top_n is set, limit results; otherwise return all scored stocks
    effective_top_n = top_n if top_n else len(df)
    overvalued, undervalued = get_top_stocks(df, top_n=effective_top_n)

    # ── Step 4: Write lightweight index.json ──
    print("\n💾 Step 4: Writing index + detail files...")

    index_overvalued = []
    index_undervalued = []

    def make_index_entry(row):
        return {
            "ticker": row["ticker"],
            "name": row["name"],
            "price": round(float(row["price"]), 2),
            "valuationScore": float(row["valuationScore"]),
            "marketCap": row.get("marketCapFormatted", "—"),
            "sector": row.get("sector", "Unknown"),
            "domain": row.get("domain", ""),
            "testsPassed": int(row.get("testsPassed", 0)),
            "grade": row.get("grade", "F"),
        }

    def make_detail_file(row):
        # Serialize test results (convert Python bools/None for JSON)
        raw_tests = row.get("valuationTests", {})
        serialized_tests = {}
        for key, test in raw_tests.items():
            serialized_tests[key] = {
                "name": test["name"],
                "passed": test["passed"],
                "value": test["value"],
                "threshold": test["threshold"],
                "label": test["label"],
            }

        return {
            "ticker": row["ticker"],
            "name": row["name"],
            "price": round(float(row["price"]), 2),
            "valuationScore": float(row["valuationScore"]),
            "marketCap": row.get("marketCapFormatted", "—"),
            "sector": row.get("sector", "Unknown"),
            "domain": row.get("domain", ""),
            "chartData": row.get("chartData", []),
            "testsPassed": int(row.get("testsPassed", 0)),
            "grade": row.get("grade", "F"),
            "valuationTests": serialized_tests,
            "metrics": {
                "pe": _safe_float(row.get("pe")),
                "sectorPe": _safe_float(row.get("sectorPe")),
                "pb": _safe_float(row.get("pb")),
                "ps": _safe_float(row.get("ps")),
                "evEbitda": _safe_float(row.get("evEbitda")),
                "fcfYield": _safe_float(row.get("fcfYield")),
                "forwardPe": _safe_float(row.get("forwardPe")),
                "dividendYield": _safe_float(row.get("dividendYield")),
                "revenueGrowth": _safe_float(row.get("revenueGrowth")),
                "profitMargin": _safe_float(row.get("profitMargin")),
                "operatingMargin": _safe_float(row.get("operatingMargin")),
                "roe": _safe_float(row.get("roe")),
                "debtEquity": _safe_float(row.get("debtEquity")),
            },
        }

    # Process overvalued
    for _, row in overvalued.iterrows():
        index_overvalued.append(make_index_entry(row))
        detail = make_detail_file(row)
        detail_path = os.path.join(details_dir, f"{row['ticker']}.json")
        with open(detail_path, "w") as f:
            json.dump(detail, f, indent=2, ensure_ascii=False)

    # Process undervalued
    for _, row in undervalued.iterrows():
        index_undervalued.append(make_index_entry(row))
        detail = make_detail_file(row)
        detail_path = os.path.join(details_dir, f"{row['ticker']}.json")
        with open(detail_path, "w") as f:
            json.dump(detail, f, indent=2, ensure_ascii=False)

    # Write lightweight index
    index_data = {
        "lastUpdated": timestamp,
        "marketName": exchange,
        "overvalued": index_overvalued,
        "undervalued": index_undervalued,
    }

    index_path = os.path.join(data_dir, f"{exchange.lower()}_index.json")
    with open(index_path, "w") as f:
        json.dump(index_data, f, indent=2, ensure_ascii=False)
    print(f"  ✓ Index: {index_path} ({len(index_overvalued)} overvalued, {len(index_undervalued)} undervalued)")

    # Also write legacy summary.json for backward compatibility
    legacy_summary = {
        "lastUpdated": timestamp,
        "marketName": exchange,
        "overvalued": [stock_to_summary_dict(row) for _, row in overvalued.iterrows()],
        "undervalued": [stock_to_summary_dict(row) for _, row in undervalued.iterrows()],
    }
    summary_path = os.path.join(data_dir, f"{exchange.lower()}_summary.json")
    with open(summary_path, "w") as f:
        json.dump(legacy_summary, f, indent=2, ensure_ascii=False)

    print(f"  ✓ Details: {len(os.listdir(details_dir))} individual files in {details_dir}")

    # ── Step 5: Write meta.json ──
    meta = {
        "lastUpdated": timestamp,
        "pipelineVersion": "2.0.0",
        "stocksAnalyzed": len(df),
        "stocksOvervalued": len(index_overvalued),
        "stocksUndervalued": len(index_undervalued),
        "dataSource": "yfinance",
        "aiModel": "gemini-2.5-flash",
    }
    meta_path = os.path.join(data_dir, f"{exchange.lower()}_meta.json")
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)
    print(f"  ✓ Meta: {meta_path}")

    # ── Step 6: Generate AI reports ──
    if not skip_reports:
        print("\n🤖 Step 5: Generating AI equity research reports...\n")
        try:
            from generate_reports import setup_gemini, generate_all_reports
            import pandas as pd

            client = setup_gemini()
            report_stocks = pd.concat([overvalued, undervalued], ignore_index=True)
            success = generate_all_reports(client, report_stocks, reports_dir, delay=3.0)
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
    print(f"  Overvalued: {len(index_overvalued)} | Undervalued: {len(index_undervalued)}")
    print(f"  Index: {index_path}")
    print(f"  Details: {details_dir}")
    print("=" * 60)


def _safe_float(val):
    """Convert to float or None."""
    import numpy as np
    if val is None:
        return None
    try:
        f = float(val)
        if np.isnan(f) or np.isinf(f):
            return None
        return round(f, 2)
    except (ValueError, TypeError):
        return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="N Valuations Pipeline v2")
    parser.add_argument("--exchange", type=str, default="ASX",
                        choices=["ASX", "NYSE", "NASDAQ"],
                        help="Exchange to analyze")
    parser.add_argument("--skip-reports", action="store_true",
                        help="Skip AI report generation")
    parser.add_argument("--tickers", nargs="+",
                        help="Specific tickers to analyze (for testing)")
    parser.add_argument("--top-n", type=int, default=None,
                        help="Limit N stocks per category (default: all)")
    parser.add_argument("--limit", type=int, default=None,
                        help="Limit total tickers to discover (for piloting)")
    args = parser.parse_args()

    run_pipeline(
        exchange=args.exchange,
        skip_reports=args.skip_reports,
        top_n=args.top_n,
        limit=args.limit,
        tickers=args.tickers,
    )
