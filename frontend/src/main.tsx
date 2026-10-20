import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
// Self-hosted fonts (Problem 10): no request leaves the site for typography.
import '@fontsource-variable/fraunces'
import '@fontsource/alfa-slab-one'
import './index.css'
import './shop.css'
import './auth.css'
import './chat.css'
import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>,
)
