import { useState } from 'react'
import Header from '../components/Header'

const MAX_REVENUE = 20_000_000
const DEFAULT_REVENUE = 4_500_000

function formatSEK(value) {
  return value.toLocaleString('sv-SE') + ' SEK'
}

function NumberInput({ label, value, onChange, min = 1 }) {
  return (
    <div className="financial-input-group">
      <label className="financial-label">{label}</label>
      <div className="input-wrapper">
        <input
          className="financial-input"
          type="number"
          min={min}
          value={value}
          onChange={e => onChange(e.target.value)}
        />
        <span className="input-suffix">SEK</span>
      </div>
    </div>
  )
}

export default function FinancialStep({ onContinue, onBack }) {
  const [revenue, setRevenue]     = useState(DEFAULT_REVENUE)
  const [avgTx,   setAvgTx]       = useState(350)
  const [maxTx,   setMaxTx]       = useState(5000)

  const pct = (revenue / MAX_REVENUE) * 100

  return (
    <div className="page-wrapper">
      <Header currentStep={2} />
      <main className="main">
        <h1 className="page-title">Financial details</h1>
        <p className="subtitle">
          Help us understand your typical business volume.
        </p>

        <div className="card" style={{ marginTop: 28 }}>
          <div className="financial-form">

            {/* Revenue slider */}
            <div className="financial-input-group">
              <label className="financial-label">Estimated yearly revenue</label>
              <div className="revenue-slider-value">{formatSEK(revenue)}</div>
              <input
                type="range"
                min={0}
                max={MAX_REVENUE}
                step={50_000}
                value={revenue}
                onChange={e => setRevenue(Number(e.target.value))}
                className="revenue-slider"
                style={{
                  background: `linear-gradient(to right, var(--moon-yellow) ${pct}%, var(--border) ${pct}%)`
                }}
              />
              <div className="slider-bounds">
                <span>0 SEK</span>
                <span>20 000 000 SEK</span>
              </div>
            </div>

            <div className="financial-divider" />

            <NumberInput
              label="Average transaction value"
              value={avgTx}
              onChange={setAvgTx}
            />

            <NumberInput
              label="Maximum transaction value"
              value={maxTx}
              onChange={setMaxTx}
            />

          </div>
        </div>

        <div className="inline-actions">
          <button className="skip-link" onClick={onBack}>← Back</button>
          <button className="btn-continue" onClick={onContinue}>
            Continue
          </button>
        </div>
      </main>
    </div>
  )
}
