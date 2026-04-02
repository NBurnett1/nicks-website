import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import './LiveTicker.css'

export default function LiveTicker() {
  const [stocks, setStocks] = useState([])
  const scrollRef = useRef(null)
  const navigate = useNavigate()

  useEffect(() => {
    fetch('/data/asx_index.json')
      .then(res => res.ok ? res.json() : null)
      .then(data => {
        if (!data) return
        const all = [...(data.undervalued || []), ...(data.overvalued || [])]
        // Sort by absolute valuation score for interesting movements
        const sorted = all
          .filter(s => s.price && s.price > 0)
          .sort((a, b) => Math.abs(b.valuationScore) - Math.abs(a.valuationScore))
          .slice(0, 40)
        setStocks(sorted)
      })
      .catch(() => {})
  }, [])

  if (stocks.length === 0) return null

  // Duplicate the list for seamless scrolling
  const tickerItems = [...stocks, ...stocks]

  return (
    <div className="live-ticker" id="live-ticker">
      <div className="live-ticker__label">
        <span className="live-ticker__dot" />
        ASX
      </div>
      <div className="live-ticker__track" ref={scrollRef}>
        <div className="live-ticker__scroll">
          {tickerItems.map((stock, i) => {
            const isUndervalued = stock.valuationScore < 0
            return (
              <button
                key={`${stock.ticker}-${i}`}
                className={`live-ticker__item ${isUndervalued ? 'live-ticker__item--up' : 'live-ticker__item--down'}`}
                onClick={() => navigate(`/stock/${stock.ticker}`)}
              >
                <span className="live-ticker__ticker">{stock.ticker}</span>
                <span className="live-ticker__price">A${stock.price.toFixed(2)}</span>
                <span className={`live-ticker__score ${isUndervalued ? 'live-ticker__score--green' : 'live-ticker__score--red'}`}>
                  {stock.valuationScore > 0 ? '+' : ''}{stock.valuationScore.toFixed(0)}
                </span>
              </button>
            )
          })}
        </div>
      </div>
    </div>
  )
}
