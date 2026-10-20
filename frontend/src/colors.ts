// Colour names in the catalogue -> a swatch colour for cards (Problem 10). Names stay the truth
// (they are read out and shown on hover); the swatch is a visual hint only.
const SWATCH: Record<string, string> = {
  'navy blue': '#13305f',
  navy: '#13305f',
  'royal blue': '#2b5fd9',
  blue: '#2a63b8',
  'light blue': '#8fb8ea',
  white: '#f4f4f2',
  ivory: '#f3ecd8',
  cream: '#efe4c8',
  'heather gray': '#a3a8ae',
  gray: '#8d9298',
  'light gray': '#c9ccd1',
  'dark heather gray': '#6a6f77',
  'charcoal gray': '#4a4f57',
  'dark heather charcoal': '#3c4047',
  'heather charcoal gray': '#585d65',
  black: '#141414',
  red: '#b22234',
  'dusty coral': '#d98b7a',
  yellow: '#f2c230',
  gold: '#c9a227',
  green: '#2e7d4f',
  multicolor: 'linear-gradient(135deg, #b22234 0 33%, #f2c230 33% 66%, #2a63b8 66%)',
}

export function swatchFor(name: string): string {
  const k = name.toLowerCase().trim()
  if (SWATCH[k]) return SWATCH[k]
  if (k.includes('navy')) return SWATCH.navy
  if (k.includes('charcoal')) return SWATCH['charcoal gray']
  if (k.includes('gray') || k.includes('grey')) return SWATCH.gray
  if (k.includes('blue')) return SWATCH.blue
  if (k.includes('white') || k.includes('cream') || k.includes('ivory')) return SWATCH.cream
  if (k.includes('red') || k.includes('crimson') || k.includes('maroon')) return SWATCH.red
  if (k.includes('gold') || k.includes('yellow')) return SWATCH.gold
  if (k.includes('green')) return SWATCH.green
  if (k.includes('black')) return SWATCH.black
  return '#7a7f88'
}
