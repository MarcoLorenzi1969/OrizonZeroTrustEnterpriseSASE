/**
 * Web RDP Component - Remote Desktop Protocol via WebSocket
 * Based on mstsc.js architecture (Canvas + WebSocket)
 * For: Marco @ Syneto/Orizon
 *
 * This component provides RDP access through the browser using:
 * - HTML5 Canvas for bitmap rendering
 * - WebSocket for bidirectional communication
 * - Mouse and keyboard event forwarding
 */

import { useEffect, useRef, useState, useCallback } from 'react'
import { X, Maximize2, Minimize2, Monitor, Wifi, WifiOff, Settings, RefreshCw } from 'lucide-react'

// RDP Connection States
const ConnectionState = {
  DISCONNECTED: 'disconnected',
  CONNECTING: 'connecting',
  CONNECTED: 'connected',
  ERROR: 'error'
}

// Default RDP settings
const DEFAULT_RDP_SETTINGS = {
  width: 1280,
  height: 720,
  colorDepth: 24,
  domain: '',
  username: '',
  password: '',
  locale: 'it-IT',
  enableClipboard: true,
  enableAudio: false
}

export default function WebRDP({
  nodeId,
  nodeName,
  rdpHost,
  rdpPort = 3389,
  tunnelPort,
  onClose,
  initialSettings = {}
}) {
  const canvasRef = useRef(null)
  const wsRef = useRef(null)
  const containerRef = useRef(null)

  const [connectionState, setConnectionState] = useState(ConnectionState.DISCONNECTED)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [sessionId, setSessionId] = useState(null)
  const [error, setError] = useState(null)
  const [showSettings, setShowSettings] = useState(false)
  const [stats, setStats] = useState({ fps: 0, latency: 0, bytesReceived: 0 })

  const [settings, setSettings] = useState({
    ...DEFAULT_RDP_SETTINGS,
    ...initialSettings
  })

  // Bitmap decoding worker (for performance)
  const decoderRef = useRef(null)

  // Initialize canvas and context
  const initCanvas = useCallback(() => {
    const canvas = canvasRef.current
    if (!canvas) return null

    canvas.width = settings.width
    canvas.height = settings.height

    const ctx = canvas.getContext('2d', {
      alpha: false,
      desynchronized: true // Better performance
    })

    // Set default background
    ctx.fillStyle = '#1e293b'
    ctx.fillRect(0, 0, canvas.width, canvas.height)

    // Welcome message
    ctx.fillStyle = '#3b82f6'
    ctx.font = '24px "Segoe UI", system-ui, sans-serif'
    ctx.textAlign = 'center'
    ctx.fillText('Orizon RDP - Connecting...', canvas.width / 2, canvas.height / 2 - 20)
    ctx.font = '14px "Segoe UI", system-ui, sans-serif'
    ctx.fillStyle = '#94a3b8'
    ctx.fillText(`Target: ${nodeName} (${rdpHost || 'via tunnel'})`, canvas.width / 2, canvas.height / 2 + 20)

    return ctx
  }, [settings.width, settings.height, nodeName, rdpHost])

  // Handle incoming bitmap data
  const handleBitmap = useCallback((data) => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')

    try {
      // data contains: destTop, destLeft, destBottom, destRight, width, height, bitsPerPixel, bitmap
      const { destLeft, destTop, width, height, bitmap } = data

      // Create ImageData from bitmap
      const imageData = ctx.createImageData(width, height)

      // Decode RLE compressed bitmap or raw bitmap
      if (data.isCompressed) {
        decodeBitmapRLE(bitmap, imageData.data, width, height, data.bitsPerPixel)
      } else {
        decodeBitmapRaw(bitmap, imageData.data, width, height, data.bitsPerPixel)
      }

      // Draw to canvas
      ctx.putImageData(imageData, destLeft, destTop)

      // Update stats
      setStats(prev => ({
        ...prev,
        bytesReceived: prev.bytesReceived + bitmap.length
      }))
    } catch (err) {
      console.error('Bitmap decode error:', err)
    }
  }, [])

  // Decode raw bitmap (no compression)
  const decodeBitmapRaw = (src, dest, width, height, bpp) => {
    const bytesPerPixel = bpp / 8
    let srcOffset = 0
    let destOffset = 0

    for (let y = 0; y < height; y++) {
      for (let x = 0; x < width; x++) {
        if (bpp === 32) {
          dest[destOffset] = src[srcOffset + 2]     // R
          dest[destOffset + 1] = src[srcOffset + 1] // G
          dest[destOffset + 2] = src[srcOffset]     // B
          dest[destOffset + 3] = 255                // A
          srcOffset += 4
        } else if (bpp === 24) {
          dest[destOffset] = src[srcOffset + 2]     // R
          dest[destOffset + 1] = src[srcOffset + 1] // G
          dest[destOffset + 2] = src[srcOffset]     // B
          dest[destOffset + 3] = 255                // A
          srcOffset += 3
        } else if (bpp === 16) {
          const pixel = src[srcOffset] | (src[srcOffset + 1] << 8)
          dest[destOffset] = ((pixel >> 11) & 0x1F) << 3     // R
          dest[destOffset + 1] = ((pixel >> 5) & 0x3F) << 2  // G
          dest[destOffset + 2] = (pixel & 0x1F) << 3         // B
          dest[destOffset + 3] = 255                          // A
          srcOffset += 2
        }
        destOffset += 4
      }
    }
  }

  // Decode RLE compressed bitmap (simplified RLE decoder)
  const decodeBitmapRLE = (src, dest, width, height, bpp) => {
    // RLE decompression based on RDP spec
    // This is a simplified version - full implementation would handle all RDP RLE variants
    let srcOffset = 0
    let destOffset = 0
    const totalPixels = width * height

    while (destOffset < totalPixels * 4 && srcOffset < src.length) {
      const header = src[srcOffset++]
      const isCompressed = (header & 0x80) !== 0
      let count = (header & 0x7F) + 1

      if (isCompressed) {
        // Run of same color
        const r = src[srcOffset++] || 0
        const g = src[srcOffset++] || 0
        const b = src[srcOffset++] || 0

        for (let i = 0; i < count && destOffset < totalPixels * 4; i++) {
          dest[destOffset++] = r
          dest[destOffset++] = g
          dest[destOffset++] = b
          dest[destOffset++] = 255
        }
      } else {
        // Literal pixels
        for (let i = 0; i < count && destOffset < totalPixels * 4; i++) {
          dest[destOffset++] = src[srcOffset++] || 0
          dest[destOffset++] = src[srcOffset++] || 0
          dest[destOffset++] = src[srcOffset++] || 0
          dest[destOffset++] = 255
        }
      }
    }
  }

  // Connect to RDP proxy via WebSocket
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return
    }

    setConnectionState(ConnectionState.CONNECTING)
    setError(null)

    // Initialize canvas
    initCanvas()

    // Get WebSocket URL for RDP proxy
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsHost = import.meta.env.VITE_RDP_PROXY_URL || `${wsProtocol}//${window.location.hostname}:8766`
    const wsUrl = `${wsHost}/rdp`

    const token = localStorage.getItem('access_token')

    console.log(`[WebRDP] Connecting to ${wsUrl}`)

    try {
      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.binaryType = 'arraybuffer'

      ws.onopen = () => {
        console.log('[WebRDP] WebSocket connected')

        // Send authentication and connection request
        ws.send(JSON.stringify({
          type: 'connect',
          token: token,
          nodeId: nodeId,
          config: {
            host: rdpHost || 'localhost',
            port: tunnelPort || rdpPort,
            width: settings.width,
            height: settings.height,
            colorDepth: settings.colorDepth,
            domain: settings.domain,
            username: settings.username,
            password: settings.password,
            locale: settings.locale
          }
        }))
      }

      ws.onmessage = (event) => {
        if (typeof event.data === 'string') {
          // JSON message
          try {
            const message = JSON.parse(event.data)
            handleMessage(message)
          } catch (err) {
            console.error('[WebRDP] JSON parse error:', err)
          }
        } else {
          // Binary data (bitmap)
          handleBinaryData(event.data)
        }
      }

      ws.onerror = (event) => {
        console.error('[WebRDP] WebSocket error:', event)
        setError('Connection error')
        setConnectionState(ConnectionState.ERROR)
      }

      ws.onclose = (event) => {
        console.log('[WebRDP] WebSocket closed:', event.code, event.reason)
        setConnectionState(ConnectionState.DISCONNECTED)
        if (event.code !== 1000) {
          setError(`Connection closed: ${event.reason || 'Unknown error'}`)
        }
      }

    } catch (err) {
      console.error('[WebRDP] Connection error:', err)
      setError(err.message)
      setConnectionState(ConnectionState.ERROR)
    }
  }, [nodeId, rdpHost, rdpPort, tunnelPort, settings, initCanvas])

  // Handle JSON messages from server
  const handleMessage = useCallback((message) => {
    switch (message.type) {
      case 'connected':
        setConnectionState(ConnectionState.CONNECTED)
        setSessionId(message.sessionId)
        console.log('[WebRDP] RDP session established:', message.sessionId)
        break

      case 'bitmap':
        handleBitmap(message.data)
        break

      case 'error':
        setError(message.message)
        setConnectionState(ConnectionState.ERROR)
        break

      case 'close':
        setConnectionState(ConnectionState.DISCONNECTED)
        break

      case 'stats':
        setStats(prev => ({ ...prev, ...message.data }))
        break

      default:
        console.log('[WebRDP] Unknown message type:', message.type)
    }
  }, [handleBitmap])

  // Handle binary bitmap data
  const handleBinaryData = useCallback((buffer) => {
    const view = new DataView(buffer)

    // Parse binary header (custom protocol)
    // Format: [type:1][destLeft:2][destTop:2][width:2][height:2][bpp:1][compressed:1][data:...]
    let offset = 0
    const type = view.getUint8(offset); offset += 1

    if (type === 0x01) { // Bitmap update
      const destLeft = view.getUint16(offset, true); offset += 2
      const destTop = view.getUint16(offset, true); offset += 2
      const width = view.getUint16(offset, true); offset += 2
      const height = view.getUint16(offset, true); offset += 2
      const bitsPerPixel = view.getUint8(offset); offset += 1
      const isCompressed = view.getUint8(offset) === 1; offset += 1

      const bitmap = new Uint8Array(buffer, offset)

      handleBitmap({
        destLeft,
        destTop,
        width,
        height,
        bitsPerPixel,
        isCompressed,
        bitmap
      })
    }
  }, [handleBitmap])

  // Send mouse event
  const sendMouseEvent = useCallback((eventType, x, y, button = 0) => {
    if (wsRef.current?.readyState !== WebSocket.OPEN) return

    wsRef.current.send(JSON.stringify({
      type: 'mouse',
      event: eventType,
      x: Math.round(x),
      y: Math.round(y),
      button: button
    }))
  }, [])

  // Send keyboard event
  const sendKeyEvent = useCallback((eventType, keyCode, scanCode, isExtended = false) => {
    if (wsRef.current?.readyState !== WebSocket.OPEN) return

    wsRef.current.send(JSON.stringify({
      type: 'keyboard',
      event: eventType,
      keyCode: keyCode,
      scanCode: scanCode,
      isExtended: isExtended
    }))
  }, [])

  // Mouse event handlers
  const handleMouseMove = useCallback((e) => {
    const rect = canvasRef.current.getBoundingClientRect()
    const scaleX = settings.width / rect.width
    const scaleY = settings.height / rect.height
    const x = (e.clientX - rect.left) * scaleX
    const y = (e.clientY - rect.top) * scaleY
    sendMouseEvent('move', x, y)
  }, [settings.width, settings.height, sendMouseEvent])

  const handleMouseDown = useCallback((e) => {
    const rect = canvasRef.current.getBoundingClientRect()
    const scaleX = settings.width / rect.width
    const scaleY = settings.height / rect.height
    const x = (e.clientX - rect.left) * scaleX
    const y = (e.clientY - rect.top) * scaleY
    sendMouseEvent('down', x, y, e.button)
  }, [settings.width, settings.height, sendMouseEvent])

  const handleMouseUp = useCallback((e) => {
    const rect = canvasRef.current.getBoundingClientRect()
    const scaleX = settings.width / rect.width
    const scaleY = settings.height / rect.height
    const x = (e.clientX - rect.left) * scaleX
    const y = (e.clientY - rect.top) * scaleY
    sendMouseEvent('up', x, y, e.button)
  }, [settings.width, settings.height, sendMouseEvent])

  const handleWheel = useCallback((e) => {
    e.preventDefault()
    const rect = canvasRef.current.getBoundingClientRect()
    const scaleX = settings.width / rect.width
    const scaleY = settings.height / rect.height
    const x = (e.clientX - rect.left) * scaleX
    const y = (e.clientY - rect.top) * scaleY

    wsRef.current?.send(JSON.stringify({
      type: 'wheel',
      x: Math.round(x),
      y: Math.round(y),
      deltaX: e.deltaX,
      deltaY: e.deltaY
    }))
  }, [settings.width, settings.height])

  // Keyboard event handlers
  const handleKeyDown = useCallback((e) => {
    e.preventDefault()
    sendKeyEvent('down', e.keyCode, e.which, e.location === 2)
  }, [sendKeyEvent])

  const handleKeyUp = useCallback((e) => {
    e.preventDefault()
    sendKeyEvent('up', e.keyCode, e.which, e.location === 2)
  }, [sendKeyEvent])

  // Context menu prevention
  const handleContextMenu = useCallback((e) => {
    e.preventDefault()
  }, [])

  // Disconnect
  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close(1000, 'User disconnect')
      wsRef.current = null
    }
    setConnectionState(ConnectionState.DISCONNECTED)
    setSessionId(null)
  }, [])

  // Toggle fullscreen
  const toggleFullscreen = useCallback(() => {
    if (!document.fullscreenElement) {
      containerRef.current?.requestFullscreen()
      setIsFullscreen(true)
    } else {
      document.exitFullscreen()
      setIsFullscreen(false)
    }
  }, [])

  // Effect: Auto-connect on mount
  useEffect(() => {
    connect()

    return () => {
      disconnect()
    }
  }, []) // Only on mount

  // Effect: Fullscreen change listener
  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement)
    }
    document.addEventListener('fullscreenchange', handleFullscreenChange)
    return () => document.removeEventListener('fullscreenchange', handleFullscreenChange)
  }, [])

  // Render connection status indicator
  const renderStatusIndicator = () => {
    const statusConfig = {
      [ConnectionState.DISCONNECTED]: { color: 'bg-slate-500', text: 'Disconnected' },
      [ConnectionState.CONNECTING]: { color: 'bg-yellow-500 animate-pulse', text: 'Connecting...' },
      [ConnectionState.CONNECTED]: { color: 'bg-green-500', text: 'Connected' },
      [ConnectionState.ERROR]: { color: 'bg-red-500', text: 'Error' }
    }
    const status = statusConfig[connectionState]

    return (
      <div className="flex items-center gap-2">
        <div className={`w-2 h-2 rounded-full ${status.color}`}></div>
        <span className="text-sm text-slate-300">{status.text}</span>
      </div>
    )
  }

  return (
    <div
      ref={containerRef}
      className={`bg-slate-900 border border-slate-700 rounded-lg shadow-2xl flex flex-col ${
        isFullscreen ? 'fixed inset-0 z-50 rounded-none' : 'w-full h-full'
      }`}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-700 bg-slate-800">
        <div className="flex items-center gap-3">
          <Monitor className="w-5 h-5 text-blue-400" />
          <span className="text-white font-semibold">{nodeName}</span>
          <span className="text-xs text-slate-400 font-mono">RDP</span>
          {sessionId && (
            <span className="text-xs text-slate-500 font-mono">
              Session: {sessionId.slice(0, 8)}
            </span>
          )}
        </div>

        <div className="flex items-center gap-4">
          {renderStatusIndicator()}

          <div className="flex items-center gap-2">
            {connectionState === ConnectionState.DISCONNECTED && (
              <button
                onClick={connect}
                className="px-3 py-1 text-xs bg-blue-600 hover:bg-blue-500 text-white rounded transition flex items-center gap-1"
              >
                <RefreshCw className="w-3 h-3" />
                Connect
              </button>
            )}

            {connectionState === ConnectionState.CONNECTED && (
              <button
                onClick={disconnect}
                className="px-3 py-1 text-xs bg-red-600 hover:bg-red-500 text-white rounded transition"
              >
                Disconnect
              </button>
            )}

            <button
              onClick={() => setShowSettings(!showSettings)}
              className="p-2 hover:bg-slate-700 rounded transition text-slate-400 hover:text-white"
              title="Settings"
            >
              <Settings className="w-4 h-4" />
            </button>

            <button
              onClick={toggleFullscreen}
              className="p-2 hover:bg-slate-700 rounded transition text-slate-400 hover:text-white"
              title={isFullscreen ? 'Exit fullscreen' : 'Fullscreen'}
            >
              {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
            </button>

            <button
              onClick={onClose}
              className="p-2 hover:bg-red-600 rounded transition text-slate-400 hover:text-white"
              title="Close"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Settings Panel */}
      {showSettings && (
        <div className="p-4 border-b border-slate-700 bg-slate-800/50">
          <div className="grid grid-cols-4 gap-4">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Resolution</label>
              <select
                value={`${settings.width}x${settings.height}`}
                onChange={(e) => {
                  const [w, h] = e.target.value.split('x').map(Number)
                  setSettings(prev => ({ ...prev, width: w, height: h }))
                }}
                className="w-full bg-slate-700 text-white text-sm rounded px-2 py-1"
              >
                <option value="1024x768">1024x768</option>
                <option value="1280x720">1280x720 (HD)</option>
                <option value="1366x768">1366x768</option>
                <option value="1920x1080">1920x1080 (FHD)</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Color Depth</label>
              <select
                value={settings.colorDepth}
                onChange={(e) => setSettings(prev => ({ ...prev, colorDepth: Number(e.target.value) }))}
                className="w-full bg-slate-700 text-white text-sm rounded px-2 py-1"
              >
                <option value={16}>16-bit</option>
                <option value={24}>24-bit</option>
                <option value={32}>32-bit</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Username</label>
              <input
                type="text"
                value={settings.username}
                onChange={(e) => setSettings(prev => ({ ...prev, username: e.target.value }))}
                placeholder="Administrator"
                className="w-full bg-slate-700 text-white text-sm rounded px-2 py-1"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Domain</label>
              <input
                type="text"
                value={settings.domain}
                onChange={(e) => setSettings(prev => ({ ...prev, domain: e.target.value }))}
                placeholder="WORKGROUP"
                className="w-full bg-slate-700 text-white text-sm rounded px-2 py-1"
              />
            </div>
          </div>
        </div>
      )}

      {/* Error Banner */}
      {error && (
        <div className="px-4 py-2 bg-red-900/50 border-b border-red-700 text-red-200 text-sm flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-red-300 hover:text-white">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Canvas Container */}
      <div
        className="flex-1 flex items-center justify-center bg-slate-950 overflow-hidden"
        style={{ minHeight: isFullscreen ? 'calc(100vh - 120px)' : '500px' }}
      >
        <canvas
          ref={canvasRef}
          className="max-w-full max-h-full cursor-default"
          style={{
            imageRendering: 'pixelated',
            backgroundColor: '#1e293b'
          }}
          onMouseMove={handleMouseMove}
          onMouseDown={handleMouseDown}
          onMouseUp={handleMouseUp}
          onWheel={handleWheel}
          onKeyDown={handleKeyDown}
          onKeyUp={handleKeyUp}
          onContextMenu={handleContextMenu}
          tabIndex={0}
        />
      </div>

      {/* Footer */}
      <div className="px-4 py-2 border-t border-slate-700 bg-slate-800 flex items-center justify-between text-xs text-slate-400">
        <div className="flex items-center gap-4">
          <span>Node: {nodeId}</span>
          <span>Resolution: {settings.width}x{settings.height}</span>
          <span>Color: {settings.colorDepth}-bit</span>
        </div>
        <div className="flex items-center gap-4">
          <span>Received: {(stats.bytesReceived / 1024).toFixed(1)} KB</span>
          <span>Orizon RDP Client v1.0</span>
        </div>
      </div>
    </div>
  )
}
