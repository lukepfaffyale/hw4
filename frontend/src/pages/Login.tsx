import { useEffect, useState, type FormEvent } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { api, messageOf } from '../api'
import { finishSocialSignIn, socialConfigured, startSocialSignIn, type SocialProvider } from '../auth/supabase'
import { useAuth } from '../auth/useAuth'
import { useHalloween } from '../halloween/useHalloween'
import { usePageTitle } from '../usePageTitle'

export default function Login() {
  usePageTitle('Sign in')
  const navigate = useNavigate()
  const { user, signIn } = useAuth()
  const { strikeLightning } = useHalloween()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [checkingSocial, setCheckingSocial] = useState(socialConfigured)
  const [error, setError] = useState('')

  // Returning from Google/GitHub: Supabase put a session in the URL; finish it with our back end.
  useEffect(() => {
    if (!socialConfigured) return
    let cancelled = false
    finishSocialSignIn()
      .then(async (token) => {
        if (!token) return
        const res = await api.social(token)
        if (cancelled) return
        signIn(res)
        strikeLightning()
        navigate('/account')
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(messageOf(err, 'Social sign-in did not complete.'))
      })
      .finally(() => {
        if (!cancelled) setCheckingSocial(false)
      })
    return () => {
      cancelled = true
    }
  }, [navigate, signIn, strikeLightning])

  if (user) return <Navigate to="/account" replace />

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      const res = await api.login({ email: email.trim(), password })
      signIn(res)
      strikeLightning()
      navigate('/account')
    } catch (err) {
      setError(messageOf(err))
    } finally {
      setBusy(false)
    }
  }

  async function social(provider: SocialProvider) {
    setError('')
    try {
      await startSocialSignIn(provider)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not start social sign-in.')
    }
  }

  return (
    <div className="auth-page">
      <h1>Sign in</h1>
      <p className="muted">Sign in to chat with the assistant and pick up where you left off.</p>

      <div className="auth-card">
        <form className="form" onSubmit={onSubmit} noValidate>
          <div className="field">
            <label htmlFor="login-email">Email</label>
            <input
              id="login-email"
              name="email"
              type="email"
              autoComplete="email"
              required
              maxLength={254}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          <div className="field">
            <label htmlFor="login-password">Password</label>
            <input
              id="login-password"
              name="password"
              type="password"
              autoComplete="current-password"
              required
              maxLength={64}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          <div>
            <button className="btn btn-primary" type="submit" disabled={busy || checkingSocial}>
              {busy ? 'Signing in…' : 'Sign in'}
            </button>
          </div>
          <p className="status" role="status" aria-live="polite">
            {checkingSocial ? 'Checking for a social sign-in…' : error}
          </p>
        </form>

        <div className="auth-divider" role="separator" aria-label="or">
          <span>or</span>
        </div>

        <div className="social-buttons">
          <button type="button" className="btn btn-secondary" onClick={() => social('google')} disabled={!socialConfigured}>
            Continue with Google
          </button>
          <button type="button" className="btn btn-secondary" onClick={() => social('github')} disabled={!socialConfigured}>
            Continue with GitHub
          </button>
        </div>
        <p className="hint">
          {socialConfigured
            ? 'Social sign-in uses the provider’s standard sign-in. We never see your password there.'
            : 'Social sign-in is not set up on this server yet. It needs a Supabase project; see the README.'}
        </p>
      </div>

      <p>
        New here? <Link to="/create-account">Create an account</Link>.
      </p>
    </div>
  )
}
