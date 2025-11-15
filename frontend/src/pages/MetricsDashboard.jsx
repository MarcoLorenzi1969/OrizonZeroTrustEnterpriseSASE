import { useEffect, useState } from 'react'
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell
} from 'recharts'
import { Activity, Server, Cpu, HardDrive, Network, AlertTriangle, CheckCircle, TrendingUp } from 'lucide-react'

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899']

export default function MetricsDashboard() {
  const [metricsData, setMetricsData] = useState([])
  const [currentMetrics, setCurrentMetrics] = useState(null)
  const [timeRange, setTimeRange] = useState('5m') // 5m, 15m, 1h, 6h, 24h
  const [selectedNode, setSelectedNode] = useState('central-hub')
  const [nodes, setNodes] = useState([])

  useEffect(() => {
    loadNodes()
    loadMetrics()

    // Refresh every 5 seconds
    const interval = setInterval(loadMetrics, 5000)
    return () => clearInterval(interval)
  }, [selectedNode])

  const loadNodes = async () => {
    try {
      const response = await fetch('/api/v1/metrics/all')
      const data = await response.json()
      setNodes(data || [])
    } catch (error) {
      console.error('Error loading nodes:', error)
    }
  }

  const loadMetrics = async () => {
    try {
      const response = await fetch(`/api/v1/metrics/node/${selectedNode}`)
      const data = await response.json()

      setCurrentMetrics(data)

      // Add to history (keep last 60 points = 5 minutes at 5s interval)
      setMetricsData(prev => {
        const newData = [...prev, {
          timestamp: new Date().toLocaleTimeString(),
          cpu: data.cpu_percent || 0,
          ram: data.ram_percent || 0,
          disk: data.disk_percent || 0,
          network_sent: data.network_sent_mb || 0,
          network_recv: data.network_recv_mb || 0
        }]
        return newData.slice(-60) // Keep last 60 points
      })
    } catch (error) {
      console.error('Error loading metrics:', error)
    }
  }

  const getStatusColor = (value, warningThreshold = 60, dangerThreshold = 80) => {
    if (value >= dangerThreshold) return 'text-red-500'
    if (value >= warningThreshold) return 'text-yellow-500'
    return 'text-green-500'
  }

  const getStatusBg = (value, warningThreshold = 60, dangerThreshold = 80) => {
    if (value >= dangerThreshold) return 'bg-red-500/10 border-red-500'
    if (value >= warningThreshold) return 'bg-yellow-500/10 border-yellow-500'
    return 'bg-green-500/10 border-green-500'
  }

  if (!currentMetrics) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-slate-400">Loading metrics...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <Activity className="w-8 h-8 text-blue-400" />
            System Metrics Dashboard
          </h1>
          <p className="text-slate-400 mt-1">Real-time monitoring and performance analytics</p>
        </div>

        <div className="flex items-center gap-4">
          {/* Node Selector */}
          <select
            value={selectedNode}
            onChange={(e) => setSelectedNode(e.target.value)}
            className="px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
          >
            {nodes.map(node => (
              <option key={node.node_id} value={node.node_id}>
                {node.node_name}
              </option>
            ))}
          </select>

          {/* Time Range Selector */}
          <div className="flex gap-2 bg-slate-800 rounded-lg p-1 border border-slate-700">
            {['5m', '15m', '1h', '6h', '24h'].map(range => (
              <button
                key={range}
                onClick={() => setTimeRange(range)}
                className={`px-3 py-1 rounded text-sm font-medium transition ${
                  timeRange === range
                    ? 'bg-blue-600 text-white'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                {range}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* CPU Card */}
        <div className={`bg-slate-800 border-2 rounded-xl p-6 ${getStatusBg(currentMetrics.cpu_percent)}`}>
          <div className="flex items-center justify-between mb-4">
            <Cpu className={`w-8 h-8 ${getStatusColor(currentMetrics.cpu_percent)}`} />
            <span className={`text-3xl font-bold ${getStatusColor(currentMetrics.cpu_percent)}`}>
              {currentMetrics.cpu_percent.toFixed(1)}%
            </span>
          </div>
          <h3 className="text-slate-400 text-sm font-medium">CPU Usage</h3>
          {currentMetrics.load_average && (
            <p className="text-xs text-slate-500 mt-2">
              Load: {currentMetrics.load_average.map(l => l.toFixed(2)).join(', ')}
            </p>
          )}
        </div>

        {/* RAM Card */}
        <div className={`bg-slate-800 border-2 rounded-xl p-6 ${getStatusBg(currentMetrics.ram_percent)}`}>
          <div className="flex items-center justify-between mb-4">
            <HardDrive className={`w-8 h-8 ${getStatusColor(currentMetrics.ram_percent)}`} />
            <span className={`text-3xl font-bold ${getStatusColor(currentMetrics.ram_percent)}`}>
              {currentMetrics.ram_percent.toFixed(1)}%
            </span>
          </div>
          <h3 className="text-slate-400 text-sm font-medium">RAM Usage</h3>
          <p className="text-xs text-slate-500 mt-2">
            {currentMetrics.ram_used_mb.toFixed(0)} MB / {currentMetrics.ram_total_mb.toFixed(0)} MB
          </p>
        </div>

        {/* Disk Card */}
        <div className={`bg-slate-800 border-2 rounded-xl p-6 ${getStatusBg(currentMetrics.disk_percent, 70, 90)}`}>
          <div className="flex items-center justify-between mb-4">
            <Server className={`w-8 h-8 ${getStatusColor(currentMetrics.disk_percent, 70, 90)}`} />
            <span className={`text-3xl font-bold ${getStatusColor(currentMetrics.disk_percent, 70, 90)}`}>
              {currentMetrics.disk_percent.toFixed(1)}%
            </span>
          </div>
          <h3 className="text-slate-400 text-sm font-medium">Disk Usage</h3>
          <p className="text-xs text-slate-500 mt-2">
            {currentMetrics.disk_used_gb.toFixed(1)} GB / {currentMetrics.disk_total_gb.toFixed(1)} GB
          </p>
        </div>

        {/* Network Card */}
        <div className="bg-slate-800 border-2 border-slate-700 rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <Network className="w-8 h-8 text-blue-400" />
            <div className="text-right">
              <div className="text-sm text-green-400">↑ {currentMetrics.network_sent_mb.toFixed(1)} MB</div>
              <div className="text-sm text-blue-400">↓ {currentMetrics.network_recv_mb.toFixed(1)} MB</div>
            </div>
          </div>
          <h3 className="text-slate-400 text-sm font-medium">Network I/O</h3>
          <p className="text-xs text-slate-500 mt-2">Total traffic since boot</p>
        </div>
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* CPU & RAM Chart */}
        <div className="bg-slate-800 border border-slate-700 rounded-xl p-6">
          <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-blue-400" />
            CPU & RAM Usage Over Time
          </h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={metricsData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="timestamp" stroke="#94a3b8" fontSize={12} />
              <YAxis stroke="#94a3b8" fontSize={12} domain={[0, 100]} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1e293b',
                  border: '1px solid #475569',
                  borderRadius: '8px'
                }}
              />
              <Legend />
              <Line
                type="monotone"
                dataKey="cpu"
                stroke="#3b82f6"
                strokeWidth={2}
                name="CPU %"
                dot={false}
              />
              <Line
                type="monotone"
                dataKey="ram"
                stroke="#10b981"
                strokeWidth={2}
                name="RAM %"
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Disk Usage Chart */}
        <div className="bg-slate-800 border border-slate-700 rounded-xl p-6">
          <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
            <Server className="w-5 h-5 text-purple-400" />
            Storage Distribution
          </h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={[
                  { name: 'Used', value: currentMetrics.disk_used_gb },
                  { name: 'Free', value: currentMetrics.disk_total_gb - currentMetrics.disk_used_gb }
                ]}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                outerRadius={100}
                fill="#8884d8"
                dataKey="value"
              >
                <Cell fill="#ef4444" />
                <Cell fill="#10b981" />
              </Pie>
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1e293b',
                  border: '1px solid #475569',
                  borderRadius: '8px'
                }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Network Traffic Chart */}
        <div className="bg-slate-800 border border-slate-700 rounded-xl p-6 lg:col-span-2">
          <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
            <Network className="w-5 h-5 text-cyan-400" />
            Network Traffic
          </h3>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={metricsData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="timestamp" stroke="#94a3b8" fontSize={12} />
              <YAxis stroke="#94a3b8" fontSize={12} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1e293b',
                  border: '1px solid #475569',
                  borderRadius: '8px'
                }}
              />
              <Legend />
              <Area
                type="monotone"
                dataKey="network_sent"
                stackId="1"
                stroke="#10b981"
                fill="#10b981"
                fillOpacity={0.6}
                name="Sent (MB)"
              />
              <Area
                type="monotone"
                dataKey="network_recv"
                stackId="2"
                stroke="#3b82f6"
                fill="#3b82f6"
                fillOpacity={0.6}
                name="Received (MB)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* System Info */}
      <div className="bg-slate-800 border border-slate-700 rounded-xl p-6">
        <h3 className="text-white font-semibold mb-4">System Information</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <p className="text-slate-400 text-sm">Node ID</p>
            <p className="text-white font-mono text-sm">{currentMetrics.node_id}</p>
          </div>
          <div>
            <p className="text-slate-400 text-sm">Last Updated</p>
            <p className="text-white font-mono text-sm">
              {new Date(currentMetrics.timestamp).toLocaleTimeString()}
            </p>
          </div>
          <div>
            <p className="text-slate-400 text-sm">Total RAM</p>
            <p className="text-white font-mono text-sm">
              {(currentMetrics.ram_total_mb / 1024).toFixed(2)} GB
            </p>
          </div>
          <div>
            <p className="text-slate-400 text-sm">Total Disk</p>
            <p className="text-white font-mono text-sm">
              {currentMetrics.disk_total_gb.toFixed(1)} GB
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
