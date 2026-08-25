import Header from '../components/Header'

const COMPANY_FIELDS = [
  { label: 'Company name',      value: 'Lindström Café AB',             verified: false },
  { label: 'Organisation nr',   value: '559234-5678',                   verified: true  },
  { label: 'Industry',          value: 'Food & Beverage',               verified: false },
  { label: 'Legal form',        value: 'Aktiebolag (AB)',               verified: false },
  { label: 'Founded',           value: 'March 2018',                    verified: false },
  { label: 'Address',           value: 'Sveavägen 47, 113 59 Stockholm', verified: false },
  { label: 'VAT registered',    value: 'Yes',                           verified: true  },
  { label: 'UBO',               value: 'Maria Lindström (100%)',        verified: false },
  { label: 'Status',            value: 'Active',                        verified: true  },
]

function VerifiedBadge() {
  return (
    <span className="verified-badge">
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
        <circle cx="12" cy="12" r="10" fill="#22C55E"/>
        <path d="M8 12l3 3 5-5" stroke="white" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"/>
      </svg>
      Verified
    </span>
  )
}

export default function CompanyStep({ onContinue }) {
  return (
    <div className="page-wrapper">
      <Header currentStep={1} />
      <main className="main">
        <h1 className="page-title">Your business profile</h1>
        <p className="subtitle">
          Here's what we've collected. Please review before continuing.
        </p>

        <div className="card" style={{ marginTop: 28 }}>
          {COMPANY_FIELDS.map((field, i) => (
            <div key={field.label} className={`company-row${i === COMPANY_FIELDS.length - 1 ? ' last' : ''}`}>
              <span className="company-label">{field.label}</span>
              <span className="company-value">
                {field.value}
                {field.verified && <VerifiedBadge />}
              </span>
            </div>
          ))}
        </div>

        <div className="inline-actions">
          <button className="skip-link">Not you? Edit details</button>
          <button className="btn-continue" onClick={onContinue}>
            Confirm and continue
          </button>
        </div>
      </main>
    </div>
  )
}
