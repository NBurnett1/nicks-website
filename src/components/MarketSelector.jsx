import { useState } from 'react'
import './MarketSelector.css'

export default function MarketSelector({ onSelect }) {
  const [exitingMarket, setExitingMarket] = useState(null)

  const handleSelect = (market) => {
    setExitingMarket(market)
    setTimeout(() => {
      onSelect(market)
    }, 600)
  }

  const handleMouseMove = (e) => {
    const card = e.currentTarget
    const rect = card.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top
    
    card.style.setProperty('--mouse-x', `${x}px`)
    card.style.setProperty('--mouse-y', `${y}px`)
    
    const centerX = rect.width / 2
    const centerY = rect.height / 2
    const rotateX = ((y - centerY) / centerY) * -8 
    const rotateY = ((x - centerX) / centerX) * 8
    
    card.style.setProperty('--rotateX', `${rotateX}deg`)
    card.style.setProperty('--rotateY', `${rotateY}deg`)
  }

  const handleMouseLeave = (e) => {
    const card = e.currentTarget
    card.style.setProperty('--rotateX', '0deg')
    card.style.setProperty('--rotateY', '0deg')
  }

  const markets = [
    { id: 'ASX', name: 'ASX', desc: 'Australian Securities Exchange', flag: '🇦🇺' },
    { id: 'NYSE', name: 'NYSE', desc: 'New York Stock Exchange', flag: '🇺🇸' },
    { id: 'NASDAQ', name: 'NASDAQ', desc: 'National Association of Securities Dealers', flag: '🇺🇸' }
  ]

  return (
    <div className={`market-selector-gate ${exitingMarket ? 'market-selector-gate--exiting' : ''}`}>
      <div className="market-selector__bg-orb market-selector__bg-orb--1" />
      <div className="market-selector__bg-orb market-selector__bg-orb--2" />
      
      <div className="container market-selector__content">
        <h1 className="market-selector__title animate-fade-in-up">
          Select <span className="text-gradient">Market</span>
        </h1>
        <p className="market-selector__subtitle animate-fade-in-up stagger-1">
          Choose an exchange to view AI-powered valuations and equity research.
        </p>

        <div className="market-selector__grid animate-fade-in-up stagger-2">
          {markets.map((market) => (
            <button 
              key={market.id}
              className={`market-card market-card--active ${exitingMarket && exitingMarket !== market.id ? 'market-card--fading' : ''} ${exitingMarket === market.id ? 'market-card--selected' : ''}`}
              onClick={() => handleSelect(market.id)}
              onMouseMove={handleMouseMove}
              onMouseLeave={handleMouseLeave}
            >
              <div className="market-card__icon-wrapper">{market.flag}</div>
              <h3 className="market-card__title">{market.name}</h3>
              <p className="market-card__desc">{market.desc}</p>
              <div className="market-card__status">LIVE</div>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
