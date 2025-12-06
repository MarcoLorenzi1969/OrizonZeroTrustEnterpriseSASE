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
  FileCode,
  ChevronDown,
  ChevronUp,
  ShieldCheck,
  ShieldAlert,
  ShieldX,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Loader2,
  FileJson
} from 'lucide-react'
import api from '../services/api'
import toast from 'react-hot-toast'
import debugService from '../services/debugService'
import { debugReact, debugData } from '../utils/debugLogger'
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
      debugReact.render('NodesPage', 'Loading nodes from API')
      const response = await api.get('/nodes/')
      const items = response.data.nodes || response.data.items || []
      // Ensure items is always an array
      const safeItems = Array.isArray(items) ? items : []

      // Debug data structure
      debugData.received('NodesPage.loadNodes', {
        rawData: response.data,
        itemsCount: safeItems.length,
        firstNode: safeItems[0] ? {
          id: safeItems[0].id,
          name: safeItems[0].name,
          exposed_applications: safeItems[0].exposed_applications,
          application_ports: safeItems[0].application_ports
        } : null
      })

      setNodes(safeItems)
      console.log('📋 [NodesPage] Nodi caricati:', safeItems.length, safeItems)
      debugService.success('Nodes Page', {
        message: 'Nodes loaded',
        count: safeItems.length
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

  // Safely ensure nodes is always an array
  const safeNodes = Array.isArray(nodes) ? nodes : []

  // Export complete configuration
  const [exporting, setExporting] = useState(false)

  const exportConfiguration = async () => {
    if (safeNodes.length === 0) {
      toast.error('No nodes to export')
      return
    }

    setExporting(true)
    const toastId = toast.loading('Exporting configuration...')

    try {
      // Fetch hardening data for all nodes
      const nodesWithHardening = await Promise.all(
        safeNodes.map(async (node) => {
          let hardeningData = null
          try {
            const response = await api.get(`/nodes/${node.id}/hardening`)
            hardeningData = response.data
          } catch (err) {
            console.warn(`Could not fetch hardening for node ${node.id}:`, err)
          }

          return {
            // Basic Info
            id: node.id,
            name: node.name,
            hostname: node.hostname,
            status: node.status,
            created_at: node.created_at,
            updated_at: node.updated_at,

            // OS Info
            os: {
              type: node.node_type,
              reverse_tunnel_type: node.reverse_tunnel_type,
              agent_token: node.agent_token ? '***REDACTED***' : null,
            },

            // Network & Geolocation
            network: {
              public_ip: node.public_ip,
              private_ip: node.private_ip,
              location: node.location,
            },
            geolocation: {
              city: node.city,
              region: node.region,
              country: node.country,
              country_code: node.country_code,
              latitude: node.latitude,
              longitude: node.longitude,
              isp: node.isp,
              org: node.org,
            },

            // Services Configuration
            services: {
              exposed_applications: node.exposed_applications,
              application_ports: node.application_ports,
            },

            // Hardening & Security
            hardening: hardeningData ? {
              last_scan: hardeningData.last_scan,
              scan_status: hardeningData.scan_status,
              firewall: hardeningData.firewall,
              antivirus: hardeningData.antivirus,
              ssh_config: hardeningData.ssh_config,
              ssl_info: hardeningData.ssl_info,
              audit: hardeningData.audit,
              security_modules: hardeningData.security_modules,
              open_ports: hardeningData.open_ports,
            } : null,
          }
        })
      )

      // Build export object
      const exportData = {
        export_info: {
          exported_at: new Date().toISOString(),
          export_version: '1.0',
          total_nodes: nodesWithHardening.length,
          online_nodes: nodesWithHardening.filter(n => n.status === 'online').length,
          offline_nodes: nodesWithHardening.filter(n => n.status === 'offline').length,
        },
        nodes: nodesWithHardening,
      }

      // Download as JSON file
      const jsonStr = JSON.stringify(exportData, null, 2)
      const blob = new Blob([jsonStr], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `orizon-nodes-export-${new Date().toISOString().split('T')[0]}.json`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)

      toast.dismiss(toastId)
      toast.success(`Exported ${nodesWithHardening.length} nodes successfully!`)
    } catch (error) {
      console.error('Export error:', error)
      toast.dismiss(toastId)
      toast.error('Failed to export configuration')
    } finally {
      setExporting(false)
    }
  }

  // Calculate stats
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
    <div className="space-y-6 p-6">
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
            onClick={exportConfiguration}
            disabled={exporting || safeNodes.length === 0}
            className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-600 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
            title="Export all nodes configuration (OS, Network, Hardening)"
          >
            {exporting ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <FileJson className="w-4 h-4" />
            )}
            Export
          </button>
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
  const [hardeningExpanded, setHardeningExpanded] = useState(false)
  const [hardeningData, setHardeningData] = useState(null)
  const [hardeningLoading, setHardeningLoading] = useState(false)
  const [downloadingScript, setDownloadingScript] = useState(false)

  // Get exposed apps from both exposed_applications and application_ports
  const configuredApps = node.exposed_applications || []
  const portApps = node.application_ports ? Object.keys(node.application_ports) : []
  // Merge and deduplicate
  const exposedApps = [...new Set([...configuredApps, ...portApps])]

  // Check which services are available
  const hasSSL = exposedApps.includes('HTTPS') || exposedApps.includes('WEB_SERVER')
  const hasSSH = exposedApps.includes('TERMINAL')
  const hasRDP = exposedApps.includes('RDP')
  const hasVNC = exposedApps.includes('VNC')

  // Fetch hardening data
  const fetchHardeningData = async () => {
    if (hardeningData) {
      setHardeningExpanded(!hardeningExpanded)
      return
    }
    setHardeningLoading(true)
    try {
      const response = await api.get(`/nodes/${node.id}/hardening`)
      setHardeningData(response.data)
      setHardeningExpanded(true)
    } catch (error) {
      toast.error('Failed to load hardening info')
      console.error('Hardening fetch error:', error)
    } finally {
      setHardeningLoading(false)
    }
  }

  const toggleHardening = () => {
    if (hardeningData) {
      setHardeningExpanded(!hardeningExpanded)
    } else {
      fetchHardeningData()
    }
  }

  // Enhanced debug logging
  debugReact.render('NodeCard', `Rendering: ${node.name}`, {
    nodeId: node.id,
    status: node.status,
    exposed_applications: node.exposed_applications,
    application_ports: node.application_ports,
    mergedApps: exposedApps,
    flags: { hasSSL, hasSSH, hasRDP, hasVNC }
  })
  console.log(`[NodeCard] ${node.name}: exposedApps=${JSON.stringify(exposedApps)}, hasSSL=${hasSSL}, hasSSH=${hasSSH}`)

  const handleEditClick = () => {
    if (onEdit) {
      onEdit(node)
    }
  }

  const handleServiceConnect = async (service) => {
    if (service === 'TERMINAL') {
      onOpenTerminal(node)
    } else if (service === 'HTTPS' || service === 'WEB_SERVER') {
      try {
        toast.loading('Generating secure access token...')
        const response = await api.post(`/nodes/${node.id}/https-proxy-token`)
        const { proxy_token } = response.data
        toast.dismiss()
        const proxyUrl = `/api/v1/nodes/${node.id}/https-proxy?t=${proxy_token}`
        window.open(proxyUrl, '_blank', 'noopener,noreferrer')
        toast.success('Opening secure HTTPS connection...')
      } catch (error) {
        toast.dismiss()
        toast.error(error.response?.data?.detail || 'Failed to generate access token')
      }
    } else {
      const ports = node.application_ports || {}
      const portInfo = ports[service] || {}
      toast(`${service} connection: Remote port ${portInfo.remote || 'N/A'}`)
    }
  }

  // Download OS-specific installation script
  const downloadNodeScript = async () => {
    const osType = node.node_type || 'linux'
    setDownloadingScript(true)

    try {
      const response = await api.get(`/nodes/${node.id}/install-script/${osType}`, {
        responseType: 'text'
      })
      const script = response.data

      const extension = osType === 'windows' ? '.ps1' : '.sh'
      const mimeType = osType === 'windows' ? 'application/x-powershell' : 'application/x-sh'
      // Sanitize filename - replace spaces and special chars with underscores
      const safeName = node.name.replace(/[^\w\-]/g, '_')
      const blob = new Blob([script], { type: mimeType })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `orizon-install-${safeName}${extension}`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)

      toast.success(`${osType} installation script downloaded!`)
    } catch (error) {
      console.error('Error downloading script:', error)
      toast.error('Failed to download installation script')
    } finally {
      setDownloadingScript(false)
    }
  }

  // Get OS icon for node type
  const getOsIcon = () => {
    const osType = node.node_type || 'linux'
    switch (osType) {
      case 'windows': return Server
      case 'macos': return Monitor
      default: return Terminal
    }
  }
  const OsIcon = getOsIcon()

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-xl overflow-hidden hover:border-slate-600 transition-colors">
      {/* Header with status indicator */}
      <div className={`h-1 ${isOnline ? 'bg-green-500' : 'bg-slate-600'}`} />

      <div className="p-5">
        {/* Node name and info */}
        <div className="flex items-start justify-between mb-3">
          <div>
            <h3 className="text-white font-bold text-lg">{node.name}</h3>
            <p className="text-sm text-slate-400">
              {node.private_ip || node.public_ip || 'No IP'} • {node.node_type || 'linux'}
            </p>
          </div>
          <div className={`px-2 py-1 rounded text-xs font-medium ${
            isOnline ? 'bg-green-500/20 text-green-400' : 'bg-slate-600 text-slate-400'
          }`}>
            {isOnline ? 'Online' : 'Offline'}
          </div>
        </div>

        {/* Service Flags */}
        <div className="flex flex-wrap gap-2 mb-4">
          {hasSSL && (
            <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-cyan-500/20 border border-cyan-500/50 rounded-lg text-cyan-400 text-sm font-medium">
              <Lock className="w-3.5 h-3.5" />
              SSL
            </span>
          )}
          {hasSSH && (
            <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-green-500/20 border border-green-500/50 rounded-lg text-green-400 text-sm font-medium">
              <Terminal className="w-3.5 h-3.5" />
              SSH
            </span>
          )}
          {hasRDP && (
            <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-blue-500/20 border border-blue-500/50 rounded-lg text-blue-400 text-sm font-medium">
              <Monitor className="w-3.5 h-3.5" />
              RDP
            </span>
          )}
          {hasVNC && (
            <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-purple-500/20 border border-purple-500/50 rounded-lg text-purple-400 text-sm font-medium">
              <Monitor className="w-3.5 h-3.5" />
              VNC
            </span>
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex gap-2">
          {hasSSH && (
            <button
              onClick={() => isOnline && handleServiceConnect('TERMINAL')}
              disabled={!isOnline}
              className={`flex-1 flex items-center justify-center gap-2 px-3 py-2 text-white text-sm font-medium rounded-lg transition-colors ${
                isOnline
                  ? 'bg-green-600 hover:bg-green-700 cursor-pointer'
                  : 'bg-green-600/40 cursor-not-allowed'
              }`}
              title={isOnline ? 'Open terminal' : 'Node offline - install agent first'}
            >
              <Terminal className="w-4 h-4" />
              Terminal
            </button>
          )}
          {hasSSL && (
            <button
              onClick={() => isOnline && handleServiceConnect('HTTPS')}
              disabled={!isOnline}
              className={`flex-1 flex items-center justify-center gap-2 px-3 py-2 text-white text-sm font-medium rounded-lg transition-colors ${
                isOnline
                  ? 'bg-cyan-600 hover:bg-cyan-700 cursor-pointer'
                  : 'bg-cyan-600/40 cursor-not-allowed'
              }`}
              title={isOnline ? 'Open web interface' : 'Node offline - install agent first'}
            >
              <Globe className="w-4 h-4" />
              Web
            </button>
          )}
          {!hasSSH && !hasSSL && (
            <div className="flex-1 text-center py-2 text-sm text-slate-500">
              No services configured
            </div>
          )}
        </div>

        {/* Security/Hardening Button */}
        <button
          onClick={toggleHardening}
          className="w-full mt-3 flex items-center justify-between px-3 py-2 bg-slate-700/50 hover:bg-slate-700 border border-slate-600 rounded-lg transition-colors"
        >
          <div className="flex items-center gap-2">
            {hardeningLoading ? (
              <Loader2 className="w-4 h-4 text-slate-400 animate-spin" />
            ) : hardeningData?.scan_status === 'completed' ? (
              <ShieldCheck className="w-4 h-4 text-green-400" />
            ) : hardeningData?.scan_status === 'stale' ? (
              <ShieldAlert className="w-4 h-4 text-yellow-400" />
            ) : (
              <Shield className="w-4 h-4 text-slate-400" />
            )}
            <span className="text-sm text-slate-300">Security Info</span>
          </div>
          {hardeningExpanded ? (
            <ChevronUp className="w-4 h-4 text-slate-400" />
          ) : (
            <ChevronDown className="w-4 h-4 text-slate-400" />
          )}
        </button>

        {/* Hardening Dropdown Content */}
        {hardeningExpanded && hardeningData && (
          <div className="mt-2 p-3 bg-slate-900/50 border border-slate-700 rounded-lg space-y-3 text-sm">
            {/* Scan Status */}
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-500">Last Scan:</span>
              <span className={`${
                hardeningData.scan_status === 'completed' ? 'text-green-400' :
                hardeningData.scan_status === 'stale' ? 'text-yellow-400' : 'text-slate-500'
              }`}>
                {hardeningData.last_scan
                  ? new Date(hardeningData.last_scan).toLocaleString()
                  : 'Never scanned'}
              </span>
            </div>

            {/* Firewall */}
            <HardeningRow
              label="Firewall"
              status={hardeningData.firewall?.enabled}
              detail={hardeningData.firewall?.default_policy || (hardeningData.firewall?.profiles ? 'Active profiles' : null)}
            />

            {/* Antivirus */}
            <HardeningRow
              label="Antivirus"
              status={hardeningData.antivirus?.enabled}
              detail={hardeningData.antivirus?.product_name || (hardeningData.antivirus?.real_time_protection ? 'Real-time ON' : null)}
            />

            {/* SSH Config (Linux only) */}
            {hardeningData.ssh_config && (
              <HardeningRow
                label="SSH Hardening"
                status={hardeningData.ssh_config?.root_login === 'no'}
                detail={`Root: ${hardeningData.ssh_config?.root_login || 'N/A'}, Port: ${hardeningData.ssh_config?.port || 22}`}
              />
            )}

            {/* Security Modules */}
            {hardeningData.security_modules && hardeningData.security_modules.length > 0 && (
              <div className="flex items-start justify-between">
                <span className="text-slate-400">Security Modules:</span>
                <div className="text-right">
                  {hardeningData.security_modules.map((mod, i) => (
                    <div key={i} className={`${mod.status === 'loaded' || mod.status === 'enabled' || mod.status === 'enforcing' ? 'text-green-400' : 'text-yellow-400'}`}>
                      {mod.name} ({mod.status})
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Open Ports */}
            {hardeningData.open_ports && hardeningData.open_ports.length > 0 && (
              <div className="flex items-start justify-between">
                <span className="text-slate-400">Open Ports:</span>
                <div className="text-right text-slate-300">
                  {hardeningData.open_ports.slice(0, 5).map((port, i) => (
                    <span key={i} className="inline-block px-1.5 py-0.5 bg-slate-700 rounded text-xs mr-1 mb-1">
                      {port.port}/{port.protocol}
                    </span>
                  ))}
                  {hardeningData.open_ports.length > 5 && (
                    <span className="text-slate-500 text-xs">+{hardeningData.open_ports.length - 5} more</span>
                  )}
                </div>
              </div>
            )}

            {/* SSL Info */}
            {hardeningData.ssl_info?.openssl_version && (
              <HardeningRow
                label="OpenSSL"
                status={true}
                detail={hardeningData.ssl_info.openssl_version}
              />
            )}

            {/* Audit */}
            {hardeningData.audit && (
              <HardeningRow
                label="Audit Logging"
                status={hardeningData.audit?.enabled}
                detail={hardeningData.audit?.service_name}
              />
            )}

            {/* No data message */}
            {hardeningData.scan_status === 'never' && (
              <div className="text-center py-2 text-slate-500 text-xs">
                <AlertTriangle className="w-4 h-4 mx-auto mb-1 text-yellow-500" />
                No hardening data collected yet.
                <br />Agent needs to report security info.
              </div>
            )}
          </div>
        )}

        {/* Bottom actions */}
        <div className="flex items-center justify-between mt-4 pt-3 border-t border-slate-700">
          <div className="flex gap-1">
            <button
              onClick={downloadNodeScript}
              disabled={downloadingScript}
              className="p-2 hover:bg-green-700/30 rounded-lg transition-colors group relative"
              title={`Download ${node.node_type || 'linux'} installation script`}
            >
              {downloadingScript ? (
                <Loader2 className="w-4 h-4 text-green-400 animate-spin" />
              ) : (
                <Download className="w-4 h-4 text-green-400" />
              )}
              <span className="absolute -top-8 left-1/2 -translate-x-1/2 bg-slate-700 text-white text-xs px-2 py-1 rounded whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
                {(node.node_type || 'linux').toUpperCase()} Script
              </span>
            </button>
            <button
              onClick={() => onViewScripts && onViewScripts(node)}
              className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
              title="View all installation scripts"
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
          </div>
          <button
            onClick={() => onDelete(node.id)}
            className="p-2 hover:bg-red-500/20 rounded-lg transition-colors"
            title="Delete node"
          >
            <Trash2 className="w-4 h-4 text-red-400" />
          </button>
        </div>
      </div>
    </div>
  )
}

// Helper component for hardening rows
function HardeningRow({ label, status, detail }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-slate-400">{label}:</span>
      <div className="flex items-center gap-2">
        {detail && <span className="text-slate-300 text-xs">{detail}</span>}
        {status === true ? (
          <CheckCircle className="w-4 h-4 text-green-400" />
        ) : status === false ? (
          <XCircle className="w-4 h-4 text-red-400" />
        ) : (
          <span className="text-slate-500 text-xs">N/A</span>
        )}
      </div>
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
// Build v2.0 - Node cards with SSL/SSH/RDP/VNC flags - 20251129
