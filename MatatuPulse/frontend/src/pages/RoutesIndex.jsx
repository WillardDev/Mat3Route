import { Navigate, useOutletContext } from 'react-router-dom'
import { useRoutes } from '../api/queries'
import Logo from '../components/Logo'
import RecentRoutes from '../components/RecentRoutes'
import RouteListItem from '../components/RouteListItem'
import SearchBar from '../components/SearchBar'
import { getRecent, useIsDesktop } from '../lib/format'

/** /routes — mobile route picker (2). On web, jump straight to a route. */
export default function RoutesIndex() {
  const desktop = useIsDesktop()
  const { search, setSearch } = useOutletContext()
  const { data: routes, isLoading, error } = useRoutes(desktop ? '' : search)
  const recent = getRecent()

  if (desktop) {
    if (recent[0]) return <Navigate to={`/routes/${recent[0].id}`} replace />
    if (routes?.length) {
      const first = routes.find((r) => r.pill === 'kwama') || routes[0]
      return <Navigate to={`/routes/${first.id}`} replace />
    }
    return <p className="text-muted">Loading routes…</p>
  }

  return (
    <div className="min-h-[100dvh] bg-background px-6 pb-10 pt-6">
      <Logo />
      <h1 className="mt-8 text-[30px] font-bold leading-tight text-ink">Which route?</h1>
      <SearchBar value={search} onChange={setSearch} className="mt-5 h-14" />
      {!search && (
        <div className="mt-6">
          <RecentRoutes items={recent} />
        </div>
      )}
      <h2 className="mb-3 mt-7 text-base font-semibold text-muted">{search ? 'Matching routes' : 'All routes'}</h2>
      <div className="overflow-hidden rounded-xl border border-border bg-surface">
        {isLoading && <p className="px-6 py-6 text-sm text-muted">Loading routes…</p>}
        {error && <p className="px-6 py-6 text-sm text-alert">{error.message}</p>}
        {routes?.length === 0 && <p className="px-6 py-6 text-sm text-muted">No route matches “{search}”.</p>}
        {routes?.map((r) => (
          <RouteListItem key={r.id} route={r} />
        ))}
      </div>
    </div>
  )
}
