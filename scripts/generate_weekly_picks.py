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
import time
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import yfinance as yf
from macro_scanner import get_macro_biases, apply_macro_bias, save_macro_context, _find_sector_bias, _bias_label


# ── Configuration ──
CORE_PICKS = 4
SPEC_PICKS = 1
MIN_MARKET_CAP_CORE = 500_000_000      # $500M for core picks
MAX_MARKET_CAP_SPEC = 500_000_000      # <$500M for speculative
MIN_MARKET_CAP_SPEC = 30_000_000       # >$30M floor (not total junk)
VOLUME_SURGE_THRESHOLD = 1.5           # 1.5x 20-day avg volume
AEST = timezone(timedelta(hours=10))

# Week 1 start date (Monday 13 April 2026)
EPOCH_START = datetime(2026, 4, 13, tzinfo=AEST)


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


# ── Qualitative Screening (Deep Dive + Short Report) ──
# Uses Gemini to assess business quality, asymmetry, and bear case risks
# for candidate picks before they go live.

def _get_gemini_client():
    """Get a Gemini client, or None if unavailable."""
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        return None
    try:
        from google import genai
        return genai.Client(api_key=key)
    except ImportError:
        return None


def qualify_picks(picks, details_dir, sector_biases=None):
    """
    Run qualitative screening on candidate picks using Gemini.
    Combines Deep Dive (business model, moat, catalyst, asymmetry)
    and Short Report (bear case) into a single prompt per stock.

    Returns picks with added 'qualScore' and 'qualReasoning' fields.
    Picks that fail the bear case kill switch are marked for rejection.
    Falls back gracefully when API is unavailable.
    """
    client = _get_gemini_client()
    if client is None:
        print("  ⚠ Gemini API unavailable — skipping qualitative screening")
        for p in picks:
            p["qualScore"] = None
            p["qualReasoning"] = "Qualitative screening skipped (no API)"
            p["qualPassed"] = True  # Don't reject without evidence
        return picks

    print(f"  🧠 Running qualitative screening on {len(picks)} candidates...")
    screened = []

    for p in picks:
        ticker = p["ticker"]
        name = p.get("name", ticker)
        sector = p.get("sector", "Unknown")
        grade = p.get("grade", "?")
        tests = p.get("testsPassed", 0)
        mcap = p.get("marketCap", "?")
        price = p.get("entryPrice", 0)
        pick_type = p.get("type", "core")
        macro_label = p.get("macroLabel", "Neutral")

        # Load detail metrics if available
        detail = _load_detail(details_dir, ticker)
        metrics_context = ""
        if detail:
            m = detail.get("metrics", {})
            metrics_context = f"""
    Financial Metrics:
    - P/E: {m.get('pe', 'N/A')}, Forward P/E: {m.get('forwardPe', 'N/A')}
    - P/B: {m.get('pb', 'N/A')}, EV/EBITDA: {m.get('evEbitda', 'N/A')}
    - FCF Yield: {m.get('fcfYield', 'N/A')}%, Revenue Growth: {m.get('revenueGrowth', 'N/A')}%
    - Profit Margin: {m.get('profitMargin', 'N/A')}%, ROE: {m.get('roe', 'N/A')}%
    - Debt/Equity: {m.get('debtEquity', 'N/A')}%"""

        bias = _find_sector_bias(sector, sector_biases or {})
        bias_label = _bias_label(bias)

        prompt = f"""You are a senior equity analyst performing due diligence on an ASX stock pick.

Stock: {name} ({ticker}.AX)
Sector: {sector} | Market Cap: {mcap} | Price: A${price:.2f}
Valuation Grade: {grade} ({tests}/7 tests passed)
Pick Type: {pick_type} | Macro Bias: {bias_label} ({bias:+.1f})
{metrics_context}

Perform TWO analyses and return a JSON object:

1. DEEP DIVE — Assess:
   - Business Model: How does this company make money? Is it simple to understand?
   - Moat: Does it have any competitive advantage (brand, patents, switching costs, network effects)?
   - Catalyst: Any upcoming events in the next 3-6 months that could move the stock?
   - Asymmetry: Is the downside limited (asset floor, cash backing) while upside is meaningful?

2. SHORT REPORT (bear case) — As a skeptic, identify:
   - The #1 risk that could cause a 20%+ drawdown
   - Any customer concentration, accounting concerns, or competitive threats
   - Whether the "cheapness" is a value trap (cheap for a reason)

Return ONLY this JSON (no markdown):
{{
  "businessModel": "1-2 sentence plain English description",
  "moatStrength": "none|weak|moderate|strong",
  "catalyst": "Specific upcoming catalyst or 'none identified'",
  "asymmetry": "favorable|neutral|unfavorable",
  "bearCase": "The strongest bear case in 1-2 sentences",
  "bearSeverity": "low|medium|high|critical",
  "conviction": 1-10,
  "recommendation": "pass|reject",
  "reasoning": "1-2 sentence summary of why to pick or reject"
}}"""

        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            text = response.text.strip()

            # Clean markdown fences
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
            if text.endswith("```"):
                text = text.rsplit("```", 1)[0]
            text = text.strip()

            result = json.loads(text)
            conviction = result.get("conviction", 5)
            recommendation = result.get("recommendation", "pass")
            bear_severity = result.get("bearSeverity", "medium")
            asymmetry = result.get("asymmetry", "neutral")

            p["qualScore"] = conviction
            p["qualReasoning"] = result.get("reasoning", "")
            p["qualDetail"] = {
                "businessModel": result.get("businessModel", ""),
                "moatStrength": result.get("moatStrength", "unknown"),
                "catalyst": result.get("catalyst", ""),
                "asymmetry": asymmetry,
                "bearCase": result.get("bearCase", ""),
                "bearSeverity": bear_severity,
            }

            # Kill switch: reject if bear case is critical, or if recommendation is reject
            # AND asymmetry is unfavorable
            if recommendation == "reject" and (bear_severity in ("critical", "high") or asymmetry == "unfavorable"):
                p["qualPassed"] = False
                icon = "❌"
            else:
                p["qualPassed"] = True
                icon = "✅"

            print(f"    {icon} {ticker}: conviction={conviction}/10, "
                  f"moat={result.get('moatStrength', '?')}, "
                  f"asymmetry={asymmetry}, "
                  f"bear={bear_severity} → {recommendation}")

        except Exception as e:
            print(f"    ⚠ {ticker}: Screening failed ({str(e)[:80]}) — keeping pick")
            p["qualScore"] = None
            p["qualReasoning"] = f"Screening error: {str(e)[:100]}"
            p["qualPassed"] = True  # Don't reject on API errors

        # Gentle rate limit
        time.sleep(2)

    return picks


def select_core_picks(index_data, details_dir, exclude_tickers=None, sector_biases=None):
    """Select top 4 core picks: Grade A/B, sector-diversified, $500M+ market cap.
    Now uses macro sector biases to rank stocks by combined valuation + macro score."""
    exclude_tickers = exclude_tickers or set()
    sector_biases = sector_biases or {}
    undervalued = index_data.get("undervalued", [])

    # Filter candidates
    grade_base = {"A": 5, "B": 4, "C": 3, "D": 2, "F": 1}
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

        # Skip stocks in strongly headwind sectors (bias < -0.5)
        sector = s.get("sector", "Unknown")
        bias = _find_sector_bias(sector, sector_biases)
        if bias <= -0.5 and grade != "A":
            print(f"    ⛔ Skipping {s['ticker']} — {sector} has strong headwind ({bias:+.1f})")
            continue

        # Compute combined score: valuation conviction + macro bias
        val_score = grade_base.get(grade, 0) + (s.get("testsPassed", 0) * 0.5)
        macro_boost = bias * 3.0  # Scale macro bias to be meaningful
        combined = val_score + macro_boost
        s["_combinedScore"] = round(combined, 2)
        s["_macroBias"] = round(bias, 2)
        candidates.append(s)

    # Sort by combined score (valuation + macro), not just valuation
    candidates.sort(key=lambda x: -x.get("_combinedScore", 0))

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
        bias = stock.get("_macroBias", 0)
        macro_label = _bias_label(bias)
        thesis = generate_thesis(stock, detail)
        if bias != 0:
            thesis = thesis.rstrip(".") + f". Macro: {macro_label} for {stock.get('sector', 'sector')}."
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
            "thesis": thesis,
            "type": "core",
            "macroBias": bias,
            "macroLabel": macro_label,
        })

    return picks


def select_speculative_pick(index_data, details_dir, exclude_tickers=None, sector_biases=None):
    """
    Select 1 speculative penny/micro-cap pick.
    Criteria: <$500M market cap, Grade C+ (at least some tests passed),
    high volume relative to average, macro-aligned sector preferred.
    """
    exclude_tickers = exclude_tickers or set()
    sector_biases = sector_biases or {}
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

    # Score candidates: prioritize tests passed + deeper discount + macro tailwind
    for c in candidates:
        bias = _find_sector_bias(c.get("sector", ""), sector_biases)
        c["_specMacro"] = bias
    candidates.sort(key=lambda x: (
        -x.get("_specMacro", 0),  # Macro-aligned sectors first
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
    spec_bias = _find_sector_bias(best.get("sector", ""), sector_biases)
    macro_note = f" Macro: {_bias_label(spec_bias)}." if spec_bias != 0 else ""
    thesis = thesis.rstrip(".") + f". Micro-cap speculative play ({best.get('marketCap', '?')}).{vol_note}{macro_note}"

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
        "macroBias": round(_find_sector_bias(best.get("sector", ""), sector_biases), 2),
        "macroLabel": _bias_label(_find_sector_bias(best.get("sector", ""), sector_biases)),
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
    """Generate a complete week JSON with macro/geopolitical overlay."""
    monday, friday = get_week_dates(week_num)
    now = datetime.now(AEST)

    # Determine status
    # Sunday before the week starts counts as active (picks are published)
    if now < monday - timedelta(days=1):
        status = "upcoming"
    elif now > friday + timedelta(days=1):  # Saturday after week ends
        status = "completed"
    else:
        status = "active"

    print(f"\n  📅 Week {week_num}: {monday.strftime('%d %b')} – {friday.strftime('%d %b %Y')}")
    print(f"     Status: {status}")

    # ── MACRO SCAN: Get geopolitical/news sector biases ──
    print(f"  🌍 Running macro/geopolitical scan...")
    sector_biases, macro_context = get_macro_biases()
    print(f"     Headline: {macro_context.get('headline', 'N/A')}")
    print(f"     Source: {macro_context.get('source', 'unknown')}")
    if macro_context.get('themes'):
        for theme in macro_context['themes'][:3]:
            print(f"     • {theme}")
    # Print sector biases
    favored = {k: v for k, v in sector_biases.items() if v >= 0.3}
    avoided = {k: v for k, v in sector_biases.items() if v <= -0.3}
    if favored:
        print(f"     ✅ Favored: {', '.join(f'{k} ({v:+.1f})' for k, v in sorted(favored.items(), key=lambda x: -x[1]))}")
    if avoided:
        print(f"     ❌ Avoided: {', '.join(f'{k} ({v:+.1f})' for k, v in sorted(avoided.items(), key=lambda x: x[1]))}")

    # Save macro context alongside week data
    save_macro_context(weeks_dir, week_num, macro_context, sector_biases)

    # Load previously picked tickers to exclude repeats
    exclude = load_previous_picks(weeks_dir, week_num)
    if exclude:
        print(f"     Excluding {len(exclude)} previously picked tickers: {', '.join(sorted(exclude))}")

    # Select picks with macro overlay
    core = select_core_picks(index_data, details_dir, exclude_tickers=exclude, sector_biases=sector_biases)
    spec = select_speculative_pick(index_data, details_dir, exclude_tickers=exclude | {p['ticker'] for p in core}, sector_biases=sector_biases)

    picks = core
    if spec:
        picks.append(spec)
    else:
        print("  ⚠ No speculative pick found")

    # ── QUALITATIVE SCREENING: Deep Dive + Short Report ──
    # Run Gemini-powered assessment on each pick to check business quality,
    # asymmetry, and bear case severity. Reject picks that fail.
    picks = qualify_picks(picks, details_dir, sector_biases=sector_biases)

    # Remove rejected picks and log
    rejected = [p for p in picks if not p.get("qualPassed", True)]
    if rejected:
        print(f"  🚫 Rejected {len(rejected)} picks after qualitative screening:")
        for r in rejected:
            print(f"     ✗ {r['ticker']}: {r.get('qualReasoning', 'No reason given')}")
    picks = [p for p in picks if p.get("qualPassed", True)]

    # Re-rank picks after screening
    for i, p in enumerate(picks, 1):
        p["rank"] = i

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
        "macro": {
            "headline": macro_context.get("headline", ""),
            "themes": macro_context.get("themes", [])[:3],
            "source": macro_context.get("source", "unknown"),
        },
    }

    # Print picks
    for p in picks:
        tag = "🔥 SPEC" if p["type"] == "speculative" else f"  #{p['rank']}"
        pnl_str = f"{p['pnlPct']:+.1f}%" if p["pnlPct"] != 0 else "—"
        qual_str = f" | Q:{p.get('qualScore', '?')}/10" if p.get('qualScore') is not None else ""
        print(f"    {tag} {p['ticker']:<6} Grade {p['grade']} ({p['testsPassed']}/7){qual_str} | "
              f"A${p['entryPrice']:.2f} → A${p['currentPrice']:.2f} ({pnl_str})")

    return week_data


def update_weeks_index(weeks_dir):
    """Rebuild the weeks index.json from all weekN.json files."""
    weeks = []
    for f in sorted(os.listdir(weeks_dir)):
        if f.startswith("week") and f.endswith(".json") and f != "index.json" and "_" not in f:
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
    parser.add_argument("--sunday", action="store_true",
                        help="Full Sunday automation: archive previous week + generate next week picks")
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

    if args.sunday:
        # ── Full Sunday automation ──
        # On Sunday, current_week still points to the just-finished week.
        # We need to: 1) archive current_week with final prices, 2) generate current_week + 1
        prev_week = current_week
        next_week = current_week + 1

        # Step 1: Archive the previous week — ONLY backfill prices, don't regenerate picks
        # This preserves historical accuracy: the picks that were published stay published,
        # even if the qualitative kill switch would reject them today.
        prev_path = os.path.join(weeks_dir, f"week{prev_week}.json")
        if os.path.exists(prev_path):
            print(f"\n  📦 Archiving Week {prev_week}...")
            with open(prev_path) as f:
                week_data = json.load(f)
            monday, friday = get_week_dates(prev_week)
            # Backfill actual prices on existing picks
            backfill_monday_open(week_data.get("picks", []), monday)
            # Recalculate summary from actual prices
            picks = week_data.get("picks", [])
            if picks:
                avg_pnl = round(sum(p["pnlPct"] for p in picks) / len(picks), 2)
                winners = sum(1 for p in picks if p["pnlPct"] > 0)
                losers = sum(1 for p in picks if p["pnlPct"] < 0)
                week_data["summary"] = {
                    "avgPnlPct": avg_pnl,
                    "winners": winners,
                    "losers": losers,
                    "flat": len(picks) - winners - losers,
                }
            week_data["status"] = "completed"
            with open(prev_path, "w") as f:
                json.dump(week_data, f, indent=2, ensure_ascii=False)
            print(f"  ✓ Week {prev_week} archived as completed")
        else:
            # First week ever, or previous week doesn't exist yet — generate it fresh
            print(f"\n  📦 Generating + archiving Week {prev_week}...")
            week_data = generate_week(prev_week, index_data, details_dir, weeks_dir, backfill=True)
            week_data["status"] = "completed"
            with open(prev_path, "w") as f:
                json.dump(week_data, f, indent=2, ensure_ascii=False)
            print(f"  ✓ Week {prev_week} saved as completed")

        # Step 2: Generate next week's fresh picks
        print(f"\n  🆕 Generating Week {next_week} picks...")
        week_data = generate_week(next_week, index_data, details_dir, weeks_dir)
        # Force status to active (will go live Monday)
        week_data["status"] = "active"
        week_path = os.path.join(weeks_dir, f"week{next_week}.json")
        with open(week_path, "w") as f:
            json.dump(week_data, f, indent=2, ensure_ascii=False)
        print(f"  ✓ Week {next_week} saved as active")

    elif args.all:
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

