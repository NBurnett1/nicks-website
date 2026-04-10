import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import Disclaimer from '../components/Disclaimer'
import Footer from '../components/Footer'
import './StockDetail.css'

const GRADE_LABELS = {
  A: 'Strong Buy Signal',
  B: 'Buy Signal',
  C: 'Moderate Signal',
  D: 'Weak Signal',
  F: 'No Signal',
}

const TEST_ORDER = [
  'peDiscount',
  'pbBelowBook',
  'evEbitdaCheap',
  'fcfYieldStrong',
  'forwardPeRerate',
  'profitabilityCheck',
]

export default function StockDetail() {
  const { ticker } = useParams()
  const navigate = useNavigate()
  const [stock, setStock] = useState(null)
  const [detail, setDetail] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    window.scrollTo(0, 0)

    // Try to load from multiple exchange indexes
    const exchanges = ['asx', 'nyse', 'nasdaq']
    let found = false

    Promise.all(
      exchanges.map(ex =>
        fetch(`/data/${ex}_index.json`)
          .then(res => res.ok ? res.json() : null)
          .then(data => {
            if (!data || found) return
            const all = [...(data.undervalued || []), ...(data.overvalued || [])]
            const match = all.find(s => s.ticker === ticker)
            if (match) {
              found = true
              setStock(match)

              // Load detail file
              fetch(`/data/${ex}/details/${ticker}.json`)
                .then(res => res.ok ? res.json() : null)
                .then(d => setDetail(d))
                .catch(() => {})
            }
          })
          .catch(() => {})
      )
    ).finally(() => setLoading(false))
  }, [ticker])

  if (loading) {
    return (
      <div className="detail-loading">
        <div className="detail-loading__spinner" />
        <p className="detail-loading__text">Loading {ticker}…</p>
      </div>
    )
  }

  if (!stock) {
    return (
      <div className="detail-error">
        <div className="detail-error__content">
          <span className="detail-error__icon">📊</span>
          <h2 className="detail-error__title">Stock Not Found</h2>
          <p className="detail-error__text">
            <strong>{ticker}</strong> isn't currently tracked.
          </p>
          <button className="detail-error__back" onClick={() => navigate('/')}>
            ← Back to Dashboard
          </button>
        </div>
      </div>
    )
  }

  const isUndervalued = stock.valuationScore < 0
  const tests = detail?.valuationTests || {}
  const grade = detail?.grade || stock.grade || null
  const testsPassed = detail?.testsPassed ?? stock.testsPassed ?? null

  return (
    <div className="stock-detail" id="stock-detail-page">
      <div className="container">
        <button className="stock-detail__back" onClick={() => navigate('/')}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="m15 18-6-6 6-6"/>
          </svg>
          Back to Dashboard
        </button>
      </div>

      <header className={`stock-detail__header stock-detail__header--${isUndervalued ? 'undervalued' : 'overvalued'}`}>
        <div className="container">
          <div className="stock-detail__header-content">
            <div className="stock-detail__header-left">
              <div className="stock-detail__ticker-row">
                <h1 className="stock-detail__ticker">{stock.ticker}</h1>
                <span className={`badge badge--${isUndervalued ? 'green' : 'red'}`}>
                  {isUndervalued ? '▼ Undervalued' : '▲ Overvalued'}
                </span>
                {grade && (
                  <span className={`stock-detail__grade-badge stock-detail__grade-badge--${grade}`}>
                    Grade {grade}
                  </span>
                )}
              </div>
              <p className="stock-detail__name">{stock.name}</p>
              <div className="stock-detail__meta-tags">
                <span className="badge badge--blue">{stock.sector}</span>
                <span className="stock-detail__mcap">Market Cap: {stock.marketCap}</span>
              </div>
            </div>

            <div className="stock-detail__header-right">
              <div className="stock-detail__price-block">
                <span className="stock-detail__current-label">Current Price</span>
                <span className="stock-detail__current-price">A${stock.price.toFixed(2)}</span>
              </div>
              <div className="stock-detail__price-block">
                <span className="stock-detail__current-label">Valuation Score</span>
                <span className={`stock-detail__mispricing stock-detail__mispricing--${isUndervalued ? 'undervalued' : 'overvalued'}`}>
                  {stock.valuationScore > 0 ? '+' : ''}{stock.valuationScore.toFixed(1)}
                </span>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Valuation Tests Breakdown */}
      {Object.keys(tests).length > 0 && (
        <section className="stock-detail__tests-section">
          <div className="container">
            <div className="stock-detail__tests-card">
              <div className="stock-detail__tests-header">
                <div className="stock-detail__tests-title-group">
                  <span className="stock-detail__tests-icon">🔬</span>
                  <div>
                    <h2 className="stock-detail__tests-title">Valuation Test Results</h2>
                    <p className="stock-detail__tests-subtitle">
                      {testsPassed !== null ? `${testsPassed}/6 tests passed` : '6 tests run'} · {grade ? GRADE_LABELS[grade] : 'Grading...'}
                    </p>
                  </div>
                </div>
                {grade && (
                  <div className={`stock-detail__tests-grade stock-detail__tests-grade--${grade}`}>
                    {grade}
                  </div>
                )}
              </div>

              <div className="stock-detail__tests-grid">
                {TEST_ORDER.map(key => {
                  const test = tests[key]
                  if (!test) return null

                  const passed = test.passed
                  const statusClass = passed === true
                    ? 'stock-detail__test--pass'
                    : passed === false
                      ? 'stock-detail__test--fail'
                      : 'stock-detail__test--na'

                  return (
                    <div key={key} className={`stock-detail__test ${statusClass}`}>
                      <div className="stock-detail__test-status">
                        {passed === true ? '✓' : passed === false ? '✗' : '—'}
                      </div>
                      <div className="stock-detail__test-info">
                        <div className="stock-detail__test-name">{test.name}</div>
                        <div className="stock-detail__test-detail">{test.label}</div>
                      </div>
                      <div className="stock-detail__test-result">
                        {passed === true ? 'PASS' : passed === false ? 'FAIL' : 'N/A'}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>
        </section>
      )}

      <Disclaimer />
      <Footer />
    </div>
  )
}

