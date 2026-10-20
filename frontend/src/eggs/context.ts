import { createContext } from 'react'
import type { EggPlan } from './eggs'

export const EggContext = createContext<EggPlan | null>(null)
