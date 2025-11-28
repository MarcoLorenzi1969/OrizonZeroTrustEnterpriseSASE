/**
 * Dashboard Layout with Sidebar Navigation
 * For: Marco @ Syneto/Orizon
 */

import { useState } from 'react'
import { useSelector, useDispatch } from 'react-redux'
import { useNavigate, useLocation, Outlet } from 'react-router-dom'
import { logout } from '../../store/slices/authSlice'
import {
  FiHome,
  FiServer,
  FiLogOut,
  FiMenu,
  FiX,
  FiActivity,
  FiUsers,
  FiLink,
  FiZap
} from 'react-icons/fi'

export default function DashboardLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const { user } = useSelector(state => state.auth)
  const dispatch = useDispatch()
  const navigate = useNavigate()
  const location = useLocation()

  const handleLogout = () => {
    dispatch(logout())
    navigate('/login')
  }

  const navigationItems = [
    { path: '/dashboard', icon: FiHome, label: 'Dashboard' },
    { path: '/provision', icon: FiLink, label: 'Edge Provisioning', adminOnly: true },
    { path: '/tunnels-dashboard', icon: FiActivity, label: 'Tunnels Dashboard' },
    { path: '/nodes', icon: FiServer, label: 'Nodes' },
    { path: '/groups', icon: FiUsers, label: 'Groups', adminOnly: true },
    { path: '/rdp-direct', icon: FiZap, label: 'RDP Direct', adminOnly: true },
  ]

  // Filter navigation items based on user role
  const visibleNavigationItems = navigationItems.filter(item => {
    if (item.adminOnly) {
      const role = user?.role?.toLowerCase()
      return role === 'admin' || role === 'superuser'
    }
    return true
  })

  return (
    <div className="flex h-screen bg-gray-900">
      {/* Sidebar */}
      <aside
        className={`bg-gray-800 border-r border-gray-700 transition-all duration-300 ${
          sidebarOpen ? 'w-64' : 'w-20'
        } flex flex-col`}
      >
        {/* Logo / Brand */}
        <div className="p-6 border-b border-gray-700">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center text-white font-bold text-xl">
              O
            </div>
            {sidebarOpen && (
              <div>
                <h1 className="text-white font-bold text-lg">Orizon</h1>
                <p className="text-gray-400 text-xs">Zero Trust Connect</p>
              </div>
            )}
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-2 overflow-y-auto">
          {visibleNavigationItems.map((item) => {
            const Icon = item.icon
            const isActive = location.pathname === item.path

            return (
              <button
                key={item.path}
                onClick={() => navigate(item.path)}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition ${
                  isActive
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-400 hover:bg-gray-700 hover:text-white'
                }`}
                title={!sidebarOpen ? item.label : ''}
              >
                <Icon className="w-5 h-5 flex-shrink-0" />
                {sidebarOpen && <span className="font-medium">{item.label}</span>}
              </button>
            )
          })}
        </nav>

        {/* User info */}
        <div className="p-4 border-t border-gray-700">
          {sidebarOpen ? (
            <div className="mb-3">
              <div className="flex items-center gap-3 px-3 py-2 bg-gray-900 rounded-lg">
                <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center text-white font-semibold">
                  {user?.full_name?.charAt(0) || user?.email?.charAt(0) || 'U'}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-white text-sm font-medium truncate">
                    {user?.full_name || 'User'}
                  </p>
                  <p className="text-gray-400 text-xs truncate capitalize">
                    {user?.role || 'user'}
                  </p>
                </div>
              </div>
            </div>
          ) : (
            <div className="mb-3 flex justify-center">
              <div className="w-10 h-10 bg-blue-600 rounded-full flex items-center justify-center text-white font-semibold">
                {user?.full_name?.charAt(0) || user?.email?.charAt(0) || 'U'}
              </div>
            </div>
          )}

          {/* Logout button */}
          <button
            onClick={handleLogout}
            className="w-full flex items-center justify-center gap-3 px-4 py-3 text-red-400 hover:bg-red-900 hover:bg-opacity-20 rounded-lg transition"
            title={!sidebarOpen ? 'Logout' : ''}
          >
            <FiLogOut className="w-5 h-5" />
            {sidebarOpen && <span className="font-medium">Logout</span>}
          </button>
        </div>
      </aside>

      {/* Main content area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top bar */}
        <header className="bg-gray-800 border-b border-gray-700 px-6 py-4">
          <div className="flex items-center justify-between">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="text-gray-400 hover:text-white transition"
            >
              {sidebarOpen ? <FiX className="w-6 h-6" /> : <FiMenu className="w-6 h-6" />}
            </button>

            <div className="flex items-center gap-4">
              {/* 2FA Badge */}
              {user?.totp_enabled && (
                <div className="flex items-center gap-2 px-3 py-1 bg-green-900 bg-opacity-30 border border-green-500 rounded-full">
                  <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                  <span className="text-green-400 text-sm font-medium">2FA Enabled</span>
                </div>
              )}

              {/* Connection status */}
              <div className="flex items-center gap-2 px-3 py-1 bg-blue-900 bg-opacity-30 border border-blue-500 rounded-full">
                <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
                <span className="text-blue-400 text-sm font-medium">Connected</span>
              </div>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto bg-gray-900">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
