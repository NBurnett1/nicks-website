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
  const [weekData, setWeekData] = useState(null)
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    // Load week index to find current/latest week
    fetch('/data/weeks/index.json')
      .then(res => res.ok ? res.json() : null)
      .then(index => {
        if (!index?.weeks?.length) { setLoading(false); return }
        // Find the active or latest week
        const active = index.weeks.find(w => w.status === 'active')
        const latest = index.weeks[index.weeks.length - 1]
        const target = active || latest
        return fetch(`/data/weeks/week${target.week}.json`)
      })
      .then(res => res?.ok ? res.json() : null)
      .then(data => {
        if (data) setWeekData(data)
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
          Loading this week's picks…
        </div>
      </div>
    )
  }

  if (!weekData) return null

  const corePicks = weekData.picks.filter(p => p.type === 'core')
  const specPick = weekData.picks.find(p => p.type === 'speculative')
  const heroPick = corePicks[0]
  const remainingCore = corePicks.slice(1)
  const isActive = weekData.status === 'active' || weekData.status === 'upcoming'

  return (
    <div className="weekly-picks" id="weekly-picks">
      {/* Section Header */}
      <div className="weekly-picks__header">
        <div className="weekly-picks__title-group">
          <div className="weekly-picks__week-badge">
            <span className="weekly-picks__week-num">Week {weekData.week}</span>
            <span className={`weekly-picks__status weekly-picks__status--${weekData.status}`}>
              {weekData.status === 'active' ? '● Live' : weekData.status === 'upcoming' ? '◉ Monday' : '✓ Complete'}
            </span>
          </div>
          <div>
            <h2 className="weekly-picks__title">This Week's Picks</h2>
            <p className="weekly-picks__subtitle">
              {weekData.dateRange} · {weekData.picks.length} stocks selected
            </p>
          </div>
        </div>
        {weekData.summary && (
          <div className="weekly-picks__summary-badge">
            <span className={`weekly-picks__summary-pnl ${weekData.summary.avgPnlPct >= 0 ? 'weekly-picks__summary-pnl--positive' : 'weekly-picks__summary-pnl--negative'}`}>
              {weekData.summary.avgPnlPct >= 0 ? '↑' : '↓'} {weekData.summary.avgPnlPct >= 0 ? '+' : ''}{weekData.summary.avgPnlPct.toFixed(1)}%
            </span>
            <span className="weekly-picks__summary-label">avg return</span>
          </div>
        )}
      </div>

      {/* Macro Context Banner */}
      {weekData.macro && weekData.macro.headline && (
        <div className="weekly-picks__macro">
          <div className="weekly-picks__macro-icon">🌍</div>
          <div className="weekly-picks__macro-content">
            <div className="weekly-picks__macro-headline">{weekData.macro.headline}</div>
            {weekData.macro.themes && weekData.macro.themes.length > 0 && (
              <div className="weekly-picks__macro-themes">
                {weekData.macro.themes.map((theme, i) => (
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
              <div className="weekly-picks__hero-tests">{heroPick.testsPassed}/6 tests</div>
            </div>
          </div>
          <div className="weekly-picks__hero-thesis">{heroPick.thesis}</div>
          <div className="weekly-picks__hero-footer">
            <div className="weekly-picks__hero-price">
              <span className="weekly-picks__label">Entry</span>
              <span className="weekly-picks__value">A${heroPick.entryPrice.toFixed(2)}</span>
            </div>
            <div className="weekly-picks__hero-price">
              <span className="weekly-picks__label">Current</span>
              <span className="weekly-picks__value">A${heroPick.currentPrice.toFixed(2)}</span>
            </div>
            <div className="weekly-picks__hero-price">
              <span className="weekly-picks__label">P&L</span>
              <span className={`weekly-picks__value ${heroPick.pnlPct > 0 ? 'weekly-picks__value--positive' : heroPick.pnlPct < 0 ? 'weekly-picks__value--negative' : ''}`}>
                {heroPick.pnlPct !== 0 ? `${heroPick.pnlPct > 0 ? '+' : ''}${heroPick.pnlPct.toFixed(1)}%` : '—'}
              </span>
            </div>
            <div className="weekly-picks__hero-mcap">
              <span className="weekly-picks__label">Market Cap</span>
              <span className="weekly-picks__value">{heroPick.marketCap}</span>
            </div>
          </div>
        </div>
      )}

      {/* Core Picks Grid — #2, #3, #4 */}
      <div className="weekly-picks__grid">
        {remainingCore.map((pick, i) => (
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
              <span className="weekly-picks__card-price">A${pick.entryPrice.toFixed(2)}</span>
              <span className={`weekly-picks__card-pnl ${pick.pnlPct > 0 ? 'weekly-picks__card-pnl--positive' : pick.pnlPct < 0 ? 'weekly-picks__card-pnl--negative' : ''}`}>
                {pick.pnlPct !== 0 ? `${pick.pnlPct > 0 ? '+' : ''}${pick.pnlPct.toFixed(1)}%` : '—'}
              </span>
            </div>
          </div>
        ))}

        {/* Speculative Pick — distinct styling */}
        {specPick && (
          <div
            className="weekly-picks__card weekly-picks__card--spec"
            onClick={() => handleClick(specPick.ticker)}
            style={{ animationDelay: `${(remainingCore.length + 1) * 0.1}s` }}
          >
            <div className="weekly-picks__card-header">
              <div className="weekly-picks__spec-badge">🔥 Speculative</div>
              <div className={`weekly-picks__grade weekly-picks__grade--${specPick.grade}`}>{specPick.grade}</div>
            </div>
            <div className="weekly-picks__card-body">
              <StockLogo ticker={specPick.ticker} name={specPick.name} className="weekly-picks__card-logo" />
              <div className="weekly-picks__card-info">
                <div className="weekly-picks__card-ticker">{specPick.ticker}</div>
                <div className="weekly-picks__card-name">{specPick.name}</div>
                <div className="weekly-picks__card-sector">{specPick.sector} · {specPick.marketCap}</div>
              </div>
            </div>
            <div className="weekly-picks__card-thesis">{specPick.thesis}</div>
            <div className="weekly-picks__card-footer">
              <span className="weekly-picks__card-price">A${specPick.entryPrice.toFixed(2)}</span>
              <span className={`weekly-picks__card-pnl ${specPick.pnlPct > 0 ? 'weekly-picks__card-pnl--positive' : specPick.pnlPct < 0 ? 'weekly-picks__card-pnl--negative' : ''}`}>
                {specPick.pnlPct !== 0 ? `${specPick.pnlPct > 0 ? '+' : ''}${specPick.pnlPct.toFixed(1)}%` : '—'}
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
