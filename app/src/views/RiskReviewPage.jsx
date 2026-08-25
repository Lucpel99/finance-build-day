import lunaLogo from '../assets/luna-logo.png'
import { BankIcon, GridIcon, CheckCircle, WarningIcon } from '../components/Icons'

const MOCK_DATA = [
  {
    id: 'yearly_revenue',
    label: 'Estimated yearly revenue',
    status: 'close_match',
    statusLabel: 'Close match',
    userInput:   '4 500 000 SEK',
    openBanking: '4 820 000 SEK',
    accounting:  '4 610 000 SEK',
  },
  {
    id: 'avg_tx',
    label: 'Avg. transaction value',
    status: 'match',
    statusLabel: 'Exact match',
    userInput:   '350 SEK',
    openBanking: '328 SEK',
    accounting:  '361 SEK',
  },
  {
    id: 'max_tx',
    label: 'Max. transaction value',
    status: 'mismatch',
    statusLabel: 'Needs review',
    userInput:   '5 000 SEK',
    openBanking: '12 400 SEK',
    accounting:  '4 200 SEK',
  },
]

const attentionCount = MOCK_DATA.filter(d => d.status === 'mismatch').length

function UserPersonIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="8" r="4"/>
      <path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/>
    </svg>
  )
}

function BuildingIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="18" height="18" rx="2"/>
      <path d="M9 21V9h6v12M9 12h6"/>
    </svg>
  )
}

function LinkIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>
      <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>
    </svg>
  )
}

function StatusIcon({ status }) {
  if (status === 'mismatch') return <WarningIcon size={16} />
  return <CheckCircle size={16} />
}

export default function RiskReviewPage() {
  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)' }}>
      {/* Risk-specific header */}
      <header className="risk-header">
        <a href="#" className="logo" style={{ textDecoration: 'none' }}>
          <img src={lunaLogo} alt="Luna" height="32" />
        </a>
        <nav className="risk-breadcrumb" aria-label="Breadcrumb">
          <span>Merchant reviews</span>
          <span>/</span>
          <span style={{ color: 'var(--deep-slate)', fontWeight: 600 }}>Lindström Café AB</span>
        </nav>
        <div className="risk-avatar">RA</div>
      </header>

      <main className="risk-main fade-in">
        <h1 className="page-title" style={{ textAlign: 'left' }}>Verification comparison</h1>
        <p className="subtitle" style={{ textAlign: 'left', marginTop: 8 }}>
          Compare the merchant's submitted information with connected banking and accounting data.
        </p>

        {/* Summary bar */}
        <div className="risk-summary-bar">
          <div className="risk-stat-chip">
            <span className="risk-stat-icon"><BuildingIcon /></span>
            <div>
              <div className="risk-stat-label">Merchant</div>
              <div className="risk-stat-value">Lindström Café AB</div>
            </div>
          </div>
          <div className="risk-stat-chip">
            <span className="risk-stat-icon"><LinkIcon /></span>
            <div>
              <div className="risk-stat-label">Sources connected</div>
              <div className="risk-stat-value ok">2 / 2</div>
            </div>
          </div>
          <div className="risk-stat-chip">
            <span className="risk-stat-icon"><WarningIcon size={16} /></span>
            <div>
              <div className="risk-stat-label">Review status</div>
              <div className={`risk-stat-value ${attentionCount > 0 ? 'warn' : 'ok'}`}>
                {attentionCount > 0 ? `${attentionCount} item needs attention` : 'All clear'}
              </div>
            </div>
          </div>
        </div>

        {/* Comparison table */}
        <div className="risk-table-wrap">
          <table className="risk-table">
            <thead>
              <tr className="risk-table-head">
                <th className="risk-th info-col">Information</th>
                <th className="risk-th data-col">
                  <span className="risk-col-icon">
                    <UserPersonIcon />
                    User input
                  </span>
                </th>
                <th className="risk-th data-col">
                  <span className="risk-col-icon">
                    <BankIcon color="var(--muted)" />
                    Open banking
                  </span>
                </th>
                <th className="risk-th data-col">
                  <span className="risk-col-icon">
                    <GridIcon color="var(--muted)" />
                    Open accounting
                  </span>
                </th>
              </tr>
            </thead>
            <tbody>
              {MOCK_DATA.map((row, i) => (
                <tr key={row.id} className={`risk-tr${row.status === 'mismatch' ? ' mismatch' : ''}`}>
                  <td className="risk-td info-col">
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <span className="risk-row-num">{i + 1}</span>
                      <div>
                        <div className="risk-row-label">{row.label}</div>
                        <div className={`risk-row-status ${row.status === 'mismatch' ? 'warn' : 'ok'}`}>
                          {row.statusLabel}
                        </div>
                      </div>
                    </div>
                  </td>
                  <td className="risk-td">
                    <div className="risk-cell-value">
                      <span className="risk-value-text">{row.userInput}</span>
                      <StatusIcon status={row.status} />
                    </div>
                  </td>
                  <td className="risk-td">
                    <div className="risk-cell-value">
                      <span className="risk-value-text">{row.openBanking}</span>
                      <StatusIcon status={row.status} />
                    </div>
                  </td>
                  <td className="risk-td">
                    <div className="risk-cell-value">
                      <span className="risk-value-text">{row.accounting}</span>
                      <StatusIcon status={row.status} />
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <p style={{ fontSize: 12, color: 'var(--muted)', marginTop: 16 }}>
          Accounting and banking data were retrieved automatically on Aug 25, 2026 at 09:11.
        </p>

        <div className="inline-actions" style={{ marginTop: 32 }}>
          <button className="btn-secondary">Request clarification</button>
          <button className="btn-continue">Approve application</button>
        </div>
      </main>
    </div>
  )
}
