"""
Batch AI report generator — reads existing detail files and generates Gemini reports.
Skips stocks that already have reports. Can resume if interrupted.

Usage:
    python scripts/batch_reports.py --exchange ASX
    python scripts/batch_reports.py --exchange NYSE
    python scripts/batch_reports.py --exchange NASDAQ
    python scripts/batch_reports.py --all
"""

import json
import os
import sys
import glob
import time
import argparse
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import format_market_cap, ANALYST_PROMPT
from generate_reports import setup_gemini, generate_report, _now_iso


def batch_generate(exchange, model, delay=2.0):
    """Generate AI reports for all detail files in an exchange."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    details_dir = os.path.join(project_root, "public", "data", exchange.lower(), "details")
    reports_dir = os.path.join(project_root, "public", "data", "reports")
    os.makedirs(reports_dir, exist_ok=True)

    # Find all detail files
    detail_files = sorted(glob.glob(os.path.join(details_dir, "*.json")))

    if not detail_files:
        print(f"  ⚠ No detail files found in {details_dir}")
        return 0

    # Filter out stocks that already have reports
    pending = []
    for f in detail_files:
        ticker = os.path.basename(f).replace(".json", "")
        report_path = os.path.join(reports_dir, f"{ticker}.json")
        if not os.path.exists(report_path):
            pending.append(f)

    print(f"  📊 {exchange}: {len(detail_files)} total, {len(detail_files) - len(pending)} already done, {len(pending)} pending")

    if not pending:
        print(f"  ✅ All {exchange} reports already generated!")
        return 0

    success = 0
    failed = 0

    for i, filepath in enumerate(pending):
        ticker = os.path.basename(filepath).replace(".json", "")

        try:
            with open(filepath, "r") as f:
                detail = json.load(f)

            # Build stock_data dict matching what generate_report expects
            metrics = detail.get("metrics", {})
            stock_data = {
                "ticker": detail["ticker"],
                "name": detail["name"],
                "price": detail["price"],
                "sector": detail.get("sector", "Unknown"),
                "marketCap": None,  # We have formatted only
                "pe": metrics.get("pe"),
                "forwardPe": metrics.get("forwardPe"),
                "pb": metrics.get("pb"),
                "evEbitda": metrics.get("evEbitda"),
                "dividendYield": metrics.get("dividendYield"),
                "revenueGrowth": metrics.get("revenueGrowth"),
                "profitMargin": metrics.get("profitMargin"),
                "operatingMargin": metrics.get("operatingMargin"),
                "roe": metrics.get("roe"),
                "debtEquity": metrics.get("debtEquity"),
                "fcf": None,
                "fcfYield": metrics.get("fcfYield"),
            }

            sector_medians = {
                "sectorPe": metrics.get("sectorPe"),
                "sectorPb": None,
                "sectorEvEbitda": None,
            }

            print(f"  [{i+1}/{len(pending)}] {ticker}...", end=" ", flush=True)
            report = generate_report(model, stock_data, sector_medians)

            if report:
                report_json = {
                    "ticker": detail["ticker"],
                    "name": detail["name"],
                    "price": detail["price"],
                    "sector": detail.get("sector", "Unknown"),
                    "marketCap": detail.get("marketCap", "—"),
                    "valuationScore": detail.get("valuationScore", 0),
                    "generatedAt": _now_iso(),
                    "report": report,
                }

                report_path = os.path.join(reports_dir, f"{ticker}.json")
                with open(report_path, "w") as f:
                    json.dump(report_json, f, indent=2, ensure_ascii=False)

                success += 1
            else:
                failed += 1

        except Exception as e:
            print(f"    ✗ {ticker}: {str(e)[:100]}")
            failed += 1

        time.sleep(delay)

    print(f"\n  {exchange} complete: {success} generated, {failed} failed")
    return success


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch AI Report Generator")
    parser.add_argument("--exchange", type=str, choices=["ASX", "NYSE", "NASDAQ"])
    parser.add_argument("--all", action="store_true", help="Generate for all exchanges")
    parser.add_argument("--delay", type=float, default=2.0, help="Seconds between API calls")
    args = parser.parse_args()

    model = setup_gemini()
    total = 0

    aest = timezone(timedelta(hours=11))
    now = datetime.now(aest)
    print("=" * 60)
    print("  N VALUATIONS — BATCH REPORT GENERATOR")
    print(f"  {now.strftime('%A %d %B %Y, %I:%M %p AEST')}")
    print("=" * 60)

    if args.all:
        for ex in ["ASX", "NYSE", "NASDAQ"]:
            print(f"\n🤖 Generating {ex} reports...\n")
            total += batch_generate(ex, model, delay=args.delay)
    elif args.exchange:
        print(f"\n🤖 Generating {args.exchange} reports...\n")
        total = batch_generate(args.exchange, model, delay=args.delay)
    else:
        print("Specify --exchange or --all")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  ✅ BATCH COMPLETE — {total} reports generated")
    print(f"{'='*60}")
