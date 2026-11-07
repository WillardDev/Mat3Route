import { X } from 'lucide-react'
import { useLockScroll } from './BottomSheet'

/** Desktop dialog — the web counterpart of BottomSheet. */
export default function Modal({ open, onClose, title, subtitle, children, width = 'max-w-[560px]' }) {
  useLockScroll(open, onClose)
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-6" role="dialog" aria-modal="true" aria-label={title || 'Dialog'}>
      <div className="animate-fade-in absolute inset-0 bg-ink/50" onClick={onClose} />
      <div className={`animate-pop-in relative max-h-[90vh] w-full overflow-y-auto rounded-2xl bg-surface p-8 shadow-xl ${width}`}>
        {title && (
          <div className="mb-6 flex items-start justify-between gap-4">
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
