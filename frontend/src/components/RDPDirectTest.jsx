/**
 * RDP Direct Test Component
 * Guacamole HTML5 RDP integration with real-time logging
 * For: Marco @ Syneto/Orizon
 * Endpoint: /api/v1/guacamole/{node_id}
 */

import { useState, useRef, useEffect } from 'react'
import { FiX, FiPlay, FiSquare, FiCopy, FiMonitor, FiAlertCircle } from 'react-icons/fi'
import { toast } from 'react-hot-toast'

export default function RDPDirectTest({ nodeId, nodeName, username = 'parallels', password = 'profano.69', onClose }) {
  const [isConnecting, setIsConnecting] = useState(false)
  const [isConnected, setIsConnected] = useState(false)
  const [logs, setLogs] = useState([])
  const [stats, setStats] = useState({
    messagesReceived: 0,
    framesReceived: 0,
    bytesReceived: 0,
    connectionTime: null,
    lastFrameTime: null,
    lastMessageType: null
  })
  const wsRef = useRef(null)
  const canvasRef = useRef(null)
  const logsEndRef = useRef(null)

  const addLog = (type, message, data = null) => {
    const timestamp = new Date().toLocaleTimeString('it-IT', { hour12: false })
    const logEntry = {
      timestamp,
      type,
      message,
      data: data ? JSON.stringify(data).substring(0, 150) : null
    }
    setLogs(prev => [...prev.slice(-100), logEntry]) // Keep last 100 logs
  }

  const handleRDPFrame = (frameData) => {
    if (!canvasRef.current) {
      addLog('RENDER_ERROR', 'Canvas ref is null')
      return
    }

    try {
      const ctx = canvasRef.current.getContext('2d')

      // Handle binary blob
      if (frameData instanceof Blob) {
        const url = URL.createObjectURL(frameData)
        const img = new Image()
        img.onload = () => {
          canvasRef.current.width = img.width || 1024
          canvasRef.current.height = img.height || 768
          ctx.drawImage(img, 0, 0)
          URL.revokeObjectURL(url)
          addLog('RENDER', `✓ Frame rendered: ${img.width}x${img.height}`)
        }
        img.onerror = () => {
          addLog('RENDER_ERROR', 'Failed to load blob image')
          URL.revokeObjectURL(url)
        }
        img.src = url
      }
      // Handle base64 string
      else if (typeof frameData === 'string') {
        const img = new Image()
        img.onload = () => {
          canvasRef.current.width = img.width || 1024
          canvasRef.current.height = img.height || 768
          ctx.drawImage(img, 0, 0)
          addLog('RENDER', `✓ Frame rendered: ${img.width}x${img.height}`)
        }
        img.onerror = () => {
          addLog('RENDER_ERROR', 'Failed to load base64 image')
        }
        img.src = frameData.startsWith('data:') ? frameData : `data:image/jpeg;base64,${frameData}`
      }
      // Handle Uint8Array
      else if (frameData instanceof Uint8Array) {
        const blob = new Blob([frameData], { type: 'image/jpeg' })
        const url = URL.createObjectURL(blob)
        const img = new Image()
        img.onload = () => {
          canvasRef.current.width = img.width || 1024
          canvasRef.current.height = img.height || 768
          ctx.drawImage(img, 0, 0)
          URL.revokeObjectURL(url)
          addLog('RENDER', `✓ Frame rendered: ${img.width}x${img.height}`)
        }
        img.onerror = () => {
          addLog('RENDER_ERROR', 'Failed to load Uint8Array image')
          URL.revokeObjectURL(url)
        }
        img.src = url
      } else {
        addLog('RENDER_ERROR', `Unknown frame type: ${typeof frameData}`)
      }
    } catch (error) {
      addLog('RENDER_ERROR', `Exception: ${error.message}`)
    }
  }

  useEffect(() => {
    // Auto-scroll logs to bottom
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  const startTest = async () => {
    try {
      setIsConnecting(true)
      addLog('INFO', `Starting RDP test for node: ${nodeId}`)

      const token = localStorage.getItem('access_token')
      if (!token) {
        addLog('ERROR', 'No authentication token found')
        toast.error('Not authenticated')
        setIsConnecting(false)
        return
      }

      // Build WebSocket URL for Guacamole endpoint
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const host = import.meta.env.VITE_API_URL
        ? import.meta.env.VITE_API_URL.replace(/^https?:\/\//, '')
        : window.location.host
      const wsUrl = `${protocol}//${host}/api/v1/guacamole/${nodeId}`

      addLog('WEBSOCKET', `Connecting to Guacamole endpoint: ${wsUrl}`)

      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onopen = () => {
        addLog('WEBSOCKET', '✓ WebSocket connection opened')
        setStats(prev => ({ ...prev, connectionTime: new Date().toISOString() }))

        // Send auth with provided credentials
        const authMsg = {
          type: 'auth',
          token: token,
          username: username,
          password: password
        }
        ws.send(JSON.stringify(authMsg))
        addLog('AUTH', 'Authentication message sent', { username })
      }

      ws.onmessage = async (event) => {
        setStats(prev => ({
          ...prev,
          messagesReceived: prev.messagesReceived + 1
        }))

        // Handle binary data (frames)
        if (event.data instanceof Blob) {
          const size = event.data.size
          addLog('FRAME', `📦 Binary frame received: ${size} bytes`, { size })
          setStats(prev => ({
            ...prev,
            framesReceived: prev.framesReceived + 1,
            bytesReceived: prev.bytesReceived + size,
            lastFrameTime: new Date().toISOString(),
            lastMessageType: 'binary_blob'
          }))

          // Render frame on canvas
          handleRDPFrame(event.data)
          return
        }

        // Handle text messages
        try {
          const message = JSON.parse(event.data)
          addLog('MESSAGE', `📨 ${message.type}`, message)

          setStats(prev => ({
            ...prev,
            lastMessageType: message.type
          }))

          switch (message.type) {
            case 'session_id':
              addLog('SESSION', `✓ Session ID: ${message.session_id}`)
              setIsConnecting(false)
              break

            case 'connected':
              addLog('CONNECTED', '✓ RDP connection established')
              setIsConnected(true)
              setIsConnecting(false)
              toast.success('RDP connected!')
              break

            case 'frame':
              const frameSize = message.data ? message.data.length : 0
              addLog('FRAME', `📦 Text frame received: ${frameSize} chars`)
              setStats(prev => ({
                ...prev,
                framesReceived: prev.framesReceived + 1,
                bytesReceived: prev.bytesReceived + frameSize,
                lastFrameTime: new Date().toISOString()
              }))

              // Render frame on canvas
              if (message.data) {
                handleRDPFrame(message.data)
              }
              break

            case 'rdp_ready':
              addLog('RDP_READY', '✓ Agent reports RDP ready')
              break

            case 'error':
              addLog('ERROR', `❌ ${message.message}`, message)
              toast.error(message.message)
              break

            case 'disconnected':
              addLog('DISCONNECTED', '⚠️ Connection closed by server')
              setIsConnected(false)
              break

            default:
              addLog('UNKNOWN', `Unknown message type: ${message.type}`, message)
          }
        } catch (error) {
          addLog('ERROR', `Failed to parse message: ${error.message}`)
        }
      }

      ws.onerror = (error) => {
        addLog('ERROR', `❌ WebSocket error: ${error.toString()}`)
        setIsConnecting(false)
        toast.error('Connection error')
      }

      ws.onclose = (event) => {
        addLog('WEBSOCKET', `⚠️ WebSocket closed (code: ${event.code})`)
        setIsConnected(false)
        setIsConnecting(false)
      }

    } catch (error) {
      addLog('ERROR', `❌ Failed to start test: ${error.message}`)
      setIsConnecting(false)
      toast.error('Test failed')
    }
  }

  const stopTest = () => {
    if (wsRef.current) {
      addLog('INFO', 'Stopping test...')
      wsRef.current.send(JSON.stringify({ type: 'disconnect' }))
      wsRef.current.close()
      wsRef.current = null
    }
    setIsConnected(false)
    setIsConnecting(false)
  }

  const copyLogs = () => {
    const logText = logs.map(log =>
      `[${log.timestamp}] ${log.type}: ${log.message}${log.data ? ` - ${log.data}` : ''}`
    ).join('\n')
    navigator.clipboard.writeText(logText)
    toast.success('Logs copied to clipboard')
  }

  const clearLogs = () => {
    setLogs([])
    setStats({
      messagesReceived: 0,
      framesReceived: 0,
      bytesReceived: 0,
      connectionTime: null,
      lastFrameTime: null,
      lastMessageType: null
    })
    toast.success('Logs cleared')
  }

  const handleMouseMove = (e) => {
    if (!isConnected || !wsRef.current || !canvasRef.current) return

    const rect = canvasRef.current.getBoundingClientRect()
    const x = Math.floor((e.clientX - rect.left) * (canvasRef.current.width / rect.width))
    const y = Math.floor((e.clientY - rect.top) * (canvasRef.current.height / rect.height))

    wsRef.current.send(JSON.stringify({
      type: 'mouse',
      action: 'move',
      x, y
    }))
  }

  const handleMouseClick = (e) => {
    if (!isConnected || !wsRef.current) return

    wsRef.current.send(JSON.stringify({
      type: 'mouse',
      action: e.type === 'mousedown' ? 'down' : 'up',
      button: e.button
    }))
  }

  const handleKeyEvent = (e) => {
    if (!isConnected || !wsRef.current) return
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

  // Calculate FPS if we have frames
  const fps = stats.framesReceived > 0 && stats.connectionTime
    ? (stats.framesReceived / ((Date.now() - new Date(stats.connectionTime).getTime()) / 1000)).toFixed(1)
    : '0.0'

  return (
    <div className="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-800 rounded-lg shadow-2xl max-w-5xl w-full max-h-[90vh] flex flex-col border border-gray-700">
        {/* Header */}
        <div className="flex items-center justify-between p-1.5 border-b border-gray-700">
          <div className="flex items-center gap-1.5">
            <FiMonitor className="w-3.5 h-3.5 text-blue-400" />
            <div>
              <h2 className="text-sm font-bold text-white">RDP Direct (Guacamole HTML5)</h2>
              <p className="text-[9px] text-gray-400">
                {nodeName || `Node ${nodeId.slice(0, 8)}...`}
              </p>
            </div>
          </div>

          {/* Connection Status */}
          <div className="flex items-center gap-3">
            <div className={`flex items-center gap-1.5 px-2 py-1 rounded-full border ${
              isConnected
                ? 'bg-green-900 bg-opacity-30 border-green-500'
                : isConnecting
                ? 'bg-yellow-900 bg-opacity-30 border-yellow-500'
                : 'bg-red-900 bg-opacity-30 border-red-500'
            }`}>
              <div className={`w-2 h-2 rounded-full ${
                isConnected ? 'bg-green-500' : isConnecting ? 'bg-yellow-500 animate-pulse' : 'bg-red-500'
              }`} />
              <span className={`text-[9px] font-medium ${
                isConnected ? 'text-green-400' : isConnecting ? 'text-yellow-400' : 'text-red-400'
              }`}>
                {isConnected ? 'Connected' : isConnecting ? 'Connecting...' : 'Disconnected'}
              </span>
            </div>

            <button
              onClick={onClose}
              className="p-1.5 text-gray-400 hover:text-white hover:bg-gray-700 rounded transition"
            >
              <FiX className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-hidden p-2 flex gap-2">
          {/* Left Side - RDP Canvas */}
          <div className="flex-1 bg-gray-900 rounded-lg border border-gray-700 flex items-center justify-center">
            <canvas
              ref={canvasRef}
              className="max-w-full max-h-full"
              style={{
                backgroundColor: '#1e1e1e',
                cursor: isConnected ? 'default' : 'not-allowed',
                imageRendering: 'auto'
              }}
              width={1024}
              height={768}
              onMouseMove={handleMouseMove}
              onMouseDown={handleMouseClick}
              onMouseUp={handleMouseClick}
              onKeyDown={handleKeyEvent}
              onKeyUp={handleKeyEvent}
              tabIndex={0}
            />
          </div>

          {/* Right Side - Stats & Controls */}
          <div className="w-56 flex flex-col gap-1.5">
            {/* Controls */}
            <div className="bg-gray-900 rounded-lg p-1.5 border border-gray-700">
              <h3 className="text-white text-[9px] font-semibold mb-1">Controls</h3>
              <div className="flex gap-1.5">
                {!isConnected && !isConnecting && (
                  <button
                    onClick={startTest}
                    className="flex-1 flex items-center justify-center gap-0.5 px-1.5 py-0.5 bg-green-600 hover:bg-green-500 text-white rounded text-[9px] transition font-medium"
                  >
                    <FiPlay className="w-2.5 h-2.5" />
                    Connect
                  </button>
                )}
                {(isConnected || isConnecting) && (
                  <button
                    onClick={stopTest}
                    className="flex-1 flex items-center justify-center gap-0.5 px-1.5 py-0.5 bg-red-600 hover:bg-red-500 text-white rounded text-[9px] transition font-medium"
                  >
                    <FiSquare className="w-2.5 h-2.5" />
                    Disconnect
                  </button>
                )}
              </div>
            </div>

            {/* Statistics */}
            <div className="bg-gray-900 rounded-lg p-1.5 border border-gray-700 flex-1">
              <h3 className="text-white text-[9px] font-semibold mb-1">Statistics</h3>
              <div className="space-y-1 text-xs">
                <div>
                  <div className="text-gray-400 text-[8px] mb-0.5">Messages</div>
                  <div className="text-white font-mono text-[10px]">{stats.messagesReceived}</div>
                </div>
                <div>
                  <div className="text-gray-400 text-[8px] mb-0.5">Frames</div>
                  <div className={`font-mono text-[10px] ${stats.framesReceived > 0 ? 'text-green-400' : 'text-white'}`}>
                    {stats.framesReceived}
                  </div>
                </div>
                <div>
                  <div className="text-gray-400 text-[8px] mb-0.5">Bytes Received</div>
                  <div className="text-white font-mono text-[9px]">{(stats.bytesReceived / 1024).toFixed(2)} KB</div>
                </div>
                <div>
                  <div className="text-gray-400 text-[8px] mb-0.5">Frame Rate</div>
                  <div className="text-white font-mono text-[9px]">{fps} FPS</div>
                </div>
                <div className="pt-0.5 border-t border-gray-700">
                  <div className="text-gray-400 text-[8px] mb-0.5">Last Message</div>
                  <div className="text-blue-400 font-mono text-[8px] truncate">
                    {stats.lastMessageType || 'none'}
                  </div>
                </div>
                {stats.lastFrameTime && (
                  <div>
                    <div className="text-gray-400 text-[8px] mb-0.5">Last Frame</div>
                    <div className="text-green-400 font-mono text-[9px]">
                      {new Date(stats.lastFrameTime).toLocaleTimeString('it-IT')}
                    </div>
                  </div>
                )}
                {stats.connectionTime && (
                  <div>
                    <div className="text-gray-400 text-[8px] mb-0.5">Connected At</div>
                    <div className="text-white font-mono text-[9px]">
                      {new Date(stats.connectionTime).toLocaleTimeString('it-IT')}
                    </div>
                  </div>
                )}
              </div>

              {/* Test Result */}
              {logs.length > 10 && (
                <div className={`mt-1 p-1 rounded border ${
                  stats.framesReceived > 0
                    ? 'bg-green-900 bg-opacity-20 border-green-600'
                    : 'bg-yellow-900 bg-opacity-20 border-yellow-600'
                }`}>
                  <div className="flex items-start gap-1">
                    {stats.framesReceived > 0 ? (
                      <div className="text-green-400 text-[8px]">
                        <div className="font-bold mb-0.5">✅ SUCCESS</div>
                        <div>Frames received</div>
                      </div>
                    ) : (
                      <div className="text-yellow-400 text-[8px]">
                        <div className="font-bold mb-0.5">⚠️ WAITING</div>
                        <div>No frames yet</div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Right Side - Logs */}
          <div className="flex-1 bg-gray-900 rounded-lg border border-gray-700 flex flex-col">
            <div className="flex items-center justify-between p-1.5 border-b border-gray-700">
              <h3 className="text-white text-[9px] font-semibold">Live Logs</h3>
              <div className="flex gap-2">
                <button
                  onClick={copyLogs}
                  className="p-1.5 text-gray-400 hover:text-white hover:bg-gray-700 rounded transition"
                  title="Copy logs"
                >
                  <FiCopy className="w-4 h-4" />
                </button>
                <button
                  onClick={clearLogs}
                  className="px-3 py-1 text-xs bg-gray-700 hover:bg-gray-600 text-white rounded transition"
                >
                  Clear
                </button>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-1.5 font-mono text-[9px]">
              {logs.length === 0 ? (
                <div className="flex items-center justify-center h-full text-gray-500 text-[10px]">
                  <div className="text-center">
                    <FiAlertCircle className="w-5 h-5 mx-auto mb-1.5" />
                    <p>No logs yet. Click "Connect" to begin.</p>
                  </div>
                </div>
              ) : (
                logs.map((log, idx) => (
                  <div
                    key={idx}
                    className={`mb-1 p-1 rounded ${
                      log.type === 'ERROR' ? 'bg-red-900 bg-opacity-20' :
                      log.type === 'CONNECTED' || log.type === 'SESSION' ? 'bg-green-900 bg-opacity-20' :
                      log.type === 'FRAME' ? 'bg-blue-900 bg-opacity-20' :
                      'bg-gray-800'
                    }`}
                  >
                    <div className="flex items-start gap-2">
                      <span className="text-gray-500 flex-shrink-0">{log.timestamp}</span>
                      <span className={`font-bold flex-shrink-0 ${
                        log.type === 'ERROR' ? 'text-red-400' :
                        log.type === 'CONNECTED' || log.type === 'SESSION' ? 'text-green-400' :
                        log.type === 'FRAME' ? 'text-blue-400' :
                        log.type === 'WEBSOCKET' ? 'text-purple-400' :
                        log.type === 'AUTH' ? 'text-yellow-400' :
                        'text-gray-400'
                      }`}>
                        [{log.type}]
                      </span>
                      <span className="text-gray-300 break-all">{log.message}</span>
                    </div>
                    {log.data && (
                      <div className="ml-20 mt-1 text-gray-600 text-[10px] break-all">
                        {log.data}
                      </div>
                    )}
                  </div>
                ))
              )}
              <div ref={logsEndRef} />
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-3 border-t border-gray-700 bg-gray-900 bg-opacity-50">
          <div className="text-xs text-gray-400 text-center">
            Apache Guacamole RDP on <span className="text-white font-mono">{nodeId}</span>
            {' • '}
            Direct RDP connection using Guacamole HTML5 gateway with WebSocket proxy
          </div>
        </div>
      </div>
    </div>
  )
}
