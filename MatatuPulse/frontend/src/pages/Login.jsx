import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { requestOtp } from '../api/client'
import Button from '../components/Button'
import { LogoMark } from '../components/Logo'
import { PhoneInput } from '../components/TextInput'
import { groupPhone } from '../lib/format'
import AuthLayout, { AuthCard } from './AuthLayout'

export default function Login() {
  const navigate = useNavigate()
  const [digits, setDigits] = useState(() => sessionStorage.getItem('mp_phone') || '')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const valid = /^[17]\d{8}$/.test(digits)

  const submit = async (e) => {
    e.preventDefault()
    if (!valid) {
      setError('Enter the 9 digits after +254, e.g. 712 345 678.')
      return
    }
    setBusy(true)
    setError('')
    try {
      const res = await requestOtp(`+254${digits}`)
      sessionStorage.setItem('mp_phone', digits)
      navigate('/login/otp', { state: { digits, demo: res.demo } })
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const onChange = (e) => {
    let d = e.target.value.replace(/\D/g, '')
    if (d.startsWith('254')) d = d.slice(3)
    if (d.startsWith('0')) d = d.slice(1)
    setDigits(d.slice(0, 9))
    setError('')
  }

  return (
    <AuthLayout>
      {/* Mobile hero (1a) */}
      <div className="flex flex-1 flex-col items-center justify-center px-6 pt-16 text-center md:hidden">
        <LogoMark size="lg" />
        <h1 className="mt-6 text-[30px] font-bold leading-tight text-ink">MatatuPulse</h1>
        <p className="mt-2 text-lg text-muted">Signal from the noise.</p>
        <p className="mt-8 max-w-[300px] text-base text-muted">Live fares and verified alerts for your route, from commuters on it.</p>
      </div>

      <AuthCard>
        <form onSubmit={submit} className="px-6 pb-[max(1.5rem,env(safe-area-inset-bottom))] md:p-0">
          <div className="mb-6 hidden md:block">
            <h2 className="text-xl font-semibold text-ink">Sign in or register</h2>
            <p className="mt-1 text-sm text-muted">No password. New numbers are registered automatically with just your phone number.</p>
          </div>
          <PhoneInput
            id="phone"
            label="Enter your phone number"
            value={groupPhone(digits)}
            onChange={onChange}
            autoFocus
            aria-invalid={!!error}
            inputClassName="text-lg"
          />
          {error ? (
            <p className="mt-2 text-sm font-medium text-alert">{error}</p>
          ) : (
            <p className="mt-2 text-sm font-medium text-muted md:hidden">
              New here? Enter your number and we'll create your account.
            </p>
          )}
          <Button type="submit" block className="mt-5 md:mt-6" disabled={busy}>
            {busy ? 'Sending code…' : 'Continue'}
          </Button>
          <p className="mt-4 text-center text-sm font-medium text-muted md:mt-6">Your number is never shown to other commuters.</p>
        </form>
      </AuthCard>
    </AuthLayout>
  )
}
