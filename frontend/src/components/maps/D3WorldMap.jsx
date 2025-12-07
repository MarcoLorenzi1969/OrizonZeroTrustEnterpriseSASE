/**
 * D3WorldMap - Unified Interactive World Map with D3.js
 * Supports both Globe (orthographic) and Flat (equirectangular) views
 * with smooth animated transition between them
 *
 * Features:
 * - Orthographic projection (3D globe)
 * - Equirectangular projection (2D flat map)
 * - Animated transition between projections
 * - Auto-rotation (globe mode)
 * - Drag to rotate/pan
 * - Clustering for overlapping nodes
 * - Smart panel positioning
 * - Responsive design
 *
 * @version 3.0.0
 * @date 2024-12-07
 */

import { useEffect, useRef, useState, useCallback, memo } from 'react'
import * as d3 from 'd3'
import * as topojson from 'topojson-client'
import { Globe, Map, Play, Pause, RotateCcw, ZoomIn, ZoomOut, Server, MapPin, ChevronDown, X } from 'lucide-react'

// World TopoJSON URL
const WORLD_TOPO_URL = 'https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json'

// Clustering radius in pixels
const CLUSTER_RADIUS = 25

// Transition duration in ms
const TRANSITION_DURATION = 1500

// Interpolate between two projections
function interpolateProjection(raw0, raw1) {
  const mutate = d3.geoProjectionMutator(t => (x, y) => {
    const [x0, y0] = raw0(x, y)
    const [x1, y1] = raw1(x, y)
    return [x0 + t * (x1 - x0), y0 + t * (y1 - y0)]
  })
  let t = 0
  return Object.assign(mutate(t), {
    alpha(_) {
      return arguments.length ? mutate(t = +_) : t
    }
  })
}

// Node selector for multiple nodes at same location
const NodeSelectorPanel = memo(function NodeSelectorPanel({ nodes, position, containerBounds, onSelectNode, onClose }) {
  if (!nodes || nodes.length === 0) return null

  const panelWidth = 280
  const panelMaxHeight = 350

  let left = position.x
  let top = position.y

  if (left + panelWidth > containerBounds.width - 10) {
    left = Math.max(10, containerBounds.width - panelWidth - 10)
  }
  if (left < 10) left = 10

  if (top + panelMaxHeight > containerBounds.height - 10) {
    top = Math.max(10, containerBounds.height - panelMaxHeight - 10)
  }
  if (top < 10) top = 10

  return (
    <div
      className="absolute bg-slate-800/95 backdrop-blur-sm border border-slate-600 rounded-xl shadow-2xl z-50 overflow-hidden"
      style={{ left, top, width: panelWidth, maxHeight: panelMaxHeight }}
    >
      <div className="px-4 py-3 bg-gradient-to-r from-purple-600/30 to-blue-600/30 flex items-center justify-between sticky top-0 z-10">
        <div className="flex items-center gap-2">
          <MapPin className="w-5 h-5 text-purple-400" />
          <span className="font-semibold text-white">{nodes.length} Nodes</span>
        </div>
        <button onClick={onClose} className="text-slate-400 hover:text-white transition-colors p-1 hover:bg-slate-700 rounded">
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="overflow-y-auto" style={{ maxHeight: panelMaxHeight - 52 }}>
        {nodes.map((node) => {
          const isHub = node.is_hub || node.node_type === 'hub'
          return (
            <div
              key={node.id}
              onClick={() => onSelectNode(node)}
              className={`px-4 py-3 cursor-pointer transition-colors border-b border-slate-700/50 last:border-b-0 hover:bg-slate-700/50 ${isHub ? 'bg-cyan-900/10' : ''}`}
            >
              <div className="flex items-center gap-3">
                {isHub ? (
                  <span className="w-8 h-8 rounded bg-cyan-500 flex items-center justify-center text-sm font-bold text-white flex-shrink-0">H</span>
                ) : (
                  <span className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${node.status === 'online' ? 'bg-green-500' : 'bg-slate-500'}`}>
                    <Server className="w-4 h-4 text-white" />
                  </span>
                )}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-white truncate">{node.name}</span>
                    <span className={`px-1.5 py-0.5 rounded text-[10px] flex-shrink-0 ${isHub ? 'bg-cyan-500/20 text-cyan-400' : node.status === 'online' ? 'bg-green-500/20 text-green-400' : 'bg-slate-600 text-slate-400'}`}>
                      {isHub ? 'HUB' : node.status?.toUpperCase()}
                    </span>
                  </div>
                  <div className="text-xs text-slate-400 truncate">
                    {node.public_ip || node.private_ip || 'No IP'}
                    {node.geo?.city && ` - ${node.geo.city}`}
                  </div>
                </div>
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
  const panelWidth = 300
  const panelHeight = 320

  let left = position.x
  let top = position.y

  if (left + panelWidth > containerBounds.width - 10) {
    left = Math.max(10, containerBounds.width - panelWidth - 10)
  }
  if (left < 10) left = 10

  if (top + panelHeight > containerBounds.height - 10) {
    top = Math.max(10, containerBounds.height - panelHeight - 10)
  }
  if (top < 10) top = 10

  return (
    <div
      className="absolute bg-slate-800/95 backdrop-blur-sm border border-slate-600 rounded-xl shadow-2xl z-50 overflow-hidden"
      style={{ left, top, width: panelWidth, maxHeight: panelHeight }}
    >
      <div className={`px-4 py-3 flex items-center justify-between ${isHub ? 'bg-gradient-to-r from-cyan-600/30 to-blue-600/30' : 'bg-gradient-to-r from-green-600/30 to-emerald-600/30'}`}>
        <div className="flex items-center gap-2">
          {hasMultiple && (
            <button onClick={onBack} className="text-slate-400 hover:text-white transition-colors p-1 hover:bg-slate-700/50 rounded mr-1" title="Back">
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
        <button onClick={onClose} className="text-slate-400 hover:text-white transition-colors p-1 hover:bg-slate-700/50 rounded">
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="p-4 space-y-3 overflow-y-auto" style={{ maxHeight: panelHeight - 52 }}>
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${node.status === 'online' ? 'bg-green-500 animate-pulse' : 'bg-slate-500'}`}></span>
          <span className={`text-sm ${node.status === 'online' ? 'text-green-400' : 'text-slate-400'}`}>
            {node.status?.toUpperCase() || 'UNKNOWN'}
          </span>
          <span className={`ml-auto px-2 py-0.5 rounded text-xs ${isHub ? 'bg-cyan-500/20 text-cyan-400' : 'bg-green-500/20 text-green-400'}`}>
            {isHub ? 'HUB' : 'EDGE'}
          </span>
        </div>

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
          </div>
        )}

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

// Main D3 World Map Component
function D3WorldMap({ nodes = [], highlightedNodeId = null, onNodeSelect, initialView = 'globe' }) {
  const svgRef = useRef(null)
  const containerRef = useRef(null)
  const [dimensions, setDimensions] = useState({ width: 800, height: 500 })
  const [viewMode, setViewMode] = useState(initialView) // 'globe' or 'flat'
  const [isRotating, setIsRotating] = useState(initialView === 'globe')
  const [isTransitioning, setIsTransitioning] = useState(false)
  const [scale, setScale] = useState(1)
  const [selectedNodes, setSelectedNodes] = useState([])
  const [selectedSingleNode, setSelectedSingleNode] = useState(null)
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

  // Get container bounds
  const getContainerBounds = useCallback(() => {
    if (containerRef.current) {
      const rect = containerRef.current.getBoundingClientRect()
      return { width: rect.width, height: rect.height }
    }
    return { width: dimensions.width, height: dimensions.height }
  }, [dimensions])

  // Cluster nodes by screen position
  const clusterNodes = useCallback((nodeList, projection, currentRotation) => {
    if (!projection) return []

    const clusters = []
    const processed = new Set()

    nodeList.forEach(node => {
      if (processed.has(node.id)) return

      const coords = projection([node.longitude, node.latitude])
      if (!coords || isNaN(coords[0]) || isNaN(coords[1])) return

      // For globe mode, check visibility
      if (viewMode === 'globe') {
        const dist = d3.geoDistance(
          [node.longitude, node.latitude],
          [-currentRotation[0], -currentRotation[1]]
        )
        if (dist > Math.PI / 2) return
      }

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
        if (!otherCoords || isNaN(otherCoords[0]) || isNaN(otherCoords[1])) return

        if (viewMode === 'globe') {
          const otherDist = d3.geoDistance(
            [otherNode.longitude, otherNode.latitude],
            [-currentRotation[0], -currentRotation[1]]
          )
          if (otherDist > Math.PI / 2) return
        }

        const dx = coords[0] - otherCoords[0]
        const dy = coords[1] - otherCoords[1]
        const distance = Math.sqrt(dx * dx + dy * dy)

        if (distance < CLUSTER_RADIUS) {
          cluster.nodes.push(otherNode)
          processed.add(otherNode.id)
          cluster.x = (cluster.x * (cluster.nodes.length - 1) + otherCoords[0]) / cluster.nodes.length
          cluster.y = (cluster.y * (cluster.nodes.length - 1) + otherCoords[1]) / cluster.nodes.length
          if (otherNode.is_hub || otherNode.node_type === 'hub') {
            cluster.isHub = true
          }
        }
      })

      clusters.push(cluster)
    })

    return clusters
  }, [viewMode])

  // Handle marker click
  const handleMarkerClick = useCallback((cluster, event) => {
    const containerRect = containerRef.current?.getBoundingClientRect()
    const x = event.clientX - (containerRect?.left || 0)
    const y = event.clientY - (containerRect?.top || 0)

    setPanelPosition({ x, y })

    if (cluster.nodes.length === 1) {
      setSelectedNodes([])
      setSelectedSingleNode(cluster.nodes[0])
      if (onNodeSelect) onNodeSelect(cluster.nodes[0])
    } else {
      setSelectedSingleNode(null)
      setSelectedNodes(cluster.nodes)
    }
  }, [onNodeSelect])

  const handleSelectNodeFromList = useCallback((node) => {
    setSelectedSingleNode(node)
    if (onNodeSelect) onNodeSelect(node)
  }, [onNodeSelect])

  const handleBackToList = useCallback(() => {
    setSelectedSingleNode(null)
  }, [])

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

    // Create projection based on view mode
    let projection
    if (viewMode === 'globe') {
      projection = d3.geoOrthographic()
        .scale(baseRadius * scale)
        .translate([width / 2, height / 2])
        .rotate(rotationRef.current)
        .clipAngle(90)
    } else {
      projection = d3.geoEquirectangular()
        .scale((width / (2 * Math.PI)) * scale)
        .translate([width / 2, height / 2])
        .rotate([0, 0, 0])
    }

    projectionRef.current = projection
    const path = d3.geoPath(projection)
    const graticule = d3.geoGraticule()

    // Defs
    const defs = svg.append('defs')

    // Globe gradient
    const globeGradient = defs.append('radialGradient')
      .attr('id', 'globe-gradient')
      .attr('cx', '30%')
      .attr('cy', '30%')
    globeGradient.append('stop').attr('offset', '0%').attr('stop-color', '#1e3a5f')
    globeGradient.append('stop').attr('offset', '100%').attr('stop-color', '#0f172a')

    // Flat gradient
    const flatGradient = defs.append('linearGradient')
      .attr('id', 'flat-gradient')
      .attr('x1', '0%')
      .attr('y1', '0%')
      .attr('x2', '0%')
      .attr('y2', '100%')
    flatGradient.append('stop').attr('offset', '0%').attr('stop-color', '#0f172a')
    flatGradient.append('stop').attr('offset', '50%').attr('stop-color', '#1e293b')
    flatGradient.append('stop').attr('offset', '100%').attr('stop-color', '#0f172a')

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

    // Background
    if (viewMode === 'globe') {
      g.append('circle')
        .attr('cx', width / 2)
        .attr('cy', height / 2)
        .attr('r', baseRadius * scale)
        .attr('fill', 'url(#globe-gradient)')
        .attr('stroke', '#334155')
        .attr('stroke-width', 1)
    } else {
      g.append('rect')
        .attr('x', 0)
        .attr('y', 0)
        .attr('width', width)
        .attr('height', height)
        .attr('fill', 'url(#flat-gradient)')
    }

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

    // Connections
    const connections = g.append('g').attr('class', 'connections')

    const renderConnections = () => {
      connections.selectAll('*').remove()
      hubs.forEach(hub => {
        edges.forEach(edge => {
          const hubCoords = [hub.longitude, hub.latitude]
          const edgeCoords = [edge.longitude, edge.latitude]

          // Visibility check for globe mode
          if (viewMode === 'globe') {
            const hubDist = d3.geoDistance(hubCoords, [-rotationRef.current[0], -rotationRef.current[1]])
            const edgeDist = d3.geoDistance(edgeCoords, [-rotationRef.current[0], -rotationRef.current[1]])
            if (hubDist > Math.PI / 2 && edgeDist > Math.PI / 2) return
          }

          const lineGenerator = d3.geoPath(projection)
          const line = { type: 'LineString', coordinates: [hubCoords, edgeCoords] }

          connections.append('path')
            .datum(line)
            .attr('d', lineGenerator)
            .attr('fill', 'none')
            .attr('stroke', edge.status === 'online' ? '#22c55e' : '#64748b')
            .attr('stroke-width', 1)
            .attr('stroke-opacity', 0.4)
            .attr('stroke-dasharray', '4,4')
        })
      })
    }

    renderConnections()

    // Markers
    const markersGroup = g.append('g').attr('class', 'markers')

    const renderMarkers = () => {
      markersGroup.selectAll('*').remove()
      const clusters = clusterNodes(nodesWithGeo, projection, rotationRef.current)

      clusters.forEach(cluster => {
        const { x, y, nodes: clusterNodes, isHub } = cluster
        if (isNaN(x) || isNaN(y)) return

        const count = clusterNodes.length
        const hasOnline = clusterNodes.some(n => n.status === 'online')
        const isHighlighted = clusterNodes.some(n => n.id === highlightedNodeId)

        if (count === 1) {
          const node = clusterNodes[0]
          const nodeIsHub = node.is_hub || node.node_type === 'hub'
          const baseSize = isHighlighted ? 12 : (nodeIsHub ? 12 : 7)
          const color = nodeIsHub ? '#06b6d4' : (node.status === 'online' ? '#22c55e' : '#64748b')

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
          const baseSize = isHighlighted ? 20 : 16
          const color = isHub ? '#06b6d4' : (hasOnline ? '#8b5cf6' : '#64748b')

          markersGroup.append('circle')
            .attr('cx', x)
            .attr('cy', y)
            .attr('r', baseSize + 4)
            .attr('fill', color)
            .attr('opacity', 0.3)

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
        if (viewMode === 'globe') setIsRotating(false)
      })
      .on('drag', (event) => {
        if (viewMode === 'globe') {
          const k = 75 / projection.scale()
          rotationRef.current = [
            rotationRef.current[0] + event.dx * k,
            Math.max(-90, Math.min(90, rotationRef.current[1] - event.dy * k)),
            rotationRef.current[2]
          ]
          projection.rotate(rotationRef.current)
        } else {
          // Pan in flat mode
          const currentTranslate = projection.translate()
          projection.translate([
            currentTranslate[0] + event.dx,
            currentTranslate[1] + event.dy
          ])
        }
        g.selectAll('path').attr('d', path)
        renderConnections()
        renderMarkers()
      })
      .on('end', () => {
        isDraggingRef.current = false
      })

    svg.call(drag)

    // Auto-rotation (globe mode only)
    const animate = () => {
      if (viewMode === 'globe' && isRotating && !isDraggingRef.current && !isTransitioning) {
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
  }, [worldData, dimensions, scale, isRotating, viewMode, nodesWithGeo, highlightedNodeId, clusterNodes, handleMarkerClick, hubs, edges, isTransitioning])

  // Toggle view with transition
  const handleToggleView = useCallback(() => {
    if (isTransitioning) return

    setIsTransitioning(true)
    setIsRotating(false)
    handleClosePanel()

    const newView = viewMode === 'globe' ? 'flat' : 'globe'

    // Animate transition
    const svg = d3.select(svgRef.current)
    const { width, height } = dimensions
    const baseRadius = Math.min(width, height) / 2 - 20

    // Get raw projection functions
    const orthoRaw = d3.geoOrthographicRaw
    const equiRaw = d3.geoEquirectangularRaw

    // Create interpolating projection
    const interp = interpolateProjection(
      viewMode === 'globe' ? orthoRaw : equiRaw,
      newView === 'globe' ? orthoRaw : equiRaw
    )

    // Set initial parameters
    if (viewMode === 'globe') {
      interp.scale(baseRadius * scale)
      interp.rotate(rotationRef.current)
    } else {
      interp.scale((width / (2 * Math.PI)) * scale)
      interp.rotate([0, 0, 0])
    }
    interp.translate([width / 2, height / 2])
    interp.clipAngle(viewMode === 'globe' ? 90 : null)

    const path = d3.geoPath(interp)

    // Animate
    d3.transition()
      .duration(TRANSITION_DURATION)
      .ease(d3.easeCubicInOut)
      .tween('projection', () => {
        return t => {
          // Interpolate alpha
          interp.alpha(t)

          // Interpolate scale
          const scaleStart = viewMode === 'globe' ? baseRadius * scale : (width / (2 * Math.PI)) * scale
          const scaleEnd = newView === 'globe' ? baseRadius * scale : (width / (2 * Math.PI)) * scale
          interp.scale(scaleStart + t * (scaleEnd - scaleStart))

          // Interpolate rotation
          const rotStart = viewMode === 'globe' ? rotationRef.current : [0, 0, 0]
          const rotEnd = newView === 'globe' ? [0, -20, 0] : [0, 0, 0]
          interp.rotate([
            rotStart[0] + t * (rotEnd[0] - rotStart[0]),
            rotStart[1] + t * (rotEnd[1] - rotStart[1]),
            rotStart[2] + t * (rotEnd[2] - rotStart[2])
          ])

          // Interpolate clip angle
          if (newView === 'globe') {
            interp.clipAngle(90 + (1 - t) * 90)
          } else {
            interp.clipAngle(90 + t * 90)
          }

          // Update paths
          svg.selectAll('path').attr('d', path)
        }
      })
      .on('end', () => {
        if (newView === 'globe') {
          rotationRef.current = [0, -20, 0]
        }
        setViewMode(newView)
        setIsTransitioning(false)
        if (newView === 'globe') {
          setIsRotating(true)
        }
      })
  }, [viewMode, isTransitioning, dimensions, scale, handleClosePanel])

  const handleZoomIn = () => setScale(s => Math.min(s + 0.2, 2))
  const handleZoomOut = () => setScale(s => Math.max(s - 0.2, 0.5))
  const handleReset = () => {
    setScale(1)
    rotationRef.current = [0, -20, 0]
    if (viewMode === 'globe') setIsRotating(true)
    handleClosePanel()
  }

  const containerBounds = getContainerBounds()

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-xl overflow-hidden relative">
      {/* Header */}
      <div className="px-6 py-4 border-b border-slate-700 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-white flex items-center gap-2">
          {viewMode === 'globe' ? (
            <Globe className="w-5 h-5 text-cyan-400" />
          ) : (
            <Map className="w-5 h-5 text-cyan-400" />
          )}
          Global Network Topology
          <span className="text-sm font-normal text-slate-400 ml-2">
            ({hubs.length} Hubs, {edges.length} Edges)
          </span>
        </h2>

        {/* Controls */}
        <div className="flex items-center gap-2">
          {/* View Toggle */}
          <div className="flex bg-slate-700 rounded-lg p-1 mr-2">
            <button
              onClick={handleToggleView}
              disabled={isTransitioning}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm transition-all ${
                viewMode === 'globe'
                  ? 'bg-cyan-500 text-white'
                  : 'text-slate-400 hover:text-white'
              } ${isTransitioning ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              <Globe className="w-4 h-4" />
              Globe
            </button>
            <button
              onClick={handleToggleView}
              disabled={isTransitioning}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm transition-all ${
                viewMode === 'flat'
                  ? 'bg-cyan-500 text-white'
                  : 'text-slate-400 hover:text-white'
              } ${isTransitioning ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              <Map className="w-4 h-4" />
              Flat
            </button>
          </div>

          {viewMode === 'globe' && (
            <button
              onClick={() => setIsRotating(!isRotating)}
              className={`p-2 rounded-lg transition-colors ${isRotating ? 'bg-cyan-500/20 text-cyan-400' : 'bg-slate-700 text-slate-400'}`}
              title={isRotating ? 'Pause rotation' : 'Resume rotation'}
            >
              {isRotating ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
            </button>
          )}
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

      {/* Transition indicator */}
      {isTransitioning && (
        <div className="absolute top-20 right-4 z-10 bg-cyan-500/20 backdrop-blur-sm rounded-lg px-4 py-2 flex items-center gap-2">
          <div className="w-4 h-4 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin"></div>
          <span className="text-cyan-400 text-sm">Transitioning...</span>
        </div>
      )}

      {/* Map Container */}
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
            style={{ cursor: viewMode === 'globe' ? 'grab' : 'move', background: 'transparent' }}
          />
        )}

        {/* Panels */}
        {selectedNodes.length > 0 && !selectedSingleNode && (
          <NodeSelectorPanel
            nodes={selectedNodes}
            position={panelPosition}
            containerBounds={containerBounds}
            onSelectNode={handleSelectNodeFromList}
            onClose={handleClosePanel}
          />
        )}

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
        <span>{viewMode === 'globe' ? 'Drag to rotate' : 'Drag to pan'}</span>
        <span>|</span>
        <span>Click nodes for details</span>
        <span>|</span>
        <span>Numbers indicate clusters</span>
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

      {/* CSS */}
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

export default memo(D3WorldMap)
