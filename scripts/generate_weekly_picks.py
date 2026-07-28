"""
Nick Knows Best — Monthly Conviction Picks Generator

Selects 3 high-conviction ASX stocks each 4-week cycle:
  • 3 "Core" picks — Grade A/B, sector-diversified, $500M+ market cap
  • Held for 4 weeks with stop-loss protection

Usage:
    python scripts/generate_weekly_picks.py                      # Auto-detect cycle
    python scripts/generate_weekly_picks.py --cycle 2            # Force cycle number
    python scripts/generate_weekly_picks.py --cycle 1 --backfill # Backfill with Mon open prices
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
CORE_PICKS = 3                          # Fewer, higher-conviction picks
HOLD_WEEKS = 4                          # 4-week holding period per cycle
MIN_MARKET_CAP_CORE = 500_000_000      # $500M for core picks
AEST = timezone(timedelta(hours=10))

# Cycle 1 start date (Monday 4 May 2026)
EPOCH_START = datetime(2026, 5, 4, tzinfo=AEST)


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


def calculate_cycle_number(now=None):
    """Calculate current cycle number from epoch start. Each cycle = 4 weeks."""
    if now is None:
        now = datetime.now(AEST)
    delta = now - EPOCH_START
    return max(1, delta.days // (7 * HOLD_WEEKS) + 1)


def is_cycle_boundary(now=None):
    """Check if today is the Sunday before a new cycle starts."""
    if now is None:
        now = datetime.now(AEST)
    delta = now - EPOCH_START
    days_into_cycle = delta.days % (7 * HOLD_WEEKS)
    # Sunday before a new cycle: days_into_cycle is -1 or 27 (last day of cycle)
    return days_into_cycle >= (7 * HOLD_WEEKS - 1) or delta.days < 0


def get_cycle_dates(cycle_num):
    """Get the Monday start → Friday end date range for a 4-week cycle."""
    monday = EPOCH_START + timedelta(weeks=(cycle_num - 1) * HOLD_WEEKS)
    friday = monday + timedelta(weeks=HOLD_WEEKS) - timedelta(days=3)  # Friday of week 4
    return monday, friday


def generate_thesis(stock, detail):
    """Generate a brief investment thesis for a pick."""
    ticker = stock["ticker"]
    grade = stock.get("grade", "?")
    tests = stock.get("testsPassed", 0)
    sector = stock.get("sector", "Unknown")
    score = abs(stock.get("valuationScore", 0))

    parts = []

    # Grade summary — labels must match actual test count
    if tests == 8:
        parts.append("Perfect 8/8 valuation test score")
    elif tests >= 7:
        parts.append(f"Excellent {tests}/8 valuation tests passed")
    elif tests >= 5:
        parts.append(f"Strong {tests}/8 valuation tests passed")
    elif tests >= 3:
        parts.append(f"Solid {tests}/8 valuation tests passed")
    else:
        parts.append(f"Only {tests}/8 valuation tests passed")

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


def check_price_trend(detail):
    """Check if stock is in acceptable price trend using chart data.
    Returns (passed: bool, reason: str, momentum_score: float).
    Rejects stocks in sustained downtrends to avoid falling knives."""
    chart = detail.get("chartData", [])
    if len(chart) < 12:
        return True, "insufficient chart data", 0.0

    current_price = chart[-1].get("price", 0)
    if current_price <= 0:
        return False, "invalid current price", 0.0

    # 3-month change (roughly 12 weekly data points)
    price_3m_ago = chart[-12].get("price", current_price)
    change_3m = ((current_price - price_3m_ago) / price_3m_ago * 100) if price_3m_ago > 0 else 0

    # 20-week SMA (or as many points as available)
    sma_window = min(20, len(chart))
    sma_20w = sum(p.get("price", 0) for p in chart[-sma_window:]) / sma_window

    # Momentum score for ranking: normalized to roughly -1 to +1
    momentum = round(change_3m / 20, 2)
    momentum = max(-1.0, min(1.0, momentum))

    if change_3m < -15:
        return False, f"3-month decline {change_3m:.1f}%", momentum
    if sma_20w > 0 and current_price < sma_20w * 0.95:
        pct_below = ((sma_20w - current_price) / sma_20w) * 100
        return False, f"price {pct_below:.1f}% below 20-week SMA", momentum

    return True, "trend OK", momentum


def check_relative_strength(ticker, period="3mo"):
    """Check stock's relative strength vs ASX200 (XJO).
    Returns (passed: bool, reason: str, rs_score: float).
    Rejects stocks underperforming the index by more than 5%."""
    try:
        stock = yf.Ticker(f"{ticker}.AX")
        index = yf.Ticker("^AXJO")
        stock_hist = stock.history(period=period)
        index_hist = index.history(period=period)

        if stock_hist is None or stock_hist.empty or len(stock_hist) < 10:
            return True, "insufficient stock data", 0.0
        if index_hist is None or index_hist.empty or len(index_hist) < 10:
            return True, "insufficient index data", 0.0

        stock_return = (float(stock_hist["Close"].iloc[-1]) - float(stock_hist["Close"].iloc[0])) / float(stock_hist["Close"].iloc[0]) * 100
        index_return = (float(index_hist["Close"].iloc[-1]) - float(index_hist["Close"].iloc[0])) / float(index_hist["Close"].iloc[0]) * 100

        relative_strength = stock_return - index_return

        if relative_strength < -5.0:
            return False, f"underperforming ASX200 by {abs(relative_strength):.1f}% (stock {stock_return:+.1f}% vs index {index_return:+.1f}%)", round(relative_strength / 10, 2)

        return True, f"RS {relative_strength:+.1f}% vs ASX200", round(relative_strength / 10, 2)
    except Exception as e:
        return True, f"RS check failed: {str(e)[:50]}", 0.0


def check_volume_liquidity(ticker, min_avg_volume=200_000):
    """Check if stock has sufficient daily trading volume.
    Returns (passed: bool, avg_volume: float).
    Rejects stocks with average daily volume below threshold."""
    try:
        t = yf.Ticker(f"{ticker}.AX")
        hist = t.history(period="1mo")
        if hist is None or hist.empty or len(hist) < 5:
            return True, 0  # Pass on insufficient data
        avg_vol = float(hist["Volume"].mean())
        if avg_vol < min_avg_volume:
            return False, avg_vol
        return True, avg_vol
    except Exception:
        return True, 0


# ── Earnings Calendar Check ──
# Flags stocks reporting earnings during the 4-week holding period

def check_earnings_calendar(ticker, hold_end_date):
    """Check if a stock has earnings scheduled within the holding period.
    Returns (has_earnings: bool, earnings_date: str or None).
    Uses yfinance calendar data when available."""
    try:
        t = yf.Ticker(f"{ticker}.AX")
        cal = t.calendar
        if cal is None or cal.empty:
            return False, None

        # yfinance returns earnings date in various formats
        earnings_date = None
        if isinstance(cal, dict):
            ed = cal.get("Earnings Date")
            if ed:
                earnings_date = ed[0] if isinstance(ed, list) else ed
        else:
            # DataFrame format
            if "Earnings Date" in cal.index:
                earnings_date = cal.loc["Earnings Date"].iloc[0] if len(cal.columns) > 0 else None

        if earnings_date is None:
            return False, None

        # Parse and compare
        from datetime import datetime as dt
        if isinstance(earnings_date, str):
            try:
                ed = dt.strptime(earnings_date, "%Y-%m-%d").replace(tzinfo=AEST)
            except ValueError:
                return False, None
        elif hasattr(earnings_date, 'date'):
            ed = earnings_date
        else:
            return False, None

        now = datetime.now(AEST)
        if now <= ed <= hold_end_date:
            return True, str(ed)[:10]
        return False, None
    except Exception:
        return False, None


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
        print("  ⚠ HARD CAP: 2 picks max without qualitative validation (reduced risk)")
        for p in picks:
            p["qualScore"] = None
            p["qualReasoning"] = "⚠ UNVALIDATED: Qualitative screening skipped (no API key)"
            p["qualPassed"] = True
        return picks[:2]  # Reduced from 3 → 2: less exposure without AI validation

    print(f"  🧠 Running adversarial qualitative screening on {len(picks)} candidates...")
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

        prompt = f"""You are a ruthlessly honest portfolio manager. Your job is to CHALLENGE this stock pick, not confirm it.
Your default stance is REJECT. Only pass stocks you would genuinely invest your own savings in for 4 weeks.

Stock: {name} ({ticker}.AX)
Sector: {sector} | Market Cap: {mcap} | Price: A${price:.2f}
Valuation Grade: {grade} ({tests}/8 quantitative tests passed)
Holding Period: 4 weeks | Macro Bias: {bias_label} ({bias:+.1f})
{metrics_context}

Answer these questions HONESTLY:

1. VALUE TRAP TEST: Is this stock cheap BECAUSE of a structural problem (declining industry,
   losing market share, management issues, regulatory risk)? Cheap alone is NOT a reason to buy.

2. CATALYST TEST: What specific event in the next 4 weeks could move this stock UP?
   If the answer is "nothing specific" — that's a strong reason to reject.

3. KILL SHOT: What is the single most likely scenario that causes a 10%+ loss in 4 weeks?
   Be specific (earnings miss, sector rotation, macro shock, liquidity dry-up).

4. PERSONAL MONEY TEST: Would you put A$10,000 of your own savings into this stock today
   for exactly 4 weeks? If not, why not?

5. RELATIVE VALUE: Are there obviously better opportunities in the same sector or market
   right now? If yes, this stock should be rejected.

Return ONLY this JSON (no markdown):
{{
  "isValueTrap": true/false,
  "valueTrapReason": "Why it is or isn't a value trap",
  "catalyst": "Specific 4-week catalyst or 'none identified'",
  "killShot": "The most likely way this trade loses 10%+ in 4 weeks",
  "wouldInvestOwnMoney": true/false,
  "whyNotOwnMoney": "Honest reason if you wouldn't invest own money (or 'N/A')",
  "betterAlternativeExists": true/false,
  "moatStrength": "none|weak|moderate|strong",
  "asymmetry": "favorable|neutral|unfavorable",
  "bearSeverity": "low|medium|high|critical",
  "conviction": 1-10,
  "recommendation": "pass|reject",
  "reasoning": "2-3 sentence brutally honest assessment"
}}

CRITICAL: A conviction score of 7+ means you would GENUINELY bet your own money.
Anything below 7 should be "reject". Do NOT be generous — most stocks should fail this screen."""

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
            is_value_trap = result.get("isValueTrap", False)
            would_invest = result.get("wouldInvestOwnMoney", False)

            p["qualScore"] = conviction
            p["qualReasoning"] = result.get("reasoning", "")
            p["qualDetail"] = {
                "businessModel": result.get("valueTrapReason", ""),
                "moatStrength": result.get("moatStrength", "unknown"),
                "catalyst": result.get("catalyst", ""),
                "killShot": result.get("killShot", ""),
                "asymmetry": asymmetry,
                "bearCase": result.get("killShot", ""),
                "bearSeverity": bear_severity,
                "isValueTrap": is_value_trap,
                "wouldInvestOwnMoney": would_invest,
            }

            # Kill switch: reject if ANY of these red flags trigger independently
            # Thresholds TIGHTENED from Cycle 1 post-mortem
            reject_reasons = []
            if bear_severity in ("critical", "high"):
                reject_reasons.append(f"{bear_severity} bear severity")
            if recommendation == "reject":
                reject_reasons.append("AI recommends reject")
            if conviction < 7:
                reject_reasons.append(f"conviction {conviction}/10 (need 7+)")
            if is_value_trap:
                reject_reasons.append("identified as value trap")
            if not would_invest:
                reject_reasons.append("wouldn't invest own money")
            if result.get("moatStrength") == "none" and asymmetry == "unfavorable":
                reject_reasons.append("no moat + unfavorable asymmetry")
            if result.get("betterAlternativeExists"):
                reject_reasons.append("better alternatives exist")

            if reject_reasons:
                p["qualPassed"] = False
                p["qualReasoning"] = f"REJECTED: {'; '.join(reject_reasons)}. {result.get('reasoning', '')}"
                icon = "❌"
            else:
                p["qualPassed"] = True
                icon = "✅"

            print(f"    {icon} {ticker}: conviction={conviction}/10, "
                  f"moat={result.get('moatStrength', '?')}, "
                  f"trap={'YES' if is_value_trap else 'no'}, "
                  f"own_money={'YES' if would_invest else 'NO'}, "
                  f"bear={bear_severity} → {recommendation}")

        except Exception as e:
            print(f"    ⚠ {ticker}: Screening failed ({str(e)[:80]}) — marking unvalidated")
            p["qualScore"] = None
            p["qualReasoning"] = f"⚠ UNVALIDATED: Screening error: {str(e)[:100]}"
            p["qualPassed"] = True  # Don't reject on API errors, but flag it

        # Gentle rate limit
        time.sleep(2)

    return picks


def select_core_picks(index_data, details_dir, exclude_tickers=None, sector_biases=None, hold_end_date=None):
    """Select top 3 core picks: Grade A/B, sector-diversified, $500M+ market cap.
    Filters: profitability gate, leverage cap, macro headwind rejection, liquidity.
    Uses macro sector biases to rank stocks by combined valuation + macro + quality score."""
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

        # Skip stocks in STRONG headwind sectors (bias <= -0.6)
        # Mild headwinds (-0.3 to -0.6) are penalized in scoring but not blocked,
        # allowing the adversarial AI screen to make the final quality judgment
        sector = s.get("sector", "Unknown")
        bias = _find_sector_bias(sector, sector_biases)
        if bias <= -0.6:
            print(f"    ⛔ Skipping {s['ticker']} — {sector} has strong headwind ({bias:+.1f})")
            continue

        # ── Profitability & leverage gate (load detail metrics) ──
        detail = _load_detail(details_dir, s["ticker"])
        if detail:
            m = detail.get("metrics", {})
            pm = m.get("profitMargin")
            roe = m.get("roe")
            de = m.get("debtEquity")
            rev_growth = m.get("revenueGrowth")

            # Reject weak profitability (hardened: min 3% margin, 5% ROE)
            if pm is not None and pm < 3:
                print(f"    ⛔ Skipping {s['ticker']} — weak profit margin ({pm:.1f}%, need 3%+)")
                continue
            if roe is not None and roe < 5:
                print(f"    ⛔ Skipping {s['ticker']} — weak ROE ({roe:.1f}%, need 5%+)")
                continue

            # Reject highly leveraged (D/E > 100%)
            if de is not None and de > 100:
                print(f"    ⛔ Skipping {s['ticker']} — high leverage D/E {de:.0f}%")
                continue

            # Reject severe revenue decline (> -10%)
            if rev_growth is not None and rev_growth < -10:
                print(f"    ⛔ Skipping {s['ticker']} — severe revenue decline ({rev_growth:.1f}%)")
                continue

        # ── Price-trend filter: reject falling knives ──
        detail = _load_detail(details_dir, s["ticker"]) if not detail else detail
        if detail:
            trend_ok, trend_reason, momentum = check_price_trend(detail)
            if not trend_ok:
                print(f"    ⛔ Skipping {s['ticker']} — {trend_reason}")
                continue
        else:
            momentum = 0.0

        # ── Relative strength vs ASX200: reject value traps ──
        rs_ok, rs_reason, rs_score = check_relative_strength(s["ticker"])
        if not rs_ok:
            print(f"    ⛔ Skipping {s['ticker']} — {rs_reason}")
            continue

        # ── Volume/liquidity gate: reject illiquid stocks ──
        vol_ok, avg_vol = check_volume_liquidity(s["ticker"])
        if not vol_ok:
            print(f"    ⛔ Skipping {s['ticker']} — illiquid (avg vol {avg_vol:,.0f}, need 200k+)")
            continue

        # ── Quality score: reward margin expansion + revenue growth ──
        quality_bonus = 0.0
        if detail:
            m = detail.get("metrics", {})
            pm = m.get("profitMargin")
            rev_growth = m.get("revenueGrowth")
            roe = m.get("roe")
            # Reward growing, profitable businesses
            if rev_growth is not None and rev_growth > 5:
                quality_bonus += 1.5  # Growing revenue
            if pm is not None and pm > 10:
                quality_bonus += 1.0  # Strong margins
            if roe is not None and roe > 15:
                quality_bonus += 1.0  # High return on equity
            # Penalize declining or low-quality businesses
            if rev_growth is not None and rev_growth < 0:
                quality_bonus -= 2.0  # Shrinking revenue = danger
            if pm is not None and pm < 5:
                quality_bonus -= 1.0  # Thin margins

        # Compute combined score: valuation + macro + momentum + quality + relative strength
        val_score = grade_base.get(grade, 0) + (s.get("testsPassed", 0) * 0.5)
        # Heavier penalty for headwinds than reward for tailwinds
        macro_boost = bias * 3.0 if bias >= 0 else bias * 5.0
        momentum_boost = momentum * 2.0  # Prefer stocks in uptrends
        rs_boost = rs_score * 2.0  # Reward stocks outperforming ASX200
        combined = val_score + macro_boost + momentum_boost + quality_bonus + rs_boost
        s["_combinedScore"] = round(combined, 2)
        s["_macroBias"] = round(bias, 2)
        s["_momentum"] = momentum
        s["_qualityBonus"] = round(quality_bonus, 2)
        s["_rsScore"] = round(rs_score, 2)
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

    # Load details for thesis generation + earnings calendar check
    # Send more candidates to qualitative screening (AI will reject the weak ones)
    picks = []
    screen_limit = max(CORE_PICKS, min(len(selected), CORE_PICKS * 3))
    for rank, stock in enumerate(selected[:screen_limit], 1):
        detail = _load_detail(details_dir, stock["ticker"])
        bias = stock.get("_macroBias", 0)
        macro_label = _bias_label(bias)
        thesis = generate_thesis(stock, detail)
        if bias != 0:
            thesis = thesis.rstrip(".") + f". Macro: {macro_label} for {stock.get('sector', 'sector')}."

        # Check earnings calendar
        earnings_warning = ""
        if hold_end_date:
            has_earnings, earnings_date = check_earnings_calendar(stock["ticker"], hold_end_date)
            if has_earnings:
                earnings_warning = f" ⚠️ Earnings due {earnings_date} — binary event risk."
                thesis = thesis.rstrip(".") + f".{earnings_warning}"
                print(f"    📅 {stock['ticker']} has earnings on {earnings_date} during hold period")

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
            "hasEarnings": bool(earnings_warning),
        })

    return picks


def select_speculative_pick(index_data, details_dir, exclude_tickers=None, sector_biases=None):
    """
    Select 1 speculative penny/micro-cap pick.
    Criteria: <$500M market cap, Grade C+ (3+ tests), macro-aligned,
    must have either positive revenue growth OR positive profit margin.
    Returns None if no quality candidate exists (better no pick than a bad one).
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
        if grade in ("F", "D"):  # Require Grade C+ (was D+)
            continue
        tests = s.get("testsPassed", 0)
        if tests < 3:
            continue

        # Reject spec picks in headwind sectors (bias <= -0.3)
        sector = s.get("sector", "Unknown")
        bias = _find_sector_bias(sector, sector_biases)
        if bias <= -0.3:
            print(f"    ⛔ Spec skip {s['ticker']} — {sector} headwind ({bias:+.1f})")
            continue

        # Fundamental quality check from detail data
        detail = _load_detail(details_dir, s["ticker"])
        if detail:
            m = detail.get("metrics", {})
            pm = m.get("profitMargin")
            rev_growth = m.get("revenueGrowth")
            # Must have at least one positive: revenue growth OR profit margin
            has_positive_margin = pm is not None and pm > 0
            has_positive_growth = rev_growth is not None and rev_growth > 0
            if not has_positive_margin and not has_positive_growth:
                print(f"    ⛔ Spec skip {s['ticker']} — negative margin AND negative growth")
                continue

        candidates.append(s)

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


def load_previous_picks(cycles_dir, current_cycle_num, cooloff_cycles=2):
    """Load tickers picked in the last N cycles to enforce a cooling-off period.
    A stock can't be re-picked until cooloff_cycles after its last appearance."""
    used = set()
    start_cycle = max(1, current_cycle_num - cooloff_cycles)
    for c in range(start_cycle, current_cycle_num):
        path = os.path.join(cycles_dir, f"cycle{c}.json")
        if os.path.exists(path):
            with open(path) as f:
                data = json.load(f)
            for pick in data.get("picks", []):
                used.add(pick["ticker"])
    if used:
        print(f"  🔒 Cooling-off exclusion ({cooloff_cycles} cycles): {', '.join(sorted(used))}")
    return used


def generate_cycle(cycle_num, index_data, details_dir, cycles_dir, backfill=False):
    """Generate a complete cycle JSON with macro/geopolitical overlay (4-week hold)."""
    monday, friday = get_cycle_dates(cycle_num)
    now = datetime.now(AEST)

    # Determine status
    if now < monday - timedelta(days=1):
        status = "upcoming"
    elif now > friday + timedelta(days=1):
        status = "completed"
    else:
        status = "active"

    print(f"\n  📅 Cycle {cycle_num}: {monday.strftime('%d %b')} – {friday.strftime('%d %b %Y')} (4-week hold)")
    print(f"     Status: {status}")

    # ── MACRO SCAN: Get geopolitical/news sector biases ──
    print(f"  🌍 Running macro/geopolitical scan...")
    sector_biases, macro_context = get_macro_biases()
    print(f"     Headline: {macro_context.get('headline', 'N/A')}")
    print(f"     Source: {macro_context.get('source', 'unknown')}")
    if macro_context.get('themes'):
        for theme in macro_context['themes'][:3]:
            print(f"     • {theme}")
    favored = {k: v for k, v in sector_biases.items() if v >= 0.3}
    avoided = {k: v for k, v in sector_biases.items() if v <= -0.3}
    if favored:
        print(f"     ✅ Favored: {', '.join(f'{k} ({v:+.1f})' for k, v in sorted(favored.items(), key=lambda x: -x[1]))}")
    if avoided:
        print(f"     ❌ Avoided: {', '.join(f'{k} ({v:+.1f})' for k, v in sorted(avoided.items(), key=lambda x: x[1]))}")

    # Save macro context
    save_macro_context(cycles_dir, cycle_num, macro_context, sector_biases)

    # Load previously picked tickers
    exclude = load_previous_picks(cycles_dir, cycle_num)
    if exclude:
        print(f"     Excluding {len(exclude)} previously picked tickers: {', '.join(sorted(exclude))}")

    # Select picks with macro overlay + earnings awareness
    core = select_core_picks(index_data, details_dir, exclude_tickers=exclude, sector_biases=sector_biases, hold_end_date=friday)

    picks = core

    # If we got zero candidates through, retry with Grade C inclusion
    # This happens in tough macro environments where A/B universe is too narrow
    if not picks:
        print(f"  ⚠️  Zero candidates from Grade A/B pool — widening to Grade C with strict AI screening")
        core = select_core_picks(index_data, details_dir, exclude_tickers=exclude,
                                 sector_biases=sector_biases, hold_end_date=friday,
                                 include_grade_c=True)
        picks = core

    # ── QUALITATIVE SCREENING ──
    picks = qualify_picks(picks, details_dir, sector_biases=sector_biases)

    # Remove rejected picks
    rejected = [p for p in picks if not p.get("qualPassed", True)]
    if rejected:
        print(f"  🚫 Rejected {len(rejected)} picks after qualitative screening:")
        for r in rejected:
            print(f"     ✗ {r['ticker']}: {r.get('qualReasoning', 'No reason given')}")
    picks = [p for p in picks if p.get("qualPassed", True)]

    # Sort survivors by qualitative conviction score (highest first), then trim to CORE_PICKS
    picks.sort(key=lambda p: -(p.get("qualScore") or 0))
    if len(picks) > CORE_PICKS:
        print(f"  ✂️  Trimming from {len(picks)} → {CORE_PICKS} best conviction picks")
        picks = picks[:CORE_PICKS]

    # Re-rank
    for i, p in enumerate(picks, 1):
        p["rank"] = i

    # Backfill with actual Monday open prices if requested
    if backfill and monday < now:
        print(f"  🔄 Backfilling prices from {monday.strftime('%Y-%m-%d')}...")
        backfill_monday_open(picks, monday)

    # Calculate summary
    avg_pnl_pct = sum(p["pnlPct"] for p in picks) / len(picks) if picks else 0
    winners = sum(1 for p in picks if p["pnlPct"] > 0)
    losers = sum(1 for p in picks if p["pnlPct"] < 0)

    cycle_data = {
        "cycle": cycle_num,
        "dateRange": f"{monday.strftime('%d %b')} – {friday.strftime('%d %b %Y')}",
        "startDate": monday.strftime("%Y-%m-%d"),
        "endDate": friday.strftime("%Y-%m-%d"),
        "holdWeeks": HOLD_WEEKS,
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
        pnl_str = f"{p['pnlPct']:+.1f}%" if p["pnlPct"] != 0 else "—"
        qual_str = f" | Q:{p.get('qualScore', '?')}/10" if p.get('qualScore') is not None else ""
        print(f"    #{p['rank']} {p['ticker']:<6} Grade {p['grade']} ({p['testsPassed']}/8){qual_str} | "
              f"A${p['entryPrice']:.2f} → A${p['currentPrice']:.2f} ({pnl_str})")

    return cycle_data


def update_cycles_index(cycles_dir):
    """Rebuild the cycles index.json from all cycleN.json files."""
    cycles = []
    for f in sorted(os.listdir(cycles_dir)):
        if f.startswith("cycle") and f.endswith(".json") and f != "index.json" and "_" not in f:
            path = os.path.join(cycles_dir, f)
            with open(path) as fh:
                data = json.load(fh)
            cycles.append({
                "cycle": data["cycle"],
                "dateRange": data["dateRange"],
                "startDate": data["startDate"],
                "endDate": data["endDate"],
                "holdWeeks": data.get("holdWeeks", HOLD_WEEKS),
                "status": data["status"],
                "avgPnlPct": data["summary"]["avgPnlPct"],
                "winners": data["summary"]["winners"],
                "losers": data["summary"]["losers"],
            })

    cycles.sort(key=lambda c: c["cycle"])
    current = max((c["cycle"] for c in cycles if c["status"] == "active"), default=cycles[-1]["cycle"] if cycles else 1)

    index = {
        "currentCycle": current,
        "totalCycles": len(cycles),
        "holdWeeks": HOLD_WEEKS,
        "cycles": cycles,
    }

    index_path = os.path.join(cycles_dir, "index.json")
    with open(index_path, "w") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)
    print(f"\n  ✓ Index updated: {len(cycles)} cycles, current = Cycle {current}")


# Keep backward-compatible alias for update_weekly_prices.py import
update_weeks_index = update_cycles_index


def _load_detail(details_dir, ticker):
    """Load a stock detail JSON file."""
    path = os.path.join(details_dir, f"{ticker}.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None


def main():
    parser = argparse.ArgumentParser(description="Generate monthly conviction picks")
    parser.add_argument("--cycle", type=int, default=None, help="Cycle number (auto if omitted)")
    parser.add_argument("--backfill", action="store_true", help="Backfill actual open prices for past cycles")
    parser.add_argument("--all", action="store_true", help="Generate all cycles up to current")
    parser.add_argument("--sunday", action="store_true",
                        help="Sunday automation: archive previous cycle + generate next cycle if at boundary")
    args = parser.parse_args()

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(project_root, "public", "data")
    cycles_dir = os.path.join(data_dir, "cycles")
    details_dir = os.path.join(data_dir, "asx", "details")
    os.makedirs(cycles_dir, exist_ok=True)

    # Load index data
    index_path = os.path.join(data_dir, "asx_index.json")
    if not os.path.exists(index_path):
        print("❌ No asx_index.json found. Run the pipeline first.")
        sys.exit(1)

    with open(index_path) as f:
        index_data = json.load(f)

    print("=" * 60)
    print("  NICK KNOWS BEST — Monthly Conviction Picks Generator")
    print("=" * 60)

    now = datetime.now(AEST)
    current_cycle = calculate_cycle_number(now)

    if args.sunday:
        # ── Sunday automation ──
        # Only generate new picks at cycle boundaries (every 4 weeks).
        # On non-boundary Sundays, just log and exit (prices updated separately).
        if not is_cycle_boundary(now):
            print(f"\n  📅 Mid-cycle (Cycle {current_cycle}) — no new picks needed.")
            print(f"     Prices are updated daily by update_weekly_prices.py")
            update_cycles_index(cycles_dir)
            print("\n" + "=" * 60)
            print("  ✅ SUNDAY CHECK COMPLETE (mid-cycle)")
            print("=" * 60)
            return

        prev_cycle = current_cycle
        next_cycle = current_cycle + 1

        # Step 1: Archive the previous cycle
        prev_path = os.path.join(cycles_dir, f"cycle{prev_cycle}.json")
        if os.path.exists(prev_path):
            print(f"\n  📦 Archiving Cycle {prev_cycle}...")
            with open(prev_path) as f:
                cycle_data = json.load(f)
            monday, friday = get_cycle_dates(prev_cycle)
            backfill_monday_open(cycle_data.get("picks", []), monday)
            picks = cycle_data.get("picks", [])
            if picks:
                avg_pnl = round(sum(p["pnlPct"] for p in picks) / len(picks), 2)
                winners = sum(1 for p in picks if p["pnlPct"] > 0)
                losers = sum(1 for p in picks if p["pnlPct"] < 0)
                cycle_data["summary"] = {
                    "avgPnlPct": avg_pnl,
                    "winners": winners,
                    "losers": losers,
                    "flat": len(picks) - winners - losers,
                }
            cycle_data["status"] = "completed"
            with open(prev_path, "w") as f:
                json.dump(cycle_data, f, indent=2, ensure_ascii=False)
            print(f"  ✓ Cycle {prev_cycle} archived as completed")
        else:
            print(f"\n  📦 Generating + archiving Cycle {prev_cycle}...")
            cycle_data = generate_cycle(prev_cycle, index_data, details_dir, cycles_dir, backfill=True)
            cycle_data["status"] = "completed"
            with open(prev_path, "w") as f:
                json.dump(cycle_data, f, indent=2, ensure_ascii=False)
            print(f"  ✓ Cycle {prev_cycle} saved as completed")

        # Step 2: Generate next cycle's fresh picks
        print(f"\n  🆕 Generating Cycle {next_cycle} picks...")
        cycle_data = generate_cycle(next_cycle, index_data, details_dir, cycles_dir)
        cycle_data["status"] = "active"
        cycle_path = os.path.join(cycles_dir, f"cycle{next_cycle}.json")
        with open(cycle_path, "w") as f:
            json.dump(cycle_data, f, indent=2, ensure_ascii=False)
        print(f"  ✓ Cycle {next_cycle} saved as active")

    elif args.all:
        for c in range(1, current_cycle + 1):
            cycle_data = generate_cycle(c, index_data, details_dir, cycles_dir, backfill=True)
            cycle_path = os.path.join(cycles_dir, f"cycle{c}.json")
            with open(cycle_path, "w") as f:
                json.dump(cycle_data, f, indent=2, ensure_ascii=False)
            print(f"  ✓ Saved {cycle_path}")
    else:
        cycle_num = args.cycle or current_cycle
        cycle_data = generate_cycle(cycle_num, index_data, details_dir, cycles_dir, backfill=args.backfill)
        cycle_path = os.path.join(cycles_dir, f"cycle{cycle_num}.json")
        with open(cycle_path, "w") as f:
            json.dump(cycle_data, f, indent=2, ensure_ascii=False)
        print(f"\n  ✓ Saved {cycle_path}")

    update_cycles_index(cycles_dir)

    print("\n" + "=" * 60)
    print("  ✅ MONTHLY CONVICTION PICKS GENERATED")
    print("=" * 60)

if __name__ == "__main__":
    main()

