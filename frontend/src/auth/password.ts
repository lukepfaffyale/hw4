// Password policy, mirrored from backend/auth.py (the server is the authority), plus the
// Halloween password roller. Everything here runs in the browser; nothing is logged.

export const PASSWORD_MIN = 12
export const PASSWORD_MAX = 64

export interface PolicyContext {
  email?: string
  firstName?: string
  lastName?: string
}

export interface Rule {
  id: string
  label: string
  test: (pw: string, ctx: PolicyContext) => boolean
}

const COMMON = [
  'password', 'password1', 'password123', 'passw0rd', 'qwerty', 'letmein', 'welcome', 'iloveyou',
  'admin', '123456', '12345678', '123456789', '1234567890', 'abc123', 'monkey', 'dragon', 'football',
  'baseball', 'sunshine', 'princess', 'trustno1', 'yale', 'bulldogs', 'campuscustoms', 'changeme',
  'secret123', 'letmein1',
]

function containsPersonal(pw: string, value?: string): boolean {
  const v = (value ?? '').trim().toLowerCase()
  return v.length >= 3 && pw.toLowerCase().includes(v)
}

export const RULES: Rule[] = [
  { id: 'length', label: `At least ${PASSWORD_MIN} characters`, test: (pw) => pw.length >= PASSWORD_MIN && pw.length <= PASSWORD_MAX },
  { id: 'lower', label: 'A lowercase letter', test: (pw) => /[a-z]/.test(pw) },
  { id: 'upper', label: 'An uppercase letter', test: (pw) => /[A-Z]/.test(pw) },
  { id: 'digit', label: 'A number', test: (pw) => /[0-9]/.test(pw) },
  { id: 'symbol', label: 'A symbol', test: (pw) => /[^A-Za-z0-9]/.test(pw) },
  { id: 'spaces', label: 'No spaces', test: (pw) => !/\s/.test(pw) && !pw.startsWith('!') },
  {
    id: 'common',
    label: 'Not based on a common password',
    test: (pw) => {
      const lowered = pw.toLowerCase()
      const squashed = lowered.replace(/[^a-z0-9]/g, '')
      return !COMMON.includes(lowered) && !COMMON.includes(squashed) && !COMMON.some((w) => w.length >= 6 && squashed.includes(w))
    },
  },
  {
    id: 'personal',
    label: 'Not your name or email',
    test: (pw, ctx) =>
      !containsPersonal(pw, ctx.email?.split('@')[0]) && !containsPersonal(pw, ctx.firstName) && !containsPersonal(pw, ctx.lastName),
  },
  { id: 'repeat', label: 'No character repeated 4 times in a row', test: (pw) => !/(.)\1\1\1/.test(pw) },
]

export function passwordIssues(pw: string, ctx: PolicyContext = {}): string[] {
  return RULES.filter((r) => !r.test(pw, ctx)).map((r) => r.label)
}

// ------------------------------------------------------------------ spooky roller

const WORDS = [
  'Pumpkin', 'Witch', 'Ghost', 'Bat', 'Skeleton', 'Cauldron', 'Haunted', 'Lantern', 'Spider',
  'Goblin', 'Phantom', 'Raven', 'Candy', 'Moonlit', 'Crypt', 'Zombie', 'Vampire', 'Cobweb',
  'Potion', 'Broomstick', 'Mummy', 'Werewolf', 'Graveyard', 'Specter', 'Scarecrow', 'Banshee',
  'Gourd', 'Midnight', 'Howling', 'Cackle', 'Ghoul', 'Tombstone', 'Bulldog', 'Handsome',
]
const SEPARATORS = ['-', '_', '.', '~']
const SYMBOLS = ['!', '?', '#', '$', '%', '&', '*', '@']

function pick<T>(list: readonly T[]): T {
  const buf = new Uint32Array(1)
  crypto.getRandomValues(buf)
  return list[buf[0] % list.length]
}

function digits(n: number): string {
  const buf = new Uint8Array(n)
  crypto.getRandomValues(buf)
  return Array.from(buf, (b) => String(b % 10)).join('')
}

/** Three Halloween words, a separator, two or three digits and a symbol, e.g. Witch-Cauldron-Raven42! */
export function generateSpookyPassword(ctx: PolicyContext = {}): string {
  for (let attempt = 0; attempt < 12; attempt++) {
    const sep = pick(SEPARATORS)
    const words = [pick(WORDS), pick(WORDS), pick(WORDS)]
    const candidate = `${words.join(sep)}${digits(attempt < 6 ? 2 : 3)}${pick(SYMBOLS)}`
    if (passwordIssues(candidate, ctx).length === 0) return candidate
  }
  // Essentially unreachable, but never return something weak.
  return `Pumpkin-Moonlit-Raven${digits(3)}!`
}
