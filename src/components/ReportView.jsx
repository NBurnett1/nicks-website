import './ReportView.css'

export default function ReportView({ report }) {
  if (!report) return null

  const sections = [
    { key: 'executiveSummary', title: 'Executive Summary', icon: '📋' },
    { key: 'businessOverview', title: 'Business Overview', icon: '🏢' },
    { key: 'financialAnalysis', title: 'Financial Analysis', icon: '📊' },
    { key: 'assumptions', title: 'Assumptions & Forecasts', icon: '🔮' },
    { key: 'valuationDCF', title: 'DCF Valuation', icon: '🧮' },
    { key: 'valuationComps', title: 'Comparable Analysis', icon: '⚖️' },
    { key: 'valuationSummary', title: 'Valuation Summary', icon: '🎯' },
    { key: 'risksAndSensitivity', title: 'Risks & Sensitivity', icon: '⚠️' },
  ]

  const renderMarkdownLite = (text) => {
    if (!text) return null

    return text.split('\n\n').map((block, i) => {
      // Check if it's a table
      if (block.includes('|') && block.includes('---')) {
        return renderTable(block, i)
      }

      // Regular paragraph with inline formatting
      const formatted = block
        .split('\n')
        .map((line, j) => {
          // Bold
          let processed = line.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
          // Bullet points
          if (processed.startsWith('- ')) {
            processed = `<span class="report__bullet">•</span> ${processed.slice(2)}`
          }
          return <span key={j} className="report__line" dangerouslySetInnerHTML={{ __html: processed }} />
        })

      return (
        <div key={i} className="report__paragraph">
          {formatted}
        </div>
      )
    })
  }

  const renderTable = (tableText, key) => {
    const rows = tableText.trim().split('\n').filter(r => !r.match(/^\|[\s-|]+\|$/))
    if (rows.length === 0) return null

    const parseRow = (row) =>
      row.split('|').filter(c => c.trim()).map(c => c.trim())

    const headers = parseRow(rows[0])
    const bodyRows = rows.slice(1)

    return (
      <div key={key} className="report__table-wrapper">
        <table className="report__table">
          <thead>
            <tr>
              {headers.map((h, i) => (
                <th key={i}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {bodyRows.map((row, i) => {
              const cells = parseRow(row)
              return (
                <tr key={i}>
                  {cells.map((cell, j) => {
                    const isBold = cell.startsWith('**') && cell.endsWith('**')
                    const content = isBold ? cell.slice(2, -2) : cell
                    return (
                      <td key={j} className={isBold ? 'report__table-bold' : ''}>
                        {content}
                      </td>
                    )
                  })}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    )
  }

  return (
    <div className="report" id="report-view">
      {sections.map(({ key, title, icon }) => {
        const content = report[key]
        if (!content) return null

        return (
          <section key={key} className="report__section animate-fade-in-up">
            <div className="report__section-header">
              <span className="report__section-icon">{icon}</span>
              <h2 className="report__section-title">{title}</h2>
            </div>
            <div className="report__section-body">
              {renderMarkdownLite(content)}
            </div>
          </section>
        )
      })}
    </div>
  )
}
