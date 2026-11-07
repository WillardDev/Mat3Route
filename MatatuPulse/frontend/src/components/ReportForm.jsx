import { useState } from 'react'
import Button from './Button'
import ReportTypeTile from './ReportTypeTile'
import TextInput, { Select, TextArea } from './TextInput'

export const REPORT_TYPES = [
  { type: 'fare_hike', label: 'Fare hike' },
  { type: 'jam', label: 'Jam / Stall' },
  { type: 'accident_police', subtype: 'police', label: 'Accident / Police' },
  { type: 'route_closed', label: 'Route closed' },
]

/** Shared by the mobile bottom sheet and the web dialog. */
export default function ReportForm({ route, onSubmit, onCancel, submitting, error, desktop }) {
  const [type, setType] = useState('fare_hike')
  const [subtype, setSubtype] = useState('accident')
  const [sacco, setSacco] = useState('')
  const [fare, setFare] = useState('')
  const [note, setNote] = useState('')
  const isFare = type === 'fare_hike'
  const fareOk = !isFare || (Number(fare) >= 10 && Number(fare) <= 999)

  const submit = (e) => {
    e.preventDefault()
    if (!fareOk || submitting) return
    onSubmit({
      route: route.id,
      type,
      subtype: type === 'accident_police' ? subtype : undefined,
      sacco: isFare && sacco ? Number(sacco) : undefined,
      fare: isFare ? Number(fare) : undefined,
      note: note.trim() || undefined,
    })
  }

  return (
    <form onSubmit={submit} className="space-y-6">
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4 md:gap-3">
        {REPORT_TYPES.map((t) => (
          <ReportTypeTile key={t.type} {...t} selected={type === t.type} onSelect={() => setType(t.type)} />
        ))}
      </div>

      {type === 'accident_police' && (
        <div className="flex gap-2" role="radiogroup" aria-label="Accident or police">
          {[
            ['accident', 'Accident'],
            ['police', 'Police check'],
          ].map(([v, l]) => (
            <button
              key={v}
              type="button"
              role="radio"
              aria-checked={subtype === v}
              onClick={() => setSubtype(v)}
              className={`h-9 rounded-full px-4 text-sm font-semibold ${
                subtype === v ? 'bg-primary text-white' : 'border border-border bg-surface text-ink'
              }`}
            >
              {l}
            </button>
          ))}
        </div>
      )}

      {isFare && (
        <div className="grid grid-cols-2 gap-4 md:grid-cols-[1fr_auto] md:gap-6">
          <Select
            id="sacco"
            label="Sacco"
            optional
            value={sacco}
            onChange={(e) => setSacco(e.target.value)}
            placeholder="Any sacco"
            options={route.saccos.map((s) => ({ value: s.id, label: s.name }))}
          />
          <TextInput
            id="fare"
            label="New fare"
            prefix="KES"
            inputMode="numeric"
            placeholder="100"
            value={fare}
            onChange={(e) => setFare(e.target.value.replace(/\D/g, '').slice(0, 3))}
            className="md:w-[220px]"
            inputClassName="font-medium"
            required
          />
        </div>
      )}

      <TextArea
        id="note"
        label="Note"
        optional
        value={note}
        onChange={(e) => setNote(e.target.value)}
        placeholder={isFare ? 'fare ni 100 sasa Odeon' : 'Where exactly? e.g. imejam Kasarani'}
        maxLength={280}
      />

      {error && <p className="rounded-xl bg-alert-tint px-4 py-3 text-sm font-medium text-[#991B1B]">{error}</p>}

      {desktop ? (
        <div className="flex justify-end gap-4">
          <Button variant="secondary" onClick={onCancel}>Cancel</Button>
          <Button type="submit" disabled={!fareOk || submitting} className="px-10">
            {submitting ? 'Sending…' : 'Submit report'}
          </Button>
        </div>
      ) : (
        <Button type="submit" block disabled={!fareOk || submitting}>
          {submitting ? 'Sending…' : 'Submit report'}
        </Button>
      )}
    </form>
  )
}
