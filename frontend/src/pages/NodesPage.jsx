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
  Save,
  Monitor,
  Copy,
  Check,
  FileCode
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
  const [showScriptsModal, setShowScriptsModal] = useState(false)
  const [scriptsData, setScriptsData] = useState(null)
  const [copiedScript, setCopiedScript] = useState(null)

  // Form state for new node (updated with reverse tunnel config)
  const [nodeName, setNodeName] = useState('')
  const [nodeHostname, setNodeHostname] = useState('')
  const [nodeType, setNodeType] = useState('linux')
  const [reverseTunnelType, setReverseTunnelType] = useState('SSH')
  const [exposedApplications, setExposedApplications] = useState({
    TERMINAL: true,
    RDP: false,
    VNC: false,
    WEB_SERVER: false
  })
  // Legacy protocols (keeping for backward compatibility)
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
      const response = await api.get('/nodes/')
      const items = response.data.nodes || response.data.items || []
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

  const handleApplicationToggle = (app) => {
    setExposedApplications(prev => ({
      ...prev,
      [app]: !prev[app]
    }))
  }

  // Create new node with reverse tunnel config
  const createNode = async () => {
    if (!nodeName.trim()) {
      toast.error('Please enter a node name')
      return
    }
    if (!nodeHostname.trim()) {
      toast.error('Please enter a hostname')
      return
    }

    const selectedApps = Object.keys(exposedApplications).filter(app => exposedApplications[app])
    if (selectedApps.length === 0) {
      toast.error('Please select at least one application to expose')
      return
    }

    try {
      debugService.info('Nodes Page', {
        message: 'Creating new node...',
        nodeName,
        nodeType,
        reverseTunnelType,
        exposedApplications: selectedApps
      })

      const response = await api.post('/nodes/', {
        name: nodeName,
        hostname: nodeHostname,
        node_type: nodeType,
        reverse_tunnel_type: reverseTunnelType,
        exposed_applications: selectedApps
      })

      const newNode = response.data
      debugService.success('Nodes Page', {
        message: 'Node created successfully',
        nodeId: newNode.id,
        agentToken: newNode.agent_token ? newNode.agent_token.substring(0, 20) + '...' : 'N/A'
      })

      toast.success('Node created successfully!')

      // Show scripts modal with the new node data
      setScriptsData({
        node: newNode,
        scripts: null // Will be fetched on demand
      })
      setShowScriptsModal(true)
      setShowAddModal(false)
      loadNodes()
    } catch (error) {
      debugService.error('Nodes Page', {
        message: 'Failed to create node',
        error: error.response?.data?.detail || error.message
      })
      toast.error(error.response?.data?.detail || 'Failed to create node')
    }
  }

  // Fetch installation scripts for a node
  const fetchScripts = async (node) => {
    try {
      setScriptsData({ node, scripts: null, loading: true })
      setShowScriptsModal(true)

      const response = await api.get(`/nodes/${node.id}/install-scripts`)
      setScriptsData({
        node,
        scripts: response.data.scripts,
        loading: false
      })
    } catch (error) {
      debugService.error('Nodes Page', {
        message: 'Failed to fetch scripts',
        error: error.message
      })
      toast.error('Failed to fetch installation scripts')
      setScriptsData({ node, scripts: null, loading: false, error: error.message })
    }
  }

  // Copy script to clipboard
  const copyScript = async (osType, script) => {
    try {
      await navigator.clipboard.writeText(script)
      setCopiedScript(osType)
      toast.success(`${osType} script copied to clipboard!`)
      setTimeout(() => setCopiedScript(null), 2000)
    } catch (error) {
      toast.error('Failed to copy script')
    }
  }

  // Download script as file
  const downloadScript = (osType, script, nodeName) => {
    const extension = osType === 'windows' ? '.ps1' : '.sh'
    const mimeType = osType === 'windows' ? 'application/x-powershell' : 'application/x-sh'
    const blob = new Blob([script], { type: mimeType })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `orizon-install-${nodeName}${extension}`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
    toast.success(`${osType} script downloaded!`)
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
    setNodeHostname('')
    setNodeType('linux')
    setReverseTunnelType('SSH')
    setExposedApplications({
      TERMINAL: true,
      RDP: false,
      VNC: false,
      WEB_SERVER: false
    })
    setProtocols({
      ssh: true,
      https: true,
      http: false,
      vpn: false,
      rdp: false
    })
  }

  const closeScriptsModal = () => {
    setShowScriptsModal(false)
    setScriptsData(null)
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
            <NodeCard
              key={node.id}
              node={node}
              onDelete={deleteNode}
              onEdit={openEditModal}
              onOpenTerminal={handleOpenTerminal}
              onViewScripts={fetchScripts}
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

            <div className="p-6 space-y-6">
              {/* Node Name */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Node Name *
                </label>
                <input
                  type="text"
                  value={nodeName}
                  onChange={(e) => setNodeName(e.target.value)}
                  placeholder="e.g., web-server-01"
                  className="w-full px-4 py-3 bg-slate-700/50 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              {/* Hostname */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Hostname *
                </label>
                <input
                  type="text"
                  value={nodeHostname}
                  onChange={(e) => setNodeHostname(e.target.value)}
                  placeholder="e.g., server.example.com or 192.168.1.100"
                  className="w-full px-4 py-3 bg-slate-700/50 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              {/* Node Type / OS */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Operating System
                </label>
                <div className="grid grid-cols-3 gap-3">
                  {[
                    { value: 'linux', label: 'Linux', icon: Terminal },
                    { value: 'macos', label: 'macOS', icon: Monitor },
                    { value: 'windows', label: 'Windows', icon: Server },
                  ].map((os) => (
                    <button
                      key={os.value}
                      onClick={() => setNodeType(os.value)}
                      className={`flex flex-col items-center gap-2 p-4 rounded-lg border-2 transition-all ${
                        nodeType === os.value
                          ? 'border-blue-500 bg-blue-500/10'
                          : 'border-slate-600 bg-slate-700/50 hover:border-slate-500'
                      }`}
                    >
                      <os.icon className={`w-6 h-6 ${nodeType === os.value ? 'text-blue-400' : 'text-slate-400'}`} />
                      <span className={`text-sm font-medium ${nodeType === os.value ? 'text-white' : 'text-slate-300'}`}>
                        {os.label}
                      </span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Reverse Tunnel Type */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Reverse Tunnel Type
                </label>
                <div className="grid grid-cols-2 gap-3">
                  {[
                    { value: 'SSH', label: 'SSH Tunnel', desc: 'Secure Shell tunnel (recommended)' },
                    { value: 'SSL', label: 'SSL/TLS Tunnel', desc: 'HTTPS-based secure tunnel' },
                  ].map((tunnel) => (
                    <button
                      key={tunnel.value}
                      onClick={() => setReverseTunnelType(tunnel.value)}
                      className={`flex flex-col items-start gap-1 p-4 rounded-lg border-2 transition-all text-left ${
                        reverseTunnelType === tunnel.value
                          ? 'border-blue-500 bg-blue-500/10'
                          : 'border-slate-600 bg-slate-700/50 hover:border-slate-500'
                      }`}
                    >
                      <span className={`font-medium ${reverseTunnelType === tunnel.value ? 'text-white' : 'text-slate-300'}`}>
                        {tunnel.label}
                      </span>
                      <span className="text-xs text-slate-400">{tunnel.desc}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Exposed Applications */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-3">
                  Applications to Expose *
                </label>
                <div className="grid grid-cols-2 gap-3">
                  <ApplicationCheckbox
                    icon={Terminal}
                    label="Terminal"
                    port="22"
                    checked={exposedApplications.TERMINAL}
                    onChange={() => handleApplicationToggle('TERMINAL')}
                  />
                  <ApplicationCheckbox
                    icon={Monitor}
                    label="RDP"
                    port="3389"
                    checked={exposedApplications.RDP}
                    onChange={() => handleApplicationToggle('RDP')}
                  />
                  <ApplicationCheckbox
                    icon={Server}
                    label="VNC"
                    port="5900"
                    checked={exposedApplications.VNC}
                    onChange={() => handleApplicationToggle('VNC')}
                  />
                  <ApplicationCheckbox
                    icon={Globe}
                    label="Web Server"
                    port="80/443"
                    checked={exposedApplications.WEB_SERVER}
                    onChange={() => handleApplicationToggle('WEB_SERVER')}
                  />
                </div>
              </div>

              {/* Summary */}
              <div className="bg-slate-700/30 border border-slate-600 rounded-lg p-4">
                <h4 className="text-sm font-medium text-slate-300 mb-2">Configuration Summary</h4>
                <div className="text-sm text-slate-400 space-y-1">
                  <p>OS: <span className="text-white">{nodeType}</span></p>
                  <p>Tunnel: <span className="text-white">{reverseTunnelType}</span></p>
                  <p>Applications: <span className="text-white">
                    {Object.keys(exposedApplications).filter(a => exposedApplications[a]).join(', ') || 'None selected'}
                  </span></p>
                </div>
              </div>

              {/* Create Button */}
              <button
                onClick={createNode}
                className="w-full px-4 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors flex items-center justify-center gap-2"
              >
                <Plus className="w-5 h-5" />
                Create Node
              </button>

              {/* QR Code Option (Legacy) */}
              <div className="border-t border-slate-700 pt-4">
                <p className="text-sm text-slate-400 text-center mb-3">Or use QR code for mobile setup</p>
                <button
                  onClick={generateQRCode}
                  className="w-full px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors text-sm"
                >
                  Generate QR Code
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Installation Scripts Modal */}
      {showScriptsModal && scriptsData && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-800 rounded-xl border border-slate-700 max-w-4xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-slate-700 flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold text-white">Installation Scripts</h2>
                <p className="text-slate-400 text-sm mt-1">Node: {scriptsData.node?.name}</p>
              </div>
              <button
                onClick={closeScriptsModal}
                className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
              >
                <X className="w-5 h-5 text-slate-400" />
              </button>
            </div>

            <div className="p-6 space-y-6">
              {/* Node Info */}
              <div className="bg-green-900/20 border border-green-800/50 rounded-lg p-4">
                <h4 className="text-green-300 font-medium mb-2">Node Created Successfully!</h4>
                <div className="text-sm text-green-400 space-y-1">
                  <p>Node ID: <span className="font-mono">{scriptsData.node?.id}</span></p>
                  <p>Agent Token: <span className="font-mono">{scriptsData.node?.agent_token?.substring(0, 30)}...</span></p>
                  <p>Tunnel Type: {scriptsData.node?.reverse_tunnel_type}</p>
                  <p>Applications: {scriptsData.node?.exposed_applications?.join(', ')}</p>
                </div>
              </div>

              {/* Instructions */}
              <div className="bg-blue-900/20 border border-blue-800/50 rounded-lg p-4">
                <h4 className="text-blue-300 font-medium mb-2">Installation Instructions</h4>
                <ol className="text-sm text-blue-400 space-y-1 list-decimal list-inside">
                  <li>Download the script for your operating system</li>
                  <li>Run the script with administrator/root privileges</li>
                  <li>The agent will automatically connect to the hub</li>
                  <li>Verify the node status in this dashboard</li>
                </ol>
              </div>

              {/* Script Download Buttons */}
              <div className="grid grid-cols-3 gap-4">
                <ScriptDownloadCard
                  osType="linux"
                  icon={Terminal}
                  label="Linux"
                  description="For Ubuntu, Debian, CentOS, RHEL"
                  node={scriptsData.node}
                  onDownload={downloadScript}
                  onCopy={copyScript}
                  copied={copiedScript === 'linux'}
                />
                <ScriptDownloadCard
                  osType="macos"
                  icon={Monitor}
                  label="macOS"
                  description="For macOS 10.15+"
                  node={scriptsData.node}
                  onDownload={downloadScript}
                  onCopy={copyScript}
                  copied={copiedScript === 'macos'}
                />
                <ScriptDownloadCard
                  osType="windows"
                  icon={Server}
                  label="Windows"
                  description="For Windows 10/11, Server 2016+"
                  node={scriptsData.node}
                  onDownload={downloadScript}
                  onCopy={copyScript}
                  copied={copiedScript === 'windows'}
                />
              </div>

              {/* Close Button */}
              <button
                onClick={closeScriptsModal}
                className="w-full px-4 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors"
              >
                Done
              </button>
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

function NodeCard({ node, onDelete, onEdit, onOpenTerminal, onViewScripts }) {
  const isOnline = node.status === 'online'
  const tunnelType = node.reverse_tunnel_type || 'SSH'

  // Get exposed apps from both exposed_applications and application_ports
  const configuredApps = node.exposed_applications || []
  const portApps = node.application_ports ? Object.keys(node.application_ports) : []
  // Merge and deduplicate
  const exposedApps = [...new Set([...configuredApps, ...portApps])]

  const handleSSHAccess = () => {
    onOpenTerminal(node)
  }

  const handleEditClick = () => {
    if (onEdit) {
      onEdit(node)
    }
  }

  const handleServiceConnect = async (service) => {
    // Per ora apre il terminale per SSH, per altri servizi mostra info
    if (service === 'TERMINAL') {
      onOpenTerminal(node)
    } else if (service === 'HTTPS') {
      // Generate one-time proxy token and open in new window
      try {
        toast.loading('Generating secure access token...')
        const response = await api.post(`/nodes/${node.id}/https-proxy-token`)
        const { proxy_token } = response.data
        toast.dismiss()

        // Open with short opaque token (not JWT)
        const proxyUrl = `/api/v1/nodes/${node.id}/https-proxy?t=${proxy_token}`
        window.open(proxyUrl, '_blank', 'noopener,noreferrer')
        toast.success('Opening secure HTTPS connection...')
      } catch (error) {
        toast.dismiss()
        toast.error(error.response?.data?.detail || 'Failed to generate access token')
      }
    } else {
      // Placeholder per connessioni VNC, RDP, Web
      const ports = node.application_ports || {}
      const portInfo = ports[service] || {}
      toast(`${service} connection: Remote port ${portInfo.remote || 'N/A'}`)
    }
  }

  // Icone per le applicazioni
  const appIcons = {
    TERMINAL: Terminal,
    RDP: Monitor,
    VNC: Monitor,
    WEB_SERVER: Globe,
    HTTPS: Lock
  }

  const appLabels = {
    TERMINAL: 'SSH',
    RDP: 'RDP',
    VNC: 'VNC',
    WEB_SERVER: 'Web',
    HTTPS: 'HTTPS'
  }

  const appColors = {
    TERMINAL: 'bg-green-600 hover:bg-green-700',
    RDP: 'bg-blue-600 hover:bg-blue-700',
    VNC: 'bg-purple-600 hover:bg-purple-700',
    WEB_SERVER: 'bg-orange-600 hover:bg-orange-700',
    HTTPS: 'bg-cyan-600 hover:bg-cyan-700'
  }

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-xl p-6 hover:border-slate-600 transition-colors">
      {/* Header */}
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
            <p className="text-sm text-slate-400">{node.hostname || node.ip_address}</p>
          </div>
        </div>
        <div className="flex gap-1">
          <button
            onClick={() => onViewScripts && onViewScripts(node)}
            className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
            title="View installation scripts"
          >
            <FileCode className="w-4 h-4 text-slate-400" />
          </button>
          <button
            onClick={handleEditClick}
            className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
            title="Edit node"
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

      {/* Node Info */}
      <div className="space-y-2 mb-4">
        <div className="flex items-center justify-between text-sm">
          <span className="text-slate-400">Status</span>
          <span className={`font-medium ${isOnline ? 'text-green-400' : 'text-slate-500'}`}>
            {isOnline ? 'Online' : 'Offline'}
          </span>
        </div>
        <div className="flex items-center justify-between text-sm">
          <span className="text-slate-400">Tunnel</span>
          <span className={`px-2 py-0.5 rounded text-xs font-medium ${
            tunnelType === 'SSH' ? 'bg-green-500/20 text-green-400' : 'bg-blue-500/20 text-blue-400'
          }`}>
            {tunnelType}
          </span>
        </div>
        <div className="flex items-center justify-between text-sm">
          <span className="text-slate-400">OS</span>
          <span className="text-white capitalize">{node.node_type || 'linux'}</span>
        </div>
        {node.location && (
          <div className="flex items-center justify-between text-sm">
            <span className="text-slate-400">Location</span>
            <span className="text-white">{node.location}</span>
          </div>
        )}
      </div>

      {/* Exposed Applications */}
      {exposedApps.length > 0 && (
        <div className="mb-4">
          <p className="text-xs text-slate-400 mb-2">Exposed Services</p>
          <div className="flex flex-wrap gap-1">
            {exposedApps.map((app) => {
              const IconComponent = appIcons[app] || Server
              return (
                <span
                  key={app}
                  className="inline-flex items-center gap-1 px-2 py-1 bg-slate-700/50 rounded text-xs text-slate-300"
                >
                  <IconComponent className="w-3 h-3" />
                  {appLabels[app] || app}
                </span>
              )
            })}
          </div>
        </div>
      )}

      {/* Action Buttons */}
      {isOnline && exposedApps.length > 0 ? (
        <div className="grid grid-cols-2 gap-2">
          {exposedApps.map((app) => {
            const IconComponent = appIcons[app] || Server
            return (
              <button
                key={app}
                onClick={() => handleServiceConnect(app)}
                className={`flex items-center justify-center gap-1.5 px-3 py-2 text-white text-sm rounded-lg transition-colors ${appColors[app] || 'bg-slate-600 hover:bg-slate-500'}`}
              >
                <IconComponent className="w-4 h-4" />
                {appLabels[app] || app}
              </button>
            )
          })}
        </div>
      ) : isOnline ? (
        <button
          onClick={handleSSHAccess}
          className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
        >
          <Terminal className="w-4 h-4" />
          SSH Access
        </button>
      ) : (
        <div className="text-center py-2 text-sm text-slate-500">
          Node offline
        </div>
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

function ApplicationCheckbox({ icon: Icon, label, port, checked, onChange }) {
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

function ScriptDownloadCard({ osType, icon: Icon, label, description, node, onDownload, onCopy, copied }) {
  const [loading, setLoading] = useState(false)
  const [script, setScript] = useState(null)

  const fetchScript = async () => {
    if (script) return script
    setLoading(true)
    try {
      const response = await api.get(`/nodes/${node.id}/install-script/${osType}`, {
        responseType: 'text'
      })
      const text = response.data
      setScript(text)
      return text
    } catch (error) {
      console.error('Error fetching script:', error)
      return null
    } finally {
      setLoading(false)
    }
  }

  const handleDownload = async () => {
    const scriptContent = await fetchScript()
    if (scriptContent) {
      onDownload(osType, scriptContent, node.name)
    }
  }

  const handleCopy = async () => {
    const scriptContent = await fetchScript()
    if (scriptContent) {
      onCopy(osType, scriptContent)
    }
  }

  return (
    <div className="bg-slate-700/30 border border-slate-600 rounded-lg p-4 flex flex-col">
      <div className="flex items-center gap-3 mb-3">
        <div className="w-12 h-12 bg-slate-600 rounded-lg flex items-center justify-center">
          <Icon className="w-6 h-6 text-slate-300" />
        </div>
        <div>
          <h4 className="text-white font-medium">{label}</h4>
          <p className="text-xs text-slate-400">{description}</p>
        </div>
      </div>
      <div className="flex gap-2 mt-auto">
        <button
          onClick={handleDownload}
          disabled={loading}
          className="flex-1 flex items-center justify-center gap-1 px-3 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-600 text-white text-sm rounded-lg transition-colors"
        >
          <Download className="w-4 h-4" />
          {loading ? 'Loading...' : 'Download'}
        </button>
        <button
          onClick={handleCopy}
          disabled={loading}
          className="flex items-center justify-center gap-1 px-3 py-2 bg-slate-600 hover:bg-slate-500 disabled:bg-slate-700 text-white text-sm rounded-lg transition-colors"
        >
          {copied ? <Check className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4" />}
        </button>
      </div>
    </div>
  )
}

export default NodesPage
// Build $(date +%s)
