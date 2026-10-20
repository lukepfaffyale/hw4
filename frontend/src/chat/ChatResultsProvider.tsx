import { useCallback, useMemo, useState, type ReactNode } from 'react'
import type { ProductSummary } from '../types'
import { ChatResultsContext, type ChatResults } from './context'

/**
 * Holds the assistant's latest product matches for the whole app. The chat widget writes
 * here after each reply; the Products grid and the "assistant found" strip read from it.
 * Nothing is persisted: a reload starts clean.
 */
export function ChatResultsProvider({ children }: { children: ReactNode }) {
  const [results, setState] = useState<ChatResults | null>(null)

  const setResults = useCallback((query: string, products: ProductSummary[]) => {
    setState((prev) => ({ query, products, version: (prev?.version ?? 0) + 1 }))
  }, [])

  const clearResults = useCallback(() => setState(null), [])

  const value = useMemo(() => ({ results, setResults, clearResults }), [results, setResults, clearResults])
  return <ChatResultsContext.Provider value={value}>{children}</ChatResultsContext.Provider>
}
