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

  const renderSparkline = (data) => {
    if (!data || data.length < 2) return null;
    const pointsData = data.map(d => typeof d === 'object' ? d.price : d);
    const min = Math.min(...pointsData);
    const max = Math.max(...pointsData);
    const range = max - min || 1;
    const height = 24;
    const width = 60;
    
    const points = pointsData.map((val, i) => {
      const x = (i / (pointsData.length - 1)) * width;
      const y = height - ((val - min) / range) * height;
      return `${x},${y}`;
    }).join(' ');

    const color = isOvervalued ? 'var(--red-400)' : 'var(--green-400)';

    return (
      <svg className="stock-list__sparkline" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
        <polyline fill="none" stroke={color} strokeWidth="1.5" points={points} />
      </svg>
    );
  };

  return (
    <div
      className={`stock-list-item stock-list-item--${type}`}
      onClick={handleClick}
      style={{ animationDelay: `${index * 0.03}s` }}
    >
      <div className="stock-list__left">
        <StockLogo ticker={stock.ticker} name={stock.name} domain={stock.domain} className="stock-list__logo" />
        <div className="stock-list__identity">
          <span className="stock-list__ticker">{stock.ticker}</span>
          <span className="stock-list__mcap">{stock.marketCap}</span>
        </div>
      </div>

      <div className="stock-list__center">
        {renderSparkline(stock.chartData)}
      </div>

      <div className="stock-list__right">
        <span className="stock-list__price">${stock.price.toFixed(2)}</span>
        <span className={`badge badge--${isOvervalued ? 'red' : 'green'}`}>
          {isOvervalued ? 'Premium' : 'Discount'} {scoreAbs}%
        </span>
      </div>
    </div>
  )
}
