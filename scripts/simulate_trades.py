"""
N Valuations — ASX Trading Engine v2

Simulated hedge fund that trades ASX stocks using valuation models
combined with technical momentum confirmation and dynamic risk management.

Strategy:
  ENTRY — Buy undervalued stocks (mispricing < -30%) ONLY when:
    • Price is above 5-day EMA (short-term uptrend established)
    • Volume is above 20-day average (institutional interest)
    • RSI(14) is between 30-65 (not overbought; recovering from oversold ideal)

  EXIT — Dynamic trailing stop + partial profit-taking:
    • Initial stop: -6% from entry
    • After +5%: trail stop to breakeven
    • After +10%: trail stop to +5%
    • Partial exit: sell 50% at +15% gain, let the rest ride
    • Max hold: 30 trading days (but extended if in profit)

  POSITION SIZING — Conviction-weighted:
    • Base allocation: 8-15% of portfolio per position
    • Max 8 concurrent positions
    • Max 3 positions per sector (diversification)

  STARTING CAPITAL: A$10,000

Usage:
    python scripts/simulate_trades.py            # Normal run
    python scripts/simulate_trades.py --reset     # Fresh start
"""

import json
import os
import sys
import argparse
from datetime import datetime, timezone, timedelta

import yfinance as yf
import numpy as np


# ---------- Configuration ----------
STARTING_CAPITAL = 10_000.00
MAX_POSITIONS = 8
MAX_POSITION_PCT = 0.15        # 15% of portfolio per trade
MAX_SECTOR_POSITIONS = 3       # Max positions per sector
MIN_MISPRICING = -30           # Only buy if mispricing < -30%
INITIAL_STOP_PCT = -0.06       # -6% initial stop loss
BREAKEVEN_TRIGGER = 0.05       # Trail to breakeven after +5%
TRAIL_TRIGGER = 0.10           # Trail to +5% after +10%
TRAIL_LOCK_PCT = 0.05          # Lock in 5% when trailing
PARTIAL_PROFIT_PCT = 0.15      # Take partial profits at +15%
PARTIAL_SELL_RATIO = 0.50      # Sell 50% at partial profit
MAX_HOLD_DAYS = 30             # Max hold for losing positions
MIN_TRADE_VALUE = 200          # Minimum trade in dollars
MIN_VOLUME_RATIO = 1.0         # Volume must be >= average
RSI_MIN = 25                   # Min RSI for entry
RSI_MAX = 65                   # Max RSI for entry


def load_portfolio(path):
    """Load existing portfolio state or create fresh one."""
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return new_portfolio()


def new_portfolio():
    """Create a fresh portfolio."""
    return {
        "startDate": datetime.now(timezone.utc).isoformat(),
        "startingCapital": STARTING_CAPITAL,
        "cash": STARTING_CAPITAL,
        "totalValue": STARTING_CAPITAL,
        "totalPnL": 0.0,
        "totalPnLPct": 0.0,
        "totalTrades": 0,
        "wins": 0,
        "losses": 0,
        "winRate": 0.0,
        "bestTrade": None,
        "worstTrade": None,
        "avgWin": 0.0,
        "avgLoss": 0.0,
        "openPositions": [],
        "tradeHistory": [],
        "equityCurve": [{"date": datetime.now(timezone.utc).isoformat(), "value": STARTING_CAPITAL}],
        "lastUpdated": datetime.now(timezone.utc).isoformat(),
    }


def get_stock_data(ticker, suffix=".AX", period="1mo"):
    """Fetch historical data for a ticker. Returns (hist_df, current_price) or (None, None)."""
    try:
        t = yf.Ticker(f"{ticker}{suffix}")
        hist = t.history(period=period)
        if hist is not None and not hist.empty and len(hist) >= 5:
            return hist, float(hist["Close"].iloc[-1])
    except Exception:
        pass
    return None, None


def calc_rsi(prices, period=14):
    """Calculate RSI from a price series."""
    if len(prices) < period + 1:
        return 50.0  # Default neutral if not enough data

    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)

    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])

    if avg_loss == 0:
        return 100.0

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def calc_ema(prices, period=5):
    """Calculate EMA from a price series. Returns the last EMA value."""
    if len(prices) < period:
        return prices[-1] if len(prices) > 0 else 0
    multiplier = 2 / (period + 1)
    ema = float(prices[0])
    for p in prices[1:]:
        ema = (float(p) - ema) * multiplier + ema
    return ema


def passes_momentum_filter(hist):
    """
    Check if a stock passes the momentum confirmation filter.
    Returns (passes: bool, details: dict)
    """
    closes = hist["Close"].values
    volumes = hist["Volume"].values

    current_price = float(closes[-1])

    # 1. Price above 5-day EMA (short-term uptrend)
    ema5 = calc_ema(closes, 5)
    above_ema = current_price >= ema5 * 0.995  # tiny tolerance

    # 2. Volume above 20-day average
    if len(volumes) >= 20:
        avg_vol = float(np.mean(volumes[-21:-1]))  # exclude today
    else:
        avg_vol = float(np.mean(volumes[:-1])) if len(volumes) > 1 else 0
    
    vol_ratio = float(volumes[-1]) / avg_vol if avg_vol > 0 else 0
    vol_ok = vol_ratio >= MIN_VOLUME_RATIO

    # 3. RSI between 25-65
    rsi = calc_rsi(closes)
    rsi_ok = RSI_MIN <= rsi <= RSI_MAX

    passes = above_ema and vol_ok and rsi_ok

    details = {
        "ema5": round(float(ema5), 2),
        "aboveEma": bool(above_ema),
        "volRatio": round(float(vol_ratio), 2),
        "volOk": bool(vol_ok),
        "rsi": round(float(rsi), 1),
        "rsiOk": bool(rsi_ok),
    }

    return passes, details


def load_candidates(data_dir):
    """Load undervalued ASX stocks with their mispricing % from reports."""
    candidates = []
    index_path = os.path.join(data_dir, "asx_index.json")
    if not os.path.exists(index_path):
        return candidates

    with open(index_path) as f:
        data = json.load(f)

    for stock in data.get("undervalued", []):
        ticker = stock["ticker"]
        report_path = os.path.join(data_dir, "reports", f"{ticker}.json")
        if not os.path.exists(report_path):
            continue

        with open(report_path) as f:
            report = json.load(f)

        verdict = report.get("report", {}).get("verdict", {})
        mispricing = verdict.get("mispricing")
        fair_value = verdict.get("fairValue")

        if mispricing is None or fair_value is None:
            continue

        # Filter by market cap (>$500M)
        mc = stock.get("marketCap", "0")
        val = 0
        if str(mc).endswith("B"):
            val = float(str(mc).replace("B", "")) * 1e9
        elif str(mc).endswith("M"):
            val = float(str(mc).replace("M", "")) * 1e6
        if val < 500_000_000:
            continue

        candidates.append({
            "ticker": ticker,
            "exchange": "ASX",
            "suffix": ".AX",
            "name": stock.get("name", ticker),
            "sector": stock.get("sector", ""),
            "mispricing": float(mispricing),
            "fairValue": float(fair_value),
            "price": stock.get("price", 0),
        })

    # Sort by most undervalued
    candidates.sort(key=lambda c: c["mispricing"])
    return candidates


def get_trailing_stop(pos, current_price):
    """
    Calculate the current trailing stop level for a position.
    Returns the stop price.
    """
    entry_price = pos["entryPrice"]
    pnl_pct = (current_price - entry_price) / entry_price
    
    # Highest price seen (track for trailing)
    highest = max(current_price, pos.get("highestPrice", current_price))

    if pnl_pct >= TRAIL_TRIGGER:
        # After +10%: trail stop to lock in 5% from highest
        stop_price = highest * (1 - (TRAIL_TRIGGER - TRAIL_LOCK_PCT))
        # But never lower than breakeven
        stop_price = max(stop_price, entry_price * 1.001)
    elif pnl_pct >= BREAKEVEN_TRIGGER:
        # After +5%: trail stop to breakeven
        stop_price = entry_price * 1.001  # tiny buffer above breakeven
    else:
        # Below +5%: fixed stop at -6%
        stop_price = entry_price * (1 + INITIAL_STOP_PCT)
    
    return stop_price, highest


def check_exits(portfolio, now):
    """Check open positions for exit conditions."""
    exits = []
    remaining = []

    for pos in portfolio["openPositions"]:
        ticker = pos["ticker"]
        suffix = pos.get("suffix", ".AX")
        hist, current_price = get_stock_data(ticker, suffix, period="5d")

        if current_price is None:
            remaining.append(pos)
            continue

        entry_price = pos["entryPrice"]
        pnl_pct = (current_price - entry_price) / entry_price
        fair_value = pos.get("fairValue", entry_price * 1.15)

        # Track highest price for trailing stop
        highest = max(current_price, pos.get("highestPrice", current_price))
        pos["highestPrice"] = round(highest, 2)

        # Calculate hold duration
        entry_date = datetime.fromisoformat(pos["entryDate"])
        hold_days = (now - entry_date).days

        exit_reason = None
        sell_ratio = 1.0  # Full position by default

        # 1. Trailing stop check
        stop_price, highest = get_trailing_stop(pos, current_price)
        pos["highestPrice"] = round(highest, 2)
        pos["stopPrice"] = round(stop_price, 2)

        if current_price <= stop_price:
            if pnl_pct > 0:
                exit_reason = "TRAILING STOP"
            else:
                exit_reason = "STOP LOSS"

        # 2. Partial profit: sell 50% at +15% (only if not already partialed)
        elif pnl_pct >= PARTIAL_PROFIT_PCT and not pos.get("partialTaken"):
            exit_reason = "PARTIAL PROFIT"
            sell_ratio = PARTIAL_SELL_RATIO

        # 3. Time-based exit (only for losing positions)
        elif hold_days >= MAX_HOLD_DAYS and pnl_pct <= 0:
            exit_reason = "TIME EXIT"

        # 4. Fair value reached — take full profit
        elif current_price >= fair_value * 0.95:
            exit_reason = "TARGET HIT"

        if exit_reason:
            shares_to_sell = int(pos["shares"] * sell_ratio)
            if shares_to_sell < 1:
                shares_to_sell = pos["shares"]
                sell_ratio = 1.0

            remaining_shares = pos["shares"] - shares_to_sell
            pnl = (current_price - entry_price) * shares_to_sell

            trade_record = {
                "ticker": ticker,
                "exchange": "ASX",
                "name": pos.get("name", ticker),
                "side": "SELL",
                "entryPrice": entry_price,
                "exitPrice": round(current_price, 2),
                "shares": shares_to_sell,
                "entryDate": pos["entryDate"],
                "exitDate": now.isoformat(),
                "holdDays": hold_days,
                "invested": round(entry_price * shares_to_sell, 2),
                "returned": round(current_price * shares_to_sell, 2),
                "pnl": round(pnl, 2),
                "pnlPct": round(pnl_pct * 100, 2),
                "exitReason": exit_reason,
            }
            exits.append(trade_record)
            portfolio["cash"] += round(current_price * shares_to_sell, 2)

            print(f"    EXIT  {ticker:8s} @ A${current_price:.2f}  P&L: A${pnl:+.2f} ({pnl_pct*100:+.1f}%)  [{exit_reason}]")

            # If partial exit, keep remaining shares
            if remaining_shares > 0:
                pos["shares"] = remaining_shares
                pos["invested"] = round(entry_price * remaining_shares, 2)
                pos["partialTaken"] = True
                pos["currentPrice"] = round(current_price, 2)
                pos["pnl"] = round((current_price - entry_price) * remaining_shares, 2)
                pos["pnlPct"] = round(pnl_pct * 100, 2)
                remaining.append(pos)
        else:
            # Update current price and tracking
            pos["currentPrice"] = round(current_price, 2)
            pos["pnl"] = round((current_price - entry_price) * pos["shares"], 2)
            pos["pnlPct"] = round(pnl_pct * 100, 2)
            remaining.append(pos)

    portfolio["openPositions"] = remaining
    return exits


def check_entries(portfolio, candidates, now):
    """Look for new entry opportunities with momentum confirmation."""
    entries = []
    open_tickers = {p["ticker"] for p in portfolio["openPositions"]}
    closed_tickers = {t["ticker"] for t in portfolio["tradeHistory"][-30:]}

    # Count positions per sector
    sector_counts = {}
    for p in portfolio["openPositions"]:
        s = p.get("sector", "Unknown")
        sector_counts[s] = sector_counts.get(s, 0) + 1

    available_slots = MAX_POSITIONS - len(portfolio["openPositions"])
    if available_slots <= 0:
        return entries

    for c in candidates:
        if available_slots <= 0:
            break

        ticker = c["ticker"]

        # Skip if already in portfolio or recently closed
        if ticker in open_tickers or ticker in closed_tickers:
            continue

        # Only enter if mispricing is significant
        if c["mispricing"] >= MIN_MISPRICING:
            continue

        # Sector diversification check
        sector = c.get("sector", "Unknown")
        if sector_counts.get(sector, 0) >= MAX_SECTOR_POSITIONS:
            continue

        # Fetch historical data for momentum check
        hist, current_price = get_stock_data(ticker, c["suffix"], period="1mo")
        if hist is None or current_price is None or current_price <= 0:
            continue

        # MOMENTUM FILTER — the key upgrade
        passes, momentum = passes_momentum_filter(hist)
        if not passes:
            reason_parts = []
            if not momentum["aboveEma"]:
                reason_parts.append(f"below EMA5 ({momentum['ema5']})")
            if not momentum["volOk"]:
                reason_parts.append(f"low vol ({momentum['volRatio']}x)")
            if not momentum["rsiOk"]:
                reason_parts.append(f"RSI {momentum['rsi']}")
            print(f"    SKIP  {ticker:8s}  mispricing {c['mispricing']:.0f}%  — {', '.join(reason_parts)}")
            continue

        # Position sizing: proportional to mispricing severity
        conviction = min(abs(c["mispricing"]) / 100, 1.0)
        position_pct = 0.08 + (conviction * 0.07)
        position_value = portfolio["cash"] * min(position_pct, MAX_POSITION_PCT)

        if position_value < MIN_TRADE_VALUE:
            continue

        shares = int(position_value / current_price)
        if shares <= 0:
            continue

        cost = round(current_price * shares, 2)
        if cost > portfolio["cash"]:
            continue

        # Calculate initial stop and target
        stop_price = current_price * (1 + INITIAL_STOP_PCT)
        target_price = c["fairValue"]  # Full fair value as ultimate target

        position = {
            "ticker": ticker,
            "exchange": "ASX",
            "name": c["name"],
            "sector": c.get("sector", ""),
            "suffix": c["suffix"],
            "entryPrice": round(current_price, 2),
            "currentPrice": round(current_price, 2),
            "targetPrice": round(target_price, 2),
            "stopPrice": round(stop_price, 2),
            "highestPrice": round(current_price, 2),
            "fairValue": c["fairValue"],
            "mispricing": c["mispricing"],
            "shares": shares,
            "invested": cost,
            "entryDate": now.isoformat(),
            "pnl": 0.0,
            "pnlPct": 0.0,
            "partialTaken": False,
            "momentum": momentum,
        }

        portfolio["openPositions"].append(position)
        portfolio["cash"] -= cost
        open_tickers.add(ticker)
        sector_counts[sector] = sector_counts.get(sector, 0) + 1
        available_slots -= 1

        entry_record = {
            "ticker": ticker,
            "exchange": "ASX",
            "name": c["name"],
            "sector": c.get("sector", ""),
            "side": "BUY",
            "entryPrice": round(current_price, 2),
            "shares": shares,
            "invested": cost,
            "targetPrice": round(target_price, 2),
            "stopPrice": round(stop_price, 2),
            "mispricing": c["mispricing"],
            "entryDate": now.isoformat(),
            "momentum": momentum,
        }
        entries.append(entry_record)

        print(f"    ENTRY {ticker:8s} @ A${current_price:.2f} x {shares} = A${cost:.2f}  "
              f"[RSI:{momentum['rsi']} Vol:{momentum['volRatio']}x EMA5:{momentum['ema5']}]")

    return entries


def update_stats(portfolio):
    """Recalculate portfolio statistics."""
    positions_value = sum(
        p.get("currentPrice", p["entryPrice"]) * p["shares"]
        for p in portfolio["openPositions"]
    )
    portfolio["totalValue"] = round(portfolio["cash"] + positions_value, 2)
    portfolio["totalPnL"] = round(portfolio["totalValue"] - STARTING_CAPITAL, 2)
    portfolio["totalPnLPct"] = round(
        (portfolio["totalValue"] / STARTING_CAPITAL - 1) * 100, 2
    )

    # Win/loss from completed trades (SELL side)
    completed = [t for t in portfolio["tradeHistory"] if t.get("side") == "SELL"]
    portfolio["totalTrades"] = len(completed)
    portfolio["wins"] = sum(1 for t in completed if t.get("pnl", 0) > 0)
    portfolio["losses"] = sum(1 for t in completed if t.get("pnl", 0) <= 0)
    portfolio["winRate"] = round(
        portfolio["wins"] / max(1, portfolio["totalTrades"]) * 100, 1
    )

    # Best/worst trade
    if completed:
        best = max(completed, key=lambda t: t.get("pnlPct", 0))
        worst = min(completed, key=lambda t: t.get("pnlPct", 0))
        portfolio["bestTrade"] = {"ticker": best["ticker"], "pnlPct": best.get("pnlPct", 0)}
        portfolio["worstTrade"] = {"ticker": worst["ticker"], "pnlPct": worst.get("pnlPct", 0)}

        wins_list = [t["pnl"] for t in completed if t.get("pnl", 0) > 0]
        losses_list = [t["pnl"] for t in completed if t.get("pnl", 0) <= 0]
        portfolio["avgWin"] = round(sum(wins_list) / len(wins_list), 2) if wins_list else 0
        portfolio["avgLoss"] = round(sum(losses_list) / len(losses_list), 2) if losses_list else 0

    portfolio["lastUpdated"] = datetime.now(timezone.utc).isoformat()

    # Equity curve
    curve = portfolio.get("equityCurve", [])
    curve.append({
        "date": datetime.now(timezone.utc).isoformat(),
        "value": portfolio["totalValue"],
    })
    if len(curve) > 200:
        curve = curve[-200:]
    portfolio["equityCurve"] = curve


def main():
    parser = argparse.ArgumentParser(description="Nick Knows Best — ASX Trading Engine v2")
    parser.add_argument("--reset", action="store_true", help="Reset portfolio to A$10,000")
    parser.add_argument("--live", action="store_true",
                        help="Live trading session: scan for entries every 5 min for 30 min")
    parser.add_argument("--maintain", action="store_true",
                        help="Maintain mode: update prices & check exits only, no new entries")
    parser.add_argument("--cycles", type=int, default=30,
                        help="Number of 1-min cycles in live mode (default: 30 = 30 min)")
    args = parser.parse_args()

    # Default to maintain mode if neither flag is set
    if not args.live and not args.maintain and not args.reset:
        args.maintain = True

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(project_root, "public", "data")
    portfolio_path = os.path.join(data_dir, "portfolio.json")

    now = datetime.now(timezone.utc)

    if args.reset or not os.path.exists(portfolio_path):
        portfolio = new_portfolio()
        print("  Portfolio initialized at A$10,000.00")
    else:
        portfolio = load_portfolio(portfolio_path)
        print(f"  Portfolio loaded: A${portfolio['totalValue']:,.2f} ({portfolio['totalPnLPct']:+.1f}%)")

    if args.live:
        # ═══════════════════════════════════════════
        #  LIVE TRADING SESSION — 30 min, 1 min price tracking
        #  Entry scans every 5 min, price updates every 1 min
        # ═══════════════════════════════════════════
        import time as _time

        total_cycles = args.cycles
        cycle_interval = 60  # 1 minute between price checks
        entry_scan_every = 5  # scan for new entries every 5th cycle

        print("\n" + "=" * 60)
        print("  🟢 LIVE TRADING SESSION")
        print(f"  {total_cycles} cycles × 1 min = {total_cycles} min")
        print(f"  Price tracking: every 1 min | Entry scan: every {entry_scan_every} min")
        print(f"  Started: {now.strftime('%Y-%m-%d %H:%M UTC')}")
        print("=" * 60)

        for cycle in range(1, total_cycles + 1):
            cycle_time = datetime.now(timezone.utc)
            is_entry_cycle = (cycle == 1) or (cycle % entry_scan_every == 0)
            marker = "📡" if is_entry_cycle else "📈"
            print(f"\n  {marker} Cycle {cycle}/{total_cycles} ({cycle_time.strftime('%H:%M:%S UTC')})")

            # Always check exits (fast — only open positions)
            exits = check_exits(portfolio, cycle_time)
            for exit_trade in exits:
                portfolio["tradeHistory"].append(exit_trade)
            if exits:
                for e in exits:
                    print(f"    🔴 EXIT {e['ticker']} {e['exitReason']}")

            # Scan for entries only on entry cycles
            if is_entry_cycle:
                print("    Scanning for entries...")
                candidates = load_candidates(data_dir)
                entries = check_entries(portfolio, candidates, cycle_time)
                for entry in entries:
                    portfolio["tradeHistory"].append(entry)

            # Update all open position prices (fast — just price fetch)
            for pos in portfolio["openPositions"]:
                _, price = get_stock_data(pos["ticker"], pos.get("suffix", ".AX"), period="5d")
                if price:
                    pos["currentPrice"] = round(price, 2)
                    pos["pnl"] = round((price - pos["entryPrice"]) * pos["shares"], 2)
                    pos["pnlPct"] = round((price / pos["entryPrice"] - 1) * 100, 2)
                    highest = max(price, pos.get("highestPrice", price))
                    pos["highestPrice"] = round(highest, 2)
                    stop_price, _ = get_trailing_stop(pos, price)
                    pos["stopPrice"] = round(stop_price, 2)

            # Save after every cycle so dashboard stays current
            update_stats(portfolio)
            if len(portfolio["tradeHistory"]) > 100:
                portfolio["tradeHistory"] = portfolio["tradeHistory"][-100:]
            with open(portfolio_path, "w") as f:
                json.dump(portfolio, f, indent=2)

            # Quick status line
            pos_summary = "  ".join(
                f"{p['ticker']}:{p['pnlPct']:+.1f}%"
                for p in portfolio["openPositions"]
            ) or "no positions"
            print(f"    A${portfolio['totalValue']:,.2f} ({portfolio['totalPnLPct']:+.1f}%) | {pos_summary}")

            # Wait before next cycle (skip on last)
            if cycle < total_cycles:
                _time.sleep(cycle_interval)

        print(f"\n{'=' * 60}")
        print(f"  🏁 LIVE SESSION COMPLETE — {total_cycles} cycles")

    else:
        # ═══════════════════════════════════════════
        #  MAINTAIN MODE — prices & exits only
        # ═══════════════════════════════════════════
        print("\n" + "=" * 60)
        print("  🔄 MAINTAIN MODE — no new entries")
        print(f"  Session: {now.strftime('%Y-%m-%d %H:%M UTC')}")
        print("=" * 60)

        # Check exits only
        print("\n  Checking exits...")
        exits = check_exits(portfolio, now)
        for exit_trade in exits:
            portfolio["tradeHistory"].append(exit_trade)
        if not exits:
            print("    No exits triggered")

        # Update open position prices
        print("\n  Updating open positions...")
        for pos in portfolio["openPositions"]:
            _, price = get_stock_data(pos["ticker"], pos.get("suffix", ".AX"), period="5d")
            if price:
                pos["currentPrice"] = round(price, 2)
                pos["pnl"] = round((price - pos["entryPrice"]) * pos["shares"], 2)
                pos["pnlPct"] = round((price / pos["entryPrice"] - 1) * 100, 2)
                highest = max(price, pos.get("highestPrice", price))
                pos["highestPrice"] = round(highest, 2)
                stop_price, _ = get_trailing_stop(pos, price)
                pos["stopPrice"] = round(stop_price, 2)

        # Update stats
        update_stats(portfolio)
        if len(portfolio["tradeHistory"]) > 100:
            portfolio["tradeHistory"] = portfolio["tradeHistory"][-100:]

        # Save
        with open(portfolio_path, "w") as f:
            json.dump(portfolio, f, indent=2)

    # Final summary
    print(f"\n{'=' * 60}")
    print(f"  PORTFOLIO SUMMARY")
    print(f"  Total Value:     A${portfolio['totalValue']:>10,.2f}")
    print(f"  Cash:            A${portfolio['cash']:>10,.2f}")
    print(f"  P&L:             A${portfolio['totalPnL']:>+10,.2f} ({portfolio['totalPnLPct']:+.1f}%)")
    print(f"  Open Positions:  {len(portfolio['openPositions'])}")
    print(f"  Total Trades:    {portfolio['totalTrades']}")
    print(f"  Win Rate:        {portfolio['winRate']:.1f}%")
    if portfolio.get("bestTrade"):
        print(f"  Best Trade:      {portfolio['bestTrade']['ticker']} ({portfolio['bestTrade']['pnlPct']:+.1f}%)")
    if portfolio.get("worstTrade"):
        print(f"  Worst Trade:     {portfolio['worstTrade']['ticker']} ({portfolio['worstTrade']['pnlPct']:+.1f}%)")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()

