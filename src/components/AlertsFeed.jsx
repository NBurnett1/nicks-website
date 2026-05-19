import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import './AlertsFeed.css'

const TYPE_CONFIG = {
  PRICE_MOVE:     { icon: '📈', label: 'Price Move' },
  EXTREME_VOLUME: { icon: '🔥', label: 'Extreme Volume' },
  VOLUME_SPIKE:   { icon: '📊', label: 'Volume Spike' },
  INSIDER_BUY:    { icon: '🟢', label: 'Insider Buy' },
  INSIDER_SELL:   { icon: '🔴', label: 'Insider Sell' },
  NEWS:           { icon: '📰', label: 'News' },
}

const SEVERITY_CLASS = {
  critical: 'alert-item--critical',
  high: 'alert-item--high',
  medium: 'alert-item--medium',
  low: 'alert-item--low',
}

function timeAgo(timestamp) {
  if (!timestamp) return ''
  try {
    const d = new Date(timestamp)
    const now = new Date()
    const diff = Math.floor((now - d) / 1000)
    if (diff < 60) return 'just now'
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
    if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`
    return d.toLocaleDateString()
  } catch {
    return ''
  }
}

export default function AlertsFeed() {
  const [alerts, setAlerts] = useState([])
  const [meta, setMeta] = useState({})
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('ALL')
  const [expanded, setExpanded] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    fetch('/data/alerts.json')
      .then(res => {
        if (!res.ok) throw new Error('No alerts')
        return res.json()
      })
      .then(data => {
        // Sort alerts by timestamp: most recent first
        const sortedAlerts = (data.alerts || []).sort((a, b) => {
          const dateA = new Date(a.timestamp || 0)
          const dateB = new Date(b.timestamp || 0)
          return dateB - dateA
        })
        setAlerts(sortedAlerts)
        setMeta({
          lastUpdated: data.lastUpdated,
          stocksScanned: data.stocksScanned,
          totalAlerts: data.totalAlerts,
        })
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [])

  if (loading || alerts.length === 0) return null

  const filters = ['ALL', 'VOLUME', 'INSIDER', 'NEWS', 'PRICE']
  const filtered = filter === 'ALL'
    ? alerts
    : alerts.filter(a => {
        if (filter === 'VOLUME') return a.type.includes('VOLUME')
        if (filter === 'INSIDER') return a.type.includes('INSIDER')
        if (filter === 'NEWS') return a.type === 'NEWS'
        if (filter === 'PRICE') return a.type === 'PRICE_MOVE'
        return true
      })

  const displayAlerts = expanded ? filtered : filtered.slice(0, 8)

  return (
    <div className="alerts-feed animate-fade-in-up">
      <div className="alerts-feed__header">
        <div className="alerts-feed__title-row">
          <h2 className="alerts-feed__title">
            <span className="alerts-feed__title-icon">⚡</span>
            Market Intelligence
          </h2>
          <div className="alerts-feed__meta">
            <span className="alerts-feed__badge">{meta.totalAlerts} alerts</span>
            <span className="alerts-feed__updated">
              Updated {timeAgo(meta.lastUpdated)}
            </span>
          </div>
        </div>

        <div className="alerts-feed__filters">
          {filters.map(f => (
            <button
              key={f}
              className={`alerts-feed__filter ${filter === f ? 'alerts-feed__filter--active' : ''}`}
              onClick={(e) => { e.stopPropagation(); setFilter(f) }}
            >
              {f === 'ALL' ? '🌐 All' :
               f === 'VOLUME' ? '📊 Volume' :
               f === 'INSIDER' ? '👤 Insider' :
               f === 'NEWS' ? '📰 News' :
               '📈 Price'}
            </button>
          ))}
        </div>
      </div>

      <div className="alerts-feed__list">
        {displayAlerts.map((alert, i) => {
          const config = TYPE_CONFIG[alert.type] || { icon: '📋', label: alert.type }
          const sevClass = SEVERITY_CLASS[alert.severity] || ''

          return (
            <div
              key={`${alert.ticker}-${alert.type}-${i}`}
              className={`alert-item ${sevClass}`}
              onClick={(e) => {
                e.stopPropagation()
                navigate(`/stock/${alert.ticker}`)
              }}
            >
              <div className="alert-item__icon">{config.icon}</div>
              <div className="alert-item__content">
                <div className="alert-item__top-row">
                  <span className="alert-item__ticker">{alert.ticker}</span>
                  <span className="alert-item__type-badge">{config.label}</span>
                  {alert.sentiment && alert.sentiment !== 'neutral' && (
                    <span className={`alert-item__sentiment alert-item__sentiment--${alert.sentiment}`}>
                      {alert.sentiment === 'positive' ? '↑' : '↓'}
                    </span>
                  )}
                  <span className="alert-item__time">{timeAgo(alert.timestamp)}</span>
                </div>
                <p className="alert-item__headline">{alert.headline}</p>
                {alert.detail && (
                  <p className="alert-item__detail">{alert.detail}</p>
                )}
              </div>
              <div className="alert-item__exchange">{alert.exchange}</div>
            </div>
          )
        })}
      </div>

      {filtered.length > 8 && (
        <button
          className="alerts-feed__expand"
          onClick={(e) => { e.stopPropagation(); setExpanded(!expanded) }}
        >
          {expanded ? 'Show less ↑' : `Show all ${filtered.length} alerts ↓`}
        </button>
      )}
    </div>
  )
}
