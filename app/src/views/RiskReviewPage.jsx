import { useState, useEffect } from 'react'
import lunaLogo from '../assets/luna-logo.png'
import { BankIcon, GridIcon, CheckCircle, WarningIcon } from '../components/Icons'

const DEFAULT_CLAIMED = { yearly_revenue: 4500000, avg_transaction: 350, max_transaction: 5000 }

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
  const [comparison, setComparison] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let claimed = DEFAULT_CLAIMED
    try {
      const raw = localStorage.getItem('luna_claimed')
      if (raw) claimed = JSON.parse(raw)
    } catch (_) {}

    fetch('http://localhost:8000/api/verify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(claimed),
    })
      .then(r => { if (!r.ok) throw new Error(`Server returned ${r.status}`); return r.json() })
      .then(json => { setComparison(json.comparison); setLoading(false) })
      .catch(err => { setError(err.message); setLoading(false) })
  }, [])

  const attentionCount = comparison ? comparison.filter(r => r.status === 'mismatch').length : 0

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
              {loading ? (
                <div className="risk-stat-value" style={{ color: 'var(--muted)' }}>Loading…</div>
              ) : error ? (
                <div className="risk-stat-value warn">Error</div>
              ) : (
                <div className={`risk-stat-value ${attentionCount > 0 ? 'warn' : 'ok'}`}>
                  {attentionCount > 0 ? `${attentionCount} item${attentionCount > 1 ? 's' : ''} need attention` : 'All clear'}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Loading */}
        {loading && (
          <div style={{ display: 'flex', justifyContent: 'center', padding: '64px 0' }}>
            <div className="spinner" style={{ width: 36, height: 36, borderWidth: 3 }} />
          </div>
        )}

        {/* Error */}
        {error && !loading && (
          <div style={{ padding: '32px', background: 'var(--cloud-white)', border: '1px solid var(--border)', borderRadius: 'var(--radius-card)', color: 'var(--muted)', textAlign: 'center' }}>
            <p style={{ fontWeight: 600, color: 'var(--danger)', marginBottom: 8 }}>Could not load verification data</p>
            <p style={{ fontSize: 13 }}>{error}</p>
            <p style={{ fontSize: 12, marginTop: 12 }}>Make sure the API server is running: <code>uvicorn src.api.server:app --reload --port 8000</code></p>
          </div>
        )}

        {/* Comparison table */}
        {comparison && !loading && (
          <>
            <div className="risk-table-wrap">
              <table className="risk-table">
                <thead>
                  <tr className="risk-table-head">
                    <th className="risk-th info-col">Information</th>
                    <th className="risk-th data-col">
                      <span className="risk-col-icon"><UserPersonIcon />User input</span>
                    </th>
                    <th className="risk-th data-col">
                      <span className="risk-col-icon"><BankIcon color="var(--muted)" />Open banking</span>
                    </th>
                    <th className="risk-th data-col">
                      <span className="risk-col-icon"><GridIcon color="var(--muted)" />Open accounting</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {comparison.map((row, i) => (
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
              Accounting and banking data were retrieved automatically. Data reflects the last 365 days.
            </p>
          </>
        )}

        <div className="inline-actions" style={{ marginTop: 32 }}>
          <button className="btn-secondary">Request clarification</button>
          <button className="btn-continue" disabled={loading || !!error}>
            Approve application
          </button>
        </div>
      </main>
    </div>
  )
}
