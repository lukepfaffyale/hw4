import { useContext } from 'react'
import { HuntContext, type HuntState } from './context'

export function useHunt(): HuntState {
  const ctx = useContext(HuntContext)
  if (!ctx) throw new Error('useHunt must be used inside HuntProvider')
  return ctx
}
