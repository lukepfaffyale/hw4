// Easter-egg planning (Problem 4), reworked for the collection (Problem 9). The server defines the
// friends and their home pages; this file only decides which unfound friend appears on this page
// visit and where. Finds and rewards live on the server (or, for guests, in HuntProvider).
import type { HuntFriend } from '../types'

export type Spot = 'scene' | 'footer' | 'card' | 'gutter'

export interface EggPlan {
  season: string
  character: string
  name: string
  spot: Spot
  /** 0..1, used for the spot's position (scene x, card index, gutter y). */
  seed: number
}

/** Chance that an unfound friend wanders onto a page that is not its home. */
const STRAY_CHANCE = 0.35

/** Same rule as hunt.is_home on the server: "/products/*" means any single-item page. */
export function isHome(homeRoute: string, pathname: string): boolean {
  if (homeRoute.endsWith('/*')) {
    const base = homeRoute.slice(0, -2)
    return pathname.startsWith(base + '/') && pathname.length > base.length + 1
  }
  return pathname === homeRoute
}

/**
 * Decide whether a friend appears on this page visit, which one, and where. A friend always hides
 * on its home page until found (the chase: each find's riddle points to the next home page), and
 * any unfound friend may stray onto another page now and then. `?egg=<key>` forces one for
 * testing (add `&spot=footer|scene|card|gutter` to pick the spot).
 */
export function planEgg(
  pathname: string,
  search: string,
  opts: { halloween: boolean; season: string; friends: HuntFriend[]; found: ReadonlySet<string> },
): EggPlan | null {
  const params = new URLSearchParams(search)
  const forcedKey = params.get('egg')
  const forced = forcedKey ? opts.friends.find((f) => f.key === forcedKey && f.available) : undefined
  // Only friends whose day has come, and not yet found. Earliest day first, so the chase is in order.
  const candidates = opts.friends.filter((f) => f.available && !opts.found.has(f.key))
  const home = candidates.find((f) => isHome(f.home_route, pathname))
  const stray = candidates.length && Math.random() < STRAY_CHANCE ? candidates[Math.floor(Math.random() * candidates.length)] : undefined
  const friend = forced ?? home ?? stray
  if (!friend) return null

  const spots: Spot[] = ['footer']
  if (opts.halloween) spots.push('scene')
  if (pathname === '/products') spots.push('card')
  if (typeof window !== 'undefined' && window.innerWidth >= 1460) spots.push('gutter')

  const wanted = params.get('spot') as Spot | null
  const spot = wanted && spots.includes(wanted) ? wanted : spots[Math.floor(Math.random() * spots.length)]
  return { season: opts.season, character: friend.key, name: friend.name, spot, seed: Math.random() }
}
