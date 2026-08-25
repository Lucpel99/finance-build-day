import { WarningIcon } from './Icons'

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

        <h2 id="skip-dialog-title">Skip automatic verification?</h2>
        <p>Without connecting your accounts, you'll need to:</p>

        <ul className="modal-list">
          <li>Upload bank statements manually</li>
          <li>Provide recent financial documents</li>
          <li>Wait for a manual review by our team</li>
        </ul>

        <p className="modal-note">
          Merchants who connect their accounts are typically approved{' '}
          <strong>3× faster</strong> — with no documents to find or upload.
        </p>

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
