"""
Fetch financial data for ASX stocks using yfinance.
"""

import yfinance as yf
import pandas as pd
import time
import sys
from config import ASX_TICKERS, SECTOR_MAP


def fetch_stock_data(tickers=None, batch_size=10, delay=1.0):
    """
    Fetch key financial metrics for ASX stocks.

    Args:
        tickers: List of ticker symbols (without .AX suffix). Defaults to ASX_TICKERS.
        batch_size: Number of tickers to fetch per batch.
        delay: Seconds to wait between batches to avoid rate limiting.

    Returns:
        pandas DataFrame with one row per stock.
    """
    if tickers is None:
        tickers = ASX_TICKERS

    all_data = []
    total = len(tickers)

    for i in range(0, total, batch_size):
        batch = tickers[i:i + batch_size]
        asx_batch = [f"{t}.AX" for t in batch]
        batch_str = " ".join(asx_batch)

        print(f"  Fetching batch {i // batch_size + 1}/{(total + batch_size - 1) // batch_size}: {', '.join(batch)}")

        try:
            data = yf.download(batch_str, period="5d", group_by="ticker", progress=False, threads=True)
        except Exception as e:
            print(f"  ⚠ Batch download failed: {e}")
            data = None

        for ticker in batch:
            asx_ticker = f"{ticker}.AX"
            try:
                stock = yf.Ticker(asx_ticker)
                info = stock.info

                if not info or info.get("regularMarketPrice") is None:
                    print(f"    ✗ {ticker}: No data available")
                    continue

                row = {
                    "ticker": ticker,
                    "name": info.get("shortName") or info.get("longName", ticker),
                    "sector": SECTOR_MAP.get(ticker, info.get("sector", "Unknown")),
                    "price": info.get("regularMarketPrice") or info.get("currentPrice"),
                    "marketCap": info.get("marketCap"),
                    "pe": info.get("trailingPE"),
                    "forwardPe": info.get("forwardPE"),
                    "pb": info.get("priceToBook"),
                    "evEbitda": info.get("enterpriseToEbitda"),
                    "dividendYield": info.get("dividendYield"),
                    "revenueGrowth": _pct(info.get("revenueGrowth")),
                    "profitMargin": _pct(info.get("profitMargins")),
                    "operatingMargin": _pct(info.get("operatingMargins")),
                    "roe": _pct(info.get("returnOnEquity")),
                    "debtEquity": info.get("debtToEquity"),
                    "fcf": info.get("freeCashflow"),
                }

                # Calculate FCF yield
                if row["fcf"] and row["marketCap"] and row["marketCap"] > 0:
                    row["fcfYield"] = round((row["fcf"] / row["marketCap"]) * 100, 2)
                else:
                    row["fcfYield"] = None

                # Skip stocks with no price
                if row["price"] is None or row["price"] <= 0:
                    print(f"    ✗ {ticker}: Invalid price")
                    continue

                all_data.append(row)
                print(f"    ✓ {ticker}: ${row['price']:.2f} | P/E: {_fmt(row['pe'])} | EV/EBITDA: {_fmt(row['evEbitda'])}")

            except Exception as e:
                print(f"    ✗ {ticker}: Error - {e}")
                continue

        # Rate limit between batches
        if i + batch_size < total:
            time.sleep(delay)

    df = pd.DataFrame(all_data)
    print(f"\n  Fetched data for {len(df)} / {total} stocks")
    return df


def _pct(val):
    """Convert decimal to percentage (0.15 → 15.0), or None."""
    if val is None or val != val:  # NaN check
        return None
    return round(val * 100, 2)


def _fmt(val):
    """Format a number for display, or return '—'."""
    if val is None or val != val:
        return "—"
    return f"{val:.1f}"


if __name__ == "__main__":
    # Quick test with a small subset
    test_tickers = sys.argv[1:] if len(sys.argv) > 1 else ["BHP", "CBA", "CSL", "XRO", "WDS"]
    print(f"Testing with: {test_tickers}\n")
    df = fetch_stock_data(tickers=test_tickers)
    print("\n" + df.to_string(index=False))
