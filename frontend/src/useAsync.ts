import { useEffect, useRef, useState } from 'react'
import { ApiError } from './api'

export type AsyncState<T> =
  | { kind: 'loading' }
  | { kind: 'error'; message: string }
  | { kind: 'ready'; data: T }

interface Options {
  /** Message to show for a 404 instead of the API's own text. */
  notFound?: string
  /** Message for unexpected errors. */
  fallback?: string
}

/**
 * Loads `load()` whenever `key` changes. The result is only trusted while it still belongs to
 * the current key, so a stale response can never show for a newer request.
 */
export function useAsync<T>(key: string, load: () => Promise<T>, options: Options = {}): AsyncState<T> {
  const [stored, setStored] = useState<{ key: string; state: AsyncState<T> } | null>(null)
  const loadRef = useRef(load)
  const optionsRef = useRef(options)

  useEffect(() => {
    loadRef.current = load
    optionsRef.current = options
  })

  useEffect(() => {
    let cancelled = false
    loadRef
      .current()
      .then((data) => {
        if (!cancelled) setStored({ key, state: { kind: 'ready', data } })
      })
      .catch((err: unknown) => {
        if (cancelled) return
        const o = optionsRef.current
        let message = o.fallback ?? 'Something went wrong.'
        if (err instanceof ApiError) {
          message = err.status === 404 && o.notFound ? o.notFound : err.message
        }
        setStored({ key, state: { kind: 'error', message } })
      })
    return () => {
      cancelled = true
    }
  }, [key])

  return stored && stored.key === key ? stored.state : { kind: 'loading' }
}
