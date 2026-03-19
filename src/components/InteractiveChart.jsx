import { useState, useRef } from 'react';
import './InteractiveChart.css';

export default function InteractiveChart({ data, isOvervalued }) {
  const [hoverIndex, setHoverIndex] = useState(null);
  const containerRef = useRef(null);

  if (!data || data.length < 2) return null;

  // normalize data
  const pointsData = data.map(d => typeof d === 'object' ? d : { date: '', price: d });
  const prices = pointsData.map(d => d.price);
  
  const min = Math.min(...prices);
  const max = Math.max(...prices);
  const range = max - min || 1;
  const height = 300;
  const width = 800; // SVG viewBox dimensions

  const getX = (i) => (i / (prices.length - 1)) * width;
  const getY = (val) => height - ((val - min) / range) * (height * 0.8) - (height * 0.1);

  const points = prices.map((val, i) => `${getX(i)},${getY(val)}`).join(' ');
  const color = isOvervalued ? 'var(--red-400)' : 'var(--green-400)';
  const glowColor = isOvervalued ? 'rgba(248, 113, 113, 0.2)' : 'rgba(74, 222, 128, 0.2)';

  const handleMouseMove = (e) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const percentage = x / rect.width;
    let index = Math.round(percentage * (prices.length - 1));
    index = Math.max(0, Math.min(prices.length - 1, index));
    setHoverIndex(index);
  };

  const handleMouseLeave = () => {
    setHoverIndex(null);
  };

  return (
    <div 
      className="interactive-chart" 
      ref={containerRef}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
    >
      <div className="interactive-chart__header">
        <h3 className="interactive-chart__title">1-Year Price History</h3>
        {hoverIndex !== null && pointsData[hoverIndex]?.date && (
          <div className="interactive-chart__tooltip">
            <span className="interactive-chart__date">{pointsData[hoverIndex].date}</span>
            <span className="interactive-chart__price">${prices[hoverIndex].toFixed(2)}</span>
          </div>
        )}
      </div>
      
      <div className="interactive-chart__svg-container">
        <svg viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
          <defs>
            <linearGradient id={`gradient-fill-${isOvervalued ? 'red' : 'green'}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={glowColor} />
              <stop offset="100%" stopColor="transparent" />
            </linearGradient>
          </defs>
          
          <polygon
            fill={`url(#gradient-fill-${isOvervalued ? 'red' : 'green'})`}
            points={`0,${height} ${points} ${width},${height}`}
          />
          
          <polyline
            fill="none"
            stroke={color}
            strokeWidth="3"
            strokeLinecap="round"
            strokeLinejoin="round"
            points={points}
          />

          {hoverIndex !== null && (
            <>
              <line 
                x1={getX(hoverIndex)} 
                y1="0" 
                x2={getX(hoverIndex)} 
                y2={height} 
                stroke="rgba(255,255,255,0.2)" 
                strokeWidth="2"
                strokeDasharray="4 4"
              />
              <circle 
                cx={getX(hoverIndex)} 
                cy={getY(prices[hoverIndex])} 
                r="6" 
                fill={color} 
                stroke="var(--bg-card)" 
                strokeWidth="2" 
              />
            </>
          )}
        </svg>
      </div>
    </div>
  );
}
