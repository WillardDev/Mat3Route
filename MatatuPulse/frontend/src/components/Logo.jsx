import { Activity } from 'lucide-react'

export function LogoMark({ size = 'md', inverse }) {
  const sizes = { sm: 'h-9 w-9 rounded-[10px]', md: 'h-10 w-10 rounded-xl', lg: 'h-16 w-16 rounded-2xl' }
  const icon = { sm: 'h-5 w-5', md: 'h-6 w-6', lg: 'h-8 w-8' }
  return (
    <span className={`flex shrink-0 items-center justify-center ${sizes[size]} ${inverse ? 'bg-surface text-primary' : 'bg-primary text-white'}`}>
      <Activity className={icon[size]} strokeWidth={2.25} />
    </span>
  )
}

export default function Logo({ inverse, size = 'md' }) {
  return (
    <span className="inline-flex items-center gap-3">
      <LogoMark inverse={inverse} size={size} />
      <span className={`text-xl font-bold ${inverse ? 'text-white' : 'text-ink'}`}>MatatuPulse</span>
    </span>
  )
}
