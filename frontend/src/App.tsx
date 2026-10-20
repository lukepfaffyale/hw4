import { Route, Routes } from 'react-router-dom'
import { AuthProvider } from './auth/AuthProvider'
import { ChatResultsProvider } from './chat/ChatResultsProvider'
import Layout from './components/Layout'
import { HalloweenProvider } from './halloween/HalloweenContext'
import { HuntProvider } from './hunt/HuntProvider'
import About from './pages/About'
import Account from './pages/Account'
import CreateAccount from './pages/CreateAccount'
import Home from './pages/Home'
import Login from './pages/Login'
import NotFound from './pages/NotFound'
import ProductDetail from './pages/ProductDetail'
import Products from './pages/Products'
import Staff from './pages/Staff'

export default function App() {
  return (
    <HalloweenProvider>
      <AuthProvider>
        <HuntProvider>
          <ChatResultsProvider>
            <Routes>
              <Route element={<Layout />}>
                <Route index element={<Home />} />
                <Route path="products" element={<Products />} />
                <Route path="products/:productId" element={<ProductDetail />} />
                <Route path="about" element={<About />} />
                <Route path="login" element={<Login />} />
                <Route path="create-account" element={<CreateAccount />} />
                <Route path="account" element={<Account />} />
                <Route path="staff" element={<Staff />} />
                <Route path="*" element={<NotFound />} />
              </Route>
            </Routes>
          </ChatResultsProvider>
        </HuntProvider>
      </AuthProvider>
    </HalloweenProvider>
  )
}
