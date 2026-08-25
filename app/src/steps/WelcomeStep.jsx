import lunaLogo from '../assets/luna-logo.png'
import { SparkleIcon } from '../components/Icons'

export default function WelcomeStep({ onContinue }) {
  return (
    <div className="welcome-page">
      {/* Background decorations — larger on welcome */}
      <div className="bg-moon welcome-moon">
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

      <div className="welcome-content">
        <img src={lunaLogo} alt="Luna" className="welcome-logo" />

        <h1 className="welcome-title">Clarity in every decision.</h1>
        <p className="welcome-subtitle">
          Let's get your business verified.<br />It only takes a few minutes.
        </p>

        <div className="pills welcome-pills">
          <span className="pill"><span>✦</span> Fast approval</span>
          <span className="pill"><span>⚡</span> No paperwork surprises</span>
          <span className="pill"><span>🔒</span> Bank-grade security</span>
        </div>

        <button className="btn-continue welcome-cta" onClick={onContinue}>
          Continue onboarding
        </button>
      </div>
    </div>
  )
}
