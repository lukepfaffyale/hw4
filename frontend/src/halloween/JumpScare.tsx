import { useEffect, useState } from 'react'
import { useHalloween } from './useHalloween'

const CHARACTERS = [
  { emoji: '👻', line: 'Boo!' },
  { emoji: '💀', line: 'Rattle rattle!' },
  { emoji: '🎃', line: 'Happy Halloween!' },
  { emoji: '🦇', line: 'Screech!' },
  { emoji: '🧙', line: 'Hex you later!' },
]

const SHOW_MS = 4000

/**
 * A friendly pop-out that appears over a product photo when Halloween mode is on.
 * Safe by design: no flashing, no sound, respects reduced motion (fades instead of
 * springing), auto-hides, and can be dismissed by keyboard.
 *
 * `trigger` is a counter: every change replays the surprise with the next character.
 */
export default function JumpScare({ trigger }: { trigger: number }) {
  const { on, reducedMotion } = useHalloween()
  const [hiddenFor, setHiddenFor] = useState(0)
  const [seed] = useState(() => Math.floor(Math.random() * CHARACTERS.length))

  useEffect(() => {
    if (!on || trigger === 0) return
    const t = window.setTimeout(() => setHiddenFor(trigger), SHOW_MS)
    return () => window.clearTimeout(t)
  }, [trigger, on])

  const visible = on && trigger > 0 && hiddenFor !== trigger
  if (!visible) return null

  const c = CHARACTERS[(seed + trigger) % CHARACTERS.length]
  return (
    <div className={`jump-scare ${reducedMotion ? 'jump-scare-calm' : ''}`} role="status" aria-live="polite">
      <span className="jump-scare-figure" aria-hidden="true">
        {c.emoji}
      </span>
      <span className="jump-scare-line">{c.line}</span>
      <button type="button" className="jump-scare-dismiss" onClick={() => setHiddenFor(trigger)}>
        Dismiss
      </button>
    </div>
  )
}
