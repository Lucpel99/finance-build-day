import { useState, useEffect } from 'react'
import lunaLogo from '../assets/luna-logo.png'
import { BankIcon, GridIcon } from '../components/Icons'

function LinkIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>
      <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>
    </svg>
  )
}

function MatchIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="20 6 9 17 4 12"/>
    </svg>
  )
}

function CloseIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
    </svg>
  )
}

// panel = 'tx' | 'inv' — drives how unmatched reads
function StatusBadge({ status, panel }) {
  const cfg = {
    matched:        { bg: '#DCFCE7', color: '#16A34A', label: 'Matched',          icon: true  },
    ambiguous:      { bg: '#EFF6FF', color: '#3B82F6', label: 'Ambiguous',        icon: false },
    // invoices: unmatched is a warning; transactions: unmatched is neutral/expected
    unmatched_inv:  { bg: '#FEF3C7', color: '#D97706', label: 'Missing payment',  icon: false },
    unmatched_tx:   { bg: 'var(--bg)', color: 'var(--muted)', label: 'No invoice', icon: false },
  }
  const key = status === 'unmatched' ? (panel === 'inv' ? 'unmatched_inv' : 'unmatched_tx') : status
  const { bg, color, label, icon } = cfg[key] || cfg.unmatched_inv
  return (
    <span style={{
      background: bg, color,
      fontSize: 11, fontWeight: 700, padding: '3px 10px',
      borderRadius: 999, letterSpacing: '0.04em', whiteSpace: 'nowrap',
      display: 'inline-flex', alignItems: 'center', gap: 4,
      border: key === 'unmatched_tx' ? '1px solid var(--border)' : 'none',
    }}>
      {icon && <MatchIcon />}
      {label}
    </span>
  )
}

function fmtAmount(amount, currency = 'SEK') {
  return `${Number(amount).toLocaleString('sv-SE')} ${currency}`
}

function fmtDate(dateStr) {
  if (!dateStr) return '—'
  try {
    return new Date(dateStr).toLocaleDateString('sv-SE', { month: 'short', day: 'numeric', year: 'numeric' })
  } catch { return dateStr }
}

function DetailModal({ item, type, onClose }) {
  if (!item) return null
  const isTx = type === 'tx'

  return (
    <div className="modal-overlay" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="modal" style={{ maxWidth: 480 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{
              width: 38, height: 38, borderRadius: '50%',
              background: isTx ? 'var(--mist-blue)' : '#EDE9FE',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              {isTx ? <BankIcon color="var(--deep-slate)" /> : <GridIcon color="#7C3AED" />}
            </div>
            <div>
              <p style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.07em', textTransform: 'uppercase', color: 'var(--muted)', marginBottom: 2 }}>
                {isTx ? 'Bank transaction' : 'Accounting invoice'}
              </p>
              <p style={{ fontSize: 15, fontWeight: 700, color: 'var(--deep-slate)' }}>
                {item.counterparty || '—'}
              </p>
            </div>
          </div>
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--muted)', padding: 4 }}>
            <CloseIcon />
          </button>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px 20px', marginBottom: 20 }}>
          {[
            ['Amount',      fmtAmount(item.amount, item.currency)],
            ['Date',        fmtDate(item.date)],
            ['Status',      null],
            isTx
              ? ['Transaction ID', item.tx_id || '—']
              : ['Invoice ref',    item.invoice_reference || '—'],
            isTx
              ? ['Description', item.description || '—']
              : ['Book ID',      item.book_id || '—'],
            ['Direction', item.direction === 'inbound' ? 'Inbound ↓' : 'Outbound ↑'],
          ].map(([label, value], i) => (
            <div key={i}>
              <p style={{ fontSize: 11, fontWeight: 600, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 4 }}>{label}</p>
              {label === 'Status'
                ? <StatusBadge status={item.status} />
                : <p style={{ fontSize: 14, fontWeight: 600, color: 'var(--deep-slate)' }}>{value}</p>
              }
            </div>
          ))}
        </div>

        {item.status === 'matched' && (
          <div style={{ background: '#DCFCE7', borderRadius: 10, padding: '12px 14px', marginBottom: 16 }}>
            <p style={{ fontSize: 12, fontWeight: 700, color: '#16A34A', marginBottom: 4 }}>Matched</p>
            <p style={{ fontSize: 13, color: 'var(--deep-slate)' }}>
              {isTx
                ? `Matched to invoice ${item.matched_book_id}`
                : `Matched to transaction ${item.matched_tx_id}`}
              {item.days_apart != null && ` · ${item.days_apart} day${item.days_apart !== 1 ? 's' : ''} apart`}
            </p>
          </div>
        )}

        {item.status === 'unmatched' && isTx && (
          <div style={{ background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 10, padding: '12px 14px', marginBottom: 16 }}>
            <p style={{ fontSize: 12, fontWeight: 700, color: 'var(--muted)', marginBottom: 4 }}>No invoice</p>
            <p style={{ fontSize: 13, color: 'var(--muted)' }}>
              This bank transaction has no corresponding invoice — this is normal and does not require action.
            </p>
          </div>
        )}
        {item.status === 'unmatched' && !isTx && (
          <div style={{ background: '#FEF3C7', borderRadius: 10, padding: '12px 14px', marginBottom: 16 }}>
            <p style={{ fontSize: 12, fontWeight: 700, color: '#D97706', marginBottom: 4 }}>Missing payment</p>
            <p style={{ fontSize: 13, color: 'var(--deep-slate)' }}>
              No bank transaction was found matching this invoice by amount, currency, and date (±5 days). This may indicate the payment hasn't been received or is recorded under a different reference.
            </p>
          </div>
        )}

        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <button className="btn-secondary" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  )
}

export default function MatchingPage() {
  const [data, setData]       = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState(null)
  const [modal, setModal]     = useState(null) // { item, type: 'tx'|'inv' }
  const [txSearch, setTxSearch]   = useState('')
  const [invSearch, setInvSearch] = useState('')

  useEffect(() => {
    fetch('http://localhost:8000/api/match', { method: 'POST' })
      .then(r => { if (!r.ok) throw new Error(`Server returned ${r.status}`); return r.json() })
      .then(json => { setData(json); setLoading(false) })
      .catch(err => { setError(err.message); setLoading(false) })
  }, [])

  const txs  = (data?.bank_transactions || []).filter(r => r.counterparty?.toLowerCase().includes(txSearch.toLowerCase()) || r.description?.toLowerCase().includes(txSearch.toLowerCase()))
  const invs = (data?.invoices || []).filter(r => r.counterparty?.toLowerCase().includes(invSearch.toLowerCase()) || (r.invoice_reference || '').toLowerCase().includes(invSearch.toLowerCase()))
  const summary = data?.summary || {}
  const noMatches = !loading && !error && summary.matched === 0

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)' }}>
      {/* Header */}
      <header className="risk-header">
        <a href="#" className="logo" style={{ textDecoration: 'none' }}>
          <img src={lunaLogo} alt="Luna" height="32" />
        </a>
        <nav className="risk-breadcrumb">
          <a href="#risk" style={{ color: 'var(--muted)', textDecoration: 'none' }}>Merchant reviews</a>
          <span>/</span>
          <a href="#risk" style={{ color: 'var(--muted)', textDecoration: 'none' }}>Lindström Café AB</a>
          <span>/</span>
          <span style={{ color: 'var(--deep-slate)', fontWeight: 600 }}>Transaction matching</span>
        </nav>
        <div className="risk-avatar">RA</div>
      </header>

      <main className="match-main fade-in">
        <h1 className="page-title" style={{ textAlign: 'left' }}>Transaction &amp; invoice matching</h1>
        <p className="subtitle" style={{ textAlign: 'left', marginTop: 8 }}>
          Every invoice should have a matching bank transaction. Not every bank transaction needs an invoice — only unmatched invoices require attention.
        </p>

        {/* Summary chips */}
        <div className="risk-summary-bar">
          <div className="risk-stat-chip">
            <span className="risk-stat-icon"><LinkIcon /></span>
            <div>
              <div className="risk-stat-label">Sources connected</div>
              <div className="risk-stat-value ok">2 / 2</div>
            </div>
          </div>
          <div className="risk-stat-chip">
            <span className="risk-stat-icon"><MatchIcon /></span>
            <div>
              <div className="risk-stat-label">Unmatched invoices</div>
              <div className={`risk-stat-value ${loading ? '' : summary.unmatched > 0 ? 'warn' : 'ok'}`}>
                {loading ? '…' : summary.unmatched}
              </div>
            </div>
          </div>
          <div className="risk-stat-chip">
            <span className="risk-stat-icon">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
            </span>
            <div>
              <div className="risk-stat-label">Review status</div>
              <div className={`risk-stat-value ${loading ? '' : noMatches ? 'warn' : 'ok'}`}>
                {loading ? '…' : noMatches ? 'No automatic matches found' : `${summary.matched} match${summary.matched !== 1 ? 'es' : ''} found`}
              </div>
            </div>
          </div>
        </div>

        {/* No-match banner */}
        {noMatches && (
          <div className="match-banner fade-in">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ flexShrink: 0 }}><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
            No invoices could be automatically matched to a bank transaction. Bank transactions without invoices are shown for reference but are not flagged as issues.
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="match-banner" style={{ background: '#FEF2F2', borderColor: '#FECACA', color: 'var(--danger)' }}>
            Could not load matching data — make sure the API server is running on port 8000.
          </div>
        )}

        {/* Two-panel layout */}
        {loading ? (
          <div style={{ display: 'flex', justifyContent: 'center', padding: '64px 0' }}>
            <div className="spinner" style={{ width: 36, height: 36, borderWidth: 3 }} />
          </div>
        ) : (
          <div className="match-panels">
            {/* Bank transactions */}
            <div className="match-panel">
              <div className="match-panel-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <BankIcon color="var(--deep-slate)" />
                  <span className="match-panel-title">Open banking transactions</span>
                  <span className="match-panel-count">{data?.bank_transactions?.length ?? 0}</span>
                </div>
                <input
                  className="match-search"
                  placeholder="Search transactions…"
                  value={txSearch}
                  onChange={e => setTxSearch(e.target.value)}
                />
              </div>
              <div className="match-table-wrap">
                {txs.length === 0 ? (
                  <div className="match-empty">No transactions to show</div>
                ) : (
                  <table className="match-table">
                    <thead>
                      <tr>
                        <th>Date</th>
                        <th>Counterparty</th>
                        <th style={{ textAlign: 'right' }}>Amount</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {txs.map(tx => (
                        <tr key={tx.tx_id} className="match-row" onClick={() => setModal({ item: tx, type: 'tx' })}>
                          <td className="match-date">{fmtDate(tx.date)}</td>
                          <td>
                            <div className="match-party">{tx.counterparty}</div>
                            {tx.description && <div className="match-desc">{tx.description}</div>}
                          </td>
                          <td style={{ textAlign: 'right', fontWeight: 600, whiteSpace: 'nowrap' }}>
                            {fmtAmount(tx.amount, tx.currency)}
                          </td>
                          <td><StatusBadge status={tx.status} panel="tx" /></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </div>

            {/* Accounting invoices */}
            <div className="match-panel">
              <div className="match-panel-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <GridIcon color="var(--deep-slate)" />
                  <span className="match-panel-title">Open accounting invoices</span>
                  <span className="match-panel-count">{data?.invoices?.length ?? 0}</span>
                </div>
                <input
                  className="match-search"
                  placeholder="Search invoices…"
                  value={invSearch}
                  onChange={e => setInvSearch(e.target.value)}
                />
              </div>
              <div className="match-table-wrap">
                {invs.length === 0 ? (
                  <div className="match-empty">No invoices to show</div>
                ) : (
                  <table className="match-table">
                    <thead>
                      <tr>
                        <th>Date</th>
                        <th>Counterparty</th>
                        <th>Invoice #</th>
                        <th style={{ textAlign: 'right' }}>Amount</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {invs.map(inv => (
                        <tr key={inv.book_id} className="match-row" onClick={() => setModal({ item: inv, type: 'inv' })}>
                          <td className="match-date">{fmtDate(inv.date)}</td>
                          <td className="match-party">{inv.counterparty}</td>
                          <td style={{ color: 'var(--muted)', fontSize: 13 }}>{inv.invoice_reference || inv.book_id}</td>
                          <td style={{ textAlign: 'right', fontWeight: 600, whiteSpace: 'nowrap' }}>
                            {fmtAmount(inv.amount, inv.currency)}
                          </td>
                          <td><StatusBadge status={inv.status} panel="inv" /></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </div>
          </div>
        )}

        <div className="inline-actions" style={{ marginTop: 28 }}>
          <a href="#risk" className="skip-link" style={{ textDecoration: 'none' }}>← Back to comparison</a>
          <button className="btn-continue">Continue review</button>
        </div>
      </main>

      {modal && (
        <DetailModal
          item={modal.item}
          type={modal.type}
          onClose={() => setModal(null)}
        />
      )}
    </div>
  )
}
