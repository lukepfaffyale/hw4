// The hidden friends, drawn as inline SVG (no image files). Decorative; the button around them
// carries the accessible name. The cast is seven original creatures (fan-made nods, credited in docs/governance.md): Bramble, Dusk, Pip,
// Whiskerline, Snaggle, Cinder and Hush); each season dresses them in trick-or-treat costumes
// drawn as overlays placed by each character's anchors. Keys come from the server as
// `<character>-<costume>`; a pairing this build cannot draw shows as a silhouette.
import type { ReactElement } from 'react'

export type Costume = 'witch' | 'ghost' | 'zombie' | 'skeleton' | 'vampire' | 'mummy' | 'pumpkin' | 'devil' | 'plain'
const COSTUMES = new Set<Costume>(['witch', 'ghost', 'zombie', 'skeleton', 'vampire', 'mummy', 'pumpkin', 'devil'])

/** Where a costume attaches on a character, in the 64x64 box. */
interface Anchor {
  cx: number
  top: number // top of the head (hats sit here)
  hw: number // half width of the body
  eyeY: number
  eyeDx: number
  mouthY: number
  bottom: number
}

const A = {
  totoro: { cx: 32, top: 14, hw: 24, eyeY: 26, eyeDx: 8, mouthY: 31, bottom: 62 },
  chu: { cx: 32, top: 21, hw: 19, eyeY: 33, eyeDx: 6.5, mouthY: 37, bottom: 60 },
  chibi: { cx: 32, top: 30, hw: 14, eyeY: 41, eyeDx: 5, mouthY: 45, bottom: 58 },
  catbus: { cx: 32, top: 18, hw: 26, eyeY: 30, eyeDx: 9, mouthY: 39, bottom: 58 },
  labubu: { cx: 32, top: 17, hw: 20, eyeY: 30, eyeDx: 7, mouthY: 37, bottom: 62 },
  soot: { cx: 32, top: 10, hw: 22, eyeY: 30, eyeDx: 7, mouthY: 40, bottom: 58 },
  noface: { cx: 32, top: 9, hw: 12, eyeY: 21, eyeDx: 3, mouthY: 28, bottom: 62 },
} satisfies Record<string, Anchor>

type CharacterKey = keyof typeof A

/** One costume, drawn under (cape) or over (everything else) the character. */
function CostumeLayer({ kind, a, layer }: { kind: Costume; a: Anchor; layer: 'under' | 'over' }) {
  const { cx, top, hw, eyeY, eyeDx, mouthY, bottom } = a
  if (layer === 'under') {
    if (kind !== 'vampire') return null
    return (
      <g>
        <polygon points={`${cx - hw - 6},${bottom} ${cx},${top + 8} ${cx + hw + 6},${bottom}`} fill="#2a1232" />
        <polygon points={`${cx - hw},${bottom - 2} ${cx},${top + 14} ${cx + hw},${bottom - 2}`} fill="#8b1a2b" />
      </g>
    )
  }
  switch (kind) {
    case 'witch':
      return (
        <g>
          <ellipse cx={cx} cy={top + 2} rx={hw * 0.85} ry="3.6" fill="#1b1330" />
          <polygon points={`${cx - hw * 0.5},${top + 2} ${cx + 2},${top - 18} ${cx + hw * 0.5},${top + 2}`} fill="#2a1d4a" />
          <path d={`M${cx - hw * 0.42} ${top} Q${cx} ${top - 4} ${cx + hw * 0.42} ${top}`} stroke="#ff4fa3" strokeWidth="2.4" fill="none" />
          <circle cx={cx + 3} cy={top - 16} r="2" fill="#ffd166" />
        </g>
      )
    case 'ghost':
      return (
        <g>
          <path
            d={`M${cx - hw} ${top + 10} Q${cx} ${top - 4} ${cx + hw} ${top + 10} L${cx + hw} ${bottom - 4} L${cx + hw * 0.7} ${bottom - 9} L${cx + hw * 0.4} ${bottom - 3} L${cx + hw * 0.1} ${bottom - 9} L${cx - hw * 0.2} ${bottom - 3} L${cx - hw * 0.5} ${bottom - 9} L${cx - hw * 0.8} ${bottom - 3} L${cx - hw} ${bottom - 8} Z`}
            fill="#f7f7fb"
          />
          <ellipse cx={cx - eyeDx} cy={eyeY} rx="2.6" ry="3.4" fill="#1d1d1d" />
          <ellipse cx={cx + eyeDx} cy={eyeY} rx="2.6" ry="3.4" fill="#1d1d1d" />
          <ellipse cx={cx} cy={mouthY + 2} rx="2" ry="2.6" fill="#1d1d1d" />
        </g>
      )
    case 'zombie':
      return (
        <g>
          <ellipse cx={cx} cy={eyeY + 3} rx={hw * 0.72} ry={hw * 0.58} fill="#6fae6a" opacity="0.32" />
          <path d={`M${cx - eyeDx - 5} ${eyeY - 7} l7 9 M${cx - eyeDx - 4} ${eyeY - 5} l2 -1.5 M${cx - eyeDx - 2} ${eyeY - 2} l2 -1.5 M${cx - eyeDx} ${eyeY + 1} l2 -1.5`} stroke="#3f6b3a" strokeWidth="1.1" fill="none" />
          <rect x={cx - hw - 11} y={mouthY + 9} width="13" height="5" rx="2" fill="#2f4f2f" />
          <rect x={cx + hw - 2} y={mouthY + 9} width="13" height="5" rx="2" fill="#2f4f2f" />
          <circle cx={cx - hw - 12} cy={mouthY + 11.5} r="2.6" fill="#8fc48a" />
          <circle cx={cx + hw + 12} cy={mouthY + 11.5} r="2.6" fill="#8fc48a" />
        </g>
      )
    case 'skeleton':
      return (
        <g stroke="#f4f4f4" strokeWidth="2" fill="none" strokeLinecap="round">
          <path d={`M${cx} ${mouthY + 6} v${Math.max(8, bottom - mouthY - 10)}`} />
          <path d={`M${cx - 8} ${mouthY + 9} q8 4 16 0 M${cx - 8} ${mouthY + 13} q8 4 16 0 M${cx - 7} ${mouthY + 17} q7 3 14 0`} />
          <path d={`M${cx - eyeDx - 5} ${eyeY - 5} l5 2 M${cx + eyeDx + 5} ${eyeY - 5} l-5 2`} strokeWidth="1.5" />
        </g>
      )
    case 'vampire':
      return (
        <g>
          <polygon points={`${cx - 5},${mouthY + 1} ${cx - 3},${mouthY + 6} ${cx - 1},${mouthY + 1}`} fill="#fff" />
          <polygon points={`${cx + 1},${mouthY + 1} ${cx + 3},${mouthY + 6} ${cx + 5},${mouthY + 1}`} fill="#fff" />
          <polygon points={`${cx - 6},${top + 4} ${cx},${top + 11} ${cx + 6},${top + 4}`} fill="#1d1d1d" />
          <path d={`M${cx - hw * 0.8} ${bottom - 8} l${hw * 0.35} -6 M${cx + hw * 0.8} ${bottom - 8} l-${hw * 0.35} -6`} stroke="#f2f2f2" strokeWidth="2" />
        </g>
      )
    case 'mummy':
      return (
        <g fill="#f3efe4" stroke="#cfc6b3" strokeWidth="0.6">
          <rect x={cx - hw - 2} y={top + 5} width={hw * 2 + 4} height="4.5" rx="2" transform={`rotate(-6 ${cx} ${top + 7})`} />
          <rect x={cx - hw - 2} y={eyeY + 7} width={hw * 2 + 4} height="4.5" rx="2" transform={`rotate(5 ${cx} ${eyeY + 9})`} />
          <rect x={cx - hw - 2} y={mouthY + 8} width={hw * 2 + 4} height="4.5" rx="2" transform={`rotate(-5 ${cx} ${mouthY + 10})`} />
          <rect x={cx - hw - 2} y={bottom - 11} width={hw * 2 + 4} height="4.5" rx="2" transform={`rotate(4 ${cx} ${bottom - 9})`} />
        </g>
      )
    case 'pumpkin':
      return (
        <g>
          <rect x={cx - 1.5} y={top - 9} width="3" height="6" fill="#2f5a1e" />
          <ellipse cx={cx} cy={top + 3} rx={hw * 0.68} ry="7" fill="#f4871e" />
          <path d={`M${cx - hw * 0.3} ${top - 3} q-2 6 0 12 M${cx + hw * 0.3} ${top - 3} q2 6 0 12`} stroke="#c9640e" strokeWidth="1.2" fill="none" />
          <polygon points={`${cx - 6},${top + 2} ${cx - 2},${top + 2} ${cx - 4},${top - 1}`} fill="#2b1500" />
          <polygon points={`${cx + 2},${top + 2} ${cx + 6},${top + 2} ${cx + 4},${top - 1}`} fill="#2b1500" />
          <circle cx={cx + hw - 1} cy={bottom - 8} r="6" fill="#f4871e" />
          <path d={`M${cx + hw - 6} ${bottom - 10} q5 -8 10 0`} stroke="#2b1500" strokeWidth="1.5" fill="none" />
          <polygon points={`${cx + hw - 4},${bottom - 9} ${cx + hw - 2},${bottom - 9} ${cx + hw - 3},${bottom - 11}`} fill="#2b1500" />
          <polygon points={`${cx + hw},${bottom - 9} ${cx + hw + 2},${bottom - 9} ${cx + hw + 1},${bottom - 11}`} fill="#2b1500" />
          <path d={`M${cx + hw - 4} ${bottom - 6} q3 2 6 0`} stroke="#2b1500" strokeWidth="1.2" fill="none" />
        </g>
      )
    case 'devil':
      return (
        <g>
          <polygon points={`${cx - hw * 0.6},${top + 9} ${cx - hw * 0.42},${top - 5} ${cx - hw * 0.25},${top + 8}`} fill="#c8102e" />
          <polygon points={`${cx + hw * 0.6},${top + 9} ${cx + hw * 0.42},${top - 5} ${cx + hw * 0.25},${top + 8}`} fill="#c8102e" />
          <path d={`M${cx + hw + 7} ${bottom - 2} V${top + 16}`} stroke="#c8102e" strokeWidth="2.2" strokeLinecap="round" />
          <path d={`M${cx + hw + 2} ${top + 20} v-6 q5 -4 10 0 v6 M${cx + hw + 7} ${top + 16} v-6`} stroke="#c8102e" strokeWidth="2" fill="none" strokeLinecap="round" />
          <path d={`M${cx - hw + 2} ${bottom - 6} q-10 2 -8 -8`} stroke="#c8102e" strokeWidth="2" fill="none" strokeLinecap="round" />
          <polygon points={`${cx - hw - 9},${bottom - 15} ${cx - hw - 3},${bottom - 13} ${cx - hw - 7},${bottom - 9}`} fill="#c8102e" />
        </g>
      )
    default:
      return null
  }
}

function Frame({ costume, a, children }: { costume: Costume; a: Anchor; children: ReactElement | ReactElement[] }) {
  return (
    <svg viewBox="0 0 64 64" aria-hidden="true" focusable="false">
      <CostumeLayer kind={costume} a={a} layer="under" />
      {children}
      <CostumeLayer kind={costume} a={a} layer="over" />
    </svg>
  )
}

function Bramble({ costume }: { costume: Costume }) {
  return (
    <Frame costume={costume} a={A.totoro}>
      <polygon points="18,20 22,3 30,20" fill="#7d8591" />
      <polygon points="46,20 42,3 34,20" fill="#7d8591" />
      <circle cx="32" cy="38" r="24" fill="#8a919c" />
      <ellipse cx="32" cy="45" rx="16" ry="14" fill="#dfe2e8" />
      <path d="M24 38 l4 -3 l4 3 M30 44 l4 -3 l4 3 M22 47 l4 -3 l4 3 M38 50 l4 -3 l4 3" stroke="#8a919c" strokeWidth="1.5" fill="none" />
      <circle cx="24" cy="26" r="3.4" fill="#fff" />
      <circle cx="40" cy="26" r="3.4" fill="#fff" />
      <circle cx="24.6" cy="26.3" r="1.6" fill="#1d1d1d" />
      <circle cx="40.6" cy="26.3" r="1.6" fill="#1d1d1d" />
      <ellipse cx="32" cy="30.5" rx="2.2" ry="1.3" fill="#2b2b2b" />
      <path d="M8 27 l12 2.5 M7 33 l13 0.5 M56 27 l-12 2.5 M57 33 l-13 0.5" stroke="#2b2b2b" strokeWidth="1" />
    </Frame>
  )
}

function Dusk({ costume }: { costume: Costume }) {
  return (
    <Frame costume={costume} a={A.chu}>
      <polygon points="22,27 25,12 31,27" fill="#5f6f94" />
      <polygon points="42,27 39,12 33,27" fill="#5f6f94" />
      <circle cx="32" cy="42" r="19" fill="#6f7fa3" />
      <ellipse cx="32" cy="48" rx="12" ry="10" fill="#e6e9f1" />
      <path d="M27 46 l3 -2.5 l3 2.5 M30 51 l3 -2.5 l3 2.5" stroke="#6f7fa3" strokeWidth="1.3" fill="none" />
      <circle cx="25.5" cy="33" r="2.8" fill="#fff" />
      <circle cx="38.5" cy="33" r="2.8" fill="#fff" />
      <circle cx="26" cy="33.3" r="1.4" fill="#1d1d1d" />
      <circle cx="39" cy="33.3" r="1.4" fill="#1d1d1d" />
      <ellipse cx="32" cy="37" rx="1.8" ry="1.1" fill="#2b2b2b" />
      <path d="M14 35 l9 1.5 M14 39 l9 0 M50 35 l-9 1.5 M50 39 l-9 0" stroke="#2b2b2b" strokeWidth="0.9" />
    </Frame>
  )
}

function Pip({ costume }: { costume: Costume }) {
  return (
    <Frame costume={costume} a={A.chibi}>
      <polygon points="25,34 27,25 31,34" fill="#e8e8ea" />
      <polygon points="39,34 37,25 33,34" fill="#e8e8ea" />
      <circle cx="32" cy="46" r="14" fill="#f5f5f7" />
      <circle cx="27" cy="41" r="1.6" fill="#1d1d1d" />
      <circle cx="37" cy="41" r="1.6" fill="#1d1d1d" />
      <path d="M18 43 l7 1 M18 46 l7 0 M46 43 l-7 1 M46 46 l-7 0" stroke="#5a5a5a" strokeWidth="0.8" />
    </Frame>
  )
}

function Whiskerline({ costume }: { costume: Costume }) {
  return (
    <Frame costume={costume} a={A.catbus}>
      <polygon points="12,26 15,14 24,24" fill="#d97a2b" />
      <polygon points="52,26 49,14 40,24" fill="#d97a2b" />
      <ellipse cx="32" cy="40" rx="26" ry="18" fill="#e8923a" />
      <path d="M10 36 q6 -2 8 4 M46 36 q6 -2 8 4 M18 52 q5 -3 9 2 M38 52 q5 -3 9 2" stroke="#8c4a16" strokeWidth="3" fill="none" strokeLinecap="round" />
      <ellipse cx="23" cy="30" rx="4.5" ry="5" fill="#ffd94a" />
      <ellipse cx="41" cy="30" rx="4.5" ry="5" fill="#ffd94a" />
      <ellipse cx="23" cy="30" rx="1.4" ry="3.6" fill="#1d1d1d" />
      <ellipse cx="41" cy="30" rx="1.4" ry="3.6" fill="#1d1d1d" />
      <path d="M16 38 Q32 52 48 38 Z" fill="#3a1a08" />
      <path d="M16 38 l2.5 4 l2.5 -4 l2.5 4 l2.5 -4 l2.5 4 l2.5 -4 l2.5 4 l2.5 -4 l2.5 4 l2.5 -4 l2.5 4 l2.5 -4" fill="#fff" />
      <rect x="14" y="50" width="6" height="5" rx="1" fill="#ffd94a" opacity="0.9" />
      <rect x="24" y="52" width="6" height="5" rx="1" fill="#ffd94a" opacity="0.9" />
      <rect x="34" y="52" width="6" height="5" rx="1" fill="#ffd94a" opacity="0.9" />
      <rect x="44" y="50" width="6" height="5" rx="1" fill="#ffd94a" opacity="0.9" />
      <path d="M6 36 l10 0 M6 40 l10 1 M58 36 l-10 0 M58 40 l-10 1" stroke="#3a1a08" strokeWidth="0.9" />
    </Frame>
  )
}

function Snaggle({ costume }: { costume: Costume }) {
  return (
    <Frame costume={costume} a={A.labubu}>
      <ellipse cx="21" cy="15" rx="5.5" ry="14" fill="#d7b48c" transform="rotate(-14 21 15)" />
      <ellipse cx="43" cy="15" rx="5.5" ry="14" fill="#d7b48c" transform="rotate(14 43 15)" />
      <ellipse cx="32" cy="57" rx="12" ry="8" fill="#d7b48c" />
      <ellipse cx="32" cy="35" rx="20" ry="18" fill="#e9caa4" />
      <circle cx="25" cy="30" r="4.2" fill="#fff" />
      <circle cx="39" cy="30" r="4.2" fill="#fff" />
      <circle cx="25.6" cy="31" r="2.3" fill="#1d1d1d" />
      <circle cx="39.6" cy="31" r="2.3" fill="#1d1d1d" />
      <ellipse cx="32" cy="36.5" rx="1.8" ry="1.2" fill="#3a2a2a" />
      <path d="M19 40 Q32 52 45 40 Z" fill="#8b2b3a" />
      <path d="M19 40 l2.6 4 l2.6 -4 l2.6 4 l2.6 -4 l2.6 4 l2.6 -4 l2.6 4 l2.6 -4 l2.6 4 l2.6 -4" fill="#fff" />
    </Frame>
  )
}

const SPIKES = Array.from({ length: 16 }, (_, i) => {
  const a = (i / 16) * Math.PI * 2
  return `${32 + Math.cos(a) * 25},${34 + Math.sin(a) * 25} ${32 + Math.cos(a + 0.2) * 18},${34 + Math.sin(a + 0.2) * 18}`
}).join(' ')

function Cinder({ costume }: { costume: Costume }) {
  return (
    <Frame costume={costume} a={A.soot}>
      <polygon points={SPIKES} fill="#171717" />
      <circle cx="32" cy="34" r="19" fill="#202020" />
      <circle cx="25" cy="30" r="5.5" fill="#fff" />
      <circle cx="39" cy="30" r="5.5" fill="#fff" />
      <circle cx="25.8" cy="30.5" r="2.4" fill="#111" />
      <circle cx="39.8" cy="30.5" r="2.4" fill="#111" />
    </Frame>
  )
}

function Hush({ costume }: { costume: Costume }) {
  return (
    <Frame costume={costume} a={A.noface}>
      <path d="M20 62 Q16 36 24 18 Q32 8 40 18 Q48 36 44 62 Z" fill="#141418" />
      <path d="M22 60 Q20 40 26 26 Q32 18 38 26 Q44 40 42 60 Z" fill="#2a2140" opacity="0.6" />
      <path d="M25 14 Q32 9 39 14 Q42 22 39 30 Q32 34 25 30 Q22 22 25 14 Z" fill="#f2f2f2" />
      <path d="M26 19 q3 -1 5 1 M38 19 q-3 -1 -5 1" stroke="#7c4d8f" strokeWidth="2" fill="none" />
      <path d="M26 24 q3 2 5 0 M38 24 q-3 2 -5 0" stroke="#7c4d8f" strokeWidth="1.5" fill="none" />
      <ellipse cx="29" cy="21" rx="1.6" ry="2.2" fill="#141418" />
      <ellipse cx="35" cy="21" rx="1.6" ry="2.2" fill="#141418" />
      <path d="M29 28 q3 2 6 0" stroke="#141418" strokeWidth="1.2" fill="none" />
    </Frame>
  )
}

/** A friend not yet drawable (or not yet found): a soft silhouette with a question mark. */
function Silhouette() {
  return (
    <svg viewBox="0 0 64 64" aria-hidden="true" focusable="false">
      <circle cx="32" cy="36" r="22" fill="#2a3a5c" />
      <polygon points="18,22 22,6 30,22" fill="#2a3a5c" />
      <polygon points="46,22 42,6 34,22" fill="#2a3a5c" />
      <text x="32" y="44" textAnchor="middle" fontSize="22" fontWeight="800" fill="#b8c0d0">
        ?
      </text>
    </svg>
  )
}

/** A friend whose day has not come: the silhouette with a small padlock. */
function Locked() {
  return (
    <svg viewBox="0 0 64 64" aria-hidden="true" focusable="false">
      <circle cx="32" cy="36" r="22" fill="#1b2740" />
      <rect x="24" y="33" width="16" height="13" rx="3" fill="#b8c0d0" />
      <path d="M27 33 v-5 a5 5 0 0 1 10 0 v5" stroke="#b8c0d0" strokeWidth="2.5" fill="none" />
    </svg>
  )
}

const BASE: Record<CharacterKey, (c: Costume) => ReactElement> = {
  totoro: (c) => <Bramble costume={c} />,
  chu: (c) => <Dusk costume={c} />,
  chibi: (c) => <Pip costume={c} />,
  catbus: (c) => <Whiskerline costume={c} />,
  labubu: (c) => <Snaggle costume={c} />,
  soot: (c) => <Cinder costume={c} />,
  noface: (c) => <Hush costume={c} />,
}

export function CharacterArt({ character }: { character: string }) {
  if (character === 'locked') return <Locked />
  const [base, costume] = character.split('-') as [string, string | undefined]
  if (!(base in BASE)) return <Silhouette />
  if (costume !== undefined && !COSTUMES.has(costume as Costume)) return <Silhouette />
  return BASE[base as CharacterKey]((costume as Costume | undefined) ?? 'plain')
}
