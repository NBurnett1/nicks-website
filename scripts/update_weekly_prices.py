"""
Nick Knows Best — Price Updater

Updates current prices for all active cycle picks.
Marks cycles as "completed" when the 4-week holding period has passed.

Usage:
    python scripts/update_weekly_prices.py          # Update all active cycles
"""

import json
import os
import sys
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import yfinance as yf

AEST = timezone(timedelta(hours=10))


def update_cycle_prices(cycle_path):
    """Update prices for all picks in a cycle file."""
    with open(cycle_path) as f:
        cycle_data = json.load(f)

    if cycle_data.get("status") == "completed":
        return False  # Skip completed cycles

    now = datetime.now(AEST)
    end_date = datetime.strptime(cycle_data["endDate"], "%Y-%m-%d").replace(tzinfo=AEST)

    # If we're past Saturday after the cycle ended, mark as completed
    if now > end_date + timedelta(days=1):
        cycle_data["status"] = "completed"

    picks = cycle_data.get("picks", [])
    updated = False

    # Stop-loss thresholds
    STOP_LOSS_PCT = -7.0     # Hard stop: exit if down 7% from entry
    TRAILING_STOP_PCT = 5.0  # Trailing: if stock was up 5%+, protect gains at +1%

    alerts = []

    for pick in picks:
        ticker = pick["ticker"]
        try:
            t = yf.Ticker(f"{ticker}.AX")

            if cycle_data["status"] == "completed":
                # Get the final Friday close price
                hist = t.history(
                    start=cycle_data["startDate"],
                    end=(end_date + timedelta(days=1)).strftime("%Y-%m-%d")
                )
                if hist is not None and not hist.empty:
                    pick["weekClosePrice"] = round(float(hist["Close"].iloc[-1]), 2)
                    pick["currentPrice"] = pick["weekClosePrice"]
            else:
                # Get latest price
                hist = t.history(period="5d")
                if hist is not None and not hist.empty:
                    pick["currentPrice"] = round(float(hist["Close"].iloc[-1]), 2)

                    # Track peak price for trailing stop
                    peak = pick.get("peakPrice", pick["entryPrice"])
                    if pick["currentPrice"] > peak:
                        pick["peakPrice"] = pick["currentPrice"]

            # Calculate P&L
            if pick["entryPrice"] > 0:
                pnl = pick["currentPrice"] - pick["entryPrice"]
                pick["pnl"] = round(pnl, 2)
                pick["pnlPct"] = round((pnl / pick["entryPrice"]) * 100, 2)

            # ── Stop-loss checks (only for active cycles) ──
            if cycle_data["status"] != "completed" and not pick.get("stopTriggered"):
                peak = pick.get("peakPrice", pick["entryPrice"])
                peak_pct = ((peak - pick["entryPrice"]) / pick["entryPrice"]) * 100 if pick["entryPrice"] > 0 else 0

                # Hard stop-loss
                if pick["pnlPct"] <= STOP_LOSS_PCT:
                    pick["stopTriggered"] = "STOP_LOSS"
                    pick["stopReason"] = f"Hard stop triggered at {pick['pnlPct']:+.1f}% (limit: {STOP_LOSS_PCT}%)"
                    alerts.append(f"🛑 {ticker} STOP LOSS: {pick['pnlPct']:+.1f}%")

                # Trailing stop: if we were up 5%+, don't let it fall below +1%
                elif peak_pct >= TRAILING_STOP_PCT and pick["pnlPct"] < 1.0:
                    pick["stopTriggered"] = "TRAILING_STOP"
                    pick["stopReason"] = f"Trailing stop: peaked at {peak_pct:+.1f}%, now {pick['pnlPct']:+.1f}%"
                    alerts.append(f"📉 {ticker} TRAILING STOP: peaked {peak_pct:+.1f}%, now {pick['pnlPct']:+.1f}%")

            updated = True
            stop_flag = " ⛔" if pick.get("stopTriggered") else ""
            status_icon = "✓" if pick["pnlPct"] >= 0 else "✗"
            print(f"    {status_icon} {ticker}: A${pick['entryPrice']:.2f} → A${pick['currentPrice']:.2f} ({pick['pnlPct']:+.1f}%){stop_flag}")

        except Exception as e:
            print(f"    ⚠ {ticker}: {e}")

    # Print alerts
    if alerts:
        print(f"\n    {'='*40}")
        print(f"    ⚠ STOP-LOSS ALERTS:")
        for a in alerts:
            print(f"      {a}")
        print(f"    {'='*40}")

    # Update summary
    if picks:
        cycle_data["summary"]["avgPnlPct"] = round(
            sum(p["pnlPct"] for p in picks) / len(picks), 2
        )
        cycle_data["summary"]["winners"] = sum(1 for p in picks if p["pnlPct"] > 0)
        cycle_data["summary"]["losers"] = sum(1 for p in picks if p["pnlPct"] < 0)
        cycle_data["summary"]["flat"] = len(picks) - cycle_data["summary"]["winners"] - cycle_data["summary"]["losers"]
        cycle_data["summary"]["stopsTriggered"] = sum(1 for p in picks if p.get("stopTriggered"))

    if updated:
        with open(cycle_path, "w") as f:
            json.dump(cycle_data, f, indent=2, ensure_ascii=False)

    return updated


def main():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cycles_dir = os.path.join(project_root, "public", "data", "cycles")

    if not os.path.exists(cycles_dir):
        print("❌ No cycles directory found.")
        sys.exit(1)

    print("=" * 60)
    print("  NICK KNOWS BEST — Price Updater")
    print(f"  {datetime.now(AEST).strftime('%A %d %B %Y, %I:%M %p AEST')}")
    print("=" * 60)

    cycle_files = sorted([
        f for f in os.listdir(cycles_dir)
        if f.startswith("cycle") and f.endswith(".json") and f != "index.json" and "_" not in f
    ])

    for cf in cycle_files:
        path = os.path.join(cycles_dir, cf)
        with open(path) as f:
            data = json.load(f)
        status = data.get("status", "?")
        print(f"\n  📅 {cf} ({data.get('dateRange', '?')}) — {status}")

        if status == "completed":
            print("    ⏭ Skipping (completed)")
            continue

        update_cycle_prices(path)

    # Rebuild index
    from generate_weekly_picks import update_cycles_index
    update_cycles_index(cycles_dir)

    # Rebuild portfolio from updated cycle data
    print("\n  📊 Rebuilding portfolio...")
    from weekly_portfolio import rebuild_portfolio
    data_dir = os.path.join(project_root, "public", "data")
    portfolio = rebuild_portfolio(cycles_dir, data_dir)
    pnl_sign = "+" if portfolio["totalPnL"] >= 0 else ""
    print(f"  💰 Portfolio: A${portfolio['totalValue']:,.2f} ({pnl_sign}{portfolio['totalPnLPct']:.1f}%)")

    print("\n" + "=" * 60)
    print("  ✅ PRICE UPDATE COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
