/**
 * Orizon Zero Trust Connect - Guacamole Remote Access Page
 * SSO-integrated remote desktop gateway
 */

import { useState, useEffect } from 'react'
import {
  Monitor,
  Terminal,
  Wifi,
  WifiOff,
  ExternalLink,
  Shield,
  RefreshCw,
  AlertCircle,
  CheckCircle,
  Loader
} from 'lucide-react'
import api from '../services/api'
import toast from 'react-hot-toast'
import debugService from '../services/debugService'

function GuacamolePage() {
  const [nodes, setNodes] = useState([])
  const [loading, setLoading] = useState(true)
  const [guacamoleHealth, setGuacamoleHealth] = useState(null)
  const [checkingHealth, setCheckingHealth] = useState(false)
  const [connectingTo, setConnectingTo] = useState(null)

  useEffect(() => {
    loadNodes()
    checkGuacamoleHealth()

    // Auto-refresh every 15 seconds
    const interval = setInterval(() => {
      loadNodes()
      checkGuacamoleHealth()
    }, 15000)

    return () => clearInterval(interval)
  }, [])

  const checkGuacamoleHealth = async () => {
    try {
      setCheckingHealth(true)
      debugService.info('Guacamole Page', { message: 'Checking Guacamole health...' })

      const response = await api.get('/guacamole/health')
      setGuacamoleHealth(response.data)

      debugService.success('Guacamole Page', {
        message: 'Health check complete',
        status: response.data.status
      })
    } catch (error) {
      debugService.error('Guacamole Page', {
        message: 'Health check failed',
        error: error.message
      })
      setGuacamoleHealth({ status: 'unhealthy', error: error.message })
    } finally {
      setCheckingHealth(false)
    }
  }

  const loadNodes = async () => {
    try {
      debugService.info('Guacamole Page', { message: 'Loading nodes...' })
      const response = await api.get('/nodes')
      const items = response.data.items || []

      // Filter only online nodes
      const onlineNodes = Array.isArray(items)
        ? items.filter(node => node.status === 'online')
        : []

      setNodes(onlineNodes)

      debugService.success('Guacamole Page', {
        message: 'Nodes loaded',
        total: items.length,
        online: onlineNodes.length
      })
    } catch (error) {
      debugService.error('Guacamole Page', {
        message: 'Failed to load nodes',
        error: error.message
      })
      setNodes([])
      if (loading) {
        toast.error('Failed to load nodes')
      }
    } finally {
      setLoading(false)
    }
  }

  const quickAccessNode = async (nodeId, protocol) => {
    try {
      setConnectingTo(`${nodeId}-${protocol}`)

      debugService.info('Guacamole Page', {
        message: 'Requesting quick access...',
        nodeId,
        protocol
      })

      toast.loading('Authenticating with Guacamole...', { id: 'guac-auth' })

      const response = await api.post(`/guacamole/nodes/${nodeId}/access/${protocol}`)

      debugService.success('Guacamole Page', {
        message: 'Access granted',
        connectionId: response.data.connection_id
      })

      toast.success('Access granted! Opening terminal...', { id: 'guac-auth' })

      // Open Guacamole in new window
      window.open(response.data.access_url, '_blank', 'noopener,noreferrer')

    } catch (error) {
      debugService.error('Guacamole Page', {
        message: 'Access failed',
        error: error.message,
        response: error.response?.data
      })

      toast.error(
        error.response?.data?.detail || 'Failed to access node',
        { id: 'guac-auth' }
      )
    } finally {
      setConnectingTo(null)
    }
  }

  const getNodeIcon = (node) => {
    if (node.status === 'online') {
      return <Wifi className="w-5 h-5 text-green-400" />
    }
    return <WifiOff className="w-5 h-5 text-gray-500" />
  }

  const getHealthStatusBadge = () => {
    if (!guacamoleHealth) {
      return (
        <span className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-gray-700 text-gray-400">
          <Loader className="w-4 h-4 mr-2 animate-spin" />
          Checking...
        </span>
      )
    }

    if (guacamoleHealth.status === 'healthy') {
      return (
        <span className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-green-900/30 text-green-400">
          <CheckCircle className="w-4 h-4 mr-2" />
          Guacamole Hub Online
        </span>
      )
    }

    return (
      <span className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-red-900/30 text-red-400">
        <AlertCircle className="w-4 h-4 mr-2" />
        Guacamole Hub Offline
      </span>
    )
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader className="w-8 h-8 text-blue-500 animate-spin" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <Monitor className="w-8 h-8 text-blue-500" />
            Remote Access
          </h1>
          <p className="text-gray-400 mt-1">
            Secure remote desktop and terminal access via Guacamole SSO
          </p>
        </div>
        <div className="flex items-center gap-4">
          {getHealthStatusBadge()}
          <button
            onClick={() => {
              loadNodes()
              checkGuacamoleHealth()
            }}
            className="p-2 bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors"
            title="Refresh"
          >
            <RefreshCw className="w-5 h-5 text-gray-400" />
          </button>
        </div>
      </div>

      {/* Guacamole Status Banner */}
      {guacamoleHealth?.status === 'unhealthy' && (
        <div className="bg-red-900/20 border border-red-800 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="text-red-400 font-semibold">Guacamole Hub Unavailable</h3>
              <p className="text-gray-400 text-sm mt-1">
                The Guacamole server is currently offline. Remote access is temporarily unavailable.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Info Banner */}
      <div className="bg-blue-900/20 border border-blue-800 rounded-lg p-4">
        <div className="flex items-start gap-3">
          <Shield className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="text-blue-400 font-semibold">Single Sign-On Enabled</h3>
            <p className="text-gray-400 text-sm mt-1">
              Your Orizon credentials are automatically used to authenticate with Guacamole.
              Click any protocol button below to establish a secure connection.
            </p>
          </div>
        </div>
      </div>

      {/* Nodes Grid */}
      {nodes.length === 0 ? (
        <div className="bg-gray-800/50 rounded-lg p-12 text-center">
          <Monitor className="w-16 h-16 text-gray-600 mx-auto mb-4" />
          <h3 className="text-xl font-semibold text-gray-400 mb-2">No Nodes Online</h3>
          <p className="text-gray-500">
            No edge nodes are currently connected. Deploy agents to enable remote access.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {nodes.map((node) => (
            <div
              key={node.id}
              className="bg-gray-800 border border-gray-700 rounded-lg p-6 hover:border-blue-500/50 transition-all"
            >
              {/* Node Header */}
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    {getNodeIcon(node)}
                    <h3 className="text-lg font-semibold text-white truncate">
                      {node.name}
                    </h3>
                  </div>
                  <p className="text-sm text-gray-400">{node.ip_address}</p>
                </div>
              </div>

              {/* Node Info */}
              <div className="space-y-2 mb-4 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-400">Type:</span>
                  <span className="text-white capitalize">{node.node_type || 'edge'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">OS:</span>
                  <span className="text-white truncate ml-2">
                    {node.os_info?.split(' ')[0] || 'Unknown'}
                  </span>
                </div>
              </div>

              {/* Protocol Buttons */}
              <div className="space-y-2">
                <p className="text-xs text-gray-500 uppercase font-semibold mb-3">
                  Connect via:
                </p>

                {/* SSH Button */}
                <button
                  onClick={() => quickAccessNode(node.id, 'ssh')}
                  disabled={connectingTo === `${node.id}-ssh` || guacamoleHealth?.status !== 'healthy'}
                  className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
                >
                  {connectingTo === `${node.id}-ssh` ? (
                    <Loader className="w-4 h-4 animate-spin" />
                  ) : (
                    <Terminal className="w-4 h-4" />
                  )}
                  <span className="font-medium">SSH Terminal</span>
                  <ExternalLink className="w-3.5 h-3.5 ml-auto" />
                </button>

                {/* RDP Button */}
                <button
                  onClick={() => quickAccessNode(node.id, 'rdp')}
                  disabled={connectingTo === `${node.id}-rdp` || guacamoleHealth?.status !== 'healthy'}
                  className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
                >
                  {connectingTo === `${node.id}-rdp` ? (
                    <Loader className="w-4 h-4 animate-spin" />
                  ) : (
                    <Monitor className="w-4 h-4" />
                  )}
                  <span className="font-medium">RDP Desktop</span>
                  <ExternalLink className="w-3.5 h-3.5 ml-auto" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default GuacamolePage
