import { Bell, Plus } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useCreateReport, useRoute, useSubscribe, useVote } from '../api/queries'
import AlertBanner from '../components/AlertBanner'
import BottomSheet from '../components/BottomSheet'
import Button from '../components/Button'
import IntelCard from '../components/IntelCard'
import Modal from '../components/Modal'
import ReportForm from '../components/ReportForm'
import ReportSuccess from '../components/ReportSuccess'
import RouteChip from '../components/RouteChip'
import SaccoFareCard from '../components/SaccoFareCard'
import TopBar from '../components/TopBar'
import { pushRecent, timeAgo, useIsDesktop, useNow } from '../lib/format'

export default function RouteDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const desktop = useIsDesktop()
  const now = useNow()
  const { data: route, isLoading, error } = useRoute(id)
  const voteMut = useVote(id)
  const reportMut = useCreateReport(id)
  const subMut = useSubscribe(id)
  const [reportOpen, setReportOpen] = useState(false)
  const [result, setResult] = useState(null)
  const [showBannerCard, setShowBannerCard] = useState(false)

  useEffect(() => {
    if (route) pushRecent(route)
  }, [route])
  useEffect(() => {
    setShowBannerCard(false)
  }, [id])

  const closeReport = useCallback(() => {
    setReportOpen(false)
    setResult(null)
    reportMut.reset()
  }, [reportMut])

  if (isLoading) return <DetailSkeleton desktop={desktop} />
  if (error || !route)
    return (
      <div className="p-6">
        <p className="text-alert">{error?.status === 404 ? 'That route does not exist.' : error?.message || 'Could not load route.'}</p>
        <Button variant="secondary" className="mt-4" onClick={() => navigate('/routes')}>Back to routes</Button>
      </div>
    )

  const updated = route.updated_at ? `updated ${timeAgo(route.updated_at, now)}` : null
  const onVote = (event, kind) => voteMut.mutate({ event, kind })
  const submit = (payload) => reportMut.mutate(payload, { onSuccess: setResult })
  const reportError = reportMut.error?.message

  const bannerCard = showBannerCard && route.banner?.event && (
    <IntelCard event={route.banner.event} now={now} onVote={onVote} />
  )

  const saccos = (
    <section>
      <div className="mb-4 flex items-baseline justify-between gap-4">
        <h2 className="text-xl font-semibold text-ink">Saccos on this route</h2>
        <span className="truncate text-sm text-muted md:hidden">{route.name}</span>
      </div>
      <div className="space-y-4">
        {route.saccos.map((s) => (
          <SaccoFareCard key={s.id} sacco={s} now={now} />
        ))}
      </div>
    </section>
  )

  const intel = (
    <section>
      <h2 className="mb-4 text-xl font-semibold text-ink">Latest from commuters</h2>
      {route.events.length === 0 ? (
        <div className="rounded-xl border border-dashed border-border bg-surface px-5 py-8 text-center">
          <p className="font-semibold text-ink">All quiet on Route {route.number}</p>
          <p className="mt-1 text-sm text-muted">No reports in the last hour. Seen something? Tap Report.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {route.events.map((e) => (
            <IntelCard key={e.id} event={e} now={now} onVote={onVote} />
          ))}
        </div>
      )}
    </section>
  )

  const reportUi = desktop ? (
    <Modal
      open={reportOpen}
      onClose={closeReport}
      title={result ? null : "What's happening?"}
      subtitle={`Route ${route.number} · ${route.name}`}
      width={result ? 'max-w-[480px]' : 'max-w-[560px]'}
    >
      {result ? (
        <ReportSuccess result={result} routeNumber={route.number} onDone={closeReport} desktop />
      ) : (
        <ReportForm route={route} onSubmit={submit} onCancel={closeReport} submitting={reportMut.isPending} error={reportError} desktop />
      )}
    </Modal>
  ) : (
    <BottomSheet
      open={reportOpen}
      onClose={closeReport}
      title={result ? null : "What's happening?"}
      subtitle={`Route ${route.number} · ${route.name}`}
    >
      {result ? (
        <ReportSuccess result={result} routeNumber={route.number} onDone={closeReport} />
      ) : (
        <ReportForm route={route} onSubmit={submit} submitting={reportMut.isPending} error={reportError} />
      )}
    </BottomSheet>
  )

  if (desktop) {
    return (
      <div>
        <div className="flex items-start gap-4">
          <RouteChip number={route.number} size="lg" />
          <div className="min-w-0 flex-1">
            <h1 className="text-[30px] font-semibold leading-[36px] text-ink">{route.name}</h1>
            <p className="mt-0.5 text-base text-muted">
              {[`via ${route.via}`, `${route.saccos.length} saccos`, updated].filter(Boolean).join(' · ')}
            </p>
          </div>
          <Button
            variant={route.subscribed ? 'tint' : 'secondary'}
            onClick={() => subMut.mutate()}
            aria-pressed={route.subscribed}
            className="px-5"
          >
            <Bell className="h-5 w-5" /> {route.subscribed ? 'Alerts on' : 'Alerts off'}
          </Button>
          <Button onClick={() => setReportOpen(true)} className="px-5">
            <Plus className="h-5 w-5" /> Report
          </Button>
        </div>
        {route.banner && (
          <div className="mt-6 space-y-3">
            <AlertBanner banner={route.banner} now={now} inline onClick={() => setShowBannerCard((v) => !v)} />
            {bannerCard}
          </div>
        )}
        <div className="mt-8 grid gap-8 lg:grid-cols-2 lg:gap-6">
          {saccos}
          {intel}
        </div>
        {reportUi}
      </div>
    )
  }

  return (
    <div className="min-h-[100dvh] bg-background pb-28">
      <TopBar
        route={route}
        subtitle={[`via ${route.via}`, updated].filter(Boolean).join(' · ')}
        onBack={() => navigate('/routes')}
        subscribed={route.subscribed}
        onToggleBell={() => subMut.mutate()}
      />
      <div className="space-y-8 px-4 pt-5">
        {route.banner && (
          <div className="space-y-3">
            <AlertBanner banner={route.banner} now={now} onClick={() => setShowBannerCard((v) => !v)} />
            {bannerCard}
          </div>
        )}
        {saccos}
        {intel}
      </div>
      <Button
        onClick={() => setReportOpen(true)}
        className="fixed bottom-[max(1.5rem,env(safe-area-inset-bottom))] right-4 z-30 h-14 rounded-full px-6 text-lg shadow-lg"
      >
        <Plus className="h-6 w-6" /> Report
      </Button>
      {reportUi}
    </div>
  )
}

function DetailSkeleton({ desktop }) {
  return (
    <div className={`animate-pulse space-y-4 ${desktop ? '' : 'p-4'}`} aria-label="Loading route">
      <div className="h-14 rounded-xl bg-border/60" />
      <div className="h-16 rounded-xl bg-alert-tint" />
      <div className="h-24 rounded-xl bg-border/60" />
      <div className="h-24 rounded-xl bg-border/60" />
    </div>
  )
}
