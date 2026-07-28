"""
Nick Knows Best — Daily Picks Generator

Replaces the cycle-based system with daily-refreshed picks.
Sources:
  1. Internal valuation pipeline (ASX index data)
  2. yfinance analyst recommendations (upgrades, strong buys)
  3. Advisory signal scraping from Google News RSS (Motley Fool, Bell Potter, etc.)
  4. Gemini AI qualitative screening

Outputs: public/data/picks.json
"""

import json
import os
import sys
import time
import re
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import yfinance as yf

try:
    import feedparser
except ImportError:
    os.system(f"{sys.executable} -m pip install feedparser")
    import feedparser

from macro_scanner import get_macro_biases, _find_sector_bias, _bias_label

# ── Configuration ──
NUM_PICKS = 5
MIN_MARKET_CAP = 300_000_000  # $300M
AEST = timezone(timedelta(hours=10))

# Advisory sources to scrape for buy signals
ADVISORY_RSS_QUERIES = [
    "ASX stock upgrade buy recommendation analyst",
    "ASX shares broker upgrade strong buy",
    "Motley Fool ASX buy shares recommendation",
    "ASX small cap best stocks to buy",
    "Bell Potter Macquarie ASX upgrade",
]

# Known advisory sources with track records
TRUSTED_SOURCES = [
    "motley fool", "fool.com.au", "bell potter", "macquarie",
    "morgan stanley", "goldman sachs", "ubs", "citi", "jp morgan",
    "morningstar", "livewire", "marcus today", "intelligent investor",
    "wilson asset", "forager", "afr", "stockhead", "simply wall st",
]


def parse_market_cap(mc_str):
    if not mc_str or mc_str == "—":
        return 0
    mc = str(mc_str).strip()
    try:
        if mc.endswith("T"): return float(mc[:-1]) * 1e12
        elif mc.endswith("B"): return float(mc[:-1]) * 1e9
        elif mc.endswith("M"): return float(mc[:-1]) * 1e6
        else: return float(mc)
    except ValueError:
        return 0


def fetch_advisory_signals():
    """Scrape Google News RSS for analyst upgrade/buy signals on ASX stocks.
    Returns dict: ticker -> {source, headline, sentiment_boost}"""
    signals = {}
    print("  📡 Scraping advisory signals from financial news...")

    for query in ADVISORY_RSS_QUERIES:
        try:
            url = f"https://news.google.com/rss/search?q={query.replace(' ', '+')}&hl=en-AU&gl=AU&ceid=AU:en"
            feed = feedparser.parse(url)
            for entry in feed.entries[:15]:
                title = entry.get("title", "")
                title_lower = title.lower()

                # Check if from trusted source
                source_match = None
                for src in TRUSTED_SOURCES:
                    if src in title_lower or src in str(entry.get("source", {}).get("title", "")).lower():
                        source_match = src
                        break

                if not source_match:
                    continue

                # Extract ASX ticker mentions (3-letter codes)
                tickers_found = re.findall(r'\b([A-Z]{3})\b', title)
                # Also check for ASX:XXX pattern
                tickers_found += re.findall(r'ASX[:\s]+([A-Z]{3})', title)

                # Check for buy/upgrade signals
                is_buy = any(kw in title_lower for kw in [
                    "buy", "upgrade", "outperform", "overweight", "strong buy",
                    "top pick", "best stock", "conviction", "accumulate",
                    "undervalued", "bullish", "breakout", "recommend",
                ])

                if is_buy and tickers_found:
                    for ticker in set(tickers_found):
                        if ticker not in signals or signals[ticker]["boost"] < 2.0:
                            signals[ticker] = {
                                "source": source_match.title(),
                                "headline": re.sub(r'\s*[-–—]\s*[^-–—]+$', '', title).strip()[:120],
                                "boost": 2.0 if "strong buy" in title_lower or "top pick" in title_lower else 1.5,
                                "timestamp": entry.get("published", ""),
                            }
            time.sleep(0.5)
        except Exception as e:
            print(f"    ⚠ RSS fetch failed: {str(e)[:60]}")

    print(f"    ✓ Found {len(signals)} advisory buy signals")
    for t, s in list(signals.items())[:5]:
        print(f"      {t}: {s['source']} — {s['headline'][:80]}")
    return signals


def fetch_analyst_recs(ticker):
    """Get analyst recommendation data from yfinance.
    Returns (consensus, upgrade_boost) or (None, 0)."""
    try:
        t = yf.Ticker(f"{ticker}.AX")
        recs = t.recommendations
        if recs is None or recs.empty:
            return None, 0

        # Get most recent recommendations
        recent = recs.tail(5)
        grades = []
        for _, row in recent.iterrows():
            grade = str(row.get("To Grade", row.get("toGrade", ""))).lower()
            if not grade or grade == "nan":
                continue
            grades.append(grade)

        if not grades:
            return None, 0

        # Score based on consensus
        buy_count = sum(1 for g in grades if any(kw in g for kw in ["buy", "outperform", "overweight", "accumulate"]))
        sell_count = sum(1 for g in grades if any(kw in g for kw in ["sell", "underperform", "underweight", "reduce"]))

        if buy_count >= 3:
            return "Strong Buy", 3.0
        elif buy_count >= 2:
            return "Buy", 2.0
        elif buy_count >= 1 and sell_count == 0:
            return "Moderate Buy", 1.0
        elif sell_count >= 2:
            return "Sell", -3.0
        else:
            return "Hold", 0
    except Exception:
        return None, 0


def check_price_trend(detail):
    """Check if stock is in acceptable price trend."""
    chart = detail.get("chartData", [])
    if len(chart) < 12:
        return True, 0.0

    current = chart[-1].get("price", 0)
    if current <= 0:
        return False, 0.0

    price_3m = chart[-12].get("price", current)
    change_3m = ((current - price_3m) / price_3m * 100) if price_3m > 0 else 0

    momentum = round(max(-1.0, min(1.0, change_3m / 20)), 2)

    if change_3m < -20:
        return False, momentum
    return True, momentum


def load_detail(details_dir, ticker):
    path = os.path.join(details_dir, f"{ticker}.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None


def qualify_with_gemini(picks, details_dir):
    """Run Gemini adversarial screening on candidates."""
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        print("  ⚠ No Gemini API key — skipping qualitative screening")
        for p in picks:
            p["qualScore"] = None
            p["qualPassed"] = True
        return picks

    try:
        from google import genai
        client = genai.Client(api_key=key)
    except Exception:
        for p in picks:
            p["qualScore"] = None
            p["qualPassed"] = True
        return picks

    print(f"  🧠 Running AI conviction screening on {len(picks)} candidates...")

    for p in picks:
        detail = load_detail(details_dir, p["ticker"])
        metrics_ctx = ""
        if detail:
            m = detail.get("metrics", {})
            metrics_ctx = f"""
    P/E: {m.get('pe', 'N/A')}, Forward P/E: {m.get('forwardPe', 'N/A')}
    P/B: {m.get('pb', 'N/A')}, EV/EBITDA: {m.get('evEbitda', 'N/A')}
    FCF Yield: {m.get('fcfYield', 'N/A')}%, ROE: {m.get('roe', 'N/A')}%
    Revenue Growth: {m.get('revenueGrowth', 'N/A')}%"""

        advisory_note = ""
        if p.get("advisorySource"):
            advisory_note = f"\nAdvisory Signal: {p['advisorySource']} — {p.get('advisoryHeadline', '')}"
        if p.get("analystConsensus"):
            advisory_note += f"\nAnalyst Consensus: {p['analystConsensus']}"

        prompt = f"""You are a ruthlessly honest ASX equity analyst. Evaluate this stock as a SHORT-TERM buy (1-4 weeks).

Stock: {p['name']} ({p['ticker']}.AX)
Sector: {p['sector']} | Market Cap: {p['marketCap']} | Price: A${p['price']:.2f}
Valuation Grade: {p['grade']} ({p['testsPassed']}/8 tests passed)
Macro: {p.get('macroLabel', 'Neutral')}{metrics_ctx}{advisory_note}

Score this stock's short-term conviction from 1-10.
A score of 6+ means you'd invest for 1-4 weeks.

Return ONLY this JSON:
{{
  "conviction": 1-10,
  "catalyst": "What could move this stock up in the near term",
  "risk": "Biggest downside risk",
  "recommendation": "buy|hold|avoid",
  "thesis": "2-3 sentence investment thesis"
}}"""

        try:
            response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
            text = response.text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
            if text.endswith("```"):
                text = text.rsplit("```", 1)[0]

            result = json.loads(text.strip())
            conviction = result.get("conviction", 5)
            p["qualScore"] = conviction
            p["thesis"] = result.get("thesis", p.get("thesis", ""))
            p["catalyst"] = result.get("catalyst", "")
            p["risk"] = result.get("risk", "")
            p["qualPassed"] = conviction >= 6 and result.get("recommendation") != "avoid"

            icon = "✅" if p["qualPassed"] else "❌"
            print(f"    {icon} {p['ticker']}: conviction={conviction}/10 → {result.get('recommendation', '?')}")
        except Exception as e:
            print(f"    ⚠ {p['ticker']}: AI screen failed ({str(e)[:60]})")
            p["qualScore"] = None
            p["qualPassed"] = True

        time.sleep(1.5)

    return picks


def generate_daily_picks():
    """Main daily picks generation."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(project_root, "public", "data")
    details_dir = os.path.join(data_dir, "asx", "details")
    output_path = os.path.join(data_dir, "picks.json")

    now = datetime.now(AEST)

    print("=" * 60)
    print("  NICK KNOWS BEST — Daily Picks Generator")
    print(f"  {now.strftime('%A %d %B %Y, %I:%M %p AEST')}")
    print("=" * 60)

    # Load index data
    index_path = os.path.join(data_dir, "asx_index.json")
    if not os.path.exists(index_path):
        print("❌ No asx_index.json found. Run the pipeline first.")
        sys.exit(1)

    with open(index_path) as f:
        index_data = json.load(f)

    undervalued = index_data.get("undervalued", [])
    print(f"\n  📊 {len(undervalued)} undervalued stocks in pipeline")

    # Step 1: Get macro biases
    print("\n  🌍 Running macro scan...")
    sector_biases, macro_context = get_macro_biases()
    print(f"     Headline: {macro_context.get('headline', 'N/A')}")

    # Step 2: Fetch advisory signals
    advisory_signals = fetch_advisory_signals()

    # Step 3: Score and rank candidates
    print("\n  🏆 Scoring candidates...")
    candidates = []

    for s in undervalued:
        grade = s.get("grade", "F")
        if grade in ("F",):
            continue

        mc = parse_market_cap(s.get("marketCap", "0"))
        if mc < MIN_MARKET_CAP:
            continue

        sector = s.get("sector", "Unknown")
        bias = _find_sector_bias(sector, sector_biases)

        # Skip only extreme headwinds
        if bias <= -0.8:
            continue

        # Load detail for deeper analysis
        detail = load_detail(details_dir, s["ticker"])
        if detail:
            m = detail.get("metrics", {})
            pm = m.get("profitMargin")
            if pm is not None and pm < 0:
                continue  # Must be profitable

            # Price trend check
            trend_ok, momentum = check_price_trend(detail)
            if not trend_ok:
                continue
        else:
            momentum = 0.0

        # Base score from valuation
        grade_scores = {"A": 5, "B": 4, "C": 3, "D": 2}
        base_score = grade_scores.get(grade, 1) + (s.get("testsPassed", 0) * 0.5)

        # Macro boost/penalty
        macro_boost = bias * 2.0

        # Advisory signal boost
        advisory_boost = 0
        adv_signal = advisory_signals.get(s["ticker"])
        if adv_signal:
            advisory_boost = adv_signal["boost"]

        # Analyst consensus boost
        analyst_consensus, analyst_boost = fetch_analyst_recs(s["ticker"])

        # Momentum boost
        momentum_boost = momentum * 1.5

        # Combined score
        total_score = base_score + macro_boost + advisory_boost + analyst_boost + momentum_boost

        candidate = {
            "ticker": s["ticker"],
            "name": s.get("name", s["ticker"]),
            "sector": sector,
            "grade": grade,
            "testsPassed": s.get("testsPassed", 0),
            "price": s.get("price", 0),
            "marketCap": s.get("marketCap", "—"),
            "valuationScore": s.get("valuationScore", 0),
            "macroLabel": _bias_label(bias),
            "macroBias": round(bias, 2),
            "advisorySource": adv_signal["source"] if adv_signal else None,
            "advisoryHeadline": adv_signal["headline"] if adv_signal else None,
            "analystConsensus": analyst_consensus,
            "analystBoost": round(analyst_boost, 1),
            "_totalScore": round(total_score, 2),
            "momentum": momentum,
        }
        candidates.append(candidate)

    print(f"  → {len(candidates)} candidates after filtering")

    # Sort by total score
    candidates.sort(key=lambda x: -x["_totalScore"])

    # Sector diversification — max 2 per sector
    diversified = []
    sector_counts = {}
    for c in candidates:
        sec = c["sector"]
        if sector_counts.get(sec, 0) >= 2:
            continue
        diversified.append(c)
        sector_counts[sec] = sector_counts.get(sec, 0) + 1
        if len(diversified) >= NUM_PICKS * 3:  # Send 3x to AI screen
            break

    # Step 4: Qualitative AI screening
    picks = qualify_with_gemini(diversified[:NUM_PICKS * 2], details_dir)

    # Filter passed picks
    passed = [p for p in picks if p.get("qualPassed", True)]
    rejected = [p for p in picks if not p.get("qualPassed", True)]

    if rejected:
        print(f"\n  🚫 Rejected {len(rejected)} picks:")
        for r in rejected:
            print(f"     ✗ {r['ticker']} (conviction {r.get('qualScore', '?')}/10)")

    # Sort by conviction score, take top N
    passed.sort(key=lambda p: -(p.get("qualScore") or 0))
    final_picks = passed[:NUM_PICKS]

    # Build thesis for picks without one
    for i, p in enumerate(final_picks, 1):
        p["rank"] = i
        # Clean up internal scoring fields
        p.pop("_totalScore", None)
        p.pop("qualPassed", None)
        if not p.get("thesis"):
            p["thesis"] = f"Grade {p['grade']} with {p['testsPassed']}/8 valuation tests passed. {p['sector']} sector."

    # Step 5: Write output
    output = {
        "generatedAt": now.isoformat(),
        "date": now.strftime("%d %B %Y"),
        "status": "live",
        "totalAnalyzed": len(undervalued),
        "picks": final_picks,
        "macro": {
            "headline": macro_context.get("headline", ""),
            "themes": macro_context.get("themes", [])[:3],
            "source": macro_context.get("source", ""),
        },
    }

    with open(output_path, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n  ✓ Saved {len(final_picks)} picks to {output_path}")
    print("\n  📋 Today's Picks:")
    for p in final_picks:
        adv = f" | 📰 {p['advisorySource']}" if p.get("advisorySource") else ""
        analyst = f" | 🏦 {p['analystConsensus']}" if p.get("analystConsensus") else ""
        print(f"    #{p['rank']} {p['ticker']:<6} Grade {p['grade']} ({p['testsPassed']}/8)"
              f" | A${p['price']:.2f} | Q:{p.get('qualScore', '?')}/10{adv}{analyst}")

    print("\n" + "=" * 60)
    print("  ✅ DAILY PICKS COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    generate_daily_picks()
