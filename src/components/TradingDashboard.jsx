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
      cash: portfolio.cash ?? 0,
      openCount: (portfolio.openPositions || []).length,
      winRate: portfolio.winRate ?? 0,
      totalTrades: portfolio.totalTrades ?? 0,
      wins: portfolio.wins ?? 0,
      losses: portfolio.losses ?? 0,
      bestTrade: portfolio.bestTrade,
      worstTrade: portfolio.worstTrade,
      avgWin: portfolio.avgWin ?? 0,
      avgLoss: portfolio.avgLoss ?? 0,
    }
  }, [portfolio])

  // Equity curve SVG
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

    return { linePath, areaPath, baselineY, isPositive }
  }, [portfolio])

  const openPositions = portfolio?.openPositions || []

  // Trade history — most recent first, sells only for display
  const tradeHistory = useMemo(() => {
    if (!portfolio?.tradeHistory) return []
    return [...portfolio.tradeHistory]
      .filter(t => t.side === 'SELL')
      .reverse()
      .slice(0, 15)
  }, [portfolio])

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

  const pctToTarget = (pos) => {
    if (!pos.targetPrice || !pos.entryPrice) return 0
    const totalGap = pos.targetPrice - pos.entryPrice
    const currentGap = (pos.currentPrice || pos.entryPrice) - pos.entryPrice
    if (totalGap <= 0) return 0
    return Math.min(Math.max((currentGap / totalGap) * 100, -20), 100)
  }

  const exitReasonClass = (reason) => {
    if (!reason) return ''
    if (reason.includes('PROFIT') || reason.includes('TARGET')) return 'trade-row__reason--take-profit'
    if (reason.includes('STOP')) return 'trade-row__reason--stop-loss'
    if (reason.includes('TRAIL')) return 'trade-row__reason--trailing'
    if (reason.includes('CHoCH')) return 'trade-row__reason--choch'
    return 'trade-row__reason--time-exit'
  }

  const confluenceEmoji = (c) => {
    const map = { STRUCTURE: '📐', BOS: '💥', CHoCH: '🔄', SWEEP: '🧹', FVG: '📊', OB: '🧱', VOL: '📈', RSI: '⚡' }
    return map[c] || '✓'
  }

  if (loading) {
    return (
      <div className="trading-dashboard">
        <div className="trading-loading">Loading trading data…</div>
      </div>
    )
  }

  if (!portfolio) return null

  return (
    <div className="trading-dashboard" id="trading-dashboard">
      {/* Header */}
      <div className="trading-dashboard__header">
        <div className="trading-dashboard__title-group">
          <div className="trading-dashboard__icon">📊</div>
          <div>
            <h2 className="trading-dashboard__title">Live Portfolio</h2>
            <p className="trading-dashboard__subtitle" style={{ fontSize: '0.7rem', opacity: 0.6 }}>SMC v3 · 
              Paper trading · Updated {fmtDate(portfolio.lastUpdated)}
            </p>
          </div>
        </div>
        <div className="trading-dashboard__badge">Paper Trading</div>
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
          <div className="trading-stat__label">Cash Available</div>
          <div className="trading-stat__value trading-stat__value--neutral">
            A${stats.cash.toLocaleString('en-AU', { minimumFractionDigits: 2 })}
          </div>
          <div className="trading-stat__delta" style={{ color: 'var(--text-muted)' }}>
            {((stats.cash / stats.totalValue) * 100).toFixed(0)}% of portfolio
          </div>
        </div>

        <div className="trading-stat trading-stat--amber">
          <div className="trading-stat__label">Positions</div>
          <div className="trading-stat__value trading-stat__value--neutral">
            {stats.openCount}<span className="trading-stat__value-sub"> / 8</span>
          </div>
          <div className="trading-stat__delta" style={{ color: 'var(--text-muted)' }}>
            slots filled
          </div>
        </div>

        <div className={`trading-stat ${stats.winRate >= 50 ? 'trading-stat--pnl-positive' : 'trading-stat--neutral'}`}>
          <div className="trading-stat__label">Win Rate</div>
          <div className="trading-stat__value trading-stat__value--neutral">
            {stats.totalTrades > 0 ? `${stats.winRate.toFixed(0)}%` : '—'}
          </div>
          <div className="trading-stat__delta" style={{ color: 'var(--text-muted)' }}>
            {stats.wins}W / {stats.losses}L · {stats.totalTrades} closed
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
        </div>
      )}

      {/* Open Positions + Trade History */}
      <div className="trading-sections">
        {/* Open Positions */}
        <div className="trading-section">
          <div className="trading-section__header">
            <span className="trading-section__title">🟢 Open Positions</span>
            <span className="trading-section__count">{openPositions.length}</span>
          </div>

          {openPositions.length === 0 ? (
            <div className="trading-empty">
              <div className="trading-empty__icon">🔍</div>
              <p>Scanning for SMC-confirmed entries…</p>
              <p style={{ fontSize: '0.75rem', opacity: 0.5, marginTop: '4px' }}>Requires: weekly bullish + daily BOS/CHoCH + sweep + FVG + 3:1 R:R</p>
            </div>
          ) : (
            openPositions.map(pos => {
              const progress = pctToTarget(pos)
              return (
                <div
                  key={pos.ticker}
                  className="position-row"
                  onClick={() => navigate(`/stock/${pos.ticker}`)}
                >
                  <div className="position-row__info">
                    <div className="position-row__ticker">{pos.ticker}</div>
                    <div className="position-row__name">{pos.name}</div>
                  </div>

                  <div className="position-row__progress-col">
                    <div className="position-row__prices">
                      <span className="position-row__entry">A${pos.entryPrice.toFixed(2)}</span>
                      <span className="position-row__arrow">→</span>
                      <span className="position-row__target">A${pos.targetPrice?.toFixed(2)}</span>
                    </div>
                    <div className="position-row__progress-bar">
                      <div
                        className={`position-row__progress-fill ${progress >= 0 ? 'position-row__progress-fill--positive' : 'position-row__progress-fill--negative'}`}
                        style={{ width: `${Math.abs(Math.min(progress, 100))}%` }}
                      />
                    </div>
                    <div className="position-row__stop">
                      Stop: A${pos.stopPrice?.toFixed(2) || '—'}
                      {pos.smc?.confluences && (
                        <span className="position-row__confluences">
                          {pos.smc.confluences.map(c => (
                            <span key={c} className="position-row__confluence-badge" title={c}>
                              {confluenceEmoji(c)}
                            </span>
                          ))}
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="position-row__pnl">
                    <div className={`position-row__pnl-value ${pos.pnl >= 0 ? 'position-row__pnl-value--positive' : 'position-row__pnl-value--negative'}`}>
                      {fmt(pos.pnl)}
                    </div>
                    <div className={`position-row__pnl-pct ${pos.pnlPct >= 0 ? 'position-row__pnl-value--positive' : 'position-row__pnl-value--negative'}`}>
                      {pos.pnlPct >= 0 ? '+' : ''}{pos.pnlPct?.toFixed(1) ?? '0.0'}%
                      {pos.rMultiple != null && (
                        <span className="position-row__r-multiple">
                          {pos.rMultiple >= 0 ? '+' : ''}{pos.rMultiple}R
                        </span>
                      )}
                    </div>
                    <div className="position-row__shares">{pos.shares} shares</div>
                  </div>
                </div>
              )
            })
          )}
        </div>

        {/* Trade History */}
        <div className="trading-section">
          <div className="trading-section__header">
            <span className="trading-section__title">📋 Closed Trades</span>
            <span className="trading-section__count">{tradeHistory.length}</span>
          </div>

          {tradeHistory.length === 0 ? (
            <div className="trading-empty">
              <div className="trading-empty__icon">⏳</div>
              <p>No closed trades yet — positions are still open</p>
            </div>
          ) : (
            tradeHistory.map((trade, i) => (
              <div key={`${trade.ticker}-${trade.exitDate}-${i}`} className="trade-row">
                <div className="trade-row__info">
                  <span className="trade-row__ticker">{trade.ticker}</span>
                  <span className="trade-row__date">{fmtDate(trade.exitDate)} · {trade.holdDays}d</span>
                </div>
                {trade.exitReason && (
                  <span className={`trade-row__reason ${exitReasonClass(trade.exitReason)}`}>
                    {trade.exitReason}
                  </span>
                )}
                <span className={`trade-row__pnl ${trade.pnl > 0 ? 'trade-row__pnl--positive' : trade.pnl < 0 ? 'trade-row__pnl--negative' : 'trade-row__pnl--neutral'}`}>
                  {fmt(trade.pnl)} ({trade.pnlPct > 0 ? '+' : ''}{trade.pnlPct?.toFixed(1)}%)
                  {trade.rMultiple != null && (
                    <span className="trade-row__r-tag">{trade.rMultiple >= 0 ? '+' : ''}{trade.rMultiple}R</span>
                  )}
                </span>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Disclaimer */}
      <div className="trading-disclaimer">
        ⚠️ Paper trading only — no real money invested. Past simulated performance does not guarantee future results.
      </div>
    </div>
  )
}
