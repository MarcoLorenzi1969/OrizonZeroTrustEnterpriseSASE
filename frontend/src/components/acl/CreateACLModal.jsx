/**
 * Create ACL Rule Modal Component
 * For: Marco @ Syneto/Orizon
 */

import { useState, useEffect } from 'react'
import { FiX, FiInfo } from 'react-icons/fi'
import api from '../../services/apiService'

export default function CreateACLModal({ onClose, onCreate }) {
  const [formData, setFormData] = useState({
    action: 'allow',
    priority: 100,
    description: '',
    source_ip: '',
    destination_ip: '',
    source_port: '',
    destination_port: '',
    protocol: '',
    user_id: null,
    is_active: true
  })
  const [loading, setLoading] = useState(false)
  const [users, setUsers] = useState([])

  useEffect(() => {
    loadUsers()
  }, [])

  const loadUsers = async () => {
    try {
      const data = await api.getUsers()
      setUsers(data)
    } catch (error) {
      console.error('Failed to load users:', error)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)

    // Clean up empty fields (convert to null)
    const cleanedData = {
      ...formData,
      source_ip: formData.source_ip || null,
      destination_ip: formData.destination_ip || null,
      source_port: formData.source_port ? parseInt(formData.source_port) : null,
      destination_port: formData.destination_port ? parseInt(formData.destination_port) : null,
      protocol: formData.protocol || null,
      user_id: formData.user_id || null,
      priority: parseInt(formData.priority)
    }

    try {
      await onCreate(cleanedData)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-800 rounded-lg max-w-3xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex justify-between items-center p-6 border-b border-gray-700">
          <h2 className="text-2xl font-bold text-white">Create ACL Rule</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white transition"
          >
            <FiX className="w-6 h-6" />
          </button>
        </div>

        {/* Zero Trust Notice */}
        <div className="mx-6 mt-6 bg-blue-900 bg-opacity-30 border border-blue-500 rounded-lg p-4 flex gap-3">
          <FiInfo className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-blue-200">
            <strong>Zero Trust Policy:</strong> Default action is DENY ALL.
            Create explicit ALLOW rules for authorized traffic only.
          </div>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          {/* Action and Priority row */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Action *
              </label>
              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => setFormData({ ...formData, action: 'allow' })}
                  className={`p-3 rounded-lg border-2 transition ${
                    formData.action === 'allow'
                      ? 'border-green-500 bg-green-500 bg-opacity-20 text-green-400'
                      : 'border-gray-600 text-gray-400 hover:border-gray-500'
                  }`}
                >
                  <div className="text-xl mb-1">✓</div>
                  <div className="font-semibold">ALLOW</div>
                </button>
                <button
                  type="button"
                  onClick={() => setFormData({ ...formData, action: 'deny' })}
                  className={`p-3 rounded-lg border-2 transition ${
                    formData.action === 'deny'
                      ? 'border-red-500 bg-red-500 bg-opacity-20 text-red-400'
                      : 'border-gray-600 text-gray-400 hover:border-gray-500'
                  }`}
                >
                  <div className="text-xl mb-1">✗</div>
                  <div className="font-semibold">DENY</div>
                </button>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Priority * (lower = higher priority)
              </label>
              <input
                type="number"
                required
                min="1"
                max="1000"
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                value={formData.priority}
                onChange={(e) => setFormData({ ...formData, priority: e.target.value })}
              />
              <p className="text-xs text-gray-400 mt-1">
                Rules are evaluated in priority order (1-1000)
              </p>
            </div>
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Description
            </label>
            <input
              type="text"
              placeholder="e.g., Allow SSH from admin network"
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            />
          </div>

          {/* Source and Destination IP */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Source IP / CIDR
              </label>
              <input
                type="text"
                placeholder="192.168.1.0/24 or any"
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white font-mono text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                value={formData.source_ip}
                onChange={(e) => setFormData({ ...formData, source_ip: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Destination IP / CIDR
              </label>
              <input
                type="text"
                placeholder="10.0.0.0/8 or any"
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white font-mono text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                value={formData.destination_ip}
                onChange={(e) => setFormData({ ...formData, destination_ip: e.target.value })}
              />
            </div>
          </div>

          {/* Source and Destination Port */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Source Port
              </label>
              <input
                type="number"
                placeholder="any"
                min="1"
                max="65535"
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white font-mono text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                value={formData.source_port}
                onChange={(e) => setFormData({ ...formData, source_port: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Destination Port
              </label>
              <input
                type="number"
                placeholder="any"
                min="1"
                max="65535"
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white font-mono text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                value={formData.destination_port}
                onChange={(e) => setFormData({ ...formData, destination_port: e.target.value })}
              />
            </div>
          </div>

          {/* Protocol and User */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Protocol
              </label>
              <select
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                value={formData.protocol}
                onChange={(e) => setFormData({ ...formData, protocol: e.target.value })}
              >
                <option value="">Any</option>
                <option value="tcp">TCP</option>
                <option value="udp">UDP</option>
                <option value="icmp">ICMP</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Restrict to User (optional)
              </label>
              <select
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                value={formData.user_id || ''}
                onChange={(e) => setFormData({ ...formData, user_id: e.target.value || null })}
              >
                <option value="">Any User</option>
                {users.map(user => (
                  <option key={user.id} value={user.id}>
                    {user.full_name} ({user.email})
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Active toggle */}
          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="is_active"
              className="w-4 h-4 text-blue-600 bg-gray-700 border-gray-600 rounded focus:ring-blue-500"
              checked={formData.is_active}
              onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
            />
            <label htmlFor="is_active" className="text-sm text-gray-300">
              Activate rule immediately
            </label>
          </div>

          {/* Buttons */}
          <div className="flex justify-end gap-3 pt-4 border-t border-gray-700">
            <button
              type="button"
              onClick={onClose}
              className="px-6 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition disabled:opacity-50"
            >
              {loading ? 'Creating...' : 'Create Rule'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
