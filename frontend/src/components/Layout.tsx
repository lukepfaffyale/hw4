import { useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import ChatResults from '../chat/ChatResults'
import { EggContext } from '../eggs/context'
import EasterEgg from '../eggs/EasterEgg'
import { planEgg, type EggPlan } from '../eggs/eggs'
import HalloweenDecor from '../halloween/HalloweenDecor'
import HalloweenScene from '../halloween/HalloweenScene'
import { useHalloween } from '../halloween/useHalloween'
import { useHunt } from '../hunt/useHunt'
import ChatPanel from './ChatPanel'
import NavBar from './NavBar'

export default function Layout() {
  const { pathname, search } = useLocation()
  const { on: halloween } = useHalloween()
  const { program, found, ready } = useHunt()
  // The Account page places the scene under its heading so the sign-in lightning is in view.
  const sceneAtBottom = pathname !== '/account'

  // One roll per page visit: does a hidden friend appear, which one, and where. The plan is keyed
  // on the visit (not on the found set) so a friend stays put after being found until you move on.
  const season = program?.current_season
  const planKey = `${pathname}?${search}|${halloween}|${season?.key ?? ''}|${ready}`
  const [planned, setPlanned] = useState<{ key: string; plan: EggPlan | null }>({ key: '', plan: null })
  if (planned.key !== planKey) {
    const plan = season && ready ? planEgg(pathname, search, { halloween, season: season.key, friends: season.friends, found }) : null
    setPlanned({ key: planKey, plan })
  }
  const egg = planned.key === planKey ? planned.plan : null

  return (
    <EggContext.Provider value={egg}>
      <a className="skip-link" href="#main">
        Skip to main content
      </a>
      <NavBar />
      <main id="main" tabIndex={-1}>
        {/* Keyed by route so each page plays its short entrance (Problem 10); off under reduced motion. */}
        <div className="container page-enter" key={pathname}>
          <Outlet />
          {/* The Products page folds the assistant's matches into its own grid instead. */}
          {pathname !== '/products' && <ChatResults />}
        </div>
      </main>
      {sceneAtBottom && <HalloweenScene />}
      <footer className="site-footer">
        <div className="container">
          <span>Campus Customs, New Haven. Officially licensed Yale merchandise.</span>
          <span className="footer-motto">Lux et Veritas, Boola Boola.</span>
          <span>Class project for MGT 409. Not affiliated with the store.</span>
          {egg?.spot === 'footer' && <EasterEgg plan={egg} />}
          <span className="footer-note">
            For academic and research purposes only. Use test passwords here, never a real one.
          </span>
        </div>
      </footer>
      <HalloweenDecor />
      {egg?.spot === 'gutter' && <EasterEgg plan={egg} />}
      <ChatPanel />
    </EggContext.Provider>
  )
}
