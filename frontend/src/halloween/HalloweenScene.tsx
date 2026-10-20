import { useEffect, useState } from 'react'
import EasterEgg from '../eggs/EasterEgg'
import { useEgg } from '../eggs/useEgg'
import { CornerWeb } from './HalloweenDecor'
import { useHalloween } from './useHalloween'
import './scene.css'

const STRIKE_MS = 1800

// Composition is 1000 x 220 and cropped from the centre (xMidYMax slice), so the important
// parts (storm, house, graveyard, moon) sit between x = 220 and x = 860.
const STARS: Array<[number, number, number]> = [
  [40, 30, 1.2], [110, 70, 0.9], [180, 22, 1.1], [300, 14, 0.8], [470, 18, 1.3], [540, 50, 0.9],
  [600, 26, 1.1], [660, 72, 0.8], [720, 20, 1.2], [760, 58, 0.9], [930, 24, 1.1], [980, 80, 0.8],
  [500, 90, 0.7], [880, 110, 0.8], [250, 100, 0.7], [820, 20, 1.0],
]

function Tombstone({ x, tilt = 0, cross = false }: { x: number; tilt?: number; cross?: boolean }) {
  return (
    <g transform={`translate(${x} 170) rotate(${tilt})`}>
      {cross ? (
        <>
          <rect x="-3" y="-34" width="6" height="34" fill="#12152b" stroke="#262b4e" strokeWidth="1" />
          <rect x="-11" y="-26" width="22" height="6" fill="#12152b" stroke="#262b4e" strokeWidth="1" />
        </>
      ) : (
        <>
          <rect x="-11" y="-30" width="22" height="32" rx="9" fill="#12152b" stroke="#262b4e" strokeWidth="1" />
          <text x="0" y="-12" textAnchor="middle" fontSize="7" fill="#3c4270" fontFamily="serif">
            RIP
          </text>
        </>
      )}
    </g>
  )
}

function Pumpkin({ x, y, r = 8 }: { x: number; y: number; r?: number }) {
  return (
    <g transform={`translate(${x} ${y})`}>
      <rect x="-1.5" y={-r - 4} width="3" height="5" fill="#2f5a1e" />
      <ellipse cx="0" cy="0" rx={r} ry={r * 0.85} fill="#ff8c1a" />
      <ellipse cx="0" cy="0" rx={r * 0.55} ry={r * 0.85} fill="none" stroke="#e06f00" strokeWidth="1" />
      <polygon points={`${-r * 0.5},${-r * 0.3} ${-r * 0.2},${-r * 0.3} ${-r * 0.35},${-r * 0.6}`} fill="#2a1200" />
      <polygon points={`${r * 0.5},${-r * 0.3} ${r * 0.2},${-r * 0.3} ${r * 0.35},${-r * 0.6}`} fill="#2a1200" />
      <path d={`M${-r * 0.5} ${r * 0.2} q ${r * 0.5} ${r * 0.5} ${r} 0`} fill="#2a1200" />
    </g>
  )
}

function Crow({ className, y }: { className: string; y: number }) {
  return (
    <g transform={`translate(0 ${y})`}>
      <g className={`crow ${className}`}>
        <path className="wings" d="M-14 0 Q-7 -9 0 0 Q7 -9 14 0" fill="none" stroke="#06070c" strokeWidth="2.6" strokeLinecap="round" />
      </g>
    </g>
  )
}

/**
 * The Halloween night scene: moon, stars, clouds, crows, a haunted house, graveyard, dead tree,
 * pumpkins, fog, and a lightning storm when `lightning` ticks. It is a block in the page flow,
 * so it never sits over text. Everything is decorative (`aria-hidden`); motion only with
 * `prefers-reduced-motion: no-preference`.
 */
export default function HalloweenScene() {
  const { on, lightning, reducedMotion } = useHalloween()
  const egg = useEgg()
  const [doneFor, setDoneFor] = useState(0)

  useEffect(() => {
    if (lightning === 0) return
    const t = window.setTimeout(() => setDoneFor(lightning), STRIKE_MS)
    return () => window.clearTimeout(t)
  }, [lightning])

  if (!on) return null
  const striking = lightning > 0 && doneFor !== lightning

  return (
    <div className={`scene${striking ? ' is-striking' : ''}${reducedMotion ? ' is-calm' : ''}`} aria-hidden="true">
      {striking && <div className="page-glow" />}
      <CornerWeb corner="tl" />
      <CornerWeb corner="tr" />
      <svg className="scene-svg" viewBox="0 0 1000 220" preserveAspectRatio="xMidYMax slice">
        <defs>
          <linearGradient id="scene-sky" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#1c1040" />
            <stop offset="0.7" stopColor="#0b0a1c" />
            <stop offset="1" stopColor="#05060d" />
          </linearGradient>
          <radialGradient id="scene-moon-glow">
            <stop offset="0" stopColor="#fff6d5" stopOpacity="0.5" />
            <stop offset="1" stopColor="#fff6d5" stopOpacity="0" />
          </radialGradient>
        </defs>

        {/* sky */}
        <rect width="1000" height="220" fill="url(#scene-sky)" />
        <g fill="#fff" opacity="0.75">
          {STARS.map(([x, y, r], i) => (
            <circle key={i} cx={x} cy={y} r={r} />
          ))}
        </g>

        {/* moon */}
        <circle cx="800" cy="58" r="74" fill="url(#scene-moon-glow)" />
        <circle cx="800" cy="58" r="28" fill="#f1ead0" />
        <circle cx="790" cy="50" r="5" fill="#d9d2b6" />
        <circle cx="810" cy="66" r="4" fill="#d9d2b6" />
        <circle cx="802" cy="44" r="2.5" fill="#d9d2b6" />

        {/* drifting clouds */}
        <g className="cloud cloud-1" fill="#2a1f4d" opacity="0.85">
          <ellipse cx="150" cy="48" rx="70" ry="16" />
          <ellipse cx="120" cy="40" rx="36" ry="18" />
          <ellipse cx="185" cy="40" rx="42" ry="20" />
        </g>
        <g className="cloud cloud-2" fill="#231a42" opacity="0.8">
          <ellipse cx="640" cy="36" rx="80" ry="14" />
          <ellipse cx="610" cy="28" rx="34" ry="16" />
          <ellipse cx="675" cy="26" rx="46" ry="19" />
        </g>
        {/* storm cloud over the house */}
        <g fill="#15102b">
          <ellipse cx="392" cy="30" rx="78" ry="16" />
          <ellipse cx="360" cy="22" rx="36" ry="18" />
          <ellipse cx="420" cy="18" rx="44" ry="21" />
        </g>

        {/* crows and bats */}
        <Crow className="crow-1" y={70} />
        <Crow className="crow-2" y={95} />
        <Crow className="crow-3" y={55} />
        <text className="bat-scene bat-scene-1" x="520" y="80" fontSize="18">
          🦇
        </text>
        <text className="bat-scene bat-scene-2" x="700" y="100" fontSize="16">
          🦇
        </text>

        {/* lightning: rendered only while a strike is playing */}
        {striking && (
          <>
            <rect className="sky-flash" width="1000" height="220" fill="#fff3c4" />
            <g className="bolt" fill="none" stroke="#fff6c8" strokeWidth="3.5" strokeLinejoin="round" strokeLinecap="round">
              <polyline points="402,40 388,66 404,68 384,104 418,72 400,70 422,42" />
              <polyline points="388,66 368,86" strokeWidth="2" />
              <polyline points="404,68 420,92" strokeWidth="2" />
            </g>
          </>
        )}

        {/* far hill */}
        <path d="M0 158 Q180 128 360 152 T720 150 T1000 146 L1000 220 L0 220 Z" fill="#0d1022" />

        {/* dead tree, at the left edge (in view on wide screens) */}
        <g stroke="#05060a" fill="none" strokeLinecap="round" transform="translate(-90 0)">
          <path d="M236 174 L240 128 L226 100" strokeWidth="7" />
          <path d="M240 128 L262 104 L258 92" strokeWidth="4" />
          <path d="M239 142 L218 130 L210 118" strokeWidth="3.5" />
          <path d="M262 104 L276 96" strokeWidth="2.5" />
          <path d="M226 100 L216 86" strokeWidth="2.5" />
        </g>
        <text x="164" y="104" fontSize="10" fill="#06070c">
          🐦‍⬛
        </text>

        {/* Harkness Tower (Problem 10): the Gothic tower behind the plaza, clock lit, lancets glowing */}
        <g id="harkness-tower" transform="translate(262 0)">
          <rect x="-17" y="82" width="34" height="92" fill="#05060a" />
          <rect x="-12" y="54" width="24" height="30" fill="#05060a" />
          <rect x="-9" y="36" width="18" height="20" fill="#05060a" />
          <polygon points="-9,36 0,18 9,36" fill="#05060a" />
          <polygon points="-17,82 -14,66 -11,82" fill="#05060a" />
          <polygon points="11,82 14,66 17,82" fill="#05060a" />
          <polygon points="-12,54 -10,42 -8,54" fill="#05060a" />
          <polygon points="8,54 10,42 12,54" fill="#05060a" />
          <path d="M-17 100 h34 M-17 126 h34 M-12 62 h24" stroke="#1a1e3a" strokeWidth="1" />
          <circle cx="0" cy="92" r="6" fill="#f1ead0" opacity="0.9" />
          <path d="M0 92 v-4 M0 92 l3 2" stroke="#05060a" strokeWidth="1" />
          <path className="window" d="M-4 112 q4 -7 8 0 v12 h-8 z" fill="#ffb347" />
          <path className="window" d="M-4 136 q4 -7 8 0 v12 h-8 z" fill="#ffb347" />
          <path d="M-9 46 q9 -6 18 0" stroke="#1a1e3a" strokeWidth="1" fill="none" />
        </g>

        {/* Evans Hall, the SOM building (Problem 10): the long glass front and its colonnade, lit orange for the night */}
        <g id="evans-hall" transform="translate(318 0)">
          <text x="118" y="110" fontSize="7" fill="#3c4270" textAnchor="middle" fontFamily="serif" letterSpacing="2">
            EVANS HALL
          </text>
          <rect x="-10" y="113" width="256" height="6" fill="#0c0e1a" />
          <rect x="0" y="119" width="236" height="55" fill="#0b1326" />
          {Array.from({ length: 11 }, (_, i) => (
            <rect key={i} className="window" x={8 + i * 21.5} y="125" width="12" height="42" fill="#ffb347" opacity="0.75" />
          ))}
          {Array.from({ length: 13 }, (_, i) => (
            <rect key={`fin-${i}`} x={i * 19.5 - 1} y="113" width="3.5" height="61" fill="#06070c" />
          ))}
          <ellipse cx="118" cy="173" rx="128" ry="6" fill="#ffb347" opacity="0.12" />
        </g>

        {/* near ground */}
        <path d="M0 172 Q250 160 500 172 T1000 168 L1000 220 L0 220 Z" fill="#07080f" />

        {/* fence */}
        <path
          d="M500 160 H900 M520 150 V172 M560 150 V172 M600 152 V172 M640 150 V172 M680 150 V172 M720 152 V172 M760 150 V172 M800 150 V172 M840 152 V172 M880 150 V172"
          stroke="#0c0e1a"
          strokeWidth="3"
          fill="none"
        />

        {/* graveyard */}
        <Tombstone x={540} tilt={-8} />
        <Tombstone x={585} cross />
        <Tombstone x={632} tilt={6} />
        <Tombstone x={690} />
        <Tombstone x={740} cross tilt={-5} />
        <Tombstone x={795} tilt={9} />
        <Tombstone x={845} />
        <Tombstone x={905} cross />
        <Tombstone x={960} tilt={-7} />

        {/* pumpkins */}
        <Pumpkin x={492} y={176} />
        <Pumpkin x={512} y={178} r={6} />
        <Pumpkin x={770} y={178} />
        <Pumpkin x={150} y={176} r={7} />

        {/* ghost and fog */}
        <text className="ghost" x="0" y="130" fontSize="26" opacity="0.8">
          👻
        </text>
        <g className="fog" fill="#cfd6e6" opacity="0.08">
          <ellipse cx="200" cy="196" rx="220" ry="12" />
          <ellipse cx="560" cy="200" rx="260" ry="10" />
          <ellipse cx="880" cy="194" rx="200" ry="12" />
        </g>
      </svg>
      {egg?.spot === 'scene' && <EasterEgg plan={egg} />}
    </div>
  )
}
