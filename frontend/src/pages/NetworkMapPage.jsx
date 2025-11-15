import { useEffect, useState, useCallback } from 'react'
import ReactFlow, {
  Controls,
  Background,
  MiniMap,
  useNodesState,
  useEdgesState,
  MarkerType,
  Panel,
  Handle,
  Position
} from 'reactflow'
import 'reactflow/dist/style.css'
import { Database, Server, Activity, Wifi, WifiOff, RefreshCw, Terminal, Globe, Lock, Unlock, Monitor, Zap, ChevronDown, ChevronUp, Save } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import api from '../services/api'
import { toast } from 'react-hot-toast'
import AnimatedEdge from '../components/AnimatedEdge'
import RDPDirectTest from '../components/RDPDirectTest'

// Custom Node Component with Services
function CustomNode({ data }) {
  const navigate = useNavigate()
  const Icon = data.type === 'hub' ? Database : Server
  const isHub = data.type === 'hub'
  const canAccess = !isHub && data.agent_connected && data.status === 'online'

  const handleSSH = (e) => {
    e.stopPropagation()
    // Navigate to SSH terminal - would need terminal modal or page
    console.log('SSH access to node:', data.id)
  }

  const handleRDP = (e) => {
    e.stopPropagation()
    navigate(`/nodes/${data.id}/rdp`)
  }

  const handleRDPTest = (e) => {
    e.stopPropagation()
    if (data.onTestClick) {
      data.onTestClick(data.id, data.label)
    }
  }

  return (
    <div className={`px-4 py-3 rounded-lg border-2 shadow-lg transition-all min-w-[180px] ${
      isHub
        ? 'bg-green-500 border-green-600'
        : data.status === 'online'
          ? 'bg-blue-500 border-blue-600'
          : 'bg-red-500 border-red-600'
    }`}>
      <Handle type="target" position={Position.Top} style={{ background: '#555' }} />

      <div className="flex items-center gap-2 mb-2">
        <Icon className="w-5 h-5 text-white flex-shrink-0" />
        <div className="flex-1">
          <p className="text-white font-semibold text-sm">{data.label}</p>
          <p className="text-white/80 text-xs">{data.ip_address}</p>
        </div>
      </div>

      {/* Agent Connection Status */}
      {data.agent_connected !== undefined && (
        <div className="flex items-center gap-1 mb-2">
          {data.agent_connected ? (
            <>
              <Wifi className="w-3 h-3 text-white" />
              <span className="text-white/80 text-xs">Agent Connected</span>
            </>
          ) : (
            <>
              <WifiOff className="w-3 h-3 text-white/50" />
              <span className="text-white/60 text-xs">Agent Offline</span>
            </>
          )}
        </div>
      )}

      {/* Services */}
      {data.services && data.services.length > 0 && (
        <div className="mt-2 pt-2 border-t border-white/20">
          <p className="text-white/70 text-xs mb-1">Services:</p>
          <div className="flex flex-wrap gap-1">
            {data.services.map((service, idx) => {
              const serviceIcon = service.includes('SSH') ? Terminal :
                                 service.includes('HTTP') || service.includes('HTTPS') ? Globe :
                                 service.includes('WebSocket') ? Wifi :
                                 Activity
              const ServiceIcon = serviceIcon

              return (
                <div
                  key={idx}
                  className="flex items-center gap-1 px-2 py-0.5 bg-white/20 rounded text-xs text-white"
                  title={service}
                >
                  <ServiceIcon className="w-3 h-3" />
                  <span>{service.split(':')[0]}</span>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Remote Access Buttons */}
      {canAccess && (
        <div className="mt-2 pt-2 border-t border-white/20 space-y-1">
          <div className="flex gap-1">
            {data.ssh_available !== false && (
              <button
                onClick={handleSSH}
                className="flex-1 flex items-center justify-center gap-1 px-2 py-1 bg-white/20 hover:bg-white/30 rounded text-xs text-white transition-colors"
                title="SSH Terminal"
              >
                <Terminal className="w-3 h-3" />
                <span>SSH</span>
              </button>
            )}
            {data.rdp_available === true && (
              <button
                onClick={handleRDP}
                className="flex-1 flex items-center justify-center gap-1 px-2 py-1 bg-white/20 hover:bg-white/30 rounded text-xs text-white transition-colors"
                title="RDP Desktop"
              >
                <Monitor className="w-3 h-3" />
                <span>RDP</span>
              </button>
            )}
          </div>
          {data.rdp_available === true && (
            <button
              onClick={handleRDPTest}
              className="w-full flex items-center justify-center gap-1 px-2 py-1 bg-yellow-600/30 hover:bg-yellow-600/40 border border-yellow-500/50 rounded text-xs text-yellow-200 transition-colors"
              title="RDP Direct - Native Node.js RDP"
            >
              <Zap className="w-3 h-3" />
              <span>RDP Direct</span>
            </button>
          )}
        </div>
      )}

      <Handle type="source" position={Position.Bottom} style={{ background: '#555' }} />
    </div>
  )
}

const nodeTypes = {
  custom: CustomNode
}

const edgeTypes = {
  animated: AnimatedEdge
}

function NetworkMapPage() {
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])
  const [loading, setLoading] = useState(true)
  const [stats, setStats] = useState(null)
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [showRDPTest, setShowRDPTest] = useState(false)
  const [testNodeId, setTestNodeId] = useState(null)
  const [testNodeName, setTestNodeName] = useState('')
  const [isTopologyCollapsed, setIsTopologyCollapsed] = useState(false)
  const [isLegendCollapsed, setIsLegendCollapsed] = useState(false)
  const [isSaving, setIsSaving] = useState(false)

  const handleOpenRDPTest = useCallback((nodeId, nodeName) => {
    setTestNodeId(nodeId)
    setTestNodeName(nodeName)
    setShowRDPTest(true)
  }, [])

  const loadTopology = useCallback(async () => {
    try {
      const response = await api.get('/network/topology')
      const data = response.data

      // Always load saved positions from backend
      let savedPositions = {}
      try {
        const positionsResponse = await api.get('/network/node-positions')
        savedPositions = positionsResponse.data.positions || {}
        console.log('Loaded saved positions:', savedPositions)
        console.log('Number of saved positions:', Object.keys(savedPositions).length)

        // Show notification if positions were loaded
        if (Object.keys(savedPositions).length > 0) {
          toast.success(`✅ Caricate ${Object.keys(savedPositions).length} posizioni salvate`, {
            duration: 3000
          })
        }
      } catch (error) {
        console.error('Failed to load saved positions:', error)
        savedPositions = {}
      }

      // Convert backend nodes to ReactFlow nodes
      const flowNodes = data.nodes.map(node => {
        const savedPos = savedPositions[node.id]
        const calculatedPos = getNodePosition(node, data.nodes)
        const finalPos = savedPos || calculatedPos

        console.log(`Node ${node.label} (${node.id}):`, {
          hasSavedPosition: !!savedPos,
          savedPosition: savedPos,
          calculatedPosition: calculatedPos,
          finalPosition: finalPos
        })

        return {
          id: node.id,
          type: 'custom',
          data: {
            label: node.label,
            type: node.type,
            status: node.status,
            ip_address: node.ip_address,
            agent_connected: node.agent_connected,
            description: node.description,
            services: node.services || [],
            rdp_available: node.rdp_available,
            ssh_available: node.ssh_available,
            onTestClick: handleOpenRDPTest
          },
          // Use saved position if available, otherwise calculate new position
          position: finalPos,
          sourcePosition: 'bottom',
          targetPosition: 'top'
        }
      })

      // Convert backend edges to ReactFlow edges
      const flowEdges = data.edges.map(edge => {
        // Create label with services
        const serviceLabel = edge.services && edge.services.length > 0
          ? edge.services.join(' | ')
          : edge.label

        const edgeColor = getEdgeColor(edge.connection_quality, edge.status)
        const isActive = edge.status === 'active'

        return {
          id: `${edge.from}-${edge.to}`,
          source: edge.from,
          target: edge.to,
          label: serviceLabel,
          data: {
            services: edge.services || [],
            quality: edge.connection_quality,
            bandwidth: edge.bandwidth || { in: 0, out: 0, total: 0, usage_percent: 0 },
            status: edge.status
          },
          type: 'animated', // Use custom animated edge
          style: {
            stroke: edgeColor,
            strokeWidth: isActive ? 3 : 2,
            strokeDasharray: edge.status === 'inactive' ? '5,5' : 'none'
          },
          // Bidirectional arrows
          markerStart: {
            type: MarkerType.ArrowClosed,
            color: edgeColor,
            width: 20,
            height: 20
          },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: edgeColor,
            width: 20,
            height: 20
          }
        }
      })

      setNodes(flowNodes)
      setEdges(flowEdges)
      setStats(data.stats)
      setLoading(false)
    } catch (error) {
      console.error('Error loading topology:', error)
      toast.error('Failed to load network topology')
      setLoading(false)
    }
  }, [setNodes, setEdges, handleOpenRDPTest])

  // Node changes handler - no automatic saving
  const handleNodesChange = useCallback((changes) => {
    onNodesChange(changes)
  }, [onNodesChange])

  // Save current positions to backend
  const savePositions = useCallback(async () => {
    setIsSaving(true)
    try {
      // Get current positions from all nodes
      const positions = {}
      nodes.forEach(node => {
        positions[node.id] = node.position
      })

      console.log('Saving positions:', positions)

      // Save to backend
      await api.post('/network/node-positions', positions)

      // Create detailed message showing all saved positions
      const positionsList = Object.entries(positions)
        .map(([nodeId, pos]) => {
          const node = nodes.find(n => n.id === nodeId)
          const nodeName = node?.data?.label || nodeId
          return `${nodeName}: (x: ${Math.round(pos.x)}, y: ${Math.round(pos.y)})`
        })
        .join('\n')

      // Show success message with details
      const message = `✅ Saved ${Object.keys(positions).length} node positions:\n\n${positionsList}`

      // Show toast that auto-dismisses after 10 seconds
      toast.success(message, {
        duration: 10000,
        style: {
          maxWidth: '500px',
          whiteSpace: 'pre-line'
        }
      })

      console.log('Positions saved successfully:', positions)
    } catch (error) {
      console.error('Failed to save positions:', error)
      toast.error('Failed to save node positions')
    } finally {
      setIsSaving(false)
    }
  }, [nodes])

  useEffect(() => {
    loadTopology()
  }, [loadTopology])

  // Auto-refresh every 30 seconds
  useEffect(() => {
    if (!autoRefresh) return

    const interval = setInterval(() => {
      loadTopology()
    }, 30000)

    return () => clearInterval(interval)
  }, [autoRefresh, loadTopology])

  // Calculate node position (hierarchical layout)
  const getNodePosition = (node, allNodes) => {
    if (node.type === 'hub') {
      // Hub at the top center
      return { x: 400, y: 50 }
    }

    // Edge nodes in a row below the hub
    const edgeNodes = allNodes.filter(n => n.type === 'edge')
    const nodeIndex = edgeNodes.findIndex(n => n.id === node.id)
    const spacing = 350
    const startX = 400 - (edgeNodes.length - 1) * spacing / 2

    return {
      x: startX + nodeIndex * spacing,
      y: 300
    }
  }

  // Get edge color based on connection quality
  const getEdgeColor = (quality, status) => {
    if (status === 'inactive') return '#64748b' // Gray

    switch (quality) {
      case 'excellent':
        return '#22c55e' // Green
      case 'fair':
        return '#eab308' // Yellow
      case 'poor':
        return '#f97316' // Orange
      default:
        return '#64748b' // Gray
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-slate-900">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-white">Loading network topology...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="h-[calc(100vh-80px)] bg-slate-900">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={handleNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        fitView
        attributionPosition="bottom-right"
      >
        <Background color="#334155" gap={16} />
        <Controls className="bg-slate-800 border-slate-700" />
        <MiniMap
          nodeColor={(node) => {
            if (node.data.type === 'hub') return '#22c55e'
            return node.data.status === 'online' ? '#3b82f6' : '#ef4444'
          }}
          maskColor="rgba(15, 23, 42, 0.8)"
          className="bg-slate-800 border border-slate-700"
        />

        {/* Stats Panel */}
        <Panel position="top-left" className="bg-slate-800/95 backdrop-blur-sm border border-slate-700 rounded-lg m-4 overflow-hidden transition-all duration-300">
          <div
            className="flex items-center justify-between p-4 cursor-pointer hover:bg-slate-750 transition-colors"
            onClick={() => setIsTopologyCollapsed(!isTopologyCollapsed)}
          >
            <div className="flex items-center gap-3">
              <Activity className="w-5 h-5 text-blue-400" />
              <h2 className="text-white font-semibold">Network Topology</h2>
            </div>
            <button className="p-1 hover:bg-slate-700 rounded transition-colors">
              {isTopologyCollapsed ? (
                <ChevronDown className="w-4 h-4 text-slate-400" />
              ) : (
                <ChevronUp className="w-4 h-4 text-slate-400" />
              )}
            </button>
          </div>

          {!isTopologyCollapsed && stats && (
            <div className="px-4 pb-4">
            <div className="space-y-2 text-sm">
              <div className="flex items-center justify-between gap-8">
                <span className="text-slate-400">Total Nodes:</span>
                <span className="text-white font-semibold">{stats.total_nodes}</span>
              </div>
              <div className="flex items-center justify-between gap-8">
                <span className="text-slate-400">Hub Nodes:</span>
                <span className="text-green-400 font-semibold">{stats.hub_nodes}</span>
              </div>
              <div className="flex items-center justify-between gap-8">
                <span className="text-slate-400">Edge Nodes:</span>
                <span className="text-blue-400 font-semibold">{stats.edge_nodes}</span>
              </div>
              <div className="h-px bg-slate-700 my-2"></div>
              <div className="flex items-center justify-between gap-8">
                <span className="text-slate-400">Online:</span>
                <span className="text-green-400 font-semibold">{stats.online_nodes}</span>
              </div>
              <div className="flex items-center justify-between gap-8">
                <span className="text-slate-400">Offline:</span>
                <span className="text-red-400 font-semibold">{stats.offline_nodes}</span>
              </div>
              <div className="h-px bg-slate-700 my-2"></div>
              <div className="flex items-center justify-between gap-8">
                <span className="text-slate-400">Active Connections:</span>
                <span className="text-green-400 font-semibold">{stats.active_connections}</span>
              </div>
              <div className="flex items-center justify-between gap-8">
                <span className="text-slate-400">Inactive Connections:</span>
                <span className="text-gray-400 font-semibold">{stats.inactive_connections}</span>
              </div>
              {stats.total_services !== undefined && (
                <>
                  <div className="h-px bg-slate-700 my-2"></div>
                  <div className="flex items-center justify-between gap-8">
                    <span className="text-slate-400">Total Services:</span>
                    <span className="text-purple-400 font-semibold">{stats.total_services}</span>
                  </div>
                  <div className="flex items-center justify-between gap-8">
                    <span className="text-slate-400">Active Services:</span>
                    <span className="text-purple-400 font-semibold">{stats.active_services}</span>
                  </div>
                </>
              )}
              {stats.total_bandwidth !== undefined && (
                <>
                  <div className="h-px bg-slate-700 my-2"></div>
                  <div className="flex items-center justify-between gap-8">
                    <span className="text-slate-400">Total Bandwidth:</span>
                    <span className="text-cyan-400 font-semibold font-mono">{stats.total_bandwidth} Mbps</span>
                  </div>
                  <div className="flex items-center justify-between gap-8 text-[11px]">
                    <span className="text-slate-500">↓ In:</span>
                    <span className="text-green-400 font-mono">{stats.total_bandwidth_in} Mbps</span>
                  </div>
                  <div className="flex items-center justify-between gap-8 text-[11px]">
                    <span className="text-slate-500">↑ Out:</span>
                    <span className="text-blue-400 font-mono">{stats.total_bandwidth_out} Mbps</span>
                  </div>
                </>
              )}
            </div>
            </div>
          )}

          {!isTopologyCollapsed && (
            <div className="px-4 pb-4">
            <div className="mt-4 pt-3 border-t border-slate-700 space-y-2">
            <button
              onClick={savePositions}
              disabled={isSaving}
              className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-green-600 hover:bg-green-700 disabled:bg-slate-600 disabled:cursor-not-allowed text-white rounded-lg transition-colors text-sm font-medium"
            >
              <Save className="w-4 h-4" />
              {isSaving ? 'Saving...' : 'Save Positions'}
            </button>

            <button
              onClick={loadTopology}
              className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors text-sm"
            >
              <RefreshCw className="w-4 h-4" />
              Refresh
            </button>

            <label className="flex items-center gap-2 text-sm text-slate-400 cursor-pointer">
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
                className="rounded border-slate-600 bg-slate-700 text-blue-600 focus:ring-blue-500 focus:ring-offset-slate-900"
              />
              Auto-refresh (30s)
            </label>
            </div>
            </div>
          )}
        </Panel>

        {/* Legend Panel */}
        <Panel position="top-right" className="bg-slate-800/95 backdrop-blur-sm border border-slate-700 rounded-lg m-4 overflow-hidden transition-all duration-300">
          <div
            className="flex items-center justify-between p-4 cursor-pointer hover:bg-slate-750 transition-colors"
            onClick={() => setIsLegendCollapsed(!isLegendCollapsed)}
          >
            <h3 className="text-white font-semibold text-sm">Legend</h3>
            <button className="p-1 hover:bg-slate-700 rounded transition-colors">
              {isLegendCollapsed ? (
                <ChevronDown className="w-4 h-4 text-slate-400" />
              ) : (
                <ChevronUp className="w-4 h-4 text-slate-400" />
              )}
            </button>
          </div>

          {!isLegendCollapsed && (
            <div className="px-4 pb-4">
          <div className="space-y-2 text-xs">
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-green-500 rounded"></div>
              <span className="text-slate-300">Hub (Online)</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-blue-500 rounded"></div>
              <span className="text-slate-300">Edge (Online)</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-red-500 rounded"></div>
              <span className="text-slate-300">Node (Offline)</span>
            </div>
            <div className="h-px bg-slate-700 my-2"></div>
            <p className="text-slate-400 font-semibold mb-1">Connections:</p>
            <div className="flex items-center gap-2">
              <div className="w-8 h-0.5 bg-green-500"></div>
              <span className="text-slate-300">Excellent</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-8 h-0.5 bg-yellow-500"></div>
              <span className="text-slate-300">Fair</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-8 h-0.5 bg-orange-500"></div>
              <span className="text-slate-300">Poor</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-8 h-0.5 bg-gray-500" style={{strokeDasharray: '5,5'}}></div>
              <span className="text-slate-300">Disconnected</span>
            </div>
            <div className="mt-1 text-slate-400 text-[10px] italic space-y-0.5">
              <div>↔ Bidirectional traffic</div>
              <div>● Particles = data flowing</div>
              <div>Speed ∝ bandwidth usage</div>
            </div>
            <div className="h-px bg-slate-700 my-2"></div>
            <p className="text-slate-400 font-semibold mb-1">Services:</p>
            <div className="flex items-center gap-2">
              <Terminal className="w-3 h-3 text-slate-300" />
              <span className="text-slate-300">SSH</span>
            </div>
            <div className="flex items-center gap-2">
              <Globe className="w-3 h-3 text-slate-300" />
              <span className="text-slate-300">HTTP/HTTPS</span>
            </div>
            <div className="flex items-center gap-2">
              <Wifi className="w-3 h-3 text-slate-300" />
              <span className="text-slate-300">WebSocket</span>
            </div>
          </div>
            </div>
          )}
        </Panel>

        {/* Controls Info */}
        <Panel position="bottom-left" className="bg-slate-800/90 backdrop-blur-sm border border-slate-700 rounded-lg p-3 m-4 text-xs text-slate-400">
          <p className="font-semibold text-white mb-1">Controls:</p>
          <ul className="space-y-0.5">
            <li>• Drag to pan</li>
            <li>• Scroll to zoom</li>
            <li>• Click node to select</li>
            <li>• Hover for details</li>
          </ul>
        </Panel>
      </ReactFlow>

      {/* RDP Direct Test Modal */}
      {showRDPTest && testNodeId && (
        <RDPDirectTest
          nodeId={testNodeId}
          nodeName={testNodeName}
          onClose={() => setShowRDPTest(false)}
        />
      )}
    </div>
  )
}

export default NetworkMapPage
