import { useEffect, useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { api, messageOf } from '../api'
import { useAuth } from '../auth/useAuth'
import { CharacterArt } from '../eggs/characters'
import HalloweenScene from '../halloween/HalloweenScene'
import { useHunt } from '../hunt/useHunt'
import type { ActivityItem, RestockRequest } from '../types'
import { usePageTitle } from '../usePageTitle'

const PROVIDER_LABEL = { password: 'Email and password', google: 'Google', github: 'GitHub' } as const
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

type ActivityState = { kind: 'loading' } | { kind: 'error'; message: string } | { kind: 'ready'; items: ActivityItem[] }
type RequestsState = { kind: 'loading' } | { kind: 'error'; message: string } | { kind: 'ready'; items: RestockRequest[] }

/** "11-06" -> "Nov 6" */
function mmdd(s: string): string {
  const [m, d] = s.split('-').map(Number)
  return m >= 1 && m <= 12 ? `${MONTHS[m - 1]} ${d}` : s
}

export default function Account() {
  usePageTitle('Account')
  const navigate = useNavigate()
  const { user, token, signOut } = useAuth()
  const { program, progress } = useHunt()
  const [confirming, setConfirming] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [leaving, setLeaving] = useState(false)
  const [activity, setActivity] = useState<ActivityState>({ kind: 'loading' })
  const [activityBusy, setActivityBusy] = useState(false)
  const [requests, setRequests] = useState<RequestsState>({ kind: 'loading' })
  const [copied, setCopied] = useState(false)
  const isAdmin = Boolean(user?.is_admin)

  useEffect(() => {
    if (!token) return
    let cancelled = false
    api
      .activity(token)
      .then((res) => {
        if (!cancelled) setActivity({ kind: 'ready', items: res.items })
      })
      .catch((err: unknown) => {
        if (!cancelled) setActivity({ kind: 'error', message: messageOf(err) })
      })
    api
      .restockRequests(token)
      .then((res) => {
        if (!cancelled) setRequests({ kind: 'ready', items: res.items })
      })
      .catch((err: unknown) => {
        if (!cancelled) setRequests({ kind: 'error', message: messageOf(err) })
      })
    return () => {
      cancelled = true
    }
  }, [token])

  async function clearActivity() {
    if (!token) return
    setActivityBusy(true)
    try {
      await api.deleteActivity(token)
      setActivity({ kind: 'ready', items: [] })
    } catch (err) {
      setActivity({ kind: 'error', message: messageOf(err) })
    } finally {
      setActivityBusy(false)
    }
  }

  function downloadBlob(name: string, type: string, content: string) {
    const url = URL.createObjectURL(new Blob([content], { type }))
    const a = document.createElement('a')
    a.href = url
    a.download = name
    a.click()
    URL.revokeObjectURL(url)
  }

  function downloadActivity() {
    if (activity.kind !== 'ready') return
    downloadBlob('campus-customs-chat-history.json', 'application/json', JSON.stringify(activity.items, null, 2))
  }

  async function cancelRequest(id: number) {
    if (!token) return
    try {
      const res = await api.cancelRestock(token, id)
      setRequests((prev) => (prev.kind === 'ready' ? { kind: 'ready', items: prev.items.map((r) => (r.id === id ? res.request : r)) } : prev))
    } catch (err) {
      setRequests({ kind: 'error', message: messageOf(err) })
    }
  }

  async function copyReferral(link: string) {
    try {
      await navigator.clipboard.writeText(link)
      setCopied(true)
    } catch {
      setCopied(false)
    }
  }

  if (leaving) return null
  if (!user || !token) return <Navigate to="/login" replace />

  function logout() {
    setLeaving(true)
    signOut()
    navigate('/')
  }

  async function deleteAccount() {
    if (!token) return
    setBusy(true)
    setError('')
    try {
      await api.deleteMe(token)
      setLeaving(true)
      signOut()
      navigate('/', { replace: true })
    } catch (err) {
      setError(messageOf(err))
      setBusy(false)
    }
  }

  const joined = new Date(user.created_at)
  const m = progress?.milestones ?? program?.milestones ?? null
  const freeItem = progress?.rewards.find((r) => r.kind === 'free_item') ?? null
  const referralLink = progress ? `${window.location.origin}/create-account?ref=${progress.referral_code}` : ''
  const coming = program?.seasons.filter((s) => s.status === 'coming') ?? []

  return (
    <div className="auth-page">
      <h1>
        Welcome back, {user.first_name}
        {isAdmin && <span className="staff-badge">Shop staff</span>}
      </h1>
      <p className="muted">This is everything the shop holds about you.</p>

      <div className="account-scene">
        <HalloweenScene />
      </div>

      <section className="auth-card" aria-labelledby="profile-h">
        <h2 id="profile-h">Your details</h2>
        <dl className="detail-facts">
          <dt>Name</dt>
          <dd>
            {user.first_name} {user.last_name}
          </dd>
          <dt>Email</dt>
          <dd>{user.email}</dd>
          <dt>Signs in with</dt>
          <dd>{PROVIDER_LABEL[user.auth_provider]}</dd>
          <dt>Member since</dt>
          <dd>{Number.isNaN(joined.getTime()) ? user.created_at : joined.toLocaleDateString()}</dd>
          <dt>Role</dt>
          <dd>
            {isAdmin ? (
              <>
                Shop staff: this email is listed in the server&apos;s <code>ADMIN_EMAILS</code>. The ordering queue is on the{' '}
                <Link to="/staff">Staff page</Link>.
              </>
            ) : (
              'Shopper. You see your own requests and finds here; only staff accounts see the ordering queue.'
            )}
          </dd>
        </dl>
        <p className="hint">
          Your password is stored only as a salted hash. Nobody at the shop can read it, and it
          never appears in logs.
        </p>
        <button type="button" className="btn btn-secondary" onClick={logout}>
          Sign out
        </button>
      </section>

      <section className="auth-card" aria-labelledby="friends-h">
        <h2 id="friends-h">My hidden friends</h2>
        {!progress || !m ? (
          <p className="muted">Loading your collection…</p>
        ) : (
          <>
            <p className="muted">
              {progress.season_name}: {progress.season_found} of {progress.season_total} found
              {progress.season_available < progress.season_total
                ? `, ${progress.season_available} out so far (a new friend each day until Halloween)`
                : ''}
              . {progress.total_finds} {progress.total_finds === 1 ? 'find' : 'finds'} in all, counting referrals.
            </p>
            <progress
              className="hunt-progress"
              value={progress.season_found}
              max={progress.season_total}
              aria-label={`${progress.season_found} of ${progress.season_total} friends found this season`}
            />
            <ul className="hunt-tray" aria-label="This season's friends, one per day">
              {progress.friends.map((f) => (
                <li key={f.key} className={f.found ? 'hunt-slot found' : f.available ? 'hunt-slot' : 'hunt-slot locked'}>
                  <CharacterArt character={f.found ? f.key : f.available ? 'unknown' : 'locked'} />
                  <span className="hunt-day">{f.day ? `Oct ${f.day}` : ''}</span>
                  <span className="hunt-name">{f.found ? f.name : f.available ? 'Not found yet' : 'Not out yet'}</span>
                  <span className="hint">
                    {f.found && f.found_at
                      ? `Found ${new Date(f.found_at).toLocaleDateString()}`
                      : f.available
                        ? 'Keep looking'
                        : `Arrives ${mmdd(f.available_from)}`}
                  </span>
                </li>
              ))}
            </ul>
            {progress.next_riddle ? (
              <p className="egg-riddle">
                <strong>Next clue:</strong> {progress.next_riddle} (The shop bulldog can repeat it for you.)
              </p>
            ) : progress.season_available < progress.season_total ? (
              <p className="muted">Every friend out so far is found. A new one arrives tomorrow.</p>
            ) : (
              <p className="muted">Set complete. The next set arrives with the next season.</p>
            )}

            <h3>Rewards</h3>
            <ul className="coupon-list">
              {progress.coupon ? (
                <li>
                  <code>{progress.coupon.code}</code>: {progress.coupon.discount_pct}% off one item, earned{' '}
                  {new Date(progress.coupon.created_at).toLocaleDateString()}.{' '}
                  {progress.coupon.redeemed_at ? 'Used.' : 'Not used yet.'}
                  {progress.coupon.discount_pct < m.lift_pct && ` Reach ${m.lift_at} finds (referrals count) and it rises to ${m.lift_pct}%.`}
                </li>
              ) : (
                <li className="muted">
                  Find {m.coupon_at} friends in a season for {m.coupon_pct}% off one item; {m.lift_at} finds across seasons lift it to{' '}
                  {m.lift_pct}%.
                </li>
              )}
              {freeItem ? (
                <li>
                  <code>{freeItem.code}</code>: the free-item voucher, earned {new Date(freeItem.created_at).toLocaleDateString()}.{' '}
                  {freeItem.redeemed_at ? 'Used.' : 'Not used yet.'} <span className="hint">{freeItem.terms}</span>
                </li>
              ) : (
                <li className="muted">
                  Collect the whole set and you earn the free-item voucher: {m.free_item_terms}
                </li>
              )}
            </ul>

            <h3>Bring a friend</h3>
            <p>
              Each friend who creates an account with your code counts as a find, up to {m.referral_credit_max}.{' '}
              {progress.referral_credits} of {m.referral_credit_max} earned so far.
            </p>
            <div className="referral-row">
              <span>
                Your code: <code>{progress.referral_code}</code>
              </span>
              <button type="button" className="btn btn-secondary btn-small" onClick={() => copyReferral(referralLink)}>
                {copied ? 'Link copied' : 'Copy invite link'}
              </button>
            </div>

            {coming.length > 0 && (
              <>
                <h3>Coming up</h3>
                <ul>
                  {coming.map((s) => (
                    <li key={s.key}>
                      {s.name} from {mmdd(s.starts)}: {s.friends.map((f) => f.name).join(', ')}.
                    </li>
                  ))}
                </ul>
              </>
            )}
            <p className="hint">Class-project codes, not redeemable at the real store. One coupon per shopper, one item, one time.</p>
          </>
        )}
      </section>

      <section className="auth-card" aria-labelledby="restock-h">
        <h2 id="restock-h">My restock requests</h2>
        <p className="muted">
          Sizes you asked the shop to reorder, from an item page or through the chat assistant. The shop sees these when
          deciding what to order.
        </p>
        {requests.kind === 'loading' && <p className="muted">Loading…</p>}
        {requests.kind === 'error' && (
          <p className="status" role="status">
            {requests.message}
          </p>
        )}
        {requests.kind === 'ready' && requests.items.length === 0 && (
          <p className="muted">
            None yet. When a size is sold out, the item page and the assistant both offer a restock request.{' '}
            <Link to="/products?in_stock=true">Browse what is in stock</Link>.
          </p>
        )}
        {requests.kind === 'ready' && requests.items.length > 0 && (
          <ul className="request-list">
            {requests.items.map((r) => (
              <li key={r.id}>
                <span>
                  <Link to={`/products/${r.product_id}`}>{r.product_name}</Link> in {r.size}
                  <span className="hint"> requested {new Date(r.created_at).toLocaleDateString()}</span>
                </span>
                <span className={`request-status ${r.status}`}>{r.status}</span>
                {r.status === 'open' && (
                  <button type="button" className="btn btn-secondary btn-small" onClick={() => cancelRequest(r.id)}>
                    Cancel
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="auth-card" aria-labelledby="activity-h">
        <h2 id="activity-h">My activity</h2>
        <p className="muted">
          Every chat turn stored for your account, oldest first, with the items the assistant showed.
        </p>
        {activity.kind === 'loading' && <p className="muted">Loading…</p>}
        {activity.kind === 'error' && (
          <p className="status" role="status">
            {activity.message}
          </p>
        )}
        {activity.kind === 'ready' && activity.items.length === 0 && (
          <p className="muted">
            Nothing yet. Open the chat and ask about merch. <Link to="/products">Browse products</Link>.
          </p>
        )}
        {activity.kind === 'ready' && activity.items.length > 0 && (
          <ol className="activity-list">
            {activity.items.map((it) => (
              <li key={it.id} className={`activity-${it.role}`}>
                <span className="chat-who">
                  {it.role === 'user' ? 'You' : 'Assistant'} · {new Date(it.created_at).toLocaleString()}
                </span>
                <p>{it.content}</p>
                {it.products.length > 0 && (
                  <p className="hint">Showed: {it.products.map((p) => p.name).join(', ')}</p>
                )}
              </li>
            ))}
          </ol>
        )}
        {activity.kind === 'ready' && activity.items.length > 0 && (
          <div className="confirm-row">
            <button type="button" className="btn btn-secondary" onClick={downloadActivity}>
              Download as JSON
            </button>
            <button type="button" className="btn btn-secondary" onClick={clearActivity} disabled={activityBusy}>
              {activityBusy ? 'Deleting…' : 'Delete my chat history'}
            </button>
          </div>
        )}
      </section>

      <section className="auth-card danger" aria-labelledby="delete-h">
        <h2 id="delete-h">Delete my account</h2>
        <p className="muted">
          Removes your account, your chat messages, your finds and codes, and your restock requests. This cannot be undone.
        </p>
        {!confirming ? (
          <button type="button" className="btn btn-secondary" onClick={() => setConfirming(true)}>
            Delete my account…
          </button>
        ) : (
          <div className="confirm-row">
            <button type="button" className="btn btn-danger" onClick={deleteAccount} disabled={busy}>
              {busy ? 'Deleting…' : 'Yes, delete everything'}
            </button>
            <button type="button" className="btn btn-secondary" onClick={() => setConfirming(false)} disabled={busy}>
              Keep my account
            </button>
          </div>
        )}
        <p className="status" role="status" aria-live="polite">
          {error}
        </p>
      </section>
    </div>
  )
}
