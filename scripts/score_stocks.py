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
