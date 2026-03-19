"""
Generate AI equity research reports using Google Gemini 2.5 Flash.
"""

import json
import time
import os
import re
import google.generativeai as genai
from config import ANALYST_PROMPT, format_market_cap


def setup_gemini():
    """Configure the Gemini API client."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY environment variable not set.\n"
            "Get a free key at: https://aistudio.google.com/apikey"
        )
    genai.configure(api_key=api_key)
    return genai.GenerativeModel("gemini-2.5-flash")


def generate_report(model, stock_data, sector_medians, retry_count=2):
    """
    Generate a full equity research report for a single stock.

    Args:
        model: Gemini GenerativeModel instance
        stock_data: Dict with stock financial data
        sector_medians: Dict with sector median values
        retry_count: Number of retries on failure

    Returns:
        Dict with structured report, or None on failure
    """
    ticker = stock_data["ticker"]

    # Fill in the prompt template
    prompt = ANALYST_PROMPT.format(
        ticker=ticker,
        name=stock_data.get("name", ticker),
        sector=stock_data.get("sector", "Unknown"),
        price=stock_data.get("price", 0),
        market_cap=format_market_cap(stock_data.get("marketCap")),
        pe=_fmt_metric(stock_data.get("pe")),
        forward_pe=_fmt_metric(stock_data.get("forwardPe")),
        pb=_fmt_metric(stock_data.get("pb")),
        ev_ebitda=_fmt_metric(stock_data.get("evEbitda")),
        dividend_yield=_fmt_pct(stock_data.get("dividendYield")),
        revenue_growth=_fmt_pct(stock_data.get("revenueGrowth")),
        profit_margin=_fmt_pct(stock_data.get("profitMargin")),
        operating_margin=_fmt_pct(stock_data.get("operatingMargin")),
        roe=_fmt_pct(stock_data.get("roe")),
        debt_equity=_fmt_metric(stock_data.get("debtEquity")),
        fcf=_fmt_currency(stock_data.get("fcf")),
        fcf_yield=_fmt_pct(stock_data.get("fcfYield")),
        sector_pe=_fmt_metric(sector_medians.get("sectorPe")),
        sector_pb=_fmt_metric(sector_medians.get("sectorPb")),
        sector_ev_ebitda=_fmt_metric(sector_medians.get("sectorEvEbitda")),
    )

    for attempt in range(retry_count + 1):
        try:
            response = model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.3,  # Low temp for analytical consistency
                    "max_output_tokens": 12288,
                    "response_mime_type": "application/json",  # Force clean JSON output
                },
            )

            text = response.text.strip()

            # Try to parse JSON from response
            report = _parse_json_response(text)

            if report and "executiveSummary" in report:
                print(f"    ✓ {ticker}: Report generated ({len(text)} chars)")
                return report
            else:
                # Log what we got for debugging
                err_msg = ""
                try:
                    json.loads(text)
                except json.JSONDecodeError as jde:
                    err_msg = str(jde)
                
                with open(f"failed_{ticker}.txt", "w", encoding="utf-8") as f:
                    f.write(text)
                print(f"    ⚠ {ticker}: Invalid report structure (attempt {attempt + 1}), error: {err_msg}")

        except Exception as e:
            err_str = str(e)[:150]
            print(f"    ✗ {ticker}: Error (attempt {attempt + 1}) - {err_str}")
            if attempt < retry_count:
                time.sleep(15)  # Back off before retry

    return None


def generate_all_reports(model, stocks_df, output_dir, delay=3.0):
    """
    Generate reports for all stocks in the DataFrame.

    Args:
        model: Gemini model instance
        stocks_df: DataFrame with scored stock data
        output_dir: Directory to save JSON reports
        delay: Seconds between API calls to stay within rate limits

    Returns:
        Number of successfully generated reports
    """
    os.makedirs(output_dir, exist_ok=True)
    success_count = 0

    for _, row in stocks_df.iterrows():
        ticker = row["ticker"]

        # Build sector medians dict
        sector_medians = {
            "sectorPe": row.get("sectorPe"),
            "sectorPb": row.get("sectorPb"),
            "sectorEvEbitda": row.get("sectorEvEbitda"),
        }

        stock_data = row.to_dict()
        report = generate_report(model, stock_data, sector_medians)

        if report:
            # Build full report JSON
            report_json = {
                "ticker": ticker,
                "name": row["name"],
                "price": round(float(row["price"]), 2),
                "sector": row["sector"],
                "marketCap": row.get("marketCapFormatted", format_market_cap(row.get("marketCap"))),
                "valuationScore": float(row["valuationScore"]),
                "generatedAt": _now_iso(),
                "report": report,
            }

            # Save to file
            filepath = os.path.join(output_dir, f"{ticker}.json")
            with open(filepath, "w") as f:
                json.dump(report_json, f, indent=2, ensure_ascii=False)

            success_count += 1
        else:
            print(f"    ✗ {ticker}: Skipped (no valid report generated)")

        # Rate limit
        time.sleep(delay)

    return success_count


def _parse_json_response(text):
    """
    Extract JSON from Gemini response. Handles cases where the model
    wraps the JSON in markdown code fences.
    """
    # Strip markdown code fences if present
    text = text.strip()
    if text.startswith("```"):
        # Remove opening fence (```json or ```)
        text = re.sub(r"^```(?:json)?\s*\n?", "", text)
        # Remove closing fence
        text = re.sub(r"\n?```\s*$", "", text)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON object in the text
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    return None


def _fmt_metric(val):
    """Format numeric metric."""
    if val is None or (isinstance(val, float) and val != val):
        return "N/A"
    return f"{val:.2f}"


def _fmt_pct(val):
    """Format percentage."""
    if val is None or (isinstance(val, float) and val != val):
        return "N/A"
    return f"{val:.1f}%"


def _fmt_currency(val):
    """Format large currency value."""
    if val is None or (isinstance(val, float) and val != val):
        return "N/A"
    if abs(val) >= 1e9:
        return f"A${val / 1e9:.2f}B"
    elif abs(val) >= 1e6:
        return f"A${val / 1e6:.0f}M"
    else:
        return f"A${val:,.0f}"


def _now_iso():
    """Current time in ISO format."""
    from datetime import datetime, timezone, timedelta
    aest = timezone(timedelta(hours=11))
    return datetime.now(aest).isoformat()
