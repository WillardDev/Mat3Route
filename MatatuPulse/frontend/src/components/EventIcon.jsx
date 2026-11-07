import { Car, OctagonX, Shield, TrendingUp, TriangleAlert } from 'lucide-react'

export function iconFor(type, subtype) {
  if (type === 'fare_hike') return TrendingUp
  if (type === 'jam') return Car
  if (type === 'route_closed') return OctagonX
  return subtype === 'police' ? Shield : TriangleAlert
}

export default function EventIcon({ type, subtype, tone = 'tint', size = 'md' }) {
  const Icon = iconFor(type, subtype)
  const tones = {
    tint: 'bg-primary-tint text-primary',
    white: 'bg-surface text-primary',
    alert: 'bg-alert-tint text-alert',
  }
  const sizes = { md: 'h-12 w-12', sm: 'h-10 w-10' }
  return (
    <span className={`flex shrink-0 items-center justify-center rounded-full ${tones[tone]} ${sizes[size]}`}>
      <Icon className="h-5 w-5" strokeWidth={2} />
    </span>
  )
}
