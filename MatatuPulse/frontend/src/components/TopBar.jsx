import { ArrowLeft, Bell } from 'lucide-react'
import RouteChip from './RouteChip'

/** Sticky top bar: back · route chip · name + subtitle · alerts bell (on/off). */
export default function TopBar({ route, subtitle, onBack, subscribed, onToggleBell, bellBusy }) {
  return (
    <header className="sticky top-0 z-20 border-b border-border bg-surface">
      <div className="flex items-center gap-3 px-4 py-3">
        {onBack && (
          <button type="button" onClick={onBack} aria-label="Back to routes" className="-ml-1 rounded-full p-1 text-ink hover:bg-background">
            <ArrowLeft className="h-6 w-6" />
          </button>
        )}
        <RouteChip number={route.number} />
        <div className="min-w-0 flex-1">
          <h1 className="truncate text-base font-semibold text-ink">{route.name}</h1>
          {subtitle && <p className="truncate text-xs font-medium text-muted">{subtitle}</p>}
        </div>
        {onToggleBell && <BellButton on={subscribed} onClick={onToggleBell} busy={bellBusy} />}
      </div>
    </header>
  )
}

export function BellButton({ on, onClick, busy }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={busy}
      aria-pressed={on}
      aria-label={on ? 'Alerts on — turn off' : 'Turn on alerts for this route'}
      className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-full transition ${
        on ? 'bg-primary-tint text-primary' : 'border border-border bg-surface text-muted hover:text-ink'
      }`}
    >
      <Bell className="h-5 w-5" fill={on ? 'currentColor' : 'none'} fillOpacity={on ? 0.15 : 0} />
    </button>
  )
}
