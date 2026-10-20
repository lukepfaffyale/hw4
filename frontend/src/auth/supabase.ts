// Social sign-in goes through Supabase Auth's OAuth flow with the provider's defaults and
// minimum scopes. We never see a provider password or token: Supabase hands the browser a
// short-lived access token, the back end asks Supabase to confirm it, and that is all we keep.
import { createClient, type SupabaseClient } from '@supabase/supabase-js'

export type SocialProvider = 'google' | 'github'

const URL = (import.meta.env.VITE_SUPABASE_URL as string | undefined) ?? ''
const ANON = (import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined) ?? ''

/** True when the front end has a Supabase project to send shoppers to. */
export const socialConfigured = Boolean(URL && ANON)

let client: SupabaseClient | null = null

function sb(): SupabaseClient {
  if (!client) {
    client = createClient(URL, ANON, {
      auth: { persistSession: true, detectSessionInUrl: true, flowType: 'pkce' },
    })
  }
  return client
}

export async function startSocialSignIn(provider: SocialProvider): Promise<void> {
  const { error } = await sb().auth.signInWithOAuth({
    provider,
    options: { redirectTo: `${window.location.origin}/login` },
  })
  if (error) throw new Error(error.message)
}

/**
 * After the provider redirects back to /login, return the Supabase access token if there is
 * one, then drop the browser-side Supabase session: our own back-end session takes over.
 */
export async function finishSocialSignIn(): Promise<string | null> {
  const { data } = await sb().auth.getSession()
  const token = data.session?.access_token ?? null
  if (token) await sb().auth.signOut({ scope: 'local' })
  return token
}
