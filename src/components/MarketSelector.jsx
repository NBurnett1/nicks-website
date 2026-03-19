import './MarketSelector.css'

export default function MarketSelector({ onSelect }) {
  return (
    <div className="market-selector-gate">
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
          {/* ASX - Active */}
          <button 
            className="market-card market-card--active"
            onClick={() => onSelect('ASX')}
          >
            <div className="market-card__icon-wrapper">🇦🇺</div>
            <h3 className="market-card__title">ASX</h3>
            <p className="market-card__desc">Australian Securities Exchange</p>
            <div className="market-card__status">LIVE</div>
          </button>

          {/* NYSE - Coming Soon */}
          <button 
            className="market-card market-card--disabled"
            disabled
          >
            <div className="market-card__icon-wrapper">🇺🇸</div>
            <h3 className="market-card__title">NYSE</h3>
            <p className="market-card__desc">New York Stock Exchange</p>
            <div className="market-card__badge">Coming Soon</div>
          </button>

          {/* NASDAQ - Coming Soon */}
          <button 
            className="market-card market-card--disabled"
            disabled
          >
            <div className="market-card__icon-wrapper">🇺🇸</div>
            <h3 className="market-card__title">NASDAQ</h3>
            <p className="market-card__desc">National Association of Securities Dealers</p>
            <div className="market-card__badge">Coming Soon</div>
          </button>
        </div>
      </div>
    </div>
  )
}
