/**
 * Node Card Component
 * For: Marco @ Syneto/Orizon
 */

import { FiServer, FiTrash2, FiActivity, FiClock, FiMapPin } from 'react-icons/fi'
import { formatDistanceToNow } from 'date-fns'

export default function NodeCard({ node, onDelete }) {
  const getStatusColor = (status) => {
    switch (status) {
      case 'online': return 'bg-green-500'
      case 'offline': return 'bg-gray-500'
      case 'error': return 'bg-red-500'
      default: return 'bg-gray-500'
    }
  }

  const getStatusBgColor = (status) => {
    switch (status) {
      case 'online': return 'border-green-500'
      case 'offline': return 'border-gray-600'
      case 'error': return 'border-red-500'
      default: return 'border-gray-600'
    }
  }

  return (
    <div className={`bg-gray-800 rounded-lg p-6 border-2 ${getStatusBgColor(node.status)} hover:border-opacity-80 transition`}>
      {/* Header */}
      <div className="flex justify-between items-start mb-4">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 bg-gray-700 rounded-lg flex items-center justify-center">
            <FiServer className="w-6 h-6 text-blue-400" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-white">{node.name}</h3>
            <p className="text-sm text-gray-400">{node.description}</p>
          </div>
        </div>
        <button
          onClick={onDelete}
          className="text-gray-400 hover:text-red-500 transition"
          title="Delete node"
        >
          <FiTrash2 className="w-5 h-5" />
        </button>
      </div>

      {/* Status */}
      <div className="flex items-center gap-2 mb-4">
        <span className={`w-3 h-3 rounded-full ${getStatusColor(node.status)} ${
          node.status === 'online' ? 'animate-pulse' : ''
        }`}></span>
        <span className={`text-sm font-medium capitalize ${
          node.status === 'online' ? 'text-green-400' :
          node.status === 'error' ? 'text-red-400' :
          'text-gray-400'
        }`}>
          {node.status}
        </span>
      </div>

      {/* Details */}
      <div className="space-y-2 text-sm">
        <div className="flex items-center justify-between">
          <span className="text-gray-400">IP Address:</span>
          <span className="text-white font-mono">{node.ip_address}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-gray-400">Type:</span>
          <span className="text-white capitalize">{node.node_type}</span>
        </div>
        {node.location && (
          <div className="flex items-center justify-between">
            <span className="text-gray-400 flex items-center gap-1">
              <FiMapPin className="w-3 h-3" />
              Location:
            </span>
            <span className="text-white">{node.location}</span>
          </div>
        )}
      </div>

      {/* Metrics (if available) */}
      {node.cpu_usage !== undefined && (
        <div className="mt-4 pt-4 border-t border-gray-700 space-y-2">
          <div className="flex justify-between text-xs">
            <span className="text-gray-400">CPU Usage:</span>
            <span className="text-white">{node.cpu_usage.toFixed(1)}%</span>
          </div>
          <div className="w-full bg-gray-700 rounded-full h-2">
            <div
              className="bg-blue-500 h-2 rounded-full transition-all"
              style={{ width: `${node.cpu_usage}%` }}
            ></div>
          </div>
          {node.memory_usage !== undefined && (
            <>
              <div className="flex justify-between text-xs">
                <span className="text-gray-400">Memory Usage:</span>
                <span className="text-white">{node.memory_usage.toFixed(1)}%</span>
              </div>
              <div className="w-full bg-gray-700 rounded-full h-2">
                <div
                  className="bg-purple-500 h-2 rounded-full transition-all"
                  style={{ width: `${node.memory_usage}%` }}
                ></div>
              </div>
            </>
          )}
        </div>
      )}

      {/* Footer */}
      <div className="mt-4 pt-4 border-t border-gray-700 flex items-center justify-between text-xs text-gray-400">
        <div className="flex items-center gap-1">
          <FiClock className="w-3 h-3" />
          <span>
            {node.last_seen
              ? formatDistanceToNow(new Date(node.last_seen), { addSuffix: true })
              : 'Never'}
          </span>
        </div>
        {node.active_tunnels !== undefined && (
          <div className="flex items-center gap-1">
            <FiActivity className="w-3 h-3" />
            <span>{node.active_tunnels} active tunnel{node.active_tunnels !== 1 ? 's' : ''}</span>
          </div>
        )}
      </div>
    </div>
  )
}
