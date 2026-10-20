import { createContext } from 'react'
import type { HuntProgram, HuntProgress } from '../types'

/** What a tap on a hidden friend came back with. */
export type FindOutcome =
  | { kind: 'progress'; progress: HuntProgress }
  | { kind: 'guest'; found: number; total: number; alreadyFound: boolean; nextFriend: string | null; nextRiddle: string | null }
  | { kind: 'error'; message: string }

export interface HuntState {
  /** The programme (seasons, friends, riddles, milestones). Null until loaded. */
  program: HuntProgram | null
  /** The signed-in shopper's progress; null for guests or until loaded. */
  progress: HuntProgress | null
  /** Friend keys found this season, from the server when signed in, else from this browser. */
  found: ReadonlySet<string>
  /** True once we know what has already been found (so a found friend is never offered again). */
  ready: boolean
  recordFind: (character: string) => Promise<FindOutcome>
  refresh: () => void
}

export const HuntContext = createContext<HuntState | null>(null)
