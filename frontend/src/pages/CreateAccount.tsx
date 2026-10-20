import { useId, useState, type FormEvent } from 'react'
import { Link, Navigate, useNavigate, useSearchParams } from 'react-router-dom'
import { api, ApiError, messageOf } from '../api'
import { generateSpookyPassword, passwordIssues, RULES } from '../auth/password'
import { useAuth } from '../auth/useAuth'
import { useHalloween } from '../halloween/useHalloween'
import { usePageTitle } from '../usePageTitle'

export default function CreateAccount() {
  usePageTitle('Create Account')
  const navigate = useNavigate()
  const { user, signIn } = useAuth()
  const { strikeLightning, on: halloween } = useHalloween()
  const ids = useId()
  const [params] = useSearchParams()

  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [email, setEmail] = useState('')
  // Problem 9: a friend's referral code, prefilled from their invite link (?ref=CODE).
  const [referral, setReferral] = useState(() => (params.get('ref') ?? '').slice(0, 16))
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [show, setShow] = useState(false)
  const [suggestion, setSuggestion] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  if (user) return <Navigate to="/account" replace />

  const ctx = { email, firstName, lastName }
  const issues = passwordIssues(password, ctx)
  const mismatch = confirm.length > 0 && confirm !== password

  function roll() {
    setSuggestion(generateSpookyPassword(ctx))
  }

  function useSuggestion() {
    setPassword(suggestion)
    setConfirm(suggestion)
    setShow(true)
  }

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setError('')
    if (issues.length) {
      setError('Password needs: ' + issues.join('; ') + '.')
      return
    }
    if (confirm !== password) {
      setError('Passwords do not match.')
      return
    }
    setBusy(true)
    try {
      const res = await api.signup({
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        email: email.trim(),
        password,
        confirm_password: confirm,
        referral_code: referral.trim() || undefined,
      })
      signIn(res)
      strikeLightning()
      navigate('/account')
    } catch (err) {
      setError(err instanceof ApiError && err.issues.length ? err.issues.map((i) => i.msg).join(' ') : messageOf(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="auth-page">
      <h1>Create an account</h1>
      <p className="muted">
        An account lets the chat assistant remember you and lets you review your own history.
      </p>

      <div className="notice">
        We store your first name, last name, email and your chat messages so the bot can remember
        you. Your password is hashed before it is stored and is never kept in plain text. You can
        view or delete everything from your Account page.
      </div>
      <div className="notice notice-warn">
        Academic project: please use a <strong>test password</strong>, never one you use anywhere
        else.
      </div>

      <div className="auth-card">
        <form className="form" onSubmit={onSubmit} noValidate>
          <div className="field">
            <label htmlFor={`${ids}-first`}>First name</label>
            <input id={`${ids}-first`} type="text" autoComplete="given-name" required maxLength={60} value={firstName} onChange={(e) => setFirstName(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor={`${ids}-last`}>Last name</label>
            <input id={`${ids}-last`} type="text" autoComplete="family-name" required maxLength={60} value={lastName} onChange={(e) => setLastName(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor={`${ids}-email`}>Email</label>
            <input id={`${ids}-email`} type="email" autoComplete="email" required maxLength={254} value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor={`${ids}-ref`}>Referral code (optional)</label>
            <input
              id={`${ids}-ref`}
              type="text"
              autoComplete="off"
              maxLength={16}
              value={referral}
              placeholder="From a friend's invite link"
              onChange={(e) => setReferral(e.target.value.toUpperCase())}
              aria-describedby={`${ids}-ref-hint`}
            />
            <span id={`${ids}-ref-hint`} className="hint">
              Your friend gets credit toward the hidden-friends rewards. An unknown code is simply ignored.
            </span>
          </div>

          <fieldset className="generator">
            <legend>{halloween ? '🎲 Need a password? Roll a spooky one' : '🎲 Need a password? Roll one'}</legend>
            <div className="generator-row">
              <button type="button" className="btn btn-secondary" onClick={roll}>
                {suggestion ? 'Roll again' : 'Roll a password'}
              </button>
              {suggestion && (
                <>
                  <output className="suggestion" aria-live="polite">
                    {suggestion}
                  </output>
                  <button type="button" className="btn btn-primary" onClick={useSuggestion}>
                    Use this password
                  </button>
                </>
              )}
            </div>
            <p className="hint">
              Made in your browser, never sent anywhere until you submit. Write it down somewhere
              safe. It is hashed before it is stored.
            </p>
          </fieldset>

          <div className="field">
            <div className="label-row">
              <label htmlFor={`${ids}-password`}>Password</label>
              <button type="button" className="link-button" aria-pressed={show} onClick={() => setShow((v) => !v)}>
                {show ? 'Hide password' : 'Show password'}
              </button>
            </div>
            <input
              id={`${ids}-password`}
              type={show ? 'text' : 'password'}
              autoComplete="new-password"
              required
              minLength={12}
              maxLength={64}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              aria-describedby={`${ids}-rules`}
            />
            <ul id={`${ids}-rules`} className="rules" aria-label="Password requirements">
              {RULES.map((r) => {
                const ok = password.length > 0 && r.test(password, ctx)
                return (
                  <li key={r.id} className={ok ? 'ok' : 'todo'}>
                    <span aria-hidden="true">{ok ? '✓' : '○'}</span> {r.label}
                    <span className="visually-hidden">{ok ? ' (met)' : ' (not met)'}</span>
                  </li>
                )
              })}
            </ul>
          </div>

          <div className="field">
            <label htmlFor={`${ids}-confirm`}>Confirm password</label>
            <input
              id={`${ids}-confirm`}
              type={show ? 'text' : 'password'}
              autoComplete="new-password"
              required
              maxLength={64}
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              aria-invalid={mismatch}
              aria-describedby={`${ids}-match`}
            />
            <span id={`${ids}-match`} className="hint">
              {mismatch ? 'Passwords do not match yet.' : confirm && confirm === password ? 'Passwords match.' : ''}
            </span>
          </div>

          <div>
            <button className="btn btn-primary" type="submit" disabled={busy}>
              {busy ? 'Creating…' : 'Create account'}
            </button>
          </div>
          <p className="status" role="status" aria-live="polite">
            {error}
          </p>
        </form>
      </div>

      <p>
        Already have an account? <Link to="/login">Sign in</Link>.
      </p>
    </div>
  )
}
