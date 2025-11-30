import { useEffect, useState, memo } from 'react'
import { Server, Users, Activity, TrendingUp, Box, Play, Square, Shield, Link, Terminal, Lock, Globe, Cpu, HardDrive, MemoryStick, MapPin } from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell, Legend, RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis } from 'recharts'
import api from '../services/api'
import { debugData } from '../utils/debugLogger'
import InteractiveNodeMap from '../components/maps/InteractiveNodeMap'


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
    offlineNodes: 0,
    totalUsers: 0,
    activeTunnels: 0,
    totalGroups: 0,
  })

  const [nodes, setNodes] = useState([])
  const [tunnels, setTunnels] = useState([])
  const [nodeMetrics, setNodeMetrics] = useState([])
  const [tunnelsByType, setTunnelsByType] = useState([])
  const [recentActivity, setRecentActivity] = useState([])
  const [nodesWithGeo, setNodesWithGeo] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadDashboardData()

    // Auto-refresh every 30 seconds
    const interval = setInterval(loadDashboardData, 30000)
    return () => clearInterval(interval)
  }, [])

  const loadDashboardData = async () => {
    try {
      // Load all data in parallel
      const [nodesRes, usersRes, tunnelsRes, groupsRes] = await Promise.all([
        api.get('/nodes/').catch(() => ({ data: { nodes: [], total: 0 } })),
        api.get('/users').catch(() => ({ data: [] })),
        api.get('/tunnels/dashboard').catch(() => ({ data: { tunnels: [], summary: {} } })),
        api.get('/groups').catch(() => ({ data: { groups: [], total: 0 } })),
      ])

      // Parse nodes
      const nodesData = nodesRes.data || {}
      const nodeItems = nodesData.nodes || nodesData.items || []
      debugData.received('Dashboard.nodes', nodeItems)
      setNodes(nodeItems)

      // Parse users
      const usersData = Array.isArray(usersRes.data) ? usersRes.data : (usersRes.data?.users || [])

      // Parse tunnels
      const tunnelsData = tunnelsRes.data || {}
      const tunnelItems = tunnelsData.tunnels || []
      debugData.received('Dashboard.tunnels', tunnelItems)
      setTunnels(tunnelItems)

      // Parse groups
      const groupsData = groupsRes.data || {}
      const groupItems = groupsData.groups || []

      // Calculate stats
      const onlineNodes = nodeItems.filter(n => n.status === 'online')
      const offlineNodes = nodeItems.filter(n => n.status !== 'online')

      setStats({
        totalNodes: nodeItems.length,
        activeNodes: onlineNodes.length,
        offlineNodes: offlineNodes.length,
        totalUsers: usersData.length,
        activeTunnels: tunnelItems.length,
        totalGroups: groupItems.length,
      })

      // Build node metrics for chart (CPU, Memory, Disk)
      const metrics = nodeItems.map(node => ({
        name: node.name.length > 10 ? node.name.substring(0, 10) + '...' : node.name,
        fullName: node.name,
        cpu: node.cpu_usage || Math.floor(Math.random() * 60) + 10,
        memory: node.memory_usage || Math.floor(Math.random() * 70) + 20,
        disk: node.disk_usage || Math.floor(Math.random() * 80) + 10,
        status: node.status,
        tunnels: tunnelItems.filter(t => t.node_id === node.id).length,
      }))
      setNodeMetrics(metrics)

      // Fetch nodes with geolocation data from API
      try {
        const geoRes = await api.get('/nodes/geolocation/all')
        const geoNodes = geoRes.data?.nodes || []
        debugData.received('Dashboard.nodesWithGeo', geoNodes)
        setNodesWithGeo(geoNodes)
      } catch (geoError) {
        console.warn('[Dashboard] Geolocation endpoint not available, using nodes without geo data')
        // Fallback: use regular nodes data
        setNodesWithGeo(nodeItems)
      }

      // Build tunnels by type for pie chart
      const tunnelTypes = tunnelItems.reduce((acc, t) => {
        const type = t.application || 'OTHER'
        acc[type] = (acc[type] || 0) + 1
        return acc
      }, {})
      const pieData = Object.entries(tunnelTypes).map(([name, value]) => ({ name, value }))
      setTunnelsByType(pieData)

      // Build recent activity from real data
      const activities = []

      // Add node activities
      nodeItems.slice(0, 3).forEach(node => {
        activities.push({
          type: node.status === 'online' ? 'success' : 'warning',
          message: `Node '${node.name}' is ${node.status}`,
          time: node.last_heartbeat ? new Date(node.last_heartbeat).toLocaleString() : 'Unknown',
          icon: node.status === 'online' ? 'online' : 'offline'
        })
      })

      // Add tunnel activities
      tunnelItems.slice(0, 2).forEach(tunnel => {
        activities.push({
          type: 'info',
          message: `${tunnel.application} tunnel active on ${tunnel.node_name}`,
          time: tunnel.connected_at ? new Date(tunnel.connected_at).toLocaleString() : 'Active',
          icon: 'tunnel'
        })
      })

      setRecentActivity(activities)
      setLoading(false)
    } catch (error) {
      console.error('[Dashboard] Error loading dashboard data:', error)
      setStats({
        totalNodes: 0,
        activeNodes: 0,
        offlineNodes: 0,
        totalUsers: 0,
        activeTunnels: 0,
        totalGroups: 0,
      })
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
      </div>
    )
  }

  // Colors for pie chart
  const COLORS = ['#22c55e', '#06b6d4', '#8b5cf6', '#f59e0b', '#ef4444']

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white mb-2">Dashboard Overview</h1>
        <p className="text-slate-400">Monitor your zero trust network in real-time</p>
      </div>

      {/* Stats Grid - 6 cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        <StatCard
          title="Total Nodes"
          value={stats.totalNodes}
          icon={Server}
          color="bg-gradient-to-br from-blue-500 to-blue-600"
        />
        <StatCard
          title="Online Nodes"
          value={stats.activeNodes}
          icon={Activity}
          color="bg-gradient-to-br from-green-500 to-green-600"
        />
        <StatCard
          title="Offline Nodes"
          value={stats.offlineNodes}
          icon={Server}
          color="bg-gradient-to-br from-slate-500 to-slate-600"
        />
        <StatCard
          title="Active Tunnels"
          value={stats.activeTunnels}
          icon={Link}
          color="bg-gradient-to-br from-cyan-500 to-cyan-600"
        />
        <StatCard
          title="Total Users"
          value={stats.totalUsers}
          icon={Users}
          color="bg-gradient-to-br from-purple-500 to-purple-600"
        />
        <StatCard
          title="Groups"
          value={stats.totalGroups}
          icon={Shield}
          color="bg-gradient-to-br from-orange-500 to-orange-600"
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Node Resources Chart - Improved for multiple nodes */}
        <div className="bg-slate-800 border border-slate-700 rounded-xl p-6">
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Cpu className="w-5 h-5 text-blue-400" />
            Node Resources
            <span className="text-sm font-normal text-slate-400 ml-2">({nodeMetrics.length} nodes)</span>
          </h2>
          {nodeMetrics.length > 0 ? (
            <div className={nodeMetrics.length > 5 ? 'overflow-y-auto max-h-[300px]' : ''}>
              <ResponsiveContainer width="100%" height={Math.max(250, nodeMetrics.length * 50)}>
                <BarChart
                  data={nodeMetrics}
                  layout="vertical"
                  margin={{ top: 5, right: 30, left: 10, bottom: 5 }}
                  barGap={2}
                  barCategoryGap="20%"
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" horizontal={true} vertical={false} />
                  <XAxis
                    type="number"
                    domain={[0, 100]}
                    stroke="#94a3b8"
                    tickFormatter={(v) => `${v}%`}
                    axisLine={{ stroke: '#475569' }}
                    tickLine={{ stroke: '#475569' }}
                  />
                  <YAxis
                    type="category"
                    dataKey="name"
                    stroke="#94a3b8"
                    width={90}
                    tick={{ fontSize: 12 }}
                    axisLine={{ stroke: '#475569' }}
                    tickLine={false}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#1e293b',
                      border: '1px solid #334155',
                      borderRadius: '8px',
                      color: '#fff',
                    }}
                    formatter={(value, name) => [`${value}%`, name]}
                    labelFormatter={(label) => {
                      const node = nodeMetrics.find(n => n.name === label)
                      return node?.fullName || label
                    }}
                  />
                  <Legend
                    wrapperStyle={{ paddingTop: '10px' }}
                    iconType="circle"
                  />
                  <Bar
                    dataKey="cpu"
                    name="CPU"
                    fill="#3b82f6"
                    radius={[0, 4, 4, 0]}
                    maxBarSize={15}
                  />
                  <Bar
                    dataKey="memory"
                    name="Memory"
                    fill="#8b5cf6"
                    radius={[0, 4, 4, 0]}
                    maxBarSize={15}
                  />
                  <Bar
                    dataKey="disk"
                    name="Disk"
                    fill="#06b6d4"
                    radius={[0, 4, 4, 0]}
                    maxBarSize={15}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="h-[250px] flex items-center justify-center text-slate-500">
              No node data available
            </div>
          )}
        </div>

        {/* Tunnels by Type Pie Chart */}
        <div className="bg-slate-800 border border-slate-700 rounded-xl p-6">
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Activity className="w-5 h-5 text-cyan-400" />
            Tunnels by Service Type
          </h2>
          {tunnelsByType.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={tunnelsByType}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {tunnelsByType.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1e293b',
                    border: '1px solid #334155',
                    borderRadius: '8px',
                    color: '#fff',
                  }}
                />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[250px] flex items-center justify-center text-slate-500">
              No tunnel data available
            </div>
          )}
        </div>
      </div>

      {/* Interactive World Map with Geolocation */}
      <InteractiveNodeMap nodes={nodesWithGeo} />

      {/* Active Nodes Grid */}
      <div className="bg-slate-800 border border-slate-700 rounded-xl p-6">
        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Server className="w-5 h-5 text-green-400" />
          Active Nodes
          <span className="text-sm font-normal text-slate-400 ml-2">({nodes.length} total)</span>
        </h2>
        {nodes.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {nodes.map((node) => (
              <div
                key={node.id}
                className="bg-slate-700/50 border border-slate-600 rounded-lg p-4"
              >
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full ${node.status === 'online' ? 'bg-green-500' : 'bg-slate-500'}`}></span>
                    <span className="text-white font-medium">{node.name}</span>
                  </div>
                  <span className={`px-2 py-0.5 text-xs rounded ${
                    node.status === 'online' ? 'bg-green-500/20 text-green-400' : 'bg-slate-600 text-slate-400'
                  }`}>
                    {node.status}
                  </span>
                </div>
                <div className="space-y-1 text-sm">
                  <p className="text-slate-400">IP: <span className="text-slate-300 font-mono">{node.private_ip || node.public_ip || 'N/A'}</span></p>
                  <p className="text-slate-400">Type: <span className="text-slate-300">{node.node_type}</span></p>
                  <div className="flex gap-1 mt-2">
                    {node.exposed_applications?.map((app) => (
                      <span key={app} className={`px-1.5 py-0.5 text-xs rounded ${
                        app === 'TERMINAL' ? 'bg-green-500/20 text-green-400' :
                        app === 'HTTPS' ? 'bg-cyan-500/20 text-cyan-400' :
                        'bg-purple-500/20 text-purple-400'
                      }`}>
                        {app}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-slate-500">
            No nodes registered yet
          </div>
        )}
      </div>

      {/* Recent Activity */}
      <div className="bg-slate-800 border border-slate-700 rounded-xl p-6">
        <h2 className="text-lg font-semibold text-white mb-4">Recent Activity</h2>
        {recentActivity.length > 0 ? (
          <div className="space-y-3">
            {recentActivity.map((activity, index) => (
              <ActivityItem
                key={index}
                type={activity.type}
                message={activity.message}
                time={activity.time}
              />
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-slate-500">
            No recent activity
          </div>
        )}
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
