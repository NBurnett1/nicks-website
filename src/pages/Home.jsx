import { useState, useEffect } from 'react'
import LiveTicker from '../components/LiveTicker'
import WeeklyPicks from '../components/WeeklyPicks'
import WeekArchive from '../components/WeekArchive'
import AlertsFeed from '../components/AlertsFeed'
import UndervaluedScreener from '../components/UndervaluedScreener'
import Disclaimer from '../components/Disclaimer'
import Footer from '../components/Footer'
import './Home.css'

export default function Home() {
  const [meta, setMeta] = useState(null)
  const [email, setEmail] = useState('')
  const [subscribed, setSubscribed] = useState(false)

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

  const handleSubscribe = (e) => {
    e.preventDefault()
    if (email.includes('@')) {
      // Store in localStorage for now — can be upgraded to a real backend later
      const subs = JSON.parse(localStorage.getItem('nkb_subscribers') || '[]')
      if (!subs.includes(email)) {
        subs.push(email)
        localStorage.setItem('nkb_subscribers', JSON.stringify(subs))
      }
      setSubscribed(true)
      setEmail('')
    }
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

      {/* Market Intelligence — alerts & news */}
      <div className="container">
        <AlertsFeed />
      </div>

      {/* Week Archive — track record */}
      <div className="container">
        <WeekArchive />
      </div>

      {/* Subscribe CTA */}
      <section className="home__subscribe" id="subscribe">
        <div className="container">
          <div className="home__subscribe-card">
            <div className="home__subscribe-content">
              <span className="home__subscribe-icon">🔔</span>
              <div>
                <h2 className="home__subscribe-title">Get Weekly Picks in Your Inbox</h2>
                <p className="home__subscribe-text">
                  New picks drop every Monday at 10am AEST. Join to get notified + stop-loss alerts.
                </p>
              </div>
            </div>
            {subscribed ? (
              <div className="home__subscribe-success">
                <span className="home__subscribe-success-icon">✓</span>
                You're in! Check your inbox on Monday.
              </div>
            ) : (
              <form className="home__subscribe-form" onSubmit={handleSubscribe}>
                <input
                  type="email"
                  placeholder="your@email.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="home__subscribe-input"
                  required
                />
                <button type="submit" className="home__subscribe-btn">
                  Subscribe
                </button>
              </form>
            )}
          </div>
        </div>
      </section>

      {/* Undervalued Screener — full research tool */}
      <div className="container">
        <UndervaluedScreener exchange="ASX" />
      </div>

      <Disclaimer />
      <Footer />
    </div>
  )
}
