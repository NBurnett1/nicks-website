"""
Nick Knows Best — Weekly Picks Generator

Selects 5 ASX stocks each week:
  • 4 "Core" picks — Grade A/B, sector-diversified, $500M+ market cap
  • 1 "Speculative" pick — small/micro-cap with high conviction score + volume surge

Usage:
    python scripts/generate_weekly_picks.py                     # Auto-detect week number
    python scripts/generate_weekly_picks.py --week 2            # Force week number
    python scripts/generate_weekly_picks.py --week 1 --backfill # Backfill with Mon open prices
"""

import json
import os
import sys
import argparse
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import yfinance as yf


# ── Configuration ──
CORE_PICKS = 4
SPEC_PICKS = 1
MIN_MARKET_CAP_CORE = 500_000_000      # $500M for core picks
MAX_MARKET_CAP_SPEC = 500_000_000      # <$500M for speculative
MIN_MARKET_CAP_SPEC = 30_000_000       # >$30M floor (not total junk)
VOLUME_SURGE_THRESHOLD = 1.5           # 1.5x 20-day avg volume
AEST = timezone(timedelta(hours=10))

# Week 1 start date (Monday 14 April 2026)
EPOCH_START = datetime(2026, 4, 14, tzinfo=AEST)


def parse_market_cap(mc_str):
    """Parse market cap string like '6.9B' or '544M' to float."""
    if not mc_str or mc_str == "—":
        return 0
    mc = str(mc_str).strip()
    try:
        if mc.endswith("T"):
            return float(mc[:-1]) * 1e12
        elif mc.endswith("B"):
            return float(mc[:-1]) * 1e9
        elif mc.endswith("M"):
            return float(mc[:-1]) * 1e6
        else:
            return float(mc)
    except ValueError:
        return 0


def calculate_week_number(now=None):
    """Calculate current week number from epoch start."""
    if now is None:
        now = datetime.now(AEST)
    delta = now - EPOCH_START
    return max(1, delta.days // 7 + 1)


def get_week_dates(week_num):
    """Get the Monday–Friday date range for a given week number."""
    monday = EPOCH_START + timedelta(weeks=week_num - 1)
    friday = monday + timedelta(days=4)
    return monday, friday


def generate_thesis(stock, detail):
    """Generate a brief investment thesis for a pick."""
    ticker = stock["ticker"]
    grade = stock.get("grade", "?")
    tests = stock.get("testsPassed", 0)
    sector = stock.get("sector", "Unknown")
    score = abs(stock.get("valuationScore", 0))

    parts = []

    # Grade summary
    if tests == 6:
        parts.append("Perfect 6/6 valuation test score")
    elif tests >= 5:
        parts.append(f"Strong {tests}/6 valuation tests passed")
    elif tests >= 4:
        parts.append(f"Solid {tests}/6 valuation tests passed")
    else:
        parts.append(f"{tests}/6 valuation tests flagged")

    # Key metric highlights from detail
    if detail:
        metrics = detail.get("metrics", {})
        vt = detail.get("valuationTests", {})

        if vt.get("peDiscount", {}).get("passed"):
            parts.append("trading at a P/E discount to sector")
        if vt.get("fcfYieldStrong", {}).get("passed"):
            fcf_val = vt["fcfYieldStrong"].get("value", 0)
            parts.append(f"strong {fcf_val:.1f}% FCF yield" if fcf_val else "strong free cash flow yield")
        if vt.get("forwardPeRerate", {}).get("passed"):
            parts.append("forward P/E re-rating expected")
        if vt.get("pbBelowBook", {}).get("passed"):
            parts.append("trading below book value")
        if vt.get("evEbitdaCheap", {}).get("passed"):
            ev_val = vt["evEbitdaCheap"].get("value", 0)
            parts.append(f"cheap EV/EBITDA of {ev_val:.1f}x" if ev_val else "cheap EV/EBITDA")

    # Sector context
    parts.append(f"{sector} sector")

    # Combine
    thesis = ". ".join(parts[:4]) + "."
    return thesis


def select_core_picks(index_data, details_dir, exclude_tickers=None):
    """Select top 4 core picks: Grade A/B, sector-diversified, $500M+ market cap."""
    exclude_tickers = exclude_tickers or set()
    undervalued = index_data.get("undervalued", [])

    # Filter and sort by conviction
    grade_order = {"A": 5, "B": 4, "C": 3, "D": 2, "F": 1}
    candidates = []
    for s in undervalued:
        if s["ticker"] in exclude_tickers:
            continue
        grade = s.get("grade", "F")
        if grade not in ("A", "B"):
            continue
        mc = parse_market_cap(s.get("marketCap", "0"))
        if mc < MIN_MARKET_CAP_CORE:
            continue
        candidates.append(s)

    candidates.sort(key=lambda x: (
        -grade_order.get(x.get("grade", "F"), 0),
        -x.get("testsPassed", 0),
        x.get("valuationScore", 0),   # More negative = more undervalued
    ))

    # Sector diversification — max 1 per sector
    selected = []
    sectors_used = set()
    for c in candidates:
        sector = c.get("sector", "Unknown")
        if sector in sectors_used and len(selected) < CORE_PICKS:
            continue
        selected.append(c)
        sectors_used.add(sector)
        if len(selected) >= CORE_PICKS:
            break

    # If we didn't get enough with diversification, relax constraint
    if len(selected) < CORE_PICKS:
        for c in candidates:
            if c not in selected:
                selected.append(c)
                if len(selected) >= CORE_PICKS:
                    break

    # Load details for thesis generation
    picks = []
    for rank, stock in enumerate(selected[:CORE_PICKS], 1):
        detail = _load_detail(details_dir, stock["ticker"])
        picks.append({
            "rank": rank,
            "ticker": stock["ticker"],
            "name": stock.get("name", stock["ticker"]),
            "sector": stock.get("sector", "Unknown"),
            "grade": stock.get("grade", "?"),
            "testsPassed": stock.get("testsPassed", 0),
            "entryPrice": stock.get("price", 0),
            "currentPrice": stock.get("price", 0),
            "weekClosePrice": None,
            "pnl": 0.0,
            "pnlPct": 0.0,
            "marketCap": stock.get("marketCap", "—"),
            "thesis": generate_thesis(stock, detail),
            "type": "core",
        })

    return picks


def select_speculative_pick(index_data, details_dir, exclude_tickers=None):
    """
    Select 1 speculative penny/micro-cap pick.
    Criteria: <$500M market cap, Grade C+ (at least some tests passed),
    high volume relative to average, interesting sector.
    """
    exclude_tickers = exclude_tickers or set()
    undervalued = index_data.get("undervalued", [])

    candidates = []
    for s in undervalued:
        if s["ticker"] in exclude_tickers:
            continue
        mc = parse_market_cap(s.get("marketCap", "0"))
        if mc >= MAX_MARKET_CAP_SPEC or mc < MIN_MARKET_CAP_SPEC:
            continue
        grade = s.get("grade", "F")
        if grade == "F":
            continue
        tests = s.get("testsPassed", 0)
        if tests < 2:
            continue
        candidates.append(s)

    if not candidates:
        # Fallback: pick the smallest-cap Grade A/B stock
        grade_order = {"A": 5, "B": 4, "C": 3, "D": 2, "F": 1}
        all_under = [s for s in undervalued if s.get("grade", "F") in ("A", "B", "C")]
        all_under.sort(key=lambda x: parse_market_cap(x.get("marketCap", "0")))
        if all_under:
            candidates = [all_under[0]]

    if not candidates:
        return None

    # Score candidates: prioritize tests passed + deeper discount
    candidates.sort(key=lambda x: (
        -x.get("testsPassed", 0),
        x.get("valuationScore", 0),
    ))

    # Check volume surge for top candidates
    best = None
    for c in candidates[:10]:
        ticker = c["ticker"]
        try:
            t = yf.Ticker(f"{ticker}.AX")
            hist = t.history(period="1mo")
            if hist is not None and not hist.empty and len(hist) >= 5:
                recent_vol = float(hist["Volume"].iloc[-1])
                avg_vol = float(hist["Volume"].iloc[:-1].mean()) if len(hist) > 1 else 1
                vol_ratio = recent_vol / avg_vol if avg_vol > 0 else 0
                c["_volRatio"] = round(vol_ratio, 2)
                if best is None or c.get("testsPassed", 0) > best.get("testsPassed", 0):
                    best = c
                # Volume surge is a bonus, not a requirement
                if vol_ratio >= VOLUME_SURGE_THRESHOLD and best is not None:
                    if c.get("testsPassed", 0) >= best.get("testsPassed", 0):
                        best = c
        except Exception:
            if best is None:
                best = c

    if best is None:
        best = candidates[0]

    detail = _load_detail(details_dir, best["ticker"])
    vol_note = ""
    if best.get("_volRatio", 0) >= VOLUME_SURGE_THRESHOLD:
        vol_note = f" Volume surge detected ({best['_volRatio']:.1f}x avg)."

    thesis = generate_thesis(best, detail)
    thesis = thesis.rstrip(".") + f". Micro-cap speculative play ({best.get('marketCap', '?')}).{vol_note}"

    return {
        "rank": CORE_PICKS + 1,
        "ticker": best["ticker"],
        "name": best.get("name", best["ticker"]),
        "sector": best.get("sector", "Unknown"),
        "grade": best.get("grade", "?"),
        "testsPassed": best.get("testsPassed", 0),
        "entryPrice": best.get("price", 0),
        "currentPrice": best.get("price", 0),
        "weekClosePrice": None,
        "pnl": 0.0,
        "pnlPct": 0.0,
        "marketCap": best.get("marketCap", "—"),
        "thesis": thesis,
        "type": "speculative",
    }


def backfill_monday_open(picks, date):
    """Attempt to get the Monday open price for backfilling historical weeks."""
    for pick in picks:
        ticker = pick["ticker"]
        try:
            t = yf.Ticker(f"{ticker}.AX")
            hist = t.history(start=date.strftime("%Y-%m-%d"),
                           end=(date + timedelta(days=5)).strftime("%Y-%m-%d"))
            if hist is not None and not hist.empty:
                pick["entryPrice"] = round(float(hist["Open"].iloc[0]), 2)
                pick["currentPrice"] = round(float(hist["Close"].iloc[-1]), 2)
                pnl = pick["currentPrice"] - pick["entryPrice"]
                pick["pnl"] = round(pnl, 2)
                pick["pnlPct"] = round((pnl / pick["entryPrice"]) * 100, 2) if pick["entryPrice"] > 0 else 0
        except Exception as e:
            print(f"    ⚠ Backfill failed for {ticker}: {e}")


def load_previous_picks(weeks_dir, current_week_num):
    """Load all tickers that were picked in previous weeks to avoid repeats."""
    used = set()
    for w in range(1, current_week_num):
        path = os.path.join(weeks_dir, f"week{w}.json")
        if os.path.exists(path):
            with open(path) as f:
                data = json.load(f)
            for pick in data.get("picks", []):
                used.add(pick["ticker"])
    return used


def generate_week(week_num, index_data, details_dir, weeks_dir, backfill=False):
    """Generate a complete week JSON."""
    monday, friday = get_week_dates(week_num)
    now = datetime.now(AEST)

    # Determine status
    if now < monday:
        status = "upcoming"
    elif now > friday + timedelta(days=2):  # Saturday after week ends
        status = "completed"
    else:
        status = "active"

    print(f"\n  📅 Week {week_num}: {monday.strftime('%d %b')} – {friday.strftime('%d %b %Y')}")
    print(f"     Status: {status}")

    # Load previously picked tickers to exclude repeats
    exclude = load_previous_picks(weeks_dir, week_num)
    if exclude:
        print(f"     Excluding {len(exclude)} previously picked tickers: {', '.join(sorted(exclude))}")

    # Select picks
    core = select_core_picks(index_data, details_dir, exclude_tickers=exclude)
    spec = select_speculative_pick(index_data, details_dir, exclude_tickers=exclude | {p['ticker'] for p in core})

    picks = core
    if spec:
        picks.append(spec)
    else:
        print("  ⚠ No speculative pick found")

    # Backfill with actual Monday open prices if requested
    if backfill and monday < now:
        print(f"  🔄 Backfilling prices from {monday.strftime('%Y-%m-%d')}...")
        backfill_monday_open(picks, monday)

    # Calculate summary
    total_pnl = sum(p["pnl"] for p in picks)
    avg_pnl_pct = sum(p["pnlPct"] for p in picks) / len(picks) if picks else 0
    winners = sum(1 for p in picks if p["pnlPct"] > 0)
    losers = sum(1 for p in picks if p["pnlPct"] < 0)

    week_data = {
        "week": week_num,
        "dateRange": f"{monday.strftime('%d %b')} – {friday.strftime('%d %b %Y')}",
        "startDate": monday.strftime("%Y-%m-%d"),
        "endDate": friday.strftime("%Y-%m-%d"),
        "status": status,
        "picks": picks,
        "summary": {
            "avgPnlPct": round(avg_pnl_pct, 2),
            "winners": winners,
            "losers": losers,
            "flat": len(picks) - winners - losers,
        },
    }

    # Print picks
    for p in picks:
        tag = "🔥 SPEC" if p["type"] == "speculative" else f"  #{p['rank']}"
        pnl_str = f"{p['pnlPct']:+.1f}%" if p["pnlPct"] != 0 else "—"
        print(f"    {tag} {p['ticker']:<6} Grade {p['grade']} ({p['testsPassed']}/6) | "
              f"A${p['entryPrice']:.2f} → A${p['currentPrice']:.2f} ({pnl_str})")

    return week_data


def update_weeks_index(weeks_dir):
    """Rebuild the weeks index.json from all weekN.json files."""
    weeks = []
    for f in sorted(os.listdir(weeks_dir)):
        if f.startswith("week") and f.endswith(".json") and f != "index.json":
            path = os.path.join(weeks_dir, f)
            with open(path) as fh:
                data = json.load(fh)
            weeks.append({
                "week": data["week"],
                "dateRange": data["dateRange"],
                "startDate": data["startDate"],
                "endDate": data["endDate"],
                "status": data["status"],
                "avgPnlPct": data["summary"]["avgPnlPct"],
                "winners": data["summary"]["winners"],
                "losers": data["summary"]["losers"],
            })

    weeks.sort(key=lambda w: w["week"])
    current = max((w["week"] for w in weeks if w["status"] == "active"), default=weeks[-1]["week"] if weeks else 1)

    index = {
        "currentWeek": current,
        "totalWeeks": len(weeks),
        "weeks": weeks,
    }

    index_path = os.path.join(weeks_dir, "index.json")
    with open(index_path, "w") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)
    print(f"\n  ✓ Index updated: {len(weeks)} weeks, current = Week {current}")


def _load_detail(details_dir, ticker):
    """Load a stock detail JSON file."""
    path = os.path.join(details_dir, f"{ticker}.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None


def main():
    parser = argparse.ArgumentParser(description="Generate weekly stock picks")
    parser.add_argument("--week", type=int, default=None, help="Week number (auto if omitted)")
    parser.add_argument("--backfill", action="store_true", help="Backfill actual open prices for past weeks")
    parser.add_argument("--all", action="store_true", help="Generate all weeks up to current")
    args = parser.parse_args()

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(project_root, "public", "data")
    weeks_dir = os.path.join(data_dir, "weeks")
    details_dir = os.path.join(data_dir, "asx", "details")
    os.makedirs(weeks_dir, exist_ok=True)

    # Load index data
    index_path = os.path.join(data_dir, "asx_index.json")
    if not os.path.exists(index_path):
        print("❌ No asx_index.json found. Run the pipeline first.")
        sys.exit(1)

    with open(index_path) as f:
        index_data = json.load(f)

    print("=" * 60)
    print("  NICK KNOWS BEST — Weekly Picks Generator")
    print("=" * 60)

    now = datetime.now(AEST)
    current_week = calculate_week_number(now)

    if args.all:
        # Generate all weeks from 1 to current
        for w in range(1, current_week + 1):
            week_data = generate_week(w, index_data, details_dir, weeks_dir, backfill=True)
            week_path = os.path.join(weeks_dir, f"week{w}.json")
            with open(week_path, "w") as f:
                json.dump(week_data, f, indent=2, ensure_ascii=False)
            print(f"  ✓ Saved {week_path}")
    else:
        week_num = args.week or current_week
        week_data = generate_week(week_num, index_data, details_dir, weeks_dir, backfill=args.backfill)
        week_path = os.path.join(weeks_dir, f"week{week_num}.json")
        with open(week_path, "w") as f:
            json.dump(week_data, f, indent=2, ensure_ascii=False)
        print(f"\n  ✓ Saved {week_path}")

    update_weeks_index(weeks_dir)

    print("\n" + "=" * 60)
    print("  ✅ WEEKLY PICKS GENERATED")
    print("=" * 60)


if __name__ == "__main__":
    main()
