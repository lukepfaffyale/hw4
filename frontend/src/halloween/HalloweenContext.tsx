import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { HalloweenContext } from './context'

const STORAGE_KEY = 'cc-halloween'

function readStored(): boolean {
  // Default ON: the shop is dressed for Halloween unless the shopper turns it off.
  try {
    const v = localStorage.getItem(STORAGE_KEY)
    return v === null ? true : v === '1'
  } catch {
    return true
  }
}

function readReducedMotion(): boolean {
  return typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

export function HalloweenProvider({ children }: { children: ReactNode }) {
  const [on, setOnState] = useState<boolean>(readStored)
  const [reducedMotion, setReducedMotion] = useState<boolean>(readReducedMotion)
  const [lightning, setLightning] = useState(0)

  useEffect(() => {
    document.documentElement.dataset.theme = on ? 'halloween' : 'classic'
  }, [on])

  useEffect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)')
    const onChange = (e: MediaQueryListEvent) => setReducedMotion(e.matches)
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  }, [])

  const setOn = useCallback((next: boolean) => {
    setOnState(next)
    try {
      localStorage.setItem(STORAGE_KEY, next ? '1' : '0')
    } catch {
      // storage unavailable: the toggle still works for this visit
    }
  }, [])

  const strikeLightning = useCallback(() => setLightning((n) => n + 1), [])

  const value = useMemo(
    () => ({ on, setOn, reducedMotion, lightning, strikeLightning }),
    [on, setOn, reducedMotion, lightning, strikeLightning],
  )

  return <HalloweenContext.Provider value={value}>{children}</HalloweenContext.Provider>
}
