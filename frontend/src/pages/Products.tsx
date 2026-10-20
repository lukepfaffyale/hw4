import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api } from '../api'
import { useChatResults } from '../chat/useChatResults'
import ProductCard from '../components/ProductCard'
import EasterEgg from '../eggs/EasterEgg'
import { useEgg } from '../eggs/useEgg'
import { CATEGORY_LABELS, SORT_LABELS, type Category, type SearchSort } from '../types'
import { useAsync } from '../useAsync'
import { usePageTitle } from '../usePageTitle'

const CATEGORIES = Object.keys(CATEGORY_LABELS) as Category[]
const SORTS = Object.keys(SORT_LABELS) as SearchSort[]

/**
 * Products you can actually narrow (Problem 9). Every filter lives in the URL, so a filtered view
 * can be shared, the back button works, and the assistant can hand the shopper a link to it.
 */
export default function Products() {
  usePageTitle('Products')
  const egg = useEgg()
  const [params, setParams] = useSearchParams()
  const { results: chat, clearResults } = useChatResults()

  const rawCategory = params.get('category') ?? ''
  const category: Category | '' = CATEGORIES.includes(rawCategory as Category) ? (rawCategory as Category) : ''
  const rawSort = params.get('sort') ?? 'relevance'
  const sort: SearchSort = SORTS.includes(rawSort as SearchSort) ? (rawSort as SearchSort) : 'relevance'
  const maxPrice = params.get('max_price') ?? ''
  const inStock = params.get('in_stock') === 'true'
  const applied = params.get('q') ?? ''
  const [search, setSearch] = useState(applied)

  function update(changes: Record<string, string | null>) {
    const next = new URLSearchParams(params)
    for (const [k, v] of Object.entries(changes)) {
      if (v === null || v === '') next.delete(k)
      else next.set(k, v)
    }
    next.delete('ids') // a new filter replaces the assistant's hand-picked list
    setParams(next)
  }

  // The grid follows the assistant: live matches from the chat, or ?ids=a,b,c from a link.
  // Either way the cards are the same ProductCard, so each opens the single-item page.
  const urlIds = (params.get('ids') ?? '').split(',').filter(Boolean)
  const liveIds = chat?.products.map((p) => p.product_id) ?? []
  const chatIds = urlIds.length ? urlIds : liveIds
  const chatQuery = urlIds.length ? '' : (chat?.query ?? '')

  const priceNumber = maxPrice ? Number(maxPrice) : undefined
  const loaded = useAsync(
    `products:${category}:${applied}:${maxPrice}:${inStock}:${sort}`,
    () =>
      api.listProducts({
        category: category || undefined,
        q: applied || undefined,
        max_price: priceNumber !== undefined && Number.isFinite(priceNumber) && priceNumber >= 0 ? priceNumber : undefined,
        in_stock: inStock,
        sort,
      }),
    { fallback: 'Something went wrong loading products.' },
  )
  const state =
    loaded.kind === 'ready' && chatIds.length
      ? {
          kind: 'ready' as const,
          data: {
            ...loaded.data,
            items: chatIds
              .map((id) => loaded.data.items.find((p) => p.product_id === id))
              .filter((p): p is NonNullable<typeof p> => Boolean(p)),
            total: loaded.data.items.filter((p) => chatIds.includes(p.product_id)).length,
          },
        }
      : loaded

  const filtered = Boolean(category || applied || maxPrice || inStock || sort !== 'relevance')
  const summary: string[] = []
  if (category) summary.push(CATEGORY_LABELS[category].toLowerCase())
  if (applied) summary.push(`matching "${applied}"`)
  if (maxPrice) summary.push(`under $${maxPrice}`)
  if (inStock) summary.push('in stock')
  if (sort !== 'relevance') summary.push(SORT_LABELS[sort].toLowerCase())

  return (
    <>
      <h1>Products</h1>
      <p className="muted">
        Hoodies, crewnecks, tees, quarter-zips and jackets. Prices and stock come straight from the
        shop database; the size chips on each card show what is in stock right now.
      </p>

      <form
        className="filters"
        onSubmit={(e) => {
          e.preventDefault()
          update({ q: search.trim() })
        }}
      >
        <div className="field">
          <label htmlFor="filter-category">Category</label>
          <select id="filter-category" value={category} onChange={(e) => update({ category: e.target.value })}>
            <option value="">All</option>
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>
                {CATEGORY_LABELS[c]}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor="filter-sort">Sort by</label>
          <select id="filter-sort" value={sort} onChange={(e) => update({ sort: e.target.value === 'relevance' ? null : e.target.value })}>
            {SORTS.map((s) => (
              <option key={s} value={s}>
                {SORT_LABELS[s]}
              </option>
            ))}
          </select>
        </div>
        <div className="field field-narrow">
          <label htmlFor="filter-price">Max price ($)</label>
          <input
            id="filter-price"
            type="number"
            inputMode="numeric"
            min={0}
            max={500}
            step={1}
            value={maxPrice}
            placeholder="any"
            onChange={(e) => update({ max_price: e.target.value })}
          />
        </div>
        <div className="field field-check">
          <label htmlFor="filter-stock">
            <input id="filter-stock" type="checkbox" checked={inStock} onChange={(e) => update({ in_stock: e.target.checked ? 'true' : null })} />{' '}
            In stock only
          </label>
        </div>
        <div className="field">
          <label htmlFor="filter-search">Search</label>
          <input
            id="filter-search"
            type="search"
            value={search}
            maxLength={80}
            placeholder="bulldog, crest, navy…"
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="filters-actions">
          <button className="btn btn-secondary" type="submit">
            Search
          </button>
          {filtered && (
            <button
              type="button"
              className="link-button"
              onClick={() => {
                setSearch('')
                setParams(new URLSearchParams())
              }}
            >
              Clear filters
            </button>
          )}
        </div>
      </form>

      {chatIds.length > 0 && (
        <p className="notice" role="status" aria-live="polite">
          Showing the {chatIds.length === 1 ? 'item' : `${chatIds.length} items`} the assistant found
          {chatQuery ? ` for "${chatQuery}"` : ''}.{' '}
          {urlIds.length ? (
            <Link to="/products">See all products</Link>
          ) : (
            <button type="button" className="link-button" onClick={clearResults}>
              See all products
            </button>
          )}
        </p>
      )}

      <p className="status" role="status" aria-live="polite">
        {state.kind === 'loading' && 'Loading products…'}
        {state.kind === 'error' && state.message}
        {state.kind === 'ready' &&
          `${state.data.total} ${state.data.total === 1 ? 'product' : 'products'}${summary.length ? `: ${summary.join(', ')}` : ''}`}
      </p>

      {state.kind === 'ready' && state.data.items.length === 0 && (
        <p className="muted">
          Nothing matches those filters.{' '}
          <button type="button" className="link-button" onClick={() => setParams(new URLSearchParams())}>
            Show everything
          </button>
          , or ask the assistant.
        </p>
      )}

      {state.kind === 'ready' && (
        <ul className="product-grid">
          {state.data.items.map((p, i) => {
            const hasEgg = egg?.spot === 'card' && i === Math.floor(egg.seed * state.data.items.length)
            return <ProductCard key={p.product_id} product={p} index={i} egg={hasEgg && egg ? <EasterEgg plan={egg} /> : undefined} />
          })}
        </ul>
      )}
    </>
  )
}
