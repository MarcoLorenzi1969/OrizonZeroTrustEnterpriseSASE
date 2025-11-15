/**
 * ACL Rule Card Component
 * For: Marco @ Syneto/Orizon
 */

import { FiShield, FiTrash2, FiToggleLeft, FiToggleRight } from 'react-icons/fi'

export default function ACLRuleCard({ rule, onDelete, onToggle }) {
  const getActionColor = (action) => {
    return action === 'allow'
      ? 'bg-green-500 bg-opacity-20 border-green-500 text-green-400'
      : 'bg-red-500 bg-opacity-20 border-red-500 text-red-400'
  }

  const getActionIcon = (action) => {
    return action === 'allow' ? '✓' : '✗'
  }

  return (
    <div className={`bg-gray-800 rounded-lg p-5 border-2 transition ${
      rule.is_active ? 'border-gray-700' : 'border-gray-800 opacity-60'
    }`}>
      <div className="flex justify-between items-start">
        {/* Left side - Rule info */}
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-3">
            {/* Priority badge */}
            <div className="bg-blue-600 text-white px-3 py-1 rounded-full text-sm font-semibold">
              Priority {rule.priority}
            </div>

            {/* Action badge */}
            <div className={`px-3 py-1 rounded-full text-sm font-semibold border-2 flex items-center gap-2 ${getActionColor(rule.action)}`}>
              <span>{getActionIcon(rule.action)}</span>
              <span className="uppercase">{rule.action}</span>
            </div>

            {/* Active status */}
            {!rule.is_active && (
              <span className="text-xs text-gray-500 bg-gray-700 px-2 py-1 rounded">
                INACTIVE
              </span>
            )}
          </div>

          {/* Description */}
          {rule.description && (
            <p className="text-gray-300 mb-3">{rule.description}</p>
          )}

          {/* Rule details grid */}
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <span className="text-gray-500">Source IP:</span>
              <span className="text-white ml-2 font-mono">
                {rule.source_ip || 'any'}
              </span>
            </div>
            <div>
              <span className="text-gray-500">Destination IP:</span>
              <span className="text-white ml-2 font-mono">
                {rule.destination_ip || 'any'}
              </span>
            </div>
            <div>
              <span className="text-gray-500">Source Port:</span>
              <span className="text-white ml-2 font-mono">
                {rule.source_port || 'any'}
              </span>
            </div>
            <div>
              <span className="text-gray-500">Destination Port:</span>
              <span className="text-white ml-2 font-mono">
                {rule.destination_port || 'any'}
              </span>
            </div>
            <div>
              <span className="text-gray-500">Protocol:</span>
              <span className="text-white ml-2 uppercase font-mono">
                {rule.protocol || 'any'}
              </span>
            </div>
            {rule.user_id && (
              <div>
                <span className="text-gray-500">User:</span>
                <span className="text-white ml-2">{rule.user_id}</span>
              </div>
            )}
          </div>

          {/* Metadata */}
          <div className="mt-3 pt-3 border-t border-gray-700 text-xs text-gray-500">
            Created: {new Date(rule.created_at).toLocaleString()}
            {rule.created_by && ` by ${rule.created_by}`}
          </div>
        </div>

        {/* Right side - Actions */}
        <div className="flex gap-2 ml-4">
          <button
            onClick={onToggle}
            className={`p-2 rounded-lg transition ${
              rule.is_active
                ? 'bg-yellow-600 hover:bg-yellow-700 text-white'
                : 'bg-green-600 hover:bg-green-700 text-white'
            }`}
            title={rule.is_active ? 'Disable rule' : 'Enable rule'}
          >
            {rule.is_active ? (
              <FiToggleRight className="w-5 h-5" />
            ) : (
              <FiToggleLeft className="w-5 h-5" />
            )}
          </button>
          <button
            onClick={onDelete}
            className="p-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition"
            title="Delete rule"
          >
            <FiTrash2 className="w-5 h-5" />
          </button>
        </div>
      </div>
    </div>
  )
}
