/**
 * Tunnels Management Page
 * For: Marco @ Syneto/Orizon
 */

import { useState, useEffect } from 'react'
import { toast } from 'react-toastify'
import api from '../services/apiService'
import websocket from '../services/websocket'
import CreateTunnelModal from '../components/tunnels/CreateTunnelModal'
import TunnelCard from '../components/tunnels/TunnelCard'
import { FiPlus, FiRefreshCw } from 'react-icons/fi'

export default function TunnelsPage() {
  const [tunnels, setTunnels] = useState([])
  const [loading, setLoading] = useState(true)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [filter, setFilter] = useState('all') // all, ssh, https, active, inactive

  useEffect(() => {
    loadTunnels()

    // WebSocket real-time updates
    const token = localStorage.getItem('access_token')
    if (token) {
      websocket.connect(token)

      websocket.on('tunnel_created', (data) => {
        setTunnels(prev => [...prev, data.tunnel])
        toast.success(`Tunnel ${data.tunnel.tunnel_id} created`)
      })

      websocket.on('tunnel_closed', (data) => {
        setTunnels(prev => prev.filter(t => t.tunnel_id !== data.tunnel_id))
        toast.info(`Tunnel ${data.tunnel_id} closed`)
      })

      websocket.on('tunnel_status_changed', (data) => {
        setTunnels(prev => prev.map(t =>
          t.tunnel_id === data.tunnel_id
            ? { ...t, status: data.status }
            : t
        ))
      })
    }

    return () => websocket.disconnect()
  }, [])

  const loadTunnels = async () => {
    try {
      setLoading(true)
      const data = await api.getTunnels()
      setTunnels(data)
    } catch (error) {
      toast.error('Failed to load tunnels')
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  const handleCloseTunnel = async (tunnelId) => {
    if (!confirm('Are you sure you want to close this tunnel?')) return

    try {
      await api.closeTunnel(tunnelId)
      setTunnels(prev => prev.filter(t => t.tunnel_id !== tunnelId))
      toast.success('Tunnel closed successfully')
    } catch (error) {
      toast.error('Failed to close tunnel')
      console.error(error)
    }
  }

  const handleCreateTunnel = async (tunnelData) => {
    try {
      const newTunnel = await api.createTunnel(tunnelData)
      setTunnels(prev => [...prev, newTunnel])
      setShowCreateModal(false)
      toast.success('Tunnel created successfully')
    } catch (error) {
      toast.error('Failed to create tunnel')
      console.error(error)
    }
  }

  const filteredTunnels = tunnels.filter(tunnel => {
    if (filter === 'all') return true
    if (filter === 'ssh') return tunnel.tunnel_type === 'ssh'
    if (filter === 'https') return tunnel.tunnel_type === 'https'
    if (filter === 'active') return tunnel.status === 'connected'
    if (filter === 'inactive') return tunnel.status !== 'connected'
    return true
  })

  const stats = {
    total: tunnels.length,
    active: tunnels.filter(t => t.status === 'connected').length,
    ssh: tunnels.filter(t => t.tunnel_type === 'ssh').length,
    https: tunnels.filter(t => t.tunnel_type === 'https').length,
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-white">Tunnels</h1>
          <p className="text-gray-400 mt-1">
            Manage SSH and HTTPS reverse tunnels
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={loadTunnels}
            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg flex items-center gap-2 transition"
          >
            <FiRefreshCw className="w-4 h-4" />
            Refresh
          </button>
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg flex items-center gap-2 transition"
          >
            <FiPlus className="w-4 h-4" />
            Create Tunnel
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatCard
          label="Total Tunnels"
          value={stats.total}
          color="blue"
        />
        <StatCard
          label="Active"
          value={stats.active}
          color="green"
        />
        <StatCard
          label="SSH Tunnels"
          value={stats.ssh}
          color="purple"
        />
        <StatCard
          label="HTTPS Tunnels"
          value={stats.https}
          color="orange"
        />
      </div>

      {/* Filter Tabs */}
      <div className="flex gap-2 border-b border-gray-700">
        {['all', 'active', 'inactive', 'ssh', 'https'].map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-4 py-2 capitalize transition ${
              filter === f
                ? 'text-blue-500 border-b-2 border-blue-500'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            {f}
          </button>
        ))}
      </div>

      {/* Tunnels Grid */}
      {filteredTunnels.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-gray-400 text-lg">No tunnels found</p>
          <button
            onClick={() => setShowCreateModal(true)}
            className="mt-4 px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg"
          >
            Create your first tunnel
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredTunnels.map(tunnel => (
            <TunnelCard
              key={tunnel.tunnel_id}
              tunnel={tunnel}
              onClose={() => handleCloseTunnel(tunnel.tunnel_id)}
            />
          ))}
        </div>
      )}

      {/* Create Tunnel Modal */}
      {showCreateModal && (
        <CreateTunnelModal
          onClose={() => setShowCreateModal(false)}
          onCreate={handleCreateTunnel}
        />
      )}
    </div>
  )
}

function StatCard({ label, value, color }) {
  const colorClasses = {
    blue: 'bg-blue-500 bg-opacity-20 border-blue-500',
    green: 'bg-green-500 bg-opacity-20 border-green-500',
    purple: 'bg-purple-500 bg-opacity-20 border-purple-500',
    orange: 'bg-orange-500 bg-opacity-20 border-orange-500',
  }

  return (
    <div className={`p-4 rounded-lg border ${colorClasses[color]}`}>
      <p className="text-gray-400 text-sm">{label}</p>
      <p className="text-3xl font-bold text-white mt-1">{value}</p>
    </div>
  )
}
