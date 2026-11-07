const PILLS = {
  maji_safi: { label: 'Maji Safi', bg: 'bg-fare-normal-tint', text: 'text-fare-normal-text', dot: 'bg-fare-normal' },
  moderate: { label: 'Moderate', bg: 'bg-fare-up-tint', text: 'text-fare-up-text', dot: 'bg-fare-up' },
  kwama: { label: 'Kwama', bg: 'bg-alert-tint', text: 'text-[#991B1B]', dot: 'bg-alert' },
}

export default function StatusPill({ status }) {
  const p = PILLS[status] || PILLS.maji_safi
  return (
    <span className={`inline-flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-medium ${p.bg} ${p.text}`}>
      <span className={`h-2 w-2 rounded-full ${p.dot}`} />
      {p.label}
    </span>
  )
}
