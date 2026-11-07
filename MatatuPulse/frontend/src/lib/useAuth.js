import { useEffect, useState } from 'react'
import { getAuth } from '../api/client'

/** Reactive view of the auth object stored by api/client.setAuth(). */
export function useAuth() {
  const [auth, setAuthState] = useState(() => getAuth())

  useEffect(() => {
    const sync = () => setAuthState(getAuth())
    window.addEventListener('mp-auth', sync)
    window.addEventListener('storage', sync)
    return () => {
      window.removeEventListener('mp-auth', sync)
      window.removeEventListener('storage', sync)
    }
  }, [])

  return auth
}
