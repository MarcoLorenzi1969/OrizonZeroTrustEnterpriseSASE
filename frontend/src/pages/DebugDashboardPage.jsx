import React, { useState, useEffect, useRef } from 'react'
import { Activity, AlertTriangle, CheckCircle, XCircle, Wifi, WifiOff, Cpu, HardDrive, Network } from 'lucide-react'

export default function DebugDashboardPage() {
  const [health, setHealth] = useState(null)
  const [connections, setConnections] = useState([])
  const [events, setEvents] = useState([])
  const [metrics, setMetrics] = useState([])
  const [selectedConnection, setSelectedConnection] = useState(null)
  const [diagnosis, setDiagnosis] = useState(null)

  const wsRef = useRef(null)
  const eventsEndRef = useRef(null)

  // API base URL
  const API_URL = import.meta.env.VITE_API_URL || window.location.origin

  // Fetch health status
  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const response = await fetch(`${API_URL}/api/v1/debug/health`)
        const data = await response.json()
        setHealth(data)
      } catch (error) {
        console.error('Failed to fetch health:', error)
      }
    }

    fetchHealth()
    const interval = setInterval(fetchHealth, 5000)
    return () => clearInterval(interval)
  }, [])

  // Fetch connections
  useEffect(() => {
    const fetchConnections = async () => {
      try {
        const response = await fetch(`${API_URL}/api/v1/debug/connections`)
        const data = await response.json()
        setConnections(data.connections || [])
      } catch (error) {
        console.error('Failed to fetch connections:', error)
      }
    }

    fetchConnections()
    const interval = setInterval(fetchConnections, 3000)
    return () => clearInterval(interval)
  }, [])

  // WebSocket for real-time events
  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = API_URL.replace(/^https?:\/\//, '')
    const wsUrl = `${protocol}//${host}/api/v1/debug/stream`

    wsRef.current = new WebSocket(wsUrl)

    wsRef.current.onopen = () => {
      console.log('Debug stream connected')
    }

    wsRef.current.onmessage = (event) => {
      const message = JSON.parse(event.data)

      if (message.type === 'event') {
        setEvents(prev => [...prev.slice(-99), message.data])
        // Auto-scroll to bottom
        setTimeout(() => eventsEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 100)
      } else if (message.type === 'metrics') {
        setMetrics(prev => [...prev.slice(-59), message.data])
      } else if (message.type === 'snapshot') {
        setEvents(message.data.recent_events || [])
        setMetrics(message.data.metrics?.history || [])
      }
    }

    wsRef.current.onerror = (error) => {
      console.error('WebSocket error:', error)
    }

    wsRef.current.onclose = () => {
      console.log('Debug stream disconnected')
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [])

  // Fetch connection diagnosis
  const diagnoseConnection = async (connectionId) => {
    try {
      const response = await fetch(`${API_URL}/api/v1/debug/diagnose/${connectionId}`)
      const data = await response.json()
      setDiagnosis(data)
    } catch (error) {
      console.error('Failed to diagnose connection:', error)
    }
  }

  // Get status color
  const getStatusColor = (status) => {
    switch (status) {
      case 'healthy':
      case 'active':
      case 'connected':
        return 'text-green-600'
      case 'degraded':
      case 'warning':
        return 'text-yellow-600'
      case 'critical':
      case 'error':
      case 'failed':
        return 'text-red-600'
      default:
        return 'text-gray-600'
    }
  }

  // Get status icon
  const getStatusIcon = (status) => {
    switch (status) {
      case 'healthy':
      case 'active':
      case 'connected':
        return <CheckCircle className="w-4 h-4" />
      case 'degraded':
      case 'warning':
        return <AlertTriangle className="w-4 h-4" />
      case 'critical':
      case 'error':
      case 'failed':
        return <XCircle className="w-4 h-4" />
      default:
        return <Activity className="w-4 h-4" />
    }
  }

  // Get event level color
  const getEventLevelColor = (level) => {
    switch (level) {
      case 'critical':
        return 'bg-red-100 text-red-800 border-red-300'
      case 'error':
        return 'bg-orange-100 text-orange-800 border-orange-300'
      case 'warning':
        return 'bg-yellow-100 text-yellow-800 border-yellow-300'
      case 'info':
        return 'bg-blue-100 text-blue-800 border-blue-300'
      default:
        return 'bg-gray-100 text-gray-800 border-gray-300'
    }
  }

  // Format bytes
  const formatBytes = (bytes) => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
  }

  // Format duration
  const formatDuration = (seconds) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
            <Activity className="w-8 h-8 text-blue-600" />
            Debug Dashboard
          </h1>
          <p className="text-gray-600 mt-2">
            Real-time monitoring and diagnostics for SSH, RDP, and VNC connections
          </p>
        </div>

        {/* System Health Overview */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {/* Backend Status */}
          <div className="bg-white rounded-lg shadow p-4 border-l-4 border-green-500">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Backend</p>
                <p className="text-2xl font-bold text-gray-900">
                  {health?.backend?.status || 'Unknown'}
                </p>
              </div>
              <Cpu className="w-8 h-8 text-green-500" />
            </div>
            {health?.backend && (
              <div className="mt-2 text-xs text-gray-500">
                CPU: {health.backend.cpu_percent?.toFixed(1)}% |
                Mem: {health.backend.memory_percent?.toFixed(1)}%
              </div>
            )}
          </div>

          {/* Connected Agents */}
          <div className="bg-white rounded-lg shadow p-4 border-l-4 border-blue-500">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Connected Agents</p>
                <p className="text-2xl font-bold text-gray-900">
                  {Object.keys(health?.agents || {}).length}
                </p>
              </div>
              <Network className="w-8 h-8 text-blue-500" />
            </div>
            <div className="mt-2 text-xs text-gray-500">
              {Object.values(health?.agents || {}).filter(a => a.status === 'healthy').length} healthy
            </div>
          </div>

          {/* Active Connections */}
          <div className="bg-white rounded-lg shadow p-4 border-l-4 border-purple-500">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Active Connections</p>
                <p className="text-2xl font-bold text-gray-900">
                  {health?.connections?.total || 0}
                </p>
              </div>
              <Wifi className="w-8 h-8 text-purple-500" />
            </div>
            {health?.connections && (
              <div className="mt-2 text-xs text-gray-500">
                SSH: {health.connections.ssh} |
                RDP: {health.connections.rdp} |
                VNC: {health.connections.vnc}
              </div>
            )}
          </div>

          {/* System Load */}
          <div className="bg-white rounded-lg shadow p-4 border-l-4 border-yellow-500">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">System Load</p>
                <p className="text-2xl font-bold text-gray-900">
                  {metrics[metrics.length - 1]?.cpu_percent?.toFixed(0) || 0}%
                </p>
              </div>
              <HardDrive className="w-8 h-8 text-yellow-500" />
            </div>
            <div className="mt-2 text-xs text-gray-500">
              Last minute average
            </div>
          </div>
        </div>

        {/* Agents Status Grid */}
        <div className="bg-white rounded-lg shadow mb-8">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">Edge Nodes Health</h2>
          </div>
          <div className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {Object.entries(health?.agents || {}).map(([nodeId, agent]) => (
                <div key={nodeId} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-mono text-sm text-gray-600">{nodeId.slice(0, 8)}...</span>
                    <div className={`flex items-center gap-1 ${getStatusColor(agent.status)}`}>
                      {getStatusIcon(agent.status)}
                      <span className="text-xs font-semibold uppercase">{agent.status}</span>
                    </div>
                  </div>

                  {agent.connected ? (
                    <div className="text-sm space-y-1">
                      {agent.latency_ms && (
                        <div className="flex justify-between">
                          <span className="text-gray-600">Latency:</span>
                          <span className="font-semibold">{agent.latency_ms.toFixed(0)} ms</span>
                        </div>
                      )}
                      {agent.last_heartbeat && (
                        <div className="flex justify-between">
                          <span className="text-gray-600">Last HB:</span>
                          <span className="font-semibold">
                            {Math.floor((Date.now() / 1000 - agent.last_heartbeat))} s ago
                          </span>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="flex items-center gap-2 text-red-600 text-sm">
                      <WifiOff className="w-4 h-4" />
                      <span>Disconnected</span>
                    </div>
                  )}

                  {agent.issues && agent.issues.length > 0 && (
                    <div className="mt-2 p-2 bg-red-50 rounded text-xs text-red-700">
                      {agent.issues.map((issue, idx) => (
                        <div key={idx}>• {issue}</div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Active Connections Table */}
        <div className="bg-white rounded-lg shadow mb-8">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">Active Connections</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Node ID</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Duration</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Data</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Latency</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {connections.map(conn => (
                  <tr key={conn.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="px-2 py-1 text-xs font-semibold rounded bg-blue-100 text-blue-800 uppercase">
                        {conn.type}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-gray-600">
                      {conn.node_id.slice(0, 12)}...
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className={`flex items-center gap-1 ${getStatusColor(conn.status)}`}>
                        {getStatusIcon(conn.status)}
                        <span className="text-xs font-semibold uppercase">{conn.status}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                      {formatDuration(conn.duration_sec)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                      <div className="text-xs">
                        ↑ {formatBytes(conn.bytes_sent)}
                        <br />
                        ↓ {formatBytes(conn.bytes_received)}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                      {conn.avg_latency_ms ? `${conn.avg_latency_ms.toFixed(0)} ms` : '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      {conn.status === 'failed' && (
                        <button
                          onClick={() => {
                            setSelectedConnection(conn)
                            diagnoseConnection(conn.id)
                          }}
                          className="text-blue-600 hover:text-blue-800 font-semibold"
                        >
                          Diagnose
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
                {connections.length === 0 && (
                  <tr>
                    <td colSpan={7} className="px-6 py-8 text-center text-gray-500">
                      No active connections
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Events Log */}
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">Real-Time Event Log</h2>
          </div>
          <div className="p-4 h-96 overflow-y-auto font-mono text-xs bg-gray-900 text-gray-100">
            {events.map((event, idx) => (
              <div key={idx} className="mb-1 flex items-start gap-2">
                <span className="text-gray-500 flex-shrink-0">
                  {new Date(event.timestamp).toLocaleTimeString()}
                </span>
                <span className={`px-1 py-0.5 rounded flex-shrink-0 ${getEventLevelColor(event.level)}`}>
                  {event.level.toUpperCase()}
                </span>
                <span className="text-blue-400 flex-shrink-0">[{event.component}]</span>
                <span className="text-gray-200">{event.message}</span>
              </div>
            ))}
            <div ref={eventsEndRef} />
          </div>
        </div>

        {/* Diagnosis Modal */}
        {selectedConnection && diagnosis && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto">
              <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
                <h3 className="text-lg font-semibold text-gray-900">Connection Diagnosis</h3>
                <button
                  onClick={() => {
                    setSelectedConnection(null)
                    setDiagnosis(null)
                  }}
                  className="text-gray-500 hover:text-gray-700"
                >
                  ✕
                </button>
              </div>

              <div className="p-6">
                <div className="mb-4">
                  <h4 className="font-semibold text-gray-700 mb-2">Connection Details</h4>
                  <div className="bg-gray-50 rounded p-3 space-y-1 text-sm">
                    <div><strong>Type:</strong> {selectedConnection.type.toUpperCase()}</div>
                    <div><strong>Node ID:</strong> <span className="font-mono">{selectedConnection.node_id}</span></div>
                    <div><strong>Status:</strong> <span className={getStatusColor(selectedConnection.status)}>{selectedConnection.status}</span></div>
                  </div>
                </div>

                {diagnosis.failure_stage && (
                  <div className="mb-4">
                    <h4 className="font-semibold text-gray-700 mb-2">Failure Point</h4>
                    <div className="bg-red-50 border border-red-200 rounded p-3">
                      <p className="text-sm font-semibold text-red-800">Stage: {diagnosis.failure_stage}</p>
                      {diagnosis.error && (
                        <p className="text-sm text-red-700 mt-1">{diagnosis.error}</p>
                      )}
                    </div>
                  </div>
                )}

                {diagnosis.root_cause && (
                  <div className="mb-4">
                    <h4 className="font-semibold text-gray-700 mb-2">Root Cause</h4>
                    <div className="bg-yellow-50 border border-yellow-200 rounded p-3">
                      <p className="text-sm text-yellow-800">{diagnosis.root_cause}</p>
                    </div>
                  </div>
                )}

                {diagnosis.suggestions && diagnosis.suggestions.length > 0 && (
                  <div>
                    <h4 className="font-semibold text-gray-700 mb-2">Suggested Actions</h4>
                    <ul className="space-y-2">
                      {diagnosis.suggestions.map((suggestion, idx) => (
                        <li key={idx} className="flex items-start gap-2 text-sm">
                          <span className="text-blue-600 flex-shrink-0">•</span>
                          <span className="text-gray-700">{suggestion}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              <div className="px-6 py-4 border-t border-gray-200 flex justify-end">
                <button
                  onClick={() => {
                    setSelectedConnection(null)
                    setDiagnosis(null)
                  }}
                  className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
