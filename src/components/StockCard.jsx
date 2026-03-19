import { useNavigate } from 'react-router-dom'
import StockLogo from './StockLogo'
import './StockCard.css'

export default function StockCard({ stock, type, index }) {
  const navigate = useNavigate()
  const isOvervalued = type === 'overvalued'
  const scoreAbs = Math.abs(stock.valuationScore).toFixed(1)

  const handleClick = () => {
    navigate(`/stock/${stock.ticker}`)
  }

  return (
    <div
      className={`stock-card glass-card stock-card--${type}`}
      onClick={handleClick}
      style={{ animationDelay: `${index * 0.05}s` }}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && handleClick()}
      id={`stock-card-${stock.ticker}`}
    >
      {/* Glow border */}
      <div className={`stock-card__glow stock-card__glow--${type}`} />

      <div className="stock-card__header">
        <div className="stock-card__brand-group">
          <StockLogo ticker={stock.ticker} name={stock.name} />
          <div>
            <div className="stock-card__ticker-group">
              <span className="stock-card__ticker">{stock.ticker}</span>
              <span className={`badge badge--${isOvervalued ? 'red' : 'green'}`}>
                {isOvervalued ? '▲' : '▼'} {scoreAbs}%
              </span>
            </div>
            <span className="stock-card__sector">{stock.sector}</span>
          </div>
        </div>
      </div>

      <div className="stock-card__name">{stock.name}</div>

      <div className="stock-card__price-row">
        <span className="stock-card__price">${stock.price.toFixed(2)}</span>
        <span className="stock-card__mcap">{stock.marketCap}</span>
      </div>

      <div className="stock-card__metrics">
        <div className="stock-card__metric">
          <span className="stock-card__metric-label">P/E</span>
          <span className="stock-card__metric-value">{stock.metrics.pe?.toFixed(1) ?? '—'}</span>
        </div>
        <div className="stock-card__metric">
          <span className="stock-card__metric-label">P/B</span>
          <span className="stock-card__metric-value">{stock.metrics.pb?.toFixed(1) ?? '—'}</span>
        </div>
        <div className="stock-card__metric">
          <span className="stock-card__metric-label">EV/EBITDA</span>
          <span className="stock-card__metric-value">{stock.metrics.evEbitda?.toFixed(1) ?? '—'}</span>
        </div>
        <div className="stock-card__metric">
          <span className="stock-card__metric-label">FCF Yield</span>
          <span className="stock-card__metric-value">{stock.metrics.fcfYield != null ? `${stock.metrics.fcfYield.toFixed(1)}%` : '—'}</span>
        </div>
      </div>

      <div className="stock-card__footer">
        <span className="stock-card__cta">View Analysis →</span>
      </div>
    </div>
  )
}
