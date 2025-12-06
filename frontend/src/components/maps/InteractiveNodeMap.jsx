import { useEffect, useState, useRef, memo } from 'react'
import { MapContainer, TileLayer, Marker, Popup, useMap, CircleMarker } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import 'leaflet.markercluster/dist/MarkerCluster.css'
import 'leaflet.markercluster/dist/MarkerCluster.Default.css'
import MarkerClusterGroup from 'react-leaflet-cluster'
import { Globe, Cpu, HardDrive, MemoryStick, Server, Wifi, Building2, MapPin, Network } from 'lucide-react'

// Fix for default markers in React-Leaflet
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
})

// Custom icon for nodes
const createNodeIcon = (status, isHub = false, isHighlighted = false) => {
  // Hubs use blue/cyan color, edges use green, highlighted uses orange/yellow
  let color
  if (isHighlighted) {
    color = '#f59e0b' // Amber/orange for highlighted
  } else if (isHub) {
    color = status === 'online' ? '#06b6d4' : '#64748b'  // Cyan for hubs
  } else {
    color = status === 'online' ? '#22c55e' : '#64748b'  // Green for edges
  }

  // Highlighted nodes are bigger and have stronger animation
  const baseSize = isHub ? 32 : 24
  const size = isHighlighted ? baseSize + 16 : baseSize
  const innerSize = isHighlighted ? (isHub ? 32 : 28) : (isHub ? 24 : 16)

  return L.divIcon({
    className: 'custom-node-marker',
    html: `
      <div style="position: relative; width: ${size}px; height: ${size}px;">
        ${(status === 'online' || isHighlighted) ? `<div style="position: absolute; width: ${size}px; height: ${size}px; background: ${color}; border-radius: ${isHub ? '6px' : '50%'}; opacity: ${isHighlighted ? '0.5' : '0.3'}; animation: pulse ${isHighlighted ? '0.5s' : '2s'} infinite;"></div>` : ''}
        ${isHighlighted ? `<div style="position: absolute; width: ${size + 8}px; height: ${size + 8}px; top: -4px; left: -4px; border: 3px solid ${color}; border-radius: 50%; animation: ping 1s infinite;"></div>` : ''}
        <div style="position: absolute; top: ${(size-innerSize)/2}px; left: ${(size-innerSize)/2}px; width: ${innerSize}px; height: ${innerSize}px; background: ${color}; border-radius: ${isHub ? '4px' : '50%'}; border: ${isHighlighted ? '3px' : '2px'} solid ${isHighlighted ? '#fff' : '#1e293b'}; box-shadow: 0 ${isHighlighted ? '4' : '2'}px ${isHighlighted ? '8' : '4'}px rgba(0,0,0,${isHighlighted ? '0.5' : '0.3'}); display: flex; align-items: center; justify-content: center;">
          ${isHub ? '<span style="color: white; font-size: 10px; font-weight: bold;">H</span>' : ''}
        </div>
      </div>
    `,
    iconSize: [size, size],
    iconAnchor: [size/2, size/2],
    popupAnchor: [0, -size/2],
  })
}

// Component to handle map bounds and fit all markers
function FitBounds({ locations }) {
  const map = useMap()

  useEffect(() => {
    if (locations.length > 0) {
      const bounds = L.latLngBounds(locations.map(loc => [loc.latitude, loc.longitude]))
      map.fitBounds(bounds, { padding: [50, 50], maxZoom: 12 })
    }
  }, [locations, map])

  return null
}

// Node details panel component
const NodeDetailsPanel = memo(function NodeDetailsPanel({ node, onClose }) {
  if (!node) return null

  return (
    <div className="absolute top-4 right-4 w-80 bg-slate-800 border border-slate-600 rounded-xl shadow-2xl z-[1000] overflow-hidden">
      {/* Header */}
      <div className="bg-gradient-to-r from-slate-700 to-slate-800 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Server className="w-5 h-5 text-green-400" />
          <span className="font-semibold text-white">{node.name}</span>
        </div>
        <button
          onClick={onClose}
          className="text-slate-400 hover:text-white transition-colors"
        >
          &times;
        </button>
      </div>

      {/* Status Badge */}
      <div className="px-4 py-2 border-b border-slate-700">
        <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
          node.status === 'online' ? 'bg-green-500/20 text-green-400' : 'bg-slate-600 text-slate-400'
        }`}>
          <span className={`w-2 h-2 rounded-full mr-2 ${node.status === 'online' ? 'bg-green-500' : 'bg-slate-500'}`}></span>
          {node.status?.toUpperCase()}
        </span>
      </div>

      {/* Network Info */}
      <div className="px-4 py-3 border-b border-slate-700">
        <h4 className="text-xs font-semibold text-slate-400 uppercase mb-2 flex items-center gap-1">
          <Network className="w-4 h-4" /> Network Info
        </h4>
        <div className="space-y-1.5 text-sm">
          <div className="flex justify-between">
            <span className="text-slate-400">Public IP:</span>
            <span className="text-white font-mono">{node.public_ip || 'N/A'}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">Private IP:</span>
            <span className="text-white font-mono">{node.private_ip || 'N/A'}</span>
          </div>
          {node.geo && (
            <>
              <div className="flex justify-between">
                <span className="text-slate-400">ISP:</span>
                <span className="text-cyan-400 text-xs">{node.geo.isp || 'N/A'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">AS:</span>
                <span className="text-purple-400 text-xs">{node.geo.as || 'N/A'}</span>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Location Info */}
      {node.geo && (
        <div className="px-4 py-3 border-b border-slate-700">
          <h4 className="text-xs font-semibold text-slate-400 uppercase mb-2 flex items-center gap-1">
            <MapPin className="w-4 h-4" /> Location
          </h4>
          <div className="space-y-1.5 text-sm">
            <div className="flex justify-between">
              <span className="text-slate-400">City:</span>
              <span className="text-white">{node.geo.city || 'N/A'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Region:</span>
              <span className="text-white">{node.geo.regionName || 'N/A'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Country:</span>
              <span className="text-white">{node.geo.country || 'N/A'} {node.geo.countryCode ? `(${node.geo.countryCode})` : ''}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Coordinates:</span>
              <span className="text-slate-300 font-mono text-xs">{node.latitude?.toFixed(4)}, {node.longitude?.toFixed(4)}</span>
            </div>
          </div>
        </div>
      )}

      {/* System Resources */}
      <div className="px-4 py-3">
        <h4 className="text-xs font-semibold text-slate-400 uppercase mb-2 flex items-center gap-1">
          <Cpu className="w-4 h-4" /> System Resources
        </h4>
        <div className="space-y-2">
          {/* CPU */}
          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-slate-400">CPU</span>
              <span className="text-white">{node.cpu_usage || 0}%</span>
            </div>
            <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-blue-500 to-blue-400 transition-all duration-500"
                style={{ width: `${node.cpu_usage || 0}%` }}
              />
            </div>
          </div>
          {/* Memory */}
          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-slate-400">Memory</span>
              <span className="text-white">{node.memory_usage || 0}%</span>
            </div>
            <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-purple-500 to-purple-400 transition-all duration-500"
                style={{ width: `${node.memory_usage || 0}%` }}
              />
            </div>
          </div>
          {/* Disk */}
          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-slate-400">Disk</span>
              <span className="text-white">{node.disk_usage || 0}%</span>
            </div>
            <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-cyan-500 to-cyan-400 transition-all duration-500"
                style={{ width: `${node.disk_usage || 0}%` }}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
})

// Main Interactive Map Component
function InteractiveNodeMap({ nodes = [], onNodeSelect, highlightedNodeId = null }) {
  const [selectedNode, setSelectedNode] = useState(null)
  const [mapReady, setMapReady] = useState(false)
  const mapRef = useRef(null)

  // Process nodes - separate those with REAL geo data from those without
  const nodesWithGeo = nodes.filter(node => {
    // Only include nodes that have REAL geolocation data (from GeoLite2)
    const hasRealGeo = node.geo && node.geo.lat && node.geo.lon
    const hasCoords = node.latitude && node.longitude
    return hasRealGeo || hasCoords
  }).map(node => ({
    ...node,
    latitude: node.geo?.lat || node.latitude,
    longitude: node.geo?.lon || node.longitude,
  }))

  // Nodes without geolocation (will be shown in a separate list)
  const nodesWithoutGeo = nodes.filter(node => {
    const hasRealGeo = node.geo && node.geo.lat && node.geo.lon
    const hasCoords = node.latitude && node.longitude
    return !hasRealGeo && !hasCoords
  })

  // Use nodesWithGeo for the map (only real locations)
  const nodeLocations = nodesWithGeo

  const handleMarkerClick = (node) => {
    setSelectedNode(node)
    if (onNodeSelect) onNodeSelect(node)
  }

  const handleClosePanel = () => {
    setSelectedNode(null)
  }

  // Default center if no nodes
  const defaultCenter = nodeLocations.length > 0
    ? [nodeLocations[0].latitude, nodeLocations[0].longitude]
    : [45.4642, 9.1900] // Milan as default

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-xl overflow-hidden relative">
      {/* Header */}
      <div className="px-6 py-4 border-b border-slate-700 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-white flex items-center gap-2">
          <Globe className="w-5 h-5 text-green-400" />
          Global Node Distribution
          <span className="text-sm font-normal text-slate-400 ml-2">({nodes.length} nodes)</span>
        </h2>
        <div className="flex items-center gap-4 text-sm">
          <div className="flex items-center gap-2">
            <span className="w-4 h-4 rounded bg-cyan-500 flex items-center justify-center text-[8px] font-bold text-white">H</span>
            <span className="text-slate-400">Hub</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-green-500"></span>
            <span className="text-slate-400">Edge Online</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-slate-500"></span>
            <span className="text-slate-400">Offline</span>
          </div>
        </div>
      </div>

      {/* Map Container */}
      <div className="h-[400px] relative">
        <MapContainer
          center={defaultCenter}
          zoom={4}
          style={{ height: '100%', width: '100%' }}
          ref={mapRef}
          whenReady={() => setMapReady(true)}
          className="z-0"
        >
          {/* CartoDB Dark Tiles */}
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>'
            url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          />

          {/* Fit bounds to show all markers */}
          {mapReady && nodeLocations.length > 0 && (
            <FitBounds locations={nodeLocations} />
          )}

          {/* Node Markers with Spiderfy for overlapping nodes */}
          <MarkerClusterGroup
            chunkedLoading
            spiderfyOnMaxZoom={true}
            showCoverageOnHover={false}
            zoomToBoundsOnClick={false}
            spiderfyDistanceMultiplier={2}
            maxClusterRadius={40}
            disableClusteringAtZoom={18}
            iconCreateFunction={(cluster) => {
              const count = cluster.getChildCount()
              return L.divIcon({
                html: `<div style="
                  background: linear-gradient(135deg, #3b82f6, #8b5cf6);
                  width: 36px;
                  height: 36px;
                  border-radius: 50%;
                  display: flex;
                  align-items: center;
                  justify-content: center;
                  color: white;
                  font-weight: bold;
                  font-size: 14px;
                  border: 3px solid #1e293b;
                  box-shadow: 0 2px 8px rgba(0,0,0,0.4);
                  cursor: pointer;
                ">${count}</div>`,
                className: 'custom-cluster-icon',
                iconSize: L.point(36, 36),
              })
            }}
          >
            {nodeLocations.map((node) => (
              <Marker
                key={node.id}
                position={[node.latitude, node.longitude]}
                icon={createNodeIcon(
                  node.status,
                  node.is_hub || node.node_type === 'hub',
                  highlightedNodeId === node.id
                )}
                zIndexOffset={highlightedNodeId === node.id ? 1000 : 0}
                eventHandlers={{
                  click: () => handleMarkerClick(node),
                }}
              >
                <Popup className="custom-popup">
                  <div className="bg-slate-800 text-white p-2 rounded min-w-[200px]">
                    <div className="font-semibold mb-1">{node.name}</div>
                    <div className="text-xs text-slate-400">
                      <div>IP: {node.public_ip || node.private_ip || 'N/A'}</div>
                      {node.geo && (
                        <>
                          <div>City: {node.geo.city}</div>
                          <div>ISP: {node.geo.isp}</div>
                          <div>AS: {node.geo.as}</div>
                        </>
                      )}
                    </div>
                  </div>
                </Popup>
              </Marker>
            ))}
          </MarkerClusterGroup>
        </MapContainer>

        {/* Node Details Panel */}
        <NodeDetailsPanel node={selectedNode} onClose={handleClosePanel} />
      </div>

      {/* Zoom Instructions */}
      <div className="px-4 py-2 bg-slate-700/50 text-center text-xs text-slate-400">
        Use mouse wheel to zoom, drag to pan. Click on markers for details.
      </div>

      {/* Nodes without geolocation */}
      {nodesWithoutGeo.length > 0 && (
        <div className="px-4 py-3 border-t border-slate-700 bg-slate-800/50">
          <h4 className="text-xs font-semibold text-amber-400 uppercase mb-2 flex items-center gap-2">
            <MapPin className="w-4 h-4" />
            Nodes without geolocation ({nodesWithoutGeo.length})
            <span className="text-slate-500 font-normal normal-case ml-2">- Missing public IP</span>
          </h4>
          <div className="flex flex-wrap gap-2">
            {nodesWithoutGeo.map(node => (
              <div
                key={node.id}
                className="flex items-center gap-2 px-3 py-1.5 bg-slate-700/50 rounded-lg border border-slate-600"
              >
                <span className={`w-2 h-2 rounded-full ${node.status === 'online' ? 'bg-green-500' : 'bg-slate-500'}`}></span>
                <span className="text-sm text-slate-300">{node.name}</span>
                <span className="text-xs text-slate-500 font-mono">{node.private_ip || 'N/A'}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// Helper function to get default coordinates based on node name/location
function getDefaultCoords(node, index) {
  // Try to extract location from node properties
  const locationHints = [
    node.location,
    node.name,
    node.private_ip,
  ].filter(Boolean).join(' ').toLowerCase()

  const locationMap = {
    'italy': [41.9028, 12.4964],
    'rome': [41.9028, 12.4964],
    'milan': [45.4642, 9.1900],
    'germany': [51.1657, 10.4515],
    'berlin': [52.5200, 13.4050],
    'frankfurt': [50.1109, 8.6821],
    'france': [48.8566, 2.3522],
    'paris': [48.8566, 2.3522],
    'uk': [51.5074, -0.1276],
    'london': [51.5074, -0.1276],
    'usa': [40.7128, -74.0060],
    'new york': [40.7128, -74.0060],
    'los angeles': [34.0522, -118.2437],
    'san francisco': [37.7749, -122.4194],
    'singapore': [1.3521, 103.8198],
    'tokyo': [35.6895, 139.6917],
    'japan': [35.6895, 139.6917],
    'sydney': [-33.8688, 151.2093],
    'australia': [-33.8688, 151.2093],
    'amsterdam': [52.3676, 4.9041],
    'netherlands': [52.3676, 4.9041],
  }

  for (const [key, coords] of Object.entries(locationMap)) {
    if (locationHints.includes(key)) {
      // Add small offset to prevent overlapping markers
      return [coords[0] + (index * 0.1), coords[1] + (index * 0.1)]
    }
  }

  // Default locations if no match
  const defaultLocations = [
    [41.9028, 12.4964],    // Rome
    [45.4642, 9.1900],     // Milan
    [50.1109, 8.6821],     // Frankfurt
    [48.8566, 2.3522],     // Paris
    [51.5074, -0.1276],    // London
    [40.7128, -74.0060],   // New York
    [37.7749, -122.4194],  // San Francisco
    [1.3521, 103.8198],    // Singapore
    [35.6895, 139.6917],   // Tokyo
  ]

  return defaultLocations[index % defaultLocations.length]
}

export default memo(InteractiveNodeMap)
