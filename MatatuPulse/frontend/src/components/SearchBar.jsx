import { Search, X } from 'lucide-react'

export default function SearchBar({ value, onChange, placeholder = 'Search route, stage or sacco', className = '', tone = 'white' }) {
  return (
    <div className={`flex h-12 items-center gap-3 rounded-xl border border-border px-4 focus-within:border-primary ${tone === 'muted' ? 'bg-background' : 'bg-surface'} ${className}`}>
      <Search className="h-5 w-5 shrink-0 text-muted" strokeWidth={2} />
      <input
        type="search"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        aria-label={placeholder}
        className="min-w-0 flex-1 bg-transparent text-base text-ink outline-none placeholder:text-muted [&::-webkit-search-cancel-button]:hidden"
      />
      {value && (
        <button type="button" aria-label="Clear search" onClick={() => onChange('')} className="text-muted hover:text-ink">
          <X className="h-4 w-4" />
        </button>
      )}
    </div>
  )
}
