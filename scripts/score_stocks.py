"""
Valuation scoring engine — ranks ASX stocks by composite valuation score.
Positive score = overvalued, negative = undervalued.
"""

import pandas as pd
import numpy as np
from config import SCORING_WEIGHTS


def score_stocks(df):
    """
    Calculate composite valuation score for each stock.

    Uses z-scores relative to sector medians for:
    - P/E ratio
    - P/B ratio
    - EV/EBITDA
    - FCF yield (inverted — higher yield = cheaper = more undervalued)

    Args:
        df: DataFrame from fetch_data with columns: ticker, sector, pe, pb, evEbitda, fcfYield

    Returns:
        DataFrame with added 'valuationScore' column, sorted by score descending.
    """
    df = df.copy()

    # Clean extreme and string values from yfinance
    for col in ["pe", "pb", "evEbitda", "fcfYield"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            df[col] = df[col].replace([np.inf, -np.inf], np.nan)

    # Calculate global medians (fallback for small sectors)
    global_medians = {
        "sectorPe": df["pe"].median(),
        "sectorPb": df["pb"].median(),
        "sectorEvEbitda": df["evEbitda"].median(),
        "sectorFcfYield": df["fcfYield"].median(),
    }

    # Calculate sector medians
    sector_counts = df.groupby("sector").size()
    sector_medians = df.groupby("sector").agg(
        sectorPe=("pe", "median"),
        sectorPb=("pb", "median"),
        sectorEvEbitda=("evEbitda", "median"),
        sectorFcfYield=("fcfYield", "median"),
    ).reset_index()

    # For sectors with < 3 stocks, use global medians instead
    for col in ["sectorPe", "sectorPb", "sectorEvEbitda", "sectorFcfYield"]:
        small_sectors = sector_counts[sector_counts < 3].index
        sector_medians.loc[sector_medians["sector"].isin(small_sectors), col] = global_medians[col]

    df = df.merge(sector_medians, on="sector", how="left")

    # Calculate z-scores relative to sector medians
    # Positive z-score = above sector median = more expensive
    df["pe_zscore"] = _safe_zscore(df["pe"], df["sectorPe"])
    df["pb_zscore"] = _safe_zscore(df["pb"], df["sectorPb"])
    df["ev_ebitda_zscore"] = _safe_zscore(df["evEbitda"], df["sectorEvEbitda"])

    # FCF yield: INVERT — higher yield = cheaper = negative score (undervalued)
    df["fcf_yield_inv"] = _safe_zscore(df["fcfYield"], df["sectorFcfYield"]) * -1

    # Composite weighted score
    weights = SCORING_WEIGHTS
    df["valuationScore"] = 0.0

    for metric, weight in weights.items():
        col = df[metric].fillna(0)
        df["valuationScore"] += col * weight

    # Scale to a more intuitive range (roughly -50 to +50)
    df["valuationScore"] = (df["valuationScore"] * 15).round(1)

    # Clamp to reasonable range
    df["valuationScore"] = df["valuationScore"].clip(-60, 60)

    # Sort by score descending (most overvalued first)
    df = df.sort_values("valuationScore", ascending=False).reset_index(drop=True)

    print(f"\n  Scoring complete. Range: {df['valuationScore'].min():.1f} to {df['valuationScore'].max():.1f}")
    return df


def run_valuation_tests(row):
    """
    Run 7 independent valuation tests on a single stock row.
    Returns a dict of test results, each with:
      { passed: bool|None, value: float|None, threshold: float|None, label: str }
    None for passed means data was insufficient (N/A).
    """
    tests = {}

    pe = row.get("pe")
    sector_pe = row.get("sectorPe")
    pb = row.get("pb")
    ps = row.get("ps")
    ev_ebitda = row.get("evEbitda")
    fcf_yield = row.get("fcfYield")
    forward_pe = row.get("forwardPe")
    profit_margin = row.get("profitMargin")
    roe = row.get("roe")
    revenue_growth = row.get("revenueGrowth")

    # Clean values
    def _clean(val):
        if val is None:
            return None
        try:
            f = float(val)
            if f != f or abs(f) == float('inf'):
                return None
            return f
        except (ValueError, TypeError):
            return None

    pe = _clean(pe)
    sector_pe = _clean(sector_pe)
    pb = _clean(pb)
    ps = _clean(ps)
    ev_ebitda = _clean(ev_ebitda)
    fcf_yield = _clean(fcf_yield)
    forward_pe = _clean(forward_pe)
    profit_margin = _clean(profit_margin)
    roe = _clean(roe)
    revenue_growth = _clean(revenue_growth)

    # Test 1: P/E Discount — P/E must be 15%+ below sector median
    if pe is not None and sector_pe is not None and pe > 0 and sector_pe > 0:
        threshold = round(sector_pe * 0.85, 2)
        tests["peDiscount"] = {
            "name": "P/E Discount",
            "passed": pe < threshold,
            "value": round(pe, 2),
            "threshold": threshold,
            "label": f"{pe:.1f}x vs {threshold:.1f}x sector"
        }
    else:
        tests["peDiscount"] = {
            "name": "P/E Discount",
            "passed": None,
            "value": round(pe, 2) if pe else None,
            "threshold": None,
            "label": "Insufficient data"
        }

    # Test 2: P/B Below Book — P/B < 1.5
    if pb is not None:
        threshold = 1.5
        tests["pbBelowBook"] = {
            "name": "P/B Below Book",
            "passed": pb < threshold,
            "value": round(pb, 2),
            "threshold": threshold,
            "label": f"{pb:.2f}x vs {threshold}x"
        }
    else:
        tests["pbBelowBook"] = {
            "name": "P/B Below Book",
            "passed": None,
            "value": None,
            "threshold": 1.5,
            "label": "No P/B data"
        }

    # Test 3: EV/EBITDA Cheap — EV/EBITDA < 10
    if ev_ebitda is not None and ev_ebitda > 0:
        threshold = 10.0
        tests["evEbitdaCheap"] = {
            "name": "EV/EBITDA Cheap",
            "passed": ev_ebitda < threshold,
            "value": round(ev_ebitda, 2),
            "threshold": threshold,
            "label": f"{ev_ebitda:.1f}x vs {threshold:.0f}x"
        }
    else:
        tests["evEbitdaCheap"] = {
            "name": "EV/EBITDA Cheap",
            "passed": None,
            "value": None,
            "threshold": 10.0,
            "label": "No EV/EBITDA data"
        }

    # Test 4: FCF Yield Strong — FCF Yield > 5%
    if fcf_yield is not None:
        threshold = 5.0
        tests["fcfYieldStrong"] = {
            "name": "FCF Yield Strong",
            "passed": fcf_yield > threshold,
            "value": round(fcf_yield, 2),
            "threshold": threshold,
            "label": f"{fcf_yield:.1f}% vs {threshold:.0f}%"
        }
    else:
        tests["fcfYieldStrong"] = {
            "name": "FCF Yield Strong",
            "passed": None,
            "value": None,
            "threshold": 5.0,
            "label": "No FCF data"
        }

    # Test 5: Forward P/E Re-rating — Forward PE < Trailing PE (earnings growth)
    if forward_pe is not None and pe is not None and forward_pe > 0 and pe > 0:
        tests["forwardPeRerate"] = {
            "name": "Forward P/E Re-rating",
            "passed": forward_pe < pe,
            "value": round(forward_pe, 2),
            "threshold": round(pe, 2),
            "label": f"Fwd {forward_pe:.1f}x vs Trail {pe:.1f}x"
        }
    else:
        tests["forwardPeRerate"] = {
            "name": "Forward P/E Re-rating",
            "passed": None,
            "value": round(forward_pe, 2) if forward_pe else None,
            "threshold": round(pe, 2) if pe else None,
            "label": "Insufficient data"
        }

    # Test 6: Profitability Check — Profit margin > 5% AND ROE > 8%
    if profit_margin is not None and roe is not None:
        margin_ok = profit_margin > 5.0
        roe_ok = roe > 8.0
        tests["profitabilityCheck"] = {
            "name": "Profitability Check",
            "passed": margin_ok and roe_ok,
            "value": round(profit_margin, 2),
            "threshold": 5.0,
            "label": f"Margin {profit_margin:.1f}% / ROE {roe:.1f}%"
        }
    else:
        tests["profitabilityCheck"] = {
            "name": "Profitability Check",
            "passed": None,
            "value": round(profit_margin, 2) if profit_margin else None,
            "threshold": 5.0,
            "label": "Insufficient data"
        }

    # Test 7: Value/Growth Score — P/S ÷ revenue growth % (lower = more growth per dollar)
    # Inspired by revenue PEG: a stock with P/S of 2x and 20% growth scores 0.10 (excellent)
    # A stock with P/S of 5x and 5% growth scores 1.0 (poor value for growth)
    if ps is not None and revenue_growth is not None and ps > 0 and revenue_growth > 0:
        vg_score = round(ps / revenue_growth, 2)
        threshold = 0.5  # Below 0.5 = you're getting significant growth per valuation dollar
        tests["valueGrowthScore"] = {
            "name": "Value/Growth Score",
            "passed": vg_score < threshold,
            "value": vg_score,
            "threshold": threshold,
            "label": f"P/S {ps:.1f}x ÷ Growth {revenue_growth:.1f}% = {vg_score:.2f}"
        }
    else:
        tests["valueGrowthScore"] = {
            "name": "Value/Growth Score",
            "passed": None,
            "value": None,
            "threshold": 0.5,
            "label": "No P/S or growth data"
        }

    return tests


def conviction_grade(tests_passed):
    """Map number of tests passed (0-7) to a letter grade."""
    if tests_passed >= 6:
        return "A"
    elif tests_passed >= 4:
        return "B"
    elif tests_passed == 3:
        return "C"
    elif tests_passed >= 1:
        return "D"
    else:
        return "F"


def get_top_stocks(df, top_n=100):
    """
    Get top N overvalued and top N undervalued stocks.
    """
    valid = df[df["valuationScore"].notna()].copy()

    # Split into definitive categories — no overlap possible
    overvalued = valid[valid["valuationScore"] >= 0.0].sort_values("valuationScore", ascending=False).head(top_n)
    undervalued = valid[valid["valuationScore"] < 0.0].sort_values("valuationScore", ascending=True).head(top_n)

    print(f"\n  Top {len(overvalued)} Overvalued:")
    for _, row in overvalued.iterrows():
        print(f"    {row['ticker']:>5}  {row['valuationScore']:>+6.1f}  (P/E: {_f(row['pe'])}, EV/EBITDA: {_f(row['evEbitda'])})")

    print(f"\n  Top {len(undervalued)} Undervalued:")
    for _, row in undervalued.iterrows():
        print(f"    {row['ticker']:>5}  {row['valuationScore']:>+6.1f}  (P/E: {_f(row['pe'])}, EV/EBITDA: {_f(row['evEbitda'])})")

    if len(overvalued) < top_n:
        print(f"\n  ⚠ Only {len(overvalued)} stocks scored as overvalued")
    if len(undervalued) < top_n:
        print(f"\n  ⚠ Only {len(undervalued)} stocks scored as undervalued")

    return overvalued, undervalued


def _safe_zscore(values, medians):
    """Calculate z-score: (value - median) / median. Handles zeros/NaN."""
    result = pd.Series(np.nan, index=values.index)
    mask = medians.notna() & values.notna() & (medians != 0)
    result[mask] = (values[mask] - medians[mask]) / medians[mask].abs()
    return result


def _f(val):
    """Format number or return '—'."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "—"
    return f"{val:.1f}"


def stock_to_summary_dict(row):
    """Convert a DataFrame row to the summary JSON format."""
    return {
        "ticker": row["ticker"],
        "name": row["name"],
        "price": round(float(row["price"]), 2),
        "sector": row["sector"],
        "domain": row.get("domain", ""),
        "chartData": row.get("chartData", []),
        "marketCap": row.get("marketCapFormatted", "—"),
        "valuationScore": float(row["valuationScore"]),
        "metrics": {
            "pe": _safe_float(row.get("pe")),
            "sectorPe": _safe_float(row.get("sectorPe")),
            "pb": _safe_float(row.get("pb")),
            "evEbitda": _safe_float(row.get("evEbitda")),
            "fcfYield": _safe_float(row.get("fcfYield")),
            "revenueGrowth": _safe_float(row.get("revenueGrowth")),
        },
    }


def _safe_float(val):
    """Convert to float or None."""
    if val is None:
        return None
    try:
        f = float(val)
        if np.isnan(f):
            return None
        return round(f, 2)
    except (ValueError, TypeError):
        return None
