// Guests can play too: their finds for the current season live in this browser until they sign in,
// when the provider banks them on the server and clears this.
const KEY = 'cc-hunt-guest'

interface Stored {
  season: string
  keys: string[]
}

export function readGuestFinds(season: string): string[] {
  try {
    const raw = localStorage.getItem(KEY)
    if (!raw) return []
    const s = JSON.parse(raw) as Stored
    return s.season === season && Array.isArray(s.keys) ? s.keys.filter((k) => typeof k === 'string') : []
  } catch {
    return []
  }
}

export function writeGuestFinds(season: string, keys: string[]): void {
  try {
    localStorage.setItem(KEY, JSON.stringify({ season, keys } satisfies Stored))
  } catch {
    // storage unavailable: the find lasts for this page only
  }
}

export function clearGuestFinds(): void {
  try {
    localStorage.removeItem(KEY)
  } catch {
    // nothing stored
  }
}
