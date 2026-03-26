"""
Fetch news, detect unusual volume, and scan insider transactions
for all tracked stocks. Outputs alerts.json for the website.

Usage:
    python scripts/fetch_alerts.py              # Full run
    python scripts/fetch_alerts.py --test-mode  # Test with 5 tickers
"""

import json
import os
import sys
import time
import argparse
from datetime import datetime, timezone, timedelta

import yfinance as yf
import pandas as pd


# Sentiment keywords for simple classification
POSITIVE_KEYWORDS = [
    "beat", "beats", "surge", "surges", "record", "upgrade", "upgraded",
    "raises", "raised", "strong", "growth", "profit", "rally", "boost",
    "bullish", "outperform", "buy", "positive", "dividend", "acquisition",
    "approve", "approved", "partnership", "deal", "breakout", "high",
    "revenue growth", "earnings beat", "exceeds", "exceeded", "soars"
]

NEGATIVE_KEYWORDS = [
    "miss", "misses", "decline", "declines", "cut", "cuts", "downgrade",
    "downgraded", "warning", "warns", "loss", "losses", "selloff",
    "sell-off", "bearish", "underperform", "sell", "negative", "lawsuit",
    "investigation", "recall", "bankruptcy", "crash", "plunge", "plunges",
    "layoff", "layoffs", "default", "fraud", "SEC", "probe", "fine",
    "risk", "debt", "deficit", "weak", "disappointing", "slump"
]


def classify_sentiment(title):
    """Simple sentiment classification from headline keywords."""
    title_lower = title.lower()
    pos = sum(1 for kw in POSITIVE_KEYWORDS if kw in title_lower)
    neg = sum(1 for kw in NEGATIVE_KEYWORDS if kw in title_lower)
    if pos > neg:
        return "positive"
    elif neg > pos:
        return "negative"
    return "neutral"


def severity_from_volume_ratio(ratio):
    """Map volume ratio to severity."""
    if ratio >= 4.0:
        return "critical"
    elif ratio >= 3.0:
        return "high"
    elif ratio >= 2.0:
        return "medium"
    return "low"


def fetch_news_alerts(ticker_obj, ticker, exchange):
    """Extract news headlines from a yfinance Ticker object."""
    alerts = []
    try:
        news = ticker_obj.news
        if not news:
            return alerts

        for item in news[:3]:  # Max 3 news per stock
            content = item.get("content", {})
            title = content.get("title", "")
            if not title:
                continue

            pub_date = content.get("pubDate", "")
            provider = content.get("provider", {})
            publisher = provider.get("displayName", "Unknown")

            # Skip old news (>7 days)
            if pub_date:
                try:
                    news_dt = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                    if (datetime.now(timezone.utc) - news_dt).days > 7:
                        continue
                except (ValueError, TypeError):
                    pass

            sentiment = classify_sentiment(title)
            sev = "medium" if sentiment == "negative" else "low"

            thumbnail = None
            thumb_data = content.get("thumbnail", {})
            if thumb_data:
                resolutions = thumb_data.get("resolutions", [])
                if resolutions:
                    thumbnail = resolutions[0].get("url")

            alerts.append({
                "type": "NEWS",
                "severity": sev,
                "ticker": ticker,
                "exchange": exchange,
                "headline": title,
                "detail": f"Source: {publisher}",
                "sentiment": sentiment,
                "thumbnail": thumbnail,
                "timestamp": pub_date or datetime.now(timezone.utc).isoformat(),
            })
    except Exception as e:
        pass  # Silently skip failures

    return alerts


def fetch_volume_alerts(ticker_obj, ticker, exchange):
    """Detect unusual volume spikes."""
    alerts = []
    try:
        hist = ticker_obj.history(period="1mo")
        if hist is None or hist.empty or len(hist) < 5:
            return alerts

        avg_vol = hist["Volume"].iloc[:-1].mean()  # Exclude today
        last_vol = hist["Volume"].iloc[-1]

        if avg_vol <= 0:
            return alerts

        ratio = last_vol / avg_vol

        if ratio >= 2.0:
            severity = severity_from_volume_ratio(ratio)
            label = "EXTREME VOLUME" if ratio >= 3.0 else "VOLUME SPIKE"

            # Also check price move
            if len(hist) >= 2:
                price_change = (hist["Close"].iloc[-1] - hist["Close"].iloc[-2]) / hist["Close"].iloc[-2] * 100
                direction = "up" if price_change > 0 else "down"
                price_note = f" | Price {direction} {abs(price_change):.1f}%"
            else:
                price_note = ""

            alerts.append({
                "type": label,
                "severity": severity,
                "ticker": ticker,
                "exchange": exchange,
                "headline": f"{ratio:.1f}x average volume detected",
                "detail": f"Volume: {last_vol:,.0f} vs 20-day avg: {avg_vol:,.0f}{price_note}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
    except Exception:
        pass

    return alerts


def fetch_insider_alerts(ticker_obj, ticker, exchange):
    """Detect significant insider transactions."""
    alerts = []
    try:
        insider = ticker_obj.insider_transactions
        if insider is None or insider.empty:
            return alerts

        # Filter recent transactions (last 30 days if date available)
        cutoff = datetime.now() - timedelta(days=30)

        for _, row in insider.head(10).iterrows():
            try:
                transaction = str(row.get("Transaction", "")).lower()
                shares = row.get("Shares", 0)
                value = row.get("Value", 0)
                insider_name = str(row.get("Insider", "Unknown"))
                position = str(row.get("Position", ""))
                start_date = row.get("Start Date", "")
                text = str(row.get("Text", ""))

                # Parse date
                if pd.notna(start_date):
                    try:
                        if isinstance(start_date, str):
                            tx_date = datetime.strptime(start_date, "%Y-%m-%d")
                        else:
                            tx_date = pd.Timestamp(start_date).to_pydatetime()
                        if tx_date < cutoff:
                            continue
                    except (ValueError, TypeError):
                        pass

                if not shares or shares == 0:
                    continue

                # Classify the transaction
                is_purchase = any(kw in transaction for kw in ["purchase", "buy", "acquisition"])
                is_sale = any(kw in transaction for kw in ["sale", "sell", "disposition"])

                # Also check the Text field for clues
                text_lower = text.lower()
                if "purchase" in text_lower or "buy" in text_lower:
                    is_purchase = True
                if "sale" in text_lower or "sell" in text_lower:
                    is_sale = True

                if not is_purchase and not is_sale:
                    # Try to infer from the text/transaction field
                    if "stock gift" in text_lower or "gift" in text_lower:
                        continue  # Skip gifts
                    continue

                # Calculate value if missing
                if pd.isna(value) or value == 0:
                    # Can't determine significance without value
                    value_str = f"{shares:,.0f} shares"
                    severity = "low"
                else:
                    value = float(value)
                    value_str = f"${value:,.0f}" if value >= 1000 else f"${value:.0f}"
                    if value >= 1_000_000:
                        severity = "high"
                    elif value >= 100_000:
                        severity = "medium"
                    else:
                        severity = "low"

                if is_purchase:
                    alert_type = "INSIDER_BUY"
                    headline = f"{insider_name} ({position}) purchased {shares:,.0f} shares"
                    if value and value > 0:
                        headline += f" ({value_str})"
                elif is_sale:
                    alert_type = "INSIDER_SELL"
                    headline = f"{insider_name} ({position}) sold {shares:,.0f} shares"
                    if value and value > 0:
                        headline += f" ({value_str})"
                else:
                    continue

                alerts.append({
                    "type": alert_type,
                    "severity": severity,
                    "ticker": ticker,
                    "exchange": exchange,
                    "headline": headline,
                    "detail": text if text and text != "nan" else f"Transaction date: {start_date}",
                    "timestamp": str(start_date) if pd.notna(start_date) else datetime.now(timezone.utc).isoformat(),
                })

            except Exception:
                continue

    except Exception:
        pass

    return alerts


def fetch_price_move_alerts(ticker_obj, ticker, exchange):
    """Detect significant single-day price moves."""
    alerts = []
    try:
        hist = ticker_obj.history(period="5d")
        if hist is None or hist.empty or len(hist) < 2:
            return alerts

        last_close = hist["Close"].iloc[-1]
        prev_close = hist["Close"].iloc[-2]
        pct_change = (last_close - prev_close) / prev_close * 100

        if abs(pct_change) >= 5.0:
            direction = "surged" if pct_change > 0 else "plunged"
            severity = "critical" if abs(pct_change) >= 10 else "high"

            alerts.append({
                "type": "PRICE_MOVE",
                "severity": severity,
                "ticker": ticker,
                "exchange": exchange,
                "headline": f"Stock {direction} {abs(pct_change):.1f}% in one session",
                "detail": f"${prev_close:.2f} → ${last_close:.2f}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
    except Exception:
        pass

    return alerts


def load_tickers(data_dir, exchange):
    """Load the list of tickers from an exchange index file."""
    path = os.path.join(data_dir, f"{exchange.lower()}_index.json")
    if not os.path.exists(path):
        return []
    with open(path) as f:
        data = json.load(f)
    all_stocks = data.get("undervalued", []) + data.get("overvalued", [])
    return [s["ticker"] for s in all_stocks]


def main():
    parser = argparse.ArgumentParser(description="Fetch market alerts")
    parser.add_argument("--test-mode", action="store_true",
                        help="Run on 5 tickers only for testing")
    args = parser.parse_args()

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(project_root, "public", "data")
    output_path = os.path.join(data_dir, "alerts.json")

    exchanges = {
        "ASX": ".AX",
        "NYSE": "",
        "NASDAQ": "",
    }

    all_alerts = []
    total_scanned = 0

    print("=" * 60)
    print("  MARKET INTELLIGENCE SCANNER")
    print("=" * 60)

    for exchange, suffix in exchanges.items():
        tickers = load_tickers(data_dir, exchange)
        if args.test_mode:
            tickers = tickers[:5]

        print(f"\n  📡 Scanning {exchange} ({len(tickers)} tickers)...")

        for i, ticker in enumerate(tickers):
            yf_ticker = f"{ticker}{suffix}"
            try:
                t = yf.Ticker(yf_ticker)

                # Fetch all alert types
                news = fetch_news_alerts(t, ticker, exchange)
                volume = fetch_volume_alerts(t, ticker, exchange)
                insider = fetch_insider_alerts(t, ticker, exchange)
                price = fetch_price_move_alerts(t, ticker, exchange)

                alerts = news + volume + insider + price
                all_alerts.extend(alerts)
                total_scanned += 1

                alert_count = len(alerts)
                if alert_count > 0:
                    types = ", ".join(set(a["type"] for a in alerts))
                    print(f"    {i+1:3d}. {ticker:8s} → {alert_count} alert(s): {types}")

            except Exception as e:
                pass

            # Rate limiting: small delay to avoid throttling
            if (i + 1) % 10 == 0:
                time.sleep(1)

    # Sort alerts by severity (critical > high > medium > low) then by timestamp
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    all_alerts.sort(key=lambda a: (
        severity_order.get(a.get("severity", "low"), 3),
        a.get("timestamp", ""),
    ))

    # Limit total alerts to prevent huge file
    max_alerts = 200
    if len(all_alerts) > max_alerts:
        # Keep all critical/high, trim medium/low
        critical_high = [a for a in all_alerts if a["severity"] in ("critical", "high")]
        medium_low = [a for a in all_alerts if a["severity"] not in ("critical", "high")]
        all_alerts = critical_high + medium_low[:max_alerts - len(critical_high)]

    # Write output
    output = {
        "lastUpdated": datetime.now(timezone(timedelta(hours=11))).isoformat(),
        "stocksScanned": total_scanned,
        "totalAlerts": len(all_alerts),
        "alerts": all_alerts,
    }

    with open(output_path, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    # Summary
    type_counts = {}
    for a in all_alerts:
        t = a["type"]
        type_counts[t] = type_counts.get(t, 0) + 1

    print(f"\n{'=' * 60}")
    print(f"  SCAN COMPLETE")
    print(f"  Stocks scanned: {total_scanned}")
    print(f"  Total alerts: {len(all_alerts)}")
    for t, c in sorted(type_counts.items()):
        print(f"    {t}: {c}")
    print(f"  Output: {output_path}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
