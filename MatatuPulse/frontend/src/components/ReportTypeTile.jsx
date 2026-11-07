import EventIcon from './EventIcon'

export default function ReportTypeTile({ type, subtype, label, selected, onSelect }) {
  return (
    <button
      type="button"
      onClick={onSelect}
      aria-pressed={selected}
      className={`flex min-h-[112px] flex-col items-center justify-center gap-3 rounded-xl px-2 py-4 text-center text-base font-semibold text-ink transition ${
        selected ? 'border-2 border-primary bg-primary-tint' : 'border border-border bg-surface hover:bg-background'
      }`}
    >
      <EventIcon type={type} subtype={subtype} tone={selected ? 'white' : 'tint'} />
      <span className="leading-tight">{label}</span>
    </button>
  )
}
