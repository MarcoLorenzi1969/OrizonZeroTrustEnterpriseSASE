import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Activity, Wifi, WifiOff, Server, MonitorPlay, Link, Link2Off, RefreshCw, AlertCircle, CheckCircle2, Copy, Check, Terminal, Lock, Globe, Shield, ShieldAlert, ShieldCheck, Heart, HeartPulse, Zap } from 'lucide-react'
import api from '../services/api'
import { toast } from 'react-hot-toast'
import { debugData } from '../utils/debugLogger'

const TunnelsDashboard = () => {
  const [dashboardData, setDashboardData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [lastUpdate, setLastUpdate] = useState(null)
  const [copied, setCopied] = useState(false)
  const [keepAliveStatus, setKeepAliveStatus] = useState({})
  const navigate = useNavigate()

  const fetchDashboard = async () => {
    try {
      setLoading(true)
      const response = await api.get('/tunnels/dashboard')
      debugData.received('TunnelsDashboard', response.data)
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

    // Auto-refresh every 15 seconds for keep-alive monitoring
    const interval = setInterval(fetchDashboard, 15000)
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
        tunnels: dashboardData.tunnels?.map(tunnel => ({
          tunnel_id: tunnel.tunnel_id,
          node_id: tunnel.node_id,
          node_name: tunnel.node_name,
          application: tunnel.application,
          local_port: tunnel.local_port,
          remote_port: tunnel.remote_port,
          status: tunnel.status,
          connected_at: tunnel.connected_at
        })) || []
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

  // Use the actual API structure: summary + system_tunnels + tunnels array
  const { summary, system_tunnels, tunnels } = dashboardData || {}

  // Group tunnels by type for display
  const terminalTunnels = tunnels?.filter(t => t.application === 'TERMINAL') || []
  const httpsTunnels = tunnels?.filter(t => t.application === 'HTTPS') || []
  const otherTunnels = tunnels?.filter(t => !['TERMINAL', 'HTTPS'].includes(t.application)) || []

  // Calculate time since last heartbeat for keep-alive indicator
  const getTimeSinceHeartbeat = (lastHeartbeat) => {
    if (!lastHeartbeat) return null
    const diff = Date.now() - new Date(lastHeartbeat).getTime()
    const seconds = Math.floor(diff / 1000)
    if (seconds < 60) return `${seconds}s ago`
    const minutes = Math.floor(seconds / 60)
    if (minutes < 60) return `${minutes}m ago`
    const hours = Math.floor(minutes / 60)
    return `${hours}h ago`
  }

  // Get icon for tunnel type
  const getTunnelIcon = (application) => {
    switch (application) {
      case 'TERMINAL': return <Terminal className="w-4 h-4 text-green-400" />
      case 'HTTPS': return <Lock className="w-4 h-4 text-cyan-400" />
      default: return <Globe className="w-4 h-4 text-purple-400" />
    }
  }

  // Get color for tunnel type
  const getTunnelColor = (application) => {
    switch (application) {
      case 'TERMINAL': return 'bg-green-500/20 text-green-400 border-green-500/50'
      case 'HTTPS': return 'bg-cyan-500/20 text-cyan-400 border-cyan-500/50'
      default: return 'bg-purple-500/20 text-purple-400 border-purple-500/50'
    }
  }

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white mb-2">Tunnels & Connections</h1>
          <p className="text-slate-400">
            Monitor all active reverse tunnels across the infrastructure
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={copyToClipboard}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
              copied
                ? 'bg-green-600 hover:bg-green-500'
                : 'bg-slate-700 hover:bg-slate-600'
            } text-white`}
          >
            {copied ? (
              <>
                <Check className="w-4 h-4" />
                Copied!
              </>
            ) : (
              <>
                <Copy className="w-4 h-4" />
                Export
              </>
            )}
          </button>
          <button
            onClick={fetchDashboard}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Last Update Time */}
      {lastUpdate && (
        <p className="text-xs text-slate-500">
          Last updated: {lastUpdate.toLocaleTimeString()}
        </p>
      )}

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <div className="bg-slate-800 border border-slate-700 rounded-xl p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-slate-400 text-sm">Total Nodes</p>
              <p className="text-2xl font-bold text-white mt-1">{summary?.total_nodes || 0}</p>
            </div>
            <Server className="w-8 h-8 text-blue-400" />
          </div>
        </div>

        <div className="bg-slate-800 border border-slate-700 rounded-xl p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-slate-400 text-sm">Online Nodes</p>
              <p className="text-2xl font-bold text-green-400 mt-1">{summary?.online_nodes || 0}</p>
            </div>
            <CheckCircle2 className="w-8 h-8 text-green-400" />
          </div>
        </div>

        {/* System Tunnels Card - highlighted */}
        <div className="bg-gradient-to-br from-amber-900/30 to-orange-900/30 border border-amber-500/50 rounded-xl p-5 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-20 h-20 bg-amber-500/10 rounded-full -mr-10 -mt-10" />
          <div className="flex items-center justify-between relative z-10">
            <div>
              <p className="text-amber-300 text-sm font-medium">System Tunnels</p>
              <div className="flex items-baseline gap-2 mt-1">
                <p className="text-2xl font-bold text-amber-400">{summary?.system_tunnels || 0}</p>
                {summary?.system_tunnels_healthy > 0 && (
                  <span className="text-xs text-green-400 flex items-center gap-1">
                    <HeartPulse className="w-3 h-3" />
                    {summary?.system_tunnels_healthy} live
                  </span>
                )}
              </div>
              {summary?.system_tunnels_unhealthy > 0 && (
                <p className="text-xs text-red-400 mt-1 flex items-center gap-1">
                  <AlertCircle className="w-3 h-3" />
                  {summary?.system_tunnels_unhealthy} need attention
                </p>
              )}
            </div>
            <Shield className="w-8 h-8 text-amber-400" />
          </div>
        </div>

        <div className="bg-slate-800 border border-slate-700 rounded-xl p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-slate-400 text-sm">App Tunnels</p>
              <p className="text-2xl font-bold text-cyan-400 mt-1">{summary?.application_tunnels || tunnels?.length || 0}</p>
            </div>
            <Activity className="w-8 h-8 text-cyan-400" />
          </div>
        </div>

        <div className="bg-slate-800 border border-slate-700 rounded-xl p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-slate-400 text-sm">Offline Nodes</p>
              <p className="text-2xl font-bold text-slate-400 mt-1">{summary?.offline_nodes || 0}</p>
            </div>
            <WifiOff className="w-8 h-8 text-slate-500" />
          </div>
        </div>
      </div>

      {/* System Tunnels Section - Distinctive Amber/Gold styling */}
      <div>
        <h2 className="text-xl font-bold mb-4 flex items-center gap-2 text-white">
          <Shield className="w-5 h-5 text-amber-400" />
          <span className="text-amber-400">System Tunnels</span>
          <span className="text-sm font-normal text-amber-300/70">
            (Keep-Alive Protected)
          </span>
          <span className="ml-auto text-xs font-normal text-slate-400 flex items-center gap-1">
            <RefreshCw className="w-3 h-3" />
            Auto-refresh: 15s
          </span>
        </h2>

        {system_tunnels && system_tunnels.length > 0 ? (
          <div className="bg-gradient-to-br from-amber-950/40 to-orange-950/30 border border-amber-500/30 rounded-xl overflow-hidden">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 p-4">
              {system_tunnels.map((tunnel) => (
                <div
                  key={tunnel.tunnel_id}
                  className={`relative p-4 rounded-lg border transition-all ${
                    tunnel.health_status === 'healthy'
                      ? 'bg-amber-900/20 border-amber-500/40 hover:border-amber-400/60'
                      : 'bg-red-900/20 border-red-500/40 hover:border-red-400/60 animate-pulse'
                  }`}
                >
                  {/* Keep-Alive indicator */}
                  <div className="absolute top-3 right-3">
                    {tunnel.health_status === 'healthy' ? (
                      <div className="flex items-center gap-1.5" title="Keep-Alive Active">
                        <span className="relative flex h-3 w-3">
                          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                          <span className="relative inline-flex rounded-full h-3 w-3 bg-green-500"></span>
                        </span>
                        <HeartPulse className="w-4 h-4 text-green-400" />
                      </div>
                    ) : (
                      <div className="flex items-center gap-1.5" title="Keep-Alive Failed - Needs Restart">
                        <ShieldAlert className="w-5 h-5 text-red-400 animate-bounce" />
                      </div>
                    )}
                  </div>

                  {/* Node info */}
                  <div className="flex items-start gap-3 mb-3">
                    <div className="p-2 rounded-lg bg-amber-500/20">
                      <Zap className="w-5 h-5 text-amber-400" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="text-white font-semibold truncate">{tunnel.node_name}</h3>
                      <p className="text-xs text-amber-300/70 truncate">{tunnel.name}</p>
                    </div>
                  </div>

                  {/* Tunnel details */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-slate-400">Hub:</span>
                      <span className="text-amber-300 font-mono text-xs">{tunnel.hub_host}:{tunnel.hub_port}</span>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-slate-400">Ports:</span>
                      <span className="text-white font-mono">
                        <span className="text-slate-400">{tunnel.local_port}</span>
                        <span className="mx-1 text-amber-400">→</span>
                        <span className="text-amber-400 font-bold">{tunnel.remote_port}</span>
                      </span>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-slate-400">Last Heartbeat:</span>
                      <span className={`text-xs ${tunnel.health_status === 'healthy' ? 'text-green-400' : 'text-red-400'}`}>
                        {getTimeSinceHeartbeat(tunnel.last_heartbeat) || 'Never'}
                      </span>
                    </div>
                  </div>

                  {/* Status badge */}
                  <div className="mt-3 pt-3 border-t border-amber-500/20">
                    <div className="flex items-center justify-between">
                      <span className={`px-2 py-1 rounded text-xs font-medium ${
                        tunnel.health_status === 'healthy'
                          ? 'bg-green-500/20 text-green-400'
                          : 'bg-red-500/20 text-red-400'
                      }`}>
                        {tunnel.health_status === 'healthy' ? 'HEALTHY' : 'NEEDS RESTART'}
                      </span>
                      <span className="text-xs text-slate-500">
                        Port {tunnel.remote_port}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="bg-gradient-to-br from-amber-950/30 to-orange-950/20 border border-amber-500/30 rounded-xl p-8 text-center">
            <Shield className="w-12 h-12 text-amber-500/50 mx-auto mb-4" />
            <p className="text-amber-300/70">No system tunnels configured</p>
            <p className="text-xs text-slate-500 mt-2">
              System tunnels are created automatically when nodes are added
            </p>
          </div>
        )}
      </div>

      {/* Application Tunnels Table */}
      <div>
        <h2 className="text-xl font-bold mb-4 flex items-center gap-2 text-white">
          <Activity className="w-5 h-5 text-cyan-400" />
          Application Tunnels
          <span className="text-sm font-normal text-slate-400">
            ({tunnels?.length || 0} active)
          </span>
        </h2>

        {tunnels && tunnels.length > 0 ? (
          <div className="bg-slate-800 border border-slate-700 rounded-xl overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="bg-slate-700/50">
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                    Node
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                    Service
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                    Local Port
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                    Remote Port
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                    Connected At
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700">
                {tunnels.map((tunnel) => (
                  <tr key={tunnel.tunnel_id} className="hover:bg-slate-700/30">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-white">{tunnel.node_name}</div>
                      <div className="text-xs text-slate-400 font-mono">{tunnel.node_id.substring(0, 8)}...</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium border ${getTunnelColor(tunnel.application)}`}>
                        {getTunnelIcon(tunnel.application)}
                        {tunnel.application}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="text-sm text-slate-300 font-mono">{tunnel.local_port}</span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="text-sm text-white font-mono font-bold">{tunnel.remote_port}</span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        {tunnel.status === 'active' ? (
                          <>
                            <span className="relative flex h-3 w-3">
                              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                              <span className="relative inline-flex rounded-full h-3 w-3 bg-green-500"></span>
                            </span>
                            <span className="text-sm text-green-400">Active</span>
                          </>
                        ) : (
                          <>
                            <span className="w-3 h-3 rounded-full bg-slate-500"></span>
                            <span className="text-sm text-slate-400">{tunnel.status}</span>
                          </>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="text-xs text-slate-400">
                        {tunnel.connected_at ? new Date(tunnel.connected_at).toLocaleString() : 'N/A'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="bg-slate-800 border border-slate-700 rounded-xl p-8 text-center">
            <Link2Off className="w-12 h-12 text-slate-600 mx-auto mb-4" />
            <p className="text-slate-400">No active tunnels</p>
            <p className="text-xs text-slate-500 mt-2">
              Tunnels are established when edge nodes connect to the hub
            </p>
          </div>
        )}
      </div>

      {/* Tunnels by Node - Card View */}
      <div>
        <h2 className="text-xl font-bold mb-4 flex items-center gap-2 text-white">
          <Server className="w-5 h-5 text-blue-400" />
          Tunnels by Node
        </h2>

        {tunnels && tunnels.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Group tunnels by node */}
            {Object.entries(
              tunnels.reduce((acc, tunnel) => {
                if (!acc[tunnel.node_id]) {
                  acc[tunnel.node_id] = {
                    node_name: tunnel.node_name,
                    node_id: tunnel.node_id,
                    tunnels: []
                  }
                }
                acc[tunnel.node_id].tunnels.push(tunnel)
                return acc
              }, {})
            ).map(([nodeId, nodeData]) => (
              <div
                key={nodeId}
                className="bg-slate-800 border border-slate-700 rounded-xl overflow-hidden hover:border-slate-600 transition-colors"
              >
                {/* Node Header */}
                <div className="h-1 bg-gradient-to-r from-blue-500 to-cyan-500" />
                <div className="p-5">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <h3 className="text-lg font-bold text-white">{nodeData.node_name}</h3>
                      <p className="text-xs text-slate-400 font-mono">{nodeId.substring(0, 12)}...</p>
                    </div>
                    <span className="px-2 py-1 bg-green-500/20 text-green-400 text-xs rounded-full">
                      {nodeData.tunnels.length} tunnel{nodeData.tunnels.length !== 1 ? 's' : ''}
                    </span>
                  </div>

                  {/* Tunnels List */}
                  <div className="space-y-2">
                    {nodeData.tunnels.map((tunnel) => (
                      <div
                        key={tunnel.tunnel_id}
                        className="flex items-center justify-between p-3 bg-slate-700/50 rounded-lg"
                      >
                        <div className="flex items-center gap-3">
                          {getTunnelIcon(tunnel.application)}
                          <div>
                            <span className="text-white font-medium">{tunnel.application}</span>
                            <p className="text-xs text-slate-400">
                              Port {tunnel.local_port} → {tunnel.remote_port}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="relative flex h-2 w-2">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                            <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
                          </span>
                          <span className="text-xs text-green-400">Active</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="bg-slate-800 border border-slate-700 rounded-xl p-8 text-center">
            <Server className="w-12 h-12 text-slate-600 mx-auto mb-4" />
            <p className="text-slate-400">No nodes with active tunnels</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default TunnelsDashboard
