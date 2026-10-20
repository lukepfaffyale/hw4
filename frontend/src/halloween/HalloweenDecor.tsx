import { useHalloween } from './useHalloween'

/** A spider web drawn into one corner. The stroke "draws itself" when motion is allowed. */
export function CornerWeb({ corner }: { corner: 'tl' | 'tr' | 'bl' | 'br' }) {
  // Spokes and rings radiating from the corner (0,0). Flipped per corner with CSS.
  const spokes = [0, 15, 30, 45, 60, 75, 90].map((deg) => {
    const r = (deg * Math.PI) / 180
    return `M0 0 L${(Math.cos(r) * 150).toFixed(1)} ${(Math.sin(r) * 150).toFixed(1)}`
  })
  const rings = [35, 65, 95, 125].map((rad) => `M${rad} 0 A${rad} ${rad} 0 0 1 0 ${rad}`)
  return (
    <div className={`web web-${corner}`} aria-hidden="true">
      <svg viewBox="0 0 150 150" width="150" height="150">
        {[...spokes, ...rings].map((d, i) => (
          <path key={i} d={d} className="web-line" style={{ animationDelay: `${i * 120}ms` }} />
        ))}
      </svg>
      <span className="spider">🕷️</span>
    </div>
  )
}

/**
 * Fixed decorations for wide screens only: webs in the four corners, bats and a ghost in the
 * empty side gutters outside the content column. Hidden entirely when the gutters are too
 * narrow, so nothing ever sits over text. The night scene (`HalloweenScene`) carries the
 * Halloween mood on every screen size.
 */
export default function HalloweenDecor() {
  const { on } = useHalloween()
  if (!on) return null
  return (
    <div className="halloween-decor" aria-hidden="true">
      <CornerWeb corner="tl" />
      <CornerWeb corner="tr" />
      <CornerWeb corner="bl" />
      <CornerWeb corner="br" />
      <span className="bat bat-1">🦇</span>
      <span className="bat bat-2">🦇</span>
      <span className="bat bat-3">🦇</span>
      <span className="ghost-drift">👻</span>
    </div>
  )
}
