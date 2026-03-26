import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import AlertsFeed from './AlertsFeed'
import './MarketSelector.css'

export default function MarketSelector({ onSelect }) {
  const [exitingMarket, setExitingMarket] = useState(null)
  const [topPicks, setTopPicks] = useState({})
  const navigate = useNavigate()

  // Load top picks for each market on mount
  useEffect(() => {
    const exchanges = ['asx', 'nyse', 'nasdaq']
    exchanges.forEach(async (ex) => {
      try {
        const res = await fetch(`/data/${ex}_index.json`)
        if (!res.ok) return
        const data = await res.json()
        let candidates = (data.undervalued || [])
          .filter(s => {
            const mc = s.marketCap || '0'
            let val = 0
            if (mc.endsWith('B')) val = parseFloat(mc) * 1e9
            else if (mc.endsWith('M')) val = parseFloat(mc) * 1e6
            else if (mc.endsWith('T')) val = parseFloat(mc) * 1e12
            return val >= 500_000_000
          })
          .sort((a, b) => a.valuationScore - b.valuationScore)
          .slice(0, 30) // take top 30 candidates to find best mispricing

        // Fetch report for each candidate to get mispricing %
        const withMispricing = await Promise.all(
          candidates.map(async (s) => {
            try {
              const rRes = await fetch(`/data/reports/${s.ticker}.json`)
              if (!rRes.ok) return { ...s, mispricing: null }
              const report = await rRes.json()
              const mispricing = report?.report?.verdict?.mispricing ?? null
              const fairValue = report?.report?.verdict?.fairValue ?? null
              return { ...s, mispricing, fairValue }
            } catch {
              return { ...s, mispricing: null }
            }
          })
        )

        // Filter to those that are actually undervalued (mispricing < 0) and sort by most undervalued
        const ranked = withMispricing
          .filter(s => s.mispricing !== null && s.mispricing < 0)
          .sort((a, b) => a.mispricing - b.mispricing) // most negative first

        setTopPicks(prev => ({ ...prev, [ex.toUpperCase()]: ranked.slice(0, 5) }))
      } catch {
        // silently fail
      }
    })
  }, [])

  const handleSelect = (market) => {
    setExitingMarket(market)
    setTimeout(() => {
      onSelect(market)
    }, 600)
  }

  const handleStockClick = (e, ticker, stock) => {
    e.stopPropagation()
    navigate(`/stock/${ticker}`, { state: { chartData: stock.chartData } })
  }

  const handleMouseMove = (e) => {
    const card = e.currentTarget
    const rect = card.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top
    
    card.style.setProperty('--mouse-x', `${x}px`)
    card.style.setProperty('--mouse-y', `${y}px`)
    
    const centerX = rect.width / 2
    const centerY = rect.height / 2
    const rotateX = ((y - centerY) / centerY) * -5  
    const rotateY = ((x - centerX) / centerX) * 5
    
    card.style.setProperty('--rotateX', `${rotateX}deg`)
    card.style.setProperty('--rotateY', `${rotateY}deg`)
  }

  const handleMouseLeave = (e) => {
    const card = e.currentTarget
    card.style.setProperty('--rotateX', '0deg')
    card.style.setProperty('--rotateY', '0deg')
  }

  const markets = [
    { id: 'ASX', name: 'ASX', desc: 'Australian Securities Exchange', flag: '🇦🇺', status: 'LIVE', accent: 'green' },
    { id: 'NYSE', name: 'NYSE', desc: 'New York Stock Exchange', flag: '🇺🇸', status: 'LIVE', accent: 'blue' },
    { id: 'NASDAQ', name: 'NASDAQ', desc: 'NASDAQ Stock Market', flag: '🇺🇸', status: 'LIVE', accent: 'purple' }
  ]

  return (
    <div className={`market-selector-gate ${exitingMarket ? 'market-selector-gate--exiting' : ''}`}>
      <div className="market-selector__bg-orb market-selector__bg-orb--1" />
      <div className="market-selector__bg-orb market-selector__bg-orb--2" />
      <div className="market-selector__bg-orb market-selector__bg-orb--3" />
      
      <div className="container market-selector__content">
        <h1 className="market-selector__title animate-fade-in-up">
          Select <span className="text-gradient">Market</span>
        </h1>
        <p className="market-selector__subtitle animate-fade-in-up stagger-1">
          AI-powered valuations and equity research across global exchanges. 
          <span className="market-selector__subtitle-highlight"> Top picks updated daily.</span>
        </p>

        <div className="market-selector__grid animate-fade-in-up stagger-2">
          {markets.map((market) => {
            const picks = topPicks[market.id] || []
            return (
              <button 
                key={market.id}
                className={`market-card market-card--active market-card--${market.accent} ${exitingMarket && exitingMarket !== market.id ? 'market-card--fading' : ''} ${exitingMarket === market.id ? 'market-card--selected' : ''}`}
                onClick={() => handleSelect(market.id)}
                onMouseMove={handleMouseMove}
                onMouseLeave={handleMouseLeave}
              >
                <div className="market-card__header">
                  <div className="market-card__icon-wrapper">{market.flag}</div>
                  <div className="market-card__header-text">
                    <h3 className="market-card__title">{market.name}</h3>
                    <p className="market-card__desc">{market.desc}</p>
                  </div>
                </div>

                <div className="market-card__status-row">
                  <div className={`market-card__status market-card__status--${market.accent}`}>LIVE</div>
                  {picks.length > 0 && (
                    <span className="market-card__picks-count">{picks.length} top picks</span>
                  )}
                </div>

                {/* Top Picks Section */}
                {picks.length > 0 && (
                  <div className="market-card__picks">
                    <div className="market-card__picks-header">
                      <span className="market-card__picks-label">🔥 Top Undervalued</span>
                    </div>
                    <div className="market-card__picks-list">
                      {picks.map((stock, i) => (
                        <div 
                          key={stock.ticker}
                          className={`pick-chip pick-chip--${market.accent}`}
                          onClick={(e) => handleStockClick(e, stock.ticker, stock)}
                          title={`${stock.name} — ${stock.sector || 'Equity'}`}
                        >
                          <span className="pick-chip__rank">{i + 1}</span>
                          <span className="pick-chip__ticker">{stock.ticker}</span>
                          <span className="pick-chip__price">
                            {market.id === 'ASX' ? 'A$' : '$'}{stock.price.toFixed(2)}
                          </span>
                          <span className="pick-chip__mispricing">
                            {stock.mispricing != null ? `${stock.mispricing.toFixed(0)}%` : '—'}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div className="market-card__cta">
                  View all stocks →
                </div>
              </button>
            )
          })}
        </div>

        <p className="market-selector__footnote animate-fade-in-up stagger-3">
          Lower valuation scores indicate stronger undervaluation signals. Click any stock to view its full analysis report.
        </p>

        <AlertsFeed />
      </div>
    </div>
  )
}
