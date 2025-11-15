/**
 * SSH Terminal Page
 * Web-based SSH terminal for remote node access
 * For: Marco @ Syneto/Orizon
 */

import { useEffect, useRef, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { FiX, FiMaximize2, FiMinimize2, FiAlertCircle } from 'react-icons/fi'

// Lazy load xterm to avoid SSR issues
let Terminal, FitAddon, WebLinksAddon
let xtermLoaded = false

const loadXterm = async () => {
  if (xtermLoaded) return true

  try {
    const xtermModule = await import('xterm')
    const fitModule = await import('xterm-addon-fit')
    const linksModule = await import('xterm-addon-web-links')

    Terminal = xtermModule.Terminal
    FitAddon = fitModule.FitAddon
    WebLinksAddon = linksModule.WebLinksAddon

    // Load CSS
    await import('xterm/css/xterm.css')

    xtermLoaded = true
    return true
  } catch (err) {
    console.error('Failed to load xterm:', err)
    return false
  }
}

export default function TerminalPage() {
  const { nodeId } = useParams()
  const navigate = useNavigate()
  const terminalRef = useRef(null)
  const [terminal, setTerminal] = useState(null)
  const [ws, setWs] = useState(null)
  const [connected, setConnected] = useState(false)
  const [error, setError] = useState(null)
  const [fullscreen, setFullscreen] = useState(false)
  const [loading, setLoading] = useState(true)
  const fitAddonRef = useRef(null)

  useEffect(() => {
    if (!nodeId) {
      setError('No node ID provided')
      setLoading(false)
      return
    }

    let mounted = true
    let websocket = null
    let term = null

    const initTerminal = async () => {
      try {
        // Load xterm
        const loaded = await loadXterm()
        if (!loaded) {
          setError('Failed to load terminal library')
          setLoading(false)
          return
        }

        if (!mounted) return

        // Create terminal
        term = new Terminal({
          cursorBlink: true,
          fontSize: 14,
          fontFamily: 'Menlo, Monaco, "Courier New", monospace',
          theme: {
            background: '#1e1e1e',
            foreground: '#d4d4d4',
            cursor: '#ffffff',
            black: '#000000',
            red: '#cd3131',
            green: '#0dbc79',
            yellow: '#e5e510',
            blue: '#2472c8',
            magenta: '#bc3fbc',
            cyan: '#11a8cd',
            white: '#e5e5e5',
            brightBlack: '#666666',
            brightRed: '#f14c4c',
            brightGreen: '#23d18b',
            brightYellow: '#f5f543',
            brightBlue: '#3b8eea',
            brightMagenta: '#d670d6',
            brightCyan: '#29b8db',
            brightWhite: '#ffffff'
          }
        })

        const fitAddon = new FitAddon()
        const webLinksAddon = new WebLinksAddon()

        term.loadAddon(fitAddon)
        term.loadAddon(webLinksAddon)

        if (terminalRef.current && mounted) {
          term.open(terminalRef.current)
          fitAddon.fit()
          fitAddonRef.current = fitAddon
        }

        term.writeln('Connecting to node...')
        setTerminal(term)
        setLoading(false)

        // Connect WebSocket
        const token = localStorage.getItem('access_token')
        if (!token) {
          setError('Not authenticated')
          term.writeln('\x1b[31mError: Not authenticated\x1b[0m')
          return
        }

        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
        const wsUrl = `${wsProtocol}//${window.location.host}/api/v1/terminal/${nodeId}`

        console.log('Connecting to WebSocket:', wsUrl)

        websocket = new WebSocket(wsUrl)

        websocket.onopen = () => {
          console.log('WebSocket connected')
          if (!mounted) return

          // Send auth
          websocket.send(JSON.stringify({
            type: 'auth',
            token: token
          }))
        }

        websocket.onmessage = (event) => {
          if (!mounted) return

          try {
            const data = JSON.parse(event.data)
            console.log('WS Message:', data.type)

            if (data.type === 'session_id') {
              console.log('Session ID:', data.session_id)
            } else if (data.type === 'connected') {
              setConnected(true)
              term.clear()
              term.writeln(`\x1b[32m${data.message}\x1b[0m`)
              term.writeln('')
            } else if (data.type === 'output') {
              term.write(data.data)
            } else if (data.type === 'error') {
              setError(data.message)
              term.writeln(`\x1b[31mError: ${data.message}\x1b[0m`)
            }
          } catch (e) {
            console.error('Failed to parse message:', e, event.data)
          }
        }

        websocket.onerror = (err) => {
          console.error('WebSocket error:', err)
          if (!mounted) return
          setError('Connection error')
          term.writeln('\x1b[31mConnection error\x1b[0m')
        }

        websocket.onclose = () => {
          console.log('WebSocket closed')
          if (!mounted) return
          setConnected(false)
          term.writeln('\r\n\x1b[33mConnection closed\x1b[0m')
        }

        // Handle terminal input
        term.onData((data) => {
          if (websocket && websocket.readyState === WebSocket.OPEN) {
            websocket.send(JSON.stringify({
              type: 'input',
              data: data
            }))
          }
        })

        // Handle terminal resize
        term.onResize(({ cols, rows }) => {
          if (websocket && websocket.readyState === WebSocket.OPEN) {
            websocket.send(JSON.stringify({
              type: 'resize',
              cols: cols,
              rows: rows
            }))
          }
        })

        setWs(websocket)

      } catch (err) {
        console.error('Terminal init error:', err)
        setError(err.message)
        setLoading(false)
      }
    }

    initTerminal()

    // Handle window resize
    const handleResize = () => {
      if (fitAddonRef.current) {
        try {
          fitAddonRef.current.fit()
        } catch (e) {
          console.error('Fit error:', e)
        }
      }
    }
    window.addEventListener('resize', handleResize)

    // Cleanup
    return () => {
      mounted = false
      window.removeEventListener('resize', handleResize)
      if (websocket) {
        websocket.close()
      }
      if (term) {
        term.dispose()
      }
    }
  }, [nodeId])

  const handleClose = () => {
    if (ws) {
      ws.close()
    }
    navigate('/nodes')
  }

  const toggleFullscreen = () => {
    setFullscreen(!fullscreen)
    setTimeout(() => {
      if (fitAddonRef.current) {
        try {
          fitAddonRef.current.fit()
        } catch (e) {
          console.error('Fit error:', e)
        }
      }
    }, 100)
  }

  if (loading) {
    return (
      <div className="h-full bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-400">Loading terminal...</p>
        </div>
      </div>
    )
  }

  if (error && !terminal) {
    return (
      <div className="h-full bg-gray-900 flex items-center justify-center">
        <div className="text-center max-w-md">
          <FiAlertCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-white mb-2">Terminal Error</h2>
          <p className="text-gray-400 mb-4">{error}</p>
          <button
            onClick={handleClose}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition"
          >
            Back to Nodes
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className={`${fullscreen ? 'fixed inset-0 z-50' : 'h-full'} bg-gray-900 flex flex-col`}>
      {/* Header */}
      <div className="bg-gray-800 border-b border-gray-700 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <div className={`w-3 h-3 rounded-full ${connected ? 'bg-green-500' : 'bg-gray-500'}`}></div>
            <span className="text-white font-medium">
              {connected ? 'Connected' : 'Connecting...'}
            </span>
          </div>
          {error && (
            <span className="text-red-400 text-sm">({error})</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={toggleFullscreen}
            className="p-2 hover:bg-gray-700 rounded text-gray-400 hover:text-white transition"
            title={fullscreen ? 'Exit fullscreen' : 'Fullscreen'}
          >
            {fullscreen ? <FiMinimize2 className="w-5 h-5" /> : <FiMaximize2 className="w-5 h-5" />}
          </button>
          <button
            onClick={handleClose}
            className="p-2 hover:bg-gray-700 rounded text-gray-400 hover:text-white transition"
            title="Close terminal"
          >
            <FiX className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Terminal */}
      <div className="flex-1 p-4 overflow-hidden">
        <div
          ref={terminalRef}
          className="h-full w-full rounded-lg"
          style={{ height: '100%' }}
        />
      </div>
    </div>
  )
}
