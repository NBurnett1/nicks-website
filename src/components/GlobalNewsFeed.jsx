import { useState, useEffect, useCallback } from 'react'
import './GlobalNewsFeed.css'

/**
 * GlobalNewsFeed — Curated financial & economic news aggregator.
 *
 * Fetches real-time headlines from multiple RSS sources via rss2json API (free tier).
 * Falls back to curated direct links to top financial news outlets.
 *
 * Props:
 *   variant: 'full' | 'compact' | 'sidebar' — controls layout and article count
 *   maxArticles: number — override max articles shown (default based on variant)
 *   className: string — additional CSS classes
 */

const NEWS_SOURCES = [
  {
    name: 'Reuters',
    icon: '🌐',
    category: 'Markets',
    rss: 'https://news.google.com/rss/search?q=global+financial+markets+economy&hl=en-AU&gl=AU&ceid=AU:en',
    directUrl: 'https://www.reuters.com/markets/',
    color: '#ff8c00',
  },
  {
    name: 'CNBC',
    icon: '📺',
    category: 'Economy',
    rss: 'https://news.google.com/rss/search?q=economy+stocks+interest+rates&hl=en-US&gl=US&ceid=US:en',
    directUrl: 'https://www.cnbc.com/world-markets/',
    color: '#005594',
  },
  {
    name: 'AFR',
    icon: '🇦🇺',
    category: 'ASX',
    rss: 'https://news.google.com/rss/search?q=ASX+Australian+stock+market+economy&hl=en-AU&gl=AU&ceid=AU:en',
    directUrl: 'https://www.afr.com/markets',
    color: '#1a4480',
  },
]

const CURATED_LINKS = [
  {
    title: 'Reuters — Global Markets',
    url: 'https://www.reuters.com/markets/',
    source: 'Reuters',
    icon: '🌐',
    category: 'Markets',
    description: 'Real-time global market data, breaking financial news, and expert analysis.',
  },
  {
    title: 'CNBC — World Markets',
    url: 'https://www.cnbc.com/world-markets/',
    source: 'CNBC',
    icon: '📺',
    category: 'Markets',
    description: 'Live market coverage, pre-market movers, and global economic data.',
  },
  {
    title: 'AFR — Markets',
    url: 'https://www.afr.com/markets',
    source: 'AFR',
    icon: '🇦🇺',
    category: 'ASX',
    description: 'Australian Financial Review — ASX coverage, economy, and company news.',
  },
  {
    title: 'Bloomberg — Markets',
    url: 'https://www.bloomberg.com/markets',
    source: 'Bloomberg',
    icon: '💹',
    category: 'Markets',
    description: 'Global market data, commodities, currencies, and economic indicators.',
  },
  {
    title: 'MarketWatch — Latest News',
    url: 'https://www.marketwatch.com/latest-news',
    source: 'MarketWatch',
    icon: '📊',
    category: 'Analysis',
    description: 'Breaking market news, stock analysis, and economic commentary.',
  },
  {
    title: 'Financial Times — Markets',
    url: 'https://www.ft.com/markets',
    source: 'FT',
    icon: '📰',
    category: 'Global',
    description: 'World-class financial journalism — markets, economics, and geopolitics.',
  },
  {
    title: 'Yahoo Finance — Market Overview',
    url: 'https://finance.yahoo.com/',
    source: 'Yahoo Finance',
    icon: '📈',
    category: 'Overview',
    description: 'Free market data, watchlists, portfolio tracking, and financial news.',
  },
  {
    title: 'Livewire Markets — ASX Expert Views',
    url: 'https://www.livewiremarkets.com/',
    source: 'Livewire',
    icon: '⚡',
    category: 'ASX',
    description: 'Expert fund manager insights, stock tips, and ASX market commentary.',
  },
  {
    title: 'RBA — Economic Policy',
    url: 'https://www.rba.gov.au/monetary-policy/',
    source: 'RBA',
    icon: '🏛️',
    category: 'Policy',
    description: 'Reserve Bank of Australia — interest rates, monetary policy, and economic outlook.',
  },
  {
    title: 'Fed — Monetary Policy',
    url: 'https://www.federalreserve.gov/monetarypolicy.htm',
    source: 'Federal Reserve',
    icon: '🇺🇸',
    category: 'Policy',
    description: 'US Federal Reserve — FOMC decisions, interest rates, and economic projections.',
  },
]

// Google News RSS → JSON via free API
const RSS_PROXY = 'https://api.rss2json.com/v1/api.json?rss_url='

function timeAgo(dateStr) {
  if (!dateStr) return ''
  try {
    const d = new Date(dateStr)
    const now = new Date()
    const diff = Math.floor((now - d) / 1000)
    if (diff < 60) return 'just now'
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
    if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`
    return d.toLocaleDateString('en-AU', { day: 'numeric', month: 'short' })
  } catch {
    return ''
  }
}

function cleanTitle(title) {
  // Remove source suffix from Google News titles (e.g., "Headline - Source Name")
  return title.replace(/\s*[-–—]\s*[^-–—]+$/, '').trim()
}

export default function GlobalNewsFeed({ variant = 'full', maxArticles, className = '' }) {
  const [articles, setArticles] = useState([])
  const [loading, setLoading] = useState(true)
  const [activeCategory, setActiveCategory] = useState('ALL')
  const [expanded, setExpanded] = useState(false)

  const defaultMax = variant === 'compact' ? 4 : variant === 'sidebar' ? 6 : 8
  const limit = maxArticles || defaultMax

  const fetchNews = useCallback(async () => {
    const allArticles = []

    // Phase 1: Try pre-cached articles from CI pipeline
    try {
      const cachedRes = await fetch('/data/top_stories.json')
      if (cachedRes.ok) {
        const cached = await cachedRes.json()
        if (cached.feedArticles?.length > 0) {
          // Sort by pubDate descending (most recent first)
          const sorted = [...cached.feedArticles]
            .sort((a, b) => new Date(b.pubDate) - new Date(a.pubDate))
          setArticles(sorted)
          setLoading(false)
          // Don't return — still try live fetch to get newer data
        }
      }
    } catch {
      // Cache miss — continue
    }

    // Phase 2: Live fetch from Google News RSS feeds
    const fetchPromises = NEWS_SOURCES.map(async (source) => {
      try {
        const res = await fetch(`${RSS_PROXY}${encodeURIComponent(source.rss)}`)
        if (!res.ok) return []
        const data = await res.json()
        if (data.status !== 'ok' || !data.items) return []
        return data.items.slice(0, 5).map(item => ({
          title: cleanTitle(item.title),
          url: item.link,
          source: item.author || source.name,
          sourceIcon: source.icon,
          category: source.category,
          pubDate: item.pubDate,
          description: item.description?.replace(/<[^>]*>/g, '').slice(0, 180) || '',
          color: source.color,
        }))
      } catch {
        return []
      }
    })

    const results = await Promise.allSettled(fetchPromises)
    results.forEach(result => {
      if (result.status === 'fulfilled' && result.value.length) {
        allArticles.push(...result.value)
      }
    })

    // Sort by date, dedup by title
    const seen = new Set()
    const deduped = allArticles
      .sort((a, b) => new Date(b.pubDate) - new Date(a.pubDate))
      .filter(a => {
        const key = a.title.toLowerCase().slice(0, 50)
        if (seen.has(key)) return false
        seen.add(key)
        return true
      })

    if (deduped.length > 0) {
      setArticles(deduped)
    }
    setLoading(false)
  }, [])

  useEffect(() => {
    fetchNews()
    // Refresh every 10 minutes
    const interval = setInterval(fetchNews, 10 * 60 * 1000)
    return () => clearInterval(interval)
  }, [fetchNews])

  const categories = ['ALL', ...new Set(articles.map(a => a.category))]

  const filtered = activeCategory === 'ALL'
    ? articles
    : articles.filter(a => a.category === activeCategory)

  const displayArticles = expanded ? filtered : filtered.slice(0, limit)

  if (variant === 'sidebar') {
    return (
      <div className={`news-sidebar ${className}`} id="global-news-sidebar">
        <div className="news-sidebar__header">
          <h3 className="news-sidebar__title">
            <span className="news-sidebar__icon">📡</span>
            Global Markets
          </h3>
          <span className="news-sidebar__live-dot" />
        </div>

        {loading ? (
          <div className="news-sidebar__loading">
            <div className="news-sidebar__skeleton" />
            <div className="news-sidebar__skeleton" />
            <div className="news-sidebar__skeleton" />
          </div>
        ) : articles.length > 0 ? (
          <div className="news-sidebar__list">
            {displayArticles.map((article, i) => (
              <a
                key={`${article.title}-${i}`}
                href={article.url}
                target="_blank"
                rel="noopener noreferrer"
                className="news-sidebar__item"
              >
                <span className="news-sidebar__item-icon">{article.sourceIcon}</span>
                <div className="news-sidebar__item-content">
                  <span className="news-sidebar__item-title">{article.title}</span>
                  <span className="news-sidebar__item-meta">
                    {article.source} · {timeAgo(article.pubDate)}
                  </span>
                </div>
              </a>
            ))}
          </div>
        ) : null}

        {/* Always show curated links */}
        <div className="news-sidebar__curated">
          <div className="news-sidebar__curated-label">Quick Links</div>
          {CURATED_LINKS.slice(0, 5).map((link, i) => (
            <a
              key={i}
              href={link.url}
              target="_blank"
              rel="noopener noreferrer"
              className="news-sidebar__curated-link"
            >
              <span>{link.icon}</span>
              <span>{link.source}</span>
              <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" /><polyline points="15 3 21 3 21 9" /><line x1="10" y1="14" x2="21" y2="3" /></svg>
            </a>
          ))}
        </div>
      </div>
    )
  }

  if (variant === 'compact') {
    return (
      <div className={`news-compact ${className}`} id="global-news-compact">
        <div className="news-compact__header">
          <div className="news-compact__title-row">
            <h3 className="news-compact__title">
              <span className="news-compact__icon">📡</span>
              Market News
            </h3>
            <span className="news-compact__live">
              <span className="news-compact__live-dot" />
              Live
            </span>
          </div>
        </div>

        <div className="news-compact__articles">
          {loading ? (
            <>
              <div className="news-compact__skeleton" />
              <div className="news-compact__skeleton" />
              <div className="news-compact__skeleton" />
            </>
          ) : articles.length > 0 ? (
            displayArticles.map((article, i) => (
              <a
                key={`${article.title}-${i}`}
                href={article.url}
                target="_blank"
                rel="noopener noreferrer"
                className="news-compact__article"
              >
                <div className="news-compact__article-header">
                  <span className="news-compact__article-source">{article.sourceIcon} {article.source}</span>
                  <span className="news-compact__article-time">{timeAgo(article.pubDate)}</span>
                </div>
                <div className="news-compact__article-title">{article.title}</div>
              </a>
            ))
          ) : (
            CURATED_LINKS.slice(0, 4).map((link, i) => (
              <a
                key={i}
                href={link.url}
                target="_blank"
                rel="noopener noreferrer"
                className="news-compact__article"
              >
                <div className="news-compact__article-header">
                  <span className="news-compact__article-source">{link.icon} {link.source}</span>
                  <span className="news-compact__article-category">{link.category}</span>
                </div>
                <div className="news-compact__article-title">{link.title}</div>
                <div className="news-compact__article-desc">{link.description}</div>
              </a>
            ))
          )}
        </div>

        <div className="news-compact__links">
          {CURATED_LINKS.slice(0, 4).map((link, i) => (
            <a
              key={i}
              href={link.url}
              target="_blank"
              rel="noopener noreferrer"
              className="news-compact__link"
              title={link.description}
            >
              {link.icon} {link.source} →
            </a>
          ))}
        </div>
      </div>
    )
  }

  // Full variant
  return (
    <div className={`news-feed ${className}`} id="global-news-feed">
      <div className="news-feed__header">
        <div className="news-feed__title-group">
          <div className="news-feed__title-row">
            <h2 className="news-feed__title">
              <span className="news-feed__title-icon">🌍</span>
              Global Economic & Financial News
            </h2>
            <span className="news-feed__live-indicator">
              <span className="news-feed__live-dot" />
              Live Feed
            </span>
          </div>
          <p className="news-feed__subtitle">
            Curated headlines from the world's top financial news sources
          </p>
        </div>

        {articles.length > 0 && categories.length > 2 && (
          <div className="news-feed__filters">
            {categories.map(cat => (
              <button
                key={cat}
                className={`news-feed__filter ${activeCategory === cat ? 'news-feed__filter--active' : ''}`}
                onClick={() => setActiveCategory(cat)}
              >
                {cat === 'ALL' ? '🌐 All' :
                 cat === 'Markets' ? '💹 Markets' :
                 cat === 'Economy' ? '🏛️ Economy' :
                 cat === 'ASX' ? '🇦🇺 ASX' :
                 cat === 'Analysis' ? '📊 Analysis' :
                 cat === 'Global' ? '🌍 Global' :
                 cat === 'Policy' ? '🏛️ Policy' :
                 cat}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Live Articles */}
      {loading ? (
        <div className="news-feed__loading">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="news-feed__skeleton">
              <div className="news-feed__skeleton-bar news-feed__skeleton-bar--title" />
              <div className="news-feed__skeleton-bar news-feed__skeleton-bar--desc" />
              <div className="news-feed__skeleton-bar news-feed__skeleton-bar--meta" />
            </div>
          ))}
        </div>
      ) : articles.length > 0 ? (
        <>
          <div className="news-feed__grid">
            {displayArticles.map((article, i) => (
              <a
                key={`${article.title}-${i}`}
                href={article.url}
                target="_blank"
                rel="noopener noreferrer"
                className="news-feed__article"
                style={{ animationDelay: `${i * 0.05}s` }}
              >
                <div className="news-feed__article-header">
                  <span className="news-feed__article-source">
                    {article.sourceIcon} {article.source}
                  </span>
                  <span className="news-feed__article-time">{timeAgo(article.pubDate)}</span>
                </div>
                <h3 className="news-feed__article-title">{article.title}</h3>
                {article.description && (
                  <p className="news-feed__article-desc">{article.description}</p>
                )}
                <div className="news-feed__article-footer">
                  <span className="news-feed__article-category">{article.category}</span>
                  <span className="news-feed__article-read">
                    Read more
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" /><polyline points="15 3 21 3 21 9" /><line x1="10" y1="14" x2="21" y2="3" /></svg>
                  </span>
                </div>
              </a>
            ))}
          </div>

          {filtered.length > limit && (
            <button
              className="news-feed__expand"
              onClick={() => setExpanded(!expanded)}
            >
              {expanded ? 'Show less ↑' : `Show all ${filtered.length} articles ↓`}
            </button>
          )}
        </>
      ) : null}

      {/* Curated Direct Links — always visible */}
      <div className="news-feed__curated">
        <div className="news-feed__curated-header">
          <span className="news-feed__curated-icon">🔗</span>
          <div>
            <h3 className="news-feed__curated-title">Financial Research & Data</h3>
            <p className="news-feed__curated-subtitle">Direct links to the world's leading financial news and economic policy sources</p>
          </div>
        </div>
        <div className="news-feed__curated-grid">
          {CURATED_LINKS.map((link, i) => (
            <a
              key={i}
              href={link.url}
              target="_blank"
              rel="noopener noreferrer"
              className="news-feed__curated-card"
              style={{ animationDelay: `${i * 0.04}s` }}
            >
              <div className="news-feed__curated-card-header">
                <span className="news-feed__curated-card-icon">{link.icon}</span>
                <span className="news-feed__curated-card-badge">{link.category}</span>
              </div>
              <div className="news-feed__curated-card-source">{link.source}</div>
              <div className="news-feed__curated-card-desc">{link.description}</div>
              <div className="news-feed__curated-card-cta">
                Visit →
              </div>
            </a>
          ))}
        </div>
      </div>
    </div>
  )
}
