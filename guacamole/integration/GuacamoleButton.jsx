/**
 * Orizon Zero Trust Connect - Guacamole Access Button Component
 *
 * Add this component to frontend/src/components/nodes/
 * Use it in NodeCard.jsx to provide SSH access via Guacamole
 */

import { useState } from 'react'
import { FiExternalLink, FiMonitor } from 'react-icons/fi'
import { toast } from 'react-toastify'
import api from '../../services/apiService'

export default function GuacamoleButton({ node }) {
  const [loading, setLoading] = useState(false)

  const handleGuacamoleAccess = async () => {
    setLoading(true)
    try {
      // Get Guacamole access URL from backend
      const response = await api.get(`/api/v1/guacamole/nodes/${node.id}/access-url`)

      if (response.data.url) {
        // Open Guacamole in new window
        const width = 1280
        const height = 800
        const left = (window.screen.width - width) / 2
        const top = (window.screen.height - height) / 2

        window.open(
          response.data.url,
          'guacamole_' + node.id,
          `width=${width},height=${height},left=${left},top=${top},toolbar=no,location=no,status=no,menubar=no,scrollbars=yes,resizable=yes`
        )

        toast.success(`Opening SSH session to ${node.name}`)
      } else {
        toast.error('Failed to get Guacamole access URL')
      }
    } catch (error) {
      console.error('Guacamole access error:', error)
      toast.error(error.response?.data?.detail || 'Failed to access node via Guacamole')
    } finally {
      setLoading(false)
    }
  }

  return (
    <button
      onClick={handleGuacamoleAccess}
      disabled={loading || node.status !== 'online'}
      className={`
        flex items-center gap-2 px-4 py-2 rounded-lg
        transition-all duration-200
        ${node.status === 'online'
          ? 'bg-green-600 hover:bg-green-700 text-white'
          : 'bg-gray-600 text-gray-400 cursor-not-allowed'
        }
        ${loading ? 'opacity-50 cursor-wait' : ''}
      `}
      title={node.status === 'online' ? 'Access via Guacamole SSH' : 'Node is offline'}
    >
      <FiMonitor className="w-4 h-4" />
      <span>{loading ? 'Opening...' : 'SSH Access'}</span>
      <FiExternalLink className="w-3 h-3" />
    </button>
  )
}
