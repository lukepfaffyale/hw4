import type { CSSProperties, ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { api, formatPrice } from '../api'
import { swatchFor } from '../colors'
import { useHalloween } from '../halloween/useHalloween'
import { SIZES, type ProductSummary } from '../types'

const FEW_LEFT_AT = 12

export default function ProductCard({ product, egg, index = 0 }: { product: ProductSummary; egg?: ReactNode; index?: number }) {
  const { on: halloween } = useHalloween()
  const soldOut = product.total_stock === 0
  const fewLeft = !soldOut && product.total_stock <= FEW_LEFT_AT
  return (
    <li className="product-card" style={{ '--i': index } as CSSProperties}>
      <Link to={`/products/${product.product_id}`} className="product-link">
        <div className="product-media">
          <img src={api.imageUrl(product)} alt={product.name} loading="lazy" width="400" height="400" />
          {soldOut && <span className="card-badge is-out">{halloween ? '👻 Sold out' : 'Sold out'}</span>}
          {fewLeft && <span className="card-badge">Few left</span>}
        </div>
        <div className="product-body">
          <h3 className="product-name">{product.name}</h3>
          <p className="product-price">{formatPrice(product.price)}</p>
          {product.colors.length > 0 && (
            <ul className="swatches" aria-label={`Colours: ${product.colors.join(', ')}`}>
              {product.colors.slice(0, 5).map((c) => (
                <li key={c} style={{ background: swatchFor(c) }} title={c}>
                  <span className="visually-hidden">{c}</span>
                </li>
              ))}
            </ul>
          )}
          <p className="product-desc muted">{product.short_description}</p>
          {/* Problem 9: sizes on the card, so a shopper knows before they click. */}
          <ul className="size-chips" aria-label={`Sizes in stock for ${product.name}`}>
            {SIZES.map((s) => {
              const ok = product.sizes_in_stock.includes(s)
              return (
                <li key={s} className={ok ? 'chip-in' : 'chip-out'}>
                  {!ok && halloween && <span aria-hidden="true">👻</span>}
                  <span className="chip-size" aria-hidden="true">
                    {s}
                  </span>
                  <span className="visually-hidden">
                    {s} {ok ? 'in stock' : 'sold out'}
                  </span>
                </li>
              )
            })}
          </ul>
        </div>
      </Link>
      {/* Outside the link so activating the friend never navigates. */}
      {egg}
    </li>
  )
}
