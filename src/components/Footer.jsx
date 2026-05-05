import './Footer.css'

const NEWS_LINKS = [
  { name: 'Reuters', url: 'https://www.reuters.com/markets/' },
  { name: 'Bloomberg', url: 'https://www.bloomberg.com/markets' },
  { name: 'CNBC', url: 'https://www.cnbc.com/world-markets/' },
  { name: 'AFR', url: 'https://www.afr.com/markets' },
  { name: 'MarketWatch', url: 'https://www.marketwatch.com/latest-news' },
  { name: 'FT', url: 'https://www.ft.com/markets' },
]

const RESEARCH_LINKS = [
  { name: 'Yahoo Finance', url: 'https://finance.yahoo.com/' },
  { name: 'Livewire', url: 'https://www.livewiremarkets.com/' },
  { name: 'RBA Policy', url: 'https://www.rba.gov.au/monetary-policy/' },
  { name: 'Fed Policy', url: 'https://www.federalreserve.gov/monetarypolicy.htm' },
]

export default function Footer() {
  const year = new Date().getFullYear()

  return (
    <footer className="footer" id="footer">
      <div className="container">
        <div className="footer__content">
          <div className="footer__brand">
            <span className="footer__logo">Nick Knows Best</span>
            <p className="footer__tagline">AI-powered ASX monthly conviction picks with valuation grading.</p>
          </div>

          <div className="footer__columns">
            <div className="footer__column">
              <h4 className="footer__column-title">Navigation</h4>
              <div className="footer__links">
                <a href="#home-page" className="footer__link">Home</a>
                <a href="#weekly-picks" className="footer__link">Current Picks</a>
                <a href="#global-news-feed" className="footer__link">Market News</a>
                <a href="#disclaimer" className="footer__link">Disclaimer</a>
              </div>
            </div>

            <div className="footer__column">
              <h4 className="footer__column-title">Financial News</h4>
              <div className="footer__links">
                {NEWS_LINKS.map(link => (
                  <a
                    key={link.name}
                    href={link.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="footer__link footer__link--external"
                  >
                    {link.name}
                    <svg width="8" height="8" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" /><polyline points="15 3 21 3 21 9" /><line x1="10" y1="14" x2="21" y2="3" /></svg>
                  </a>
                ))}
              </div>
            </div>

            <div className="footer__column">
              <h4 className="footer__column-title">Research & Policy</h4>
              <div className="footer__links">
                {RESEARCH_LINKS.map(link => (
                  <a
                    key={link.name}
                    href={link.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="footer__link footer__link--external"
                  >
                    {link.name}
                    <svg width="8" height="8" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" /><polyline points="15 3 21 3 21 9" /><line x1="10" y1="14" x2="21" y2="3" /></svg>
                  </a>
                ))}
              </div>
            </div>
          </div>
        </div>

        <div className="footer__bottom">
          <p className="footer__copyright">© {year} Nick Knows Best. All rights reserved.</p>
          <p className="footer__note">Simulated paper trading only. Not affiliated with ASX Limited.</p>
        </div>
      </div>
    </footer>
  )
}
