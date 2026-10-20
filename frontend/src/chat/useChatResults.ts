import { useContext } from 'react'
import { ChatResultsContext, type ChatResultsState } from './context'

export function useChatResults(): ChatResultsState {
  const ctx = useContext(ChatResultsContext)
  if (!ctx) throw new Error('useChatResults must be used inside ChatResultsProvider')
  return ctx
}
