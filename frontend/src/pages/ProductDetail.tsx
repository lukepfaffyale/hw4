import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, formatPrice, messageOf } from '../api'
import { useAuth } from '../auth/useAuth'
import { swatchFor } from '../colors'
import { askTheShop } from '../components/askTheShop'
import JumpScare from '../halloween/JumpScare'
import { useHalloween } from '../halloween/useHalloween'
import { CATEGORY_LABELS, STOCK_LABELS, type Size } from '../types'
import { useAsync } from '../useAsync'
import { usePageTitle } from '../usePageTitle'

type RequestState = { kind: 'busy' } | { kind: 'done'; already: boolean } | { kind: 'error'; message: string }

export default function ProductDetail() {
  const { productId = '' } = useParams()
  const { on: halloween } = useHalloween()
  const { token } = useAuth()
  const [scare, setScare] = useState(0)
  // Problem 9: restock requests per size, keyed by product so a new item starts clean.
  const [requests, setRequests] = useState<{ key: string; by: Partial<Record<Size, RequestState>> }>({ key: productId, by: {} })
  const by = requests.key === productId ? requests.by : {}

  const state = useAsync(`product:${productId}`, () => api.getProduct(productId), {
    notFound: 'We could not find that product.',
    fallback: 'Something went wrong loading this product.',
  })

  usePageTitle(state.kind === 'ready' ? state.data.name : 'Product')

  function setRequest(size: Size, value: RequestState) {
    setRequests((prev) => ({ key: productId, by: { ...(prev.key === productId ? prev.by : {}), [size]: value } }))
  }

  async function requestRestock(size: Size) {
    if (!token) return
    setRequest(size, { kind: 'busy' })
    try {
      const res = await api.createRestock(token, productId, size)
      setRequest(size, { kind: 'done', already: res.request.created_at !== res.request.updated_at })
    } catch (err) {
      setRequest(size, { kind: 'error', message: messageOf(err) })
    }
  }

  if (state.kind !== 'ready') {
    return (
      <>
        <p>
          <Link to="/products">← All products</Link>
        </p>
        <p className="status" role="status" aria-live="polite">
          {state.kind === 'loading' ? 'Loading product…' : state.message}
        </p>
      </>
    )
  }

  const p = state.data
  const image = (
    <img
      src={api.imageUrl(p)}
      alt={p.name}
      width="800"
      height="800"
      onLoad={() => halloween && setScare((n) => n + 1)}
    />
  )
  const anySoldOut = p.stock.some((s) => s.status === 'sold_out')

  return (
    <>
      <p>
        <Link to="/products">← All products</Link>
      </p>
      <article className="detail">
        <div className="detail-media">
          {halloween ? (
            <button
              type="button"
              className="detail-photo-button"
              aria-label={`${p.name} photo. Activate for a Halloween surprise.`}
              onClick={() => setScare((n) => n + 1)}
            >
              {image}
            </button>
          ) : (
            image
          )}
          <JumpScare trigger={scare} />
        </div>

        <div className="detail-text">
          <p className="eyebrow">{CATEGORY_LABELS[p.category]}</p>
          <h1>{p.name}</h1>
          <p className="detail-price">{formatPrice(p.price)}</p>
          <p>{p.description}</p>

          <dl className="detail-facts">
            <dt>Type</dt>
            <dd>{p.garment_type}</dd>
            <dt>Colours</dt>
            <dd>
              {p.colors.length ? (
                <span className="detail-colours">
                  <ul className="swatches swatches-lg" aria-hidden="true">
                    {p.colors.map((c) => (
                      <li key={c} style={{ background: swatchFor(c) }} title={c} />
                    ))}
                  </ul>
                  {p.colors.join(', ')}
                </span>
              ) : (
                'Colour not listed'
              )}
            </dd>
          </dl>

          <p className="detail-actions">
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => askTheShop(`Is the ${p.name} in stock in my size, and what else is similar?`)}
            >
              Ask the bulldog about this item
            </button>
          </p>

          <h2>Sizes and stock</h2>
          <table className="stock-table">
            <caption className="muted">Live from the shop database</caption>
            <thead>
              <tr>
                <th scope="col">Size</th>
                <th scope="col">Availability</th>
                <th scope="col">Units</th>
                {anySoldOut && <th scope="col">Restock</th>}
              </tr>
            </thead>
            <tbody>
              {p.stock.map((s) => {
                const req = by[s.size]
                return (
                  <tr key={s.size} className={`stock-${s.status}`}>
                    <th scope="row">{s.size}</th>
                    <td>
                      {halloween && s.status === 'sold_out' && <span aria-hidden="true">👻 </span>}
                      {STOCK_LABELS[s.status]}
                    </td>
                    <td>{s.quantity}</td>
                    {anySoldOut && (
                      <td className="restock-cell">
                        {s.status === 'sold_out' &&
                          (token ? (
                            !req || req.kind === 'error' ? (
                              <>
                                <button type="button" className="btn btn-secondary btn-small" onClick={() => requestRestock(s.size)}>
                                  Request a restock
                                </button>
                                {req?.kind === 'error' && <span className="hint"> {req.message}</span>}
                              </>
                            ) : req.kind === 'busy' ? (
                              <span className="muted">Sending…</span>
                            ) : (
                              <span className="hint">{req.already ? 'Already requested.' : 'Requested.'} See your Account page.</span>
                            )
                          ) : (
                            <Link to="/login">Sign in to request</Link>
                          ))}
                      </td>
                    )}
                  </tr>
                )
              })}
            </tbody>
          </table>
          {anySoldOut && (
            <p className="hint">
              Sold out in your size? A restock request tells the shop what to order and for whom. Or ask the chat assistant
              for the same item in your size from a similar design.
            </p>
          )}

          {p.search_tags.length > 0 && (
            <ul className="tag-list" aria-label="Tags">
              {p.search_tags.map((t) => (
                <li key={t}>{t}</li>
              ))}
            </ul>
          )}
        </div>
      </article>
    </>
  )
}
