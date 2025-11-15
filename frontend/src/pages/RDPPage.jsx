/**
 * RDP Remote Desktop Page - FIXED VERSION
 * Web-based RDP remote desktop access
 * For: Marco @ Syneto/Orizon
 */

import { useEffect, useRef, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { FiX, FiMaximize2, FiMinimize2, FiAlertCircle, FiMonitor, FiTerminal, FiRefreshCw } from 'react-icons/fi'
import { toast } from 'react-toastify'

export default function RDPPage() {
  const { nodeId } = useParams()
  const navigate = useNavigate()
  const canvasRef = useRef(null)
  const wsRef = useRef(null)
  const [connected, setConnected] = useState(false)
  const [error, setError] = useState(null)
  const [fullscreen, setFullscreen] = useState(false)
  const [loading, setLoading] = useState(false) // FIX: Start as false, not true
  const [nodeName, setNodeName] = useState('')
  const [credentials, setCredentials] = useState({ username: '', password: '' })
  const [showCredentials, setShowCredentials] = useState(true)
  const [debugMode, setDebugMode] = useState(false)
  const [debugLogs, setDebugLogs] = useState([])
  const [stats, setStats] = useState({
    messagesReceived: 0,
    framesReceived: 0,
    bytesReceived: 0,
    lastFrameTime: null,
    lastMessageType: null
  })

  useEffect(() => {
    if (!nodeId) {
      setError('No node ID provided')
      return
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [nodeId])

  const addDebugLog = (type, message, data = null) => {
    const timestamp = new Date().toISOString().split('T')[1].split('.')[0]
    const logEntry = {
      timestamp,
      type,
      message,
      data: data ? JSON.stringify(data).substring(0, 100) : null
    }
    setDebugLogs(prev => [...prev.slice(-50), logEntry]) // Keep last 50 logs
    console.log(`[RDP DEBUG ${timestamp}] ${type}:`, message, data)
  }

  const connectRDP = async () => {
    try {
      setLoading(true)
      setError(null)

      // Get token from localStorage
      const token = localStorage.getItem('access_token')
      if (!token) {
        setError('Not authenticated')
        setLoading(false)
        navigate('/login')
        return
      }

      // Construct WebSocket URL
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const host = import.meta.env.VITE_API_URL
        ? import.meta.env.VITE_API_URL.replace(/^https?:\/\//, '')
        : window.location.host
      const wsUrl = `${protocol}//${host}/api/v1/rdp/${nodeId}/connect`

      console.log('[RDP] Connecting to:', wsUrl)

      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onopen = () => {
        console.log('[RDP] WebSocket connected')
        addDebugLog('WEBSOCKET', 'WebSocket connected', { url: wsUrl })

        // Send auth message with credentials
        const authMsg = {
          type: 'auth',
          token: token,
          username: credentials.username,
          password: credentials.password
        }
        ws.send(JSON.stringify(authMsg))
        addDebugLog('AUTH', 'Auth message sent', { username: credentials.username })
      }

      ws.onmessage = async (event) => {
        try {
          setStats(prev => ({
            ...prev,
            messagesReceived: prev.messagesReceived + 1,
            lastMessageType: 'checking...'
          }))

          // Handle binary data (RDP frames)
          if (event.data instanceof Blob) {
            const size = event.data.size
            addDebugLog('BLOB', `Binary blob received: ${size} bytes`)
            setStats(prev => ({
              ...prev,
              framesReceived: prev.framesReceived + 1,
              bytesReceived: prev.bytesReceived + size,
              lastFrameTime: new Date().toISOString(),
              lastMessageType: 'binary blob'
            }))

            const arrayBuffer = await event.data.arrayBuffer()
            const dataArray = new Uint8Array(arrayBuffer)
            handleRDPFrame(dataArray)
            return
          }

          // Handle text messages
          const message = JSON.parse(event.data)
          console.log('[RDP] Message:', message.type)
          addDebugLog('MESSAGE', `Text message: ${message.type}`, message)

          setStats(prev => ({
            ...prev,
            lastMessageType: message.type
          }))

          switch (message.type) {
            case 'session_id':
              console.log('[RDP] Session ID:', message.session_id)
              addDebugLog('SESSION', `Session ID received: ${message.session_id}`)
              setShowCredentials(false) // Hide credentials form
              setLoading(false) // Enable interactions
              break

            case 'connected':
              console.log('[RDP] RDP connected')
              addDebugLog('CONNECTED', 'RDP connection established')
              setConnected(true)
              setLoading(false)
              toast.success('Connected to remote desktop')
              break

            case 'frame':
              // Handle frame data
              const frameSize = message.data ? message.data.length : 0
              addDebugLog('FRAME', `Frame data in message: ${frameSize} chars`)
              setStats(prev => ({
                ...prev,
                framesReceived: prev.framesReceived + 1,
                bytesReceived: prev.bytesReceived + frameSize,
                lastFrameTime: new Date().toISOString()
              }))
              handleRDPFrame(message.data)
              break

            case 'error':
              console.error('[RDP] Error:', message.message)
              addDebugLog('ERROR', message.message, message)
              setError(message.message)
              setLoading(false)
              toast.error(message.message)
              break

            case 'disconnected':
              console.log('[RDP] Disconnected')
              addDebugLog('DISCONNECTED', 'Connection closed by server')
              setConnected(false)
              setLoading(false)
              toast.info('Disconnected from remote desktop')
              break

            default:
              console.log('[RDP] Unknown message type:', message.type)
              addDebugLog('UNKNOWN', `Unknown message type: ${message.type}`, message)
          }
        } catch (error) {
          console.error('[RDP] Error processing message:', error)
          addDebugLog('ERROR', `Processing error: ${error.message}`, { error: error.toString() })
        }
      }

      ws.onerror = (error) => {
        console.error('[RDP] WebSocket error:', error)
        setError('WebSocket connection error')
        setLoading(false)
        toast.error('Connection error')
      }

      ws.onclose = () => {
        console.log('[RDP] WebSocket closed')
        setConnected(false)
        setLoading(false)
      }

    } catch (err) {
      console.error('[RDP] Init error:', err)
      setError(err.message || 'Failed to initialize RDP')
      setLoading(false)
      toast.error('Failed to connect to remote desktop')
    }
  }

  const handleRDPFrame = (frameData) => {
    if (!canvasRef.current) {
      addDebugLog('RENDER_ERROR', 'Canvas ref is null')
      return
    }

    try {
      const ctx = canvasRef.current.getContext('2d')

      addDebugLog('RENDER', `Attempting to render frame, type: ${typeof frameData}, length: ${frameData?.length || 'N/A'}`)

      // If frameData is base64 string
      if (typeof frameData === 'string') {
        addDebugLog('RENDER', `Base64 string frame: ${frameData.length} chars`)
        const img = new Image()
        img.onload = () => {
          addDebugLog('RENDER', `Image loaded: ${img.width}x${img.height}`)
          canvasRef.current.width = img.width
          canvasRef.current.height = img.height
          ctx.drawImage(img, 0, 0)
          addDebugLog('RENDER', 'Frame drawn to canvas successfully')
        }
        img.onerror = (e) => {
          addDebugLog('RENDER_ERROR', 'Failed to load image from base64', { error: e })
        }
        img.src = 'data:image/jpeg;base64,' + frameData
      }
      // If frameData is Uint8Array
      else if (frameData instanceof Uint8Array) {
        addDebugLog('RENDER', `Uint8Array frame: ${frameData.length} bytes`)
        // Convert to blob and create object URL
        const blob = new Blob([frameData], { type: 'image/jpeg' })
        const url = URL.createObjectURL(blob)
        const img = new Image()
        img.onload = () => {
          addDebugLog('RENDER', `Image loaded: ${img.width}x${img.height}`)
          canvasRef.current.width = img.width
          canvasRef.current.height = img.height
          ctx.drawImage(img, 0, 0)
          URL.revokeObjectURL(url)
          addDebugLog('RENDER', 'Frame drawn to canvas successfully')
        }
        img.onerror = (e) => {
          addDebugLog('RENDER_ERROR', 'Failed to load image from Uint8Array', { error: e })
          URL.revokeObjectURL(url)
        }
        img.src = url
      } else {
        addDebugLog('RENDER_ERROR', `Unknown frame data type: ${typeof frameData}`, { sample: frameData?.toString().substring(0, 50) })
      }
    } catch (error) {
      console.error('[RDP] Error rendering frame:', error)
      addDebugLog('RENDER_ERROR', `Exception: ${error.message}`, { stack: error.stack })
    }
  }

  const handleMouseMove = (e) => {
    if (!connected || !wsRef.current) return

    const rect = canvasRef.current.getBoundingClientRect()
    const x = Math.floor((e.clientX - rect.left) * (canvasRef.current.width / rect.width))
    const y = Math.floor((e.clientY - rect.top) * (canvasRef.current.height / rect.height))

    wsRef.current.send(JSON.stringify({
      type: 'mouse',
      action: 'move',
      x: x,
      y: y
    }))
  }

  const handleMouseClick = (e) => {
    if (!connected || !wsRef.current) return

    wsRef.current.send(JSON.stringify({
      type: 'mouse',
      action: e.type === 'mousedown' ? 'down' : 'up',
      button: e.button
    }))
  }

  const handleKeyEvent = (e) => {
    if (!connected || !wsRef.current) return

    e.preventDefault()

    wsRef.current.send(JSON.stringify({
      type: 'key',
      action: e.type === 'keydown' ? 'down' : 'up',
      key: e.key,
      keyCode: e.keyCode,
      ctrlKey: e.ctrlKey,
      shiftKey: e.shiftKey,
      altKey: e.altKey
    }))
  }

  const handleDisconnect = () => {
    if (wsRef.current) {
      wsRef.current.send(JSON.stringify({ type: 'disconnect' }))
      wsRef.current.close()
    }
    navigate('/nodes')
  }

  const toggleFullscreen = () => {
    setFullscreen(!fullscreen)
  }

  const handleCredentialsSubmit = (e) => {
    e.preventDefault()
    if (credentials.username && credentials.password) {
      connectRDP()
    } else {
      toast.error('Please enter username and password')
    }
  }

  // Show credentials form if not connected
  if (showCredentials && !connected) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center p-6">
        <div className="bg-gray-800 rounded-lg shadow-xl p-8 max-w-md w-full">
          <div className="flex items-center gap-3 mb-6">
            <FiMonitor className="w-8 h-8 text-blue-400" />
            <h1 className="text-2xl font-bold text-white">Connect to RDP</h1>
          </div>

          <form onSubmit={handleCredentialsSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Username
              </label>
              <input
                type="text"
                value={credentials.username}
                onChange={(e) => setCredentials({ ...credentials, username: e.target.value })}
                className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="parallels"
                autoComplete="username"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Password
              </label>
              <input
                type="password"
                value={credentials.password}
                onChange={(e) => setCredentials({ ...credentials, password: e.target.value })}
                className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="••••••••"
                autoComplete="current-password"
                required
              />
            </div>

            <div className="flex gap-3 mt-6">
              <button
                type="submit"
                disabled={loading}
                className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-lg transition font-medium"
              >
                {loading ? 'Connecting...' : 'Connect'}
              </button>
              <button
                type="button"
                onClick={() => navigate('/nodes')}
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition"
              >
                Cancel
              </button>
            </div>
          </form>

          {error && (
            <div className="mt-4 p-3 bg-red-900 bg-opacity-30 border border-red-500 rounded-lg">
              <div className="flex items-center gap-2">
                <FiAlertCircle className="w-5 h-5 text-red-400" />
                <p className="text-red-400 text-sm">{error}</p>
              </div>
            </div>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className={`${fullscreen ? 'fixed inset-0 z-50' : 'p-6'} bg-gray-900`}>
      {/* Header */}
      <div className="bg-gray-800 border-b border-gray-700 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <FiMonitor className="w-5 h-5 text-blue-400" />
          <div>
            <h1 className="text-white font-semibold">
              RDP Remote Desktop {nodeName && `- ${nodeName}`}
            </h1>
            <p className="text-gray-400 text-sm">Node: {nodeId.slice(0, 8)}...</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Connection Status */}
          <div className={`flex items-center gap-2 px-3 py-1 rounded-full ${
            connected
              ? 'bg-green-900 bg-opacity-30 border border-green-500'
              : loading
              ? 'bg-yellow-900 bg-opacity-30 border border-yellow-500'
              : 'bg-red-900 bg-opacity-30 border border-red-500'
          }`}>
            <div className={`w-2 h-2 rounded-full ${
              connected ? 'bg-green-500' : loading ? 'bg-yellow-500 animate-pulse' : 'bg-red-500'
            }`} />
            <span className={`text-sm font-medium ${
              connected ? 'text-green-400' : loading ? 'text-yellow-400' : 'text-red-400'
            }`}>
              {connected ? 'Connected' : loading ? 'Connecting...' : 'Disconnected'}
            </span>
          </div>

          <button
            onClick={() => setDebugMode(!debugMode)}
            className={`p-2 ${debugMode ? 'text-green-400 bg-green-900 bg-opacity-30' : 'text-gray-400'} hover:text-white hover:bg-gray-700 rounded transition`}
            title="Toggle Debug Mode"
          >
            <FiTerminal className="w-5 h-5" />
          </button>

          <button
            onClick={toggleFullscreen}
            className="p-2 text-gray-400 hover:text-white hover:bg-gray-700 rounded transition"
            title={fullscreen ? 'Exit Fullscreen' : 'Fullscreen'}
          >
            {fullscreen ? <FiMinimize2 className="w-5 h-5" /> : <FiMaximize2 className="w-5 h-5" />}
          </button>

          <button
            onClick={handleDisconnect}
            className="p-2 text-red-400 hover:text-red-300 hover:bg-red-900 hover:bg-opacity-20 rounded transition"
            title="Disconnect"
          >
            <FiX className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* RDP Canvas Container */}
      <div className="relative" style={{ height: fullscreen ? 'calc(100vh - 60px)' : 'calc(100vh - 180px)' }}>
        {loading && !error && (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-900">
            <div className="text-center">
              <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
              <p className="text-gray-400">Connecting to remote desktop...</p>
            </div>
          </div>
        )}

        {error && (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-900">
            <div className="text-center max-w-md p-6">
              <FiAlertCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
              <h2 className="text-xl font-semibold text-white mb-2">Connection Error</h2>
              <p className="text-gray-400 mb-4">{error}</p>
              <button
                onClick={handleDisconnect}
                className="mt-4 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded transition"
              >
                Back to Nodes
              </button>
            </div>
          </div>
        )}

        {/* RDP Canvas */}
        <canvas
          ref={canvasRef}
          className={`w-full h-full ${loading || error ? 'hidden' : 'block'}`}
          style={{
            backgroundColor: '#1e1e1e',
            objectFit: 'contain',
            cursor: connected ? 'default' : 'not-allowed'
          }}
          onMouseMove={handleMouseMove}
          onMouseDown={handleMouseClick}
          onMouseUp={handleMouseClick}
          onKeyDown={handleKeyEvent}
          onKeyUp={handleKeyEvent}
          tabIndex={0}
          width={1920}
          height={1080}
        />
      </div>

      {/* Debug Panel */}
      {debugMode && (
        <div className="fixed bottom-0 right-0 w-1/3 h-96 bg-gray-900 bg-opacity-95 border-t border-l border-gray-700 p-4 overflow-hidden flex flex-col z-50">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-white font-semibold flex items-center gap-2">
              <FiTerminal className="w-5 h-5 text-green-400" />
              RDP Debug Console
            </h3>
            <button
              onClick={() => setDebugLogs([])}
              className="p-1 text-gray-400 hover:text-white hover:bg-gray-700 rounded transition"
              title="Clear logs"
            >
              <FiRefreshCw className="w-4 h-4" />
            </button>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-2 gap-2 mb-3 text-xs">
            <div className="bg-gray-800 p-2 rounded">
              <div className="text-gray-400">Messages</div>
              <div className="text-white font-mono">{stats.messagesReceived}</div>
            </div>
            <div className="bg-gray-800 p-2 rounded">
              <div className="text-gray-400">Frames</div>
              <div className="text-white font-mono">{stats.framesReceived}</div>
            </div>
            <div className="bg-gray-800 p-2 rounded">
              <div className="text-gray-400">Bytes</div>
              <div className="text-white font-mono">{(stats.bytesReceived / 1024).toFixed(2)} KB</div>
            </div>
            <div className="bg-gray-800 p-2 rounded">
              <div className="text-gray-400">Last Type</div>
              <div className="text-white font-mono text-xs truncate">{stats.lastMessageType || 'none'}</div>
            </div>
          </div>

          {stats.lastFrameTime && (
            <div className="bg-blue-900 bg-opacity-30 border border-blue-500 p-2 rounded mb-3 text-xs">
              <div className="text-blue-400">Last Frame: {stats.lastFrameTime}</div>
            </div>
          )}

          {/* Logs */}
          <div className="flex-1 overflow-y-auto bg-black bg-opacity-50 rounded p-2 font-mono text-xs">
            {debugLogs.length === 0 ? (
              <div className="text-gray-500 text-center py-4">No debug logs yet</div>
            ) : (
              debugLogs.map((log, idx) => (
                <div key={idx} className="mb-1 text-gray-300 hover:bg-gray-800 px-1 rounded">
                  <span className="text-gray-500">{log.timestamp}</span>
                  {' '}
                  <span className={`font-bold ${
                    log.type === 'ERROR' || log.type === 'RENDER_ERROR' ? 'text-red-400' :
                    log.type === 'CONNECTED' || log.type === 'SESSION' ? 'text-green-400' :
                    log.type === 'FRAME' || log.type === 'BLOB' ? 'text-blue-400' :
                    log.type === 'RENDER' ? 'text-purple-400' :
                    'text-yellow-400'
                  }`}>
                    [{log.type}]
                  </span>
                  {' '}
                  <span>{log.message}</span>
                  {log.data && (
                    <div className="text-gray-600 ml-4 text-xs truncate">{log.data}</div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  )
}
