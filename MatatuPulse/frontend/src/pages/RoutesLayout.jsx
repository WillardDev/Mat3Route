import { LogOut } from 'lucide-react'
import { useState } from 'react'
import { Link, Outlet, useParams } from 'react-router-dom'
import { setAuth } from '../api/client'
import { useRoutes } from '../api/queries'
import Logo from '../components/Logo'
import RecentRoutes from '../components/RecentRoutes'
import RouteListItem from '../components/RouteListItem'
import SearchBar from '../components/SearchBar'
import { getRecent, useIsDesktop } from '../lib/format'
import { useAuth } from '../lib/useAuth'

/** Mobile: each page is full screen. Web (md+): header + routes sidebar + main panel (W2–3). */
export default function RoutesLayout() {
  const desktop = useIsDesktop()
  const [search, setSearch] = useState('')
  const ctx = { search, setSearch }
  if (!desktop) return <Outlet context={ctx} />
  return <DesktopShell ctx={ctx} />
}

function DesktopShell({ ctx }) {
  const { id } = useParams()
  const auth = useAuth()
  const { data: routes, isLoading } = useRoutes(ctx.search)
  const recent = getRecent()

  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-20 border-b border-border bg-surface">
        <div className="flex h-16 items-center gap-6 px-6">
          <Link to="/routes" aria-label="MatatuPulse home"><Logo /></Link>
          <SearchBar value={ctx.search} onChange={ctx.setSearch} tone="muted" className="h-11 w-full max-w-[480px]" />
          <div className="ml-auto flex items-center gap-4">
            <Link to="/signal" className="text-sm font-semibold text-primary hover:underline">Signal panel</Link>
            <a
              href="/live-map.html"
              className="text-sm font-semibold text-primary hover:underline"
              title="Live map"
            >Live Map</a>
            <span className="text-sm tabular-nums text-muted">{auth?.user?.phone_masked}</span>
            <button
              type="button"
              onClick={() => setAuth(null)}
              aria-label="Sign out"
              title="Sign out"
              className="rounded-full p-2 text-muted hover:bg-background hover:text-ink"
            >
              <LogOut className="h-5 w-5" />
            </button>
          </div>
        </div>
      </header>
      <div className="mx-auto grid max-w-[1440px] grid-cols-[minmax(240px,280px)_1fr] gap-6 px-6 py-6 lg:gap-8">
        <aside className="space-y-6">
          <RecentRoutes items={recent} layout="stack" />
          <section>
            <h2 className="mb-2 text-sm font-semibold text-muted">{ctx.search ? 'Matching routes' : 'All routes'}</h2>
            <div className="overflow-hidden rounded-xl border border-border bg-surface">
              {isLoading && <p className="px-5 py-6 text-sm text-muted">Loading routes…</p>}
              {routes?.length === 0 && <p className="px-5 py-6 text-sm text-muted">No route matches “{ctx.search}”.</p>}
              {routes?.map((r) => (
                <RouteListItem key={r.id} route={r} selected={String(r.id) === id} />
              ))}
            </div>
          </section>
        </aside>
        <main className="min-w-0">
          <Outlet context={ctx} />
        </main>
      </div>
    </div>
  )
}
