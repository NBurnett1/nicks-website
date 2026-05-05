import { useState, useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import './TradingDashboard.css'

export default function TradingDashboard() {
  const [portfolio, setPortfolio] = useState(null)
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    fetch('/data/portfolio.json')
      .then(res => {
        if (!res.ok) throw new Error('No portfolio data')
        return res.json()
      })
      .then(data => {
        setPortfolio(data)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [])

  const stats = useMemo(() => {
    if (!portfolio) return null
    return {
      totalValue: portfolio.totalValue ?? 10000,
      startingCapital: portfolio.startingCapital ?? 10000,
      pnl: portfolio.totalPnL ?? 0,
      pnlPct: portfolio.totalPnLPct ?? 0,
      winRate: portfolio.winRate ?? 0,
      totalTrades: portfolio.totalTrades ?? 0,
      wins: portfolio.wins ?? 0,
      losses: portfolio.losses ?? 0,
      flat: portfolio.flat ?? 0,
      bestTrade: portfolio.bestTrade,
      worstTrade: portfolio.worstTrade,
      avgWin: portfolio.avgWin ?? 0,
      avgLoss: portfolio.avgLoss ?? 0,
      currentCycle: portfolio.currentCycle ?? 0,
      completedCycles: portfolio.completedCycles ?? 0,
      totalCycles: portfolio.totalCycles ?? 0,
    }
  }, [portfolio])

  // Equity curve SVG from weekly returns
  const equityCurve = useMemo(() => {
    if (!portfolio?.equityCurve?.length || portfolio.equityCurve.length < 2) return null
    const points = portfolio.equityCurve
    const values = points.map(p => p.value)
    const minVal = Math.min(...values) * 0.998
    const maxVal = Math.max(...values) * 1.002
    const range = maxVal - minVal || 1

    const width = 100
    const height = 100

    const coords = values.map((v, i) => ({
      x: (i / Math.max(values.length - 1, 1)) * width,
      y: height - ((v - minVal) / range) * height,
    }))

    const linePath = coords.map((c, i) => `${i === 0 ? 'M' : 'L'} ${c.x} ${c.y}`).join(' ')
    const areaPath = `${linePath} L ${width} ${height} L 0 ${height} Z`
    const baselineY = height - ((portfolio.startingCapital - minVal) / range) * height
    const isPositive = values[values.length - 1] >= portfolio.startingCapital

    return { linePath, areaPath, baselineY, isPositive, labels: points }
  }, [portfolio])

  const openPositions = portfolio?.openPositions || []

  // Trade history — most recent first
  const tradeHistory = useMemo(() => {
    if (!portfolio?.tradeHistory) return []
    return [...portfolio.tradeHistory].reverse().slice(0, 20)
  }, [portfolio])

  // Weekly returns
  const cycleReturns = portfolio?.cycleReturns || []

  const fmt = (val, prefix = 'A$') => {
    if (val == null) return '—'
    const abs = Math.abs(val)
    const sign = val < 0 ? '-' : val > 0 ? '+' : ''
    return `${sign}${prefix}${abs.toLocaleString('en-AU', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
  }

  const fmtDate = (iso) => {
    if (!iso) return '—'
    const d = new Date(iso)
    return d.toLocaleDateString('en-AU', { day: 'numeric', month: 'short' })
  }

  if (loading) {
    return (
      <div className="trading-dashboard">
        <div className="trading-loading">Loading portfolio data…</div>
      </div>
    )
  }

  if (!portfolio) return null

  return (
    <div className="trading-dashboard" id="trading-dashboard">
      {/* Header */}
      <div className="trading-dashboard__header">
        <div className="trading-dashboard__title-group">
          <div className="trading-dashboard__icon">💰</div>
          <div>
            <h2 className="trading-dashboard__title">Monthly Conviction Portfolio</h2>
            <p className="trading-dashboard__subtitle" style={{ fontSize: '0.7rem', opacity: 0.6 }}>
              Equal-weight · 4-week holds · Stop-loss protected · Updated {fmtDate(portfolio.lastUpdated)}
            </p>
          </div>
        </div>
        <div className="trading-dashboard__badge">
          Cycle {stats.currentCycle} {stats.completedCycles > 0 ? `· ${stats.completedCycles} completed` : '· Active'}
        </div>
      </div>

      {/* Stats Grid */}
      <div className="trading-stats">
        <div className={`trading-stat ${stats.pnl >= 0 ? 'trading-stat--pnl-positive' : 'trading-stat--pnl-negative'}`}>
          <div className="trading-stat__label">Portfolio Value</div>
          <div className={`trading-stat__value ${stats.pnl >= 0 ? 'trading-stat__value--positive' : 'trading-stat__value--negative'}`}>
            A${stats.totalValue.toLocaleString('en-AU', { minimumFractionDigits: 2 })}
          </div>
          <div className={`trading-stat__delta ${stats.pnlPct >= 0 ? 'trading-stat__delta--positive' : 'trading-stat__delta--negative'}`}>
            {stats.pnlPct >= 0 ? '↑' : '↓'} {fmt(stats.pnl)} ({stats.pnlPct >= 0 ? '+' : ''}{stats.pnlPct.toFixed(1)}%)
          </div>
        </div>

        <div className="trading-stat trading-stat--neutral">
          <div className="trading-stat__label">Starting Capital</div>
          <div className="trading-stat__value trading-stat__value--neutral">
            A${stats.startingCapital.toLocaleString('en-AU', { minimumFractionDigits: 2 })}
          </div>
          <div className="trading-stat__delta" style={{ color: 'var(--text-muted)' }}>
            $2,500 per pick (equal-weight)
          </div>
        </div>

        <div className="trading-stat trading-stat--amber">
          <div className="trading-stat__label">Active Positions</div>
          <div className="trading-stat__value trading-stat__value--neutral">
            {openPositions.length}<span className="trading-stat__value-sub"> picks</span>
          </div>
          <div className="trading-stat__delta" style={{ color: 'var(--text-muted)' }}>
            Week {Math.ceil((new Date() - new Date(portfolio.startDate)) / (7 * 24 * 60 * 60 * 1000)) || 1} of Cycle {stats.currentCycle}
          </div>
        </div>

        <div className={`trading-stat ${stats.winRate >= 50 ? 'trading-stat--pnl-positive' : 'trading-stat--neutral'}`}>
          <div className="trading-stat__label">Win Rate</div>
          <div className="trading-stat__value trading-stat__value--neutral">
            {stats.totalTrades > 0 ? `${stats.winRate.toFixed(0)}%` : '—'}
          </div>
          <div className="trading-stat__delta" style={{ color: 'var(--text-muted)' }}>
            {stats.totalTrades > 0
              ? `${stats.wins}W / ${stats.losses}L / ${stats.flat}F · ${stats.totalTrades} closed`
              : 'No completed cycles yet'}
          </div>
        </div>
      </div>

      {/* Equity Curve */}
      {equityCurve && (
        <div className="equity-curve">
          <div className="equity-curve__header">
            <span className="equity-curve__title">📈 Equity Curve</span>
            <span className={`equity-curve__current ${equityCurve.isPositive ? 'trading-stat__value--positive' : 'trading-stat__value--negative'}`}>
              A${stats.totalValue.toLocaleString('en-AU', { minimumFractionDigits: 2 })}
            </span>
          </div>
          <div className="equity-curve__chart">
            <svg className="equity-curve__svg" viewBox="0 0 100 100" preserveAspectRatio="none">
              <defs>
                <linearGradient id="greenGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="rgba(16, 185, 129, 0.3)" />
                  <stop offset="100%" stopColor="rgba(16, 185, 129, 0)" />
                </linearGradient>
                <linearGradient id="redGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="rgba(239, 68, 68, 0.3)" />
                  <stop offset="100%" stopColor="rgba(239, 68, 68, 0)" />
                </linearGradient>
              </defs>
              <line x1="0" y1={equityCurve.baselineY} x2="100" y2={equityCurve.baselineY} className="equity-curve__baseline" />
              <path d={equityCurve.areaPath} className={equityCurve.isPositive ? 'equity-curve__area--positive' : 'equity-curve__area--negative'} />
              <path d={equityCurve.linePath} className={`equity-curve__line ${equityCurve.isPositive ? 'equity-curve__line--positive' : 'equity-curve__line--negative'}`} />
            </svg>
          </div>
          {/* Weekly return labels */}
          {cycleReturns.length > 0 && (
            <div className="equity-curve__labels">
              {cycleReturns.map(cr => (
                <span key={cr.cycle} className={`equity-curve__label ${cr.returnPct >= 0 ? 'equity-curve__label--positive' : 'equity-curve__label--negative'}`}>
                  C{cr.cycle}: {cr.returnPct >= 0 ? '+' : ''}{cr.returnPct.toFixed(1)}%
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Open Positions + Trade History */}
      <div className="trading-sections">
        {/* Open Positions */}
        <div className="trading-section">
          <div className="trading-section__header">
            <span className="trading-section__title">🟢 Active Positions</span>
            <span className="trading-section__count">{openPositions.length}</span>
          </div>

          {openPositions.length === 0 ? (
            <div className="trading-empty">
              <div className="trading-empty__icon">📅</div>
              <p>No active positions — waiting for next cycle's picks</p>
            </div>
          ) : (
            openPositions.map(pos => (
              <div
                key={pos.ticker}
                className="position-row"
                onClick={() => navigate(`/stock/${pos.ticker}`)}
              >
                <div className="position-row__info">
                  <div className="position-row__ticker">
                    {pos.ticker}
                    <span className={`position-row__grade position-row__grade--${pos.grade?.toLowerCase()}`}>
                      {pos.grade}
                    </span>
                  </div>
                  <div className="position-row__name">{pos.name}</div>
                </div>

                <div className="position-row__progress-col">
                  <div className="position-row__prices">
                    <span className="position-row__entry">A${pos.entryPrice.toFixed(2)}</span>
                    <span className="position-row__arrow">→</span>
                    <span className={pos.exitPrice >= pos.entryPrice ? 'position-row__target' : 'position-row__entry'}>
                      A${pos.exitPrice.toFixed(2)}
                    </span>
                  </div>
                  <div className="position-row__alloc-bar">
                    <div
                      className={`position-row__alloc-fill ${pos.pnl >= 0 ? 'position-row__progress-fill--positive' : 'position-row__progress-fill--negative'}`}
                      style={{ width: `${Math.min(Math.abs(pos.pnlPct) * 10, 100)}%` }}
                    />
                  </div>
                  <div className="position-row__stop">
                    {pos.shares} shares · A${pos.allocation.toLocaleString('en-AU', { minimumFractionDigits: 0 })} allocated
                  </div>
                </div>

                <div className="position-row__pnl">
                  <div className={`position-row__pnl-value ${pos.pnl >= 0 ? 'position-row__pnl-value--positive' : 'position-row__pnl-value--negative'}`}>
                    {fmt(pos.pnl)}
                  </div>
                  <div className={`position-row__pnl-pct ${pos.pnlPct >= 0 ? 'position-row__pnl-value--positive' : 'position-row__pnl-value--negative'}`}>
                    {pos.pnlPct >= 0 ? '+' : ''}{pos.pnlPct.toFixed(1)}%
                  </div>
                  <div className="position-row__shares">{pos.type === 'speculative' ? '🔥 Spec' : 'Core'}</div>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Closed Trades / Weekly History */}
        <div className="trading-section">
          <div className="trading-section__header">
            <span className="trading-section__title">📋 Completed Cycles</span>
            <span className="trading-section__count">{stats.completedCycles}</span>
          </div>

          {tradeHistory.length === 0 && stats.completedCycles === 0 ? (
            <div className="trading-empty">
              <div className="trading-empty__icon">⏳</div>
              <p>No completed cycles yet</p>
              <p style={{ fontSize: '0.75rem', opacity: 0.5, marginTop: '4px' }}>
                Positions close after the 4-week holding period
              </p>
            </div>
          ) : (
            tradeHistory.map((trade, i) => (
              <div key={`${trade.ticker}-${trade.week}-${i}`} className="trade-row">
                <div className="trade-row__info">
                  <span className="trade-row__ticker">{trade.ticker}</span>
                  <span className="trade-row__date">
                    Cycle {trade.cycle} · {trade.dateRange}
                  </span>
                </div>
                <span className="trade-row__grade-tag">
                  Grade {trade.grade}
                </span>
                <span className={`trade-row__pnl ${trade.pnl > 0 ? 'trade-row__pnl--positive' : trade.pnl < 0 ? 'trade-row__pnl--negative' : 'trade-row__pnl--neutral'}`}>
                  {fmt(trade.pnl)} ({trade.pnlPct > 0 ? '+' : ''}{trade.pnlPct.toFixed(1)}%)
                </span>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Disclaimer */}
      <div className="trading-disclaimer">
        ⚠️ Paper trading only — no real money invested. Equal-weight 4-week conviction strategy.
        Past simulated performance does not guarantee future results.
      </div>
    </div>
  )
}
