import { useEffect, useState, useCallback } from 'react'
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  addEdge,
  MarkerType,
  Panel,
  BaseEdge,
  EdgeLabelRenderer,
  getBezierPath
} from 'reactflow'
import 'reactflow/dist/style.css'
import { Server, Activity, Wifi, Shield, Lock, ArrowRight, X, Terminal as TerminalIcon, Cpu, HardDrive } from 'lucide-react'
import apiService from '../services/apiService'
import WebTerminal from '../components/WebTerminal'

// Custom Node Component
function CustomNode({ data }) {
  const statusColor = data.status === 'online' ? 'border-green-500 bg-green-500/10' : 'border-red-500 bg-red-500/10'
  const statusDot = data.status === 'online' ? 'bg-green-500' : 'bg-red-500'
  const isHub = data.isHub

  return (
    <div
      className={`px-6 py-4 shadow-xl rounded-lg border-2 bg-slate-800 ${statusColor} min-w-[200px] ${
        !isHub && data.status === 'online' ? 'cursor-pointer hover:border-blue-400 transition-all' : ''
      }`}
      onClick={() => !isHub && data.status === 'online' && data.onNodeClick && data.onNodeClick(data.nodeId, data.label)}
    >
      <div className="flex items-center gap-3 mb-2">
        <div className={`w-10 h-10 rounded-lg ${data.status === 'online' ? 'bg-green-500/20' : 'bg-red-500/20'} flex items-center justify-center`}>
          <Server className={`w-5 h-5 ${data.status === 'online' ? 'text-green-400' : 'text-red-400'}`} />
        </div>
        <div className="flex-1">
          <div className="font-semibold text-white text-sm">{data.label}</div>
          <div className="text-xs text-slate-400">{data.ip_address}</div>
        </div>
        <div className={`w-2 h-2 rounded-full ${statusDot} animate-pulse`}></div>
      </div>

      {/* Metrics Section */}
      {data.metrics && (
        <div className="mt-3 pt-3 border-t border-slate-700 space-y-2">
          <div className="flex items-center justify-between text-xs">
            <div className="flex items-center gap-2 text-slate-400">
              <Cpu className="w-3 h-3" />
              <span>CPU</span>
            </div>
            <span className={`font-semibold ${
              data.metrics.cpu > 80 ? 'text-red-400' : data.metrics.cpu > 60 ? 'text-yellow-400' : 'text-green-400'
            }`}>
              {data.metrics.cpu}%
            </span>
          </div>
          <div className="flex items-center justify-between text-xs">
            <div className="flex items-center gap-2 text-slate-400">
              <HardDrive className="w-3 h-3" />
              <span>RAM</span>
            </div>
            <span className={`font-semibold ${
              data.metrics.ram > 80 ? 'text-red-400' : data.metrics.ram > 60 ? 'text-yellow-400' : 'text-green-400'
            }`}>
              {data.metrics.ram}%
            </span>
          </div>
        </div>
      )}

      {data.tunnelCount > 0 && (
        <div className="mt-3 pt-3 border-t border-slate-700">
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <Wifi className="w-3 h-3" />
            <span>{data.tunnelCount} active tunnel{data.tunnelCount !== 1 ? 's' : ''}</span>
          </div>
        </div>
      )}

      {/* SSH Access Button */}
      {!isHub && data.status === 'online' && (
        <div className="mt-3 pt-3 border-t border-slate-700">
          <button
            onClick={(e) => {
              e.stopPropagation()
              data.onNodeClick && data.onNodeClick(data.nodeId, data.label)
            }}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium rounded transition"
          >
            <TerminalIcon className="w-3 h-3" />
            <span>SSH Access</span>
          </button>
        </div>
      )}
    </div>
  )
}

// Custom Edge Component with detailed labels
function CustomConnectionEdge({ id, sourceX, sourceY, targetX, targetY, data, style }) {
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
  })

  return (
    <>
      <BaseEdge id={id} path={edgePath} style={style} />
      <EdgeLabelRenderer>
        <div
          style={{
            position: 'absolute',
            transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
            pointerEvents: 'all',
          }}
          className="nodrag nopan"
        >
          <div className="bg-slate-800/95 backdrop-blur-sm border border-slate-700 rounded-lg px-3 py-2 shadow-xl">
            <div className="flex items-center gap-2 text-xs">
              <span className="font-semibold" style={{ color: data.color }}>{data.protocol}</span>
              <span className="text-slate-400">→</span>
            </div>
            <div className="flex items-center gap-2 mt-1 text-xs text-slate-400">
              <span className="font-mono">{data.sourceNode}</span>
              <span>:{data.localPort}</span>
              <ArrowRight className="w-3 h-3" />
              <span>Hub:{data.remotePort}</span>
            </div>
            {data.bandwidth && (
              <div className="text-xs text-slate-500 mt-1">
                {data.bandwidth} Mbps
              </div>
            )}
          </div>
        </div>
      </EdgeLabelRenderer>
    </>
  )
}

const nodeTypes = {
  custom: CustomNode,
}

const edgeTypes = {
  custom: CustomConnectionEdge,
}

function NetworkDiagramPage() {
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])
  const [loading, setLoading] = useState(true)
  const [selectedEdge, setSelectedEdge] = useState(null)
  const [selectedNode, setSelectedNode] = useState(null)
  const [stats, setStats] = useState({
    totalNodes: 0,
    totalTunnels: 0,
    activeTunnels: 0,
    peerConnections: 0,
    ssh: 0,
    https: 0,
    other: 0
  })

  const handleNodeClick = useCallback((nodeId, nodeName) => {
    setSelectedNode({ id: nodeId, name: nodeName })
  }, [])

  const handleCloseTerminal = useCallback(() => {
    setSelectedNode(null)
  }, [])

  useEffect(() => {
    loadNetworkData()

    // Refresh every 10 seconds
    const interval = setInterval(loadNetworkData, 10000)
    return () => clearInterval(interval)
  }, [])

  const loadNetworkData = async () => {
    try {
      // Load nodes, tunnels, and metrics in parallel
      const [nodesResponse, tunnelsResponse, metricsResponse] = await Promise.all([
        apiService.getNodes(),
        apiService.getTunnels(),
        fetch('/api/v1/metrics/all').then(res => res.json()).catch(() => [])
      ])

      const nodesData = nodesResponse || []
      const tunnelsData = tunnelsResponse || []

      // Create a map of node metrics by node_id
      const metricsMap = {}
      if (metricsResponse && Array.isArray(metricsResponse)) {
        metricsResponse.forEach(item => {
          if (item.metrics) {
            metricsMap[item.node_id] = {
              cpu: Math.round(item.metrics.cpu_percent || 0),
              ram: Math.round(item.metrics.ram_percent || 0),
              disk: Math.round(item.metrics.disk_percent || 0),
              network: item.metrics.network_sent_mb || 0
            }
          }
        })
      }

      // Count tunnels per node
      const tunnelCountByNode = {}
      tunnelsData.forEach(tunnel => {
        tunnelCountByNode[tunnel.node_id] = (tunnelCountByNode[tunnel.node_id] || 0) + 1
      })

      // Calculate stats
      const sshCount = tunnelsData.filter(t => t.tunnel_type === 'ssh').length
      const httpsCount = tunnelsData.filter(t => t.tunnel_type === 'https').length
      const otherCount = tunnelsData.filter(t => !['ssh', 'https'].includes(t.tunnel_type)).length
      const activeCount = tunnelsData.filter(t => t.status === 'connected').length

      // Calculate peer connections (n * (n-1) / 2 for full mesh)
      const activeNodeCount = nodesData.filter(n => n.status === 'online').length
      const peerConnectionsCount = activeNodeCount > 1 ? (activeNodeCount * (activeNodeCount - 1)) / 2 : 0

      setStats({
        totalNodes: nodesData.length,
        totalTunnels: tunnelsData.length,
        activeTunnels: activeCount,
        peerConnections: peerConnectionsCount,
        ssh: sshCount,
        https: httpsCount,
        other: otherCount
      })

      // Add a central hub node first
      const flowNodes = [{
        id: 'central-hub',
        type: 'custom',
        position: { x: 0, y: 0 },
        data: {
          label: 'Orizon ZTC Hub',
          status: 'online',
          ip_address: '46.101.189.126',
          tunnelCount: tunnelsData.length,
          metrics: metricsMap['central-hub'] || null,
          isHub: true,
          onNodeClick: handleNodeClick
        },
      }]

      // Create nodes for React Flow positioned around the hub
      nodesData.forEach((node, index) => {
        const angle = (index / nodesData.length) * 2 * Math.PI
        const radius = 400
        const x = Math.cos(angle) * radius
        const y = Math.sin(angle) * radius

        // Get real metrics from backend
        const metrics = metricsMap[node.id] || null

        flowNodes.push({
          id: node.id,
          type: 'custom',
          position: { x, y },
          data: {
            nodeId: node.id,
            label: node.name,
            status: node.status,
            ip_address: node.ip_address,
            tunnelCount: tunnelCountByNode[node.id] || 0,
            metrics: metrics,
            isHub: false,
            onNodeClick: handleNodeClick
          },
        })
      })

      // Create edges (connections) from tunnels to hub
      const flowEdges = []

      tunnelsData.forEach((tunnel) => {
        // Determine color based on tunnel type
        let color, label
        switch (tunnel.tunnel_type) {
          case 'ssh':
            color = '#3b82f6' // blue
            label = 'SSH'
            break
          case 'https':
            color = '#10b981' // green
            label = 'HTTPS'
            break
          case 'http':
            color = '#f59e0b' // amber
            label = 'HTTP'
            break
          case 'vpn':
            color = '#8b5cf6' // purple
            label = 'VPN'
            break
          case 'rdp':
            color = '#ec4899' // pink
            label = 'RDP'
            break
          default:
            color = '#6b7280' // gray
            label = tunnel.tunnel_type?.toUpperCase() || 'UNKNOWN'
        }

        // Connection from node to hub
        flowEdges.push({
          id: tunnel.tunnel_id,
          source: tunnel.node_id,
          target: 'central-hub',
          type: 'custom',
          animated: tunnel.status === 'connected',
          style: {
            stroke: color,
            strokeWidth: tunnel.status === 'connected' ? 3 : 1,
            opacity: tunnel.status === 'connected' ? 1 : 0.3
          },
          data: {
            protocol: label,
            sourceNode: tunnel.node_name,
            localPort: tunnel.local_port,
            remotePort: tunnel.remote_port,
            bandwidth: tunnel.bandwidth_mbps?.toFixed(1),
            color: color,
            tunnelId: tunnel.tunnel_id,
            status: tunnel.status
          },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: color,
            width: 20,
            height: 20
          }
        })
      })

      // Create peer-to-peer connections between nodes (mesh topology)
      // Connect ALL nodes that are online
      const activeNodes = nodesData.filter(n => n.status === 'online')

      console.log('Creating peer connections for', activeNodes.length, 'active nodes')

      for (let i = 0; i < activeNodes.length; i++) {
        for (let j = i + 1; j < activeNodes.length; j++) {
          const node1 = activeNodes[i]
          const node2 = activeNodes[j]

          console.log(`Creating peer link: ${node1.id} <-> ${node2.id}`)

          // Create a peer connection with higher visibility
          flowEdges.push({
            id: `peer-${node1.id}-${node2.id}`,
            source: node1.id,
            target: node2.id,
            type: 'straight', // Use straight line for better visibility
            animated: false,
            style: {
              stroke: '#64748b',
              strokeWidth: 2,
              strokeDasharray: '5,5',
              opacity: 0.6
            }
          })
        }
      }

      console.log('Total edges created:', flowEdges.length)

      setNodes(flowNodes)
      setEdges(flowEdges)
      setLoading(false)
    } catch (error) {
      console.error('Error loading network data:', error)
      setLoading(false)
    }
  }

  const onConnect = useCallback(
    (params) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  )

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-120px)]">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-slate-400">Loading network diagram...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="h-[calc(100vh-120px)] relative">
      {/* Terminal Modal */}
      {selectedNode && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="w-full max-w-6xl h-[80vh]">
            <WebTerminal
              nodeId={selectedNode.id}
              nodeName={selectedNode.name}
              onClose={handleCloseTerminal}
            />
          </div>
        </div>
      )}

      <div className="absolute inset-0 bg-slate-900 rounded-xl overflow-hidden border border-slate-700">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          nodeTypes={nodeTypes}
          edgeTypes={edgeTypes}
          fitView
          attributionPosition="bottom-right"
          className="bg-slate-900"
        >
          <Background color="#334155" gap={16} />
          <Controls className="bg-slate-800 border border-slate-700" />
          <MiniMap
            className="bg-slate-800 border border-slate-700"
            nodeColor={(node) => {
              if (node.data.status === 'online') return '#10b981'
              return '#ef4444'
            }}
          />

          {/* Stats Panel */}
          <Panel position="top-left" className="bg-slate-800/95 backdrop-blur-sm border border-slate-700 rounded-lg p-4 m-4">
            <div className="flex items-center gap-2 mb-4">
              <Activity className="w-5 h-5 text-blue-400" />
              <h3 className="text-white font-semibold">Network Overview</h3>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <p className="text-xs text-slate-400">Total Nodes</p>
                <p className="text-xl font-bold text-white">{stats.totalNodes}</p>
              </div>
              <div>
                <p className="text-xs text-slate-400">Hub Tunnels</p>
                <p className="text-xl font-bold text-green-400">{stats.activeTunnels}/{stats.totalTunnels}</p>
              </div>
              <div>
                <p className="text-xs text-slate-400">Peer Links</p>
                <p className="text-xl font-bold text-slate-400">{stats.peerConnections}</p>
              </div>
              <div>
                <p className="text-xs text-slate-400">Total Links</p>
                <p className="text-xl font-bold text-blue-400">{stats.activeTunnels + stats.peerConnections}</p>
              </div>
            </div>
          </Panel>

          {/* Legend Panel */}
          <Panel position="top-right" className="bg-slate-800/95 backdrop-blur-sm border border-slate-700 rounded-lg p-4 m-4">
            <div className="flex items-center gap-2 mb-4">
              <Shield className="w-5 h-5 text-blue-400" />
              <h3 className="text-white font-semibold">Connection Types</h3>
            </div>

            <div className="space-y-2">
              <div className="flex items-center gap-3">
                <div className="w-12 h-1 bg-blue-500 rounded"></div>
                <span className="text-sm text-slate-300">SSH</span>
                <span className="text-xs text-slate-400">({stats.ssh})</span>
              </div>
              <div className="flex items-center gap-3">
                <div className="w-12 h-1 bg-green-500 rounded"></div>
                <span className="text-sm text-slate-300">HTTPS</span>
                <span className="text-xs text-slate-400">({stats.https})</span>
              </div>
              <div className="flex items-center gap-3">
                <div className="w-12 h-1 bg-amber-500 rounded"></div>
                <span className="text-sm text-slate-300">HTTP</span>
                <span className="text-xs text-slate-400">(0)</span>
              </div>
              <div className="flex items-center gap-3">
                <div className="w-12 h-1 bg-purple-500 rounded"></div>
                <span className="text-sm text-slate-300">VPN</span>
                <span className="text-xs text-slate-400">(0)</span>
              </div>
              {stats.other > 0 && (
                <div className="flex items-center gap-3">
                  <div className="w-12 h-1 bg-gray-500 rounded"></div>
                  <span className="text-sm text-slate-300">Other</span>
                  <span className="text-xs text-slate-400">({stats.other})</span>
                </div>
              )}
            </div>

            <div className="mt-4 pt-4 border-t border-slate-700 space-y-2">
              <div className="text-xs font-semibold text-slate-300 mb-2">Node Status:</div>
              <div className="flex items-center gap-3 mb-2">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                <span className="text-xs text-slate-400">Online Node</span>
              </div>
              <div className="flex items-center gap-3 mb-3">
                <div className="w-2 h-2 bg-red-500 rounded-full"></div>
                <span className="text-xs text-slate-400">Offline Node</span>
              </div>

              <div className="text-xs font-semibold text-slate-300 mb-2">Connections:</div>
              <div className="flex items-center gap-3 mb-2">
                <div className="w-12 h-0.5 bg-blue-500"></div>
                <span className="text-xs text-slate-400">Tunnel to Hub</span>
              </div>
              <div className="flex items-center gap-3">
                <div className="w-12 h-0.5 bg-slate-500" style={{ borderTop: '1px dashed #64748b' }}></div>
                <span className="text-xs text-slate-400">Peer Link</span>
              </div>
            </div>
          </Panel>

          {/* Instructions */}
          <Panel position="bottom-left" className="bg-slate-800/95 backdrop-blur-sm border border-slate-700 rounded-lg p-3 m-4">
            <div className="text-xs text-slate-400 space-y-1">
              <p>• Drag to pan</p>
              <p>• Scroll to zoom</p>
              <p>• Click and drag nodes</p>
            </div>
          </Panel>
        </ReactFlow>
      </div>
    </div>
  )
}

export default NetworkDiagramPage
