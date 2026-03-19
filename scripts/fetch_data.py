"""
Fetch financial data for ASX, NYSE, and NASDAQ stocks using yfinance.
"""

import yfinance as yf
import pandas as pd
import time
import sys
import re

def fetch_stock_data(tickers=None, exchange="ASX", batch_size=10, delay=1.0):
    if tickers is None:
        from config import ASX_TICKERS, NYSE_TICKERS, NASDAQ_TICKERS
        if exchange == "NYSE":
            tickers = NYSE_TICKERS
        elif exchange == "NASDAQ":
            tickers = NASDAQ_TICKERS
        else:
            tickers = ASX_TICKERS

    from config import SECTOR_MAP
    all_data = []
    total = len(tickers)

    for i in range(0, total, batch_size):
        batch = tickers[i:i + batch_size]
        yf_batch = [f"{t}.AX" if exchange == "ASX" else t for t in batch]
        batch_str = " ".join(yf_batch)

        print(f"  Fetching batch {i // batch_size + 1}/{(total + batch_size - 1) // batch_size}: {', '.join(batch)}")

        try:
            data = yf.download(batch_str, period="5d", group_by="ticker", progress=False, threads=True)
        except Exception as e:
            print(f"  ⚠ Batch download failed: {e}")
            data = None

        for idx, ticker in enumerate(batch):
            yf_ticker = yf_batch[idx]
            try:
                stock = yf.Ticker(yf_ticker)
                info = stock.info

                if not info or (info.get("regularMarketPrice") is None and info.get("currentPrice") is None):
                    print(f"    ✗ {ticker}: No data available")
                    continue

                hist = stock.history(period="1y")
                chart_data = []
                if not hist.empty:
                    weekly = hist['Close'].resample('W').last().dropna()
                    chart_data = [round(x, 2) for x in weekly.tolist()]

                website = info.get("website", "")
                domain = ""
                if website:
                    match = re.search(r'https?://(?:www\.)?([^/]+)', website)
                    if match:
                        domain = match.group(1)

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
                    "domain": domain,
                    "chartData": chart_data,
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
                print(f"    ✓ {ticker}: ${row['price']:.2f} | P/E: {_fmt(row['pe'])}")

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
    if val is None or val != val: return None
    return round(val * 100, 2)

def _fmt(val):
    if val is None or val != val: return "—"
    return f"{val:.1f}"

if __name__ == "__main__":
    test_tickers = sys.argv[1:] if len(sys.argv) > 1 else ["BHP", "CBA"]
    print(f"Testing with: {test_tickers}\n")
    df = fetch_stock_data(tickers=test_tickers, exchange="ASX")
    print("\n" + df.to_string(index=False))
