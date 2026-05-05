"""
Nick Knows Best — Macro / Geopolitical Scanner

Uses the Gemini API to analyze current news and geopolitical events,
producing sector-level biases that overlay the valuation-based stock picks.

The scanner:
  1. Gathers current macro context (configurable or auto-detected)
  2. Asks Gemini to assess sector-by-sector impact for ASX stocks
  3. Returns sector_biases dict: sector → weight modifier (-1.0 to +1.0)
     Positive = tailwind (boost this sector), Negative = headwind (penalize)

Usage:
    from macro_scanner import get_macro_biases
    biases = get_macro_biases()  # Returns {"Energy": 0.8, "Consumer Discretionary": -0.6, ...}
"""

import json
import os
import sys
from datetime import datetime, timezone, timedelta

AEST = timezone(timedelta(hours=10))

# ── Sector categories for ASX stocks ──
ASX_SECTORS = [
    "Energy", "Materials", "Basic Materials", "Gold", "Silver",
    "Industrials", "Consumer Discretionary", "Consumer Cyclical",
    "Consumer Staples", "Consumer Defensive",
    "Healthcare", "Financials", "Financial Services",
    "Technology", "Communication Services",
    "Utilities", "Real Estate",
]

# ── Fallback biases when Gemini is unavailable ──
# These are manually set based on the current macro environment.
# Updated: 19 April 2026 — US-Iran ceasefire expiring 22 April
FALLBACK_BIASES = {
    "Energy": 0.8,
    "Materials": 0.4,
    "Basic Materials": 0.5,
    "Gold": 0.9,
    "Silver": 0.7,
    "Industrials": -0.1,
    "Consumer Discretionary": -0.7,
    "Consumer Cyclical": -0.6,
    "Consumer Staples": 0.3,
    "Consumer Defensive": 0.4,
    "Healthcare": 0.2,
    "Financials": 0.1,
    "Financial Services": 0.2,
    "Technology": -0.2,
    "Communication Services": -0.1,
    "Utilities": 0.1,
    "Real Estate": -0.3,
}

FALLBACK_CONTEXT = {
    "headline": "US-Iran ceasefire expiring 22 April — escalation risk high",
    "themes": [
        "Energy prices elevated — Strait of Hormuz disruption risk",
        "Gold as safe haven — central bank buying + geopolitical fear",
        "Consumer confidence weak — inflationary pressures from energy",
        "Insurance premiums rising — geopolitical uncertainty",
        "Defense spending structural tailwind globally",
    ],
    "generated": datetime.now(AEST).isoformat(),
    "source": "fallback",
}


def get_macro_biases(gemini_key=None):
    """
    Get macro/geopolitical sector biases.
    Tries Gemini first, falls back to manual biases.
    Returns: (biases_dict, context_dict)
    """
    key = gemini_key or os.environ.get("GEMINI_API_KEY")
    if key:
        try:
            biases, context = _gemini_macro_scan(key)
            if biases:
                return biases, context
        except Exception as e:
            print(f"  ⚠ Gemini macro scan failed: {e}")
            print(f"  → Falling back to manual biases")

    return FALLBACK_BIASES.copy(), FALLBACK_CONTEXT.copy()


def _gemini_macro_scan(api_key):
    """Use Gemini to analyze current macro environment and produce sector biases."""
    try:
        from google import genai
    except ImportError:
        print("  ⚠ google-genai not installed. Install with: pip install google-genai")
        return None, None

    client = genai.Client(api_key=api_key)

    prompt = f"""You are an ASX (Australian Stock Exchange) equity strategist.
Today is {datetime.now(AEST).strftime('%A %d %B %Y')} (AEST).

Analyze the CURRENT global macro and geopolitical environment and its impact on
ASX-listed stocks for the coming trading week. Focus on:
1. Geopolitical conflicts (especially US-Iran, any active wars/tensions)
2. Commodity prices (oil, gold, iron ore, LNG)
3. Interest rate outlook (RBA, Fed)
4. Consumer confidence and inflation
5. Any major upcoming events (earnings, central bank meetings, political events)

Return your analysis as a JSON object with this exact structure:
{{
  "headline": "One-line summary of the key macro theme this week",
  "themes": ["Theme 1 with brief explanation", "Theme 2...", ...],
  "sector_biases": {{
    "Energy": <float -1.0 to 1.0>,
    "Materials": <float>,
    "Basic Materials": <float>,
    "Industrials": <float>,
    "Consumer Discretionary": <float>,
    "Consumer Cyclical": <float>,
    "Consumer Staples": <float>,
    "Consumer Defensive": <float>,
    "Healthcare": <float>,
    "Financials": <float>,
    "Financial Services": <float>,
    "Technology": <float>,
    "Communication Services": <float>,
    "Utilities": <float>,
    "Real Estate": <float>
  }},
  "avoid_sectors": ["sectors to strongly avoid this week"],
  "favor_sectors": ["sectors with strong tailwinds this week"]
}}

Bias values:
  +1.0 = extremely strong tailwind (e.g. energy during oil crisis)
  +0.5 = moderate tailwind
   0.0 = neutral
  -0.5 = moderate headwind
  -1.0 = extremely strong headwind (e.g. airlines during oil crisis)

IMPORTANT: Return ONLY the JSON, no markdown, no explanation."""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        text = response.text.strip()

        # Clean markdown fences if present
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
        text = text.strip()

        data = json.loads(text)
        biases = data.get("sector_biases", {})
        context = {
            "headline": data.get("headline", ""),
            "themes": data.get("themes", []),
            "avoid_sectors": data.get("avoid_sectors", []),
            "favor_sectors": data.get("favor_sectors", []),
            "generated": datetime.now(AEST).isoformat(),
            "source": "gemini",
        }
        return biases, context

    except Exception as e:
        print(f"  ⚠ Gemini parse error: {e}")
        return None, None


def apply_macro_bias(candidates, sector_biases):
    """
    Apply macro biases to candidate stocks.
    Returns candidates with a 'macroScore' field added.

    Scoring:
      macroScore = valuation_conviction + sector_bias_boost
      - Grade A/B + positive sector bias = strong buy
      - Grade A/B + negative sector bias = downgraded / skipped
      - Grade C/D + strong positive bias = potential speculative play
    """
    grade_base = {"A": 5, "B": 4, "C": 3, "D": 2, "F": 0}

    for c in candidates:
        sector = c.get("sector", "Unknown")
        grade = c.get("grade", "F")
        tests = c.get("testsPassed", 0)

        # Base conviction score from valuation
        base = grade_base.get(grade, 0) + (tests * 0.5)

        # Sector bias — check exact match first, then partial
        bias = _find_sector_bias(sector, sector_biases)

        # Macro-adjusted score
        # Bias is -1 to +1, scaled to have significant impact
        # A +0.8 bias on a Grade B (base 4+2=6) → 6 + 2.4 = 8.4
        # A -0.7 bias on a Grade A (base 5+2.5=7.5) → 7.5 - 2.1 = 5.4
        macro_boost = bias * 3.0  # Scale factor
        c["macroScore"] = round(base + macro_boost, 2)
        c["macroBias"] = round(bias, 2)
        c["macroLabel"] = _bias_label(bias)

    return candidates


def _find_sector_bias(sector, biases):
    """Find the best matching bias for a given sector string."""
    sector_lower = sector.lower()

    # Exact match
    for key, val in biases.items():
        if key.lower() == sector_lower:
            return val

    # Partial match
    for key, val in biases.items():
        if key.lower() in sector_lower or sector_lower in key.lower():
            return val

    return 0.0  # Neutral if no match


def _bias_label(bias):
    """Human-readable label for a bias value."""
    if bias >= 0.6:
        return "Strong Tailwind"
    elif bias >= 0.3:
        return "Tailwind"
    elif bias >= 0.1:
        return "Slight Tailwind"
    elif bias > -0.1:
        return "Neutral"
    elif bias > -0.3:
        return "Slight Headwind"
    elif bias > -0.6:
        return "Headwind"
    else:
        return "Strong Headwind"


def save_macro_context(cycles_dir, cycle_num, context, biases):
    """Save macro analysis alongside the cycle data for transparency."""
    macro_data = {
        "cycle": cycle_num,
        "macro": context,
        "sectorBiases": biases,
        "savedAt": datetime.now(AEST).isoformat(),
    }

    path = os.path.join(cycles_dir, f"cycle{cycle_num}_macro.json")
    with open(path, "w") as f:
        json.dump(macro_data, f, indent=2, ensure_ascii=False)
    return path

