/**
 * VNC Remote Desktop Page
 * Web-based VNC remote desktop for node access
 * For: Marco @ Syneto/Orizon
 */

import { useEffect, useRef, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { FiX, FiMaximize2, FiMinimize2, FiAlertCircle, FiMonitor } from 'react-icons/fi'
import { toast } from 'react-toastify'
import RFB from '@novnc/novnc/lib/rfb.js'

export default function RemoteDesktopPage() {
  const { nodeId } = useParams()
  const navigate = useNavigate()
  const canvasRef = useRef(null)
  const [rfb, setRfb] = useState(null)
  const [connected, setConnected] = useState(false)
  const [error, setError] = useState(null)
  const [fullscreen, setFullscreen] = useState(false)
  const [loading, setLoading] = useState(true)
  const [nodeName, setNodeName] = useState('')

  useEffect(() => {
    if (!nodeId) {
      setError('No node ID provided')
      setLoading(false)
      return
    }

    let mounted = true
    let rfbConnection = null

    const initVNC = async () => {
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
        const wsUrl = `${protocol}//${host}/api/v1/vnc/${nodeId}/connect`

        console.log('[VNC] Connecting to:', wsUrl)

        // Create RFB connection
        rfbConnection = new RFB(canvasRef.current, wsUrl)

        // Configure RFB
        rfbConnection.scaleViewport = true
        rfbConnection.resizeSession = true
        rfbConnection.showDotCursor = true
        rfbConnection.background = '#1e1e1e'
        rfbConnection.qualityLevel = 6
        rfbConnection.compressionLevel = 2

        // Event handlers
        rfbConnection.addEventListener('connect', () => {
          if (!mounted) return
          console.log('[VNC] Connected')
          setConnected(true)
          setLoading(false)
          toast.success('Connected to remote desktop')

          // Send auth message
          setTimeout(() => {
            try {
              const ws = rfbConnection._sock._websocket
              if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({
                  type: 'auth',
                  token: token
                }))
                console.log('[VNC] Auth message sent')
              }
            } catch (e) {
              console.error('[VNC] Error sending auth:', e)
            }
          }, 100)
        })

        rfbConnection.addEventListener('disconnect', (e) => {
          if (!mounted) return
          console.log('[VNC] Disconnected:', e.detail)
          setConnected(false)

          if (e.detail.clean) {
            toast.info('Disconnected from remote desktop')
          } else {
            setError('Connection lost')
            toast.error('Connection to remote desktop lost')
          }
        })

        rfbConnection.addEventListener('credentialsrequired', () => {
          if (!mounted) return
          console.log('[VNC] Credentials required')
          // VNC server requires password - we're using -nopw so this shouldn't happen
          setError('VNC server requires password')
        })

        rfbConnection.addEventListener('securityfailure', (e) => {
          if (!mounted) return
          console.error('[VNC] Security failure:', e.detail)
          setError(`Security failure: ${e.detail.status}`)
          toast.error('VNC security failure')
        })

        rfbConnection.addEventListener('desktopname', (e) => {
          if (!mounted) return
          console.log('[VNC] Desktop name:', e.detail.name)
          setNodeName(e.detail.name)
        })

        setRfb(rfbConnection)

      } catch (err) {
        console.error('[VNC] Init error:', err)
        setError(err.message || 'Failed to initialize VNC')
        setLoading(false)
        toast.error('Failed to connect to remote desktop')
      }
    }

    initVNC()

    // Cleanup
    return () => {
      mounted = false
      if (rfbConnection) {
        try {
          rfbConnection.disconnect()
        } catch (e) {
          console.error('[VNC] Cleanup error:', e)
        }
      }
    }
  }, [nodeId, navigate])

  const handleDisconnect = () => {
    if (rfb) {
      rfb.disconnect()
    }
    navigate('/nodes')
  }

  const toggleFullscreen = () => {
    setFullscreen(!fullscreen)
  }

  return (
    <div className={`${fullscreen ? 'fixed inset-0 z-50' : 'p-6'} bg-gray-900`}>
      {/* Header */}
      <div className="bg-gray-800 border-b border-gray-700 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <FiMonitor className="w-5 h-5 text-blue-400" />
          <div>
            <h1 className="text-white font-semibold">
              Remote Desktop {nodeName && `- ${nodeName}`}
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

          {/* Fullscreen Toggle */}
          <button
            onClick={toggleFullscreen}
            className="p-2 text-gray-400 hover:text-white hover:bg-gray-700 rounded transition"
            title={fullscreen ? 'Exit Fullscreen' : 'Fullscreen'}
          >
            {fullscreen ? <FiMinimize2 className="w-5 h-5" /> : <FiMaximize2 className="w-5 h-5" />}
          </button>

          {/* Disconnect */}
          <button
            onClick={handleDisconnect}
            className="p-2 text-red-400 hover:text-red-300 hover:bg-red-900 hover:bg-opacity-20 rounded transition"
            title="Disconnect"
          >
            <FiX className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* VNC Canvas Container */}
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
              <div className="space-y-2 text-sm text-gray-500 text-left bg-gray-800 p-4 rounded">
                <p><strong>Troubleshooting:</strong></p>
                <ul className="list-disc list-inside space-y-1">
                  <li>Ensure x11vnc is installed on the node</li>
                  <li>Start x11vnc: <code className="text-blue-400">x11vnc -display :0 -localhost -nopw -forever</code></li>
                  <li>Check that the agent is connected</li>
                  <li>Verify VNC is running on port 5900</li>
                </ul>
              </div>
              <button
                onClick={handleDisconnect}
                className="mt-4 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded transition"
              >
                Back to Nodes
              </button>
            </div>
          </div>
        )}

        {/* noVNC Canvas */}
        <div
          ref={canvasRef}
          className={`w-full h-full ${loading || error ? 'hidden' : 'block'}`}
          style={{
            backgroundColor: '#1e1e1e',
            overflow: 'hidden'
          }}
        />
      </div>
    </div>
  )
}
