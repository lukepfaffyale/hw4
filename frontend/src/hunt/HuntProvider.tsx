import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { api, messageOf } from '../api'
import { useAuth } from '../auth/useAuth'
import type { HuntProgram, HuntProgress } from '../types'
import { HuntContext, type FindOutcome } from './context'
import { clearGuestFinds, readGuestFinds, writeGuestFinds } from './guestFinds'

/**
 * The hidden-friends collection (Problem 9). The server defines the seasons and owns every rule
 * and code; this provider only remembers what the shopper has found and asks the server when they
 * tap a friend. Guests keep finds in this browser; signing in banks them on the account.
 */
export function HuntProvider({ children }: { children: ReactNode }) {
  const { token } = useAuth()
  const [program, setProgram] = useState<HuntProgram | null>(null)
  // Keyed by token so a different session (or signing out) never shows another shopper's finds.
  const [serverState, setServerState] = useState<{ key: string; progress: HuntProgress } | null>(null)
  const [guest, setGuest] = useState<{ season: string; keys: string[] } | null>(null)
  const [version, setVersion] = useState(0)

  useEffect(() => {
    let cancelled = false
    api
      .hunt()
      .then((p) => {
        if (cancelled) return
        setProgram(p)
        setGuest({ season: p.current_season.key, keys: readGuestFinds(p.current_season.key) })
      })
      .catch(() => {
        // no programme: the site simply has no friends hiding today
      })
    return () => {
      cancelled = true
    }
  }, [])

  // Signed in: bank any guest finds, then load the account's progress.
  useEffect(() => {
    if (!token || !program) return
    let cancelled = false
    const season = program.current_season.key
    const pending = readGuestFinds(season)
    const bank = pending.reduce<Promise<unknown>>(
      (chain, key) => chain.then(() => api.recordFind(token, season, key).catch(() => undefined)),
      Promise.resolve(),
    )
    bank
      .then(() => api.myHunt(token))
      .then((progress) => {
        if (cancelled) return
        clearGuestFinds()
        setGuest({ season, keys: [] })
        setServerState({ key: token, progress })
      })
      .catch(() => {
        // progress unavailable right now; friends still appear and a tap retries
      })
    return () => {
      cancelled = true
    }
  }, [token, program, version])

  const progress = token && serverState?.key === token ? serverState.progress : null
  const found = useMemo(() => {
    if (token) return new Set(progress ? progress.friends.filter((f) => f.found).map((f) => f.key) : [])
    return new Set(guest?.keys ?? [])
  }, [token, progress, guest])
  const ready = program !== null && (token ? progress !== null : guest !== null)

  const recordFind = useCallback(
    async (character: string): Promise<FindOutcome> => {
      if (!program) return { kind: 'error', message: 'The shop is still waking up. Try again in a moment.' }
      const season = program.current_season
      if (token) {
        try {
          const next = await api.recordFind(token, season.key, character)
          setServerState({ key: token, progress: next })
          return { kind: 'progress', progress: next }
        } catch (err) {
          return { kind: 'error', message: messageOf(err) }
        }
      }
      const have = readGuestFinds(season.key)
      const alreadyFound = have.includes(character)
      const keys = alreadyFound ? have : [...have, character]
      writeGuestFinds(season.key, keys)
      setGuest({ season: season.key, keys })
      const next = season.friends.find((f) => f.available && !keys.includes(f.key)) ?? null
      return {
        kind: 'guest',
        found: keys.length,
        total: season.friends.length,
        alreadyFound,
        nextFriend: next?.name ?? null,
        nextRiddle: next?.riddle ?? null,
      }
    },
    [program, token],
  )

  const refresh = useCallback(() => setVersion((v) => v + 1), [])

  const value = useMemo(
    () => ({ program, progress, found, ready, recordFind, refresh }),
    [program, progress, found, ready, recordFind, refresh],
  )

  return <HuntContext.Provider value={value}>{children}</HuntContext.Provider>
}
