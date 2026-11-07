import { useEffect, useState } from 'react'

const RECENT_KEY = 'mp_recent'
const RECENT_LIMIT = 5
const DESKTOP_QUERY = '(min-width: 768px)'

/** "just now", "4m ago", "2h ago", "3d ago", then a short date. */
export function timeAgo(value, now = Date.now()) {
  if (!value) return ''
  const then = new Date(value).getTime()
  if (Number.isNaN(then)) return ''

  const seconds = Math.max(0, Math.round((now - then) / 1000))
  if (seconds < 45) return 'just now'
  const minutes = Math.round(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.round(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.round(hours / 24)
  if (days < 7) return `${days}d ago`
  return new Date(then).toLocaleDateString([], { day: 'numeric', month: 'short' })
}

/** Short local time used in the signal panel. */
export function clock(value) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

/** Format the 9 local digits shown after +254: 712 345 678. */
export function groupPhone(value) {
  const digits = String(value || '').replace(/\D/g, '')
  if (!digits) return ''
  if (digits.length <= 3) return digits
  if (digits.length <= 6) return `${digits.slice(0, 3)} ${digits.slice(3)}`
  return `${digits.slice(0, 3)} ${digits.slice(3, 6)} ${digits.slice(6, 9)}`.trim()
}

export function getRecent() {
  try {
    const stored = JSON.parse(localStorage.getItem(RECENT_KEY) || '[]')
    return Array.isArray(stored) ? stored.filter((item) => item && item.id) : []
  } catch {
    return []
  }
}

export function pushRecent(route) {
  if (!route?.id) return
  const item = {
    id: route.id,
    number: route.number,
    destination: route.destination,
  }
  try {
    const next = [
      item,
      ...getRecent().filter((entry) => entry.id !== item.id),
    ].slice(0, RECENT_LIMIT)
    localStorage.setItem(RECENT_KEY, JSON.stringify(next))
    window.dispatchEvent(new Event('mp-recent'))
  } catch {
    /* storage unavailable */
  }
}

export function useIsDesktop() {
  const [desktop, setDesktop] = useState(
    () => typeof window !== 'undefined' && window.matchMedia(DESKTOP_QUERY).matches,
  )

  useEffect(() => {
    const media = window.matchMedia(DESKTOP_QUERY)
    const onChange = (event) => setDesktop(event.matches)
    setDesktop(media.matches)
    media.addEventListener('change', onChange)
    return () => media.removeEventListener('change', onChange)
  }, [])

  return desktop
}

/** Shared clock for relative timestamps so cards refresh without a data refetch. */
export function useNow(intervalMs = 30_000) {
  const [now, setNow] = useState(() => Date.now())

  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), intervalMs)
    return () => clearInterval(timer)
  }, [intervalMs])

  return now
}
