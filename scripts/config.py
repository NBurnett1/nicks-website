"""
Configuration for ASX Valuation Pipeline
"""

# ASX 100 large-cap tickers (without .AX suffix — added at fetch time)
ASX_TICKERS = [
    "BHP", "CBA", "CSL", "NAB", "WBC", "ANZ", "MQG", "WES", 
    "TLS", "WOW", "RIO", "TCL", "FMG", "GMG", "GLEN", "STO", 
    "APA", "S32", "WTC", "XRO", "COH", "MIN", "RMD", "QBE", 
    "SUN", "IAG", "NCM", "SCG", "SGP", "REH", "SEK", "ALL", 
    "AMC", "NST", "BSL", "BXB", "SHL", "CPU", "REA", "EDV", 
    "ALQ", "ASX", "AIA", "ORG", "SDF", "CAR", "IGO", "PLS", 
    "WHC", "JHX", "CWH", "TWE", "ALX", "PME", "RHC", "ILU", 
    "LYC", "DXS", "MGR", "CHR", "AMP", "BOQ", "BEN", "VCX", 
    "AUB", "HVN", "JBH", "DMP", "SUL", "PMV", "WEB", "BAP", 
    "MTS", "SGR", "SGF", "GUD", "NXT", "APX", "MP1", "ALU", 
    "BRG", "ARB", "COL", "A2M", "ING", "CGC", "GNC", "BGA", 
    "DOW", "SEV", "AZJ", "QAN", "SYD", "CIM", "CHC", "TPG",
    "AGL", "AST", "VUK", "VHT", "LNW", "NHC", "YAL", "WOR",
    "FLT", "ANN", "ABC", "BPT", "VEA", "KAR", "STW", "SVW",
    "TGR", "MND", "CEN", "GMA", "HGO", "IPH", "OORA", "SBM",
    "VRL", "BIN", "BKL", "BWX", "CDA", "GEM", "ISU", "PPC",
    "RRL", "RSG", "GDF", "GMD", "SMR", "EMR", "PRU", "BGL",
    "GWA", "PTM", "ASB", "ASL", "BWP", "CQR", "ECX", "GDI",
    "NSR", "VVR", "CXP", "KMD", "NWH", "SKE", "SIQ", "SSM"
]

NYSE_TICKERS = [
    "MMM",
    "AOS",
    "ABT",
    "ABBV",
    "ACN",
    "ADBE",
    "AES",
    "AFL",
    "A",
    "APD",
    "ALB",
    "ARE",
    "ALLE",
    "LNT",
    "ALL",
    "GOOGL",
    "MO",
    "AMZN",
    "AMCR",
    "AEE",
    "AXP",
    "AIG",
    "AMT",
    "AWK",
    "AMP",
    "AME",
    "AMGN",
    "APH",
    "AON",
    "APA",
    "APO",
    "AAPL",
    "AMAT",
    "APTV",
    "ACGL",
    "ADM",
    "ARES",
    "ANET",
    "AJG",
    "AIZ",
    "T",
    "ATO",
    "ADSK",
    "AZO",
    "AVB",
    "AVY",
    "BALL",
    "BAC",
    "BAX",
    "BDX",
    "BRK-B",
    "BBY",
    "TECH",
    "BIIB",
    "BLK",
    "BX",
    "XYZ",
    "BK",
    "BA",
    "BKNG",
    "BSX",
    "BMY",
    "BR",
    "BRO",
    "BF-B",
    "BLDR",
    "BG",
    "BXP",
    "CHRW",
    "CPT",
    "CPB",
    "COF",
    "CAH",
    "CCL",
    "CARR",
    "CVNA",
    "CAT",
    "CBOE",
    "CBRE",
    "COR",
    "CNC",
    "CNP",
    "CF",
    "CRL",
    "SCHW",
    "CVX",
    "CMG",
    "CB",
    "CHD",
    "CIEN",
    "CI",
    "CINF",
    "CSCO",
    "C",
    "CFG",
    "CLX",
    "CME",
    "CMS",
    "KO",
    "CTSH",
    "COIN",
    "CL",
    "CMCSA",
    "FIX",
    "CAG",
    "COP",
    "ED",
    "STZ",
    "COO",
    "GLW",
    "CPAY",
    "CTVA",
    "COST",
    "CTRA",
    "CRH",
    "CCI",
    "CMI",
    "CVS",
    "DHR",
    "DRI",
    "DVA",
    "DECK",
    "DE",
    "DELL",
    "DAL",
    "DVN",
    "DLR",
    "DG",
    "D",
    "DPZ",
    "DOV",
    "DOW",
    "DHI",
    "DTE",
    "DUK",
    "DD",
    "ETN",
    "EBAY",
    "ECL",
    "EIX",
    "EW",
    "ELV",
    "EME",
    "EMR",
    "ETR",
    "EOG",
    "EPAM",
    "EQT",
    "EFX",
    "EQR",
    "ERIE",
    "ESS",
    "EL",
    "EG",
    "EVRG",
    "ES",
    "EXE",
    "EXPD",
    "EXR",
    "XOM",
    "FDS",
    "FICO",
    "FAST",
    "FRT",
    "FDX",
    "FIS",
    "FITB",
    "FE",
    "FISV",
    "F",
    "FTV",
    "BEN",
    "FCX",
    "GRMN",
    "IT",
    "GE",
    "GEV",
    "GEN",
    "GNRC",
    "GD",
    "GIS",
    "GM",
    "GPC",
    "GILD",
    "GPN",
    "GL",
    "GDDY",
    "GS",
    "HAL",
    "HIG",
    "HCA",
    "DOC",
    "HSIC",
    "HSY",
    "HPE",
    "HLT",
    "HD",
    "HRL",
    "HST",
    "HWM"
]

NASDAQ_TICKERS = [
    "PEP",
    "MRVL",
    "NFLX",
    "LMCA",
    "BATRK",
    "XRAY",
    "CDW",
    "LCID",
    "ULTA",
    "ASML",
    "TXN",
    "LIFE",
    "INSM",
    "ADI",
    "WFMI",
    "ZS",
    "ANSS",
    "CSGP",
    "ROP",
    "SRCL",
    "PTON",
    "SWKS",
    "TTD",
    "KDP",
    "WYNN",
    "MSTR",
    "SNPS",
    "VOD",
    "SBAC",
    "MYL",
    "TRI",
    "ODFL",
    "WDAY",
    "LBTYA",
    "CEPH",
    "RYAAY",
    "SHOP",
    "PYPL",
    "BIDU",
    "ABNB",
    "DXCM",
    "CRWD",
    "KFT",
    "TTWO",
    "EA",
    "TRIP",
    "ALXN",
    "WLTW",
    "EQIX",
    "LILA",
    "KLAC",
    "ILMN",
    "UAUA",
    "INCY",
    "XEL",
    "PPDI",
    "FLIR",
    "APP",
    "BMC",
    "ARM",
    "RIVN",
    "PRGO",
    "MPWR",
    "VRSK",
    "STLD",
    "SGEN",
    "SOLS",
    "GEHC",
    "VRSN",
    "AZN",
    "CPRT",
    "CHTR",
    "LULU",
    "BMRN",
    "KHC",
    "NUAN",
    "AKAM",
    "MAT",
    "LIN",
    "DDOG",
    "NTES",
    "GFS",
    "AVGO",
    "SIRI",
    "WCRX",
    "URBN",
    "FMCN",
    "NTAP",
    "LRCX",
    "UAL",
    "CERN",
    "PDD",
    "DOCU",
    "TEAM",
    "FFIV",
    "HON",
    "FOX",
    "BATRA",
    "ZM",
    "MU",
    "ORLY",
    "ON",
    "NCLH",
    "GMCR",
    "SMCI",
    "JBHT",
    "MXIM",
    "CA",
    "TSCO",
    "VIP",
    "AEP",
    "DLTR",
    "EXC",
    "WBD",
    "AMD",
    "CSX",
    "LILAK",
    "CTRP",
    "AAL",
    "DTV",
    "REGN",
    "VIAB",
    "ENPH",
    "KRFT",
    "Security",
    "CMCSK",
    "WMT",
    "FOXA",
    "NXPI",
    "MELI",
    "SPLK",
    "HOLX",
    "DISCA",
    "MDB",
    "CDNS",
    "CEG",
    "FOSL",
    "WBA",
    "LEAP",
    "PCLN",
    "HANS",
    "JD",
    "CCEP",
    "STX",
    "PANW",
    "NWSA",
    "LOGI",
    "OKTA",
    "MAR",
    "EXPE",
    "TSLA",
    "AXON",
    "WDC",
    "FSLR",
    "DASH",
    "SHPG",
    "VSNT",
    "MTCH",
    "HAS",
    "FANG",
    "LBTYK",
    "ALNY",
    "ADP",
    "FWLT",
    "GOLD",
    "ALGN",
    "VMED",
    "FER",
    "MCHP",
    "BKR",
    "GOOG",
    "MRNA",
    "TMUS",
    "IDXX",
    "FB",
    "SNDK",
    "STRZA",
    "QGEN",
    "ENDP",
    "CTAS",
    "CTRX",
    "ROST",
    "PLTR",
    "FTNT",
    "DISH"
]

# Sector mapping for z-score calculations
SECTOR_MAP = {
    "CBA": "Financials", "NAB": "Financials", "WBC": "Financials", "ANZ": "Financials",
    "MQG": "Financials", "SUN": "Financials", "IAG": "Financials", "QBE": "Financials",
    "BEN": "Financials", "BOQ": "Financials", "GQG": "Financials", "HUB": "Financials",
    "NWL": "Financials", "MPL": "Financials", "AMP": "Financials",
    "BHP": "Materials", "RIO": "Materials", "FMG": "Materials", "MIN": "Materials",
    "S32": "Materials", "IGO": "Materials", "ILU": "Materials", "OZL": "Materials",
    "SFR": "Materials", "NST": "Materials", "NCM": "Materials", "EVN": "Materials",
    "NHC": "Materials", "WHC": "Materials", "AMC": "Materials",
    "WDS": "Energy", "STO": "Energy", "ORG": "Energy", "WPL": "Energy",
    "KAR": "Energy", "BPT": "Energy", "VEA": "Energy",
    "CSL": "Healthcare", "COH": "Healthcare", "RMD": "Healthcare", "PME": "Healthcare",
    "SHL": "Healthcare", "RHC": "Healthcare", "FPH": "Healthcare", "NAN": "Healthcare",
    "EBR": "Healthcare",
    "XRO": "Technology", "WTC": "Technology", "TNE": "Technology", "REA": "Technology",
    "CAR": "Technology", "SEK": "Technology", "APX": "Technology", "MP1": "Technology",
    "ALU": "Technology", "NXT": "Technology",
    "ALL": "Consumer Discretionary", "WES": "Consumer Discretionary",
    "HVN": "Consumer Discretionary", "JBH": "Consumer Discretionary",
    "SUL": "Consumer Discretionary", "LOV": "Consumer Discretionary",
    "PMV": "Consumer Discretionary", "IEL": "Consumer Discretionary",
    "BRG": "Consumer Discretionary", "ARB": "Consumer Discretionary",
    "WOW": "Consumer Staples", "COL": "Consumer Staples", "TWE": "Consumer Staples",
    "A2M": "Consumer Staples", "ING": "Consumer Staples", "CGC": "Consumer Staples",
    "GNC": "Consumer Staples", "BGA": "Consumer Staples",
    "TCL": "Industrials", "BXB": "Industrials", "DOW": "Industrials",
    "SEV": "Industrials", "AZJ": "Industrials", "QAN": "Industrials",
    "SYD": "Industrials", "AIA": "Industrials", "CIM": "Industrials",
    "GMG": "Real Estate", "SGP": "Real Estate", "DXS": "Real Estate",
    "GPT": "Real Estate", "MGR": "Real Estate", "VCX": "Real Estate",
    "SCG": "Real Estate", "CHC": "Real Estate",
    "TLS": "Telecom", "TPG": "Telecom", "AGL": "Utilities",
    "APA": "Utilities", "AST": "Utilities",
}

# Valuation scoring weights
SCORING_WEIGHTS = {
    "pe_zscore": 0.30,       # P/E vs sector median
    "pb_zscore": 0.20,       # P/B vs sector median
    "ev_ebitda_zscore": 0.30, # EV/EBITDA vs sector median
    "fcf_yield_inv": 0.20,   # FCF yield (inverted — lower yield = more overvalued)
}

# Format market cap for display
def format_market_cap(value):
    """Format market cap in human-readable form (e.g., '216B', '8.2B')"""
    if value is None or value != value:  # NaN check
        return "—"
    if value >= 1e12:
        return f"{value / 1e12:.1f}T"
    elif value >= 1e9:
        return f"{value / 1e9:.1f}B"
    elif value >= 1e6:
        return f"{value / 1e6:.0f}M"
    else:
        return f"{value:,.0f}"


# Gemini AI prompt template
ANALYST_PROMPT = """You are an elite, highly analytical, and inquisitive investment analyst working at a top-tier global investment bank (e.g., Goldman Sachs). Your task is to conduct institutional-grade equity research and valuation on companies.

Your mindset:
* Be skeptical, detail-oriented, and intellectually rigorous
* Think like a buy-side and sell-side analyst simultaneously
* Always question assumptions and validate inputs
* Prioritize accuracy, logic, and defensibility over speed
* Clearly explain reasoning while maintaining professional tone

---

### OBJECTIVE

Given the company data below, determine:
1. Intrinsic value (fair value per share in AUD)
2. Whether the company is overvalued or undervalued
3. By approximately what percentage
4. Key drivers behind the valuation

---

### COMPANY DATA

Ticker: {ticker}
Company: {name}
Sector: {sector}
Current Price: A${price:.2f}
Market Cap: {market_cap}

Financial Metrics:
- P/E Ratio: {pe}
- Forward P/E: {forward_pe}
- P/B Ratio: {pb}
- EV/EBITDA: {ev_ebitda}
- Dividend Yield: {dividend_yield}
- Revenue Growth (YoY): {revenue_growth}
- Profit Margin: {profit_margin}
- Operating Margin: {operating_margin}
- ROE: {roe}
- Debt/Equity: {debt_equity}
- Free Cash Flow: {fcf}
- Free Cash Flow Yield: {fcf_yield}

Sector Median P/E: {sector_pe}
Sector Median P/B: {sector_pb}
Sector Median EV/EBITDA: {sector_ev_ebitda}

---

### REQUIRED ANALYSIS FRAMEWORK

#### 1. BUSINESS UNDERSTANDING
* Explain the company's business model
* Revenue streams and cost structure
* Industry positioning and competitive advantages (moat)
* Key risks (macro, industry, company-specific)

#### 2. FINANCIAL ANALYSIS
* Analyze the provided financial metrics
* Assess profitability and efficiency
* Evaluate capital structure and debt levels
* Identify trends and anomalies

#### 3. FORECASTING
* Build forward projections (5-10 years where appropriate)
* Clearly state all assumptions with justification

#### 4. VALUATION METHODS (USE MULTIPLE)

**A. Discounted Cash Flow (DCF)**
* Project free cash flows, determine WACC, estimate terminal value
* Show step-by-step calculation logic

**B. Comparable Company Analysis (Trading Multiples)**
* Use relevant ASX and global peers
* Apply P/E, EV/EBITDA, EV/Revenue multiples

**C. Additional Methods (if applicable)**
* Dividend Discount Model (for dividend-paying firms)
* Sum-of-the-Parts (for conglomerates)

#### 5. TRIANGULATION
* Compare outputs from all valuation methods
* Weight methods appropriately based on company type
* Arrive at a final fair value range and point estimate

#### 6. CONCLUSION
* Fair value per share (in AUD)
* Current market price
* % overvalued or undervalued
* View: Potentially Undervalued / Fairly Valued / Potentially Overvalued

#### 7. SENSITIVITY & RISKS
* Show how valuation changes under different assumptions
* Identify the 3-5 most critical variables impacting valuation
* Provide Bear/Base/Bull case scenarios with price targets

---

### OUTPUT FORMAT

You must respond with a JSON object using EXACTLY this structure (no markdown, no code fences):

{{
  "executiveSummary": "...",
  "businessOverview": "...",
  "financialAnalysis": "...",
  "assumptions": "...",
  "valuationDCF": "...",
  "valuationComps": "...",
  "valuationSummary": "| Method | Fair Value (A$/share) | Weight |\\n|--------|----------------------|--------|\\n...",
  "verdict": {{
    "fairValue": <number>,
    "currentPrice": {price},
    "mispricing": <number (negative=undervalued, positive=overvalued)>,
    "signal": "<undervalued|overvalued|fairlyvalued>",
    "recommendation": "<Potentially Undervalued|Fairly Valued|Potentially Overvalued>"
  }},
  "risksAndSensitivity": "..."
}}

IMPORTANT: **KEEP ALL SECTIONS EXTREMELY CONCISE.** Maximum 2-3 sentences per section. Do not write long paragraphs. This is critical.
IMPORTANT: Use markdown formatting within string values (bold with **, tables with |, bullet points with -).
IMPORTANT: The JSON must be valid — escape quotes and newlines properly.
IMPORTANT: Do NOT wrap the response in markdown code fences. Output raw JSON only.
"""
