import { ArrowDown, ArrowUp, CircleCheck } from 'lucide-react'
import { timeAgo } from '../lib/format'

/** Fare up (amber) · Normal (green "Usual fare") · Pending (grey "KES 90?", under 3 reports). */
export default function SaccoFareCard({ sacco, now }) {
  const { name, fare, usual_fare: usual, state, delta, reporters, updated_at: updated } = sacco
  const up = state === 'up' || state === 'down'
  return (
    <div className="flex items-start justify-between gap-4 rounded-xl border border-border bg-surface px-5 py-4">
      <div className="min-w-0">
        <p className="text-base font-semibold text-ink">{name}</p>
        {up && (
          <>
            <div className="mt-1 flex items-center gap-2">
              <span className="text-sm text-muted line-through">KES {usual}</span>
              <span className="inline-flex items-center gap-0.5 rounded-full bg-fare-up-tint px-2 py-0.5 text-xs font-semibold text-fare-up-text">
                {delta >= 0 ? <ArrowUp className="h-3 w-3" strokeWidth={2.5} /> : <ArrowDown className="h-3 w-3" strokeWidth={2.5} />}
                {delta >= 0 ? `+${delta}` : delta}
              </span>
            </div>
            <p className="mt-2 flex items-center gap-1.5 text-xs font-medium text-muted">
              <CircleCheck className="h-4 w-4 text-primary" strokeWidth={2} />
              Verified by {reporters} commuters · {timeAgo(updated, now)}
            </p>
          </>
        )}
        {state === 'normal' && (
          <p className="mt-1 flex items-center gap-1.5 text-sm font-semibold text-fare-normal-text">
            <span className="h-2 w-2 rounded-full bg-fare-normal" /> Usual fare
          </p>
        )}
        {state === 'pending' && (
          <p className="mt-1 flex items-center gap-1.5 text-sm font-semibold text-pending-text">
            <span className="h-2 w-2 rounded-full bg-pending" /> Pending · {reporters} {reporters === 1 ? 'report' : 'reports'}
          </p>
        )}
      </div>
      <p
        className={`shrink-0 whitespace-nowrap text-28 tabular-nums ${
          up ? 'text-fare-up' : state === 'pending' ? 'text-pending-text' : 'text-ink'
        }`}
      >
        KES {fare}
        {state === 'pending' ? '?' : ''}
      </p>
    </div>
  )
}
