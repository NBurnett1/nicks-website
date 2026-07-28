import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import StockLogo from './StockLogo'
import './WeeklyPicks.css'

const GRADE_COLORS = {
  A: 'var(--green-400)',
  B: '#5eead4',
  C: 'var(--amber-400)',
  D: 'var(--red-400)',
  F: 'var(--text-muted)',
}

export default function WeeklyPicks({ exchange = 'ASX' }) {
  const [picksData, setPicksData] = useState(null)
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    fetch('/data/picks.json')
      .then(res => res.ok ? res.json() : null)
      .then(data => {
        if (data?.picks?.length) setPicksData(data)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [])

  const handleClick = (ticker) => {
    navigate(`/stock/${ticker}`)
  }

  if (loading) {
    return (
      <div className="weekly-picks">
        <div className="weekly-picks__loading">
          <div className="weekly-picks__loading-spinner" />
          Loading picks…
        </div>
      </div>
    )
  }

  // ── No Picks State ──
  if (!picksData || !picksData.picks?.length) {
    return (
      <div className="weekly-picks" id="weekly-picks">
        <div className="weekly-picks__awaiting">
          <div className="weekly-picks__awaiting-glow" />
          <div className="weekly-picks__awaiting-icon">📊</div>
          <h2 className="weekly-picks__awaiting-title">Picks Refreshing</h2>
          <p className="weekly-picks__awaiting-subtitle">
            Our AI-powered selection engine is analyzing the ASX, sourcing analyst recommendations,
            and running adversarial screening. Fresh picks are generated daily.
          </p>
          <div className="weekly-picks__awaiting-features">
            <div className="weekly-picks__awaiting-feature">
              <span className="weekly-picks__awaiting-feature-icon">🏦</span>
              <span>Analyst consensus signals</span>
            </div>
            <div className="weekly-picks__awaiting-feature">
              <span className="weekly-picks__awaiting-feature-icon">📰</span>
              <span>Advisory firm recommendations</span>
            </div>
            <div className="weekly-picks__awaiting-feature">
              <span className="weekly-picks__awaiting-feature-icon">🧠</span>
              <span>AI conviction screening</span>
            </div>
          </div>
        </div>
      </div>
    )
  }

  const picks = picksData.picks
  const heroPick = picks[0]
  const remainingPicks = picks.slice(1)

  return (
    <div className="weekly-picks" id="weekly-picks">
      {/* Section Header */}
      <div className="weekly-picks__header">
        <div className="weekly-picks__title-group">
          <div className="weekly-picks__week-badge">
            <span className="weekly-picks__week-num">Today's Picks</span>
            <span className="weekly-picks__status weekly-picks__status--active">
              ● Live
            </span>
          </div>
          <div>
            <h2 className="weekly-picks__title">Daily Conviction Picks</h2>
            <p className="weekly-picks__subtitle">
              {picksData.date} · {picks.length} stocks · Refreshed daily
            </p>
          </div>
        </div>
      </div>

      {/* Macro Context Banner */}
      {picksData.macro && picksData.macro.headline && (
        <div className="weekly-picks__macro">
          <div className="weekly-picks__macro-icon">🌍</div>
          <div className="weekly-picks__macro-content">
            <div className="weekly-picks__macro-headline">{picksData.macro.headline}</div>
            {picksData.macro.themes && picksData.macro.themes.length > 0 && (
              <div className="weekly-picks__macro-themes">
                {picksData.macro.themes.map((theme, i) => (
                  <span key={i} className="weekly-picks__macro-theme">• {theme}</span>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Hero Pick — #1 */}
      {heroPick && (
        <div
          className="weekly-picks__hero"
          onClick={() => handleClick(heroPick.ticker)}
        >
          <div className="weekly-picks__hero-rank">
            <span className="weekly-picks__hero-rank-num">#1</span>
            <span className="weekly-picks__hero-rank-label">Top Pick</span>
          </div>
          <div className="weekly-picks__hero-content">
            <div className="weekly-picks__hero-left">
              <StockLogo ticker={heroPick.ticker} name={heroPick.name} className="weekly-picks__hero-logo" />
              <div className="weekly-picks__hero-info">
                <div className="weekly-picks__hero-ticker">{heroPick.ticker}</div>
                <div className="weekly-picks__hero-name">{heroPick.name}</div>
                <div className="weekly-picks__hero-sector">
                  {heroPick.sector}
                  {heroPick.macroLabel && (
                    <span className={`weekly-picks__macro-pill weekly-picks__macro-pill--${heroPick.macroBias >= 0.3 ? 'tailwind' : heroPick.macroBias <= -0.3 ? 'headwind' : 'neutral'}`}>
                      {heroPick.macroBias >= 0.3 ? '↑' : heroPick.macroBias <= -0.3 ? '↓' : '→'} {heroPick.macroLabel}
                    </span>
                  )}
                </div>
              </div>
            </div>
            <div className="weekly-picks__hero-right">
              <div className={`weekly-picks__grade weekly-picks__grade--${heroPick.grade}`}>{heroPick.grade}</div>
              <div className="weekly-picks__hero-tests">{heroPick.testsPassed}/8 tests</div>
            </div>
          </div>
          <div className="weekly-picks__hero-thesis">{heroPick.thesis}</div>
          <div className="weekly-picks__hero-footer">
            <div className="weekly-picks__hero-price">
              <span className="weekly-picks__label">Price</span>
              <span className="weekly-picks__value">A${heroPick.price?.toFixed(2)}</span>
            </div>
            <div className="weekly-picks__hero-mcap">
              <span className="weekly-picks__label">Market Cap</span>
              <span className="weekly-picks__value">{heroPick.marketCap}</span>
            </div>
            {heroPick.qualScore && (
              <div className="weekly-picks__hero-price">
                <span className="weekly-picks__label">AI Score</span>
                <span className="weekly-picks__value">{heroPick.qualScore}/10</span>
              </div>
            )}
            {heroPick.advisorySource && (
              <div className="weekly-picks__hero-price">
                <span className="weekly-picks__label">📰 Signal</span>
                <span className="weekly-picks__value" style={{fontSize: '0.7rem'}}>{heroPick.advisorySource}</span>
              </div>
            )}
            {heroPick.analystConsensus && (
              <div className="weekly-picks__hero-price">
                <span className="weekly-picks__label">🏦 Analyst</span>
                <span className="weekly-picks__value" style={{fontSize: '0.7rem'}}>{heroPick.analystConsensus}</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Remaining Picks Grid */}
      <div className="weekly-picks__grid">
        {remainingPicks.map((pick, i) => (
          <div
            key={pick.ticker}
            className="weekly-picks__card"
            onClick={() => handleClick(pick.ticker)}
            style={{ animationDelay: `${(i + 1) * 0.1}s` }}
          >
            <div className="weekly-picks__card-header">
              <div className="weekly-picks__card-rank">#{pick.rank}</div>
              <div className={`weekly-picks__grade weekly-picks__grade--${pick.grade}`}>{pick.grade}</div>
            </div>
            <div className="weekly-picks__card-body">
              <StockLogo ticker={pick.ticker} name={pick.name} className="weekly-picks__card-logo" />
              <div className="weekly-picks__card-info">
                <div className="weekly-picks__card-ticker">{pick.ticker}</div>
                <div className="weekly-picks__card-name">{pick.name}</div>
                <div className="weekly-picks__card-sector">
                  {pick.sector}
                  {pick.macroLabel && (
                    <span className={`weekly-picks__macro-pill weekly-picks__macro-pill--${pick.macroBias >= 0.3 ? 'tailwind' : pick.macroBias <= -0.3 ? 'headwind' : 'neutral'}`}>
                      {pick.macroBias >= 0.3 ? '↑' : pick.macroBias <= -0.3 ? '↓' : '→'} {pick.macroLabel}
                    </span>
                  )}
                </div>
              </div>
            </div>
            <div className="weekly-picks__card-thesis">{pick.thesis}</div>
            <div className="weekly-picks__card-footer">
              <span className="weekly-picks__card-price">A${pick.price?.toFixed(2)}</span>
              {pick.qualScore && (
                <span className="weekly-picks__card-pnl weekly-picks__card-pnl--positive">
                  AI: {pick.qualScore}/10
                </span>
              )}
              {pick.advisorySource && (
                <span className="weekly-picks__card-advisory" title={pick.advisoryHeadline}>
                  📰 {pick.advisorySource}
                </span>
              )}
              {pick.analystConsensus && (
                <span className="weekly-picks__card-analyst">
                  🏦 {pick.analystConsensus}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
