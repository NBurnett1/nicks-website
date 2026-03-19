import { useState, useEffect } from 'react'
import MarketSelector from '../components/MarketSelector'
import MarketSection from '../components/MarketSection'
import SearchBar from '../components/SearchBar'
import Disclaimer from '../components/Disclaimer'
import Footer from '../components/Footer'
import './Home.css'

export default function Home() {
  const [selectedExchange, setSelectedExchange] = useState(null)
  const [data, setData] = useState(null)
  const [meta, setMeta] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!selectedExchange) return;
    setLoading(true);
    const exchangeKey = selectedExchange.toLowerCase();
    Promise.all([
      fetch(`/data/${exchangeKey}_summary.json`).then(res => res.json()),
      fetch(`/data/${exchangeKey}_meta.json`).then(res => res.json())
    ])
      .then(([summaryData, metaData]) => {
        setData(summaryData)
        setMeta(metaData)
        setLoading(false)
      })
      .catch(() => {
        setData(null)
        setLoading(false)
      })
  }, [selectedExchange])

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
      <div className="home__bg-orbs">
        <div className="home__bg-orb home__bg-orb--1" />
        <div className="home__bg-orb home__bg-orb--2" />
        <div className="home__bg-orb home__bg-orb--3" />
      </div>

      <header className="home__header">
        <div className="container home__header-container">
          <div className="home__brand">
            <img src="/logo.png" alt="N Valuations Logo" className="home__logo-img" />
            <span className="home__brand-text">N Valuations</span>
          </div>
          {meta && (
            <div className="home__header-meta">
              Updated {formatDate(meta.lastUpdated)} <span className="hide-mobile">• {meta.stocksAnalyzed} stocks analyzed</span>
            </div>
          )}
        </div>
      </header>

      {/* Hero Section */}
      {selectedExchange && (
        <div className="home__hero animate-fade-in-up">
          <div className="container">
            <h1 className="home__hero-title">
              Institutional-Grade <br/>
              <span className="home__hero-highlight">Equity Research.</span>
            </h1>
            <p className="home__hero-subtitle">
              Discover the most profoundly mispriced stocks across global markets with AI-powered financial models.
            </p>
          </div>
        </div>
      )}

      {/* Search Filter */}
      {selectedExchange && (
        <div className="container" style={{ position: 'relative', zIndex: 10 }}>
          <SearchBar onSearch={setSearchQuery} />
        </div>
      )}

      {/* Market Gates */}
      <div id="market-overview" className="container home__split-grid">
        <MarketSection
          title="Undervalued"
          subtitle="Companies trading at a massive systemic discount"
          stocks={data.undervalued.filter(s => s.ticker.toLowerCase().includes(searchQuery.toLowerCase()) || s.name.toLowerCase().includes(searchQuery.toLowerCase()))}
          type="undervalued"
          icon="📈"
        />

        <MarketSection
          title="Overvalued"
          subtitle="Companies trading at a severe systemic premium"
          stocks={data.overvalued.filter(s => s.ticker.toLowerCase().includes(searchQuery.toLowerCase()) || s.name.toLowerCase().includes(searchQuery.toLowerCase()))}
          type="overvalued"
          icon="📉"
        />
      </div>

      <Disclaimer />
      <Footer />
    </div>
  )
}
