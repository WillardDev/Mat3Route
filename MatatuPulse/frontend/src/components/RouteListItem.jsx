import { Link } from 'react-router-dom'
import RouteChip from './RouteChip'
import StatusPill from './StatusPill'

export default function RouteListItem({ route, selected }) {
  const sub = [`via ${route.via}`, route.alert_count ? `${route.alert_count} alert${route.alert_count > 1 ? 's' : ''}` : null]
    .filter(Boolean)
    .join(' · ')
  return (
    <Link
      to={`/routes/${route.id}`}
      aria-current={selected ? 'page' : undefined}
      className={`flex items-center gap-4 border-b border-border px-6 py-4 last:border-b-0 transition md:gap-3 md:px-4 md:py-3 ${
        selected ? 'border-l-4 border-l-primary bg-primary-tint pl-5 md:pl-3' : 'bg-surface hover:bg-background'
      }`}
    >
      {selected ? (
        <span className="w-14 shrink-0 text-center text-xl font-semibold text-primary md:w-12 md:text-base">{route.number}</span>
      ) : (
        <RouteChip number={route.number} tone="tint" size="md" className="w-14 md:w-12" />
      )}
      <span className="min-w-0 flex-1">
        <span className="block text-base font-semibold leading-snug text-ink md:text-sm">{route.name}</span>
        <span className="block text-sm text-muted md:text-xs">{sub}</span>
      </span>
      <StatusPill status={route.pill} />
    </Link>
  )
}
