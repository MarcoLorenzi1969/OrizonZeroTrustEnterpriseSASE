import { useEffect, useState } from 'react'
import { Server, Users, Activity, TrendingUp, Box, Play, Square } from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import api from '../services/api'
import wsService from '../services/websocket'

function StatCard({ title, value, icon: Icon, change, color }) {
  return (
    <div className="bg-slate-800 border border-slate-700 rounded-xl p-6 hover:border-slate-600 transition-colors">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-slate-400 text-sm font-medium">{title}</h3>
        <div className={`w-10 h-10 ${color} rounded-lg flex items-center justify-center`}>
          <Icon className="w-6 h-6 text-white" />
        </div>
      </div>
      
      <div className="flex items-end justify-between">
        <div>
          <p className="text-3xl font-bold text-white mb-1">{value}</p>
          {change && (
            <p className={`text-sm ${change >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {change >= 0 ? '↑' : '↓'} {Math.abs(change)}% from last week
            </p>
          )}
        </div>
      </div>
    </div>
  )
}

function DashboardPage() {
  const [stats, setStats] = useState({
    totalNodes: 0,
    activeNodes: 0,
    totalUsers: 0,
    activeTunnels: 0,
  })

  const [networkData, setNetworkData] = useState([])
  const [containers, setContainers] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadDashboardData()

    // TODO: Enable WebSocket when backend is ready
    // wsService.connect()
    // wsService.on('node_status', handleNodeUpdate)

    return () => {
      // wsService.off('node_status', handleNodeUpdate)
    }
  }, [])

  const loadDashboardData = async () => {
    try {
      // Load data with Promise.allSettled to handle partial failures
      const [dashboardRes, nodesRes, usersRes, containersRes] = await Promise.allSettled([
        api.get('/dashboard/stats').catch(err => {
          console.warn('[Dashboard] /dashboard/stats not available:', err.message)
          return { data: { active_tunnels: 0 } }
        }),
        api.get('/nodes').catch(err => {
          console.warn('[Dashboard] /nodes not available:', err.message)
          return { data: { total: 0, items: [] } }
        }),
        api.get('/users').catch(err => {
          console.warn('[Dashboard] /users not available:', err.message)
          return { data: { total: 0 } }
        }),
        api.get('/containers').catch(err => {
          console.warn('[Dashboard] /containers not available:', err.message)
          return { data: { items: [], docker_available: false } }
        }),
      ])

      // Extract data from settled promises
      const dashboardData = dashboardRes.status === 'fulfilled' ? dashboardRes.value.data : { active_tunnels: 0 }
      const nodesData = nodesRes.status === 'fulfilled' ? nodesRes.value.data : { total: 0, items: [] }
      const usersData = usersRes.status === 'fulfilled' ? usersRes.value.data : { total: 0 }
      const containersData = containersRes.status === 'fulfilled' ? containersRes.value.data : { items: [], docker_available: false }

      setStats({
        totalNodes: nodesData.total || 0,
        activeNodes: nodesData.items?.filter(n => n.status === 'online').length || 0,
        totalUsers: usersData.total || 0,
        activeTunnels: dashboardData.active_tunnels || 0,
      })

      setContainers(containersData.items || [])

      // Mock network data for chart
      setNetworkData([
        { time: '00:00', bandwidth: 45 },
        { time: '04:00', bandwidth: 32 },
        { time: '08:00', bandwidth: 67 },
        { time: '12:00', bandwidth: 89 },
        { time: '16:00', bandwidth: 95 },
        { time: '20:00', bandwidth: 78 },
        { time: '24:00', bandwidth: 56 },
      ])

      setLoading(false)
    } catch (error) {
      console.error('[Dashboard] Error loading dashboard data:', error)
      // Even on error, show the dashboard with zero stats
      setStats({
        totalNodes: 0,
        activeNodes: 0,
        totalUsers: 0,
        activeTunnels: 0,
      })
      setLoading(false)
    }
  }

  const handleNodeUpdate = (data) => {
    console.log('Node update received:', data)
    // Update stats in real-time
    loadDashboardData()
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white mb-2">Dashboard Overview</h1>
        <p className="text-slate-400">Monitor your zero trust network in real-time</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Total Nodes"
          value={stats.totalNodes}
          icon={Server}
          change={12}
          color="bg-gradient-to-br from-blue-500 to-blue-600"
        />
        <StatCard
          title="Active Nodes"
          value={stats.activeNodes}
          icon={Activity}
          change={8}
          color="bg-gradient-to-br from-green-500 to-green-600"
        />
        <StatCard
          title="Total Users"
          value={stats.totalUsers}
          icon={Users}
          change={5}
          color="bg-gradient-to-br from-purple-500 to-purple-600"
        />
        <StatCard
          title="Active Tunnels"
          value={stats.activeTunnels}
          icon={TrendingUp}
          change={-3}
          color="bg-gradient-to-br from-orange-500 to-orange-600"
        />
      </div>

      {/* Docker Containers */}
      {containers.length > 0 && (
        <div className="bg-slate-800 border border-slate-700 rounded-xl p-6">
          <div className="flex items-center gap-2 mb-4">
            <Box className="w-5 h-5 text-blue-400" />
            <h2 className="text-xl font-semibold text-white">Hub Server Containers</h2>
            <span className="ml-auto text-sm text-slate-400">{containers.length} container{containers.length !== 1 ? 's' : ''}</span>
          </div>
          <div className="space-y-3">
            {containers.map((container) => (
              <div key={container.id} className="flex items-center gap-4 p-4 bg-slate-700/50 rounded-lg">
                <div className={`w-10 h-10 ${container.status === 'running' ? 'bg-green-500/20' : 'bg-gray-500/20'} rounded-lg flex items-center justify-center`}>
                  {container.status === 'running' ? (
                    <Play className="w-5 h-5 text-green-400" />
                  ) : (
                    <Square className="w-5 h-5 text-gray-400" />
                  )}
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <p className="text-white font-medium">{container.name}</p>
                    <span className={`px-2 py-0.5 text-xs rounded-full ${
                      container.status === 'running'
                        ? 'bg-green-500/20 text-green-400'
                        : 'bg-gray-500/20 text-gray-400'
                    }`}>
                      {container.status}
                    </span>
                  </div>
                  <p className="text-sm text-slate-400">{container.image}</p>
                  {container.ports && (
                    <p className="text-xs text-slate-500 mt-1">Ports: {container.ports || 'none'}</p>
                  )}
                </div>
                <div className="text-right">
                  <p className="text-xs text-slate-400">{container.raw_status}</p>
                  <p className="text-xs text-slate-500 mt-1">{new Date(container.created_at).toLocaleDateString()}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Network Traffic Chart */}
      <div className="bg-slate-800 border border-slate-700 rounded-xl p-6">
        <h2 className="text-xl font-semibold text-white mb-6">Network Bandwidth (Mbps)</h2>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={networkData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="time" stroke="#94a3b8" />
            <YAxis stroke="#94a3b8" />
            <Tooltip
              contentStyle={{
                backgroundColor: '#1e293b',
                border: '1px solid #334155',
                borderRadius: '8px',
                color: '#fff',
              }}
            />
            <Line
              type="monotone"
              dataKey="bandwidth"
              stroke="#3b82f6"
              strokeWidth={2}
              dot={{ fill: '#3b82f6', r: 4 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Recent Activity */}
      <div className="bg-slate-800 border border-slate-700 rounded-xl p-6">
        <h2 className="text-xl font-semibold text-white mb-4">Recent Activity</h2>
        <div className="space-y-3">
          <ActivityItem
            type="info"
            message="Node 'web-server-01' connected successfully"
            time="2 minutes ago"
          />
          <ActivityItem
            type="success"
            message="New SSH tunnel established to 'db-server-03'"
            time="15 minutes ago"
          />
          <ActivityItem
            type="warning"
            message="Node 'app-server-02' experiencing high latency"
            time="1 hour ago"
          />
          <ActivityItem
            type="info"
            message="User 'john@example.com' logged in"
            time="2 hours ago"
          />
        </div>
      </div>
    </div>
  )
}

function ActivityItem({ type, message, time }) {
  const colors = {
    info: 'bg-blue-500',
    success: 'bg-green-500',
    warning: 'bg-yellow-500',
    error: 'bg-red-500',
  }

  return (
    <div className="flex items-start gap-4 p-4 bg-slate-700/50 rounded-lg">
      <div className={`w-2 h-2 rounded-full ${colors[type]} mt-2`}></div>
      <div className="flex-1">
        <p className="text-white">{message}</p>
        <p className="text-sm text-slate-400 mt-1">{time}</p>
      </div>
    </div>
  )
}

export default DashboardPage
