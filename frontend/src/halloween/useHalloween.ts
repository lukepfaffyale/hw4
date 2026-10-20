import { useContext } from 'react'
import { HalloweenContext, type HalloweenState } from './context'

export function useHalloween(): HalloweenState {
  const ctx = useContext(HalloweenContext)
  if (!ctx) throw new Error('useHalloween must be used inside HalloweenProvider')
  return ctx
}
