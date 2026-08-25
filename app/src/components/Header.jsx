import { QuestionIcon } from './Icons'
import lunaLogo from '../assets/luna-logo.png'

const STEPS = [
  'Business profile',
  'Financial details',
  'Account verification',
  'Review & submit',
]

export default function Header({ currentStep = 1 }) {
  return (
    <header className="header">
      <a href="#" className="logo">
        <img src={lunaLogo} alt="Luna" height="36" />
      </a>

      <nav className="stepper" aria-label="Onboarding progress">
        {STEPS.map((label, i) => {
          const step = i + 1
          const isActive = step === currentStep
          return (
            <div key={step} style={{ display: 'flex', alignItems: 'flex-start' }}>
              <div className={`step ${isActive ? 'active' : ''}`}>
                <div className="step-circle">{step}</div>
                <span className="step-label">{label}</span>
              </div>
              {step < STEPS.length && <div className="step-line" />}
            </div>
          )
        })}
      </nav>

      <button className="help-btn">
        <QuestionIcon />
        Need help?
      </button>
    </header>
  )
}
