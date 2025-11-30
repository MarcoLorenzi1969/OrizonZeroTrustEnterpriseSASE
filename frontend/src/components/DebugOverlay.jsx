/**
 * Orizon Debug Overlay - Visual debugging panel
 * Shows real-time logs, API calls, component renders
 */

import { useState, useEffect, useRef } from 'react'
import { getLogs, clearLogs } from '../utils/debugLogger'
import { X, Trash2, ChevronDown, ChevronUp, Bug, Activity, Database, Layout, AlertCircle } from 'lucide-react'

export default function DebugOverlay() {
  const [isOpen, setIsOpen] = useState(false)
  const [isMinimized, setIsMinimized] = useState(false)
  const [logs, setLogs] = useState([])
  const [filter, setFilter] = useState('all')
  const [autoScroll, setAutoScroll] = useState(true)
  const logsEndRef = useRef(null)

  // Listen for new logs
  useEffect(() => {
    const handleNewLog = (event) => {
      setLogs(prev => [event.detail, ...prev].slice(0, 100))
    }

    window.addEventListener('debug-log', handleNewLog)
    return () => window.removeEventListener('debug-log', handleNewLog)
  }, [])

  // Initial load
  useEffect(() => {
    setLogs(getLogs())
  }, [isOpen])

  // Auto scroll
  useEffect(() => {
    if (autoScroll && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [logs, autoScroll])

  const handleClear = () => {
    clearLogs()
    setLogs([])
  }

  const filteredLogs = filter === 'all'
    ? logs
    : logs.filter(log => log.type === filter)

  const getIcon = (type) => {
    switch (type) {
      case 'api': return <Activity className="w-3 h-3" />
      case 'render': return <Layout className="w-3 h-3" />
      case 'state': return <Database className="w-3 h-3" />
      case 'error': return <AlertCircle className="w-3 h-3" />
      default: return <Bug className="w-3 h-3" />
    }
  }

  const counts = {
    all: logs.length,
    api: logs.filter(l => l.type === 'api').length,
    render: logs.filter(l => l.type === 'render').length,
    state: logs.filter(l => l.type === 'state').length,
    error: logs.filter(l => l.type === 'error').length,
    data: logs.filter(l => l.type === 'data').length,
  }

  // Toggle button (always visible)
  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-4 right-4 z-[9999] flex items-center gap-2 px-3 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg shadow-lg transition-all"
      >
        <Bug className="w-4 h-4" />
        <span className="text-sm font-medium">Debug</span>
        {counts.error > 0 && (
          <span className="px-1.5 py-0.5 bg-red-500 text-xs rounded-full">{counts.error}</span>
        )}
      </button>
    )
  }

  return (
    <div className={`fixed bottom-0 right-0 z-[9999] ${isMinimized ? 'w-80' : 'w-[600px]'} bg-slate-900 border border-slate-700 rounded-tl-xl shadow-2xl transition-all`}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 bg-slate-800 border-b border-slate-700 rounded-tl-xl">
        <div className="flex items-center gap-2">
          <Bug className="w-4 h-4 text-purple-400" />
          <span className="text-white font-bold text-sm">Orizon Debug</span>
          <span className="text-xs text-slate-400">({counts.all} logs)</span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={handleClear}
            className="p-1.5 hover:bg-slate-700 rounded transition-colors"
            title="Clear logs"
          >
            <Trash2 className="w-4 h-4 text-slate-400" />
          </button>
          <button
            onClick={() => setIsMinimized(!isMinimized)}
            className="p-1.5 hover:bg-slate-700 rounded transition-colors"
          >
            {isMinimized ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
          </button>
          <button
            onClick={() => setIsOpen(false)}
            className="p-1.5 hover:bg-slate-700 rounded transition-colors"
          >
            <X className="w-4 h-4 text-slate-400" />
          </button>
        </div>
      </div>

      {!isMinimized && (
        <>
          {/* Filter tabs */}
          <div className="flex gap-1 px-2 py-2 bg-slate-800/50 border-b border-slate-700 overflow-x-auto">
            {Object.entries(counts).map(([type, count]) => (
              <button
                key={type}
                onClick={() => setFilter(type)}
                className={`flex items-center gap-1 px-2 py-1 rounded text-xs font-medium transition-colors whitespace-nowrap ${
                  filter === type
                    ? 'bg-purple-600 text-white'
                    : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                }`}
              >
                {type === 'all' ? 'All' : type.charAt(0).toUpperCase() + type.slice(1)}
                <span className={`px-1 rounded ${filter === type ? 'bg-purple-500' : 'bg-slate-600'}`}>
                  {count}
                </span>
              </button>
            ))}
          </div>

          {/* Logs */}
          <div className="h-80 overflow-y-auto p-2 space-y-1 font-mono text-xs">
            {filteredLogs.length === 0 ? (
              <div className="text-center text-slate-500 py-8">
                No logs yet. Interact with the app to see debug info.
              </div>
            ) : (
              filteredLogs.map((log) => (
                <LogEntry key={log.id} log={log} getIcon={getIcon} />
              ))
            )}
            <div ref={logsEndRef} />
          </div>

          {/* Footer */}
          <div className="flex items-center justify-between px-3 py-2 bg-slate-800 border-t border-slate-700 text-xs text-slate-400">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={autoScroll}
                onChange={(e) => setAutoScroll(e.target.checked)}
                className="rounded border-slate-600"
              />
              Auto-scroll
            </label>
            <span>Press F12 for full console</span>
          </div>
        </>
      )}
    </div>
  )
}

function LogEntry({ log, getIcon }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div
      className="bg-slate-800/50 rounded border border-slate-700/50 hover:border-slate-600 transition-colors"
    >
      <div
        className="flex items-start gap-2 px-2 py-1.5 cursor-pointer"
        onClick={() => log.data && setExpanded(!expanded)}
      >
        <span className="text-slate-500 shrink-0">{log.time}</span>
        <span style={{ color: log.color }} className="shrink-0">
          {getIcon(log.type)}
        </span>
        <span style={{ color: log.color }} className="font-medium shrink-0">
          [{log.category}]
        </span>
        <span className="text-slate-300 truncate flex-1">
          {log.message}
        </span>
        {log.data && (
          <span className="text-slate-500 shrink-0">
            {expanded ? '▼' : '▶'}
          </span>
        )}
      </div>
      {expanded && log.data && (
        <div className="px-2 py-2 border-t border-slate-700/50 bg-slate-900/50">
          <pre className="text-xs text-slate-400 overflow-x-auto whitespace-pre-wrap">
            {JSON.stringify(log.data, null, 2)}
          </pre>
        </div>
      )}
    </div>
  )
}
