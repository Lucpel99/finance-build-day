export function LunaLogo() {
  return (
    <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
      <circle cx="14" cy="14" r="14" fill="#2F3442"/>
      <path
        d="M18 14C18 17.314 15.314 20 12 20C8.686 20 6 17.314 6 14C6 10.686 8.686 8 12 8C10.5 9.5 10 11.5 10.2 14C10.4 16.5 11.5 18.5 13.5 19.2C15.5 19.9 17.6 18 18 14Z"
        fill="#F4D04E"
      />
      <circle cx="18" cy="9" r="1.5" fill="#F4D04E"/>
    </svg>
  )
}

export function BankIcon({ color = '#2F3442' }) {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
      <path d="M3 10h18M3 10l9-7 9 7M5 10v8m4-8v8m4-8v8m4-8v8M3 18h18"
        stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  )
}

export function GridIcon({ color = '#2F3442' }) {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
      <rect x="3" y="3" width="7" height="7" rx="1.5" stroke={color} strokeWidth="2"/>
      <rect x="14" y="3" width="7" height="7" rx="1.5" stroke={color} strokeWidth="2"/>
      <rect x="3" y="14" width="7" height="7" rx="1.5" stroke={color} strokeWidth="2"/>
      <rect x="14" y="14" width="7" height="7" rx="1.5" stroke={color} strokeWidth="2"/>
    </svg>
  )
}

export function ChevronRight() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
      <path d="M9 18l6-6-6-6" stroke="#9CA3AF" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  )
}

export function CheckCircle({ size = 24 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="10" fill="#22C55E"/>
      <path d="M8 12l3 3 5-5" stroke="white" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  )
}

export function MoonIcon({ size = 18 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 20 20" fill="none">
      <path d="M17 11.5A7.5 7.5 0 0 1 8.5 3a7.5 7.5 0 1 0 8.5 8.5z" fill="#2F3442"/>
    </svg>
  )
}

export function WarningIcon({ size = 28 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <path
        d="M12 9v4M12 17h.01M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"
        stroke="#F4D04E" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
      />
    </svg>
  )
}

export function QuestionIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2"/>
      <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3M12 17h.01"
        stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
    </svg>
  )
}

export function SparkleIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" width="1em" height="1em">
      <path d="M12 2l2.09 7.91L22 12l-7.91 2.09L12 22l-2.09-7.91L2 12l7.91-2.09L12 2z"/>
    </svg>
  )
}

export function BigCheckIcon() {
  return (
    <svg width="36" height="36" viewBox="0 0 24 24" fill="none">
      <path d="M5 13l4 4L19 7" stroke="#22C55E" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  )
}
