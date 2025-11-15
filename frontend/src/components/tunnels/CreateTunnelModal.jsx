/**
 * Create Tunnel Modal Component
 */

import { useState, useEffect } from 'react'
import { FiX } from 'react-icons/fi'
import api from '../../services/apiService'

export default function CreateTunnelModal({ onClose, onCreate }) {
  const [formData, setFormData] = useState({
    node_id: '',
    tunnel_type: 'ssh',
    agent_public_key: '',
    agent_ip: '',
    cert_data: ''
  })
  const [nodes, setNodes] = useState([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    loadNodes()
  }, [])

  const loadNodes = async () => {
    try {
      const data = await api.getNodes()
      setNodes(data.filter(n => n.status === 'online'))
    } catch (error) {
      console.error('Failed to load nodes:', error)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      await onCreate(formData)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-800 rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex justify-between items-center p-6 border-b border-gray-700">
          <h2 className="text-2xl font-bold text-white">Create New Tunnel</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white transition"
          >
            <FiX className="w-6 h-6" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {/* Node Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Target Node *
            </label>
            <select
              required
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={formData.node_id}
              onChange={(e) => setFormData({ ...formData, node_id: e.target.value })}
            >
              <option value="">Select a node</option>
              {nodes.map(node => (
                <option key={node.id} value={node.id}>
                  {node.name} ({node.ip_address})
                </option>
              ))}
            </select>
          </div>

          {/* Tunnel Type */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Tunnel Type *
            </label>
            <div className="grid grid-cols-2 gap-4">
              <button
                type="button"
                onClick={() => setFormData({ ...formData, tunnel_type: 'ssh' })}
                className={`p-4 rounded-lg border-2 transition ${
                  formData.tunnel_type === 'ssh'
                    ? 'border-blue-500 bg-blue-500 bg-opacity-20'
                    : 'border-gray-600 hover:border-gray-500'
                }`}
              >
                <div className="text-3xl mb-2">🔐</div>
                <div className="text-white font-semibold">SSH Tunnel</div>
                <div className="text-sm text-gray-400 mt-1">
                  Secure Shell reverse tunnel
                </div>
              </button>
              <button
                type="button"
                onClick={() => setFormData({ ...formData, tunnel_type: 'https' })}
                className={`p-4 rounded-lg border-2 transition ${
                  formData.tunnel_type === 'https'
                    ? 'border-blue-500 bg-blue-500 bg-opacity-20'
                    : 'border-gray-600 hover:border-gray-500'
                }`}
              >
                <div className="text-3xl mb-2">🔒</div>
                <div className="text-white font-semibold">HTTPS Tunnel</div>
                <div className="text-sm text-gray-400 mt-1">
                  TLS-encrypted tunnel
                </div>
              </button>
            </div>
          </div>

          {/* Agent IP */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Agent IP Address *
            </label>
            <input
              type="text"
              required
              placeholder="192.168.1.100"
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={formData.agent_ip}
              onChange={(e) => setFormData({ ...formData, agent_ip: e.target.value })}
            />
          </div>

          {/* SSH Public Key (for SSH tunnels) */}
          {formData.tunnel_type === 'ssh' && (
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Agent SSH Public Key *
              </label>
              <textarea
                required
                rows="4"
                placeholder="ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC..."
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white font-mono text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                value={formData.agent_public_key}
                onChange={(e) => setFormData({ ...formData, agent_public_key: e.target.value })}
              />
              <p className="text-xs text-gray-400 mt-1">
                Paste the agent's SSH public key (id_rsa.pub)
              </p>
            </div>
          )}

          {/* SSL Certificate (for HTTPS tunnels) */}
          {formData.tunnel_type === 'https' && (
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                SSL Certificate Data *
              </label>
              <textarea
                required
                rows="4"
                placeholder="-----BEGIN CERTIFICATE-----&#10;MIIDXTCCAkWgAwIBAgIJAK..."
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white font-mono text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                value={formData.cert_data}
                onChange={(e) => setFormData({ ...formData, cert_data: e.target.value })}
              />
              <p className="text-xs text-gray-400 mt-1">
                Paste the SSL certificate (PEM format)
              </p>
            </div>
          )}

          {/* Buttons */}
          <div className="flex justify-end gap-3 pt-4">
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
              {loading ? 'Creating...' : 'Create Tunnel'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
