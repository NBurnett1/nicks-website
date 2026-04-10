"""
Nick Knows Best — ASX Trading Engine v3 (SMC Edition)

Smart Money Concepts + Valuation confluence trading system.

Strategy based on:
  1. Technical Analysis — Market structure (HH/HL/LH/LL), trend identification
  2. Multi-Timeframe — Weekly bias (trend) + daily entry confirmation
  3. Market Structure — Break of Structure (BOS), Change of Character (CHoCH)
  4. Liquidity Sweeps — Equal highs/lows, sweep + reversal patterns
  5. Fair Value Gaps — Three-candle imbalance zones for optimal entries
  6. Risk Management — Asymmetric R:R (min 3:1), 1-2% account risk per trade

ENTRY CONDITIONS (ALL must align):
  1. Undervalued by our valuation model (mispricing < -25%)
  2. Weekly structure is bullish (HH/HL pattern) — multi-timeframe bias
  3. Daily structure shows BOS or CHoCH confirming bullish shift
  4. Recent liquidity sweep of lows (stop hunt) followed by reversal
  5. Fair Value Gap present as entry zone
  6. Volume confirms (above average)
  7. Minimum 3:1 risk-reward ratio to fair value target

EXIT:
  • Stop-loss behind the most recent swing low (structure-based, not fixed %)
  • Trail stop to previous swing lows as new structure forms
  • Partial profit at 3R, let remainder ride toward fair value
  • Full exit at fair value target or on bearish CHoCH

POSITION SIZING:
  • Risk 1.5% of portfolio value per trade
  • Position size = risk amount / distance to stop-loss
  • Max 8 concurrent positions, max 3 per sector

Usage:
    python scripts/simulate_trades.py --live        # 30-min live session
    python scripts/simulate_trades.py --maintain     # Update prices & exits only
    python scripts/simulate_trades.py --reset        # Fresh start
"""

import json
import os
import sys
import argparse
from datetime import datetime, timezone, timedelta

import yfinance as yf
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from score_stocks import run_valuation_tests, conviction_grade


# ---------- Configuration ----------
STARTING_CAPITAL = 10_000.00
MAX_POSITIONS = 8
MAX_SECTOR_POSITIONS = 3
MIN_MISPRICING = -25           # Slightly relaxed from -30 to catch more setups
RISK_PER_TRADE_PCT = 0.015     # 1.5% of portfolio per trade
MIN_RR_RATIO = 3.0             # Minimum 3:1 risk-reward
MIN_TRADE_VALUE = 150          # Minimum trade in dollars
MAX_HOLD_DAYS = 40             # Max hold for losing positions
PARTIAL_PROFIT_R = 3.0         # Take partial at 3R
PARTIAL_SELL_RATIO = 0.50      # Sell 50% at partial profit target
SWING_LOOKBACK = 5             # Bars to look back for swing detection

# Grade-based portfolio allocation — higher conviction = bigger position
GRADE_ALLOCATION = {
    "A": 0.15,   # 15% of portfolio per Grade A stock
    "B": 0.10,   # 10%
    "C": 0.06,   #  6%
    "D": 0.03,   #  3%
    "F": 0.00,   #  0% — don't trade Grade F
}


# ═══════════════════════════════════════════════════════════
#  SMART MONEY CONCEPTS — Technical Analysis Functions
# ═══════════════════════════════════════════════════════════

def find_swing_highs(highs, lookback=SWING_LOOKBACK):
    """Find swing high points in a price series.
    A swing high is a bar whose high is higher than the `lookback` bars on each side."""
    swings = []
    for i in range(lookback, len(highs) - lookback):
        is_swing = True
        for j in range(1, lookback + 1):
            if highs[i] <= highs[i - j] or highs[i] <= highs[i + j]:
                is_swing = False
                break
        if is_swing:
            swings.append((i, float(highs[i])))
    return swings


def find_swing_lows(lows, lookback=SWING_LOOKBACK):
    """Find swing low points in a price series."""
    swings = []
    for i in range(lookback, len(lows) - lookback):
        is_swing = True
        for j in range(1, lookback + 1):
            if lows[i] >= lows[i - j] or lows[i] >= lows[i + j]:
                is_swing = False
                break
        if is_swing:
            swings.append((i, float(lows[i])))
    return swings


def detect_market_structure(highs, lows, closes, lookback=SWING_LOOKBACK):
    """
    Detect market structure: HH/HL (bullish) or LH/LL (bearish).
    Returns: structure dict with trend, swing points, BOS, CHoCH signals.
    """
    swing_highs = find_swing_highs(highs, lookback)
    swing_lows = find_swing_lows(lows, lookback)

    if len(swing_highs) < 2 or len(swing_lows) < 2:
        return {
            "trend": "neutral", "swingHighs": [], "swingLows": [],
            "lastSwingHigh": 0, "lastSwingLow": 0,
            "hh": False, "hl": False, "lh": False, "ll": False,
            "bos": False, "bosBearish": False, "choch": False, "chochBearish": False,
        }

    # Classify swing point sequences
    sh = swing_highs[-2:]
    sl = swing_lows[-2:]

    hh = sh[-1][1] > sh[-2][1]  # Higher High
    hl = sl[-1][1] > sl[-2][1]  # Higher Low
    lh = sh[-1][1] < sh[-2][1]  # Lower High
    ll = sl[-1][1] < sl[-2][1]  # Lower Low

    # Determine trend
    if hh and hl:
        trend = "bullish"
    elif lh and ll:
        trend = "bearish"
    elif hh and not hl:
        trend = "bullish_weak"  # HH but not HL yet
    elif hl and not hh:
        trend = "bullish_building"  # HL forming
    else:
        trend = "neutral"

    # Break of Structure (BOS) — price broke the most recent swing high (bullish)
    current_price = float(closes[-1])
    last_swing_high = sh[-1][1]
    last_swing_low = sl[-1][1]
    bos_bullish = current_price > last_swing_high
    bos_bearish = current_price < last_swing_low

    # Change of Character (CHoCH) — trend reversal signal
    # Bullish CHoCH: was making LH/LL but now breaks above the last LH
    choch_bullish = (lh or ll) and current_price > sh[-1][1]
    choch_bearish = (hh or hl) and current_price < sl[-1][1]

    return {
        "trend": trend,
        "swingHighs": [(i, round(v, 2)) for i, v in swing_highs[-3:]],
        "swingLows": [(i, round(v, 2)) for i, v in swing_lows[-3:]],
        "lastSwingHigh": round(last_swing_high, 2),
        "lastSwingLow": round(last_swing_low, 2),
        "hh": bool(hh), "hl": bool(hl), "lh": bool(lh), "ll": bool(ll),
        "bos": bool(bos_bullish),
        "bosBearish": bool(bos_bearish),
        "choch": bool(choch_bullish),
        "chochBearish": bool(choch_bearish),
    }


def detect_liquidity_sweep(lows, closes, swing_lows):
    """
    Detect if a recent liquidity sweep occurred.
    A sweep happens when price dips below a swing low then closes back above it.
    This indicates smart money grabbed stop-losses and reversed.
    """
    if len(swing_lows) < 1 or len(lows) < 3:
        return {"swept": False}

    # Check the last few bars for a sweep of the most recent swing low
    target_low = swing_lows[-1][1]

    for i in range(-3, 0):  # Check last 3 bars
        if i >= -len(lows):
            bar_low = float(lows[i])
            bar_close = float(closes[i])
            # Price wicked below swing low but closed above it = sweep
            if bar_low < target_low * 0.998 and bar_close > target_low:
                return {
                    "swept": True,
                    "sweepLevel": round(target_low, 2),
                    "sweepLow": round(bar_low, 2),
                    "closeAbove": round(bar_close, 2),
                }

    # Also check for equal lows sweep (double bottom + break below then reversal)
    if len(swing_lows) >= 2:
        prev_low = swing_lows[-2][1]
        recent_low = swing_lows[-1][1]
        # Equal lows (within 1% of each other)
        if abs(prev_low - recent_low) / max(prev_low, 0.01) < 0.01:
            for i in range(-3, 0):
                if i >= -len(lows):
                    bar_low = float(lows[i])
                    bar_close = float(closes[i])
                    if bar_low < min(prev_low, recent_low) and bar_close > min(prev_low, recent_low):
                        return {
                            "swept": True,
                            "sweepLevel": round(min(prev_low, recent_low), 2),
                            "type": "equal_lows",
                            "sweepLow": round(bar_low, 2),
                            "closeAbove": round(bar_close, 2),
                        }

    return {"swept": False}


def detect_fair_value_gap(highs, lows, closes):
    """
    Detect bullish Fair Value Gaps (FVGs) in recent price action.
    A bullish FVG is a 3-candle pattern where:
      - Candle 1 high < Candle 3 low (gap between wicks)
      - Candle 2 is a strong bullish candle (the impulse)
    The gap zone is a high-probability entry area.
    """
    fvgs = []
    for i in range(2, min(len(highs), 10)):  # Check last 10 bars
        idx = len(highs) - i
        if idx < 2:
            break

        c1_high = float(highs[idx - 2])  # First candle high
        c2_open = float(closes[idx - 2])
        c2_close = float(closes[idx - 1])
        c3_low = float(lows[idx])        # Third candle low

        # Bullish FVG: gap between candle 1's high and candle 3's low
        if c3_low > c1_high and c2_close > c2_open:
            gap_top = c3_low
            gap_bottom = c1_high
            gap_size = (gap_top - gap_bottom) / gap_bottom * 100

            if gap_size > 0.3:  # Minimum gap size of 0.3%
                fvgs.append({
                    "top": round(gap_top, 2),
                    "bottom": round(gap_bottom, 2),
                    "midpoint": round((gap_top + gap_bottom) / 2, 2),
                    "gapPct": round(gap_size, 2),
                    "barsAgo": i,
                })

    return fvgs


def detect_order_block(opens, highs, lows, closes):
    """
    Detect bullish order blocks.
    A bullish OB is the last bearish candle before a strong impulsive bullish move.
    """
    if len(closes) < 5:
        return None

    # Look back through recent bars
    for i in range(len(closes) - 4, max(0, len(closes) - 15), -1):
        candle_open = float(opens[i])
        candle_close = float(closes[i])
        candle_low = float(lows[i])
        candle_high = float(highs[i])

        # Is this a bearish candle?
        if candle_close >= candle_open:
            continue

        # Check if the next 2-3 candles form a strong bullish impulse
        impulse_high = max(float(highs[j]) for j in range(i + 1, min(i + 4, len(highs))))
        move_size = (impulse_high - candle_close) / candle_close * 100

        if move_size > 2.0:  # At least 2% impulse move
            return {
                "top": round(candle_open, 2),  # OB zone top
                "bottom": round(candle_low, 2),  # OB zone bottom
                "midpoint": round((candle_open + candle_low) / 2, 2),
                "impulsePct": round(move_size, 2),
                "barsAgo": len(closes) - 1 - i,
            }

    return None


def calc_rsi(prices, period=14):
    """Calculate RSI from a price series."""
    if len(prices) < period + 1:
        return 50.0

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
    """Calculate EMA from a price series."""
    if len(prices) < period:
        return prices[-1] if len(prices) > 0 else 0
    multiplier = 2 / (period + 1)
    ema = float(prices[0])
    for p in prices[1:]:
        ema = (float(p) - ema) * multiplier + ema
    return ema


# ═══════════════════════════════════════════════════════════
#  PORTFOLIO & DATA FUNCTIONS
# ═══════════════════════════════════════════════════════════

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


def get_stock_data(ticker, suffix=".AX", period="3mo"):
    """Fetch historical data for a ticker. Returns (hist_df, current_price) or (None, None)."""
    try:
        t = yf.Ticker(f"{ticker}{suffix}")
        hist = t.history(period=period)
        if hist is not None and not hist.empty and len(hist) >= 10:
            return hist, float(hist["Close"].iloc[-1])
    except Exception:
        pass
    return None, None


def get_weekly_data(ticker, suffix=".AX"):
    """Fetch weekly data for higher-timeframe analysis."""
    try:
        t = yf.Ticker(f"{ticker}{suffix}")
        hist = t.history(period="6mo", interval="1wk")
        if hist is not None and not hist.empty and len(hist) >= 8:
            return hist
    except Exception:
        pass
    return None


def load_candidates(data_dir):
    """Load undervalued ASX stocks with conviction grades and metrics.
    Uses the multi-test grade system from index data. Falls back to reports
    for fair value when available."""
    candidates = []
    index_path = os.path.join(data_dir, "asx_index.json")
    if not os.path.exists(index_path):
        return candidates

    with open(index_path) as f:
        data = json.load(f)

    for stock in data.get("undervalued", []):
        ticker = stock["ticker"]
        grade = stock.get("grade", "F")
        tests_passed = stock.get("testsPassed", 0)

        # Skip Grade F — no conviction
        if grade == "F":
            continue

        # Try to get fair value from report
        fair_value = None
        mispricing = None
        report_path = os.path.join(data_dir, "reports", f"{ticker}.json")
        if os.path.exists(report_path):
            with open(report_path) as f:
                report = json.load(f)
            verdict = report.get("report", {}).get("verdict", {})
            mispricing = verdict.get("mispricing")
            fair_value = verdict.get("fairValue")

        # Fallback: estimate fair value from valuation score
        price = stock.get("price", 0)
        if fair_value is None and price > 0:
            score = stock.get("valuationScore", 0)
            # Rough estimate: score represents % mispricing direction
            fair_value = price * (1 + abs(score) / 100 * 0.5)
            mispricing = -abs(score)

        if fair_value is None or mispricing is None:
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

        # Load detail for full test data
        detail_path = os.path.join(data_dir, "asx", "details", f"{ticker}.json")
        detail_tests = {}
        if os.path.exists(detail_path):
            with open(detail_path) as f:
                detail = json.load(f)
            detail_tests = detail.get("valuationTests", {})

        candidates.append({
            "ticker": ticker,
            "exchange": "ASX",
            "suffix": ".AX",
            "name": stock.get("name", ticker),
            "sector": stock.get("sector", ""),
            "mispricing": float(mispricing),
            "fairValue": float(fair_value),
            "price": price,
            "grade": grade,
            "testsPassed": tests_passed,
            "valuationTests": detail_tests,
        })

    # Sort by grade first (A > B > C > D), then by tests passed
    grade_order = {"A": 0, "B": 1, "C": 2, "D": 3, "F": 4}
    candidates.sort(key=lambda c: (grade_order.get(c["grade"], 4), -c["testsPassed"]))
    return candidates


# ═══════════════════════════════════════════════════════════
#  SMC ENTRY ANALYSIS
# ═══════════════════════════════════════════════════════════

def analyze_smc_entry(ticker, suffix, fair_value, portfolio_value, **kwargs):
    """
    Run full SMC analysis on a stock to determine if it's a valid entry.
    Returns (valid: bool, analysis: dict, stop_price: float, position_size: int)
    """
    # 1. Get daily data (3 months for structure analysis)
    hist, current_price = get_stock_data(ticker, suffix, period="3mo")
    if hist is None or current_price is None or current_price <= 0:
        return False, {"reason": "no data"}, 0, 0

    closes = hist["Close"].values
    highs = hist["High"].values
    lows = hist["Low"].values
    opens = hist["Open"].values
    volumes = hist["Volume"].values

    # 2. MULTI-TIMEFRAME: Weekly structure for bias
    weekly = get_weekly_data(ticker, suffix)
    weekly_bullish = False
    weekly_structure = {"trend": "unknown"}

    if weekly is not None:
        w_highs = weekly["High"].values
        w_lows = weekly["Low"].values
        w_closes = weekly["Close"].values
        weekly_structure = detect_market_structure(w_highs, w_lows, w_closes, lookback=3)
        weekly_bullish = weekly_structure["trend"] in (
            "bullish", "bullish_weak", "bullish_building"
        )
        # Also accept neutral with HL pattern (market recovering)
        if not weekly_bullish and weekly_structure.get("hl"):
            weekly_bullish = True

    if not weekly_bullish:
        return False, {
            "reason": f"weekly trend {weekly_structure['trend']}",
            "weeklyStructure": weekly_structure["trend"]
        }, 0, 0

    # 3. DAILY MARKET STRUCTURE
    daily_structure = detect_market_structure(highs, lows, closes)

    # Need bullish structure or CHoCH (reversal from bearish to bullish)
    structure_bullish = daily_structure["trend"] in ("bullish", "bullish_weak", "bullish_building")
    has_bos = daily_structure["bos"]
    has_choch = daily_structure["choch"]

    if not (structure_bullish or has_bos or has_choch):
        return False, {
            "reason": f"daily structure {daily_structure['trend']}, no BOS/CHoCH",
            "dailyStructure": daily_structure["trend"],
        }, 0, 0

    # 4. LIQUIDITY SWEEP check
    sweep = detect_liquidity_sweep(lows, closes, daily_structure.get("swingLows", []))

    # 5. FAIR VALUE GAP check
    fvgs = detect_fair_value_gap(highs, lows, closes)

    # 6. ORDER BLOCK check
    ob = detect_order_block(opens, highs, lows, closes)

    # 7. VOLUME confirmation
    if len(volumes) >= 20:
        avg_vol = float(np.mean(volumes[-21:-1]))
    else:
        avg_vol = float(np.mean(volumes[:-1])) if len(volumes) > 1 else 0
    vol_ratio = float(volumes[-1]) / avg_vol if avg_vol > 0 else 0

    # 8. RSI check (not overbought)
    rsi = calc_rsi(closes)

    # ── SCORING: How many SMC confluences align? ──
    score = 0
    confluences = []

    if structure_bullish:
        score += 2
        confluences.append("STRUCTURE")
    if has_bos:
        score += 2
        confluences.append("BOS")
    if has_choch:
        score += 3  # CHoCH is a strong signal
        confluences.append("CHoCH")
    if sweep.get("swept"):
        score += 3  # Liquidity sweep is very high value
        confluences.append("SWEEP")
    if fvgs:
        score += 2
        confluences.append("FVG")
    if ob:
        score += 1
        confluences.append("OB")
    if vol_ratio >= 1.2:
        score += 1
        confluences.append("VOL")
    if 25 <= rsi <= 60:
        score += 1
        confluences.append("RSI")

    # Need minimum 5 confluence points to enter
    min_score = 5
    if score < min_score:
        return False, {
            "reason": f"score {score}/{min_score} — {', '.join(confluences) or 'none'}",
            "score": score,
            "confluences": confluences,
        }, 0, 0

    # 9. STOP-LOSS placement (behind the most recent swing low — structure-based)
    swing_lows_list = daily_structure.get("swingLows", [])
    if swing_lows_list:
        stop_price = swing_lows_list[-1][1] * 0.995  # Tiny buffer below swing low
    else:
        stop_price = current_price * 0.94  # Fallback: 6% below

    # 10. RISK-REWARD calculation
    risk_per_share = current_price - stop_price
    if risk_per_share <= 0:
        return False, {"reason": "stop above current price"}, 0, 0

    reward_per_share = fair_value - current_price
    if reward_per_share <= 0:
        return False, {"reason": "already above fair value"}, 0, 0

    rr_ratio = reward_per_share / risk_per_share
    if rr_ratio < MIN_RR_RATIO:
        return False, {
            "reason": f"R:R {rr_ratio:.1f} < {MIN_RR_RATIO}",
            "rrRatio": round(rr_ratio, 1),
        }, 0, 0

    # 11. POSITION SIZING — use grade-based allocation OR risk-based, whichever is smaller
    risk_amount = portfolio_value * RISK_PER_TRADE_PCT
    shares_risk = int(risk_amount / risk_per_share)

    # Grade-based allocation cap (don't exceed the grade's max allocation)
    grade_alloc = GRADE_ALLOCATION.get(kwargs.get("grade", "D"), 0.03)
    max_position_value = portfolio_value * grade_alloc
    shares_alloc = int(max_position_value / current_price) if current_price > 0 else 0

    # Use the smaller of risk-based and allocation-based sizing
    shares = min(shares_risk, shares_alloc) if shares_alloc > 0 else shares_risk
    if shares <= 0:
        return False, {"reason": "position too small"}, 0, 0

    position_value = shares * current_price
    if position_value < MIN_TRADE_VALUE:
        return False, {"reason": f"value ${position_value:.0f} < min"}, 0, 0

    # ── ENTRY CONFIRMED ──
    analysis = {
        "score": score,
        "confluences": confluences,
        "weeklyTrend": weekly_structure["trend"],
        "dailyTrend": daily_structure["trend"],
        "bos": has_bos,
        "choch": has_choch,
        "sweep": sweep,
        "fvgCount": len(fvgs),
        "fvg": fvgs[0] if fvgs else None,
        "orderBlock": ob,
        "rsi": round(float(rsi), 1),
        "volRatio": round(float(vol_ratio), 2),
        "rrRatio": round(rr_ratio, 1),
        "riskPerShare": round(risk_per_share, 2),
        "riskAmount": round(risk_amount, 2),
    }

    return True, analysis, round(stop_price, 2), shares


# ═══════════════════════════════════════════════════════════
#  EXIT LOGIC
# ═══════════════════════════════════════════════════════════

def get_structure_stop(pos, hist):
    """
    Calculate stop-loss based on market structure (swing lows).
    As new higher lows form, the stop trails up.
    """
    if hist is None or len(hist) < 10:
        # Fallback to initial stop
        return pos.get("stopPrice", pos["entryPrice"] * 0.94)

    lows = hist["Low"].values
    highs = hist["High"].values
    closes = hist["Close"].values
    current_price = float(closes[-1])

    structure = detect_market_structure(highs, lows, closes)
    swing_lows = structure.get("swingLows", [])

    if not swing_lows:
        return pos.get("stopPrice", pos["entryPrice"] * 0.94)

    # Use the most recent swing low as the trailing stop
    latest_swing_low = swing_lows[-1][1]
    stop_price = latest_swing_low * 0.995  # Buffer below

    # Never move stop below the initial stop
    initial_stop = pos.get("initialStop", pos["entryPrice"] * 0.94)
    stop_price = max(stop_price, initial_stop)

    return round(stop_price, 2)


def check_exits(portfolio, now):
    """Check open positions for exit conditions using SMC structure."""
    exits = []
    remaining = []

    for pos in portfolio["openPositions"]:
        ticker = pos["ticker"]
        suffix = pos.get("suffix", ".AX")
        hist, current_price = get_stock_data(ticker, suffix, period="3mo")

        if current_price is None:
            remaining.append(pos)
            continue

        entry_price = pos["entryPrice"]
        risk_per_share = pos.get("riskPerShare", entry_price * 0.06)
        pnl_pct = (current_price - entry_price) / entry_price
        r_multiple = (current_price - entry_price) / risk_per_share if risk_per_share > 0 else 0

        # Update structure-based trailing stop
        new_stop = get_structure_stop(pos, hist)
        # Only move stop UP, never down
        pos["stopPrice"] = max(new_stop, pos.get("stopPrice", 0))

        # Track highest price and R-multiple
        highest = max(current_price, pos.get("highestPrice", current_price))
        pos["highestPrice"] = round(highest, 2)
        pos["rMultiple"] = round(r_multiple, 1)

        # Hold duration
        entry_date = datetime.fromisoformat(pos["entryDate"])
        hold_days = (now - entry_date).days

        exit_reason = None
        sell_ratio = 1.0

        # 1. Structure-based stop-loss
        if current_price <= pos["stopPrice"]:
            exit_reason = "STOP LOSS" if pnl_pct <= 0 else "TRAILING STOP"

        # 2. Partial profit at 3R
        elif r_multiple >= PARTIAL_PROFIT_R and not pos.get("partialTaken"):
            exit_reason = f"PARTIAL {PARTIAL_PROFIT_R:.0f}R"
            sell_ratio = PARTIAL_SELL_RATIO

        # 3. Fair value target hit
        elif current_price >= pos.get("fairValue", entry_price * 1.5) * 0.97:
            exit_reason = "TARGET HIT"

        # 4. Bearish CHoCH on daily — structure reversal
        elif hist is not None and len(hist) >= 10:
            closes = hist["Close"].values
            highs_arr = hist["High"].values
            lows_arr = hist["Low"].values
            struct = detect_market_structure(highs_arr, lows_arr, closes)
            if struct.get("chochBearish") and pnl_pct > 0:
                exit_reason = "CHoCH EXIT"

        # 5. Time-based exit for losing positions
        elif hold_days >= MAX_HOLD_DAYS and pnl_pct <= 0:
            exit_reason = "TIME EXIT"

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
                "rMultiple": round(r_multiple, 1),
                "exitReason": exit_reason,
            }
            exits.append(trade_record)
            portfolio["cash"] += round(current_price * shares_to_sell, 2)

            print(f"    EXIT  {ticker:8s} @ A${current_price:.2f}  "
                  f"P&L: A${pnl:+.2f} ({pnl_pct*100:+.1f}%) {r_multiple:+.1f}R  [{exit_reason}]")

            # Keep remaining shares if partial
            if remaining_shares > 0:
                pos["shares"] = remaining_shares
                pos["invested"] = round(entry_price * remaining_shares, 2)
                pos["partialTaken"] = True
                pos["currentPrice"] = round(current_price, 2)
                pos["pnl"] = round((current_price - entry_price) * remaining_shares, 2)
                pos["pnlPct"] = round(pnl_pct * 100, 2)
                remaining.append(pos)
        else:
            # Update tracking
            pos["currentPrice"] = round(current_price, 2)
            pos["pnl"] = round((current_price - entry_price) * pos["shares"], 2)
            pos["pnlPct"] = round(pnl_pct * 100, 2)
            remaining.append(pos)

    portfolio["openPositions"] = remaining
    return exits


def check_entries(portfolio, candidates, now):
    """Look for new SMC-confirmed entry opportunities."""
    entries = []
    open_tickers = {p["ticker"] for p in portfolio["openPositions"]}
    closed_tickers = {t["ticker"] for t in portfolio["tradeHistory"][-30:]}

    # Sector diversification
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
        if ticker in open_tickers or ticker in closed_tickers:
            continue
        if c["mispricing"] >= MIN_MISPRICING:
            continue

        sector = c.get("sector", "Unknown")
        if sector_counts.get(sector, 0) >= MAX_SECTOR_POSITIONS:
            continue

        # Run full SMC analysis with grade for position sizing
        valid, analysis, stop_price, shares = analyze_smc_entry(
            ticker, c["suffix"], c["fairValue"], portfolio["totalValue"],
            grade=c.get("grade", "D"),
        )

        if not valid:
            reason = analysis.get("reason", "unknown")
            if "weekly" not in reason and "no data" not in reason:
                print(f"    SKIP  {ticker:8s}  mispricing {c['mispricing']:.0f}%  — {reason}")
            continue

        # Check we can afford it
        _, current_price = get_stock_data(ticker, c["suffix"], period="5d")
        if current_price is None:
            continue

        cost = round(current_price * shares, 2)
        if cost > portfolio["cash"]:
            shares = int(portfolio["cash"] / current_price)
            cost = round(current_price * shares, 2)
        if shares <= 0 or cost < MIN_TRADE_VALUE:
            continue

        risk_per_share = current_price - stop_price
        target_price = c["fairValue"]
        grade = c.get("grade", "D")
        alloc_pct = GRADE_ALLOCATION.get(grade, 0.03)

        # Calculate suggested exit price:
        # Blended: 70% fair value + 30% technical target (entry + R*reward)
        rr_ratio = analysis.get("rrRatio", 3.0)
        technical_target = current_price + (risk_per_share * rr_ratio)
        exit_price = round(0.7 * target_price + 0.3 * technical_target, 2)

        position = {
            "ticker": ticker,
            "exchange": "ASX",
            "name": c["name"],
            "sector": c.get("sector", ""),
            "suffix": c["suffix"],
            "grade": grade,
            "allocationPct": round(alloc_pct * 100, 1),
            "entryPrice": round(current_price, 2),
            "currentPrice": round(current_price, 2),
            "targetPrice": round(target_price, 2),
            "exitPrice": exit_price,
            "stopPrice": round(stop_price, 2),
            "initialStop": round(stop_price, 2),
            "highestPrice": round(current_price, 2),
            "fairValue": c["fairValue"],
            "mispricing": c["mispricing"],
            "testsPassed": c.get("testsPassed", 0),
            "shares": shares,
            "invested": cost,
            "entryDate": now.isoformat(),
            "pnl": 0.0,
            "pnlPct": 0.0,
            "rMultiple": 0.0,
            "riskPerShare": round(risk_per_share, 2),
            "partialTaken": False,
            "smc": {
                "score": analysis["score"],
                "confluences": analysis["confluences"],
                "rrRatio": analysis["rrRatio"],
                "weeklyTrend": analysis["weeklyTrend"],
                "dailyTrend": analysis["dailyTrend"],
            },
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
            "grade": grade,
            "allocationPct": round(alloc_pct * 100, 1),
            "entryPrice": round(current_price, 2),
            "exitPrice": exit_price,
            "shares": shares,
            "invested": cost,
            "targetPrice": round(target_price, 2),
            "stopPrice": round(stop_price, 2),
            "mispricing": c["mispricing"],
            "testsPassed": c.get("testsPassed", 0),
            "entryDate": now.isoformat(),
            "smc": analysis,
        }
        entries.append(entry_record)

        conf_str = "+".join(analysis["confluences"])
        print(f"    ENTRY {ticker:8s} [Grade {grade}] @ A${current_price:.2f} x {shares} = A${cost:.2f}  "
              f"({alloc_pct*100:.0f}% alloc) Exit: A${exit_price:.2f}  "
              f"[{conf_str}] R:R={analysis['rrRatio']:.1f}")

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

    completed = [t for t in portfolio["tradeHistory"] if t.get("side") == "SELL"]
    portfolio["totalTrades"] = len(completed)
    portfolio["wins"] = sum(1 for t in completed if t.get("pnl", 0) > 0)
    portfolio["losses"] = sum(1 for t in completed if t.get("pnl", 0) <= 0)
    portfolio["winRate"] = round(
        portfolio["wins"] / max(1, portfolio["totalTrades"]) * 100, 1
    )

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

    curve = portfolio.get("equityCurve", [])
    curve.append({
        "date": datetime.now(timezone.utc).isoformat(),
        "value": portfolio["totalValue"],
    })
    if len(curve) > 200:
        curve = curve[-200:]
    portfolio["equityCurve"] = curve


# ═══════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Nick Knows Best — ASX Trading Engine v3 (SMC)")
    parser.add_argument("--reset", action="store_true", help="Reset portfolio to A$10,000")
    parser.add_argument("--live", action="store_true",
                        help="Live trading session: 30 min, 1-min price tracking")
    parser.add_argument("--maintain", action="store_true",
                        help="Maintain mode: update prices & check exits only")
    parser.add_argument("--cycles", type=int, default=30,
                        help="Number of 1-min cycles in live mode (default: 30)")
    args = parser.parse_args()

    # Default to maintain mode
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
        #  LIVE TRADING SESSION — SMC Analysis
        # ═══════════════════════════════════════════
        import time as _time

        total_cycles = args.cycles
        cycle_interval = 60
        entry_scan_every = 5

        print("\n" + "=" * 60)
        print("  🟢 LIVE SESSION — Smart Money Concepts v3")
        print(f"  {total_cycles} cycles × 1 min = {total_cycles} min")
        print(f"  Price tracking: 1 min | Entry scan: every {entry_scan_every} min")
        print(f"  Strategy: Market Structure + Liquidity + FVG + R:R")
        print(f"  Started: {now.strftime('%Y-%m-%d %H:%M UTC')}")
        print("=" * 60)

        for cycle in range(1, total_cycles + 1):
            cycle_time = datetime.now(timezone.utc)
            is_entry_cycle = (cycle == 1) or (cycle % entry_scan_every == 0)
            marker = "📡" if is_entry_cycle else "📈"
            print(f"\n  {marker} Cycle {cycle}/{total_cycles} ({cycle_time.strftime('%H:%M:%S UTC')})")

            # Always check exits
            exits = check_exits(portfolio, cycle_time)
            for exit_trade in exits:
                portfolio["tradeHistory"].append(exit_trade)
            if exits:
                for e in exits:
                    print(f"    🔴 EXIT {e['ticker']} {e['exitReason']}")

            # SMC entry scan on entry cycles
            if is_entry_cycle:
                print("    Scanning for SMC-confirmed entries...")
                candidates = load_candidates(data_dir)
                entries = check_entries(portfolio, candidates, cycle_time)
                for entry in entries:
                    portfolio["tradeHistory"].append(entry)

            # Update all open position prices
            for pos in portfolio["openPositions"]:
                hist, price = get_stock_data(pos["ticker"], pos.get("suffix", ".AX"), period="3mo")
                if price:
                    pos["currentPrice"] = round(price, 2)
                    pos["pnl"] = round((price - pos["entryPrice"]) * pos["shares"], 2)
                    pos["pnlPct"] = round((price / pos["entryPrice"] - 1) * 100, 2)
                    highest = max(price, pos.get("highestPrice", price))
                    pos["highestPrice"] = round(highest, 2)
                    new_stop = get_structure_stop(pos, hist)
                    pos["stopPrice"] = max(new_stop, pos.get("stopPrice", 0))

            # Save after every cycle
            update_stats(portfolio)
            if len(portfolio["tradeHistory"]) > 100:
                portfolio["tradeHistory"] = portfolio["tradeHistory"][-100:]
            with open(portfolio_path, "w") as f:
                json.dump(portfolio, f, indent=2)

            pos_summary = "  ".join(
                f"{p['ticker']}:{p['pnlPct']:+.1f}%"
                for p in portfolio["openPositions"]
            ) or "no positions"
            print(f"    A${portfolio['totalValue']:,.2f} ({portfolio['totalPnLPct']:+.1f}%) | {pos_summary}")

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

        print("\n  Checking exits...")
        exits = check_exits(portfolio, now)
        for exit_trade in exits:
            portfolio["tradeHistory"].append(exit_trade)
        if not exits:
            print("    No exits triggered")

        print("\n  Updating open positions...")
        for pos in portfolio["openPositions"]:
            hist, price = get_stock_data(pos["ticker"], pos.get("suffix", ".AX"), period="3mo")
            if price:
                pos["currentPrice"] = round(price, 2)
                pos["pnl"] = round((price - pos["entryPrice"]) * pos["shares"], 2)
                pos["pnlPct"] = round((price / pos["entryPrice"] - 1) * 100, 2)
                highest = max(price, pos.get("highestPrice", price))
                pos["highestPrice"] = round(highest, 2)
                new_stop = get_structure_stop(pos, hist)
                pos["stopPrice"] = max(new_stop, pos.get("stopPrice", 0))

        update_stats(portfolio)
        if len(portfolio["tradeHistory"]) > 100:
            portfolio["tradeHistory"] = portfolio["tradeHistory"][-100:]

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
