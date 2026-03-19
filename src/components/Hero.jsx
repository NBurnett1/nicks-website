import { useState, useEffect } from 'react'
import './Hero.css'

export default function Hero() {
  const [meta, setMeta] = useState(null)

  useEffect(() => {
    fetch('/data/meta.json')
      .then(res => res.json())
      .then(setMeta)
      .catch(() => {})
  }, [])

  const formatDate = (dateStr) => {
    const d = new Date(dateStr)
    return d.toLocaleDateString('en-AU', {
      weekday: 'long',
      day: 'numeric',
      month: 'long',
      year: 'numeric'
    })
  }

  return (
    <section className="hero" id="hero">
      <div className="hero__bg-orb hero__bg-orb--1" />
      <div className="hero__bg-orb hero__bg-orb--2" />
      <div className="hero__bg-orb hero__bg-orb--3" />

      <div className="container hero__content">
        <div className="hero__badge animate-fade-in">
          <span className="hero__badge-dot" />
          ASX Market Analysis
        </div>

        <h1 className="hero__title animate-fade-in-up">
          Find{' '}
          <span className="hero__title--green">Undervalued</span>
          {' '}&{' '}
          <span className="hero__title--red">Overvalued</span>
          <br />
          ASX Stocks
        </h1>

        <p className="hero__subtitle animate-fade-in-up" style={{ animationDelay: '0.15s' }}>
          AI-powered institutional-grade equity research. We analyse the top 100 ASX stocks
          weekly and surface the 10 most undervalued and overvalued — so you can make
          educated investment decisions.
        </p>

        <div className="hero__meta animate-fade-in-up" style={{ animationDelay: '0.3s' }}>
          {meta && (
            <>
              <div className="hero__meta-item">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="10"/>
                  <polyline points="12 6 12 12 16 14"/>
                </svg>
                Updated {formatDate(meta.lastUpdated)}
              </div>
              <div className="hero__meta-item">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 20V10"/>
                  <path d="M18 20V4"/>
                  <path d="M6 20v-4"/>
                </svg>
                {meta.stocksAnalyzed} stocks analysed
              </div>
              <div className="hero__meta-item">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 2a4 4 0 0 0-4 4c0 2 2 3 2 6H14c0-3 2-4 2-6a4 4 0 0 0-4-4z"/>
                  <line x1="10" y1="16" x2="14" y2="16"/>
                  <line x1="10" y1="19" x2="14" y2="19"/>
                  <line x1="11" y1="22" x2="13" y2="22"/>
                </svg>
                Powered by AI
              </div>
            </>
          )}
        </div>

        <a href="#market-overview" className="hero__cta animate-fade-in-up" style={{ animationDelay: '0.45s' }}>
          View Analysis
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 5v14"/>
            <path d="m19 12-7 7-7-7"/>
          </svg>
        </a>
      </div>
    </section>
  )
}
