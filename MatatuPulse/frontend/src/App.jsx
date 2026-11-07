import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import Login from './pages/Login'
import LoginOtp from './pages/LoginOtp'
import RouteDetail from './pages/RouteDetail'
import RoutesIndex from './pages/RoutesIndex'
import RoutesLayout from './pages/RoutesLayout'
import Signal from './pages/Signal'
import { useAuth } from './lib/useAuth'

function RequireAuth({ children }) {
  const auth = useAuth()
  const location = useLocation()
  if (!auth?.access) return <Navigate to="/login" replace state={{ from: location.pathname }} />
  return children
}

function GuestOnly({ children }) {
  const auth = useAuth()
  if (auth?.access) return <Navigate to="/routes" replace />
  return children
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<GuestOnly><Login /></GuestOnly>} />
      <Route path="/login/otp" element={<GuestOnly><LoginOtp /></GuestOnly>} />
      <Route path="/signal" element={<Signal />} />
      <Route
        path="/routes"
        element={
          <RequireAuth>
            <RoutesLayout />
          </RequireAuth>
        }
      >
        <Route index element={<RoutesIndex />} />
        <Route path=":id" element={<RouteDetail />} />
      </Route>
      <Route path="*" element={<Navigate to="/routes" replace />} />
    </Routes>
  )
}
