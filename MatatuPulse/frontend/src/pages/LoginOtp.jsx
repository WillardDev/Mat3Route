import { ArrowLeft } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { requestOtp, setAuth, verifyOtp } from '../api/client'
import Button from '../components/Button'
import OtpInput from '../components/OtpInput'
import { groupPhone } from '../lib/format'
import AuthLayout, { AuthCard } from './AuthLayout'

const RESEND_AFTER = 30

export default function LoginOtp() {
  const navigate = useNavigate()
  const { state } = useLocation()
  const digits = state?.digits || sessionStorage.getItem('mp_phone') || ''
  const [code, setCode] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [left, setLeft] = useState(RESEND_AFTER)
  const [demo, setDemo] = useState(state?.demo)

  useEffect(() => {
    if (left <= 0) return
    const t = setTimeout(() => setLeft((s) => s - 1), 1000)
    return () => clearTimeout(t)
  }, [left])

  const verify = async (value = code) => {
    if (value.length !== 4 || busy) return
    setBusy(true)
    setError('')
    try {
      const res = await verifyOtp(`+254${digits}`, value)
      setAuth({ access: res.access, refresh: res.refresh, user: res.user })
      navigate('/routes', { replace: true })
    } catch (err) {
      setError(err.message)
      setCode('')
    } finally {
      setBusy(false)
    }
  }

  const onChange = (v) => {
    setCode(v)
    setError('')
    if (v.length === 4) verify(v)
  }

  const resend = async () => {
    try {
      const res = await requestOtp(`+254${digits}`)
      setDemo(res.demo)
      setLeft(RESEND_AFTER)
    } catch (err) {
      setError(err.message)
    }
  }

  if (!digits) return <Navigate to="/login" replace />

  return (
    <AuthLayout>
      <AuthCard>
        <form
          onSubmit={(e) => {
            e.preventDefault()
            verify()
          }}
          className="flex min-h-[100dvh] flex-col px-6 pb-[max(1.5rem,env(safe-area-inset-bottom))] pt-6 md:min-h-0 md:p-0"
        >
          <button type="button" onClick={() => navigate('/login')} aria-label="Back" className="-ml-1 self-start rounded-full p-1 text-ink hover:bg-background">
            <ArrowLeft className="h-6 w-6" />
          </button>
          <h1 className="mt-8 text-[28px] font-bold leading-tight text-ink md:mt-4 md:text-xl md:font-semibold">Enter the code</h1>
          <p className="mt-2 text-base text-muted">
            Sent by SMS to +254 {groupPhone(digits)}.{' '}
            <Link to="/login" className="font-semibold text-primary underline underline-offset-2">Change</Link>
          </p>
          <div className="mt-8">
            <OtpInput value={code} onChange={onChange} autoFocus disabled={busy} />
          </div>
          {error && <p className="mt-3 text-sm font-medium text-alert">{error}</p>}
          <p className="mt-4 text-sm font-medium text-muted">
            {left > 0 ? (
              `Resend code in 0:${String(left).padStart(2, '0')}`
            ) : (
              <button type="button" onClick={resend} className="font-semibold text-primary underline underline-offset-2">Resend code</button>
            )}
          </p>
          {demo && <p className="mt-2 text-sm text-muted">Demo mode: the code is <span className="font-semibold text-ink">4729</span>.</p>}
          <div className="flex-1 md:hidden" />
          <Button type="submit" block className="mt-8" disabled={code.length !== 4 || busy}>
            {busy ? 'Checking…' : 'Verify'}
          </Button>
        </form>
      </AuthCard>
    </AuthLayout>
  )
}
