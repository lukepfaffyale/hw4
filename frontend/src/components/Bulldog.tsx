// The shop bulldog: an original drawing used as the brand mark and the chat counter's face.
// Decorative everywhere it appears; the surrounding control carries the accessible name.
export default function Bulldog({ size = 40 }: { size?: number }) {
  return (
    <svg viewBox="0 0 64 64" width={size} height={size} aria-hidden="true" focusable="false">
      <path d="M13 30 q-7 -15 6 -15 q5 6 3 15 z" fill="#b89b7b" />
      <path d="M51 30 q7 -15 -6 -15 q-5 6 -3 15 z" fill="#b89b7b" />
      <ellipse cx="32" cy="35" rx="22" ry="19" fill="#e9dccb" />
      <path d="M17 26 q7 -5 12 -1 M35 25 q5 -4 12 1" stroke="#9a7a55" strokeWidth="2" fill="none" strokeLinecap="round" />
      <ellipse cx="32" cy="43" rx="14" ry="10" fill="#f7f0e6" />
      <ellipse cx="32" cy="38.5" rx="4.2" ry="3" fill="#1d1d1d" />
      <path d="M32 41 v4 M26 46 q6 4 12 0" stroke="#1d1d1d" strokeWidth="1.5" fill="none" strokeLinecap="round" />
      <rect x="27" y="46.5" width="3" height="4" rx="1" fill="#fff" />
      <rect x="34" y="46.5" width="3" height="4" rx="1" fill="#fff" />
      <circle cx="24" cy="31" r="3.2" fill="#1d1d1d" />
      <circle cx="40" cy="31" r="3.2" fill="#1d1d1d" />
      <circle cx="25.1" cy="30" r="1" fill="#fff" />
      <circle cx="41.1" cy="30" r="1" fill="#fff" />
      <rect x="12" y="52" width="40" height="7" rx="3.5" fill="#00356b" />
      <circle cx="32" cy="58" r="4.5" fill="#f2c230" />
      <text x="32" y="60.6" fontSize="6" textAnchor="middle" fontWeight="800" fill="#00356b" fontFamily="Georgia, serif">
        Y
      </text>
    </svg>
  )
}
