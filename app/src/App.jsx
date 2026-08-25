import { useState, useCallback } from 'react'
import Header from './components/Header'
import ConnectionRow from './components/ConnectionRow'
import SkipDialog from './components/SkipDialog'
import { SparkleIcon, BigCheckIcon, WarningIcon } from './components/Icons'
import WelcomeStep from './steps/WelcomeStep'
import CompanyStep from './steps/CompanyStep'
import FinancialStep from './steps/FinancialStep'

const TYPES = ['bank', 'accounting']

export default function App() {
  const [step, setStep] = useState(1)
  const [connections, setConnections] = useState({ bank: 'idle', accounting: 'idle' })
  const [showSkipDialog, setShowSkipDialog] = useState(false)
  const [outcome, setOutcome] = useState(null) // null | 'fast-lane' | 'manual'

  const handleConnect = useCallback((type) => {
    setConnections(prev => {
      if (prev[type] !== 'idle') return prev
      return { ...prev, [type]: 'connecting' }
    })
    setTimeout(() => {
      setConnections(prev => ({ ...prev, [type]: 'connected' }))
    }, 1600)
  }, [])

  const bothConnected = connections.bank === 'connected' && connections.accounting === 'connected'
  const pendingTypes   = TYPES.filter(t => connections[t] !== 'connected')
  const connectedTypes = TYPES.filter(t => connections[t] === 'connected')

  const resetDemo = () => {
    setStep(1)
    setOutcome(null)
    setConnections({ bank: 'idle', accounting: 'idle' })
  }

  // ── Step 1: Welcome ──────────────────────────────────────
  if (step === 1) {
    return <WelcomeStep onContinue={() => setStep(2)} />
  }

  // ── Step 2: Business profile ─────────────────────────────
  if (step === 2) {
    return <CompanyStep onContinue={() => setStep(3)} />
  }

  // ── Step 3: Financial details ────────────────────────────
  if (step === 3) {
    return <FinancialStep onContinue={() => setStep(4)} onBack={() => setStep(2)} />
  }

  // ── Step 4: Outcomes ─────────────────────────────────────
  if (outcome === 'fast-lane') {
    return (
      <div className="page-wrapper">
        <Header currentStep={3} />
        <main className="main">
          <div className="outcome">
            <div className="outcome-icon success">
              <BigCheckIcon />
            </div>
            <h1 className="page-title">You're in the fast lane!</h1>
            <p className="subtitle">
              Your accounts are verified. We'll proceed straight to the automated
              decision — no manual document review required.
            </p>
            <div className="pills" style={{ marginTop: 28 }}>
              <span className="pill"><span>✦</span> No documents needed</span>
              <span className="pill"><span>⚡</span> Decision in seconds</span>
            </div>
            <div className="inline-actions" style={{ justifyContent: 'flex-end' }}>
              <button className="btn-continue" onClick={resetDemo}>
                Start over (demo)
              </button>
            </div>
          </div>
        </main>
      </div>
    )
  }

  if (outcome === 'manual') {
    return (
      <div className="page-wrapper">
        <Header currentStep={3} />
        <main className="main">
          <div className="outcome">
            <div className="outcome-icon warning">
              <WarningIcon size={32} />
            </div>
            <h1 className="page-title">Manual verification selected</h1>
            <p className="subtitle">
              You'll be asked to upload bank statements and financial documents in
              the next steps. Processing typically takes 3–5 business days.
            </p>
            <div className="inline-actions" style={{ justifyContent: 'flex-end' }}>
              <button className="btn-continue" onClick={resetDemo}>
                Start over (demo)
              </button>
            </div>
          </div>
        </main>
      </div>
    )
  }

  // ── Step 4: Account verification ─────────────────────────
  return (
    <div className="page-wrapper">
      <div className="bg-moon">
        <svg viewBox="0 0 200 200" fill="none">
          <path
            d="M160 100C160 133.137 133.137 160 100 160C66.863 160 40 133.137 40 100C40 66.863 66.863 40 100 40C85 55 80 75 82 100C84 125 95 145 115 152C135 158 155 138 160 100Z"
            fill="#F4D04E"
          />
        </svg>
      </div>
      <div className="bg-cloud">
        <svg viewBox="0 0 180 100" fill="none">
          <ellipse cx="90" cy="65" rx="80" ry="35" fill="#DCE7F4"/>
          <ellipse cx="65" cy="52" rx="42" ry="30" fill="#DCE7F4"/>
          <ellipse cx="115" cy="48" rx="38" ry="26" fill="#DCE7F4"/>
        </svg>
      </div>
      <span className="sparkle sparkle-1"><SparkleIcon /></span>
      <span className="sparkle sparkle-2"><SparkleIcon /></span>
      <span className="sparkle sparkle-3"><SparkleIcon /></span>
      <span className="sparkle sparkle-4"><SparkleIcon /></span>

      <Header currentStep={3} />

      <main className="main">
        <h1 className="page-title">Automatic account verification</h1>
        <p className="subtitle">
          Connect your bank and accounting system for a smooth process.
          Avoid manually uploading bank statements and speed up approval
          by letting us verify the information automatically.
        </p>

        <div className="pills">
          <span className="pill"><span>✦</span> No bank statements to upload</span>
          <span className="pill"><span>⚡</span> Faster approval</span>
        </div>

        {pendingTypes.length > 0 && (
          <div className="card">
            <p className="card-label">Connect your accounts</p>
            {pendingTypes.map((type, i) => (
              <div key={type}>
                {i > 0 && <div className="divider" />}
                <ConnectionRow
                  type={type}
                  status={connections[type]}
                  onConnect={() => handleConnect(type)}
                />
              </div>
            ))}
          </div>
        )}

        {connectedTypes.length > 0 && (
          <div className="card fade-in">
            <p className="card-label">Connected accounts</p>
            {connectedTypes.map((type, i) => (
              <div key={type}>
                {i > 0 && <div className="divider" />}
                <ConnectionRow type={type} status="connected" />
              </div>
            ))}
          </div>
        )}

        <div className="inline-actions">
          <button className="skip-link" onClick={() => setShowSkipDialog(true)}>
            Skip automatic account verification
          </button>
          <button
            className="btn-continue"
            disabled={!bothConnected}
            onClick={() => setOutcome('fast-lane')}
          >
            Continue
          </button>
        </div>
      </main>

      {showSkipDialog && (
        <SkipDialog
          onClose={() => setShowSkipDialog(false)}
          onConfirm={() => { setShowSkipDialog(false); setOutcome('manual') }}
        />
      )}
    </div>
  )
}
