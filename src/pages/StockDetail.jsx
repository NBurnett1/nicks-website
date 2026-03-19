import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import ReportView from '../components/ReportView'
import Disclaimer from '../components/Disclaimer'
import Footer from '../components/Footer'
import './StockDetail.css'

export default function StockDetail() {
  const { ticker } = useParams()
  const navigate = useNavigate()
  const [reportData, setReportData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    window.scrollTo(0, 0)
    fetch(`/data/reports/${ticker}.json`)
      .then(res => {
        if (!res.ok) throw new Error('Not found')
        return res.json()
      })
      .then(d => {
        setReportData(d)
        setLoading(false)
      })
      .catch(() => {
        setError(true)
        setLoading(false)
      })
  }, [ticker])

  if (loading) {
    return (
      <div className="detail-loading">
        <div className="detail-loading__spinner" />
        <p className="detail-loading__text">Loading analysis for {ticker}...</p>
      </div>
    )
  }

  if (error || !reportData) {
    return (
      <div className="detail-error">
        <div className="detail-error__content">
          <span className="detail-error__icon">📊</span>
          <h2 className="detail-error__title">Analysis Not Available</h2>
          <p className="detail-error__text">
            The detailed AI analysis for <strong>{ticker}</strong> hasn't been generated yet. 
            Check back after the next weekly refresh.
          </p>
          <button className="detail-error__back" onClick={() => navigate('/')}>
            ← Back to Overview
          </button>
        </div>
      </div>
    )
  }

  const { report, verdict } = reportData
  const isOvervalued = reportData.valuationScore > 0
  const signalType = isOvervalued ? 'overvalued' : 'undervalued'

  return (
    <div className="stock-detail" id="stock-detail-page">
      {/* Navigation */}
      <div className="container">
        <button className="stock-detail__back" onClick={() => navigate('/')}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="m15 18-6-6 6-6"/>
          </svg>
          Back to Overview
        </button>
      </div>

      {/* Header */}
      <header className={`stock-detail__header stock-detail__header--${signalType}`}>
        <div className="container">
          <div className="stock-detail__header-content">
            <div className="stock-detail__header-left">
              <div className="stock-detail__ticker-row">
                <h1 className="stock-detail__ticker">{reportData.ticker}</h1>
                <span className={`badge badge--${isOvervalued ? 'red' : 'green'}`}>
                  {isOvervalued ? '▲ Overvalued' : '▼ Undervalued'}
                </span>
              </div>
              <p className="stock-detail__name">{reportData.name}</p>
              <div className="stock-detail__meta-tags">
                <span className="badge badge--blue">{reportData.sector}</span>
                <span className="stock-detail__mcap">Market Cap: {reportData.marketCap}</span>
              </div>
            </div>

            <div className="stock-detail__header-right">
              <div className="stock-detail__price-block">
                <span className="stock-detail__current-label">Current Price</span>
                <span className="stock-detail__current-price">${reportData.price.toFixed(2)}</span>
              </div>
              {report?.verdict && (
                <>
                  <div className="stock-detail__price-block">
                    <span className="stock-detail__current-label">Fair Value</span>
                    <span className={`stock-detail__fair-value stock-detail__fair-value--${signalType}`}>
                      ${report.verdict.fairValue.toFixed(2)}
                    </span>
                  </div>
                  <div className="stock-detail__price-block">
                    <span className="stock-detail__current-label">Mispricing</span>
                    <span className={`stock-detail__mispricing stock-detail__mispricing--${signalType}`}>
                      {report.verdict.mispricing > 0 ? '+' : ''}{report.verdict.mispricing.toFixed(1)}%
                    </span>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Report */}
      <main className="stock-detail__body">
        <div className="container">
          <ReportView report={report} />
        </div>
      </main>

      <Disclaimer />
      <Footer />
    </div>
  )
}
