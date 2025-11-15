/**
 * Tunnel Card Component
 */

import { FiX, FiActivity, FiClock } from 'react-icons/fi'
import { formatDistanceToNow } from 'date-fns'

export default function TunnelCard({ tunnel, onClose }) {
  const getStatusColor = (status) => {
    switch (status) {
      case 'connected': return 'bg-green-500'
      case 'connecting': return 'bg-yellow-500'
      case 'disconnected': return 'bg-gray-500'
      case 'error': return 'bg-red-500'
      default: return 'bg-gray-500'
    }
  }

  const getTypeIcon = (type) => {
    return type === 'ssh' ? '🔐' : '🔒'
  }

  return (
    <div className="bg-gray-800 rounded-lg p-6 border border-gray-700 hover:border-gray-600 transition">
      {/* Header */}
      <div className="flex justify-between items-start mb-4">
        <div className="flex items-center gap-3">
          <span className="text-3xl">{getTypeIcon(tunnel.tunnel_type)}</span>
          <div>
            <h3 className="text-lg font-semibold text-white">
              {tunnel.tunnel_type.toUpperCase()} Tunnel
            </h3>
            <p className="text-sm text-gray-400">
              Node: {tunnel.node_id}
            </p>
          </div>
        </div>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-red-500 transition"
          title="Close tunnel"
        >
          <FiX className="w-5 h-5" />
        </button>
      </div>

      {/* Status Badge */}
      <div className="flex items-center gap-2 mb-4">
        <span className={`w-2 h-2 rounded-full ${getStatusColor(tunnel.status)}`}></span>
        <span className="text-sm text-gray-300 capitalize">{tunnel.status}</span>
      </div>

      {/* Details */}
      <div className="space-y-2 text-sm">
        <div className="flex justify-between">
          <span className="text-gray-400">Local Port:</span>
          <span className="text-white font-mono">{tunnel.local_port}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-400">Remote Port:</span>
          <span className="text-white font-mono">{tunnel.remote_port}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-400">Tunnel ID:</span>
          <span className="text-white font-mono text-xs">
            {tunnel.tunnel_id.substring(0, 8)}...
          </span>
        </div>
      </div>

      {/* Footer */}
      <div className="mt-4 pt-4 border-t border-gray-700 flex items-center gap-4 text-xs text-gray-400">
        <div className="flex items-center gap-1">
          <FiClock className="w-3 h-3" />
          <span>
            {tunnel.created_at
              ? formatDistanceToNow(new Date(tunnel.created_at), { addSuffix: true })
              : 'Unknown'}
          </span>
        </div>
        {tunnel.health_status && (
          <div className="flex items-center gap-1">
            <FiActivity className="w-3 h-3" />
            <span className="capitalize">{tunnel.health_status}</span>
          </div>
        )}
      </div>
    </div>
  )
}
