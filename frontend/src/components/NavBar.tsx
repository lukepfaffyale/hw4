import { useEffect, useState } from 'react'
import { NavLink } from 'react-router-dom'
import { useAuth } from '../auth/useAuth'
import HalloweenToggle from '../halloween/HalloweenToggle'
import { useHalloween } from '../halloween/useHalloween'
import { useHunt } from '../hunt/useHunt'
import Bulldog from './Bulldog'

interface Item {
  to: string
  label: string
  end?: boolean
  cta?: boolean
  /** Problem 9: a small count of hidden friends found this season, next to the Account link. */
  badge?: { text: string; label: string }
}

const PUBLIC: Item[] = [
  { to: '/', label: 'Home', end: true },
  { to: '/products', label: 'Products' },
  { to: '/about', label: 'About Us' },
]

export default function NavBar() {
  const [open, setOpen] = useState(false)
  const { user } = useAuth()
  const { program, found } = useHunt()
  const { on: halloween } = useHalloween()

  const total = program?.current_season.friends.length ?? 0
  const badge =
    user && total > 0
      ? { text: `${found.size}/${total}`, label: `${found.size} of ${total} hidden friends found this season` }
      : undefined
  const account: Item[] = user
    ? [
        ...(user.is_admin ? [{ to: '/staff', label: 'Staff' }] : []),
        { to: '/account', label: `Account (${user.first_name})`, cta: true, badge },
      ]
    : [
        { to: '/login', label: 'Sign in' },
        { to: '/create-account', label: 'Create Account', cta: true },
      ]
  const links = [...PUBLIC, ...account]

  // Escape closes the mobile menu.
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open])

  return (
    <header className="site-header">
      {/* Storefront strip (Problem 10): where we are and what is on this season. */}
      <div className="top-strip">
        <div className="container top-strip-row">
          <span>Licensed Yale gear. 57 Broadway, New Haven.</span>
          <span>
            {halloween
              ? `The Halloween drop is on: ${total || 'six'} friends are hiding. Find three for a coupon.`
              : 'Ask the shop bulldog: real stock, real prices, no guesses.'}
          </span>
        </div>
      </div>
      <div className="container header-row">
        <NavLink to="/" className="brand" aria-label="Campus Customs home">
          <span className="brand-dog">
            <Bulldog size={40} />
          </span>
          <span className="brand-text">
            <span className="brand-name">Campus Customs</span>
            <span className="brand-sub">Yale gear, New Haven</span>
          </span>
        </NavLink>

        <button
          type="button"
          className="menu-toggle"
          aria-expanded={open}
          aria-controls="site-nav"
          onClick={() => setOpen((v) => !v)}
        >
          {open ? 'Close menu' : 'Menu'}
        </button>

        <nav id="site-nav" className="site-nav" aria-label="Main" data-open={open}>
          <ul className="nav-list">
            {links.map((l) => (
              <li key={l.to}>
                <NavLink
                  to={l.to}
                  end={l.end}
                  className={l.cta ? 'nav-cta' : undefined}
                  onClick={() => setOpen(false)}
                >
                  {l.label}
                  {l.badge && (
                    <span className="nav-badge" aria-label={l.badge.label} title={l.badge.label}>
                      {l.badge.text}
                    </span>
                  )}
                </NavLink>
              </li>
            ))}
            <li>
              <HalloweenToggle />
            </li>
          </ul>
        </nav>
      </div>
    </header>
  )
}
