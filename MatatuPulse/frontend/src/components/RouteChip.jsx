export default function RouteChip({ number, size = 'md', tone = 'solid', className = '' }) {
  const sizes = {
    sm: 'h-7 min-w-[44px] px-2.5 text-sm',
    md: 'h-8 min-w-[48px] px-3 text-base',
    lg: 'h-9 min-w-[60px] px-4 text-xl',
  }
  const tones = {
    solid: 'bg-primary text-white',
    tint: 'bg-primary-tint text-primary',
  }
  return (
    <span className={`inline-flex shrink-0 items-center justify-center rounded-full font-semibold tabular-nums ${sizes[size]} ${tones[tone]} ${className}`}>
      {number}
    </span>
  )
}
