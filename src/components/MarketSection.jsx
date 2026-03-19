import StockCard from './StockCard'
import './MarketSection.css'

export default function MarketSection({ title, subtitle, stocks, type, icon, exchange }) {
  return (
    <section className={`market-section market-section--${type}`} id={`${type}-stocks`}>
      <div className="market-section__header">
        <div className="market-section__icon-wrapper">
          <span className={`market-section__icon market-section__icon--${type}`}>{icon}</span>
        </div>
        <div>
          <h2 className="market-section__title">{title}</h2>
          <p className="market-section__subtitle">{subtitle}</p>
        </div>
      </div>

      <div className="market-section__list stagger-children">
        {stocks.map((stock, i) => (
          <StockCard stock={stock} type={type} index={i} key={stock.ticker} exchange={exchange} />
        ))}
        {stocks.length === 0 && (
          <p className="market-section__empty">No stocks match your search.</p>
        )}
      </div>
    </section>
  )
}

