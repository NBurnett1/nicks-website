"""
Nick Knows Best — Monthly Conviction Portfolio Engine

Rebuilds portfolio.json from the cycle picks data.
Strategy: Equal-weight allocation across all picks each cycle.
  - Cycle start: divide capital equally among picks, buy at entryPrice
  - Cycle end (4 weeks later): sell all at cycleClosePrice (or currentPrice if still active)
  - Roll the accumulated capital into the next cycle

This script is idempotent — it reads all cycleN.json files and rebuilds
the entire portfolio from scratch every time.

Usage:
    python scripts/weekly_portfolio.py                    # Rebuild from cycle files
    python scripts/weekly_portfolio.py --starting 10000   # Custom starting capital
"""

import json
import math
import os
import sys
import argparse
from datetime import datetime, timezone, timedelta

AEST = timezone(timedelta(hours=10))
DEFAULT_STARTING_CAPITAL = 10_000.00


def load_cycle_files(cycles_dir):
    """Load all cycleN.json files, sorted by cycle number."""
    cycles = []
    for f in sorted(os.listdir(cycles_dir)):
        if f.startswith("cycle") and f.endswith(".json") and f != "index.json" and "_" not in f:
            path = os.path.join(cycles_dir, f)
            with open(path) as fh:
                data = json.load(fh)
            cycles.append(data)
    cycles.sort(key=lambda c: c.get("cycle", 0))
    return cycles


def simulate_cycle(cycle_data, capital):
    """
    Simulate one cycle of equal-weight conviction holds.

    Returns:
        end_capital: capital after selling all positions
        positions: list of position dicts with P&L details
        is_active: whether this cycle is still active (not yet closed)
    """
    picks = cycle_data.get("picks", [])
    status = cycle_data.get("status", "active")
    is_active = status != "completed"

    if not picks:
        return capital, [], is_active

    # Equal-weight allocation
    num_picks = len(picks)
    allocation_per_pick = capital / num_picks

    positions = []
    total_proceeds = 0.0

    for pick in picks:
        entry_price = pick.get("entryPrice", 0)
        if entry_price <= 0:
            positions.append({
                "ticker": pick.get("ticker", "?"),
                "name": pick.get("name", ""),
                "sector": pick.get("sector", ""),
                "grade": pick.get("grade", "?"),
                "type": pick.get("type", "core"),
                "shares": 0,
                "entryPrice": 0,
                "exitPrice": 0,
                "allocation": round(allocation_per_pick, 2),
                "costBasis": 0,
                "exitValue": round(allocation_per_pick, 2),
                "pnl": 0,
                "pnlPct": 0,
                "cycle": cycle_data.get("cycle", 0),
                "dateRange": cycle_data.get("dateRange", ""),
                "status": "skipped",
            })
            total_proceeds += allocation_per_pick
            continue

        # Buy as many whole shares as we can afford
        shares = math.floor(allocation_per_pick / entry_price)
        if shares <= 0:
            positions.append({
                "ticker": pick.get("ticker", "?"),
                "name": pick.get("name", ""),
                "sector": pick.get("sector", ""),
                "grade": pick.get("grade", "?"),
                "type": pick.get("type", "core"),
                "shares": 0,
                "entryPrice": entry_price,
                "exitPrice": entry_price,
                "allocation": round(allocation_per_pick, 2),
                "costBasis": 0,
                "exitValue": round(allocation_per_pick, 2),
                "pnl": 0,
                "pnlPct": 0,
                "cycle": cycle_data.get("cycle", 0),
                "dateRange": cycle_data.get("dateRange", ""),
                "status": "skipped",
            })
            total_proceeds += allocation_per_pick
            continue

        cost_basis = shares * entry_price
        leftover_cash = allocation_per_pick - cost_basis

        # Determine exit price
        if is_active:
            exit_price = pick.get("currentPrice", entry_price)
            pos_status = "open"
        else:
            exit_price = pick.get("weekClosePrice") or pick.get("currentPrice", entry_price)
            pos_status = "closed"

        exit_value = (shares * exit_price) + leftover_cash
        pnl = exit_value - allocation_per_pick
        pnl_pct = (pnl / allocation_per_pick) * 100 if allocation_per_pick > 0 else 0

        positions.append({
            "ticker": pick.get("ticker", "?"),
            "name": pick.get("name", ""),
            "sector": pick.get("sector", ""),
            "grade": pick.get("grade", "?"),
            "type": pick.get("type", "core"),
            "shares": shares,
            "entryPrice": round(entry_price, 2),
            "exitPrice": round(exit_price, 2),
            "allocation": round(allocation_per_pick, 2),
            "costBasis": round(cost_basis, 2),
            "exitValue": round(exit_value, 2),
            "pnl": round(pnl, 2),
            "pnlPct": round(pnl_pct, 2),
            "cycle": cycle_data.get("cycle", 0),
            "dateRange": cycle_data.get("dateRange", ""),
            "status": pos_status,
        })

        total_proceeds += exit_value

    end_capital = round(total_proceeds, 2)
    return end_capital, positions, is_active


def rebuild_portfolio(cycles_dir, data_dir, starting_capital=DEFAULT_STARTING_CAPITAL):
    """
    Rebuild portfolio.json by simulating all cycles sequentially.
    Returns the portfolio dict.
    """
    cycles = load_cycle_files(cycles_dir)
    if not cycles:
        print("  ⚠ No cycle files found — writing empty portfolio")
        portfolio = _empty_portfolio(starting_capital)
        _write_portfolio(portfolio, data_dir)
        return portfolio

    capital = starting_capital
    all_positions = []
    cycle_returns = []
    equity_curve = [{"date": cycles[0].get("startDate", ""), "value": starting_capital}]
    trade_history = []
    open_positions = []

    total_wins = 0
    total_losses = 0
    total_flat = 0

    for cycle_data in cycles:
        cycle_num = cycle_data.get("cycle", 0)
        cycle_start_capital = capital

        end_capital, positions, is_active = simulate_cycle(cycle_data, capital)

        # Classify positions
        for pos in positions:
            if pos["status"] == "closed":
                trade_history.append(pos)
                if pos["pnl"] > 0:
                    total_wins += 1
                elif pos["pnl"] < 0:
                    total_losses += 1
                else:
                    total_flat += 1
            elif pos["status"] == "open":
                open_positions.append(pos)

        # Cycle return record
        cycle_return_pct = ((end_capital - cycle_start_capital) / cycle_start_capital) * 100 if cycle_start_capital > 0 else 0
        cycle_returns.append({
            "cycle": cycle_num,
            "dateRange": cycle_data.get("dateRange", ""),
            "startCapital": round(cycle_start_capital, 2),
            "endCapital": round(end_capital, 2),
            "returnPct": round(cycle_return_pct, 2),
            "picks": len(positions),
            "status": "active" if is_active else "completed",
        })

        # Equity curve point
        equity_curve.append({
            "date": cycle_data.get("endDate", ""),
            "value": round(end_capital, 2),
        })

        # Roll capital forward (only for completed cycles)
        if not is_active:
            capital = end_capital

    current_value = end_capital

    total_pnl = current_value - starting_capital
    total_pnl_pct = (total_pnl / starting_capital) * 100 if starting_capital > 0 else 0

    total_closed = total_wins + total_losses + total_flat
    win_rate = (total_wins / total_closed) * 100 if total_closed > 0 else 0

    # Best/worst trade
    closed_with_pnl = [t for t in trade_history if t["pnl"] != 0]
    best_trade = None
    worst_trade = None
    if closed_with_pnl:
        best = max(closed_with_pnl, key=lambda t: t["pnlPct"])
        worst = min(closed_with_pnl, key=lambda t: t["pnlPct"])
        best_trade = {"ticker": best["ticker"], "pnlPct": best["pnlPct"], "cycle": best["cycle"]}
        worst_trade = {"ticker": worst["ticker"], "pnlPct": worst["pnlPct"], "cycle": worst["cycle"]}

    # Average win/loss
    wins_list = [t["pnlPct"] for t in trade_history if t["pnl"] > 0]
    losses_list = [t["pnlPct"] for t in trade_history if t["pnl"] < 0]
    avg_win = sum(wins_list) / len(wins_list) if wins_list else 0
    avg_loss = sum(losses_list) / len(losses_list) if losses_list else 0

    portfolio = {
        "strategy": "monthly_conviction",
        "holdWeeks": 4,
        "startDate": cycles[0].get("startDate", ""),
        "startingCapital": starting_capital,
        "totalValue": round(current_value, 2),
        "totalPnL": round(total_pnl, 2),
        "totalPnLPct": round(total_pnl_pct, 2),
        "totalTrades": total_closed,
        "wins": total_wins,
        "losses": total_losses,
        "flat": total_flat,
        "winRate": round(win_rate, 1),
        "bestTrade": best_trade,
        "worstTrade": worst_trade,
        "avgWin": round(avg_win, 2),
        "avgLoss": round(avg_loss, 2),
        "currentCycle": cycles[-1].get("cycle", 0) if cycles else 0,
        "totalCycles": len(cycles),
        "completedCycles": sum(1 for c in cycles if c.get("status") == "completed"),
        "openPositions": open_positions,
        "tradeHistory": trade_history,
        "cycleReturns": cycle_returns,
        "equityCurve": equity_curve,
        "lastUpdated": datetime.now(AEST).isoformat(),
    }

    _write_portfolio(portfolio, data_dir)
    return portfolio


def _empty_portfolio(starting_capital):
    """Create an empty portfolio when no cycles exist."""
    return {
        "strategy": "monthly_conviction",
        "holdWeeks": 4,
        "startDate": datetime.now(AEST).strftime("%Y-%m-%d"),
        "startingCapital": starting_capital,
        "totalValue": starting_capital,
        "totalPnL": 0.0,
        "totalPnLPct": 0.0,
        "totalTrades": 0,
        "wins": 0,
        "losses": 0,
        "flat": 0,
        "winRate": 0.0,
        "bestTrade": None,
        "worstTrade": None,
        "avgWin": 0.0,
        "avgLoss": 0.0,
        "currentCycle": 0,
        "totalCycles": 0,
        "completedCycles": 0,
        "openPositions": [],
        "tradeHistory": [],
        "cycleReturns": [],
        "equityCurve": [],
        "lastUpdated": datetime.now(AEST).isoformat(),
    }


def _write_portfolio(portfolio, data_dir):
    """Write portfolio.json to the data directory."""
    path = os.path.join(data_dir, "portfolio.json")
    with open(path, "w") as f:
        json.dump(portfolio, f, indent=2, ensure_ascii=False)
    print(f"  ✓ Portfolio written: {path}")


def main():
    parser = argparse.ArgumentParser(description="Rebuild monthly conviction portfolio")
    parser.add_argument("--starting", type=float, default=DEFAULT_STARTING_CAPITAL,
                        help=f"Starting capital (default: ${DEFAULT_STARTING_CAPITAL:,.0f})")
    args = parser.parse_args()

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(project_root, "public", "data")
    cycles_dir = os.path.join(data_dir, "cycles")

    print("=" * 60)
    print("  NICK KNOWS BEST — Monthly Conviction Portfolio")
    print(f"  {datetime.now(AEST).strftime('%A %d %B %Y, %I:%M %p AEST')}")
    print("=" * 60)

    portfolio = rebuild_portfolio(cycles_dir, data_dir, starting_capital=args.starting)

    # Print summary
    print(f"\n  💰 Starting Capital:  A${portfolio['startingCapital']:,.2f}")
    print(f"  📊 Current Value:     A${portfolio['totalValue']:,.2f}")
    pnl_sign = "+" if portfolio["totalPnL"] >= 0 else ""
    print(f"  📈 Total P&L:         {pnl_sign}A${portfolio['totalPnL']:,.2f} ({pnl_sign}{portfolio['totalPnLPct']:.1f}%)")
    print(f"  🏆 Win Rate:          {portfolio['winRate']:.0f}% ({portfolio['wins']}W / {portfolio['losses']}L / {portfolio['flat']}F)")
    print(f"  📅 Cycles:            {portfolio['completedCycles']} completed, {portfolio['totalCycles']} total")

    if portfolio.get("openPositions"):
        print(f"\n  🟢 Active Positions ({len(portfolio['openPositions'])}):‎")
        for pos in portfolio["openPositions"]:
            sign = "+" if pos["pnlPct"] >= 0 else ""
            icon = "✓" if pos["pnlPct"] >= 0 else "✗"
            print(f"     {icon} {pos['ticker']:<6} {pos['shares']} shares @ A${pos['entryPrice']:.2f}"
                  f" → A${pos['exitPrice']:.2f} ({sign}{pos['pnlPct']:.1f}%)"
                  f" | A${pos['allocation']:,.0f} allocated")

    if portfolio.get("cycleReturns"):
        print(f"\n  📋 Cycle Returns:")
        for cr in portfolio["cycleReturns"]:
            sign = "+" if cr["returnPct"] >= 0 else ""
            status = "🔴" if cr["returnPct"] < 0 else "🟢" if cr["returnPct"] > 0 else "⚪"
            active = " ← active" if cr["status"] == "active" else ""
            print(f"     {status} Cycle {cr['cycle']}: A${cr['startCapital']:,.2f} → A${cr['endCapital']:,.2f}"
                  f" ({sign}{cr['returnPct']:.1f}%) [{cr['picks']} picks]{active}")

    print("\n" + "=" * 60)
    print("  ✅ PORTFOLIO REBUILD COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
