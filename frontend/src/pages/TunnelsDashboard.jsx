import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Activity, Wifi, WifiOff, Server, MonitorPlay, Link, Link2Off, RefreshCw, AlertCircle, CheckCircle2, Copy, Check } from 'lucide-react'
import api from '../services/api'
import { toast } from 'react-hot-toast'

const TunnelsDashboard = () => {
  const [dashboardData, setDashboardData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [lastUpdate, setLastUpdate] = useState(null)
  const [copied, setCopied] = useState(false)
  const navigate = useNavigate()

  const fetchDashboard = async () => {
    try {
      setLoading(true)
      const response = await api.get('/tunnels/dashboard')
      setDashboardData(response.data)
      setLastUpdate(new Date())
    } catch (error) {
      console.error('Error fetching tunnels dashboard:', error)
      toast.error('Failed to load tunnels dashboard')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchDashboard()

    // Auto-refresh every 30 seconds
    const interval = setInterval(fetchDashboard, 30000)
    return () => clearInterval(interval)
  }, [])

  const copyToClipboard = async () => {
    if (!dashboardData) {
      toast.error('No data to copy')
      return
    }

    try {
      // Create a formatted JSON with all tunnel information
      const tunnelConfig = {
        timestamp: new Date().toISOString(),
        summary: dashboardData.summary,
        nodes: dashboardData.nodes.map(node => ({
          id: node.id,
          name: node.name,
          type: node.node_type,
          status: node.status,
          ip_address: node.ip_address,
          websocket_connected: node.websocket_connected,
          services: node.services,
          last_seen: node.last_seen
        })),
        websocket_tunnels: dashboardData.websocket_tunnels.map(tunnel => ({
          node_name: tunnel.node_name,
          node_ip: tunnel.node_ip,
          node_type: tunnel.node_type,
          protocol: tunnel.protocol,
          endpoint: tunnel.endpoint,
          status: tunnel.status,
          last_heartbeat: tunnel.last_heartbeat
        })),
        ssh_tunnels: dashboardData.ssh_tunnels.map(tunnel => ({
          node_name: tunnel.node_name,
          protocol: tunnel.protocol,
          tunnel_port: tunnel.tunnel_port,
          local_port: tunnel.local_port,
          guacamole_server: tunnel.guacamole_server,
          guacamole_server_name: tunnel.guacamole_server_name,
          connection_name: tunnel.connection_name,
          status: tunnel.status
        }))
      }

      // Copy to clipboard
      await navigator.clipboard.writeText(JSON.stringify(tunnelConfig, null, 2))

      setCopied(true)
      toast.success('Tunnel configuration copied to clipboard!')

      // Reset copied state after 2 seconds
      setTimeout(() => setCopied(false), 2000)
    } catch (error) {
      console.error('Error copying to clipboard:', error)
      toast.error('Failed to copy to clipboard')
    }
  }

  if (loading && !dashboardData) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="flex flex-col items-center gap-4">
          <RefreshCw className="w-8 h-8 animate-spin text-blue-400" />
          <p className="text-slate-400">Loading tunnels dashboard...</p>
        </div>
      </div>
    )
  }

  const { nodes, websocket_tunnels, ssh_tunnels, summary, timestamp } = dashboardData || {}

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white p-6">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">
              Tunnels & Connections Dashboard
            </h1>
            <p className="text-slate-400 mt-2">
              Monitor all WebSocket and SSH tunnels across the infrastructure
            </p>
          </div>
          <div className="flex gap-3">
            <button
              onClick={copyToClipboard}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                copied
                  ? 'bg-green-600 hover:bg-green-500'
                  : 'bg-blue-600 hover:bg-blue-500'
              }`}
            >
              {copied ? (
                <>
                  <Check className="w-4 h-4" />
                  Copied!
                </>
              ) : (
                <>
                  <Copy className="w-4 h-4" />
                  Copy JSON
                </>
              )}
            </button>
            <button
              onClick={fetchDashboard}
              className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>
        </div>

        {/* Last Update Time */}
        {lastUpdate && (
          <p className="text-xs text-slate-500 mt-2">
            Last updated: {lastUpdate.toLocaleTimeString()}
          </p>
        )}
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-slate-400 text-sm">Total Nodes</p>
              <p className="text-3xl font-bold text-white mt-1">{summary?.total_nodes || 0}</p>
            </div>
            <Server className="w-10 h-10 text-blue-400" />
          </div>
        </div>

        <div className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-slate-400 text-sm">Online Nodes</p>
              <p className="text-3xl font-bold text-green-400 mt-1">{summary?.online_nodes || 0}</p>
            </div>
            <CheckCircle2 className="w-10 h-10 text-green-400" />
          </div>
        </div>

        <div className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-slate-400 text-sm">WebSocket Active</p>
              <p className="text-3xl font-bold text-cyan-400 mt-1">{summary?.websocket_active || 0}</p>
            </div>
            <Wifi className="w-10 h-10 text-cyan-400" />
          </div>
        </div>

        <div className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-slate-400 text-sm">SSH Tunnels</p>
              <p className="text-3xl font-bold text-purple-400 mt-1">{summary?.ssh_tunnels_configured || 0}</p>
            </div>
            <Link className="w-10 h-10 text-purple-400" />
          </div>
        </div>
      </div>

      {/* Nodes Grid */}
      <div className="mb-8">
        <h2 className="text-2xl font-bold mb-4 flex items-center gap-2">
          <Server className="w-6 h-6 text-blue-400" />
          Registered Nodes
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {nodes?.map((node) => (
            <div
              key={node.id}
              className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-6 hover:border-blue-500/50 transition-colors"
            >
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-white mb-1">{node.name}</h3>
                  <p className="text-sm text-slate-400">{node.description}</p>
                </div>
                <div className={`px-3 py-1 rounded-full text-xs font-medium ${
                  node.status === 'online' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
                }`}>
                  {node.status}
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex items-center gap-2 text-sm">
                  <span className="text-slate-500">Type:</span>
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                    node.node_type === 'hub' ? 'bg-blue-500/20 text-blue-400' : 'bg-cyan-500/20 text-cyan-400'
                  }`}>
                    {node.node_type}
                  </span>
                </div>

                <div className="flex items-center gap-2 text-sm">
                  <span className="text-slate-500">IP:</span>
                  <span className="text-slate-300 font-mono text-xs">{node.ip_address}</span>
                </div>

                <div className="flex items-center gap-2 text-sm">
                  <span className="text-slate-500">WebSocket:</span>
                  {node.websocket_connected ? (
                    <div className="flex items-center gap-1 text-green-400">
                      <Wifi className="w-4 h-4" />
                      <span className="text-xs">Connected</span>
                    </div>
                  ) : (
                    <div className="flex items-center gap-1 text-red-400">
                      <WifiOff className="w-4 h-4" />
                      <span className="text-xs">Disconnected</span>
                    </div>
                  )}
                </div>

                {node.services && node.services.length > 0 && (
                  <div className="mt-4 pt-4 border-t border-slate-700">
                    <p className="text-xs text-slate-500 mb-2">Services:</p>
                    <div className="flex flex-wrap gap-2">
                      {node.services.map((service, idx) => (
                        <div
                          key={idx}
                          className="px-2 py-1 bg-slate-700/50 rounded text-xs text-slate-300"
                        >
                          {service.protocol || service.type}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {node.last_seen && (
                  <div className="text-xs text-slate-500 mt-2">
                    Last seen: {new Date(node.last_seen).toLocaleString()}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* WebSocket Tunnels */}
      <div className="mb-8">
        <h2 className="text-2xl font-bold mb-4 flex items-center gap-2">
          <Wifi className="w-6 h-6 text-cyan-400" />
          WebSocket Tunnels
          <span className="text-sm font-normal text-slate-400">
            ({websocket_tunnels?.length || 0} active)
          </span>
        </h2>

        {websocket_tunnels && websocket_tunnels.length > 0 ? (
          <div className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="bg-slate-700/50">
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                    Node
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                    IP Address
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                    Type
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                    Protocol
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                    Last Heartbeat
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700">
                {websocket_tunnels.map((tunnel) => (
                  <tr key={tunnel.node_id} className="hover:bg-slate-700/30">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-white">{tunnel.node_name}</div>
                      <div className="text-xs text-slate-400 font-mono">{tunnel.node_id.substring(0, 8)}...</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="text-sm text-slate-300 font-mono">{tunnel.node_ip}</span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 rounded text-xs font-medium ${
                        tunnel.node_type === 'hub' ? 'bg-blue-500/20 text-blue-400' : 'bg-cyan-500/20 text-cyan-400'
                      }`}>
                        {tunnel.node_type}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="text-sm text-slate-300">{tunnel.protocol}</span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        <Activity className="w-4 h-4 text-green-400 animate-pulse" />
                        <span className="text-sm text-green-400">{tunnel.status}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="text-xs text-slate-400">
                        {tunnel.last_heartbeat ? new Date(tunnel.last_heartbeat).toLocaleTimeString() : 'N/A'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-8 text-center">
            <WifiOff className="w-12 h-12 text-slate-600 mx-auto mb-4" />
            <p className="text-slate-400">No active WebSocket tunnels</p>
          </div>
        )}
      </div>

      {/* SSH Tunnels */}
      <div>
        <h2 className="text-2xl font-bold mb-4 flex items-center gap-2">
          <Link className="w-6 h-6 text-purple-400" />
          SSH Reverse Tunnels
          <span className="text-sm font-normal text-slate-400">
            ({ssh_tunnels?.length || 0} configured)
          </span>
        </h2>

        {ssh_tunnels && ssh_tunnels.length > 0 ? (
          <div className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="bg-slate-700/50">
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                    Node
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                    Protocol
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                    Tunnel Port
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                    Local Port
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                    Guacamole Server
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                    Status
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700">
                {ssh_tunnels.map((tunnel, idx) => (
                  <tr key={idx} className="hover:bg-slate-700/30">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-white">{tunnel.node_name}</div>
                      <div className="text-xs text-slate-400">{tunnel.connection_name}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 rounded text-xs font-medium ${
                        tunnel.protocol === 'SSH' ? 'bg-green-500/20 text-green-400' : 'bg-purple-500/20 text-purple-400'
                      }`}>
                        {tunnel.protocol}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="text-sm text-slate-300 font-mono">{tunnel.tunnel_port}</span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="text-sm text-slate-300 font-mono">{tunnel.local_port}</span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-slate-300 font-mono">{tunnel.guacamole_server}</div>
                      <div className="text-xs text-slate-500">{tunnel.guacamole_server_name}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        <CheckCircle2 className="w-4 h-4 text-green-400" />
                        <span className="text-sm text-green-400">{tunnel.status}</span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-8 text-center">
            <Link2Off className="w-12 h-12 text-slate-600 mx-auto mb-4" />
            <p className="text-slate-400">No SSH reverse tunnels configured</p>
            <p className="text-xs text-slate-500 mt-2">
              SSH tunnels are used for NAT traversal to enable remote access
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

export default TunnelsDashboard
