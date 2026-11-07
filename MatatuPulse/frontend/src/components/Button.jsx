const VARIANTS = {
  primary: 'bg-primary text-white hover:bg-primary-dark disabled:bg-primary/50',
  secondary: 'bg-surface text-primary border border-border hover:bg-background disabled:text-muted',
  tint: 'bg-primary-tint text-primary hover:bg-primary-tint/70',
  ghost: 'text-primary hover:bg-primary-tint/50',
}
const SIZES = {
  md: 'h-12 px-4 text-base rounded-xl',
  sm: 'h-9 px-3 text-sm rounded-xl',
}

export default function Button({ variant = 'primary', size = 'md', block, className = '', children, ...props }) {
  return (
    <button
      type="button"
      className={`inline-flex items-center justify-center gap-2 font-semibold transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 disabled:cursor-not-allowed ${VARIANTS[variant]} ${SIZES[size]} ${block ? 'w-full' : ''} ${className}`}
      {...props}
    >
      {children}
    </button>
  )
}
