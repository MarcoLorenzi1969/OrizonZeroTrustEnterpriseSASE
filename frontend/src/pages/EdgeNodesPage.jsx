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

function EdgeNodesPage() {
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
    console.log('🔷 [EdgeNodesPage] Component mounted')
    loadNodes()

    // Auto-refresh every 10 seconds
    const interval = setInterval(loadNodes, 10000)
    return () => clearInterval(interval)
  }, [])

  const loadNodes = async () => {
    try {
      console.log('📋 [EdgeNodesPage] Loading nodes...')
      debugService.info('Edge Nodes Page', { message: 'Loading nodes...' })
      const response = await api.get('/nodes/')
      const items = response.data.items || []
      setNodes(Array.isArray(items) ? items : [])
      console.log('✅ [EdgeNodesPage] Nodes loaded:', items.length)
      debugService.success('Edge Nodes Page', {
        message: 'Nodes loaded',
        count: Array.isArray(items) ? items.length : 0
      })
    } catch (error) {
      console.error('❌ [EdgeNodesPage] Failed to load nodes:', error)
      debugService.error('Edge Nodes Page', {
        message: 'Failed to load nodes',
        error: error.message
      })
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
      debugService.info('Edge Nodes Page', {
        message: 'Generating QR code...',
        nodeName,
        protocols: selectedProtocols
      })

      const response = await api.post('/nodes/generate-token', {
        name: nodeName,
        protocols: selectedProtocols
      })

      const { token, registration_url } = response.data

      const qrPayload = {
        url: registration_url,
        token: token,
        name: nodeName,
        protocols: selectedProtocols,
        server: window.location.origin
      }

      setQrData(qrPayload)
      debugService.success('Edge Nodes Page', {
        message: 'QR code generated',
        token: token.substring(0, 20) + '...'
      })
      toast.success('QR Code generated! Scan to register node')
    } catch (error) {
      debugService.error('Edge Nodes Page', {
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
      console.log('🗑️ [EdgeNodesPage] Deleting node:', nodeId)
      await api.delete(`/nodes/${nodeId}`)
      toast.success('Node deleted successfully')
      loadNodes()
    } catch (error) {
      console.error('❌ [EdgeNodesPage] Delete failed:', error)
      toast.error('Failed to delete node')
    }
  }

  const openEditModal = (node) => {
    console.log('🔵 [EdgeNodesPage] Opening edit modal for node:', node)
    setEditingNode(node)
    setEditForm({
      name: node.name || '',
      location: node.location || ''
    })
  }

  const closeEditModal = () => {
    console.log('❌ [EdgeNodesPage] Closing edit modal')
    setEditingNode(null)
    setEditForm({ name: '', location: '' })
  }

  const saveNodeChanges = async () => {
    if (!editForm.name.trim()) {
      toast.error('Node name is required')
      return
    }

    try {
      console.log('💾 [EdgeNodesPage] Saving changes for node:', editingNode.id, editForm)
      await api.patch(`/nodes/${editingNode.id}`, {
        name: editForm.name,
        location: editForm.location
      })
      toast.success('Node updated successfully')
      closeEditModal()
      loadNodes()
    } catch (error) {
      console.error('❌ [EdgeNodesPage] Save failed:', error)
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

  const handleOpenTerminal = (node) => {
    console.log('🖥️ [EdgeNodesPage] Opening terminal for node:', node.name)
    setSelectedNode(node)
  }

  const handleCloseTerminal = () => {
    console.log('❌ [EdgeNodesPage] Closing terminal')
    setSelectedNode(null)
  }

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

  return (
    <div className="space-y-6">
      {/* Debug Panel */}
      <div className="fixed bottom-4 right-4 bg-slate-800 border-2 border-green-500 rounded-lg p-4 text-xs z-50 max-w-sm shadow-xl">
        <div className="text-green-400 font-bold mb-2 text-sm">🎯 EDGE NODES PAGE v1.0</div>
        <div className="text-slate-300 space-y-1">
          <div className="text-green-400">✅ Nuova pagina con Edit funzionante!</div>
          <div>📋 Nodi caricati: <span className="font-bold text-white">{safeNodes.length}</span></div>
          <div>🔵 Edit Modal: {editingNode ? 'APERTO' : 'Chiuso'}</div>
          <div>🔷 Funzione openEditModal: <span className="font-bold text-green-400">ATTIVA</span></div>
          <div className="text-yellow-400 mt-2 pt-2 border-t border-slate-600">
            Cerca nei log della console: 🔵 e 🔷
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
          <div className="bg-slate-800 rounded-xl border border-slate-700 max-w-md w-full shadow-2xl">
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
          <h1 className="text-2xl font-bold text-white mb-2">Edge Nodes Management</h1>
          <p className="text-slate-400">Manage and connect edge devices with edit capabilities</p>
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

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-slate-800 border border-slate-700 rounded-xl p-6">
          <div className="flex items-center gap-3 mb-2">
            <Server className="w-5 h-5 text-blue-400" />
            <h3 className="text-slate-400 font-medium">Total Nodes</h3>
          </div>
          <p className="text-3xl font-bold text-white">{stats.total}</p>
        </div>
        <div className="bg-slate-800 border border-slate-700 rounded-xl p-6">
          <div className="flex items-center gap-3 mb-2">
            <Wifi className="w-5 h-5 text-green-400" />
            <h3 className="text-slate-400 font-medium">Online</h3>
          </div>
          <p className="text-3xl font-bold text-green-400">{stats.online}</p>
        </div>
        <div className="bg-slate-800 border border-slate-700 rounded-xl p-6">
          <div className="flex items-center gap-3 mb-2">
            <WifiOff className="w-5 h-5 text-red-400" />
            <h3 className="text-slate-400 font-medium">Offline</h3>
          </div>
          <p className="text-3xl font-bold text-red-400">{stats.offline}</p>
        </div>
      </div>

      {/* Nodes Grid */}
      {safeNodes.length === 0 ? (
        <div className="text-center py-12">
          <Server className="w-16 h-16 text-slate-600 mx-auto mb-4" />
          <h3 className="text-xl font-semibold text-slate-400 mb-2">No nodes registered</h3>
          <p className="text-slate-500 mb-6">Get started by adding your first node</p>
          <button
            onClick={() => setShowAddModal(true)}
            className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
          >
            <Plus className="w-5 h-5" />
            Add Your First Node
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {safeNodes.map((node) => (
            <NodeCard
              key={node.id}
              node={node}
              onDelete={deleteNode}
              onEdit={openEditModal}
              onOpenTerminal={handleOpenTerminal}
            />
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

            {!qrData ? (
              <div className="p-6 space-y-6">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Node Name
                  </label>
                  <input
                    type="text"
                    value={nodeName}
                    onChange={(e) => setNodeName(e.target.value)}
                    placeholder="e.g., edge-server-01"
                    className="w-full px-4 py-3 bg-slate-700/50 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-3">
                    Select Protocols
                  </label>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
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
                  </div>
                </div>

                <button
                  onClick={generateQRCode}
                  className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors"
                >
                  Generate QR Code
                </button>
              </div>
            ) : (
              <div className="p-6 space-y-6">
                <div className="bg-white p-8 rounded-lg flex items-center justify-center">
                  <QRCodeSVG
                    id="node-qr-code"
                    value={JSON.stringify(qrData)}
                    size={256}
                    level="H"
                    includeMargin={true}
                  />
                </div>

                <div className="space-y-3">
                  <div className="bg-slate-700/50 rounded-lg p-4">
                    <p className="text-sm text-slate-400 mb-1">Node Name</p>
                    <p className="text-white font-medium">{qrData.name}</p>
                  </div>
                  <div className="bg-slate-700/50 rounded-lg p-4">
                    <p className="text-sm text-slate-400 mb-1">Protocols</p>
                    <p className="text-white font-medium">{qrData.protocols.join(', ')}</p>
                  </div>
                </div>

                <div className="flex gap-3">
                  <button
                    onClick={downloadQRCode}
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
                  >
                    <Download className="w-4 h-4" />
                    Download QR
                  </button>
                  <button
                    onClick={closeModal}
                    className="flex-1 px-4 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
                  >
                    Done
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function NodeCard({ node, onDelete, onEdit, onOpenTerminal }) {
  const isOnline = node.status === 'online'

  console.log('🔷 [NodeCard] Rendering:', node.name, 'onEdit available:', !!onEdit)

  const handleSSHAccess = () => {
    onOpenTerminal(node)
  }

  const handleEditClick = () => {
    console.log('🔵 [NodeCard] Edit clicked for:', node.name)
    if (onEdit) {
      onEdit(node)
    } else {
      console.error('❌ [NodeCard] onEdit is not defined!')
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
          <span className="text-white">{node.location || 'Unknown'}</span>
        </div>
        <div className="flex items-center justify-between text-sm">
          <span className="text-slate-400">Last Seen</span>
          <span className="text-white">{new Date(node.last_seen).toLocaleString()}</span>
        </div>
      </div>

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

export default EdgeNodesPage
