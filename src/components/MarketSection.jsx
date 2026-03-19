import StockCard from './StockCard'
import './MarketSection.css'

export default function MarketSection({ title, subtitle, stocks, type, icon }) {
  return (
    <section className={`market-section market-section--${type}`} id={`${type}-stocks`}>
      <div className="container">
        <div className="market-section__header">
          <div className="market-section__icon-wrapper">
            <span className={`market-section__icon market-section__icon--${type}`}>{icon}</span>
          </div>
          <div>
            <h2 className="market-section__title">{title}</h2>
            <p className="market-section__subtitle">{subtitle}</p>
          </div>
        </div>
      </div>

      <div className="market-section__carousel-wrapper">
        <div className="market-section__carousel stagger-children">
          {stocks.map((stock, i) => (
            <div className="market-section__card-wrapper" key={stock.ticker}>
              <StockCard stock={stock} type={type} index={i} />
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
