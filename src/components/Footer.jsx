import './Footer.css'

export default function Footer() {
  const year = new Date().getFullYear()

  return (
    <footer className="footer" id="footer">
      <div className="container">
        <div className="footer__content">
          <div className="footer__brand">
            <span className="footer__logo">Nick Knows Best</span>
            <p className="footer__tagline">AI-powered ASX trading with momentum confirmation.</p>
          </div>

          <div className="footer__links">
            <a href="#home-page" className="footer__link">Home</a>
            <a href="#trading-dashboard" className="footer__link">Portfolio</a>
            <a href="#disclaimer" className="footer__link">Disclaimer</a>
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
