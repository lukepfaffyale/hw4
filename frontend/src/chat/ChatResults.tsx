import { useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import ProductCard from '../components/ProductCard'
import { useHalloween } from '../halloween/useHalloween'
import { useChatResults } from './useChatResults'

/**
 * The strip of product cards the assistant just found, rendered in the page itself (not inside
 * the chat panel) with the same ProductCard as the Products grid, so every card opens the
 * single-item page. Shown on every page except Products, which folds the matches into its grid.
 */
export default function ChatResults() {
  const { results, clearResults } = useChatResults()
  const { reducedMotion } = useHalloween()
  const ref = useRef<HTMLElement>(null)

  // New matches: bring the strip into view so the shopper sees the page change.
  useEffect(() => {
    if (!results || results.products.length === 0) return
    ref.current?.scrollIntoView({ block: 'start', behavior: reducedMotion ? 'auto' : 'smooth' })
  }, [results, reducedMotion])

  if (!results || results.products.length === 0) return null
  const n = results.products.length

  return (
    <section ref={ref} className="chat-results" aria-labelledby="chat-results-h">
      <div className="chat-results-head">
        <h2 id="chat-results-h">The assistant found {n === 1 ? 'this' : `these ${n} items`}</h2>
        <p className="muted" role="status" aria-live="polite">
          For "{results.query}". Tap a card for the full view.
        </p>
        <div className="chat-results-actions">
          <Link className="btn btn-secondary" to={`/products?ids=${results.products.map((p) => p.product_id).join(',')}`}>
            Open on the Products page
          </Link>
          <button type="button" className="btn btn-secondary" onClick={clearResults}>
            Clear
          </button>
        </div>
      </div>
      <ul className="product-grid">
        {results.products.map((p) => (
          <ProductCard key={p.product_id} product={p} />
        ))}
      </ul>
    </section>
  )
}
