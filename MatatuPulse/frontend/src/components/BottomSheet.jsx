import { X } from 'lucide-react'
import { useEffect } from 'react'

/** Fixed bottom sheet: rounded-t-xl, handle, title + close. */
export default function BottomSheet({ open, onClose, title, subtitle, children }) {
  useLockScroll(open, onClose)
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50" role="dialog" aria-modal="true" aria-label={title || 'Sheet'}>
      <div className="animate-fade-in absolute inset-0 bg-ink/50" onClick={onClose} />
      <div className="animate-sheet-up absolute inset-x-0 bottom-0 max-h-[92vh] overflow-y-auto rounded-t-[20px] bg-surface px-4 pb-[max(1.5rem,env(safe-area-inset-bottom))] pt-3">
        <div className="mx-auto mb-4 h-1 w-10 rounded-full bg-border" />
        {title && (
          <div className="mb-5 flex items-start justify-between gap-4">
            <div>
              <h2 className="text-xl font-semibold text-ink">{title}</h2>
              {subtitle && <p className="mt-0.5 text-sm font-medium text-muted">{subtitle}</p>}
            </div>
            <button type="button" onClick={onClose} aria-label="Close" className="rounded-full p-1 text-muted hover:text-ink">
              <X className="h-6 w-6" />
            </button>
          </div>
        )}
        {children}
      </div>
    </div>
  )
}

export function useLockScroll(open, onClose) {
  useEffect(() => {
    if (!open) return
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    const onKey = (e) => e.key === 'Escape' && onClose?.()
    window.addEventListener('keydown', onKey)
    return () => {
      document.body.style.overflow = prev
      window.removeEventListener('keydown', onKey)
    }
  }, [open, onClose])
}
