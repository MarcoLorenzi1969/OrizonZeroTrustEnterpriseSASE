/**
 * Audit Filters Component
 * For: Marco @ Syneto/Orizon
 */

import { useState, useEffect } from 'react'
import { FiX } from 'react-icons/fi'
import api from '../../services/apiService'

export default function AuditFilters({ filters, onApply, onReset }) {
  const [localFilters, setLocalFilters] = useState(filters)
  const [users, setUsers] = useState([])

  useEffect(() => {
    loadUsers()
  }, [])

  const loadUsers = async () => {
    try {
      const data = await api.getUsers()
      setUsers(data)
    } catch (error) {
      // Silently handle - user might not have permission to list users
      if (error.response?.status !== 403) {
        console.error('Failed to load users:', error)
      }
    }
  }

  const handleApply = () => {
    onApply(localFilters)
  }

  const handleReset = () => {
    const resetFilters = {
      action: '',
      user_id: '',
      start_date: '',
      end_date: '',
      ip_address: '',
      resource_type: '',
      limit: 100
    }
    setLocalFilters(resetFilters)
    onReset()
  }

  const commonActions = [
    { value: 'login', label: 'Login' },
    { value: 'logout', label: 'Logout' },
    { value: 'create', label: 'Create' },
    { value: 'update', label: 'Update' },
    { value: 'delete', label: 'Delete' },
    { value: 'access_granted', label: 'Access Granted' },
    { value: 'access_denied', label: 'Access Denied' },
    { value: 'tunnel_created', label: 'Tunnel Created' },
    { value: 'tunnel_closed', label: 'Tunnel Closed' },
    { value: '2fa_enabled', label: '2FA Enabled' },
    { value: '2fa_disabled', label: '2FA Disabled' },
    { value: 'password_changed', label: 'Password Changed' },
  ]

  return (
    <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold text-white">Advanced Filters</h3>
        <button
          onClick={handleReset}
          className="text-gray-400 hover:text-white text-sm flex items-center gap-2"
        >
          <FiX className="w-4 h-4" />
          Clear All
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Action filter */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Action Type
          </label>
          <select
            className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            value={localFilters.action}
            onChange={(e) => setLocalFilters({ ...localFilters, action: e.target.value })}
          >
            <option value="">All Actions</option>
            {commonActions.map(action => (
              <option key={action.value} value={action.value}>
                {action.label}
              </option>
            ))}
          </select>
        </div>

        {/* User filter */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            User
          </label>
          <select
            className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            value={localFilters.user_id}
            onChange={(e) => setLocalFilters({ ...localFilters, user_id: e.target.value })}
          >
            <option value="">All Users</option>
            {users.map(user => (
              <option key={user.id} value={user.id}>
                {user.full_name} ({user.email})
              </option>
            ))}
          </select>
        </div>

        {/* Resource Type filter */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Resource Type
          </label>
          <select
            className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            value={localFilters.resource_type}
            onChange={(e) => setLocalFilters({ ...localFilters, resource_type: e.target.value })}
          >
            <option value="">All Types</option>
            <option value="auth">Authentication</option>
            <option value="node">Node</option>
            <option value="group">Group</option>
            <option value="user">User</option>
            <option value="tunnel">Tunnel</option>
            <option value="acl">ACL</option>
            <option value="system">System</option>
          </select>
        </div>

        {/* IP Address filter */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            IP Address
          </label>
          <input
            type="text"
            placeholder="e.g., 192.168.1.100"
            className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white font-mono text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            value={localFilters.ip_address}
            onChange={(e) => setLocalFilters({ ...localFilters, ip_address: e.target.value })}
          />
        </div>

        {/* Start date */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Start Date
          </label>
          <input
            type="datetime-local"
            className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            value={localFilters.start_date}
            onChange={(e) => setLocalFilters({ ...localFilters, start_date: e.target.value })}
          />
        </div>

        {/* End date */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            End Date
          </label>
          <input
            type="datetime-local"
            className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            value={localFilters.end_date}
            onChange={(e) => setLocalFilters({ ...localFilters, end_date: e.target.value })}
          />
        </div>

        {/* Results limit */}
        <div className="md:col-span-3">
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Results Limit: {localFilters.limit}
          </label>
          <input
            type="range"
            min="10"
            max="1000"
            step="10"
            className="w-full"
            value={localFilters.limit}
            onChange={(e) => setLocalFilters({ ...localFilters, limit: parseInt(e.target.value) })}
          />
          <div className="flex justify-between text-xs text-gray-500 mt-1">
            <span>10</span>
            <span>1000</span>
          </div>
        </div>
      </div>

      {/* Apply button */}
      <div className="mt-6 flex justify-end gap-3">
        <button
          onClick={handleReset}
          className="px-6 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition"
        >
          Reset
        </button>
        <button
          onClick={handleApply}
          className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition"
        >
          Apply Filters
        </button>
      </div>
    </div>
  )
}
