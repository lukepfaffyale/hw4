import { createContext } from 'react'
import type { AuthResponse, UserPublic } from '../types'

export interface AuthState {
  user: UserPublic | null
  token: string | null
  signIn: (res: AuthResponse) => void
  signOut: () => void
}

export const AuthContext = createContext<AuthState | null>(null)
