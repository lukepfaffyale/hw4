import { useEffect, useState } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { api, messageOf } from '../api'
import { useAuth } from '../auth/useAuth'
import type { AdminRestockQueue } from '../types'
import { usePageTitle } from '../usePageTitle'

type QueueState = { kind: 'loading' } | { kind: 'error'; message: string } | { kind: 'ready'; queue: AdminRestockQueue }

/**
 * Shop staff only (Problem 9, split out in Problem 10): what needs ordering, with who is waiting.
 * The server decides who is staff (`ADMIN_EMAILS` in backend/.env) and answers 403 to anyone else;
 * this page is simply not linked for shoppers, and shows nothing if one types the URL.
 */
export default function Staff() {
  usePageTitle('Staff')
  const { user, token } = useAuth()
  const [queue, setQueue] = useState<QueueState>({ kind: 'loading' })
  const isAdmin = Boolean(user?.is_admin)

  useEffect(() => {
    if (!token || !isAdmin) return
    let cancelled = false
    api
      .adminRestockQueue(token)
      .then((q) => {
        if (!cancelled) setQueue({ kind: 'ready', queue: q })
      })
      .catch((err: unknown) => {
        if (!cancelled) setQueue({ kind: 'error', message: messageOf(err) })
      })
    return () => {
      cancelled = true
    }
  }, [token, isAdmin])

  if (!user || !token) return <Navigate to="/login" replace />

  async function markOrdered(id: number) {
    if (!token) return
    try {
      await api.adminMarkOrdered(token, id)
      setQueue({ kind: 'ready', queue: await api.adminRestockQueue(token) })
    } catch (err) {
      setQueue({ kind: 'error', message: messageOf(err) })
    }
  }

  async function downloadCsv() {
    if (!token) return
    try {
      const csv = await api.adminRestockCsv(token)
      const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }))
      const a = document.createElement('a')
      a.href = url
      a.download = 'restock-requests.csv'
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      setQueue({ kind: 'error', message: messageOf(err) })
    }
  }

  if (!isAdmin) {
    return (
      <div className="auth-page">
        <h1>Shop staff only</h1>
        <p className="muted">
          This page is for the shop's staff accounts. Your own restock requests are on your{' '}
          <Link to="/account">Account page</Link>.
        </p>
      </div>
    )
  }

  return (
    <div className="auth-page">
      <p className="eyebrow">Shop staff</p>
      <h1>What needs ordering</h1>
      <p className="muted">
        Open restock requests grouped by product and size, most requested first, with who is waiting so they can be
        told when stock arrives.
      </p>
      <div className="notice">
        You see this page because <strong>{user.email}</strong> is listed in <code>ADMIN_EMAILS</code> on the server.
        Shoppers never see it or this list; they see only their own requests on their Account page, and the server
        refuses these records to anyone not on that list.
      </div>

      <section className="auth-card" aria-labelledby="queue-h">
        <h2 id="queue-h">Restock queue</h2>
        {queue.kind === 'loading' && <p className="muted">Loading…</p>}
        {queue.kind === 'error' && (
          <p className="status" role="status">
            {queue.message}
          </p>
        )}
        {queue.kind === 'ready' && queue.queue.groups.length === 0 && <p className="muted">Nothing to order right now.</p>}
        {queue.kind === 'ready' && queue.queue.groups.length > 0 && (
          <>
            <table className="admin-table">
              <caption className="muted">
                {queue.queue.total_open} open {queue.queue.total_open === 1 ? 'request' : 'requests'}
              </caption>
              <thead>
                <tr>
                  <th scope="col">Product</th>
                  <th scope="col">Size</th>
                  <th scope="col">Waiting</th>
                  <th scope="col">Requested by</th>
                </tr>
              </thead>
              <tbody>
                {queue.queue.groups.map((g) => (
                  <tr key={`${g.product_id}-${g.size}`}>
                    <td>
                      <Link to={`/products/${g.product_id}`}>{g.product_name}</Link>
                    </td>
                    <td>{g.size}</td>
                    <td>{g.open_count}</td>
                    <td>
                      <ul>
                        {g.requested_by.map((w) => (
                          <li key={w.request_id}>
                            {w.name} ({w.email}){' '}
                            <button type="button" className="link-button" onClick={() => markOrdered(w.request_id)}>
                              Mark ordered
                            </button>
                          </li>
                        ))}
                      </ul>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="confirm-row">
              <button type="button" className="btn btn-secondary" onClick={downloadCsv}>
                Download as CSV
              </button>
            </div>
          </>
        )}
      </section>
    </div>
  )
}
