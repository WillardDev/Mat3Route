import { CircleCheck, Plus, TrendingUp } from 'lucide-react'
import Logo from '../components/Logo'

/** Web: teal story panel on the left, white card on the right (W1a/W1b). Mobile: just children. */
export default function AuthLayout({ children }) {
  return (
    <div className="min-h-[100dvh] bg-background md:grid md:grid-cols-2">
      <aside className="hidden flex-col justify-between bg-primary px-12 py-12 text-white md:flex">
        <Logo inverse />
        <div>
          <h1 className="text-[32px] font-bold leading-[40px] tracking-tight lg:text-[36px] lg:leading-[44px]">Know the fare before you board.</h1>
          <p className="mt-5 max-w-[460px] text-lg text-primary-tint">
            Signal from the noise. Live fares and verified alerts for your route, from commuters on it.
          </p>
          <ul className="mt-6 space-y-4 text-lg">
            <li className="flex items-center gap-3"><TrendingUp className="h-5 w-5" /> Current fares for every sacco on your route</li>
            <li className="flex items-center gap-3"><CircleCheck className="h-5 w-5" /> Alerts verified once 3 commuters confirm</li>
            <li className="flex items-center gap-3"><Plus className="h-5 w-5" /> Report a fare hike or jam in two taps</li>
          </ul>
        </div>
        <p className="text-xs font-medium text-primary-tint">Nairobi · Kencom · Ambassadeur · Odeon · Ngara · Kasarani · Githurai 45</p>
      </aside>
      <main className="flex min-h-[100dvh] flex-col md:items-center md:justify-center md:px-10">{children}</main>
    </div>
  )
}

export function AuthCard({ children }) {
  return (
    <div className="w-full md:max-w-[400px] md:rounded-2xl md:border md:border-border md:bg-surface md:p-8">{children}</div>
  )
}
