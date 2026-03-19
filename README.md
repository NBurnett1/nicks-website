# ASX Valuations — AI-Powered Stock Analysis

A web app that surfaces the **10 most overvalued and 10 most undervalued ASX stocks** with AI-generated institutional-grade equity research reports.

## 🚀 Stack

| Layer | Tool |
|---|---|
| Frontend | Vite + React + Vanilla CSS |
| Data | yfinance (Python) |
| AI | Google Gemini 2.5 Flash |
| Hosting | Vercel |
| CI/CD | GitHub Actions (weekly refresh) |

## 🏃 Quick Start

```bash
# Install frontend dependencies
npm install

# Run dev server
npm run dev
```

## 📊 Data Pipeline

```bash
# Install Python dependencies
pip install -r scripts/requirements.txt

# Run full pipeline (requires GEMINI_API_KEY)
GEMINI_API_KEY=your_key python scripts/run_pipeline.py

# Run data-only (no AI reports)
python scripts/run_pipeline.py --skip-reports

# Test with specific tickers
python scripts/run_pipeline.py --tickers BHP CBA CSL
```

## ⚠️ Disclaimer

This is **not financial advice**. All analysis is AI-generated for educational purposes only. Always do your own research.
