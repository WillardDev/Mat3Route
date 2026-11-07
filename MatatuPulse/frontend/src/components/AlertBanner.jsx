import { ChevronRight, TriangleAlert } from 'lucide-react'
import { timeAgo } from '../lib/format'

/** Red banner — only ever used for verified alerts. */
export default function AlertBanner({ banner, now, onClick, inline }) {
  if (!banner) return null
  const meta = `Verified · ${banner.reports} reports · ${timeAgo(banner.verified_at, now)}`
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex w-full items-center gap-3 rounded-xl bg-alert px-4 py-3 text-left text-white transition hover:bg-[#C81E1E] md:py-4"
    >
      <TriangleAlert className="h-6 w-6 shrink-0" strokeWidth={2} />
      {inline ? (
        <span className="min-w-0 flex-1 truncate text-base">
          <span className="font-semibold">{banner.title}</span>
          <span className="text-white/90"> · {meta}</span>
        </span>
      ) : (
        <span className="min-w-0 flex-1">
          <span className="block text-base font-semibold">{banner.title}</span>
          <span className="block text-xs font-medium text-white/90">{meta}</span>
        </span>
      )}
      <ChevronRight className="h-5 w-5 shrink-0" />
    </button>
  )
}
