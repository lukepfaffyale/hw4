import { useEffect, useId, useRef, useState, type FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { api, formatPrice, messageOf } from '../api'
import { useAuth } from '../auth/useAuth'
import { useChatResults } from '../chat/useChatResults'
import { CharacterArt } from '../eggs/characters'
import { useHalloween } from '../halloween/useHalloween'
import { useHunt } from '../hunt/useHunt'
import type { ChatTurn, PageContext, PageLink, ProductSummary } from '../types'
import { ASK_EVENT, type AskDetail } from './askTheShop'
import Bulldog from './Bulldog'

interface Message {
  id: number
  role: 'user' | 'assistant'
  text: string
  products?: ProductSummary[]
  flagged?: boolean
  /** Problem 9: a page the assistant offered, validated by the server against the site's own routes. */
  goTo?: PageLink
}

const WELCOME =
  'Woof. I am the shop bulldog. Ask me about hoodies, crews, tees, sizes or prices. Everything I say about stock and prices comes straight from the shop database.'
const GUEST_HISTORY_TURNS = 10
const WELCOME_MSG: Message = { id: 1, role: 'assistant', text: WELCOME }
/** First questions a new shopper tends to have; one tap sends them (Problem 10). */
const SUGGESTIONS = ['Hoodies under $50', 'What crewnecks are in stock in M?', 'Cheapest Yale tee?', 'Give me a clue for the hidden friends']

/** What the browser tells the agent about where the shopper is (Problem 8). */
function pageContext(pathname: string): PageContext {
  const m = pathname.match(/^\/products\/([a-z0-9]+(?:-[a-z0-9]+)*)$/)
  return m ? { route: pathname, product_id: m[1] } : { route: pathname }
}

/** Floating chat in the bottom-right corner, talking to POST /chat. */
export default function ChatPanel() {
  const { on: halloween } = useHalloween()
  const { token, user } = useAuth()
  const { setResults } = useChatResults()
  const { program } = useHunt()
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [draft, setDraft] = useState('')
  const [busy, setBusy] = useState(false)
  // Messages are keyed by the session token: a different session (or signing out) starts clean
  // without an effect having to reset state.
  const [store, setStore] = useState<{ key: string | null; messages: Message[] }>({ key: null, messages: [WELCOME_MSG] })
  const messages = store.key === token ? store.messages : [WELCOME_MSG]
  const setMessages = (update: (prev: Message[]) => Message[]) =>
    setStore((prev) => ({ key: token, messages: update(prev.key === token ? prev.messages : [WELCOME_MSG]) }))

  // Signed in: reload the shopper's saved history into the window (Problem 8).
  useEffect(() => {
    if (!token) return
    let cancelled = false
    api
      .activity(token)
      .then((res) => {
        if (cancelled) return
        const saved: Message[] = res.items.map((it) => ({ id: it.id, role: it.role, text: it.content, products: it.products }))
        setStore({ key: token, messages: [WELCOME_MSG, ...saved] })
      })
      .catch(() => {
        // history unavailable: the window just starts with the welcome
      })
    return () => {
      cancelled = true
    }
  }, [token])
  // Easter egg: now and then one of this season's friends keeps the bulldog company in the header.
  const [roll] = useState(() => Math.random())
  const friends = program?.current_season.friends ?? []
  const friend = roll < 0.2 && friends.length ? friends[Math.floor((roll / 0.2) * friends.length)] : null
  const panelId = useId()
  const toggleRef = useRef<HTMLButtonElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const logRef = useRef<HTMLDivElement>(null)
  // Message ids for turns typed in this window (saved turns use their database ids, which are small).
  const nextId = useRef(1_000_000)

  useEffect(() => {
    if (!open) return
    inputRef.current?.focus()
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setOpen(false)
        toggleRef.current?.focus()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open])

  // "Ask the bulldog about this item" on a product page: open the counter with the question drafted.
  useEffect(() => {
    const onAsk = (e: Event) => {
      const detail = (e as CustomEvent<AskDetail>).detail
      setOpen(true)
      setDraft(detail.question)
      window.setTimeout(() => inputRef.current?.focus(), 50)
    }
    window.addEventListener(ASK_EVENT, onAsk)
    return () => window.removeEventListener(ASK_EVENT, onAsk)
  }, [])

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight })
  }, [store, busy])

  async function sendText(raw: string) {
    const text = raw.trim()
    if (!text || busy) return
    const userMsg: Message = { id: nextId.current++, role: 'user', text }
    setMessages((m) => [...m, userMsg])
    setDraft('')
    setBusy(true)
    // Guests carry their own recent turns; signed-in shoppers are remembered on the server.
    const history: ChatTurn[] = token
      ? []
      : messages
          .filter((m) => m.id !== 1)
          .slice(-GUEST_HISTORY_TURNS)
          .map((m) => ({ role: m.role, content: m.text }))
    try {
      const res = await api.chat({ message: text, history, page: pageContext(pathname) }, token)
      setMessages((m) => [
        ...m,
        { id: nextId.current++, role: 'assistant', text: res.reply, products: res.products, flagged: res.flagged, goTo: res.go_to ?? undefined },
      ])
      // The API contract: structured matches from the agent become cards on the page itself.
      if (res.products.length > 0) setResults(text, res.products)
      // Problem 9: the assistant can take the shopper to a page they asked for (fewer clicks).
      if (res.go_to?.navigate) navigate(res.go_to.route)
    } catch (err) {
      setMessages((m) => [...m, { id: nextId.current++, role: 'assistant', text: messageOf(err) }])
    } finally {
      setBusy(false)
      inputRef.current?.focus()
    }
  }

  function send(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    void sendText(draft)
  }

  const fresh = messages.length === 1

  return (
    <div className="chat-root">
      {open && (
        <section id={panelId} className="chat-panel" role="dialog" aria-label="Campus Customs chat">
          <header className="chat-header">
            <span className="chat-avatar" aria-hidden="true">
              <Bulldog size={34} />
            </span>
            <h2>
              {friend && (
                <span className="chat-friend" title={`${friend.name} is keeping me company`}>
                  <CharacterArt character={friend.key} />
                </span>
              )}
              {halloween ? '🎃 The shop counter' : 'The shop counter'}
            </h2>
            <button
              type="button"
              className="chat-close"
              aria-label="Close chat"
              onClick={() => {
                setOpen(false)
                toggleRef.current?.focus()
              }}
            >
              ×
            </button>
          </header>
          <p className="chat-note">
            {user
              ? `Signed in as ${user.first_name}. Your chat is saved to your account and reloads when you return; see it or delete it on the Account page.`
              : 'Browsing as a guest: nothing is saved. Sign in and the bulldog remembers you.'}
            {pathname.startsWith('/products/') && ' The bulldog can see which product is on screen and its stock by size.'}
          </p>
          <div className="chat-log" ref={logRef} role="log" aria-live="polite" aria-label="Messages">
            {messages.map((m) => (
              <div key={m.id} className={`chat-msg chat-${m.role}`}>
                <span className="chat-who">{m.role === 'user' ? 'You' : 'Bulldog'}</span>
                <p>{m.text}</p>
                {m.products && m.products.length > 0 && (
                  <>
                    <ul className="chat-cards" aria-label="Mentioned items">
                      {m.products.map((p) => (
                        <li key={p.product_id}>
                          <Link to={`/products/${p.product_id}`} className="chat-card">
                            <img src={api.imageUrl(p)} alt="" width="64" height="64" loading="lazy" />
                            <span className="chat-card-name">{p.name}</span>
                            <span className="chat-card-price">{formatPrice(p.price)}</span>
                          </Link>
                        </li>
                      ))}
                    </ul>
                    <span className="chat-showall muted">These items are now showing on the page.</span>
                  </>
                )}
                {m.goTo && (
                  <Link className="btn btn-secondary chat-goto" to={m.goTo.route}>
                    {m.goTo.navigate ? `Opened: ${m.goTo.label}` : m.goTo.label}
                  </Link>
                )}
              </div>
            ))}
            {busy && (
              <div className="chat-msg chat-assistant">
                <span className="chat-who">Bulldog</span>
                <p>
                  <span className="typing" aria-hidden="true">
                    <i />
                    <i />
                    <i />
                  </span>
                  <span className="visually-hidden">Checking the shelves</span>
                </p>
              </div>
            )}
          </div>
          {fresh && !busy && (
            <ul className="chat-chips" aria-label="Suggested questions">
              {SUGGESTIONS.map((s) => (
                <li key={s}>
                  <button type="button" onClick={() => void sendText(s)}>
                    {s}
                  </button>
                </li>
              ))}
            </ul>
          )}
          <form className="chat-form" onSubmit={send}>
            <label htmlFor={`${panelId}-input`} className="visually-hidden">
              Message
            </label>
            <input
              id={`${panelId}-input`}
              ref={inputRef}
              type="text"
              value={draft}
              maxLength={1000}
              placeholder="Ask about merch…"
              autoComplete="off"
              disabled={busy}
              onChange={(e) => setDraft(e.target.value)}
            />
            <button type="submit" className="btn btn-primary" disabled={busy}>
              Send
            </button>
          </form>
        </section>
      )}
      <button
        ref={toggleRef}
        type="button"
        className="chat-toggle"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((v) => !v)}
      >
        <span className="chat-toggle-dog" aria-hidden="true">
          <Bulldog size={30} />
        </span>
        {open ? 'Hide the counter' : halloween ? 'Ask the bulldog 🎃' : 'Ask the bulldog'}
      </button>
    </div>
  )
}
