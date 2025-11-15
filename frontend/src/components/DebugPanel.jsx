/**
 * Debug Panel Component - Visual Debug Interface
 * For: Marco @ Syneto/Orizon
 *
 * Press Ctrl+Shift+D to toggle
 */

import { useState, useEffect } from 'react'
import { FiX, FiDownload, FiCopy, FiTrash2, FiRefreshCw, FiInfo } from 'react-icons/fi'
import debugService from '../services/debugService'

export default function DebugPanel() {
  const [isOpen, setIsOpen] = useState(false)
  const [logs, setLogs] = useState([])
  const [filter, setFilter] = useState('all')
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [systemInfo, setSystemInfo] = useState(null)

  useEffect(() => {
    // Keyboard shortcut: Ctrl+Shift+D
    const handleKeyDown = (e) => {
      if (e.ctrlKey && e.shiftKey && e.key === 'D') {
        e.preventDefault()
        setIsOpen(prev => !prev)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  useEffect(() => {
    if (isOpen) {
      loadLogs()
      setSystemInfo(debugService.getSystemInfo())

      if (autoRefresh) {
        const interval = setInterval(loadLogs, 2000)
        return () => clearInterval(interval)
      }
    }
  }, [isOpen, autoRefresh, filter])

  const loadLogs = () => {
    let allLogs = debugService.getRecentLogs(100)
    if (filter !== 'all') {
      allLogs = allLogs.filter(log => log.level === filter)
    }
    setLogs(allLogs.reverse()) // Show newest first
  }

  const handleExport = () => {
    debugService.exportLogs()
  }

  const handleCopy = () => {
    debugService.copyLogsToClipboard()
  }

  const handleClear = () => {
    if (confirm('Are you sure you want to clear all logs?')) {
      debugService.clearLogs()
      loadLogs()
    }
  }

  const getLevelColor = (level) => {
    const colors = {
      debug: 'text-gray-400',
      info: 'text-blue-400',
      warn: 'text-yellow-400',
      error: 'text-red-400',
      success: 'text-green-400'
    }
    return colors[level] || 'text-gray-400'
  }

  const getLevelBg = (level) => {
    const colors = {
      debug: 'bg-gray-900',
      info: 'bg-blue-900/20',
      warn: 'bg-yellow-900/20',
      error: 'bg-red-900/20',
      success: 'bg-green-900/20'
    }
    return colors[level] || 'bg-gray-900'
  }

  if (!isOpen) {
    return (
      <div className="fixed bottom-4 right-4 z-50">
        <button
          onClick={() => setIsOpen(true)}
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg shadow-lg flex items-center gap-2 transition-all"
          title="Open Debug Panel (Ctrl+Shift+D)"
        >
          <FiInfo className="w-5 h-5" />
          <span>Debug</span>
        </button>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 backdrop-blur-sm">
      <div className="bg-gray-900 border border-gray-700 rounded-xl shadow-2xl w-11/12 h-5/6 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <div className="flex items-center gap-4">
            <h2 className="text-xl font-bold text-white">Debug Panel</h2>
            <div className="flex gap-2">
              <button
                onClick={() => setFilter('all')}
                className={`px-3 py-1 rounded text-sm ${
                  filter === 'all' ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400'
                }`}
              >
                All ({debugService.logs.length})
              </button>
              <button
                onClick={() => setFilter('error')}
                className={`px-3 py-1 rounded text-sm ${
                  filter === 'error' ? 'bg-red-600 text-white' : 'bg-gray-800 text-gray-400'
                }`}
              >
                Errors ({debugService.getLogsByLevel('error').length})
              </button>
              <button
                onClick={() => setFilter('warn')}
                className={`px-3 py-1 rounded text-sm ${
                  filter === 'warn' ? 'bg-yellow-600 text-white' : 'bg-gray-800 text-gray-400'
                }`}
              >
                Warnings ({debugService.getLogsByLevel('warn').length})
              </button>
              <button
                onClick={() => setFilter('info')}
                className={`px-3 py-1 rounded text-sm ${
                  filter === 'info' ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400'
                }`}
              >
                Info ({debugService.getLogsByLevel('info').length})
              </button>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={`p-2 rounded transition ${
                autoRefresh ? 'bg-green-600 text-white' : 'bg-gray-800 text-gray-400'
              }`}
              title={autoRefresh ? 'Auto-refresh ON' : 'Auto-refresh OFF'}
            >
              <FiRefreshCw className={`w-4 h-4 ${autoRefresh ? 'animate-spin' : ''}`} />
            </button>
            <button
              onClick={handleCopy}
              className="p-2 bg-gray-800 hover:bg-gray-700 text-white rounded transition"
              title="Copy logs to clipboard"
            >
              <FiCopy className="w-4 h-4" />
            </button>
            <button
              onClick={handleExport}
              className="p-2 bg-gray-800 hover:bg-gray-700 text-white rounded transition"
              title="Export logs"
            >
              <FiDownload className="w-4 h-4" />
            </button>
            <button
              onClick={handleClear}
              className="p-2 bg-red-600 hover:bg-red-700 text-white rounded transition"
              title="Clear logs"
            >
              <FiTrash2 className="w-4 h-4" />
            </button>
            <button
              onClick={() => setIsOpen(false)}
              className="p-2 bg-gray-800 hover:bg-gray-700 text-white rounded transition"
              title="Close (Ctrl+Shift+D)"
            >
              <FiX className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* System Info */}
        {systemInfo && (
          <div className="p-4 bg-gray-800/50 border-b border-gray-700 text-xs">
            <div className="grid grid-cols-4 gap-4 text-gray-400">
              <div>
                <span className="font-semibold text-gray-300">Platform:</span> {systemInfo.platform}
              </div>
              <div>
                <span className="font-semibold text-gray-300">Screen:</span> {systemInfo.screenResolution}
              </div>
              <div>
                <span className="font-semibold text-gray-300">Memory:</span> {systemInfo.memory.used} / {systemInfo.memory.total}
              </div>
              <div>
                <span className="font-semibold text-gray-300">Token:</span>{' '}
                {systemInfo.localStorage.hasToken ? (
                  <span className="text-green-400">Present ({systemInfo.localStorage.tokenLength} chars)</span>
                ) : (
                  <span className="text-red-400">Missing</span>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Logs */}
        <div className="flex-1 overflow-y-auto p-4 space-y-2 font-mono text-sm">
          {logs.length === 0 ? (
            <div className="text-center text-gray-500 py-8">No logs to display</div>
          ) : (
            logs.map((log, index) => (
              <div
                key={index}
                className={`${getLevelBg(log.level)} border border-gray-700 rounded p-3 hover:border-gray-600 transition`}
              >
                <div className="flex items-start justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <span className={`font-bold ${getLevelColor(log.level)}`}>
                      [{log.level.toUpperCase()}]
                    </span>
                    <span className="text-white font-semibold">{log.category}</span>
                  </div>
                  <span className="text-gray-500 text-xs">
                    {new Date(log.timestamp).toLocaleTimeString()}
                  </span>
                </div>
                <div className="text-gray-300 whitespace-pre-wrap break-all">
                  {typeof log.data === 'object'
                    ? JSON.stringify(log.data, null, 2)
                    : String(log.data)}
                </div>
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-gray-700 bg-gray-800/50 text-xs text-gray-400 text-center">
          Press <kbd className="px-2 py-1 bg-gray-700 rounded">Ctrl</kbd> +{' '}
          <kbd className="px-2 py-1 bg-gray-700 rounded">Shift</kbd> +{' '}
          <kbd className="px-2 py-1 bg-gray-700 rounded">D</kbd> to toggle Debug Panel
        </div>
      </div>
    </div>
  )
}
