import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import StockLogo from './StockLogo'
import './WeekArchive.css'

export default function WeekArchive() {
  const [weeksIndex, setWeeksIndex] = useState(null)
  const [weekDetails, setWeekDetails] = useState({})
  const [expandedWeek, setExpandedWeek] = useState(null)
  const navigate = useNavigate()

  useEffect(() => {
    fetch('/data/weeks/index.json')
      .then(res => res.ok ? res.json() : null)
      .then(data => {
        if (data) setWeeksIndex(data)
      })
      .catch(() => {})
  }, [])

  const loadWeekDetail = (weekNum) => {
    if (weekDetails[weekNum]) return
    fetch(`/data/weeks/week${weekNum}.json`)
      .then(res => res.ok ? res.json() : null)
      .then(data => {
        if (data) setWeekDetails(prev => ({ ...prev, [weekNum]: data }))
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

  if (!weeksIndex?.weeks?.length) return null

  // Only show completed or active past weeks (not upcoming, not current active)
  const pastWeeks = weeksIndex.weeks
    .filter(w => w.status === 'completed' || w.status === 'active')
    .sort((a, b) => b.week - a.week)

  if (pastWeeks.length === 0) return null

  // Calculate cumulative stats
  const cumPnl = pastWeeks.reduce((sum, w) => sum + (w.avgPnlPct || 0), 0)
  const totalWinners = pastWeeks.reduce((sum, w) => sum + (w.winners || 0), 0)
  const totalLosers = pastWeeks.reduce((sum, w) => sum + (w.losers || 0), 0)
  const totalPicks = totalWinners + totalLosers + pastWeeks.reduce((sum, w) => sum + ((w.flat || 0)), 0)
  const winRate = totalPicks > 0 ? ((totalWinners / totalPicks) * 100).toFixed(0) : '—'

  return (
    <div className="week-archive" id="week-archive">
      {/* Header */}
      <div className="week-archive__header">
        <div className="week-archive__title-group">
          <span className="week-archive__icon">📁</span>
          <div>
            <h2 className="week-archive__title">Track Record</h2>
            <p className="week-archive__subtitle">{pastWeeks.length} weeks completed · {totalPicks} picks</p>
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

      {/* Week Accordion */}
      <div className="week-archive__weeks">
        {pastWeeks.map(week => {
          const isExpanded = expandedWeek === week.week
          const detail = weekDetails[week.week]

          return (
            <div key={week.week} className={`week-archive__week ${isExpanded ? 'week-archive__week--expanded' : ''}`}>
              <button
                className="week-archive__week-header"
                onClick={() => toggleWeek(week.week)}
              >
                <div className="week-archive__week-left">
                  <span className="week-archive__week-num">Week {week.week}</span>
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
