import { useState, useEffect } from 'react'
import { Monitor, Zap, Eye, EyeOff, Save, Trash2, RefreshCw } from 'lucide-react'
import api from '../services/api'
import toast from 'react-hot-toast'
import debugService from '../services/debugService'
import RDPDirectTest from '../components/RDPDirectTest'

function RDPDirectPage() {
  const [nodes, setNodes] = useState([])
  const [loading, setLoading] = useState(true)
  const [credentials, setCredentials] = useState({})
  const [showPassword, setShowPassword] = useState({})
  const [activeConnection, setActiveConnection] = useState(null)

  useEffect(() => {
    loadNodes()
    loadSavedCredentials()
  }, [])

  const loadNodes = async () => {
    try {
      debugService.info('RDP Direct Page', { message: 'Loading RDP-enabled nodes...' })
      const response = await api.get('/network/topology')
      const rdpNodes = response.data.nodes.filter(
        node => node.rdp_available === true && node.status === 'online'
      )
      setNodes(rdpNodes)
      debugService.success('RDP Direct Page', {
        message: 'RDP nodes loaded',
        count: rdpNodes.length
      })
    } catch (error) {
      debugService.error('RDP Direct Page', {
        message: 'Failed to load nodes',
        error: error.message
      })
      toast.error('Failed to load RDP nodes')
    } finally {
      setLoading(false)
    }
  }

  const loadSavedCredentials = () => {
    try {
      const saved = localStorage.getItem('rdp_credentials')
      if (saved) {
        setCredentials(JSON.parse(saved))
      }
    } catch (error) {
      console.error('Failed to load saved credentials:', error)
    }
  }

  const saveCredentials = (nodeId, username, password) => {
    const updated = {
      ...credentials,
      [nodeId]: { username, password, savedAt: new Date().toISOString() }
    }
    setCredentials(updated)
    localStorage.setItem('rdp_credentials', JSON.stringify(updated))
    toast.success('Credentials saved')
  }

  const deleteCredentials = (nodeId) => {
    const updated = { ...credentials }
    delete updated[nodeId]
    setCredentials(updated)
    localStorage.setItem('rdp_credentials', JSON.stringify(updated))
    toast.success('Credentials deleted')
  }

  const handleConnect = (node, username, password) => {
    if (!username || !password) {
      toast.error('Please enter username and password')
      return
    }

    debugService.info('RDP Direct Page', {
      message: 'Connecting to RDP',
      node: node.label,
      username
    })

    setActiveConnection({
      node,
      username,
      password
    })
  }

  const togglePasswordVisibility = (nodeId) => {
    setShowPassword(prev => ({
      ...prev,
      [nodeId]: !prev[nodeId]
    }))
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* RDP Connection Modal */}
      {activeConnection && (
        <RDPDirectTest
          nodeId={activeConnection.node.id}
          nodeName={activeConnection.node.label}
          username={activeConnection.username}
          password={activeConnection.password}
          onClose={() => setActiveConnection(null)}
        />
      )}

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white mb-2 flex items-center gap-3">
            <Zap className="w-8 h-8 text-yellow-500" />
            RDP Direct Connections
          </h1>
          <p className="text-slate-400">
            Connect to remote desktops with native RDP protocol
          </p>
        </div>
        <button
          onClick={loadNodes}
          className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {/* Info Banner */}
      <div className="bg-blue-900/20 border border-blue-800/50 rounded-lg p-4">
        <div className="flex items-start gap-3">
          <Monitor className="w-5 h-5 text-blue-400 mt-0.5" />
          <div>
            <h3 className="text-blue-300 font-medium mb-1">
              Microsoft Remote Desktop Style
            </h3>
            <p className="text-sm text-blue-400">
              Enter your credentials for each host. You can save them for quick access.
              Credentials are stored locally in your browser.
            </p>
          </div>
        </div>
      </div>

      {/* RDP Nodes Grid */}
      {nodes.length === 0 ? (
        <div className="text-center py-12 bg-slate-800 border border-slate-700 rounded-xl">
          <Monitor className="w-16 h-16 text-slate-600 mx-auto mb-4" />
          <h3 className="text-xl font-semibold text-white mb-2">No RDP hosts available</h3>
          <p className="text-slate-400 mb-4">
            No online nodes with RDP enabled found
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {nodes.map((node) => (
            <RDPHostCard
              key={node.id}
              node={node}
              savedCredentials={credentials[node.id]}
              showPassword={showPassword[node.id]}
              onTogglePassword={() => togglePasswordVisibility(node.id)}
              onSave={(username, password) => saveCredentials(node.id, username, password)}
              onDelete={() => deleteCredentials(node.id)}
              onConnect={(username, password) => handleConnect(node, username, password)}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function RDPHostCard({
  node,
  savedCredentials,
  showPassword,
  onTogglePassword,
  onSave,
  onDelete,
  onConnect
}) {
  const [username, setUsername] = useState(savedCredentials?.username || '')
  const [password, setPassword] = useState(savedCredentials?.password || '')

  useEffect(() => {
    if (savedCredentials) {
      setUsername(savedCredentials.username)
      setPassword(savedCredentials.password)
    }
  }, [savedCredentials])

  const handleSave = () => {
    if (!username || !password) {
      toast.error('Please enter both username and password')
      return
    }
    onSave(username, password)
  }

  const handleConnect = () => {
    onConnect(username, password)
  }

  const hasSavedCredentials = !!savedCredentials

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-xl p-6 hover:border-slate-600 transition-colors">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-lg bg-blue-500/20 flex items-center justify-center">
            <Monitor className="w-6 h-6 text-blue-400" />
          </div>
          <div>
            <h3 className="text-white font-semibold">{node.label}</h3>
            <p className="text-sm text-slate-400">{node.ip_address}</p>
          </div>
        </div>
        {hasSavedCredentials && (
          <button
            onClick={onDelete}
            className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
            title="Delete saved credentials"
          >
            <Trash2 className="w-4 h-4 text-red-400" />
          </button>
        )}
      </div>

      {/* Status */}
      <div className="mb-4">
        <div className="flex items-center gap-2 text-sm">
          <div className="w-2 h-2 rounded-full bg-green-500"></div>
          <span className="text-green-400">Online</span>
          {hasSavedCredentials && (
            <>
              <span className="text-slate-600">•</span>
              <span className="text-blue-400">Credentials saved</span>
            </>
          )}
        </div>
      </div>

      {/* Credentials Form */}
      <div className="space-y-3">
        {/* Username */}
        <div>
          <label className="block text-xs font-medium text-slate-400 mb-1.5">
            Username
          </label>
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="e.g., parallels"
            className="w-full px-3 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-white text-sm placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        {/* Password */}
        <div>
          <label className="block text-xs font-medium text-slate-400 mb-1.5">
            Password
          </label>
          <div className="relative">
            <input
              type={showPassword ? 'text' : 'password'}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full px-3 py-2 pr-10 bg-slate-700/50 border border-slate-600 rounded-lg text-white text-sm placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
              onClick={onTogglePassword}
              className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 hover:bg-slate-600 rounded transition-colors"
              type="button"
            >
              {showPassword ? (
                <EyeOff className="w-4 h-4 text-slate-400" />
              ) : (
                <Eye className="w-4 h-4 text-slate-400" />
              )}
            </button>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-2 pt-2">
          <button
            onClick={handleSave}
            className="flex-1 flex items-center justify-center gap-2 px-3 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors text-sm"
          >
            <Save className="w-4 h-4" />
            Save
          </button>
          <button
            onClick={handleConnect}
            disabled={!username || !password}
            className="flex-1 flex items-center justify-center gap-2 px-3 py-2 bg-yellow-600 hover:bg-yellow-700 disabled:bg-slate-700 disabled:text-slate-500 text-white rounded-lg transition-colors text-sm font-medium"
          >
            <Zap className="w-4 h-4" />
            Connect
          </button>
        </div>
      </div>
    </div>
  )
}

export default RDPDirectPage
