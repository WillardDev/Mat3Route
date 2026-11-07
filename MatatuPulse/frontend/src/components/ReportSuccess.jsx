import { CircleCheck } from 'lucide-react'
import Button from './Button'

const VERIFY_AT = 3

function describe(event) {
  if (event.type === 'fare_hike') return `The fare hike${event.sacco ? ` on ${event.sacco}` : ''}`
  if (event.type === 'jam') return `The jam${event.stage ? ` at ${event.stage}` : ''}`
  if (event.type === 'route_closed') return `The closure${event.stage ? ` at ${event.stage}` : ''}`
  return `The ${event.subtype === 'police' ? 'police check' : 'accident'}${event.stage ? ` at ${event.stage}` : ''}`
}

export default function ReportSuccess({ result, routeNumber, onDone, desktop }) {
  const { event, others_count: others, merged_count: merged, verified_now: verifiedNow } = result
  const count = event.confirmations
  const headline =
    others === 0 ? "Thanks — you're the first to report this" : `Thanks — ${others} other${others === 1 ? '' : 's'} reported this`
  let body
  if (verifiedNow) body = `That makes ${count}. ${describe(event)} is now verified for Route ${routeNumber}.`
  else if (event.status === 'verified') body = `${describe(event)} is already verified. Your report keeps it fresh.`
  else
    body = `${event.needed} more ${event.needed === 1 ? 'commuter' : 'commuters'} to verify. We'll alert Route ${routeNumber} once ${VERIFY_AT} confirm.`

  return (
    <div className="flex flex-col items-center px-2 pt-2 text-center">
      <span className="flex h-[72px] w-[72px] items-center justify-center rounded-full bg-primary-tint text-primary">
        <CircleCheck className="h-9 w-9" strokeWidth={2.25} />
      </span>
      <h2 className="mt-6 text-xl font-semibold text-ink">{headline}</h2>
      <p className="mt-2 text-base text-muted">{body}</p>
      <div className="mt-6 w-full rounded-xl bg-background px-4 py-4">
        <div className="flex gap-2" aria-hidden="true">
          {Array.from({ length: VERIFY_AT }).map((_, i) => (
            <span key={i} className={`h-2 flex-1 rounded-full ${i < count ? 'bg-primary' : 'bg-border'}`} />
          ))}
        </div>
        <p className="mt-3 text-sm font-medium text-muted">
          {Math.min(count, VERIFY_AT)} of {VERIFY_AT} confirmations
          {merged > 0 && ` · merged with ${merged} earlier report${merged === 1 ? '' : 's'}`}
        </p>
      </div>
      <Button block className="mt-6" onClick={onDone}>
        {desktop ? `Back to Route ${routeNumber}` : 'Done'}
      </Button>
    </div>
  )
}
