import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import StockLogo from './StockLogo'
import './WeekArchive.css'

export default function WeekArchive() {
  const [weeksIndex, setWeeksIndex] = useState(null)
  const [weekDetails, setWeekDetails] = useState({})
  const [expandedWeek, setExpandedWeek] = useState(null)
  const [attrib, setAttrib] = useState(null)
  const navigate = useNavigate()

  useEffect(() => {
    fetch('/data/attribution.json')
      .then(res => res.ok ? res.json() : null)
      .then(setAttrib)
      .catch(() => {})
  }, [])

  useEffect(() => {
    fetch('/data/cycles/index.json')
      .then(res => res.ok ? res.json() : null)
      .then(data => {
        if (data) setWeeksIndex(data)
      })
      .catch(() => {})
  }, [])

  const loadWeekDetail = (cycleNum) => {
    if (weekDetails[cycleNum]) return
    fetch(`/data/cycles/cycle${cycleNum}.json`)
      .then(res => res.ok ? res.json() : null)
      .then(data => {
        if (data) setWeekDetails(prev => ({ ...prev, [cycleNum]: data }))
      })
      .catch(() => {})
  }

  const toggleWeek = (weekNum) => {
    if (expandedWeek === weekNum) {
      setExpandedWeek(null)
    } else {
      setExpandedWeek(weekNum)
      loadWeekDetail(weekNum)
    }
  }

  if (!weeksIndex?.cycles?.length) return null

  // Only show completed or active past cycles
  const pastWeeks = weeksIndex.cycles
    .filter(c => c.status === 'completed' || c.status === 'active')
    .sort((a, b) => b.cycle - a.cycle)

  if (pastWeeks.length === 0) return null

  // Calculate cumulative stats
  const cumPnl = pastWeeks.reduce((sum, w) => sum + (w.avgPnlPct || 0), 0)
  const totalWinners = pastWeeks.reduce((sum, w) => sum + (w.winners || 0), 0)
  const totalLosers = pastWeeks.reduce((sum, w) => sum + (w.losers || 0), 0)
  const totalPicks = totalWinners + totalLosers + pastWeeks.reduce((sum, w) => sum + ((w.flat || 0)), 0)
  const winRate = totalPicks > 0 ? ((totalWinners / totalPicks) * 100).toFixed(0) : '—'

  // Build equity curve: $10K compounding weekly returns
  const sortedWeeks = [...pastWeeks].sort((a, b) => a.cycle - b.cycle)
  const startingCapital = 10000
  const equityPoints = [{ week: 0, value: startingCapital, label: 'Start' }]
  let runningValue = startingCapital
  sortedWeeks.forEach(c => {
    runningValue = runningValue * (1 + (c.avgPnlPct || 0) / 100)
    equityPoints.push({ week: c.cycle, value: Math.round(runningValue), label: `C${c.cycle}` })
  })

  // SVG path for equity curve
  const curveData = (() => {
    if (equityPoints.length < 2) return null
    const values = equityPoints.map(p => p.value)
    const minVal = Math.min(...values) * 0.995
    const maxVal = Math.max(...values) * 1.005
    const range = maxVal - minVal || 1
    const w = 100, h = 60
    const coords = equityPoints.map((p, i) => ({
      x: (i / Math.max(equityPoints.length - 1, 1)) * w,
      y: h - ((p.value - minVal) / range) * h
    }))
    const line = coords.map((c, i) => `${i === 0 ? 'M' : 'L'} ${c.x} ${c.y}`).join(' ')
    const area = `${line} L ${w} ${h} L 0 ${h} Z`
    const baseY = h - ((startingCapital - minVal) / range) * h
    const isPositive = values[values.length - 1] >= startingCapital
    return { line, area, baseY, isPositive, finalValue: values[values.length - 1] }
  })()

  return (
    <div className="week-archive" id="week-archive">
      {/* Header */}
      <div className="week-archive__header">
        <div className="week-archive__title-group">
          <span className="week-archive__icon">📁</span>
          <div>
            <h2 className="week-archive__title">Track Record</h2>
            <p className="week-archive__subtitle">{pastWeeks.length} cycles completed · {totalPicks} picks</p>
          </div>
        </div>
      </div>

      {/* Cumulative Stats */}
      <div className="week-archive__stats">
        <div className="week-archive__stat">
          <span className={`week-archive__stat-value ${cumPnl >= 0 ? 'week-archive__stat-value--positive' : 'week-archive__stat-value--negative'}`}>
            {cumPnl >= 0 ? '+' : ''}{cumPnl.toFixed(1)}%
          </span>
          <span className="week-archive__stat-label">Cumulative Return</span>
        </div>
        <div className="week-archive__stat">
          <span className="week-archive__stat-value">{winRate}%</span>
          <span className="week-archive__stat-label">Win Rate</span>
        </div>
        <div className="week-archive__stat">
          <span className="week-archive__stat-value week-archive__stat-value--positive">{totalWinners}</span>
          <span className="week-archive__stat-label">Winners</span>
        </div>
        <div className="week-archive__stat">
          <span className="week-archive__stat-value week-archive__stat-value--negative">{totalLosers}</span>
          <span className="week-archive__stat-label">Losers</span>
        </div>
      </div>

      {/* Equity Curve */}
      {curveData && (
        <div className="week-archive__equity">
          <div className="week-archive__equity-header">
            <span className="week-archive__equity-title">📈 $10K Growth</span>
            <span className={`week-archive__equity-value ${curveData.isPositive ? 'week-archive__stat-value--positive' : 'week-archive__stat-value--negative'}`}>
              ${curveData.finalValue.toLocaleString('en-AU')}
            </span>
          </div>
          <div className="week-archive__equity-chart">
            <svg className="week-archive__equity-svg" viewBox="0 0 100 60" preserveAspectRatio="none">
              <defs>
                <linearGradient id="equityGreenGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="rgba(16, 185, 129, 0.25)" />
                  <stop offset="100%" stopColor="rgba(16, 185, 129, 0)" />
                </linearGradient>
                <linearGradient id="equityRedGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="rgba(239, 68, 68, 0.25)" />
                  <stop offset="100%" stopColor="rgba(239, 68, 68, 0)" />
                </linearGradient>
              </defs>
              <line x1="0" y1={curveData.baseY} x2="100" y2={curveData.baseY}
                stroke="rgba(255,255,255,0.08)" strokeWidth="0.5" strokeDasharray="2,2" />
              <path d={curveData.area}
                fill={curveData.isPositive ? 'url(#equityGreenGrad)' : 'url(#equityRedGrad)'} />
              <path d={curveData.line}
                fill="none" stroke={curveData.isPositive ? 'var(--green-400)' : 'var(--red-400)'}
                strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
          <div className="week-archive__equity-labels">
            {equityPoints.map((p, i) => (
              <span key={i} className="week-archive__equity-label">{p.label}</span>
            ))}
          </div>
        </div>
      )}

      {/* Performance Attribution */}
      {attrib && attrib.totalPicks >= 5 && (
        <div className="week-archive__attrib">
          <div className="week-archive__attrib-title">📊 What's Working</div>
          <div className="week-archive__attrib-grid">
            {/* Grade breakdown */}
            <div className="week-archive__attrib-block">
              <span className="week-archive__attrib-label">By Grade</span>
              <div className="week-archive__attrib-bars">
                {Object.entries(attrib.byGrade)
                  .sort((a, b) => b[1].avg - a[1].avg)
                  .map(([grade, data]) => (
                    <div key={grade} className="week-archive__attrib-bar-row">
                      <span className="week-archive__attrib-bar-label">Grade {grade}</span>
                      <div className="week-archive__attrib-bar-track">
                        <div
                          className={`week-archive__attrib-bar-fill ${data.avg >= 0 ? 'week-archive__attrib-bar-fill--positive' : 'week-archive__attrib-bar-fill--negative'}`}
                          style={{ width: `${Math.min(Math.abs(data.avg) * 5, 100)}%` }}
                        />
                      </div>
                      <span className={`week-archive__attrib-bar-value ${data.avg >= 0 ? 'week-archive__stat-value--positive' : 'week-archive__stat-value--negative'}`}>
                        {data.avg >= 0 ? '+' : ''}{data.avg.toFixed(1)}%
                      </span>
                    </div>
                  ))}
              </div>
            </div>
            {/* Sector breakdown - top 3 and bottom 3 */}
            <div className="week-archive__attrib-block">
              <span className="week-archive__attrib-label">By Sector</span>
              <div className="week-archive__attrib-bars">
                {Object.entries(attrib.bySector)
                  .sort((a, b) => b[1].avg - a[1].avg)
                  .slice(0, 4)
                  .map(([sector, data]) => (
                    <div key={sector} className="week-archive__attrib-bar-row">
                      <span className="week-archive__attrib-bar-label">{sector.replace('Consumer ', '').replace('Financial ', 'Fin ')}</span>
                      <div className="week-archive__attrib-bar-track">
                        <div
                          className={`week-archive__attrib-bar-fill ${data.avg >= 0 ? 'week-archive__attrib-bar-fill--positive' : 'week-archive__attrib-bar-fill--negative'}`}
                          style={{ width: `${Math.min(Math.abs(data.avg) * 5, 100)}%` }}
                        />
                      </div>
                      <span className={`week-archive__attrib-bar-value ${data.avg >= 0 ? 'week-archive__stat-value--positive' : 'week-archive__stat-value--negative'}`}>
                        {data.avg >= 0 ? '+' : ''}{data.avg.toFixed(1)}%
                      </span>
                    </div>
                  ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Week Accordion */}
      <div className="week-archive__weeks">
        {pastWeeks.map(week => {
          const isExpanded = expandedWeek === week.cycle
          const detail = weekDetails[week.cycle]

          return (
            <div key={week.cycle} className={`week-archive__week ${isExpanded ? 'week-archive__week--expanded' : ''}`}>
              <button
                className="week-archive__week-header"
                onClick={() => toggleWeek(week.cycle)}
              >
                <div className="week-archive__week-left">
                  <span className="week-archive__week-num">Cycle {week.cycle}</span>
                  <span className="week-archive__week-dates">{week.dateRange}</span>
                </div>
                <div className="week-archive__week-right">
                  <span className={`week-archive__week-pnl ${(week.avgPnlPct || 0) >= 0 ? 'week-archive__week-pnl--positive' : 'week-archive__week-pnl--negative'}`}>
                    {(week.avgPnlPct || 0) >= 0 ? '+' : ''}{(week.avgPnlPct || 0).toFixed(1)}%
                  </span>
                  <span className="week-archive__week-record">
                    {week.winners || 0}W · {week.losers || 0}L
                  </span>
                  <span className={`week-archive__chevron ${isExpanded ? 'week-archive__chevron--open' : ''}`}>
                    ›
                  </span>
                </div>
              </button>

              {/* Expanded Detail */}
              {isExpanded && detail && (
                <div className="week-archive__detail">
                  {detail.picks.map(pick => (
                    <div
                      key={pick.ticker}
                      className="week-archive__pick"
                      onClick={() => navigate(`/stock/${pick.ticker}`)}
                    >
                      <div className="week-archive__pick-left">
                        <StockLogo ticker={pick.ticker} name={pick.name} className="week-archive__pick-logo" />
                        <div className="week-archive__pick-info">
                          <div className="week-archive__pick-ticker">
                            {pick.ticker}
                            {pick.type === 'speculative' && (
                              <span className="week-archive__pick-spec">🔥</span>
                            )}
                          </div>
                          <div className="week-archive__pick-name">{pick.name}</div>
                        </div>
                      </div>
                      <div className="week-archive__pick-mid">
                        <span className="week-archive__pick-entry">A${pick.entryPrice?.toFixed(2)}</span>
                        <span className="week-archive__pick-arrow">→</span>
                        <span className="week-archive__pick-exit">
                          A${(pick.weekClosePrice || pick.currentPrice)?.toFixed(2)}
                        </span>
                      </div>
                      <div className="week-archive__pick-right">
                        <span className={`week-archive__pick-pnl ${pick.pnlPct > 0 ? 'week-archive__pick-pnl--positive' : pick.pnlPct < 0 ? 'week-archive__pick-pnl--negative' : ''}`}>
                          {pick.pnlPct !== 0 ? `${pick.pnlPct > 0 ? '+' : ''}${pick.pnlPct.toFixed(1)}%` : '—'}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {isExpanded && !detail && (
                <div className="week-archive__detail week-archive__detail--loading">
                  Loading…
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
