"""
Generate institutional-grade screener reports for the top N undervalued stocks
on each exchange, using existing pipeline data (no external API calls).

Usage:
    python scripts/generate_screener_reports.py --exchange ASX --top 50
    python scripts/generate_screener_reports.py --exchange NYSE --top 50
    python scripts/generate_screener_reports.py --all --top 50
"""

import json
import os
import sys
import argparse
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from score_stocks import run_valuation_tests, conviction_grade


def load_index(data_dir, exchange):
    """Load the index file for an exchange."""
    path = os.path.join(data_dir, f"{exchange.lower()}_index.json")
    with open(path) as f:
        return json.load(f)


def load_detail(data_dir, exchange, ticker):
    """Load detailed metrics for a specific stock."""
    path = os.path.join(data_dir, exchange.lower(), "details", f"{ticker}.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None


def fmt(val, suffix="", prefix="", decimals=2):
    """Format a numeric value, returning 'N/A' for None/NaN."""
    if val is None:
        return "N/A"
    try:
        f = float(val)
        if f != f:  # NaN check
            return "N/A"
        if suffix == "%":
            return f"{prefix}{f:.{decimals}f}%"
        elif suffix == "x":
            return f"{prefix}{f:.{decimals}f}x"
        else:
            return f"{prefix}{f:.{decimals}f}{suffix}"
    except (ValueError, TypeError):
        return "N/A"


def estimate_fair_value(metrics, price, score):
    """
    Estimate fair value using a multi-factor approach based on available metrics.
    Uses relative valuation (PE vs sector PE) and FCF yield to triangulate.
    """
    estimates = []
    weights = []

    pe = metrics.get("pe")
    sector_pe = metrics.get("sectorPe")
    forward_pe = metrics.get("forwardPe")
    pb = metrics.get("pb")
    ev_ebitda = metrics.get("evEbitda")
    fcf_yield = metrics.get("fcfYield")

    # Method 1: PE vs Sector PE relative valuation
    if pe and sector_pe and pe > 0 and sector_pe > 0:
        # Fair value = price * (sector_pe / pe) — if PE is below sector, stock is cheap
        fv = price * (sector_pe / pe)
        # Apply a dampening factor (don't assume full reversion)
        fv = price + (fv - price) * 0.7
        estimates.append(fv)
        weights.append(0.30)

    # Method 2: Forward PE re-rating
    if forward_pe and sector_pe and forward_pe > 0 and sector_pe > 0:
        # If forward PE is well below sector PE, there's re-rating potential
        fv = price * (sector_pe / forward_pe)
        fv = price + (fv - price) * 0.5  # Conservative dampening
        estimates.append(fv)
        weights.append(0.25)

    # Method 3: FCF yield implied value
    if fcf_yield and fcf_yield > 0:
        # Compare FCF yield to a "fair" FCF yield of ~5% for mature, ~3% for growth
        target_yield = 5.0
        if forward_pe and forward_pe < 15:
            target_yield = 6.0  # Value stocks should yield more
        elif forward_pe and forward_pe > 25:
            target_yield = 3.5  # Growth stocks can yield less
        fv = price * (fcf_yield / target_yield)
        estimates.append(fv)
        weights.append(0.20)

    # Method 4: EV/EBITDA-implied (use 10x as generic fair multiple)
    if ev_ebitda and ev_ebitda > 0:
        sector_ev = 12.0  # Generic fair multiple
        fv = price * (sector_ev / ev_ebitda)
        fv = price + (fv - price) * 0.5
        estimates.append(fv)
        weights.append(0.15)

    # Method 5: Score-based adjustment
    # Score is already a z-score composite — use it as a % adjustment
    score_adj = min(max(score * -0.5, -30), 30)  # Cap at ±30%
    score_fv = price * (1 + score_adj / 100)
    estimates.append(score_fv)
    weights.append(0.10)

    if not estimates:
        # Fallback: use score only
        return round(price * (1 + min(max(score * -0.5, -25), 25) / 100), 2)

    # Weighted average
    total_weight = sum(weights)
    weighted_fv = sum(e * w for e, w in zip(estimates, weights)) / total_weight
    return round(weighted_fv, 2)


def determine_beta_class(sector):
    """Estimate beta category based on sector."""
    low_beta = ["Consumer Defensive", "Consumer Staples", "Utilities",
                "Healthcare", "Real Estate", "Communication Services"]
    high_beta = ["Technology", "Consumer Cyclical", "Basic Materials",
                 "Energy", "Materials"]
    if sector in low_beta:
        return 0.7, "low"
    elif sector in high_beta:
        return 1.3, "high"
    else:
        return 1.0, "medium"


def generate_report_for_stock(stock_index, detail, exchange):
    """Generate a full report JSON for a single stock."""
    ticker = stock_index["ticker"]
    name = stock_index["name"]
    price = stock_index["price"]
    score = stock_index["valuationScore"]
    sector = stock_index.get("sector", "Unknown")
    mcap = stock_index.get("marketCap", "—")

    metrics = detail.get("metrics", {}) if detail else {}
    pe = metrics.get("pe")
    forward_pe = metrics.get("forwardPe")
    pb = metrics.get("pb")
    ev_ebitda = metrics.get("evEbitda")
    fcf_yield = metrics.get("fcfYield")
    div_yield = metrics.get("dividendYield")
    rev_growth = metrics.get("revenueGrowth")
    profit_margin = metrics.get("profitMargin")
    op_margin = metrics.get("operatingMargin")
    roe = metrics.get("roe")
    debt_equity = metrics.get("debtEquity")
    sector_pe = metrics.get("sectorPe")

    # Calculate fair value
    fair_value = estimate_fair_value(metrics, price, score)
    mispricing = round((price - fair_value) / fair_value * 100, 1)
    gap_pct = abs(mispricing)

    # Determine signal
    if mispricing < -15:
        signal = "undervalued"
        recommendation = "Potentially Undervalued"
    elif mispricing > 15:
        signal = "overvalued"
        recommendation = "Potentially Overvalued"
    else:
        signal = "fairlyvalued"
        recommendation = "Fairly Valued"
        if mispricing < -5:
            recommendation += " (lean undervalued)"
        elif mispricing > 5:
            recommendation += " (lean overvalued)"

    # Beta estimation
    est_beta, beta_class = determine_beta_class(sector)

    # Margin of safety based on beta
    if est_beta < 0.8:
        mos = 0.10
    elif est_beta <= 1.3:
        mos = 0.15
    else:
        mos = 0.22

    # Trade levels
    buy_lower = round(fair_value * (1 - mos), 2)
    buy_upper = round(fair_value * 0.95, 2)
    sell_trim = round(fair_value * 1.10, 2)
    sell_exit = round(fair_value * 1.20, 2)
    stop_loss = round(min(fair_value * 0.75, buy_lower * 0.85), 2)

    # Position sizing
    if beta_class == "low":
        max_position = "5%"
        vol_scale = "100%"
    elif beta_class == "medium":
        max_position = "3.75%"
        vol_scale = "75%"
    else:
        max_position = "2.5%"
        vol_scale = "50%"

    # Time horizon
    if gap_pct > 30:
        horizon = "2–4 years"
        pos_type = "CORE HOLD"
    elif gap_pct > 15:
        horizon = "12–24 months"
        pos_type = "CORE HOLD"
    else:
        horizon = "6–12 months"
        pos_type = "TACTICAL TRADE"

    # Currency
    currency = "A$" if exchange == "ASX" else "$"

    # === Build Report Sections ===

    executive_summary = (
        f"**{name}** ({ticker}) trades at {currency}{price:.2f} against our estimated fair value of "
        f"{currency}{fair_value:.2f}, implying a **{gap_pct:.1f}% {'discount' if mispricing < 0 else 'premium'}** "
        f"to intrinsic value. Valuation Score: {score:.1f}/100 (lower = more undervalued). "
        f"Sector: {sector}. Market Cap: {mcap}."
    )

    # Financial metrics table
    financial_analysis = (
        f"| Metric | Value | Assessment |\n"
        f"|--------|-------|------------|\n"
        f"| P/E (TTM) | {fmt(pe, 'x')} | {'Below' if pe and sector_pe and pe < sector_pe else 'Above'} sector median of {fmt(sector_pe, 'x')} |\n"
        f"| Forward P/E | {fmt(forward_pe, 'x')} | {'Attractive' if forward_pe and forward_pe < 20 else 'Moderate' if forward_pe and forward_pe < 30 else 'Elevated' if forward_pe else 'N/A'} |\n"
        f"| P/B Ratio | {fmt(pb, 'x')} | {'Below book' if pb and pb < 1 else 'Reasonable' if pb and pb < 3 else 'Premium' if pb else 'N/A'} |\n"
        f"| EV/EBITDA | {fmt(ev_ebitda, 'x')} | {'Cheap' if ev_ebitda and ev_ebitda < 8 else 'Fair' if ev_ebitda and ev_ebitda < 14 else 'Rich' if ev_ebitda else 'N/A'} |\n"
        f"| FCF Yield | {fmt(fcf_yield, '%')} | {'Strong' if fcf_yield and fcf_yield > 5 else 'Adequate' if fcf_yield and fcf_yield > 3 else 'Low' if fcf_yield else 'N/A'} |\n"
        f"| Dividend Yield | {fmt(div_yield, '%')} | {'High yield' if div_yield and div_yield > 4 else 'Moderate' if div_yield and div_yield > 2 else 'Low' if div_yield else 'N/A'} |\n"
        f"| Revenue Growth (YoY) | {fmt(rev_growth, '%')} | {'Strong' if rev_growth and rev_growth > 10 else 'Moderate' if rev_growth and rev_growth > 0 else 'Declining' if rev_growth else 'N/A'} |\n"
        f"| Profit Margin | {fmt(profit_margin, '%')} | {'Excellent' if profit_margin and profit_margin > 20 else 'Healthy' if profit_margin and profit_margin > 10 else 'Thin' if profit_margin and profit_margin > 0 else 'Negative' if profit_margin else 'N/A'} |\n"
        f"| Operating Margin | {fmt(op_margin, '%')} | {'Strong' if op_margin and op_margin > 20 else 'Adequate' if op_margin and op_margin > 10 else 'Weak' if op_margin else 'N/A'} |\n"
        f"| ROE | {fmt(roe, '%')} | {'Excellent' if roe and roe > 15 else 'Good' if roe and roe > 10 else 'Low' if roe else 'N/A'} |\n"
        f"| Debt/Equity | {fmt(debt_equity, '%')} | {'Conservative' if debt_equity and debt_equity < 50 else 'Moderate' if debt_equity and debt_equity < 100 else 'Leveraged' if debt_equity else 'N/A'} |"
    )

    # Business overview (sector-based)
    business_overview = (
        f"**{name}** operates in the **{sector}** sector on the {exchange}. "
        f"Market capitalisation of {mcap}. "
        f"{'Strong profitability with margins above sector norms.' if profit_margin and profit_margin > 15 else 'Profitability metrics suggest room for operational improvement.' if profit_margin and profit_margin < 5 else 'Margins are in line with sector expectations.'}\n\n"
        f"**Key Strengths**: "
        f"{'High FCF yield provides cash flow safety. ' if fcf_yield and fcf_yield > 5 else ''}"
        f"{'Attractive dividend for income investors. ' if div_yield and div_yield > 3 else ''}"
        f"{'Revenue growth trajectory is positive. ' if rev_growth and rev_growth > 5 else ''}"
        f"{'Strong return on equity signals efficient capital use. ' if roe and roe > 15 else ''}"
        f"{'Trades below book value — asset-backed floor. ' if pb and pb < 1 else ''}\n\n"
        f"**Key Concerns**: "
        f"{'High leverage warrants monitoring. ' if debt_equity and debt_equity > 100 else ''}"
        f"{'Revenue declining year-over-year. ' if rev_growth and rev_growth < 0 else ''}"
        f"{'Low return on equity. ' if roe and roe < 5 and roe is not None else ''}"
        f"{'Thin margins leave little room for error. ' if profit_margin and profit_margin < 5 and profit_margin is not None else ''}"
        f"{'No major red flags identified from available data.' if not (debt_equity and debt_equity > 100) and not (rev_growth and rev_growth < 0) else ''}"
    )

    # Valuation summary
    bear_case = round(fair_value * 0.80, 2)
    bull_case = round(fair_value * 1.25, 2)

    valuation_summary = (
        f"| Scenario | Target ({currency}) | Key Assumption |\n"
        f"|----------|-----------|----------------|\n"
        f"| Bear Case | {currency}{bear_case:.2f} | Multiple compression, earnings miss |\n"
        f"| **Base Case** | **{currency}{fair_value:.2f}** | **Current trajectory, sector re-rating** |\n"
        f"| Bull Case | {currency}{bull_case:.2f} | Earnings beat, multiple expansion |\n\n"
        f"**Weighted Fair Value**: {currency}{fair_value:.2f}\n"
        f"**Current Price**: {currency}{price:.2f}\n"
        f"**Mispricing**: {abs(mispricing):.1f}% {'undervalued' if mispricing < 0 else 'overvalued'}"
    )

    # DCF placeholder (estimated from multiples)
    valuation_dcf = (
        f"**Estimated Intrinsic Value Range**: {currency}{bear_case:.2f} – {currency}{bull_case:.2f}\n\n"
        f"Fair value derived from multi-factor model combining:\n"
        f"- P/E relative to sector median (30% weight)\n"
        f"- Forward P/E re-rating potential (25% weight)\n"
        f"- FCF yield implied value (20% weight)\n"
        f"- EV/EBITDA multiple analysis (15% weight)\n"
        f"- Composite valuation score (10% weight)\n\n"
        f"**Note**: This is an algorithmic estimate based on quantitative metrics. "
        f"For full DCF with explicit cash flow projections, refer to the AI deep-dive report if available."
    )

    # Comps section
    valuation_comps = (
        f"**Sector**: {sector}\n"
        f"**Sector Median P/E**: {fmt(sector_pe, 'x')}\n"
        f"**Stock P/E**: {fmt(pe, 'x')}\n\n"
        f"{'The stock trades at a **discount** to its sector median P/E, suggesting the market is pricing in lower growth expectations or temporary headwinds. If fundamentals normalise, re-rating toward the sector median would imply significant upside.' if pe and sector_pe and pe < sector_pe else 'The stock trades at a premium to sector median P/E. This may be justified by superior growth or quality metrics, but limits near-term upside from multiple expansion.' if pe and sector_pe else 'Insufficient comparable data for detailed peer analysis.'}"
    )

    # Assumptions
    assumptions = (
        f"**Valuation methodology**: Multi-factor quantitative model using publicly available financial data.\n\n"
        f"**Key assumptions**:\n"
        f"- Sector median multiples are used as fair value anchors\n"
        f"- FCF yield normalisation target: {'6%' if forward_pe and forward_pe < 15 else '5%' if forward_pe and forward_pe < 25 else '3.5%'} (based on growth profile)\n"
        f"- Estimated beta: {est_beta:.1f} ({beta_class} volatility)\n"
        f"- Terminal growth aligned with nominal GDP (~2.5%)\n\n"
        f"**Limitations**: This report uses static pipeline data. Live analyst consensus, short interest, insider activity, and options data are not included. Use this as a screening tool, not a final investment decision."
    )

    # Risks
    risks = (
        f"| Risk Factor | Assessment |\n"
        f"|-------------|------------|\n"
        f"| Valuation risk | {'Low — trades well below fair value' if mispricing < -15 else 'Moderate — near fair value' if abs(mispricing) < 15 else 'High — trades above fair value'} |\n"
        f"| Balance sheet | {'Conservative' if debt_equity and debt_equity < 50 else 'Moderate leverage' if debt_equity and debt_equity < 100 else 'High leverage — monitor closely' if debt_equity else 'Insufficient data'} |\n"
        f"| Profitability | {'Strong margins provide cushion' if profit_margin and profit_margin > 15 else 'Thin margins increase downside risk' if profit_margin and profit_margin < 5 else 'Adequate margins'} |\n"
        f"| Growth trajectory | {'Positive momentum' if rev_growth and rev_growth > 5 else 'Stable' if rev_growth and rev_growth > 0 else 'Declining — key risk factor' if rev_growth else 'No data'} |\n"
        f"| Sector exposure | {sector} — {'defensive, lower cyclical risk' if sector in ['Consumer Defensive', 'Healthcare', 'Utilities', 'Consumer Staples'] else 'cyclical, higher macro sensitivity' if sector in ['Materials', 'Energy', 'Basic Materials', 'Consumer Cyclical'] else 'moderate cyclicality'} |\n\n"
        f"**Trade Levels**:\n"
        f"- ✅ Buy Zone: {currency}{buy_lower:.2f} — {currency}{buy_upper:.2f}\n"
        f"- 🔴 Sell/Trim: {currency}{sell_trim:.2f} (trim) → {currency}{sell_exit:.2f} (exit)\n"
        f"- ⛔ Stop-Loss: {currency}{stop_loss:.2f}\n"
        f"- Max Position: {max_position} of portfolio ({vol_scale} scaling)\n"
        f"- Time Horizon: {horizon}\n"
        f"- Position Type: {pos_type}"
    )

    # Run valuation tests
    test_row = {
        "pe": pe, "sectorPe": sector_pe, "pb": pb, "evEbitda": ev_ebitda,
        "fcfYield": fcf_yield, "forwardPe": forward_pe,
        "profitMargin": profit_margin, "roe": roe,
    }
    valuation_tests = run_valuation_tests(test_row)
    tests_passed = sum(1 for t in valuation_tests.values() if t["passed"] is True)
    grade = conviction_grade(tests_passed)

    # Build the report JSON
    report = {
        "ticker": ticker,
        "name": name,
        "price": round(price, 2),
        "sector": sector,
        "marketCap": mcap,
        "valuationScore": float(score),
        "testsPassed": tests_passed,
        "grade": grade,
        "valuationTests": valuation_tests,
        "generatedAt": datetime.now(timezone(timedelta(hours=11))).isoformat(),
        "report": {
            "executiveSummary": executive_summary,
            "businessOverview": business_overview,
            "financialAnalysis": financial_analysis,
            "assumptions": assumptions,
            "valuationDCF": valuation_dcf,
            "valuationComps": valuation_comps,
            "valuationSummary": valuation_summary,
            "verdict": {
                "fairValue": fair_value,
                "currentPrice": round(price, 2),
                "mispricing": mispricing,
                "signal": signal,
                "recommendation": recommendation,
            },
            "risksAndSensitivity": risks,
        },
    }

    return report


def run(exchange, top_n, data_dir, reports_dir):
    """Generate reports for the top N undervalued stocks on an exchange."""
    print(f"\n{'='*60}")
    print(f"  SCREENER REPORT GENERATION — {exchange} (Top {top_n})")
    print(f"{'='*60}\n")

    # Load index
    index_data = load_index(data_dir, exchange)
    undervalued = sorted(
        index_data.get("undervalued", []),
        key=lambda x: x.get("valuationScore", 0)
    )

    # Filter out micro-caps (market cap < $50M)
    filtered = []
    for s in undervalued:
        mcap_str = s.get("marketCap", "0")
        # Parse market cap string
        try:
            if mcap_str.endswith("B"):
                mcap_val = float(mcap_str.replace("B", "")) * 1e9
            elif mcap_str.endswith("M"):
                mcap_val = float(mcap_str.replace("M", "")) * 1e6
            elif mcap_str.endswith("T"):
                mcap_val = float(mcap_str.replace("T", "")) * 1e12
            else:
                mcap_val = 0
        except ValueError:
            mcap_val = 0

        if mcap_val >= 50_000_000:  # $50M minimum
            filtered.append(s)

    stocks = filtered[:top_n]
    print(f"  Found {len(undervalued)} undervalued stocks")
    print(f"  After micro-cap filter (>$50M): {len(filtered)}")
    print(f"  Generating reports for top {len(stocks)}\n")

    os.makedirs(reports_dir, exist_ok=True)
    success = 0

    for i, stock in enumerate(stocks):
        ticker = stock["ticker"]
        detail = load_detail(data_dir, exchange, ticker)

        try:
            report = generate_report_for_stock(stock, detail, exchange)
            filepath = os.path.join(reports_dir, f"{ticker}.json")
            with open(filepath, "w") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            success += 1
            score = stock["valuationScore"]
            fv = report["report"]["verdict"]["fairValue"]
            gap = report["report"]["verdict"]["mispricing"]
            print(f"  {i+1:3d}. ✓ {ticker:8s} | Score: {score:>6.1f} | FV: ${fv:>10.2f} | Gap: {gap:>6.1f}%")
        except Exception as e:
            print(f"  {i+1:3d}. ✗ {ticker:8s} | Error: {str(e)[:80]}")

    print(f"\n  ✅ Generated {success}/{len(stocks)} reports → {reports_dir}")
    return success


def main():
    parser = argparse.ArgumentParser(description="Generate screener reports")
    parser.add_argument("--exchange", type=str, choices=["ASX", "NYSE", "NASDAQ"],
                        help="Exchange to generate reports for")
    parser.add_argument("--all", action="store_true",
                        help="Generate for all exchanges")
    parser.add_argument("--top", type=int, default=50,
                        help="Number of top undervalued stocks (default: 50)")
    args = parser.parse_args()

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(project_root, "public", "data")
    reports_dir = os.path.join(data_dir, "reports")

    exchanges = []
    if args.all:
        exchanges = ["ASX", "NYSE"]
    elif args.exchange:
        exchanges = [args.exchange]
    else:
        print("Please specify --exchange or --all")
        sys.exit(1)

    total = 0
    for ex in exchanges:
        total += run(ex, args.top, data_dir, reports_dir)

    print(f"\n{'='*60}")
    print(f"  COMPLETE: {total} reports generated across {len(exchanges)} exchanges")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
