import { WarningIcon } from './Icons'

function UserIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="8" r="4" />
      <path d="M4 20c0-4 3.6-7 8-7s8 3 8 7" />
    </svg>
  )
}

function ClockIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="9" />
      <polyline points="12 7 12 12 15 15" />
    </svg>
  )
}

export default function SkipDialog({ onClose, onConfirm }) {
  const handleOverlayClick = (e) => {
    if (e.target === e.currentTarget) onClose()
  }

  return (
    <div className="modal-overlay" onClick={handleOverlayClick} role="dialog" aria-modal="true" aria-labelledby="skip-dialog-title">
      <div className="modal">
        <div className="modal-warning-icon">
          <WarningIcon size={28} />
        </div>

        <h2 id="skip-dialog-title">Skip automatic account verification?</h2>
        <p>
          You can continue without connecting your bank and accounting system, but you'll need to
          manually upload bank statements and supporting information. This usually means more manual
          effort and a longer review time, so you'll miss out on the faster onboarding process.
        </p>

        <div className="modal-badges">
          <span className="modal-badge">
            <UserIcon />
            More manual work
          </span>
          <span className="modal-badge">
            <ClockIcon />
            Longer approval time
          </span>
        </div>

        <div className="modal-actions">
          <button className="btn-secondary" onClick={onClose}>
            Go back
          </button>
          <button className="btn-danger-ghost" onClick={onConfirm}>
            Skip anyway
          </button>
        </div>
      </div>
    </div>
  )
}
