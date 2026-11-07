import { History } from 'lucide-react'
import { Link } from 'react-router-dom'
import RouteChip from './RouteChip'

export default function RecentRoutes({ items, layout = 'grid' }) {
  if (!items.length) return null
  return (
    <section>
      <h2 className="mb-3 flex items-center gap-2 text-base font-semibold text-muted md:mb-2 md:text-sm">
        <History className="h-5 w-5 md:h-4 md:w-4" /> Recent
      </h2>
      <div className={layout === 'grid' ? 'grid grid-cols-2 gap-3' : 'flex flex-col items-start gap-3'}>
        {items.map((r) => (
          <Link
            key={r.id}
            to={`/routes/${r.id}`}
            className="flex min-w-0 items-center gap-3 rounded-xl border border-border bg-surface px-4 py-3 hover:bg-background md:px-3 md:py-2"
          >
            <RouteChip number={r.number} size="sm" />
            <span className="truncate text-base font-semibold text-ink md:text-sm">{r.destination}</span>
          </Link>
        ))}
      </div>
    </section>
  )
}
