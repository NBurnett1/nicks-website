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
  const [nextCycleDate, setNextCycleDate] = useState(null)
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    // Load cycle index to find current/latest cycle
    fetch('/data/cycles/index.json')
      .then(res => res.ok ? res.json() : null)
      .then(index => {
        if (!index?.cycles?.length) {
          // No cycles — show awaiting state
          setNextCycleDate(index?.nextCycleDate || '2026-06-01')
          setLoading(false)
          return
        }
        // Find the active or latest cycle
        const active = index.cycles.find(c => c.status === 'active')
        const latest = index.cycles[index.cycles.length - 1]
        const target = active || latest
        return fetch(`/data/cycles/cycle${target.cycle}.json`)
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
          Loading picks…
        </div>
      </div>
    )
  }

  // ── Awaiting New Picks State ──
  if (!weekData) {
    const launchDate = nextCycleDate ? new Date(nextCycleDate) : new Date('2026-06-01')
    const now = new Date()
    const daysUntil = Math.max(0, Math.ceil((launchDate - now) / (1000 * 60 * 60 * 24)))
    const dateFormatted = launchDate.toLocaleDateString('en-AU', { day: 'numeric', month: 'long', year: 'numeric' })

    return (
      <div className="weekly-picks" id="weekly-picks">
        <div className="weekly-picks__awaiting">
          <div className="weekly-picks__awaiting-glow" />
          <div className="weekly-picks__awaiting-icon">⏳</div>
          <h2 className="weekly-picks__awaiting-title">Awaiting New Picks</h2>
          <p className="weekly-picks__awaiting-subtitle">
            Our selection engine has been upgraded with tighter filters, adversarial AI screening,
            and quality-first ranking. The next cycle of high-conviction picks drops on:
          </p>
          <div className="weekly-picks__awaiting-date">
            <span className="weekly-picks__awaiting-date-day">{dateFormatted}</span>
            {daysUntil > 0 && (
              <span className="weekly-picks__awaiting-date-countdown">
                {daysUntil} day{daysUntil !== 1 ? 's' : ''} to go
              </span>
            )}
          </div>
          <div className="weekly-picks__awaiting-features">
            <div className="weekly-picks__awaiting-feature">
              <span className="weekly-picks__awaiting-feature-icon">🛡️</span>
              <span>Macro-aligned sector filtering</span>
            </div>
            <div className="weekly-picks__awaiting-feature">
              <span className="weekly-picks__awaiting-feature-icon">📊</span>
              <span>Relative strength vs ASX200</span>
            </div>
            <div className="weekly-picks__awaiting-feature">
              <span className="weekly-picks__awaiting-feature-icon">🧠</span>
              <span>Adversarial AI conviction screening</span>
            </div>
          </div>
        </div>
      </div>
    )
  }

  const corePicks = weekData.picks.filter(p => p.type === 'core')
  const heroPick = corePicks[0]
  const remainingCore = corePicks.slice(1)
  const isActive = weekData.status === 'active' || weekData.status === 'upcoming'

  // Calculate days remaining in hold period
  const endDate = weekData.endDate ? new Date(weekData.endDate) : null
  const daysRemaining = endDate ? Math.max(0, Math.ceil((endDate - new Date()) / (1000 * 60 * 60 * 24))) : null

  return (
    <div className="weekly-picks" id="weekly-picks">
      {/* Section Header */}
      <div className="weekly-picks__header">
        <div className="weekly-picks__title-group">
          <div className="weekly-picks__week-badge">
            <span className="weekly-picks__week-num">Cycle {weekData.cycle}</span>
            <span className={`weekly-picks__status weekly-picks__status--${weekData.status}`}>
              {weekData.status === 'active' ? '● Live' : weekData.status === 'upcoming' ? '◉ Monday' : '✓ Complete'}
            </span>
          </div>
          <div>
            <h2 className="weekly-picks__title">Current Picks</h2>
            <p className="weekly-picks__subtitle">
              {weekData.dateRange} · {weekData.picks.length} stocks · 4-week hold
              {daysRemaining !== null && isActive && (
                <span className="weekly-picks__days-remaining"> · {daysRemaining}d remaining</span>
              )}
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
              <div className="weekly-picks__hero-tests">{heroPick.testsPassed}/8 tests</div>
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
              {pick.stopTriggered && (
                <span className="weekly-picks__stop-badge" title={pick.stopReason}>
                  🛑 {pick.stopTriggered === 'STOP_LOSS' ? 'Stopped' : 'Trailed'}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
