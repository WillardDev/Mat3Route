import { ChevronDown } from 'lucide-react'

const FIELD =
  'flex h-12 w-full items-center rounded-xl border border-border bg-surface px-4 text-base text-ink transition focus-within:border-2 focus-within:border-primary focus-within:px-[15px]'

export function Label({ children, optional, htmlFor }) {
  return (
    <label htmlFor={htmlFor} className="mb-2 block text-sm font-semibold text-ink">
      {children}
      {optional && <span className="font-normal text-muted"> (optional)</span>}
    </label>
  )
}

/** Plain field. `prefix` renders fixed text before the value (e.g. "+254" or "KES"). */
export default function TextInput({ label, optional, id, prefix, divider, className = '', inputClassName = '', ...props }) {
  return (
    <div className={className}>
      {label && <Label optional={optional} htmlFor={id}>{label}</Label>}
      <div className={FIELD}>
        {prefix && (
          <span className={`shrink-0 ${divider ? 'mr-4 border-r border-border pr-4 font-semibold text-ink' : 'mr-3 text-muted'}`}>
            {prefix}
          </span>
        )}
        <input id={id} className={`min-w-0 flex-1 bg-transparent outline-none placeholder:text-pending ${inputClassName}`} {...props} />
      </div>
    </div>
  )
}

export function PhoneInput(props) {
  return <TextInput prefix="+254" divider type="tel" inputMode="numeric" autoComplete="tel-national" placeholder="712 345 678" {...props} />
}

export function Select({ label, optional, id, options, placeholder, className = '', ...props }) {
  return (
    <div className={className}>
      {label && <Label optional={optional} htmlFor={id}>{label}</Label>}
      <div className={`${FIELD} relative`}>
        <select id={id} className="min-w-0 flex-1 appearance-none truncate bg-transparent pr-6 outline-none" {...props}>
          {placeholder !== undefined && <option value="">{placeholder}</option>}
          {options.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
        <ChevronDown className="pointer-events-none absolute right-4 h-5 w-5 text-muted" strokeWidth={2} />
      </div>
    </div>
  )
}

export function TextArea({ label, optional, id, className = '', ...props }) {
  return (
    <div className={className}>
      {label && <Label optional={optional} htmlFor={id}>{label}</Label>}
      <textarea
        id={id}
        rows={2}
        className="block w-full resize-none rounded-xl border border-border bg-surface px-4 py-3 text-base text-ink outline-none transition placeholder:text-pending focus:border-2 focus:border-primary focus:px-[15px] focus:py-[11px]"
        {...props}
      />
    </div>
  )
}
