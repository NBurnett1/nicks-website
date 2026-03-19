import { useState } from 'react';
import './StockLogo.css';

// Generate a deterministic vibrant gradient based on the ticker
const generateGradient = (str) => {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
  }
  const hue1 = Math.abs(hash % 360);
  const hue2 = Math.abs((hash + 50) % 360);
  return `linear-gradient(135deg, hsl(${hue1}, 85%, 60%), hsl(${hue2}, 90%, 50%))`;
};

export default function StockLogo({ ticker, name, domain }) {
  const [imageError, setImageError] = useState(false);
  
  const cleanTicker = ticker.replace('.AX', '');
  
  let logoUrl = '';
  if (domain && domain.length > 3) {
    logoUrl = `https://logo.clearbit.com/${domain}`;
  } else {
    // Best effort domain guess as a final fallback
    const domainGuess = name.split(' ')[0].toLowerCase().replace(/[^a-z0-9]/g, '') + '.com';
    logoUrl = `https://logo.clearbit.com/${domainGuess}`;
  }

  return (
    <div className="stock-logo" style={{ background: generateGradient(ticker) }}>
      {!imageError ? (
        <img 
          src={logoUrl} 
          alt={`${ticker} logo`} 
          onError={() => setImageError(true)}
          className="stock-logo__img"
        />
      ) : (
        <span className="stock-logo__text">{cleanTicker.slice(0, 2)}</span>
      )}
    </div>
  );
}
