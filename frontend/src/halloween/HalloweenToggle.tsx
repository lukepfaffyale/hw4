import { useHalloween } from './useHalloween'

export default function HalloweenToggle() {
  const { on, setOn } = useHalloween()
  return (
    <button
      type="button"
      className="halloween-toggle"
      role="switch"
      aria-checked={on}
      aria-label="Halloween toggle"
      onClick={() => setOn(!on)}
    >
      <span aria-hidden="true">{on ? '🎃' : '🔵'}</span>
      <span>Halloween {on ? 'on' : 'off'}</span>
    </button>
  )
}
