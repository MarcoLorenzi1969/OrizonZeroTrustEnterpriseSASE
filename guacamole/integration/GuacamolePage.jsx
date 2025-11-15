/**
 * Orizon Zero Trust Connect - Guacamole Management Page
 *
 * Add this to frontend/src/pages/GuacamolePage.jsx
 * Add route in App.jsx: <Route path="/guacamole" element={<GuacamolePage />} />
 */

import { useState, useEffect } from 'react'
import { toast } from 'react-toastify'
import {
  FiMonitor,
  FiRefreshCw,
  FiExternalLink,
  FiServer,
  FiActivity,
  FiUsers,
  FiLink
} from 'react-icons/fi'
import api from '../services/apiService'

export default function GuacamolePage() {
  const [status, setStatus] = useState(null)
  const [connections, setConnections] = useState([])
  const [activeSessions, setActiveSessions] = useState([])
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState(false)

  useEffect(() => {
    loadGuacamoleData()
  }, [])

  const loadGuacamoleData = async () => {
    setLoading(true)
    try {
      const [statusRes, connectionsRes, sessionsRes] = await Promise.all([
        api.get('/api/v1/guacamole/status'),
        api.get('/api/v1/guacamole/connections'),
        api.get('/api/v1/guacamole/active-sessions')
      ])

      setStatus(statusRes.data)
      setConnections(connectionsRes.data)
      setActiveSessions(sessionsRes.data.sessions || [])
    } catch (error) {
      console.error('Failed to load Guacamole data:', error)
      toast.error('Failed to load Guacamole data')
    } finally {
      setLoading(false)
    }
  }

  const handleSyncNodes = async () => {
    setSyncing(true)
    try {
      const response = await api.post('/api/v1/guacamole/sync-all-nodes')
      toast.success(response.data.message)
      await loadGuacamoleData()
    } catch (error) {
      console.error('Failed to sync nodes:', error)
      toast.error('Failed to sync nodes to Guacamole')
    } finally {
      setSyncing(false)
    }
  }

  const openGuacamole = () => {
    const url = status?.url + '/guacamole/'
    window.open(url, 'guacamole_admin', 'width=1280,height=800')
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-white">Guacamole Gateway</h1>
          <p className="text-gray-400 mt-1">
            Web-based SSH/RDP/VNC access to edge nodes
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={loadGuacamoleData}
            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg flex items-center gap-2"
          >
            <FiRefreshCw className="w-4 h-4" />
            Refresh
          </button>
          {status?.status === 'online' && (
            <button
              onClick={openGuacamole}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg flex items-center gap-2"
            >
              <FiExternalLink className="w-4 h-4" />
              Open Guacamole
            </button>
          )}
        </div>
      </div>

      {/* Status Card */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-gray-800 rounded-lg p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-400 text-sm">Status</p>
              <p className="text-2xl font-bold text-white mt-1">
                {status?.status === 'online' ? (
                  <span className="text-green-500">Online</span>
                ) : (
                  <span className="text-red-500">Offline</span>
                )}
              </p>
            </div>
            <FiServer className={`w-10 h-10 ${
              status?.status === 'online' ? 'text-green-500' : 'text-red-500'
            }`} />
          </div>
          {status?.url && (
            <p className="text-xs text-gray-500 mt-2">{status.url}</p>
          )}
        </div>

        <div className="bg-gray-800 rounded-lg p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-400 text-sm">Connections</p>
              <p className="text-2xl font-bold text-white mt-1">
                {connections.length}
              </p>
            </div>
            <FiLink className="w-10 h-10 text-blue-500" />
          </div>
          <p className="text-xs text-gray-500 mt-2">Configured connections</p>
        </div>

        <div className="bg-gray-800 rounded-lg p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-400 text-sm">Active Sessions</p>
              <p className="text-2xl font-bold text-white mt-1">
                {activeSessions.length}
              </p>
            </div>
            <FiUsers className="w-10 h-10 text-purple-500" />
          </div>
          <p className="text-xs text-gray-500 mt-2">Currently active</p>
        </div>

        <div className="bg-gray-800 rounded-lg p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-400 text-sm">Server</p>
              <p className="text-lg font-bold text-white mt-1">
                {status?.url?.replace('https://', '')}
              </p>
            </div>
            <FiActivity className="w-10 h-10 text-yellow-500" />
          </div>
          <p className="text-xs text-gray-500 mt-2">Gateway address</p>
        </div>
      </div>

      {/* Sync Button */}
      <div className="bg-gray-800 rounded-lg p-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-white">Sync Nodes to Guacamole</h2>
            <p className="text-gray-400 text-sm mt-1">
              Synchronize all Orizon nodes as SSH connections in Guacamole
            </p>
          </div>
          <button
            onClick={handleSyncNodes}
            disabled={syncing || status?.status !== 'online'}
            className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <FiRefreshCw className={`w-4 h-4 ${syncing ? 'animate-spin' : ''}`} />
            {syncing ? 'Syncing...' : 'Sync All Nodes'}
          </button>
        </div>
      </div>

      {/* Connections List */}
      <div className="bg-gray-800 rounded-lg">
        <div className="p-6 border-b border-gray-700">
          <h2 className="text-xl font-bold text-white">Configured Connections</h2>
        </div>
        <div className="p-6">
          {connections.length === 0 ? (
            <div className="text-center py-12 text-gray-400">
              <FiMonitor className="w-16 h-16 mx-auto mb-4 opacity-50" />
              <p>No connections configured</p>
              <p className="text-sm mt-2">Click "Sync All Nodes" to create connections</p>
            </div>
          ) : (
            <div className="space-y-3">
              {connections.map(conn => (
                <div
                  key={conn.id}
                  className="flex items-center justify-between p-4 bg-gray-700 rounded-lg hover:bg-gray-600 transition"
                >
                  <div className="flex items-center gap-4">
                    <div className={`p-3 rounded-lg ${
                      conn.protocol === 'ssh' ? 'bg-green-500 bg-opacity-20' :
                      conn.protocol === 'rdp' ? 'bg-blue-500 bg-opacity-20' :
                      'bg-purple-500 bg-opacity-20'
                    }`}>
                      <FiMonitor className={`w-6 h-6 ${
                        conn.protocol === 'ssh' ? 'text-green-400' :
                        conn.protocol === 'rdp' ? 'text-blue-400' :
                        'text-purple-400'
                      }`} />
                    </div>
                    <div>
                      <h3 className="text-white font-semibold">{conn.name}</h3>
                      <p className="text-sm text-gray-400">
                        {conn.protocol.toUpperCase()} - {conn.hostname}:{conn.port}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                      conn.protocol === 'ssh' ? 'bg-green-500 bg-opacity-20 text-green-400' :
                      conn.protocol === 'rdp' ? 'bg-blue-500 bg-opacity-20 text-blue-400' :
                      'bg-purple-500 bg-opacity-20 text-purple-400'
                    }`}>
                      {conn.protocol.toUpperCase()}
                    </span>
                    <button
                      onClick={() => window.open(
                        `${status.url}/guacamole/#/client/${conn.id}`,
                        'guacamole_' + conn.id,
                        'width=1280,height=800'
                      )}
                      className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg flex items-center gap-2"
                    >
                      Connect
                      <FiExternalLink className="w-3 h-3" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Active Sessions */}
      {activeSessions.length > 0 && (
        <div className="bg-gray-800 rounded-lg">
          <div className="p-6 border-b border-gray-700">
            <h2 className="text-xl font-bold text-white">Active Sessions</h2>
          </div>
          <div className="p-6">
            <div className="space-y-3">
              {activeSessions.map((session, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between p-4 bg-gray-700 rounded-lg"
                >
                  <div className="flex items-center gap-4">
                    <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                    <div>
                      <h3 className="text-white font-semibold">
                        {session.username || 'Unknown User'}
                      </h3>
                      <p className="text-sm text-gray-400">
                        Connection: {session.connectionIdentifier || 'N/A'}
                      </p>
                    </div>
                  </div>
                  <span className="text-xs text-gray-500">Active</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
