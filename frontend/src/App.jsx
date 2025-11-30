/**
 * Orizon Zero Trust Connect - Main App Component
 * For: Marco @ Syneto/Orizon
 */

import { Routes, Route, Navigate, Outlet } from 'react-router-dom'
import { useSelector, useDispatch } from 'react-redux'
import { useEffect, useState } from 'react'
import { ToastContainer } from 'react-toastify'
import 'react-toastify/dist/ReactToastify.css'
import { getCurrentUser } from './store/slices/authSlice'

// Pages
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import EdgeProvisioningPage from './pages/EdgeProvisioningPage'
import NodesPage from './pages/NodesPage'
import GroupsPage from './pages/GroupsPage'
import UsersPage from './pages/UsersPage'
import TunnelsDashboard from './pages/TunnelsDashboard'

// Layout
import DashboardLayout from './components/layout/DashboardLayout'
import DebugPanel from './components/DebugPanel'
import DebugOverlay from './components/DebugOverlay'
import debugService from './services/debugService'
import { debugReact } from './utils/debugLogger'

function App() {
  const dispatch = useDispatch()
  const { isAuthenticated, user } = useSelector(state => state.auth)
  const [isLoading, setIsLoading] = useState(true)

  // On app mount, check if we have a token and load user data
  useEffect(() => {
    const initializeAuth = async () => {
      const token = localStorage.getItem('access_token')
      debugService.info('App Init', {
        hasToken: !!token,
        isAuthenticated,
        hasUser: !!user,
        pathname: window.location.pathname
      })

      // Only fetch user data if we have a token but no user data yet
      if (token && !user && isAuthenticated) {
        debugService.info('App Init', { message: 'Fetching current user...' })
        try {
          const userData = await dispatch(getCurrentUser()).unwrap()
          debugService.success('App Init', {
            message: 'User data loaded',
            user: { email: userData.email, role: userData.role }
          })
        } catch (error) {
          debugService.error('App Init', {
            message: 'Failed to load user data',
            error: error.message,
            stack: error.stack
          })
          // Token might be invalid, clear it
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
        }
      }

      setIsLoading(false)
    }

    initializeAuth()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []) // Run only once on mount

  // Show loading spinner while initializing
  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-400">Loading...</p>
        </div>
      </div>
    )
  }

  // Log App render
  debugReact.render('App', 'Main render', { isAuthenticated, user: user?.email })

  return (
    <>
      <DebugPanel />
      <DebugOverlay />
      <Routes>
        {/* Public Routes */}
        <Route
          path="/login"
          element={!isAuthenticated ? <LoginPage /> : <Navigate to="/dashboard" />}
        />

        {/* Protected Routes */}
        <Route element={<PrivateRoute />}>
          <Route element={<DashboardLayout />}>
            {/* Routes accessible to all authenticated users */}
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/tunnels-dashboard" element={<TunnelsDashboard />} />
            <Route path="/nodes" element={<NodesPage />} />
            <Route path="/" element={<Navigate to="/dashboard" replace />} />

            {/* Admin-only routes */}
            <Route element={<AdminRoute />}>
              <Route path="/provision" element={<EdgeProvisioningPage />} />
              <Route path="/groups" element={<GroupsPage />} />
              <Route path="/users" element={<UsersPage />} />
            </Route>
          </Route>
        </Route>

        {/* Catch-all redirect */}
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>

      {/* Toast notifications */}
      <ToastContainer
        position="top-right"
        autoClose={3000}
        hideProgressBar={false}
        newestOnTop
        closeOnClick
        rtl={false}
        pauseOnFocusLoss
        draggable
        pauseOnHover
        theme="dark"
      />
    </>
  )
}

// Private Route Component
function PrivateRoute() {
  const { isAuthenticated } = useSelector(state => state.auth)

  console.log('[PrivateRoute] isAuthenticated:', isAuthenticated)

  if (!isAuthenticated) {
    console.log('[PrivateRoute] Not authenticated, redirecting to /login')
    return <Navigate to="/login" replace />
  }

  console.log('[PrivateRoute] Authenticated, rendering Outlet')
  return <Outlet />
}

// Admin Route Component - requires SUPERUSER or ADMIN role
function AdminRoute() {
  const { isAuthenticated, user } = useSelector(state => state.auth)

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  const role = user?.role?.toLowerCase()
  const isAdmin = role === 'superuser' || role === 'admin' || role === 'super_admin'

  if (!isAdmin) {
    console.log('[AdminRoute] User is not admin, redirecting to /dashboard')
    return <Navigate to="/dashboard" replace />
  }

  return <Outlet />
}

export default App
