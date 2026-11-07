import { CircleCheck } from 'lucide-react'
import { timeAgo } from '../lib/format'
import Button from './Button'
import EventIcon from './EventIcon'

/** A commuter report (Event): type icon · stage · note · confirmations · status chip · 2 vote buttons. */
export default function IntelCard({ event, now, onVote, voting }) {
  const verified = event.status === 'verified'
  const title = [event.label, event.stage].filter(Boolean).join(' · ')
  const sub = [timeAgo(event.last_seen, now), event.type === 'fare_hike' && event.sacco].filter(Boolean).join(' · ')
  const mine = event.my_vote
  return (
    <article className="rounded-xl border border-border bg-surface p-5">
      <div className="flex items-start gap-3">
        <EventIcon type={event.type} subtype={event.subtype} />
        <div className="min-w-0 flex-1">
          <h3 className="text-base font-semibold text-ink">
            {title}
          </h3>
          <p className="text-sm text-muted">{sub}</p>
        </div>
        {verified ? (
          <span className="shrink-0 rounded-full bg-alert px-2.5 py-0.5 text-sm font-semibold text-white">Verified</span>
        ) : (
          <span className="shrink-0 rounded-full bg-pending-tint px-2.5 py-0.5 text-sm font-semibold text-pending-text">Pending</span>
        )}
      </div>

      {event.note && <p className="mt-4 text-base text-ink">“{event.note}”</p>}

      <div className="mt-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <p className="flex items-center gap-1.5 text-sm font-medium text-muted">
          <CircleCheck className={`h-4 w-4 md:hidden ${verified ? 'text-primary' : 'text-pending'}`} strokeWidth={2} />
          {event.confirmations} confirmed
          {!verified && event.needed > 0 && ` · ${event.needed} more to verify`}
        </p>
        <div className="grid grid-cols-2 gap-3 md:flex md:shrink-0">
          <Button
            variant={mine === 'still' ? 'tint' : 'secondary'}
            size="sm"
            className="h-11 md:h-10"
            aria-pressed={mine === 'still'}
            disabled={voting}
            onClick={() => onVote?.(event, 'still')}
          >
            {mine === 'still' ? 'Still accurate ✓' : 'Still accurate?'}
          </Button>
          <Button
            variant={mine === 'cleared' ? 'tint' : 'secondary'}
            size="sm"
            className="h-11 md:h-10"
            aria-pressed={mine === 'cleared'}
            disabled={voting}
            onClick={() => onVote?.(event, 'cleared')}
          >
            {mine === 'cleared' ? 'Cleared ✓' : 'Cleared?'}
          </Button>
        </div>
      </div>
    </article>
  )
}
