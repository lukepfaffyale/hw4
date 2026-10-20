import { Link } from 'react-router-dom'
import { api } from '../api'
import { CharacterArt } from '../eggs/characters'
import { useHalloween } from '../halloween/useHalloween'
import { useHunt } from '../hunt/useHunt'
import { CATEGORY_LABELS, type Category, type ProductSummary } from '../types'
import { useAsync } from '../useAsync'
import { usePageTitle } from '../usePageTitle'

/** Yale's residential colleges; only the ones with a product in the catalogue get a chip. */
const COLLEGES = [
  'Benjamin Franklin',
  'Berkeley',
  'Branford',
  'Davenport',
  'Ezra Stiles',
  'Grace Hopper',
  'Jonathan Edwards',
  'Morse',
  'Pauli Murray',
  'Pierson',
  'Saybrook',
  'Silliman',
  'Timothy Dwight',
  'Trumbull',
]

const FEATURED: Array<{ category: Category; blurb: string }> = [
  { category: 'hoodie', blurb: 'Pullover hoods with kangaroo pockets, navy and heather gray, YALE lettering and vintage bulldogs.' },
  { category: 'crewneck', blurb: 'The biggest part of the catalogue: college crests, arched wordmarks and team names on the left chest.' },
  { category: 't-shirt', blurb: 'Everyday Yale pride, including the 2025 Harvard-Yale game shirt.' },
  { category: 'quarter-zip', blurb: 'Layers for a New Haven fall: quarter-zips, fleece and bombers with residential college crests.' },
]

/** Home page as a storefront (Problem 10): real product photos lead each category. */
export default function Home() {
  usePageTitle('')
  const { on: halloween } = useHalloween()
  const { program, found } = useHunt()
  const loaded = useAsync('home:products', () => api.listProducts(), { fallback: 'The shelves are loading slowly.' })
  const items: ProductSummary[] = loaded.kind === 'ready' ? loaded.data.items : []

  const lead = (category: Category) => {
    const inCategory = items.filter((p) => p.category === category || (category === 'quarter-zip' && p.category === 'jacket'))
    return { count: inCategory.length, photo: inCategory.find((p) => p.total_stock > 0) ?? inCategory[0] }
  }
  const colleges = COLLEGES.filter((c) => items.some((p) => p.name.toLowerCase().includes(c.toLowerCase())))
  const season = program?.current_season
  const friends = season?.friends ?? []

  return (
    <>
      <section className="hero" aria-labelledby="home-title">
        <div className="hero-copy">
          <span className="hero-y" aria-hidden="true">
            Y
          </span>
          <p className="eyebrow">Licensed Yale gear, made for New Haven weather</p>
          <h1 id="home-title">Bulldog pride you can actually wear.</h1>
          <p className="lead">
            Hoodies, crewnecks, tees, quarter-zips and jackets for students, alumni, parents and
            anyone who bleeds Yale blue. Every item is real stock at a real price, and the shop
            bulldog will tell you honestly what is on the shelf in your size.
          </p>
          <div className="hero-actions">
            <Link className="btn btn-primary" to="/products">
              Shop the catalogue
            </Link>
            <Link className="btn btn-secondary" to="/products?in_stock=true&sort=price_asc">
              In stock, cheapest first
            </Link>
          </div>
        </div>
        <aside className="hero-panel" aria-label="Why shop with us">
          <h2>Why Campus Customs</h2>
          <ul>
            <li>Licensed Yale designs, from the big YALE wordmark to residential college crests.</li>
            <li>Team gear for Bulldogs sports, plus the Harvard-Yale game tee.</li>
            <li>Prices from $32 tees to $98 jackets, sizes XS to XXL, stock shown per size.</li>
            <li>Ask the chat and matching items appear on the page as you talk.</li>
            <li>Little friends hide around the shop each season. Find three for a coupon.</li>
          </ul>
        </aside>
      </section>

      {friends.length > 0 && (
        <section className="drop-strip" aria-labelledby="drop-title">
          <ul className="drop-friends" aria-hidden="true">
            {friends
              .filter((f) => f.available)
              .slice(-6)
              .map((f) => (
                <li key={f.key} className={found.has(f.key) ? 'is-found' : ''}>
                  <CharacterArt character={found.has(f.key) ? f.key : 'unknown'} />
                </li>
              ))}
          </ul>
          <div>
            <h2 id="drop-title">
              {halloween ? 'The Halloween drop is on' : `${season?.name ?? 'A new set'} is hiding`}
              {season?.daily && season.available_count < friends.length ? `: day ${season.available_count} of ${friends.length}` : ''}
            </h2>
            <p className="muted">
              {season?.daily
                ? `${friends.length} costumed friends, a new one each day of October; ${season.available_count} are out so far.`
                : `${friends.length} costumed friends hide around the shop.`}{' '}
              Each hides on its home page with a riddle to the next. Three finds earn a coupon, ten lift it, and the whole
              set earns a free item.{' '}
              {found.size > 0 ? `You have found ${found.size} of ${friends.length}.` : 'Start on this page.'}
            </p>
          </div>
          <Link className="btn btn-secondary" to="/account">
            My collection
          </Link>
        </section>
      )}

      <section className="section" aria-labelledby="shop-by">
        <div className="section-head">
          <h2 id="shop-by">Shop by the way you wear it</h2>
          <Link to="/products">All {items.length ? items.length : ''} products</Link>
        </div>
        <ul className="cat-grid">
          {FEATURED.map(({ category, blurb }, i) => {
            const { count, photo } = lead(category)
            return (
              <li key={category} className="cat-card" style={{ '--i': i } as React.CSSProperties}>
                <Link to={`/products?category=${category}`}>
                  <div className="cat-media">
                    {photo ? <img src={api.imageUrl(photo)} alt="" loading="lazy" width="400" height="400" /> : <div className="cat-placeholder" />}
                  </div>
                  <div className="cat-body">
                    <h3>{CATEGORY_LABELS[category]}</h3>
                    <p className="muted">{blurb}</p>
                    <span className="cat-count">{count ? `${count} styles` : 'Loading'}</span>
                  </div>
                </Link>
              </li>
            )
          })}
        </ul>
      </section>

      {colleges.length > 0 && (
        <section className="section" aria-labelledby="colleges">
          <div className="section-head">
            <h2 id="colleges">Show your residential college</h2>
            <span className="muted">Crests and names from the catalogue</span>
          </div>
          <ul className="college-chips">
            {colleges.map((c) => (
              <li key={c}>
                <Link to={`/products?q=${encodeURIComponent(c)}`}>{c}</Link>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="section" aria-labelledby="for-everyone">
        <h2 id="for-everyone">Made for the whole Yale family</h2>
        <p className="muted">
          Whether you live in Benjamin Franklin or Saybrook, row for the crew team, or are the
          proud parent of a first-year, there is a design with your name on it. Residential college
          gear, team gear and relatives gear all live under one roof.
        </p>
        <p>
          <Link to="/about">Read more about the shop</Link>
        </p>
      </section>
    </>
  )
}
