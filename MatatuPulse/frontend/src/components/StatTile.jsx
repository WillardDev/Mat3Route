export default function StatTile({ label, value, highlight, muted }) {
  return (
    <div className={`rounded-xl bg-surface p-4 md:p-5 ${highlight ? 'border-2 border-primary' : 'border border-border'}`}>
      <p className="text-sm text-muted">{label}</p>
      <p className={`mt-1 text-28 tabular-nums ${highlight ? 'text-primary' : muted ? 'text-pending-text' : 'text-ink'}`}>
        {value}
      </p>
    </div>
  )
}
