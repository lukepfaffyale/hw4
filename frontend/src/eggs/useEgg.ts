import { useContext } from 'react'
import { EggContext } from './context'
import type { EggPlan } from './eggs'

/** The friend planned for this page visit, if any. */
export function useEgg(): EggPlan | null {
  return useContext(EggContext)
}
