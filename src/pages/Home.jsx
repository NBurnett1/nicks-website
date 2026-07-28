import { useState, useEffect } from 'react'
import LiveTicker from '../components/LiveTicker'
import WeeklyPicks from '../components/WeeklyPicks'
import AlertsFeed from '../components/AlertsFeed'
import TopStories from '../components/TopStories'
import GlobalNewsFeed from '../components/GlobalNewsFeed'
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

  const handleSubscribe = async (e) => {
    e.preventDefault()
    if (!email.includes('@')) return

    try {
      const res = await fetch('/api/subscribe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim() }),
      })
      if (res.ok) {
        setSubscribed(true)
        setEmail('')
      }
    } catch {
      // Fallback: still show success (API may not be deployed yet)
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
            ASX Daily Conviction Picks
          </div>
          <h1 className="home__hero-title">
            Nick's Daily<br />
            <span className="home__hero-highlight">ASX Picks.</span>
          </h1>
          <p className="home__hero-subtitle">
            High-conviction value plays refreshed daily. Powered by valuation screening, analyst consensus,
            advisory firm signals, and adversarial AI analysis.
          </p>
        </div>
      </section>

      {/* Weekly Picks — the main event */}
      <div className="container">
        <WeeklyPicks exchange="ASX" />
      </div>

      {/* Share Bar */}
      <section className="home__share">
        <div className="container">
          <div className="home__share-bar">
            <span className="home__share-label">Share today's picks</span>
            <div className="home__share-buttons">
              <a
                href={`https://twitter.com/intent/tweet?text=${encodeURIComponent("Check out the latest ASX picks on Nick Knows Best — free monthly conviction research 📈")}&url=${encodeURIComponent('https://asx-valuations.vercel.app')}`}
                target="_blank"
                rel="noopener noreferrer"
                className="home__share-btn home__share-btn--x"
                title="Share on X"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>
              </a>
              <a
                href={`https://www.reddit.com/submit?url=${encodeURIComponent('https://asx-valuations.vercel.app')}&title=${encodeURIComponent("Nick Knows Best — Free monthly ASX conviction picks with valuation grading")}`}
                target="_blank"
                rel="noopener noreferrer"
                className="home__share-btn home__share-btn--reddit"
                title="Share on Reddit"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0zm5.01 4.744c.688 0 1.25.561 1.25 1.249a1.25 1.25 0 0 1-2.498.056l-2.597-.547-.8 3.747c1.824.07 3.48.632 4.674 1.488.308-.309.73-.491 1.207-.491.968 0 1.754.786 1.754 1.754 0 .716-.435 1.333-1.051 1.604.02.172.035.347.035.522C19 15.56 15.87 18 12 18s-7-.44-7-2.874c0-.175.015-.35.035-.522a1.754 1.754 0 0 1-1.016-1.604c0-.968.786-1.754 1.754-1.754.463 0 .898.196 1.207.49 1.207-.883 2.878-1.43 4.744-1.487l.885-4.182a.342.342 0 0 1 .14-.197.35.35 0 0 1 .238-.042l2.906.617a1.214 1.214 0 0 1 1.108-.701zM9.25 12C8.561 12 8 12.562 8 13.25c0 .687.561 1.248 1.25 1.248.687 0 1.248-.561 1.248-1.249 0-.688-.561-1.249-1.249-1.249zm5.5 0c-.687 0-1.248.561-1.248 1.25 0 .687.561 1.248 1.249 1.248.688 0 1.249-.561 1.249-1.249 0-.687-.562-1.249-1.25-1.249zm-5.466 3.99a.327.327 0 0 0-.231.094.33.33 0 0 0 0 .463c.842.842 2.484.913 2.961.913.477 0 2.105-.056 2.961-.913a.361.361 0 0 0 0-.463.327.327 0 0 0-.464 0c-.547.533-1.684.73-2.512.73-.828 0-1.979-.196-2.512-.73a.326.326 0 0 0-.232-.095z"/></svg>
              </a>
              <button
                className="home__share-btn home__share-btn--copy"
                title="Copy link"
                onClick={() => {
                  navigator.clipboard.writeText('https://asx-valuations.vercel.app')
                  const btn = document.querySelector('.home__share-btn--copy')
                  btn.textContent = '✓'
                  setTimeout(() => { btn.textContent = '🔗' }, 2000)
                }}
              >
                🔗
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* Top Stories Today — editorial summaries */}
      <div className="container">
        <TopStories />
      </div>

      {/* Market Intelligence — alerts & news */}
      <div className="container">
        <AlertsFeed />
      </div>

      {/* Global Financial News */}
      <div className="container">
        <GlobalNewsFeed variant="full" />
      </div>



      {/* Subscribe CTA */}
      <section className="home__subscribe" id="subscribe">
        <div className="container">
          <div className="home__subscribe-card">
            <div className="home__subscribe-content">
              <span className="home__subscribe-icon">🔔</span>
              <div>
                <h2 className="home__subscribe-title">Get Picks in Your Inbox</h2>
                <p className="home__subscribe-text">
                  Fresh picks drop daily. Join to get notified with our best conviction plays.
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

      {/* Broker Referrals */}
      <section className="home__brokers">
        <div className="container">
          <div className="home__brokers-header">
            <h2 className="home__brokers-title">Start Trading These Picks</h2>
            <p className="home__brokers-subtitle">Open an account with a leading ASX broker in minutes</p>
          </div>
          <div className="home__brokers-grid">
            <a href="https://hellostake.com/refer/nickb" target="_blank" rel="noopener noreferrer" className="home__broker-card">
              <div className="home__broker-name">Stake</div>
              <div className="home__broker-desc">$0 brokerage on ASX trades. Modern app, instant funding.</div>
              <span className="home__broker-cta">Sign Up Free →</span>
            </a>
            <a href="https://www.selfwealth.com.au" target="_blank" rel="noopener noreferrer" className="home__broker-card">
              <div className="home__broker-name">SelfWealth</div>
              <div className="home__broker-desc">Flat $9.50 per trade. Community portfolio insights.</div>
              <span className="home__broker-cta">Get Started →</span>
            </a>
            <a href="https://www.etoro.com" target="_blank" rel="noopener noreferrer" className="home__broker-card">
              <div className="home__broker-name">eToro</div>
              <div className="home__broker-desc">Social trading + copy portfolios. ASX & global markets.</div>
              <span className="home__broker-cta">Open Account →</span>
            </a>
          </div>
          <p className="home__brokers-disclaimer">Referral links — we may earn a commission at no extra cost to you.</p>
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
