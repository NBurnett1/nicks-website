import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import Disclaimer from '../components/Disclaimer'
import Footer from '../components/Footer'
import './StockDetail.css'

export default function StockDetail() {
  const { ticker } = useParams()
  const navigate = useNavigate()
  const [stock, setStock] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    window.scrollTo(0, 0)
    // Try to load from index data
    fetch('/data/asx_index.json')
      .then(res => res.ok ? res.json() : null)
      .then(data => {
        if (!data) { setLoading(false); return }
        const all = [...(data.undervalued || []), ...(data.overvalued || [])]
        const found = all.find(s => s.ticker === ticker)
        if (found) {
          setStock(found)
        }
        setLoading(false)
      })
      .catch(() => setLoading(false))
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

      <Disclaimer />
      <Footer />
    </div>
  )
}
