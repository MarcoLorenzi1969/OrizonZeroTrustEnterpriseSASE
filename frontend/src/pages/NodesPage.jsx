import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { QRCodeSVG } from 'qrcode.react'
import {
  Server,
  Plus,
  Wifi,
  WifiOff,
  Terminal,
  Globe,
  Lock,
  Shield,
  Trash2,
  Download,
  X,
  RefreshCw,
  Edit2,
  Save
} from 'lucide-react'
import api from '../services/api'
import toast from 'react-hot-toast'
import debugService from '../services/debugService'
import WebTerminal from '../components/WebTerminal'

function NodesPage() {
  const navigate = useNavigate()
  const [nodes, setNodes] = useState([])
  const [loading, setLoading] = useState(true)
  const [showAddModal, setShowAddModal] = useState(false)
  const [qrData, setQrData] = useState(null)
  const [selectedNode, setSelectedNode] = useState(null)
  const [editingNode, setEditingNode] = useState(null)
  const [editForm, setEditForm] = useState({ name: '', location: '' })

  // Form state for new node
  const [nodeName, setNodeName] = useState('')
  const [protocols, setProtocols] = useState({
    ssh: true,
    https: true,
    http: false,
    vpn: false,
    rdp: false
  })

  useEffect(() => {
    loadNodes()

    // Auto-refresh every 10 seconds
    const interval = setInterval(loadNodes, 10000)
    return () => clearInterval(interval)
  }, [])

  const loadNodes = async () => {
    try {
      debugService.info('Nodes Page', { message: 'Loading nodes...' })
      const response = await api.get('/nodes')
      const items = response.data.items || []
      // Ensure items is always an array
      setNodes(Array.isArray(items) ? items : [])
      console.log('📋 [NodesPage] Nodi caricati:', items.length)
      debugService.success('Nodes Page', {
        message: 'Nodes loaded',
        count: Array.isArray(items) ? items.length : 0
      })
    } catch (error) {
      debugService.error('Nodes Page', {
        message: 'Failed to load nodes',
        error: error.message
      })
      // Set empty array on error
      setNodes([])
      if (loading) {
        toast.error('Failed to load nodes')
      }
    } finally {
      setLoading(false)
    }
  }

  const handleProtocolToggle = (protocol) => {
    setProtocols(prev => ({
      ...prev,
      [protocol]: !prev[protocol]
    }))
  }

  const generateQRCode = async () => {
    if (!nodeName.trim()) {
      toast.error('Please enter a node name')
      return
    }

    const selectedProtocols = Object.keys(protocols).filter(p => protocols[p])
    if (selectedProtocols.length === 0) {
      toast.error('Please select at least one protocol')
      return
    }

    try {
      debugService.info('Nodes Page', {
        message: 'Generating QR code...',
        nodeName,
        protocols: selectedProtocols
      })

      // Call backend to generate registration token
      const response = await api.post('/nodes/generate-token', {
        name: nodeName,
        protocols: selectedProtocols
      })

      const { token, registration_url } = response.data

      // Create QR data with all necessary info
      const qrPayload = {
        url: registration_url,
        token: token,
        name: nodeName,
        protocols: selectedProtocols,
        server: window.location.origin
      }

      setQrData(qrPayload)
      debugService.success('Nodes Page', {
        message: 'QR code generated',
        token: token.substring(0, 20) + '...'
      })
      toast.success('QR Code generated! Scan to register node')
    } catch (error) {
      debugService.error('Nodes Page', {
        message: 'Failed to generate QR code',
        error: error.message
      })
      toast.error('Failed to generate QR code')
    }
  }

  const downloadQRCode = () => {
    const svg = document.getElementById('node-qr-code')
    const svgData = new XMLSerializer().serializeToString(svg)
    const canvas = document.createElement('canvas')
    const ctx = canvas.getContext('2d')
    const img = new Image()

    img.onload = () => {
      canvas.width = img.width
      canvas.height = img.height
      ctx.drawImage(img, 0, 0)
      const pngFile = canvas.toDataURL('image/png')
      const downloadLink = document.createElement('a')
      downloadLink.download = `node-${nodeName}-qr.png`
      downloadLink.href = pngFile
      downloadLink.click()
      toast.success('QR Code downloaded!')
    }

    img.src = 'data:image/svg+xml;base64,' + btoa(svgData)
  }

  const deleteNode = async (nodeId) => {
    if (!confirm('Are you sure you want to delete this node?')) return

    try {
      await api.delete(`/nodes/${nodeId}`)
      toast.success('Node deleted successfully')
      loadNodes()
    } catch (error) {
      toast.error('Failed to delete node')
    }
  }

  const openEditModal = (node) => {
    console.log('🔵 [NodesPage] openEditModal chiamato per nodo:', node)
    setEditingNode(node)
    setEditForm({
      name: node.name || '',
      location: node.location || ''
    })
  }

  const closeEditModal = () => {
    setEditingNode(null)
    setEditForm({ name: '', location: '' })
  }

  const saveNodeChanges = async () => {
    if (!editForm.name.trim()) {
      toast.error('Node name is required')
      return
    }

    try {
      await api.patch(`/nodes/${editingNode.id}`, {
        name: editForm.name,
        location: editForm.location
      })
      toast.success('Node updated successfully')
      closeEditModal()
      loadNodes()
    } catch (error) {
      toast.error('Failed to update node')
    }
  }

  const closeModal = () => {
    setShowAddModal(false)
    setQrData(null)
    setNodeName('')
    setProtocols({
      ssh: true,
      https: true,
      http: false,
      vpn: false,
      rdp: false
    })
  }

  // Safely calculate stats - ensure nodes is always an array
  const safeNodes = Array.isArray(nodes) ? nodes : []
  const stats = {
    total: safeNodes.length,
    online: safeNodes.filter(n => n.status === 'online').length,
    offline: safeNodes.filter(n => n.status === 'offline').length
  }

  if (loading && safeNodes.length === 0) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
      </div>
    )
  }

  const handleOpenTerminal = (node) => {
    setSelectedNode(node)
  }

  const handleCloseTerminal = () => {
    setSelectedNode(null)
  }

  return (
    <div className="space-y-6">
      {/* Debug Panel - Versione Frontend */}
      <div className="fixed bottom-4 right-4 bg-slate-800 border border-blue-500 rounded-lg p-3 text-xs z-50 max-w-sm">
        <div className="text-blue-400 font-bold mb-2">🔧 DEBUG INFO</div>
        <div className="text-slate-300 space-y-1">
          <div>✅ NodesPage v1.1 - Edit Feature ATTIVO</div>
          <div>📋 Nodi caricati: {safeNodes.length}</div>
          <div>🔵 Funzione openEditModal: {typeof openEditModal}</div>
          <div>🔷 NodeCard riceve onEdit: {safeNodes.length > 0 ? 'SI' : 'N/A'}</div>
          <div className="text-yellow-400 mt-2">
            Cerca nel console (F12) i log con 🔵 e 🔷
          </div>
        </div>
      </div>

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

      {/* Edit Node Modal */}
      {editingNode && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-800 rounded-xl border border-slate-700 max-w-md w-full">
            <div className="p-6 border-b border-slate-700 flex items-center justify-between">
              <h2 className="text-xl font-bold text-white">Edit Node</h2>
              <button
                onClick={closeEditModal}
                className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
              >
                <X className="w-5 h-5 text-slate-400" />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Node Name
                </label>
                <input
                  type="text"
                  value={editForm.name}
                  onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                  placeholder="e.g., web-server-01"
                  className="w-full px-4 py-3 bg-slate-700/50 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Location
                </label>
                <input
                  type="text"
                  value={editForm.location}
                  onChange={(e) => setEditForm({ ...editForm, location: e.target.value })}
                  placeholder="e.g., Data Center A, Office HQ"
                  className="w-full px-4 py-3 bg-slate-700/50 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div className="flex gap-3 pt-4">
                <button
                  onClick={closeEditModal}
                  className="flex-1 px-4 py-3 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={saveNodeChanges}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors"
                >
                  <Save className="w-4 h-4" />
                  Save Changes
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white mb-2">Nodes Management</h1>
          <p className="text-slate-400">Manage and connect devices to your zero trust network</p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={loadNodes}
            className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
          <button
            onClick={() => setShowAddModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
          >
            <Plus className="w-5 h-5" />
            Add Node
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <StatCard title="Total Nodes" value={stats.total} color="bg-blue-500" />
        <StatCard title="Online" value={stats.online} color="bg-green-500" />
        <StatCard title="Offline" value={stats.offline} color="bg-slate-500" />
      </div>

      {/* Nodes Grid */}
      {safeNodes.length === 0 ? (
        <div className="text-center py-12 bg-slate-800 border border-slate-700 rounded-xl">
          <Server className="w-16 h-16 text-slate-600 mx-auto mb-4" />
          <h3 className="text-xl font-semibold text-white mb-2">No nodes yet</h3>
          <p className="text-slate-400 mb-4">Add your first node to get started</p>
          <button
            onClick={() => setShowAddModal(true)}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
          >
            Add Node
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {safeNodes.map((node) => (
            <NodeCard key={node.id} node={node} onDelete={deleteNode} onEdit={openEditModal} onOpenTerminal={handleOpenTerminal} />
          ))}
        </div>
      )}

      {/* Add Node Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-800 rounded-xl border border-slate-700 max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-slate-700 flex items-center justify-between">
              <h2 className="text-xl font-bold text-white">Add New Node</h2>
              <button
                onClick={closeModal}
                className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
              >
                <X className="w-5 h-5 text-slate-400" />
              </button>
            </div>

            <div className="p-6 space-y-6">
              {!qrData ? (
                <>
                  {/* Node Name */}
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-2">
                      Node Name
                    </label>
                    <input
                      type="text"
                      value={nodeName}
                      onChange={(e) => setNodeName(e.target.value)}
                      placeholder="e.g., web-server-01"
                      className="w-full px-4 py-3 bg-slate-700/50 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>

                  {/* Protocols Selection */}
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-3">
                      Select Protocols to Enable
                    </label>
                    <div className="grid grid-cols-2 gap-3">
                      <ProtocolCheckbox
                        icon={Terminal}
                        label="SSH"
                        port="22"
                        checked={protocols.ssh}
                        onChange={() => handleProtocolToggle('ssh')}
                      />
                      <ProtocolCheckbox
                        icon={Lock}
                        label="HTTPS"
                        port="443"
                        checked={protocols.https}
                        onChange={() => handleProtocolToggle('https')}
                      />
                      <ProtocolCheckbox
                        icon={Globe}
                        label="HTTP"
                        port="80"
                        checked={protocols.http}
                        onChange={() => handleProtocolToggle('http')}
                      />
                      <ProtocolCheckbox
                        icon={Shield}
                        label="VPN"
                        port="1194"
                        checked={protocols.vpn}
                        onChange={() => handleProtocolToggle('vpn')}
                      />
                      <ProtocolCheckbox
                        icon={Server}
                        label="RDP"
                        port="3389"
                        checked={protocols.rdp}
                        onChange={() => handleProtocolToggle('rdp')}
                      />
                    </div>
                  </div>

                  {/* Generate Button */}
                  <button
                    onClick={generateQRCode}
                    className="w-full px-4 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors"
                  >
                    Generate QR Code
                  </button>
                </>
              ) : (
                <>
                  {/* QR Code Display */}
                  <div className="text-center space-y-4">
                    <div className="bg-white p-6 rounded-lg inline-block">
                      <QRCodeSVG
                        id="node-qr-code"
                        value={JSON.stringify(qrData)}
                        size={256}
                        level="H"
                        includeMargin={true}
                      />
                    </div>

                    <div className="space-y-2">
                      <h3 className="text-lg font-semibold text-white">
                        Scan to Register: {nodeName}
                      </h3>
                      <p className="text-slate-400 text-sm">
                        Enabled protocols: {protocols && typeof protocols === 'object'
                          ? Object.keys(protocols).filter(p => protocols[p]).join(', ').toUpperCase()
                          : 'None'
                        }
                      </p>
                    </div>

                    {/* Instructions */}
                    <div className="bg-blue-900/20 border border-blue-800/50 rounded-lg p-4 text-left">
                      <h4 className="text-blue-300 font-medium mb-2">Setup Instructions:</h4>
                      <ol className="text-sm text-blue-400 space-y-1 list-decimal list-inside">
                        <li>Scan this QR code with the Orizon Agent app</li>
                        <li>The node will automatically register with selected protocols</li>
                        <li>Tunnels will be created for each enabled protocol</li>
                        <li>You can manage the node from this dashboard</li>
                      </ol>
                    </div>

                    {/* Action Buttons */}
                    <div className="flex gap-3">
                      <button
                        onClick={downloadQRCode}
                        className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
                      >
                        <Download className="w-4 h-4" />
                        Download QR
                      </button>
                      <button
                        onClick={closeModal}
                        className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
                      >
                        Done
                      </button>
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function StatCard({ title, value, color }) {
  return (
    <div className="bg-slate-800 border border-slate-700 rounded-xl p-6">
      <h3 className="text-slate-400 text-sm font-medium mb-2">{title}</h3>
      <div className="flex items-center gap-3">
        <div className={`w-3 h-3 rounded-full ${color}`}></div>
        <p className="text-3xl font-bold text-white">{value}</p>
      </div>
    </div>
  )
}

function NodeCard({ node, onDelete, onEdit, onOpenTerminal }) {
  const isOnline = node.status === 'online'

  console.log('🔷 [NodeCard] Rendering nodo:', node.name, 'onEdit disponibile:', !!onEdit)

  const handleSSHAccess = () => {
    onOpenTerminal(node)
  }

  const handleEditClick = () => {
    console.log('🔵 [NodeCard] Edit button clicked per nodo:', node.name)
    if (onEdit) {
      onEdit(node)
    } else {
      console.error('❌ [NodeCard] onEdit non è definito!')
    }
  }

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-xl p-6 hover:border-slate-600 transition-colors">
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${
            isOnline ? 'bg-green-500/20' : 'bg-slate-700'
          }`}>
            {isOnline ? (
              <Wifi className="w-6 h-6 text-green-500" />
            ) : (
              <WifiOff className="w-6 h-6 text-slate-500" />
            )}
          </div>
          <div>
            <h3 className="text-white font-semibold">{node.name}</h3>
            <p className="text-sm text-slate-400">{node.ip_address}</p>
          </div>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleEditClick}
            className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
            title="Edit node details"
            data-testid="edit-node-btn"
          >
            <Edit2 className="w-4 h-4 text-blue-400" />
          </button>
          <button
            onClick={() => onDelete(node.id)}
            className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
            title="Delete node"
          >
            <Trash2 className="w-4 h-4 text-red-400" />
          </button>
        </div>
      </div>

      <div className="space-y-2 mb-4">
        <div className="flex items-center justify-between text-sm">
          <span className="text-slate-400">Status</span>
          <span className={`font-medium ${isOnline ? 'text-green-400' : 'text-slate-500'}`}>
            {isOnline ? 'Online' : 'Offline'}
          </span>
        </div>
        <div className="flex items-center justify-between text-sm">
          <span className="text-slate-400">Location</span>
          <span className="text-white">{node.location}</span>
        </div>
        <div className="flex items-center justify-between text-sm">
          <span className="text-slate-400">Last Seen</span>
          <span className="text-white">{new Date(node.last_seen).toLocaleString()}</span>
        </div>
      </div>

      {/* SSH Access Button */}
      {isOnline && (
        <button
          onClick={handleSSHAccess}
          className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
        >
          <Terminal className="w-4 h-4" />
          SSH Access
        </button>
      )}
    </div>
  )
}

function ProtocolCheckbox({ icon: Icon, label, port, checked, onChange }) {
  return (
    <label className={`flex items-center gap-3 p-4 rounded-lg border-2 cursor-pointer transition-all ${
      checked
        ? 'border-blue-500 bg-blue-500/10'
        : 'border-slate-600 bg-slate-700/50 hover:border-slate-500'
    }`}>
      <input
        type="checkbox"
        checked={checked}
        onChange={onChange}
        className="w-5 h-5 rounded border-slate-600 text-blue-600 focus:ring-blue-500 focus:ring-offset-slate-800"
      />
      <Icon className={`w-5 h-5 ${checked ? 'text-blue-400' : 'text-slate-400'}`} />
      <div className="flex-1">
        <div className={`font-medium ${checked ? 'text-white' : 'text-slate-300'}`}>
          {label}
        </div>
        <div className="text-xs text-slate-400">Port {port}</div>
      </div>
    </label>
  )
}

export default NodesPage
// Build $(date +%s)
