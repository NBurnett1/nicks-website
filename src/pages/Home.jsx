import { useState, useEffect } from 'react'
import MarketSelector from '../components/MarketSelector'
import MarketSection from '../components/MarketSection'
import Disclaimer from '../components/Disclaimer'
import Footer from '../components/Footer'
import './Home.css'

export default function Home() {
  const [selectedExchange, setSelectedExchange] = useState(null)
  const [data, setData] = useState(null)
  const [meta, setMeta] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      fetch('/data/summary.json').then(res => res.json()),
      fetch('/data/meta.json').then(res => res.json())
    ])
      .then(([summaryData, metaData]) => {
        setData(summaryData)
        setMeta(metaData)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [])

  const formatDate = (dateStr) => {
    if (!dateStr) return ''
    const d = new Date(dateStr)
    return d.toLocaleDateString('en-AU', { day: 'numeric', month: 'short', year: 'numeric' })
  }

  if (!selectedExchange) {
    return <MarketSelector onSelect={setSelectedExchange} />
  }

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="loading-screen__spinner" />
        <p className="loading-screen__text">Loading market data...</p>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="loading-screen">
        <p className="loading-screen__text">Unable to load market data. Please try again later.</p>
      </div>
    )
  }

  return (
    <div className="home" id="home-page">
      <header className="home__header">
        <div className="container home__header-container">
          <div className="home__brand">
            <span style={{ display: 'inline-block', width: '8px', height: '8px', background: 'var(--blue-400)', borderRadius: '50%', boxShadow: '0 0 10px var(--blue-400)' }} />
            ASX AI Valuations
          </div>
          {meta && (
            <div className="home__header-meta">
              Updated {formatDate(meta.lastUpdated)} <span className="hide-mobile">• {meta.stocksAnalyzed} stocks analyzed</span>
            </div>
          )}
        </div>
      </header>

      <div id="market-overview">
        <MarketSection
          title="Top 10 Undervalued"
          subtitle="Stocks trading below their estimated intrinsic value"
          stocks={data.undervalued}
          type="undervalued"
          icon="📈"
        />

        <div className="home__divider">
          <div className="container">
            <div className="home__divider-line" />
          </div>
        </div>

        <MarketSection
          title="Top 10 Overvalued"
          subtitle="Stocks trading above their estimated intrinsic value"
          stocks={data.overvalued}
          type="overvalued"
          icon="📉"
        />
      </div>

      <Disclaimer />
      <Footer />
    </div>
  )
}
