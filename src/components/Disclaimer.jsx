import './Disclaimer.css'

export default function Disclaimer() {
  return (
    <div className="disclaimer" id="disclaimer">
      <div className="container">
        <div className="disclaimer__content">
          <svg className="disclaimer__icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
            <line x1="12" y1="9" x2="12" y2="13"/>
            <line x1="12" y1="17" x2="12.01" y2="17"/>
          </svg>
          <p className="disclaimer__text">
            <strong>Not financial advice.</strong> All analysis on this site is AI-generated and for 
            educational and informational purposes only. Past performance is not indicative of future 
            results. Data sourced via unofficial channels and may contain inaccuracies. Always conduct 
            your own research and consult a licensed financial adviser before making investment decisions.
          </p>
        </div>
      </div>
    </div>
  )
}
