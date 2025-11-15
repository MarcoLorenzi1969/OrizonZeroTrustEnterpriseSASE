/**
 * Web Terminal Component using xterm.js
 * Provides SSH/RDP access via WebSocket
 * For: Marco @ Syneto/Orizon
 */

import { useEffect, useRef, useState } from 'react'
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import { WebLinksAddon } from '@xterm/addon-web-links'
import '@xterm/xterm/css/xterm.css'
import { X, Maximize2, Minimize2, Download, Copy } from 'lucide-react'

export default function WebTerminal({ nodeId, nodeName, onClose }) {
  const terminalRef = useRef(null)
  const terminalInstanceRef = useRef(null)
  const fitAddonRef = useRef(null)
  const wsRef = useRef(null)
  const [isConnected, setIsConnected] = useState(false)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [sessionId, setSessionId] = useState(null)

  useEffect(() => {
    // Initialize terminal
    const term = new Terminal({
      cursorBlink: true,
      fontSize: 14,
      fontFamily: 'Menlo, Monaco, "Courier New", monospace',
      theme: {
        background: '#1e293b',
        foreground: '#e2e8f0',
        cursor: '#3b82f6',
        cursorAccent: '#1e293b',
        selection: '#3b82f6',
        black: '#1e293b',
        red: '#ef4444',
        green: '#10b981',
        yellow: '#f59e0b',
        blue: '#3b82f6',
        magenta: '#a855f7',
        cyan: '#06b6d4',
        white: '#e2e8f0',
        brightBlack: '#475569',
        brightRed: '#f87171',
        brightGreen: '#34d399',
        brightYellow: '#fbbf24',
        brightBlue: '#60a5fa',
        brightMagenta: '#c084fc',
        brightCyan: '#22d3ee',
        brightWhite: '#f1f5f9'
      },
      scrollback: 1000,
      allowProposedApi: true
    })

    // Add addons
    const fitAddon = new FitAddon()
    const webLinksAddon = new WebLinksAddon()

    term.loadAddon(fitAddon)
    term.loadAddon(webLinksAddon)

    // Open terminal in DOM
    term.open(terminalRef.current)
    fitAddon.fit()

    terminalInstanceRef.current = term
    fitAddonRef.current = fitAddon

    // Show welcome message
    term.writeln('\x1b[1;34mOrizon Zero Trust Connect - Secure Remote Access\x1b[0m')
    term.writeln(`\x1b[1;32mConnecting to ${nodeName}...\x1b[0m`)
    term.writeln('')

    // Connect WebSocket
    connectWebSocket(term)

    // Handle resize
    const handleResize = () => {
      if (fitAddonRef.current) {
        fitAddonRef.current.fit()
        // Send resize to backend
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          wsRef.current.send(JSON.stringify({
            type: 'resize',
            cols: term.cols,
            rows: term.rows
          }))
        }
      }
    }

    window.addEventListener('resize', handleResize)

    // Cleanup
    return () => {
      window.removeEventListener('resize', handleResize)
      if (wsRef.current) {
        wsRef.current.close()
      }
      term.dispose()
    }
  }, [nodeId, nodeName])

  const connectWebSocket = (term) => {
    // Get API base URL and convert to WebSocket URL
    // Default to HTTPS for production (required for secure WebSocket)
    const apiBase = import.meta.env.VITE_API_BASE_URL || 'https://46.101.189.126/api/v1'
    // Correctly handle both http and https
    const protocol = apiBase.startsWith('https') ? 'wss' : 'ws'
    const wsUrl = apiBase.replace(/^https?:\/\//, `${protocol}://`) + `/terminal/${nodeId}`

    const token = localStorage.getItem('access_token')

    term.writeln(`\x1b[90mConnecting to ${wsUrl}...\x1b[0m`)

    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => {
      setIsConnected(true)
      term.writeln('\x1b[1;32m✓ Connected\x1b[0m')
      term.writeln('')

      // Send authentication
      ws.send(JSON.stringify({
        type: 'auth',
        token: token
      }))

      // Send initial terminal size
      ws.send(JSON.stringify({
        type: 'resize',
        cols: term.cols,
        rows: term.rows
      }))

      // Handle user input
      term.onData((data) => {
        ws.send(JSON.stringify({
          type: 'input',
          data: data
        }))
      })
    }

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data)

        switch (message.type) {
          case 'output':
            term.write(message.data)
            break
          case 'session_id':
            setSessionId(message.session_id)
            break
          case 'error':
            term.writeln(`\x1b[1;31mError: ${message.message}\x1b[0m`)
            break
          default:
            console.log('Unknown message type:', message.type)
        }
      } catch (error) {
        // If not JSON, treat as raw output
        term.write(event.data)
      }
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
      term.writeln('\x1b[1;31m✗ Connection error\x1b[0m')
      setIsConnected(false)
    }

    ws.onclose = () => {
      term.writeln('')
      term.writeln('\x1b[1;33m✗ Connection closed\x1b[0m')
      setIsConnected(false)
    }
  }

  const handleReconnect = () => {
    if (terminalInstanceRef.current) {
      terminalInstanceRef.current.writeln('')
      terminalInstanceRef.current.writeln('\x1b[1;34mReconnecting...\x1b[0m')
      connectWebSocket(terminalInstanceRef.current)
    }
  }

  const handleCopySelection = () => {
    if (terminalInstanceRef.current) {
      const selection = terminalInstanceRef.current.getSelection()
      if (selection) {
        navigator.clipboard.writeText(selection)
      }
    }
  }

  const handleDownloadSession = () => {
    // Download terminal session as text file
    if (terminalInstanceRef.current && sessionId) {
      const content = terminalInstanceRef.current.buffer.active.getLine(0)
      // In a real implementation, this would download the full session log from the backend
      console.log('Download session:', sessionId)
      alert('Session download will be implemented in the backend')
    }
  }

  const toggleFullscreen = () => {
    setIsFullscreen(!isFullscreen)
    setTimeout(() => {
      if (fitAddonRef.current) {
        fitAddonRef.current.fit()
      }
    }, 100)
  }

  return (
    <div
      className={`bg-slate-900 border border-slate-700 rounded-lg shadow-2xl flex flex-col ${
        isFullscreen ? 'fixed inset-4 z-50' : 'w-full h-full'
      }`}
    >
      {/* Terminal Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-700 bg-slate-800">
        <div className="flex items-center gap-3">
          <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`}></div>
          <span className="text-white font-semibold">{nodeName}</span>
          {sessionId && (
            <span className="text-xs text-slate-400 font-mono">Session: {sessionId.slice(0, 8)}</span>
          )}
        </div>

        <div className="flex items-center gap-2">
          {!isConnected && (
            <button
              onClick={handleReconnect}
              className="px-3 py-1 text-xs bg-blue-600 hover:bg-blue-500 text-white rounded transition"
            >
              Reconnect
            </button>
          )}

          <button
            onClick={handleCopySelection}
            className="p-2 hover:bg-slate-700 rounded transition text-slate-400 hover:text-white"
            title="Copy selection"
          >
            <Copy className="w-4 h-4" />
          </button>

          <button
            onClick={handleDownloadSession}
            className="p-2 hover:bg-slate-700 rounded transition text-slate-400 hover:text-white"
            title="Download session"
          >
            <Download className="w-4 h-4" />
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
            title="Close terminal"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Terminal */}
      <div
        ref={terminalRef}
        className="flex-1 p-4 overflow-hidden"
        style={{ minHeight: isFullscreen ? 'calc(100vh - 100px)' : '400px' }}
      />

      {/* Terminal Footer */}
      <div className="px-4 py-2 border-t border-slate-700 bg-slate-800 flex items-center justify-between text-xs text-slate-400">
        <div className="flex items-center gap-4">
          <span>Node ID: {nodeId}</span>
          {isConnected && (
            <span className="text-green-400">● Connected</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span>Orizon ZTC</span>
          <span>•</span>
          <span>Secure Terminal</span>
        </div>
      </div>
    </div>
  )
}
