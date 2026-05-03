import { useState, useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import StockLogo from './StockLogo'
import './UndervaluedScreener.css'

const TEST_KEYS = [
  { key: 'peDiscount', short: 'P/E' },
  { key: 'pbBelowBook', short: 'P/B' },
  { key: 'evEbitdaCheap', short: 'EV/EB' },
  { key: 'fcfYieldStrong', short: 'FCF' },
  { key: 'forwardPeRerate', short: 'Fwd PE' },
  { key: 'profitabilityCheck', short: 'Profit' },
]

const GRADE_LABELS = {
  A: 'Strong Buy',
  B: 'Buy Signal',
  C: 'Moderate',
  D: 'Weak',
  F: 'No Signal',
}

const SORT_OPTIONS = [
  { key: 'grade', label: 'Grade' },
  { key: 'testsPassed', label: 'Tests Passed' },
  { key: 'price', label: 'Price' },
  { key: 'sector', label: 'Sector' },
]

export default function UndervaluedScreener({ exchange = 'ASX' }) {
  const [stocks, setStocks] = useState([])
  const [loading, setLoading] = useState(true)
  const [detailCache, setDetailCache] = useState({})
  const [sortBy, setSortBy] = useState('grade')
  const [minGrade, setMinGrade] = useState('all')
  const [sectorFilter, setSectorFilter] = useState('all')
  const [showCount, setShowCount] = useState(20)
  const navigate = useNavigate()

  // Load index data
  useEffect(() => {
    const exchangeKey = exchange.toLowerCase()
    fetch(`/data/${exchangeKey}_index.json`)
      .then(res => res.ok ? res.json() : null)
      .then(data => {
        if (!data) { setLoading(false); return }
        // Only undervalued stocks with test data
        const undervalued = (data.undervalued || [])
          .filter(s => s.testsPassed != null)
        setStocks(undervalued)
        setLoading(false)

        // Lazy-load detail files for all undervalued stocks
        undervalued.forEach(s => {
          fetch(`/data/${exchangeKey}/details/${s.ticker}.json`)
            .then(res => res.ok ? res.json() : null)
            .then(detail => {
              if (detail) {
                setDetailCache(prev => ({ ...prev, [s.ticker]: detail }))
              }
            })
            .catch(() => {})
        })
      })
      .catch(() => setLoading(false))
  }, [exchange])

  // Get list of sectors for filter
  const sectors = useMemo(() => {
    const set = new Set(stocks.map(s => s.sector).filter(Boolean))
    return [...set].sort()
  }, [stocks])

  // Filter and sort
  const filteredStocks = useMemo(() => {
    let result = [...stocks]

    // Grade filter
    if (minGrade !== 'all') {
      const gradeOrder = { A: 5, B: 4, C: 3, D: 2, F: 1 }
      const minVal = gradeOrder[minGrade] || 0
      result = result.filter(s => {
        const grade = s.grade || detailCache[s.ticker]?.grade || 'F'
        return (gradeOrder[grade] || 0) >= minVal
      })
    }

    // Sector filter
    if (sectorFilter !== 'all') {
      result = result.filter(s => s.sector === sectorFilter)
    }

    // Sort
    const gradeOrder = { A: 5, B: 4, C: 3, D: 2, F: 1 }
    result.sort((a, b) => {
      if (sortBy === 'grade') {
        const ga = gradeOrder[a.grade || 'F'] || 0
        const gb = gradeOrder[b.grade || 'F'] || 0
        if (gb !== ga) return gb - ga
        return (b.testsPassed || 0) - (a.testsPassed || 0)
      }
      if (sortBy === 'testsPassed') {
        return (b.testsPassed || 0) - (a.testsPassed || 0)
      }
      if (sortBy === 'price') {
        return (b.price || 0) - (a.price || 0)
      }
      if (sortBy === 'sector') {
        return (a.sector || '').localeCompare(b.sector || '')
      }
      return 0
    })

    return result
  }, [stocks, sortBy, minGrade, sectorFilter, detailCache])

  const displayStocks = filteredStocks.slice(0, showCount)

  // Stats
  const stats = useMemo(() => {
    const gradeA = stocks.filter(s => s.grade === 'A').length
    const gradeB = stocks.filter(s => s.grade === 'B').length
    const gradeC = stocks.filter(s => s.grade === 'C').length
    const total = stocks.length
    return { gradeA, gradeB, gradeC, total }
  }, [stocks])

  const getTestResult = (ticker, testKey) => {
    const detail = detailCache[ticker]
    if (!detail?.valuationTests) return null
    return detail.valuationTests[testKey] || null
  }

  const handleStockClick = (ticker) => {
    navigate(`/stock/${ticker}`, { state: { fromScreener: true } })
  }

  if (loading) {
    return (
      <div className="screener">
        <div className="screener__loading">
          <div className="screener__loading-spinner" />
          Loading screener data…
        </div>
      </div>
    )
  }

  if (stocks.length === 0) {
    return (
      <div className="screener">
        <div className="screener__header">
          <div className="screener__title-group">
            <span className="screener__icon">🔬</span>
            <div>
              <h2 className="screener__title">Undervalued Screener</h2>
              <p className="screener__subtitle">Multi-test valuation analysis</p>
            </div>
          </div>
        </div>
        <div className="screener__empty">
          <div className="screener__empty-icon">📊</div>
          <p>No test data available yet. Run the pipeline to generate valuation tests.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="screener" id="undervalued-screener">
      {/* Header */}
      <div className="screener__header">
        <div className="screener__title-group">
          <span className="screener__icon">🔬</span>
          <div>
            <h2 className="screener__title">Undervalued Screener</h2>
            <p className="screener__subtitle">8 independent valuation tests · {stats.total} stocks analysed</p>
          </div>
        </div>

        <div className="screener__controls">
          {/* Sort */}
          <div className="screener__filter">
            <span>Sort:</span>
            <select value={sortBy} onChange={e => setSortBy(e.target.value)}>
              {SORT_OPTIONS.map(o => (
                <option key={o.key} value={o.key}>{o.label}</option>
              ))}
            </select>
          </div>

          {/* Min Grade */}
          <div className="screener__filter">
            <span>Min Grade:</span>
            <select value={minGrade} onChange={e => setMinGrade(e.target.value)}>
              <option value="all">All</option>
              <option value="A">A+</option>
              <option value="B">B+</option>
              <option value="C">C+</option>
            </select>
          </div>

          {/* Sector */}
          <div className="screener__filter">
            <span>Sector:</span>
            <select value={sectorFilter} onChange={e => setSectorFilter(e.target.value)}>
              <option value="all">All</option>
              {sectors.map(s => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="screener__stats">
        <div className="screener__stat">
          <span className="screener__stat-value" style={{ color: 'var(--green-400)' }}>{stats.gradeA}</span>
          <span className="screener__stat-label">Grade A</span>
        </div>
        <div className="screener__stat">
          <span className="screener__stat-value" style={{ color: '#5eead4' }}>{stats.gradeB}</span>
          <span className="screener__stat-label">Grade B</span>
        </div>
        <div className="screener__stat">
          <span className="screener__stat-value" style={{ color: 'var(--amber-400)' }}>{stats.gradeC}</span>
          <span className="screener__stat-label">Grade C</span>
        </div>
        <div className="screener__stat">
          <span className="screener__stat-value">{filteredStocks.length}</span>
          <span className="screener__stat-label">Showing</span>
        </div>
      </div>

      {/* Table Header — desktop only */}
      <div className="screener__table-header">
        <span>Stock</span>
        <div className="screener__th-tests">
          {TEST_KEYS.map(t => (
            <span key={t.key} className="screener__th-test">{t.short}</span>
          ))}
        </div>
        <span style={{ textAlign: 'center' }}>Grade</span>
      </div>

      {/* Stock Rows */}
      {displayStocks.map((stock, index) => {
        const grade = stock.grade || 'F'
        const detail = detailCache[stock.ticker]
        const tests = detail?.valuationTests || {}

        return (
          <div
            key={stock.ticker}
            className="screener__row"
            onClick={() => handleStockClick(stock.ticker)}
            style={{ animationDelay: `${index * 0.04}s` }}
          >
            {/* Stock Info */}
            <div className="screener__stock-info">
              <StockLogo
                ticker={stock.ticker}
                name={stock.name}
                domain={stock.domain}
                className="screener__stock-logo"
              />
              <div className="screener__stock-identity">
                <div className="screener__stock-ticker">{stock.ticker}</div>
                <div className="screener__stock-name">{stock.name}</div>
                <div className="screener__stock-meta">
                  <span className="screener__stock-price">
                    {exchange === 'ASX' ? 'A$' : '$'}{stock.price.toFixed(2)}
                  </span>
                  <span className="screener__stock-mcap">{stock.marketCap}</span>
                </div>
              </div>
            </div>

            {/* Test Indicators */}
            <div className="screener__tests">
              {TEST_KEYS.map(({ key, short }) => {
                const test = tests[key]
                const passed = test?.passed
                const indicatorClass = passed === true
                  ? 'screener__test-indicator--pass'
                  : passed === false
                    ? 'screener__test-indicator--fail'
                    : 'screener__test-indicator--na'

                return (
                  <div key={key} className="screener__test">
                    <div className={`screener__test-indicator ${indicatorClass}`}>
                      {passed === true ? '✓' : passed === false ? '✗' : '—'}
                    </div>
                    <span className="screener__test-label">{short}</span>
                    {test && (
                      <div className="screener__test-tooltip">
                        <strong>{test.name}</strong><br />
                        {test.label}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>

            {/* Grade */}
            <div className="screener__grade-section">
              <div className={`screener__grade screener__grade--${grade}`}>
                {grade}
              </div>
              <div className="screener__tests-count">
                {stock.testsPassed || 0}/8
              </div>
              <div className="screener__grade-label">
                {GRADE_LABELS[grade]}
              </div>
            </div>
          </div>
        )
      })}

      {/* Show More */}
      {displayStocks.length < filteredStocks.length && (
        <button
          className="screener__show-more"
          onClick={() => setShowCount(prev => prev + 20)}
        >
          Show more ({filteredStocks.length - displayStocks.length} remaining) →
        </button>
      )}
    </div>
  )
}
