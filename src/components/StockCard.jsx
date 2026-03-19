import { useNavigate } from 'react-router-dom'
import StockLogo from './StockLogo'
import './StockCard.css'

export default function StockCard({ stock, type, index }) {
  const navigate = useNavigate()
  const isOvervalued = type === 'overvalued'
  const scoreAbs = Math.abs(stock.valuationScore).toFixed(1)

  const handleClick = () => {
    navigate(`/stock/${stock.ticker}`, { state: { chartData: stock.chartData, isOvervalued } })
  }

  const renderSparkline = (data, isOvervalued) => {
    if (!data || data.length < 2) return null;
    const min = Math.min(...data);
    const max = Math.max(...data);
    const range = max - min || 1;
    const height = 40;
    const width = 120;
    
    // Smooth polyline coordinates
    const points = data.map((val, i) => {
      const x = (i / (data.length - 1)) * width;
      const y = height - ((val - min) / range) * height;
      // Add slight padding to prevent clipping at the top/bottom edges
      return `${x},${y * 0.8 + height * 0.1}`; 
    }).join(' ');

    const color = isOvervalued ? 'var(--red-400)' : 'var(--green-400)';
    const strokeWidth = 2;

    return (
      <svg className="stock-card__sparkline" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
        <polyline
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeLinejoin="round"
          points={points}
        />
      </svg>
    );
  };

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
      <div className={`stock-card__glow stock-card__glow--${type}`} />

      <div className="stock-card__header">
        <div className="stock-card__brand-group">
          <StockLogo ticker={stock.ticker} name={stock.name} domain={stock.domain} />
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
        <div className="stock-card__price-info">
          <span className="stock-card__price">${stock.price.toFixed(2)}</span>
          <span className="stock-card__mcap">{stock.marketCap}</span>
        </div>
        {renderSparkline(stock.chartData, isOvervalued)}
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
