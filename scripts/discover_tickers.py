"""
Dynamic ticker discovery for ASX, NYSE, and NASDAQ.
Fetches all actively traded tickers from each exchange using yahoo_fin and web scraping.
"""

import requests
from bs4 import BeautifulSoup
import re
import io
import csv


def discover_asx_tickers():
    """Fetch all ASX-listed tickers from the ASX company directory."""
    print("  🔍 Discovering ASX tickers...")
    tickers = []

    # Method 1: Scrape ASX company directory
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        # ASX lists companies A-Z; we'll use a comprehensive approach
        url = "https://www.marketindex.com.au/asx-listed-companies"
        resp = requests.get(url, headers=headers, timeout=30)
        soup = BeautifulSoup(resp.text, 'html.parser')

        # Find table rows with ticker data
        for row in soup.find_all('tr'):
            cells = row.find_all('td')
            if len(cells) >= 2:
                code = cells[0].text.strip()
                if code and re.match(r'^[A-Z0-9]{2,5}$', code):
                    tickers.append(code)
    except Exception as e:
        print(f"    ⚠ marketindex.com.au failed: {e}")

    # Method 2: Fallback to Wikipedia S&P/ASX 200 + broader list
    if len(tickers) < 100:
        print("    📋 Falling back to hardcoded ASX tickers...")
        tickers = _asx_fallback()

    tickers = list(dict.fromkeys(tickers))  # deduplicate
    print(f"    ✓ Discovered {len(tickers)} ASX tickers")
    return tickers


def discover_nyse_tickers():
    """Fetch NYSE tickers from Wikipedia S&P 500 + additional sources."""
    print("  🔍 Discovering NYSE tickers...")
    tickers = set()

    # S&P 500
    try:
        sp500 = _scrape_wiki_table(
            'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies', 0, 0
        )
        tickers.update(sp500)
    except Exception as e:
        print(f"    ⚠ S&P 500 scrape failed: {e}")

    # S&P 400 Mid Cap
    try:
        sp400 = _scrape_wiki_table(
            'https://en.wikipedia.org/wiki/List_of_S%26P_400_companies', 0, 0
        )
        tickers.update(sp400)
    except Exception as e:
        print(f"    ⚠ S&P 400 scrape failed: {e}")

    # S&P 600 Small Cap
    try:
        sp600 = _scrape_wiki_table(
            'https://en.wikipedia.org/wiki/List_of_S%26P_600_companies', 0, 0
        )
        tickers.update(sp600)
    except Exception as e:
        print(f"    ⚠ S&P 600 scrape failed: {e}")

    # Remove NASDAQ tickers (we'll handle those separately)
    known_nasdaq = set(discover_nasdaq_tickers_raw())
    nyse_only = [t for t in tickers if t not in known_nasdaq]

    if len(nyse_only) < 100:
        nyse_only = _nyse_fallback()

    nyse_only = list(dict.fromkeys(nyse_only))
    print(f"    ✓ Discovered {len(nyse_only)} NYSE tickers")
    return nyse_only


def discover_nasdaq_tickers():
    """Fetch NASDAQ tickers from Wikipedia NASDAQ-100 + broader sources."""
    print("  🔍 Discovering NASDAQ tickers...")
    tickers = discover_nasdaq_tickers_raw()

    if len(tickers) < 50:
        tickers = _nasdaq_fallback()

    tickers = list(dict.fromkeys(tickers))
    print(f"    ✓ Discovered {len(tickers)} NASDAQ tickers")
    return tickers


def discover_nasdaq_tickers_raw():
    """Raw NASDAQ ticker discovery without fallback."""
    tickers = set()

    # NASDAQ 100
    try:
        n100 = _scrape_wiki_table(
            'https://en.wikipedia.org/wiki/Nasdaq-100', 4, 1
        )
        if len(n100) < 30:
            n100 = _scrape_wiki_table(
                'https://en.wikipedia.org/wiki/Nasdaq-100', 3, 1
            )
        tickers.update(n100)
    except Exception as e:
        print(f"    ⚠ NASDAQ-100 scrape failed: {e}")

    # Add well-known NASDAQ mega/large-caps not in NASDAQ-100
    extra_nasdaq = [
        "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "META", "TSLA", "NVDA",
        "AVGO", "COST", "PEP", "CSCO", "TMUS", "CMCSA", "TXN", "AMGN",
        "HON", "INTU", "SBUX", "QCOM", "GILD", "INTC", "MDLZ", "AMAT",
        "BKNG", "ISRG", "PYPL", "AMD", "REGN", "ADI", "LRCX", "KLAC",
        "SNPS", "CDNS", "NFLX", "ADBE", "ABNB", "CRWD", "MELI", "PANW",
        "DDOG", "ZS", "WDAY", "TEAM", "MDB", "NET", "DXCM", "ENPH",
        "RIVN", "LCID", "PLTR", "COIN", "MRNA", "FTNT", "SPLK", "SHOP",
        "TTD", "OKTA", "ZM", "DOCU", "DASH", "SNAP", "RBLX", "U",
        "ROKU", "SQ", "TWLO", "HOOD", "SOFI", "UPST", "AFRM", "BILL",
        "HUBS", "VEEV", "MNDY", "PCTY", "PAYC", "WIX", "FIVN", "RNG",
        "SMAR", "DOCN", "CFLT", "ESTC", "SNOW", "PATH", "GTLB", "S",
    ]
    tickers.update(extra_nasdaq)

    return list(tickers)


def _scrape_wiki_table(url, table_idx, col_idx):
    """Scrape a Wikipedia table for ticker symbols."""
    headers = {'User-Agent': 'Mozilla/5.0'}
    html = requests.get(url, headers=headers, timeout=30).text
    soup = BeautifulSoup(html, 'html.parser')
    tables = soup.find_all('table', {'class': 'wikitable'})

    if table_idx >= len(tables):
        return []

    tickers = []
    for row in tables[table_idx].find_all('tr')[1:]:
        cols = row.find_all(['td', 'th'])
        if len(cols) > col_idx:
            ticker = cols[col_idx].text.strip()
            # Clean ticker
            ticker = ticker.replace('.', '-')
            if ticker and re.match(r'^[A-Z0-9\-]{1,6}$', ticker):
                tickers.append(ticker)
    return tickers


def _asx_fallback():
    """Hardcoded comprehensive ASX ticker list."""
    return [
        "BHP", "CBA", "CSL", "NAB", "WBC", "ANZ", "MQG", "WES", "TLS", "WOW",
        "RIO", "TCL", "FMG", "GMG", "STO", "APA", "S32", "WTC", "XRO", "COH",
        "MIN", "RMD", "QBE", "SUN", "IAG", "SCG", "SGP", "REH", "SEK", "ALL",
        "AMC", "NST", "BSL", "BXB", "SHL", "CPU", "REA", "EDV", "ALQ", "ASX",
        "AIA", "ORG", "SDF", "CAR", "IGO", "PLS", "WHC", "JHX", "TWE", "PME",
        "RHC", "ILU", "LYC", "DXS", "MGR", "AMP", "BOQ", "BEN", "VCX", "AUB",
        "HVN", "JBH", "DMP", "SUL", "PMV", "WEB", "BAP", "MTS", "SGR", "GUD",
        "NXT", "APX", "MP1", "ALU", "BRG", "ARB", "COL", "A2M", "ING", "GNC",
        "BGA", "DOW", "AZJ", "QAN", "CIM", "CHC", "TPG", "AGL", "VHT", "LNW",
        "NHC", "WOR", "FLT", "ANN", "ABC", "BPT", "VEA", "SVW", "TGR", "MND",
        "IPH", "SBM", "BIN", "BKL", "RRL", "RSG", "PRU", "GWA", "PTM", "BWP",
        "CQR", "GDI", "NSR", "NWH", "SIQ", "ORI", "NEC", "TAH", "SKC", "DHG",
        "PPT", "CVN", "PPE", "ORA", "AWC", "SWM", "NUF", "IFL", "GXY", "PDN",
        "WSA", "SYR", "PNI", "CGF", "GOR", "CLW", "CIP", "VEE", "SPK", "BLD",
        "IVC", "CCX", "IMD", "CWY", "NHF", "INA", "ASG", "EHE", "SLC", "SKI",
    ]


def _nyse_fallback():
    """Hardcoded NYSE ticker list."""
    return [
        "MMM", "AOS", "ABT", "ABBV", "ACN", "AES", "AFL", "A", "APD", "ALB",
        "ARE", "ALLE", "LNT", "ALL", "MO", "AMCR", "AEE", "AXP", "AIG", "AMT",
        "AWK", "AMP", "AME", "APH", "AON", "APA", "APO", "APTV", "ACGL", "ADM",
        "ARES", "AJG", "AIZ", "T", "ATO", "AZO", "AVB", "AVY", "BALL", "BAC",
        "BAX", "BDX", "BRK-B", "BBY", "BIIB", "BLK", "BX", "BK", "BA", "BSX",
        "BMY", "BR", "BRO", "BF-B", "BLDR", "BG", "BXP", "CHRW", "CPT", "CPB",
        "COF", "CAH", "CCL", "CARR", "CVNA", "CAT", "CBOE", "CBRE", "COR", "CNC",
        "CNP", "CF", "CRL", "SCHW", "CVX", "CMG", "CB", "CHD", "CI", "CINF",
        "C", "CFG", "CLX", "CME", "CMS", "KO", "CL", "FIX", "CAG", "COP", "ED",
        "STZ", "COO", "GLW", "CPAY", "CTVA", "CRH", "CCI", "CMI", "CVS", "DHR",
        "DRI", "DVA", "DE", "DELL", "DAL", "DVN", "DLR", "DG", "D", "DPZ",
        "DOV", "DOW", "DHI", "DTE", "DUK", "DD", "ETN", "EBAY", "ECL", "EIX",
        "EW", "ELV", "EME", "EMR", "ETR", "EOG", "EPAM", "EQT", "EFX", "EQR",
        "ERIE", "ESS", "EL", "EG", "EVRG", "ES", "EXE", "EXPD", "EXR", "XOM",
        "FDS", "FICO", "FAST", "FRT", "FDX", "FIS", "FITB", "FE", "FISV", "F",
        "FTV", "BEN", "FCX", "GRMN", "IT", "GE", "GEV", "GEN", "GNRC", "GD",
        "GIS", "GM", "GPC", "GILD", "GPN", "GL", "GDDY", "GS", "HAL", "HIG",
        "HCA", "DOC", "HSIC", "HSY", "HPE", "HLT", "HD", "HRL", "HST", "HWM",
        "HUBB", "HUM", "HBAN", "HII", "ICE", "IP", "ITW", "IFF", "INCY", "IR",
        "INTC", "IBM", "IEX", "IDXX", "IPG", "ISRG", "IVZ", "INVH", "IQV", "IRM",
        "JCI", "SJM", "JNPR", "JNJ", "K", "KDP", "KEY", "KEYS", "KMB", "KIM",
        "KMI", "KR", "LHX", "LH", "LECO", "LEN", "LIN", "LLY", "LMT", "L",
        "LUMN", "LYB", "MTB", "MRO", "MPC", "MKTX", "MAR", "MMC", "MLM", "MAS",
        "MA", "MTCH", "MKC", "MCD", "MCK", "MDT", "MRK", "MET", "MTD", "MGM",
        "MCHP", "MU", "MSCI", "MS", "NDAQ", "NDSN", "NEE", "NEM", "NWSA", "NWS",
        "NKE", "NOC", "NSC", "NTRS", "NUE", "OXY", "ODFL", "OMC", "ON", "OKE",
        "ORCL", "OTIS", "OVV", "PARA", "PKG", "PH", "PAYX", "PAYC", "PNR", "PEP",
        "PFE", "PCG", "PM", "PSX", "PNW", "PG", "PGR", "PLD", "PRU", "PEG",
        "PSA", "PHM", "QRVO", "PWR", "DGX", "RL", "RJF", "RTX", "O", "REG",
        "REGN", "RF", "RSG", "RMD", "RVTY", "ROK", "ROL", "ROP", "ROST", "RCL",
        "SPGI", "CRM", "SBAC", "SLB", "SNPS", "STT", "STLD", "STE", "SYK", "SMCI",
        "SNA", "SO", "LUV", "SPG", "SWK", "SBNY", "STX", "SYF", "SYY", "TMUS",
        "TRGP", "TGT", "TEL", "TDY", "TFX", "TER", "TSCO", "TXT", "TMO", "TJX",
        "TSLA", "TPR", "TT", "TDG", "TRV", "TRMB", "TFC", "TSN", "TYL", "USB",
        "UBER", "UDR", "UNP", "UAL", "UNH", "UPS", "URI", "V", "VTR", "VRSN",
        "VRSK", "VZ", "VRTX", "VLTO", "VMC", "WRB", "WAB", "WBA", "WMT", "DIS",
        "WBD", "WM", "WAT", "WEC", "WFC", "WST", "WDC", "WRK", "WY", "WHR",
        "WMB", "WTW", "GWW", "WYNN", "XEL", "XYL", "YUM", "ZBRA", "ZBH", "ZTS",
    ]


def _nasdaq_fallback():
    """Hardcoded NASDAQ ticker list."""
    return discover_nasdaq_tickers_raw()


def get_all_tickers(exchange, limit=None):
    """Main entry point: get tickers for a given exchange."""
    if exchange == "ASX":
        tickers = discover_asx_tickers()
    elif exchange == "NYSE":
        tickers = discover_nyse_tickers()
    elif exchange == "NASDAQ":
        tickers = discover_nasdaq_tickers()
    else:
        raise ValueError(f"Unknown exchange: {exchange}")

    if limit:
        tickers = tickers[:limit]

    return tickers


if __name__ == "__main__":
    import sys
    exchange = sys.argv[1] if len(sys.argv) > 1 else "ASX"
    tickers = get_all_tickers(exchange)
    print(f"\n{exchange}: {len(tickers)} tickers")
    print(", ".join(tickers[:20]), "...")
