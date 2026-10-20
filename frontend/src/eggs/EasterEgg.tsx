import { useEffect, useRef, useState, type CSSProperties } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../auth/useAuth'
import type { FindOutcome } from '../hunt/context'
import { useHunt } from '../hunt/useHunt'
import { CharacterArt } from './characters'
import type { EggPlan } from './eggs'
import './eggs.css'

/**
 * A hidden friend peeking from a text-free spot. Activating it (click or keyboard) records a find:
 * on the account for a signed-in shopper, in this browser for a guest. The dialog says what that
 * earned and gives the riddle for the next friend. Escape or the button closes it and focus
 * returns to the friend, which stays put (marked found) until the shopper moves on.
 */
export default function EasterEgg({ plan }: { plan: EggPlan }) {
  const { token } = useAuth()
  const { recordFind } = useHunt()
  const [result, setResult] = useState<FindOutcome | null>(null)
  const [busy, setBusy] = useState(false)
  const [done, setDone] = useState(false)
  const eggRef = useRef<HTMLButtonElement>(null)
  const closeRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (!result) return
    closeRef.current?.focus()
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setResult(null)
        eggRef.current?.focus()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [result])

  function close() {
    setResult(null)
    eggRef.current?.focus()
  }

  async function found() {
    setBusy(true)
    try {
      const outcome = await recordFind(plan.character)
      setResult(outcome)
      if (outcome.kind !== 'error') setDone(true)
    } finally {
      setBusy(false)
    }
  }

  const style: CSSProperties =
    plan.spot === 'scene'
      ? { left: `${12 + plan.seed * 72}%` }
      : plan.spot === 'gutter'
        ? { top: `${18 + plan.seed * 60}%` }
        : {}

  return (
    <>
      <button
        ref={eggRef}
        type="button"
        className={`egg egg-${plan.spot}${done ? ' egg-found' : ''}`}
        style={style}
        aria-label={done ? `${plan.name}, found.` : `${plan.name} is hiding here. Activate to find them.`}
        disabled={busy || done}
        onClick={found}
      >
        <CharacterArt character={plan.character} />
      </button>

      {result && (
        <div className="egg-dialog" role="dialog" aria-label={`You found ${plan.name}`}>
          {result.kind === 'progress' && <ProgressNews name={plan.name} outcome={result} />}
          {result.kind === 'guest' && (
            <>
              <p className="egg-title">
                {result.alreadyFound ? `You already found ${plan.name}.` : `You found ${plan.name}!`}
              </p>
              <p>
                {result.found} of {result.total} this season, saved in this browser. Sign in and the finds move to your
                account, where three of them earn a coupon.
              </p>
              {result.nextRiddle && (
                <p className="egg-riddle">
                  <strong>Next clue:</strong> {result.nextRiddle}
                </p>
              )}
              <p>
                <Link className="btn btn-secondary" to="/login" onClick={() => setResult(null)}>
                  Sign in
                </Link>{' '}
                <Link className="btn btn-secondary" to="/create-account" onClick={() => setResult(null)}>
                  Create account
                </Link>
              </p>
            </>
          )}
          {result.kind === 'error' && (
            <>
              <p className="egg-title">{plan.name} slipped away.</p>
              <p className="status">{result.message}</p>
            </>
          )}
          <button ref={closeRef} type="button" className="btn btn-primary" onClick={close}>
            Keep shopping
          </button>
          {token && (
            <p className="hint">
              <Link to="/account" onClick={() => setResult(null)}>
                See your collection and codes on the Account page
              </Link>
              .
            </p>
          )}
        </div>
      )}
    </>
  )
}

function ProgressNews({ name, outcome }: { name: string; outcome: Extract<FindOutcome, { kind: 'progress' }> }) {
  const p = outcome.progress
  const m = p.milestones
  const again = p.unlocked.includes('already_found')
  const freeItem = p.rewards.find((r) => r.kind === 'free_item')
  return (
    <>
      <p className="egg-title">{again ? `You already found ${name}.` : `You found ${name}!`}</p>
      <p>
        {p.season_found} of {p.season_total} this season
        {p.season_available < p.season_total ? ` (${p.season_available} out so far)` : ''}, {p.total_finds} finds in all.
      </p>
      {p.unlocked.includes('coupon') && p.coupon && (
        <>
          <p>That makes {m.coupon_at}. They brought you {p.coupon.discount_pct}% off one item:</p>
          <p className="egg-code">
            <code>{p.coupon.code}</code>
          </p>
        </>
      )}
      {p.unlocked.includes('coupon_upgrade') && p.coupon && (
        <>
          <p>
            {m.lift_at} finds! Your coupon now takes {p.coupon.discount_pct}% off one item:
          </p>
          <p className="egg-code">
            <code>{p.coupon.code}</code>
          </p>
        </>
      )}
      {p.unlocked.includes('free_item') && freeItem && (
        <>
          <p>The whole set! Your free-item voucher, up to ${freeItem.max_value_usd}:</p>
          <p className="egg-code">
            <code>{freeItem.code}</code>
          </p>
          <p className="hint">{freeItem.terms}</p>
        </>
      )}
      {p.next_riddle ? (
        <p className="egg-riddle">
          <strong>Next clue:</strong> {p.next_riddle}
        </p>
      ) : p.season_available < p.season_total ? (
        <p>Every friend out so far is found. A new one arrives tomorrow.</p>
      ) : (
        <p>The set is complete. The next set arrives with the next season.</p>
      )}
      <p className="hint">Class-project codes, not redeemable at the real store. Saved on your Account page.</p>
    </>
  )
}
