import { useState } from 'react'
import { X, Users } from 'lucide-react'

function CreateGroupModal({ onClose, onCreate }) {
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    settings: {
      allow_terminal: true,
      allow_rdp: false,
      allow_vnc: false,
      max_concurrent_sessions: 5
    }
  })

  const handleSubmit = (e) => {
    e.preventDefault()
    onCreate(formData)
  }

  const handleSettingToggle = (setting) => {
    setFormData(prev => ({
      ...prev,
      settings: {
        ...prev.settings,
        [setting]: !prev.settings[setting]
      }
    }))
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-2">
            <Users className="w-6 h-6 text-blue-600" />
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
              Create New Group
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {/* Name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Group Name *
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
              className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              placeholder="e.g., Engineering, Marketing, DevOps"
              required
            />
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Description
            </label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
              className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              placeholder="Describe the purpose of this group"
              rows={3}
            />
          </div>

          {/* Settings */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
              Access Permissions
            </label>
            <div className="space-y-3">
              {/* SSH Terminal */}
              <label className="flex items-center gap-3 p-3 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700/50 cursor-pointer">
                <input
                  type="checkbox"
                  checked={formData.settings.allow_terminal}
                  onChange={() => handleSettingToggle('allow_terminal')}
                  className="w-5 h-5 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                />
                <div className="flex-1">
                  <div className="font-medium text-gray-900 dark:text-white">
                    Allow SSH Terminal
                  </div>
                  <div className="text-sm text-gray-500 dark:text-gray-400">
                    Members can access nodes via SSH terminal
                  </div>
                </div>
              </label>

              {/* RDP */}
              <label className="flex items-center gap-3 p-3 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700/50 cursor-pointer">
                <input
                  type="checkbox"
                  checked={formData.settings.allow_rdp}
                  onChange={() => handleSettingToggle('allow_rdp')}
                  className="w-5 h-5 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                />
                <div className="flex-1">
                  <div className="font-medium text-gray-900 dark:text-white">
                    Allow RDP Access
                  </div>
                  <div className="text-sm text-gray-500 dark:text-gray-400">
                    Members can access Windows nodes via Remote Desktop
                  </div>
                </div>
              </label>

              {/* VNC */}
              <label className="flex items-center gap-3 p-3 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700/50 cursor-pointer">
                <input
                  type="checkbox"
                  checked={formData.settings.allow_vnc}
                  onChange={() => handleSettingToggle('allow_vnc')}
                  className="w-5 h-5 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                />
                <div className="flex-1">
                  <div className="font-medium text-gray-900 dark:text-white">
                    Allow VNC Access
                  </div>
                  <div className="text-sm text-gray-500 dark:text-gray-400">
                    Members can access nodes via VNC
                  </div>
                </div>
              </label>
            </div>
          </div>

          {/* Max Sessions */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Max Concurrent Sessions
            </label>
            <input
              type="number"
              min="1"
              max="50"
              value={formData.settings.max_concurrent_sessions}
              onChange={(e) => setFormData(prev => ({
                ...prev,
                settings: {
                  ...prev.settings,
                  max_concurrent_sessions: parseInt(e.target.value)
                }
              }))}
              className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
            />
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              Maximum number of concurrent sessions per member
            </p>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              Create Group
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default CreateGroupModal
