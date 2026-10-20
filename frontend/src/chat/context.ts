import { createContext } from 'react'
import type { ProductSummary } from '../types'

/** The latest structured product matches the assistant returned, shared with every page. */
export interface ChatResults {
  query: string
  products: ProductSummary[]
  /** Increments on every update so pages can react even when the same items come back. */
  version: number
}

export interface ChatResultsState {
  results: ChatResults | null
  setResults: (query: string, products: ProductSummary[]) => void
  clearResults: () => void
}

export const ChatResultsContext = createContext<ChatResultsState | null>(null)
