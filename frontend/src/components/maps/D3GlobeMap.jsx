/**
 * D3GlobeMap - Interactive 3D Globe with D3.js
 * Displays Orizon Zero Trust hubs and nodes with geolocation
 *
 * Features:
 * - Orthographic projection (3D globe effect)
 * - Auto-rotation with pause on hover
 * - Drag to rotate manually
 * - Click on nodes for details
 * - Connection lines between hubs and nodes
 * - Clustering for overlapping nodes
 * - Smart panel positioning
 * - Responsive design
 *
 * @version 2.1.0
 * @date 2024-12-07
 */

import { useEffect, useRef, useState, useCallback, memo } from 'react'
import * as d3 from 'd3'
import * as topojson from 'topojson-client'
import { Globe, Play, Pause, RotateCcw, ZoomIn, ZoomOut, Server, MapPin, Wifi, ChevronDown, X } from 'lucide-react'

// World TopoJSON URL (Natural Earth 110m)
const WORLD_TOPO_URL = 'https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json'

// Clustering radius in pixels - nodes within this distance are grouped
const CLUSTER_RADIUS = 25

// Versor class for smooth quaternion interpolation (SLERP)
class Versor {
  static fromAngles([l, p, g]) {
    l *= Math.PI / 360
    p *= Math.PI / 360
    g *= Math.PI / 360
    const sl = Math.sin(l), cl = Math.cos(l)
    const sp = Math.sin(p), cp = Math.cos(p)
    const sg = Math.sin(g), cg = Math.cos(g)
    return [
      cl * cp * cg + sl * sp * sg,
      sl * cp * cg - cl * sp * sg,
      cl * sp * cg + sl * cp * sg,
      cl * cp * sg - sl * sp * cg
    ]
  }

  static toAngles([a, b, c, d]) {
    return [
      Math.atan2(2 * (a * b + c * d), 1 - 2 * (b * b + c * c)) * 180 / Math.PI,
      Math.asin(Math.max(-1, Math.min(1, 2 * (a * c - d * b)))) * 180 / Math.PI,
      Math.atan2(2 * (a * d + b * c), 1 - 2 * (c * c + d * d)) * 180 / Math.PI
    ]
  }

  static interpolateAngles(a, b) {
    const i = Versor.interpolate(Versor.fromAngles(a), Versor.fromAngles(b))
    return t => Versor.toAngles(i(t))
  }

  static interpolate([a1, b1, c1, d1], [a2, b2, c2, d2]) {
    let dot = a1 * a2 + b1 * b2 + c1 * c2 + d1 * d2
    if (dot < 0) { a2 = -a2; b2 = -b2; c2 = -c2; d2 = -d2; dot = -dot }
    if (dot > 0.9995) return t => Versor.normalize([a1 + t * (a2 - a1), b1 + t * (b2 - b1), c1 + t * (c2 - c1), d1 + t * (d2 - d1)])
    const theta0 = Math.acos(Math.max(-1, Math.min(1, dot)))
    const sinTheta0 = Math.sin(theta0)
    return t => {
      const theta = theta0 * t
      const s0 = Math.cos(theta) - dot * Math.sin(theta) / sinTheta0
      const s1 = Math.sin(theta) / sinTheta0
      return Versor.normalize([s0 * a1 + s1 * a2, s0 * b1 + s1 * b2, s0 * c1 + s1 * c2, s0 * d1 + s1 * d2])
    }
  }

  static normalize([a, b, c, d]) {
    const l = Math.hypot(a, b, c, d)
    return [a / l, b / l, c / l, d / l]
  }
}

// Node selector for multiple nodes at same location
const NodeSelectorPanel = memo(function NodeSelectorPanel({ nodes, position, containerBounds, onSelectNode, onClose }) {
  if (!nodes || nodes.length === 0) return null

  // Calculate position relative to container, ensuring panel stays within bounds
  const panelWidth = 280
  const panelMaxHeight = 350

  let left = position.x
  let top = position.y

  // Adjust horizontal position
  if (left + panelWidth > containerBounds.width - 10) {
    left = Math.max(10, containerBounds.width - panelWidth - 10)
  }
  if (left < 10) left = 10

  // Adjust vertical position
  if (top + panelMaxHeight > containerBounds.height - 10) {
    top = Math.max(10, containerBounds.height - panelMaxHeight - 10)
  }
  if (top < 10) top = 10

  return (
    <div
      className="absolute bg-slate-800/95 backdrop-blur-sm border border-slate-600 rounded-xl shadow-2xl z-50 overflow-hidden"
      style={{
        left: left,
        top: top,
        width: panelWidth,
        maxHeight: panelMaxHeight
      }}
    >
      {/* Header */}
      <div className="px-4 py-3 bg-gradient-to-r from-purple-600/30 to-blue-600/30 flex items-center justify-between sticky top-0 z-10">
        <div className="flex items-center gap-2">
          <MapPin className="w-5 h-5 text-purple-400" />
          <span className="font-semibold text-white">
            {nodes.length} Nodes at this location
          </span>
        </div>
        <button
          onClick={onClose}
          className="text-slate-400 hover:text-white transition-colors p-1 hover:bg-slate-700 rounded"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Node list */}
      <div className="overflow-y-auto" style={{ maxHeight: panelMaxHeight - 52 }}>
        {nodes.map((node, index) => {
          const isHub = node.is_hub || node.node_type === 'hub'
          return (
            <div
              key={node.id}
              onClick={() => onSelectNode(node)}
              className={`px-4 py-3 cursor-pointer transition-colors border-b border-slate-700/50 last:border-b-0 hover:bg-slate-700/50 ${
                isHub ? 'bg-cyan-900/10' : ''
              }`}
            >
              <div className="flex items-center gap-3">
                {/* Icon */}
                {isHub ? (
                  <span className="w-8 h-8 rounded bg-cyan-500 flex items-center justify-center text-sm font-bold text-white flex-shrink-0">H</span>
                ) : (
                  <span className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                    node.status === 'online' ? 'bg-green-500' : 'bg-slate-500'
                  }`}>
                    <Server className="w-4 h-4 text-white" />
                  </span>
                )}

                {/* Info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-white truncate">{node.name}</span>
                    <span className={`px-1.5 py-0.5 rounded text-[10px] flex-shrink-0 ${
                      isHub ? 'bg-cyan-500/20 text-cyan-400' :
                      node.status === 'online' ? 'bg-green-500/20 text-green-400' : 'bg-slate-600 text-slate-400'
                    }`}>
                      {isHub ? 'HUB' : node.status?.toUpperCase()}
                    </span>
                  </div>
                  <div className="text-xs text-slate-400 truncate">
                    {node.public_ip || node.private_ip || 'No IP'}
                    {node.geo?.city && ` - ${node.geo.city}`}
                  </div>
                </div>

                {/* Arrow */}
                <ChevronDown className="w-4 h-4 text-slate-500 -rotate-90 flex-shrink-0" />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
})

// Single node details panel
const NodeDetailsPanel = memo(function NodeDetailsPanel({ node, position, containerBounds, onClose, onBack, hasMultiple }) {
  if (!node) return null

  const isHub = node.is_hub || node.node_type === 'hub'

  // Calculate position relative to container
  const panelWidth = 300
  const panelHeight = 320

  let left = position.x
  let top = position.y

  // Adjust horizontal position
  if (left + panelWidth > containerBounds.width - 10) {
    left = Math.max(10, containerBounds.width - panelWidth - 10)
  }
  if (left < 10) left = 10

  // Adjust vertical position
  if (top + panelHeight > containerBounds.height - 10) {
    top = Math.max(10, containerBounds.height - panelHeight - 10)
  }
  if (top < 10) top = 10

  return (
    <div
      className="absolute bg-slate-800/95 backdrop-blur-sm border border-slate-600 rounded-xl shadow-2xl z-50 overflow-hidden"
      style={{
        left: left,
        top: top,
        width: panelWidth,
        maxHeight: panelHeight
      }}
    >
      {/* Header */}
      <div className={`px-4 py-3 flex items-center justify-between ${isHub ? 'bg-gradient-to-r from-cyan-600/30 to-blue-600/30' : 'bg-gradient-to-r from-green-600/30 to-emerald-600/30'}`}>
        <div className="flex items-center gap-2">
          {hasMultiple && (
            <button
              onClick={onBack}
              className="text-slate-400 hover:text-white transition-colors p-1 hover:bg-slate-700/50 rounded mr-1"
              title="Back to node list"
            >
              <ChevronDown className="w-4 h-4 rotate-90" />
            </button>
          )}
          {isHub ? (
            <span className="w-6 h-6 rounded bg-cyan-500 flex items-center justify-center text-xs font-bold text-white">H</span>
          ) : (
            <Server className="w-5 h-5 text-green-400" />
          )}
          <span className="font-semibold text-white truncate">{node.name}</span>
        </div>
        <button
          onClick={onClose}
          className="text-slate-400 hover:text-white transition-colors p-1 hover:bg-slate-700/50 rounded"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Content */}
      <div className="p-4 space-y-3 overflow-y-auto" style={{ maxHeight: panelHeight - 52 }}>
        {/* Status */}
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${node.status === 'online' ? 'bg-green-500 animate-pulse' : 'bg-slate-500'}`}></span>
          <span className={`text-sm ${node.status === 'online' ? 'text-green-400' : 'text-slate-400'}`}>
            {node.status?.toUpperCase() || 'UNKNOWN'}
          </span>
          <span className={`ml-auto px-2 py-0.5 rounded text-xs ${isHub ? 'bg-cyan-500/20 text-cyan-400' : 'bg-green-500/20 text-green-400'}`}>
            {isHub ? 'HUB' : 'EDGE'}
          </span>
        </div>

        {/* Network info */}
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-slate-400">Public IP:</span>
            <span className="text-white font-mono text-xs">{node.public_ip || 'N/A'}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">Private IP:</span>
            <span className="text-white font-mono text-xs">{node.private_ip || 'N/A'}</span>
          </div>
        </div>

        {/* Geolocation */}
        {node.geo && (
          <div className="pt-2 border-t border-slate-700 space-y-2 text-sm">
            <div className="flex items-center gap-1 text-xs text-slate-500 uppercase font-medium">
              <MapPin className="w-3 h-3" /> Location
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">City:</span>
              <span className="text-cyan-400">{node.geo.city || 'N/A'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Country:</span>
              <span className="text-cyan-400">{node.geo.country || 'N/A'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">ISP:</span>
              <span className="text-purple-400 text-xs truncate ml-2">{node.geo.isp || 'N/A'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Coords:</span>
              <span className="text-slate-500 font-mono text-xs">
                {node.latitude?.toFixed(4)}, {node.longitude?.toFixed(4)}
              </span>
            </div>
          </div>
        )}

        {/* Services */}
        {node.exposed_applications?.length > 0 && (
          <div className="pt-2 border-t border-slate-700">
            <div className="text-xs text-slate-500 uppercase font-medium mb-2">Services</div>
            <div className="flex flex-wrap gap-1">
              {node.exposed_applications.map(app => (
                <span key={app} className="px-2 py-0.5 rounded text-xs bg-slate-700 text-slate-300">{app}</span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
})

// Main D3 Globe Component
function D3GlobeMap({ nodes = [], highlightedNodeId = null, onNodeSelect }) {
  const svgRef = useRef(null)
  const containerRef = useRef(null)
  const [dimensions, setDimensions] = useState({ width: 800, height: 500 })
  const [isRotating, setIsRotating] = useState(true)
  const [scale, setScale] = useState(1)
  const [selectedNodes, setSelectedNodes] = useState([]) // Array of nodes at clicked location
  const [selectedSingleNode, setSelectedSingleNode] = useState(null) // Single node view
  const [panelPosition, setPanelPosition] = useState({ x: 0, y: 0 })
  const [worldData, setWorldData] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const rotationRef = useRef([0, -20, 0])
  const animationRef = useRef(null)
  const isDraggingRef = useRef(false)
  const projectionRef = useRef(null)

  // Process nodes with geolocation
  const nodesWithGeo = nodes.filter(node => {
    const hasRealGeo = node.geo && (node.geo.lat || node.geo.lon)
    const hasCoords = node.latitude && node.longitude
    return hasRealGeo || hasCoords
  }).map(node => ({
    ...node,
    latitude: node.geo?.lat || node.latitude,
    longitude: node.geo?.lon || node.longitude,
  }))

  const hubs = nodesWithGeo.filter(n => n.is_hub || n.node_type === 'hub')
  const edges = nodesWithGeo.filter(n => !n.is_hub && n.node_type !== 'hub')

  // Get container bounds for panel positioning
  const getContainerBounds = useCallback(() => {
    if (containerRef.current) {
      const rect = containerRef.current.getBoundingClientRect()
      return { width: rect.width, height: rect.height }
    }
    return { width: dimensions.width, height: dimensions.height }
  }, [dimensions])

  // Cluster nodes by screen position
  const clusterNodes = useCallback((nodeList, projection) => {
    if (!projection) return []

    const clusters = []
    const processed = new Set()

    nodeList.forEach(node => {
      if (processed.has(node.id)) return

      const coords = projection([node.longitude, node.latitude])
      if (!coords) return

      // Check if visible (front of globe)
      const dist = d3.geoDistance(
        [node.longitude, node.latitude],
        [-rotationRef.current[0], -rotationRef.current[1]]
      )
      if (dist > Math.PI / 2) return

      // Find nearby nodes
      const cluster = {
        nodes: [node],
        x: coords[0],
        y: coords[1],
        isHub: node.is_hub || node.node_type === 'hub'
      }
      processed.add(node.id)

      nodeList.forEach(otherNode => {
        if (processed.has(otherNode.id)) return

        const otherCoords = projection([otherNode.longitude, otherNode.latitude])
        if (!otherCoords) return

        const otherDist = d3.geoDistance(
          [otherNode.longitude, otherNode.latitude],
          [-rotationRef.current[0], -rotationRef.current[1]]
        )
        if (otherDist > Math.PI / 2) return

        // Check distance in pixels
        const dx = coords[0] - otherCoords[0]
        const dy = coords[1] - otherCoords[1]
        const distance = Math.sqrt(dx * dx + dy * dy)

        if (distance < CLUSTER_RADIUS) {
          cluster.nodes.push(otherNode)
          processed.add(otherNode.id)
          // Update cluster position to center
          cluster.x = (cluster.x * (cluster.nodes.length - 1) + otherCoords[0]) / cluster.nodes.length
          cluster.y = (cluster.y * (cluster.nodes.length - 1) + otherCoords[1]) / cluster.nodes.length
          // Mark if contains hub
          if (otherNode.is_hub || otherNode.node_type === 'hub') {
            cluster.isHub = true
          }
        }
      })

      clusters.push(cluster)
    })

    return clusters
  }, [])

  // Handle click on cluster/node
  const handleMarkerClick = useCallback((cluster, event) => {
    const containerRect = containerRef.current?.getBoundingClientRect()
    const x = event.clientX - (containerRect?.left || 0)
    const y = event.clientY - (containerRect?.top || 0)

    setPanelPosition({ x, y })

    if (cluster.nodes.length === 1) {
      // Single node - show details directly
      setSelectedNodes([])
      setSelectedSingleNode(cluster.nodes[0])
      if (onNodeSelect) onNodeSelect(cluster.nodes[0])
    } else {
      // Multiple nodes - show selector
      setSelectedSingleNode(null)
      setSelectedNodes(cluster.nodes)
    }
  }, [onNodeSelect])

  // Handle node selection from list
  const handleSelectNodeFromList = useCallback((node) => {
    setSelectedSingleNode(node)
    if (onNodeSelect) onNodeSelect(node)
  }, [onNodeSelect])

  // Handle back to list
  const handleBackToList = useCallback(() => {
    setSelectedSingleNode(null)
  }, [])

  // Handle close panel
  const handleClosePanel = useCallback(() => {
    setSelectedNodes([])
    setSelectedSingleNode(null)
  }, [])

  // Load world topology
  useEffect(() => {
    setIsLoading(true)
    fetch(WORLD_TOPO_URL)
      .then(res => res.json())
      .then(world => {
        setWorldData(world)
        setIsLoading(false)
      })
      .catch(err => {
        console.error('Failed to load world data:', err)
        setIsLoading(false)
      })
  }, [])

  // Handle resize
  useEffect(() => {
    const handleResize = () => {
      if (containerRef.current) {
        const { width } = containerRef.current.getBoundingClientRect()
        setDimensions({ width, height: Math.min(500, width * 0.6) })
      }
    }
    handleResize()
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  // Main D3 rendering
  useEffect(() => {
    if (!worldData || !svgRef.current) return

    const svg = d3.select(svgRef.current)
    svg.selectAll('*').remove()

    const { width, height } = dimensions
    const baseRadius = Math.min(width, height) / 2 - 20
    const radius = baseRadius * scale

    // Projection
    const projection = d3.geoOrthographic()
      .scale(radius)
      .translate([width / 2, height / 2])
      .rotate(rotationRef.current)
      .clipAngle(90)

    projectionRef.current = projection

    const path = d3.geoPath(projection)

    // Graticule (grid lines)
    const graticule = d3.geoGraticule()

    // Defs for gradients and filters
    const defs = svg.append('defs')

    // Globe gradient
    const globeGradient = defs.append('radialGradient')
      .attr('id', 'globe-gradient')
      .attr('cx', '30%')
      .attr('cy', '30%')
    globeGradient.append('stop').attr('offset', '0%').attr('stop-color', '#1e3a5f')
    globeGradient.append('stop').attr('offset', '100%').attr('stop-color', '#0f172a')

    // Glow filter
    const glowFilter = defs.append('filter')
      .attr('id', 'glow')
      .attr('x', '-50%').attr('y', '-50%')
      .attr('width', '200%').attr('height', '200%')
    glowFilter.append('feGaussianBlur').attr('stdDeviation', '3').attr('result', 'coloredBlur')
    const feMerge = glowFilter.append('feMerge')
    feMerge.append('feMergeNode').attr('in', 'coloredBlur')
    feMerge.append('feMergeNode').attr('in', 'SourceGraphic')

    // Main group
    const g = svg.append('g')

    // Ocean sphere
    g.append('circle')
      .attr('cx', width / 2)
      .attr('cy', height / 2)
      .attr('r', radius)
      .attr('fill', 'url(#globe-gradient)')
      .attr('stroke', '#334155')
      .attr('stroke-width', 1)

    // Graticule
    g.append('path')
      .datum(graticule())
      .attr('d', path)
      .attr('fill', 'none')
      .attr('stroke', '#334155')
      .attr('stroke-width', 0.3)
      .attr('stroke-opacity', 0.5)

    // Countries
    const countries = topojson.feature(worldData, worldData.objects.countries)
    g.append('g')
      .selectAll('path')
      .data(countries.features)
      .join('path')
      .attr('d', path)
      .attr('fill', '#1e293b')
      .attr('stroke', '#475569')
      .attr('stroke-width', 0.5)

    // Connection lines from hubs to edges
    const connections = g.append('g').attr('class', 'connections')

    const renderConnections = () => {
      connections.selectAll('*').remove()
      hubs.forEach(hub => {
        edges.forEach(edge => {
          const hubCoords = [hub.longitude, hub.latitude]
          const edgeCoords = [edge.longitude, edge.latitude]

          const hubDist = d3.geoDistance(hubCoords, [-rotationRef.current[0], -rotationRef.current[1]])
          const edgeDist = d3.geoDistance(edgeCoords, [-rotationRef.current[0], -rotationRef.current[1]])

          if (hubDist < Math.PI / 2 || edgeDist < Math.PI / 2) {
            const lineGenerator = d3.geoPath(projection)
            const line = {
              type: 'LineString',
              coordinates: [hubCoords, edgeCoords]
            }

            connections.append('path')
              .datum(line)
              .attr('d', lineGenerator)
              .attr('fill', 'none')
              .attr('stroke', edge.status === 'online' ? '#22c55e' : '#64748b')
              .attr('stroke-width', 1)
              .attr('stroke-opacity', 0.4)
              .attr('stroke-dasharray', '4,4')
          }
        })
      })
    }

    renderConnections()

    // Node markers
    const markersGroup = g.append('g').attr('class', 'markers')

    const renderMarkers = () => {
      markersGroup.selectAll('*').remove()

      // Get clusters
      const clusters = clusterNodes(nodesWithGeo, projection)

      clusters.forEach(cluster => {
        const { x, y, nodes: clusterNodes, isHub } = cluster
        const count = clusterNodes.length
        const hasOnline = clusterNodes.some(n => n.status === 'online')
        const isHighlighted = clusterNodes.some(n => n.id === highlightedNodeId)

        if (count === 1) {
          // Single node
          const node = clusterNodes[0]
          const nodeIsHub = node.is_hub || node.node_type === 'hub'
          const baseSize = isHighlighted ? 12 : (nodeIsHub ? 12 : 7)
          const color = nodeIsHub ? '#06b6d4' : (node.status === 'online' ? '#22c55e' : '#64748b')

          // Pulse for online
          if (node.status === 'online' || nodeIsHub) {
            markersGroup.append('circle')
              .attr('cx', x)
              .attr('cy', y)
              .attr('r', baseSize + 6)
              .attr('fill', color)
              .attr('opacity', 0.2)
              .attr('class', 'pulse-ring')
          }

          if (nodeIsHub) {
            // Hub marker (square)
            markersGroup.append('rect')
              .attr('x', x - baseSize/2)
              .attr('y', y - baseSize/2)
              .attr('width', baseSize)
              .attr('height', baseSize)
              .attr('rx', 3)
              .attr('fill', color)
              .attr('stroke', isHighlighted ? '#fff' : '#1e293b')
              .attr('stroke-width', isHighlighted ? 3 : 2)
              .attr('cursor', 'pointer')
              .attr('filter', 'url(#glow)')
              .on('click', (event) => {
                event.stopPropagation()
                handleMarkerClick(cluster, event)
              })

            // H label
            markersGroup.append('text')
              .attr('x', x)
              .attr('y', y + 4)
              .attr('text-anchor', 'middle')
              .attr('fill', 'white')
              .attr('font-size', '10px')
              .attr('font-weight', 'bold')
              .attr('pointer-events', 'none')
              .text('H')
          } else {
            // Edge marker (circle)
            markersGroup.append('circle')
              .attr('cx', x)
              .attr('cy', y)
              .attr('r', baseSize)
              .attr('fill', color)
              .attr('stroke', isHighlighted ? '#fff' : '#1e293b')
              .attr('stroke-width', isHighlighted ? 3 : 2)
              .attr('cursor', 'pointer')
              .attr('filter', isHighlighted ? 'url(#glow)' : null)
              .on('click', (event) => {
                event.stopPropagation()
                handleMarkerClick(cluster, event)
              })
              .on('mouseenter', function() {
                d3.select(this).transition().duration(200).attr('r', baseSize + 3)
              })
              .on('mouseleave', function() {
                d3.select(this).transition().duration(200).attr('r', baseSize)
              })
          }
        } else {
          // Multiple nodes - cluster marker
          const baseSize = isHighlighted ? 20 : 16
          const color = isHub ? '#06b6d4' : (hasOnline ? '#8b5cf6' : '#64748b')

          // Outer ring
          markersGroup.append('circle')
            .attr('cx', x)
            .attr('cy', y)
            .attr('r', baseSize + 4)
            .attr('fill', color)
            .attr('opacity', 0.3)

          // Main circle
          markersGroup.append('circle')
            .attr('cx', x)
            .attr('cy', y)
            .attr('r', baseSize)
            .attr('fill', color)
            .attr('stroke', isHighlighted ? '#fff' : '#1e293b')
            .attr('stroke-width', isHighlighted ? 3 : 2)
            .attr('cursor', 'pointer')
            .attr('filter', 'url(#glow)')
            .on('click', (event) => {
              event.stopPropagation()
              handleMarkerClick(cluster, event)
            })
            .on('mouseenter', function() {
              d3.select(this).transition().duration(200).attr('r', baseSize + 3)
            })
            .on('mouseleave', function() {
              d3.select(this).transition().duration(200).attr('r', baseSize)
            })

          // Count label
          markersGroup.append('text')
            .attr('x', x)
            .attr('y', y + 5)
            .attr('text-anchor', 'middle')
            .attr('fill', 'white')
            .attr('font-size', '12px')
            .attr('font-weight', 'bold')
            .attr('pointer-events', 'none')
            .text(count)
        }
      })
    }

    renderMarkers()

    // Drag behavior
    const drag = d3.drag()
      .on('start', () => {
        isDraggingRef.current = true
        setIsRotating(false)
      })
      .on('drag', (event) => {
        const k = 75 / projection.scale()
        rotationRef.current = [
          rotationRef.current[0] + event.dx * k,
          Math.max(-90, Math.min(90, rotationRef.current[1] - event.dy * k)),
          rotationRef.current[2]
        ]
        projection.rotate(rotationRef.current)
        g.selectAll('path').attr('d', path)
        renderConnections()
        renderMarkers()
      })
      .on('end', () => {
        isDraggingRef.current = false
      })

    svg.call(drag)

    // Auto-rotation animation
    const animate = () => {
      if (isRotating && !isDraggingRef.current) {
        rotationRef.current = [
          rotationRef.current[0] + 0.2,
          rotationRef.current[1],
          rotationRef.current[2]
        ]
        projection.rotate(rotationRef.current)
        g.selectAll('path').attr('d', path)
        renderConnections()
        renderMarkers()
      }
      animationRef.current = requestAnimationFrame(animate)
    }

    animationRef.current = requestAnimationFrame(animate)

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
      }
    }
  }, [worldData, dimensions, scale, isRotating, nodesWithGeo, highlightedNodeId, clusterNodes, handleMarkerClick, hubs, edges])

  // Fly to highlighted node
  useEffect(() => {
    if (highlightedNodeId && nodesWithGeo.length > 0) {
      const node = nodesWithGeo.find(n => n.id === highlightedNodeId)
      if (node) {
        const targetRotation = [-node.longitude, -node.latitude + 20, 0]
        const startRotation = [...rotationRef.current]

        d3.transition()
          .duration(1000)
          .tween('rotate', () => {
            const interpolate = Versor.interpolateAngles(startRotation, targetRotation)
            return t => {
              rotationRef.current = interpolate(t)
            }
          })
      }
    }
  }, [highlightedNodeId, nodesWithGeo])

  const handleZoomIn = () => setScale(s => Math.min(s + 0.2, 2))
  const handleZoomOut = () => setScale(s => Math.max(s - 0.2, 0.5))
  const handleReset = () => {
    setScale(1)
    rotationRef.current = [0, -20, 0]
    setIsRotating(true)
    handleClosePanel()
  }

  const containerBounds = getContainerBounds()

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-xl overflow-hidden relative">
      {/* Header */}
      <div className="px-6 py-4 border-b border-slate-700 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-white flex items-center gap-2">
          <Globe className="w-5 h-5 text-cyan-400" />
          Global Network Topology
          <span className="text-sm font-normal text-slate-400 ml-2">
            ({hubs.length} Hubs, {edges.length} Edges)
          </span>
        </h2>

        {/* Controls */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsRotating(!isRotating)}
            className={`p-2 rounded-lg transition-colors ${isRotating ? 'bg-cyan-500/20 text-cyan-400' : 'bg-slate-700 text-slate-400'}`}
            title={isRotating ? 'Pause rotation' : 'Resume rotation'}
          >
            {isRotating ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
          </button>
          <button
            onClick={handleZoomIn}
            className="p-2 rounded-lg bg-slate-700 text-slate-400 hover:text-white transition-colors"
            title="Zoom in"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
          <button
            onClick={handleZoomOut}
            className="p-2 rounded-lg bg-slate-700 text-slate-400 hover:text-white transition-colors"
            title="Zoom out"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
          <button
            onClick={handleReset}
            className="p-2 rounded-lg bg-slate-700 text-slate-400 hover:text-white transition-colors"
            title="Reset view"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Legend */}
      <div className="absolute top-20 left-4 z-10 bg-slate-900/80 backdrop-blur-sm rounded-lg p-3 space-y-2 text-sm">
        <div className="flex items-center gap-2">
          <span className="w-4 h-4 rounded bg-cyan-500 flex items-center justify-center text-[8px] font-bold text-white">H</span>
          <span className="text-slate-300">Hub</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-green-500"></span>
          <span className="text-slate-300">Edge Online</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-slate-500"></span>
          <span className="text-slate-300">Edge Offline</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-4 h-4 rounded-full bg-purple-500 flex items-center justify-center text-[8px] font-bold text-white">3</span>
          <span className="text-slate-300">Cluster</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-6 border-t border-dashed border-green-500/50"></span>
          <span className="text-slate-300">Connection</span>
        </div>
      </div>

      {/* Globe Container */}
      <div ref={containerRef} className="relative" style={{ minHeight: 400 }}>
        {isLoading ? (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="w-12 h-12 border-4 border-cyan-500 border-t-transparent rounded-full animate-spin"></div>
          </div>
        ) : (
          <svg
            ref={svgRef}
            width={dimensions.width}
            height={dimensions.height}
            style={{ cursor: 'grab', background: 'transparent' }}
          />
        )}

        {/* Node Selector Panel (for multiple nodes) */}
        {selectedNodes.length > 0 && !selectedSingleNode && (
          <NodeSelectorPanel
            nodes={selectedNodes}
            position={panelPosition}
            containerBounds={containerBounds}
            onSelectNode={handleSelectNodeFromList}
            onClose={handleClosePanel}
          />
        )}

        {/* Single Node Details Panel */}
        {selectedSingleNode && (
          <NodeDetailsPanel
            node={selectedSingleNode}
            position={panelPosition}
            containerBounds={containerBounds}
            onClose={handleClosePanel}
            onBack={handleBackToList}
            hasMultiple={selectedNodes.length > 1}
          />
        )}
      </div>

      {/* Footer */}
      <div className="px-4 py-2 bg-slate-700/50 text-center text-xs text-slate-400 flex items-center justify-center gap-4">
        <span>Drag to rotate</span>
        <span>|</span>
        <span>Click nodes for details</span>
        <span>|</span>
        <span>Numbers indicate multiple nodes</span>
      </div>

      {/* Stats bar */}
      <div className="px-4 py-3 border-t border-slate-700 grid grid-cols-4 gap-4 text-center">
        <div>
          <div className="text-2xl font-bold text-cyan-400">{hubs.length}</div>
          <div className="text-xs text-slate-400">Hubs</div>
        </div>
        <div>
          <div className="text-2xl font-bold text-green-400">{edges.filter(e => e.status === 'online').length}</div>
          <div className="text-xs text-slate-400">Edges Online</div>
        </div>
        <div>
          <div className="text-2xl font-bold text-slate-400">{edges.filter(e => e.status !== 'online').length}</div>
          <div className="text-xs text-slate-400">Edges Offline</div>
        </div>
        <div>
          <div className="text-2xl font-bold text-purple-400">{nodesWithGeo.length}</div>
          <div className="text-xs text-slate-400">Total Geolocated</div>
        </div>
      </div>

      {/* CSS for pulse animation */}
      <style>{`
        @keyframes pulse-ring {
          0% { transform: scale(1); opacity: 0.3; }
          50% { transform: scale(1.5); opacity: 0.1; }
          100% { transform: scale(1); opacity: 0.3; }
        }
        .pulse-ring {
          animation: pulse-ring 2s ease-in-out infinite;
          transform-origin: center;
        }
      `}</style>
    </div>
  )
}

export default memo(D3GlobeMap)
