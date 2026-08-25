import { BankIcon, GridIcon, ChevronRight, CheckCircle } from './Icons'

const ICON = {
  bank:       { idle: <BankIcon />, active: <BankIcon color="#22C55E" /> },
  accounting: { idle: <GridIcon />, active: <GridIcon color="#22C55E" /> },
}

const LABEL = {
  bank:       'Bank connection',
  accounting: 'Accounting connection',
}

const SUBTITLE = {
  bank:       'Connect your bank now',
  accounting: 'Connect your accounting system now',
}

const INSTITUTION = {
  bank:       'Handelsbanken',
  accounting: 'Fortnox',
}

export default function ConnectionRow({ type, status, onConnect }) {
  if (status === 'connected') {
    return (
      <div className="connection-row connected fade-in">
        <div className="row-icon green">{ICON[type].active}</div>
        <div className="row-text">
          <strong>{LABEL[type]}</strong>
        </div>
        <span className="institution-name">{INSTITUTION[type]}</span>
        <CheckCircle />
      </div>
    )
  }

  if (status === 'connecting') {
    return (
      <div className="connection-row connecting">
        <div className="row-icon mist">{ICON[type].idle}</div>
        <div className="row-text">
          <strong>{LABEL[type]}</strong>
          <span>Connecting…</span>
        </div>
        <div className="spinner" />
      </div>
    )
  }

  return (
    <div
      className="connection-row"
      onClick={onConnect}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && onConnect()}
      aria-label={`Connect ${LABEL[type]}`}
    >
      <div className="row-icon mist">{ICON[type].idle}</div>
      <div className="row-text">
        <strong>{LABEL[type]}</strong>
        <span>{SUBTITLE[type]}</span>
      </div>
      <span className="row-chevron"><ChevronRight /></span>
    </div>
  )
}
