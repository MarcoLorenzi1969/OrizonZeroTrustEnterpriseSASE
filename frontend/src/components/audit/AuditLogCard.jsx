/**
 * Audit Log Card Component
 * For: Marco @ Syneto/Orizon
 */

import { FiClock, FiUser, FiMapPin, FiAlertCircle } from 'react-icons/fi'
import { formatDistanceToNow } from 'date-fns'

export default function AuditLogCard({ log }) {
  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'critical': return 'bg-red-500'
      case 'high': return 'bg-orange-500'
      case 'medium': return 'bg-yellow-500'
      case 'low': return 'bg-green-500'
      default: return 'bg-gray-500'
    }
  }

  const getSeverityBgColor = (severity) => {
    switch (severity) {
      case 'critical': return 'bg-red-500 bg-opacity-10 border-red-500'
      case 'high': return 'bg-orange-500 bg-opacity-10 border-orange-500'
      case 'medium': return 'bg-yellow-500 bg-opacity-10 border-yellow-500'
      case 'low': return 'bg-green-500 bg-opacity-10 border-green-500'
      default: return 'bg-gray-500 bg-opacity-10 border-gray-500'
    }
  }

  const getActionIcon = (action) => {
    const icons = {
      'login': '🔑',
      'logout': '🚪',
      'create': '➕',
      'update': '✏️',
      'delete': '🗑️',
      'access_granted': '✅',
      'access_denied': '🚫',
      'tunnel_created': '🔗',
      'tunnel_closed': '🔓',
      '2fa_enabled': '🔐',
      '2fa_disabled': '🔓',
      'password_changed': '🔑',
    }
    return icons[action] || '📝'
  }

  const status = log.status || 'success'
  const statusColor = status === 'failed' ? 'red' : status === 'success' ? 'green' : 'gray'

  return (
    <div className="bg-gray-800 rounded-lg p-2 border border-gray-700 hover:border-gray-600 transition">
      <div className="flex items-start gap-2">
        {/* Icon */}
        <div className="flex flex-col items-center">
          <span className="text-lg">{getActionIcon(log.action)}</span>
        </div>

        {/* Main content */}
        <div className="flex-1 min-w-0">
          {/* Header row - SMALLER TEXT */}
          <div className="flex justify-between items-start gap-2">
            <div className="flex-1 min-w-0">
              <h3 className="text-white font-medium text-xs truncate">
                {log.action}
              </h3>
              {log.resource_name && (
                <p className="text-gray-400 text-xs truncate">{log.resource_name}</p>
              )}
            </div>
            <span className={`px-2 py-0.5 rounded text-xs font-medium bg-${statusColor}-500 bg-opacity-20 text-${statusColor}-400 border border-${statusColor}-500 border-opacity-30 whitespace-nowrap`}>
              {log.resource_type || 'system'}
            </span>
          </div>

          {/* Metadata - COMPACT */}
          <div className="grid grid-cols-2 gap-2 mt-1.5 text-xs">
            {/* User */}
            {log.user_email && (
              <div className="flex items-center gap-1 text-gray-400 truncate">
                <FiUser className="w-3 h-3 flex-shrink-0" />
                <span className="truncate">{log.user_email}</span>
              </div>
            )}

            {/* Timestamp */}
            {log.timestamp && (
              <div className="flex items-center gap-1 text-gray-400 truncate">
                <FiClock className="w-3 h-3 flex-shrink-0" />
                <span className="truncate">
                  {formatDistanceToNow(new Date(log.timestamp), { addSuffix: true })}
                </span>
              </div>
            )}

            {/* IP Address */}
            {log.ip_address && (
              <div className="flex items-center gap-1 text-gray-400 truncate">
                <FiMapPin className="w-3 h-3 flex-shrink-0" />
                <span className="font-mono text-xs truncate">{log.ip_address}</span>
              </div>
            )}

            {/* Role */}
            {log.user_role && (
              <div className="text-gray-500 text-xs truncate">
                {log.user_role}
              </div>
            )}
          </div>

          {/* Additional details if present */}
          {(log.details || log.changes) && (
            <details className="mt-1.5 cursor-pointer">
              <summary className="text-xs text-gray-500 hover:text-gray-400">
                Details
              </summary>
              <div className="mt-1">
                <pre className="bg-gray-900 rounded p-1.5 text-gray-400 font-mono text-xs overflow-x-auto max-h-32 overflow-y-auto">
                  {JSON.stringify(log.details || log.changes, null, 2)}
                </pre>
              </div>
            </details>
          )}
        </div>
      </div>
    </div>
  )
}
