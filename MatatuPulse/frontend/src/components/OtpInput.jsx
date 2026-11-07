import { useEffect, useRef } from 'react'

/** 4 × 64px boxes. Filled = ink border, active = teal 2px, empty = light border. */
export default function OtpInput({ value, onChange, length = 4, autoFocus, disabled }) {
  const refs = useRef([])
  const digits = value.split('')
  const active = Math.min(value.length, length - 1)

  // Focus always follows the first empty box.
  const mounted = useRef(false)
  useEffect(() => {
    if (!mounted.current) {
      mounted.current = true
      if (!autoFocus) return
    }
    const el = refs.current[Math.min(value.length, length - 1)]
    if (el && document.activeElement !== el) el.focus()
  }, [value, length, autoFocus])

  const setAt = (i, ch) => onChange((value.slice(0, Math.min(i, value.length)) + ch).slice(0, length))

  return (
    <div className="flex gap-4" onPaste={(e) => {
      const text = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, length)
      if (text) { e.preventDefault(); onChange(text) }
    }}>
      {Array.from({ length }).map((_, i) => {
        const filled = !!digits[i]
        const isActive = i === active && !filled
        return (
          <input
            key={i}
            ref={(el) => (refs.current[i] = el)}
            value={digits[i] || ''}
            inputMode="numeric"
            autoComplete={i === 0 ? 'one-time-code' : 'off'}
            maxLength={1}
            disabled={disabled}
            aria-label={`Digit ${i + 1}`}
            onFocus={(e) => e.target.select()}
            onChange={(e) => {
              const ch = e.target.value.replace(/\D/g, '').slice(-1)
              if (ch) setAt(i, ch)
            }}
            onKeyDown={(e) => {
              if (e.key === 'Backspace') {
                e.preventDefault()
                const cut = filled ? i : i - 1
                if (cut >= 0) onChange(value.slice(0, cut))
              }
            }}
            className={`h-16 w-16 min-w-0 flex-1 rounded-xl bg-surface text-center text-28 text-ink outline-none sm:flex-none ${
              filled ? 'border border-ink' : isActive ? 'border-2 border-primary' : 'border border-border'
            }`}
          />
        )
      })}
    </div>
  )
}
