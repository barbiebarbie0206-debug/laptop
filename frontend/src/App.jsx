import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import { ToastProvider } from './components/Toast'
import ProtectedRoute from './components/ProtectedRoute'
import Layout from './components/Layout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Laptops from './pages/Laptops'
import Interns from './pages/Interns'
import AllocateLaptop from './pages/AllocateLaptop'
import ActiveAllocations from './pages/ActiveAllocations'
import AllocationHistory from './pages/AllocationHistory'
import Reports from './pages/Reports'
import Handover from './pages/Handover'
import Inover from './pages/Inover'
import Settings from './pages/Settings'

function AppRoutes() {
  const { isAuthenticated } = useAuth()
  return (
    <Routes>
      <Route path="/login" element={isAuthenticated ? <Navigate to="/" replace /> : <Login />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="allocate" element={<AllocateLaptop />} />
        <Route path="allocations" element={<ActiveAllocations />} />
        <Route path="allocations/history" element={<AllocationHistory />} />
        <Route path="handover" element={<Handover />} />
        <Route path="inover" element={<Inover />} />
        <Route path="laptops" element={<Laptops />} />
        <Route path="interns" element={<Interns />} />
        <Route path="reports" element={<Reports />} />
        <Route path="settings" element={<Settings />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <ToastProvider>
          <AppRoutes />
        </ToastProvider>
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App
