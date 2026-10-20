import { createContext } from 'react'

export interface HalloweenState {
  on: boolean
  setOn: (on: boolean) => void
  reducedMotion: boolean
  /** Counter: every increment plays one lightning strike over the haunted house. */
  lightning: number
  strikeLightning: () => void
}

export const HalloweenContext = createContext<HalloweenState | null>(null)
