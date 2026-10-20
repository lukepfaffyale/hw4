import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { api, ApiError } from '../api'
import type { AuthResponse, UserPublic } from '../types'
import { AuthContext } from './context'

const STORAGE_KEY = 'cc-session'

interface StoredSession {
  token: string
  expires_at: string
  user: UserPublic
}

function readStored(): StoredSession | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const s = JSON.parse(raw) as StoredSession
    if (!s.token || !s.user || Date.parse(s.expires_at) <= Date.now()) return null
    return s
  } catch {
    return null
  }
}

/**
 * Holds the signed-in shopper. The session token is a signed, expiring value issued by our
 * back end; it is kept in localStorage so a refresh keeps you signed in. The app renders no
 * raw HTML, which is the main defence for that choice.
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<StoredSession | null>(readStored)

  const signIn = useCallback((res: AuthResponse) => {
    const s: StoredSession = { token: res.token, expires_at: res.expires_at, user: res.user }
    setSession(s)
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(s))
    } catch {
      // storage unavailable: signed in for this page only
    }
  }, [])

  const signOut = useCallback(() => {
    setSession(null)
    try {
      localStorage.removeItem(STORAGE_KEY)
    } catch {
      // nothing to clear
    }
  }, [])

  // Re-check a remembered token once: a deleted account or a restarted server drops it.
  useEffect(() => {
    const s = readStored()
    if (!s) return
    let cancelled = false
    api
      .me(s.token)
      .then((user) => {
        if (!cancelled) setSession((prev) => (prev && prev.token === s.token ? { ...prev, user } : prev))
      })
      .catch((err: unknown) => {
        if (!cancelled && err instanceof ApiError && err.status === 401) signOut()
      })
    return () => {
      cancelled = true
    }
  }, [signOut])

  const value = useMemo(
    () => ({ user: session?.user ?? null, token: session?.token ?? null, signIn, signOut }),
    [session, signIn, signOut],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
