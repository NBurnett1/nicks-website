import { useState, useEffect } from 'react'
import LiveTicker from '../components/LiveTicker'
import WeeklyPicks from '../components/WeeklyPicks'
import WeekArchive from '../components/WeekArchive'
import UndervaluedScreener from '../components/UndervaluedScreener'
import Disclaimer from '../components/Disclaimer'
import Footer from '../components/Footer'
import './Home.css'

export default function Home() {
  const [meta, setMeta] = useState(null)

  useEffect(() => {
    fetch('/data/asx_meta.json')
      .then(res => res.ok ? res.json() : null)
      .then(setMeta)
      .catch(() => {})
  }, [])

  const formatDate = (dateStr) => {
    if (!dateStr) return ''
    const d = new Date(dateStr)
    return d.toLocaleDateString('en-AU', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
  }

  return (
    <div className="home" id="home-page">
      {/* Background effects */}
      <div className="home__bg-orbs">
        <div className="home__bg-orb home__bg-orb--1" />
        <div className="home__bg-orb home__bg-orb--2" />
      </div>

      {/* Live Ticker Bar */}
      <LiveTicker />

      {/* Header */}
      <header className="home__header">
        <div className="container home__header-container">
          <div className="home__brand">
            <img src="/logo.png" alt="Nick Knows Best" className="home__logo-img" />
            <span className="home__brand-text">Nick Knows Best</span>
          </div>
          {meta && (
            <div className="home__header-meta">
              Updated {formatDate(meta.lastUpdated)}
              <span className="hide-mobile"> · {meta.stocksAnalyzed || 0} stocks tracked</span>
            </div>
          )}
        </div>
      </header>

      {/* Hero */}
      <section className="home__hero animate-fade-in-up">
        <div className="container">
          <div className="home__hero-badge">
            <span className="home__hero-badge-dot" />
            ASX Weekly Picks
          </div>
          <h1 className="home__hero-title">
            Nick's Weekly<br />
            <span className="home__hero-highlight">ASX Picks.</span>
          </h1>
          <p className="home__hero-subtitle">
            5 curated stocks every Monday. 4 high-conviction value plays + 1 speculative moonshot.
            Track the performance week by week.
          </p>
        </div>
      </section>

      {/* Weekly Picks — the main event */}
      <div className="container">
        <WeeklyPicks exchange="ASX" />
      </div>

      {/* Week Archive — track record */}
      <div className="container">
        <WeekArchive />
      </div>

      {/* Undervalued Screener — full research tool */}
      <div className="container">
        <UndervaluedScreener exchange="ASX" />
      </div>

      <Disclaimer />
      <Footer />
    </div>
  )
}
