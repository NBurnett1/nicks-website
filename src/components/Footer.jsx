import './Footer.css'

export default function Footer() {
  const year = new Date().getFullYear()

  return (
    <footer className="footer" id="footer">
      <div className="container">
        <div className="footer__content">
          <div className="footer__brand">
            <span className="footer__logo">ASX Valuations</span>
            <p className="footer__tagline">AI-powered stock analysis for the Australian market.</p>
          </div>

          <div className="footer__links">
            <a href="#hero" className="footer__link">Home</a>
            <a href="#undervalued-stocks" className="footer__link">Undervalued</a>
            <a href="#overvalued-stocks" className="footer__link">Overvalued</a>
            <a href="#disclaimer" className="footer__link">Disclaimer</a>
          </div>
        </div>

        <div className="footer__bottom">
          <p className="footer__copyright">© {year} ASX Valuations. All rights reserved.</p>
          <p className="footer__note">Data refreshed weekly. Not affiliated with ASX Limited.</p>
        </div>
      </div>
    </footer>
  )
}
