/**
 * D3TunnelGraph - Radial Tree showing Hub-to-Edge tunnel connections
 * Uses D3 tree layout with radial projection
 *
 * @version 2.3.0
 * @date 2024-12-07
 */

import { useEffect, useRef, useState, useCallback, useMemo, memo } from 'react'
import * as d3 from 'd3'
import { Network, Server, ZoomIn, ZoomOut, RotateCcw, X, Link } from 'lucide-react'

// Service type colors
const SERVICE_COLORS = {
  SSH: '#22c55e',
  TERMINAL: '#10b981',
  HTTPS: '#06b6d4',
  HTTP: '#0ea5e9',
  RDP: '#8b5cf6',
  VNC: '#a855f7',
  API: '#f59e0b',
  DATABASE: '#ef4444',
  FTP: '#ec4899',
  OTHER: '#64748b',
}

const getServiceColor = (service) => {
  const key = service?.toUpperCase() || 'OTHER'
  return SERVICE_COLORS[key] || SERVICE_COLORS.OTHER
}

// Detail Panel Component
const DetailPanel = memo(function DetailPanel({ node, onClose, tunnels }) {
  if (!node) return null

  const isHub = node.data?.isHub
  const isEdge = node.data?.isEdge
  const nodeTunnels = node.data?.tunnels || []
  const services = [...new Set(nodeTunnels.map(t => t.application || 'OTHER'))]

  return (
    <div
      className="absolute top-0 right-0 w-full sm:w-72 h-full bg-slate-900/98 backdrop-blur-sm border-l border-slate-600 shadow-2xl z-50 overflow-hidden flex flex-col"
      onClick={(e) => e.stopPropagation()}
    >
      {/* Header */}
      <div className={`p-4 border-b border-slate-700 flex items-center justify-between shrink-0 ${isHub ? 'bg-cyan-900/40' : 'bg-green-900/40'}`}>
        <div className="flex items-center gap-3">
          {isHub ? (
            <span className="w-10 h-10 rounded-lg bg-cyan-500 flex items-center justify-center text-lg font-bold text-white shadow-lg">H</span>
          ) : (
            <span className={`w-10 h-10 rounded-full flex items-center justify-center shadow-lg ${node.data?.status === 'online' ? 'bg-green-500' : 'bg-slate-500'}`}>
              <Server className="w-5 h-5 text-white" />
            </span>
          )}
          <div>
            <h3 className="font-semibold text-white text-base leading-tight">{node.data?.name || 'Unknown'}</h3>
            <span className={`text-xs px-2 py-0.5 rounded ${isHub ? 'bg-cyan-500/30 text-cyan-300' : 'bg-green-500/30 text-green-300'}`}>
              {isHub ? 'HUB' : 'EDGE'}
            </span>
          </div>
        </div>
        <button
          onClick={onClose}
          className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
        >
          <X className="w-5 h-5 text-slate-400" />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {/* Status */}
        <div className="bg-slate-800/60 rounded-lg p-3">
          <h4 className="text-[10px] font-medium text-slate-500 uppercase mb-2">Status</h4>
          <div className="flex items-center gap-2">
            <span className={`w-3 h-3 rounded-full ${node.data?.status === 'online' || isHub ? 'bg-green-500 animate-pulse' : 'bg-slate-500'}`}></span>
            <span className={`font-medium ${node.data?.status === 'online' || isHub ? 'text-green-400' : 'text-slate-400'}`}>
              {node.data?.status === 'online' || isHub ? 'Online' : 'Offline'}
            </span>
          </div>
        </div>

        {/* Hub Stats */}
        {isHub && (
          <div className="bg-slate-800/60 rounded-lg p-3">
            <h4 className="text-[10px] font-medium text-slate-500 uppercase mb-2">Connections</h4>
            <div className="grid grid-cols-2 gap-2">
              <div className="text-center p-2 bg-slate-700/50 rounded">
                <div className="text-xl font-bold text-cyan-400">{node.children?.length || 0}</div>
                <div className="text-[10px] text-slate-500">Edges</div>
              </div>
              <div className="text-center p-2 bg-slate-700/50 rounded">
                <div className="text-xl font-bold text-purple-400">{tunnels?.length || 0}</div>
                <div className="text-[10px] text-slate-500">Tunnels</div>
              </div>
            </div>
          </div>
        )}

        {/* Tunnels List */}
        {isEdge && nodeTunnels.length > 0 && (
          <div className="bg-slate-800/60 rounded-lg p-3">
            <h4 className="text-[10px] font-medium text-slate-500 uppercase mb-2">
              Tunnels ({nodeTunnels.length})
            </h4>
            <div className="space-y-1.5 max-h-32 overflow-y-auto">
              {nodeTunnels.map((tunnel, i) => (
                <div key={i} className="flex items-center justify-between p-2 bg-slate-700/50 rounded text-sm">
                  <div className="flex items-center gap-2">
                    <span
                      className="w-2.5 h-2.5 rounded-full"
                      style={{ backgroundColor: getServiceColor(tunnel.application) }}
                    ></span>
                    <span className="text-white text-xs">{tunnel.application || 'OTHER'}</span>
                  </div>
                  <span className="text-slate-400 text-[10px] font-mono">
                    :{tunnel.local_port || tunnel.remote_port || '?'}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Services */}
        {isEdge && services.length > 0 && (
          <div className="bg-slate-800/60 rounded-lg p-3">
            <h4 className="text-[10px] font-medium text-slate-500 uppercase mb-2">Services</h4>
            <div className="flex flex-wrap gap-1.5">
              {services.map((svc, i) => (
                <span
                  key={i}
                  className="px-2 py-1 rounded-full text-xs font-medium"
                  style={{
                    backgroundColor: getServiceColor(svc) + '25',
                    color: getServiceColor(svc),
                    border: `1px solid ${getServiceColor(svc)}50`
                  }}
                >
                  {svc}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* No tunnels */}
        {isEdge && nodeTunnels.length === 0 && (
          <div className="bg-slate-800/60 rounded-lg p-4 text-center">
            <Link className="w-6 h-6 mx-auto mb-2 text-slate-600" />
            <p className="text-slate-500 text-xs">No active tunnels</p>
          </div>
        )}
      </div>
    </div>
  )
})

// Main Component
function D3TunnelGraph({ nodes = [], tunnels = [], title = "Tunnel Interconnections" }) {
  const svgRef = useRef(null)
  const zoomRef = useRef(null)
  const containerRef = useRef(null)
  const [dimensions, setDimensions] = useState({ width: 400, height: 350 })
  const [selectedNode, setSelectedNode] = useState(null)
  const [zoomLevel, setZoomLevel] = useState(1)

  // IMPORTANT: Memoize treeData to prevent unnecessary re-renders
  const treeData = useMemo(() => {
    const hubs = nodes.filter(n => n.is_hub || n.node_type === 'hub')
    const edges = nodes.filter(n => !n.is_hub && n.node_type !== 'hub')

    if (hubs.length === 0) {
      return {
        name: 'Network',
        isRoot: true,
        children: edges.map(edge => ({
          id: edge.id,
          name: edge.name,
          isEdge: true,
          status: edge.status,
          tunnels: tunnels.filter(t => t.node_id === edge.id)
        }))
      }
    }

    if (hubs.length === 1) {
      const hub = hubs[0]
      const hubTunnels = tunnels.filter(t => t.hub_id === hub.id || !t.hub_id)

      const edgeNodes = edges.map(edge => {
        const edgeTunnels = hubTunnels.filter(t => t.node_id === edge.id)
        return {
          id: edge.id,
          name: edge.name,
          isEdge: true,
          status: edge.status,
          tunnels: edgeTunnels
        }
      }).filter(e => e.tunnels.length > 0 || edges.length <= 10)

      return {
        id: hub.id,
        name: hub.name,
        isHub: true,
        status: hub.status,
        children: edgeNodes.length > 0 ? edgeNodes : edges.map(e => ({
          id: e.id,
          name: e.name,
          isEdge: true,
          status: e.status,
          tunnels: []
        }))
      }
    }

    return {
      name: 'Network',
      isRoot: true,
      children: hubs.map(hub => {
        const hubTunnels = tunnels.filter(t => t.hub_id === hub.id || !t.hub_id)
        const edgeNodes = edges
          .filter(edge => hubTunnels.some(t => t.node_id === edge.id))
          .map(edge => ({
            id: edge.id,
            name: edge.name,
            isEdge: true,
            status: edge.status,
            tunnels: hubTunnels.filter(t => t.node_id === edge.id)
          }))

        return {
          id: hub.id,
          name: hub.name,
          isHub: true,
          status: hub.status,
          children: edgeNodes.length > 0 ? edgeNodes : undefined
        }
      })
    }
  }, [nodes, tunnels])

  const serviceTypes = useMemo(() =>
    [...new Set(tunnels.map(t => t.application || t.service_type || 'OTHER'))],
    [tunnels]
  )

  // Zoom handlers - use the stored zoom behavior
  const handleZoomIn = useCallback(() => {
    if (!svgRef.current || !zoomRef.current) return
    d3.select(svgRef.current)
      .transition()
      .duration(300)
      .call(zoomRef.current.scaleBy, 1.5)
  }, [])

  const handleZoomOut = useCallback(() => {
    if (!svgRef.current || !zoomRef.current) return
    d3.select(svgRef.current)
      .transition()
      .duration(300)
      .call(zoomRef.current.scaleBy, 0.67)
  }, [])

  const handleZoomReset = useCallback(() => {
    if (!svgRef.current || !zoomRef.current) return
    d3.select(svgRef.current)
      .transition()
      .duration(400)
      .call(zoomRef.current.transform, d3.zoomIdentity)
  }, [])

  // Resize handler
  useEffect(() => {
    const handleResize = () => {
      if (containerRef.current) {
        const { width, height } = containerRef.current.getBoundingClientRect()
        setDimensions({ width: Math.max(300, width), height: Math.max(300, height) })
      }
    }
    handleResize()
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  // D3 Rendering - separate effect for initial setup
  useEffect(() => {
    if (!svgRef.current || !treeData) return

    const svg = d3.select(svgRef.current)
    svg.selectAll('*').remove()

    const { width, height } = dimensions
    const cx = width / 2
    const cy = height / 2
    const radius = Math.min(width, height) / 2 - 90

    // Create main group centered
    const g = svg.append('g')
      .attr('class', 'main-group')
      .attr('transform', `translate(${cx},${cy})`)

    // Setup zoom behavior ONCE and store in ref
    const zoom = d3.zoom()
      .scaleExtent([0.3, 4])
      .on('zoom', (event) => {
        // Apply transform to the group
        g.attr('transform', `translate(${cx},${cy}) scale(${event.transform.k}) translate(${event.transform.x / event.transform.k},${event.transform.y / event.transform.k})`)
        setZoomLevel(event.transform.k)
      })

    // Store zoom in ref for button handlers
    zoomRef.current = zoom

    // Apply zoom to SVG
    svg.call(zoom)
      .on('dblclick.zoom', null) // Disable double-click zoom

    // Create hierarchy and layout
    const root = d3.hierarchy(treeData)
    const tree = d3.tree()
      .size([2 * Math.PI, radius])
      .separation((a, b) => (a.parent === b.parent ? 1 : 2) / a.depth)

    tree(root)

    // Draw links
    const linkGenerator = d3.linkRadial()
      .angle(d => d.x)
      .radius(d => d.y)

    g.append('g')
      .attr('class', 'links')
      .attr('fill', 'none')
      .attr('stroke-opacity', 0.6)
      .attr('stroke-width', 2)
      .selectAll('path')
      .data(root.links())
      .join('path')
      .attr('d', linkGenerator)
      .attr('stroke', d => {
        if (d.target.data.isEdge && d.target.data.tunnels?.length > 0) {
          return getServiceColor(d.target.data.tunnels[0].application)
        }
        return d.target.data.isHub ? '#06b6d4' : '#64748b'
      })

    // Draw nodes
    const nodeGroups = g.append('g')
      .attr('class', 'nodes')
      .selectAll('g')
      .data(root.descendants())
      .join('g')
      .attr('transform', d => `rotate(${d.x * 180 / Math.PI - 90}) translate(${d.y},0)`)

    // Node shapes
    nodeGroups.each(function(d) {
      const el = d3.select(this)

      if (d.data.isRoot) {
        el.append('circle')
          .attr('r', 8)
          .attr('fill', '#475569')
          .attr('stroke', '#64748b')
          .attr('stroke-width', 2)
      } else if (d.data.isHub) {
        el.append('circle')
          .attr('r', 24)
          .attr('fill', '#06b6d4')
          .attr('fill-opacity', 0.2)

        el.append('rect')
          .attr('x', -15)
          .attr('y', -15)
          .attr('width', 30)
          .attr('height', 30)
          .attr('rx', 6)
          .attr('fill', '#06b6d4')
          .attr('stroke', '#0891b2')
          .attr('stroke-width', 2)

        el.append('text')
          .attr('text-anchor', 'middle')
          .attr('dy', 6)
          .attr('fill', 'white')
          .attr('font-size', '16px')
          .attr('font-weight', 'bold')
          .attr('transform', `rotate(${90 - d.x * 180 / Math.PI})`)
          .attr('pointer-events', 'none')
          .text('H')
      } else if (d.data.isEdge) {
        const color = d.data.status === 'online' ? '#22c55e' : '#64748b'

        el.append('circle')
          .attr('r', 18)
          .attr('fill', color)
          .attr('fill-opacity', 0.2)

        el.append('circle')
          .attr('r', 12)
          .attr('fill', color)
          .attr('stroke', d.data.status === 'online' ? '#16a34a' : '#475569')
          .attr('stroke-width', 2)

        if (d.data.tunnels?.length > 0) {
          const svcs = [...new Set(d.data.tunnels.map(t => t.application || 'OTHER'))]
          svcs.slice(0, 4).forEach((svc, i) => {
            const angle = (i * Math.PI / 2) - Math.PI / 4
            el.append('circle')
              .attr('cx', Math.cos(angle) * 18)
              .attr('cy', Math.sin(angle) * 18)
              .attr('r', 5)
              .attr('fill', getServiceColor(svc))
              .attr('stroke', '#1e293b')
              .attr('stroke-width', 1)
              .attr('pointer-events', 'none')
          })
        }
      }
    })

    // Click handlers for nodes (not root)
    nodeGroups.filter(d => !d.data.isRoot)
      .style('cursor', 'pointer')
      .on('click', function(event, d) {
        event.stopPropagation()
        setSelectedNode(d)
      })

    // Labels
    nodeGroups.append('text')
      .attr('dy', '0.32em')
      .attr('x', d => d.x < Math.PI === !d.children ? 28 : -28)
      .attr('text-anchor', d => d.x < Math.PI === !d.children ? 'start' : 'end')
      .attr('transform', d => {
        if (d.data.isRoot) return ''
        const angle = d.x * 180 / Math.PI
        return `rotate(${angle < 180 ? 0 : 180})`
      })
      .attr('fill', d => {
        if (d.data.isRoot) return '#64748b'
        if (d.data.isHub) return '#22d3ee'
        return d.data.status === 'online' ? '#86efac' : '#94a3b8'
      })
      .attr('font-size', d => d.data.isHub ? '11px' : '10px')
      .attr('font-weight', d => d.data.isHub ? '600' : '400')
      .attr('pointer-events', 'none')
      .text(d => {
        if (d.data.isRoot) return ''
        const name = d.data.name || ''
        return name.length > 14 ? name.substring(0, 12) + '...' : name
      })

    // Click background to deselect
    svg.on('click', () => setSelectedNode(null))

    return () => {
      svg.on('.zoom', null)
      svg.on('click', null)
    }
  }, [treeData, dimensions])

  // Empty state
  if (nodes.length === 0) {
    return (
      <div className="bg-slate-800 border border-slate-700 rounded-xl p-6">
        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Network className="w-5 h-5 text-purple-400" />
          {title}
        </h2>
        <div className="h-[300px] flex items-center justify-center text-slate-500">
          <div className="text-center">
            <Network className="w-12 h-12 mx-auto mb-2 opacity-50" />
            <p>No network data</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-xl p-6 relative">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-lg font-semibold text-white flex items-center gap-2">
          <Network className="w-5 h-5 text-purple-400" />
          {title}
          <span className="text-sm font-normal text-slate-400">
            ({tunnels.length} tunnels)
          </span>
        </h2>

        {/* Zoom Controls */}
        <div className="flex items-center gap-1 bg-slate-700/70 rounded-lg p-1">
          <button
            onClick={handleZoomOut}
            className="p-2 hover:bg-slate-600 rounded transition-colors active:bg-slate-500"
            title="Zoom Out (-)"
          >
            <ZoomOut className="w-4 h-4 text-slate-300" />
          </button>
          <span className="text-xs text-slate-400 px-2 min-w-[50px] text-center font-mono">
            {Math.round(zoomLevel * 100)}%
          </span>
          <button
            onClick={handleZoomIn}
            className="p-2 hover:bg-slate-600 rounded transition-colors active:bg-slate-500"
            title="Zoom In (+)"
          >
            <ZoomIn className="w-4 h-4 text-slate-300" />
          </button>
          <div className="w-px h-5 bg-slate-600 mx-1"></div>
          <button
            onClick={handleZoomReset}
            className="p-2 hover:bg-slate-600 rounded transition-colors active:bg-slate-500"
            title="Reset (0)"
          >
            <RotateCcw className="w-4 h-4 text-slate-300" />
          </button>
        </div>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-2 mb-3 text-xs">
        {serviceTypes.map(service => (
          <div key={service} className="flex items-center gap-1">
            <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: getServiceColor(service) }}></span>
            <span className="text-slate-400">{service}</span>
          </div>
        ))}
        <div className="flex items-center gap-1 ml-2 pl-2 border-l border-slate-600">
          <span className="w-4 h-4 rounded bg-cyan-500 flex items-center justify-center text-[8px] font-bold text-white">H</span>
          <span className="text-slate-400">Hub</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="w-2.5 h-2.5 rounded-full bg-green-500"></span>
          <span className="text-slate-400">Online</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="w-2.5 h-2.5 rounded-full bg-slate-500"></span>
          <span className="text-slate-400">Offline</span>
        </div>
      </div>

      {/* Graph */}
      <div
        ref={containerRef}
        className="relative overflow-hidden rounded-lg bg-slate-900/50 border border-slate-700/50"
        style={{ height: 340 }}
      >
        <svg
          ref={svgRef}
          width={dimensions.width}
          height={dimensions.height}
          className="cursor-grab active:cursor-grabbing"
        />

        {/* Detail Panel */}
        {selectedNode && (
          <DetailPanel
            node={selectedNode}
            tunnels={tunnels}
            onClose={() => setSelectedNode(null)}
          />
        )}
      </div>

      {/* Footer */}
      <div className="text-center text-[10px] text-slate-500 mt-2">
        Scroll or buttons to zoom • Click node for details • Drag to pan
      </div>
    </div>
  )
}

export default memo(D3TunnelGraph)
