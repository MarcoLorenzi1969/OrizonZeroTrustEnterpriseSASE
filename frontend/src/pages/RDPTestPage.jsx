/**
 * RDP Test Page
 * Standalone page for testing WebRDP component
 *
 * Route: /rdp-test
 */

import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import WebRDP from '../components/WebRDP'
import { Monitor, ArrowLeft, Info } from 'lucide-react'

export default function RDPTestPage() {
  const [searchParams] = useSearchParams()
  const [showRDP, setShowRDP] = useState(false)
  const [config, setConfig] = useState({
    nodeId: searchParams.get('nodeId') || 'test-node-001',
    nodeName: searchParams.get('nodeName') || 'Test Windows Server',
    rdpHost: searchParams.get('host') || '',
    rdpPort: parseInt(searchParams.get('port')) || 3389,
    tunnelPort: searchParams.get('tunnelPort') || null
  })

  const handleStartRDP = (e) => {
    e.preventDefault()
    setShowRDP(true)
  }

  const handleCloseRDP = () => {
    setShowRDP(false)
  }

  if (showRDP) {
    return (
      <div className="fixed inset-0 bg-slate-900 z-50">
        <WebRDP
          nodeId={config.nodeId}
          nodeName={config.nodeName}
          rdpHost={config.rdpHost}
          rdpPort={config.rdpPort}
          tunnelPort={config.tunnelPort}
          onClose={handleCloseRDP}
        />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-900 text-white p-8">
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <div className="flex items-center gap-4 mb-8">
          <a
            href="/dashboard"
            className="p-2 hover:bg-slate-800 rounded-lg transition"
          >
            <ArrowLeft className="w-5 h-5" />
          </a>
          <div className="flex items-center gap-3">
            <Monitor className="w-8 h-8 text-blue-400" />
            <div>
              <h1 className="text-2xl font-bold">Orizon RDP Test</h1>
              <p className="text-slate-400 text-sm">Web-based Remote Desktop Client</p>
            </div>
          </div>
        </div>

        {/* Info Box */}
        <div className="bg-blue-900/30 border border-blue-700 rounded-lg p-4 mb-8">
          <div className="flex gap-3">
            <Info className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-blue-200">
              <p className="font-medium mb-1">About WebRDP</p>
              <p className="text-blue-300">
                This is a web-based RDP client that connects to Windows servers through the Orizon RDP Proxy.
                It uses WebSocket for real-time communication and HTML5 Canvas for rendering.
              </p>
            </div>
          </div>
        </div>

        {/* Configuration Form */}
        <form onSubmit={handleStartRDP} className="bg-slate-800 rounded-lg p-6 space-y-6">
          <h2 className="text-lg font-semibold border-b border-slate-700 pb-3">Connection Settings</h2>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-slate-400 mb-2">Node ID</label>
              <input
                type="text"
                value={config.nodeId}
                onChange={(e) => setConfig({ ...config, nodeId: e.target.value })}
                className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-blue-500"
                placeholder="node-001"
              />
            </div>

            <div>
              <label className="block text-sm text-slate-400 mb-2">Node Name</label>
              <input
                type="text"
                value={config.nodeName}
                onChange={(e) => setConfig({ ...config, nodeName: e.target.value })}
                className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-blue-500"
                placeholder="Windows Server 2022"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-slate-400 mb-2">RDP Host (IP or Hostname)</label>
              <input
                type="text"
                value={config.rdpHost}
                onChange={(e) => setConfig({ ...config, rdpHost: e.target.value })}
                className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-blue-500"
                placeholder="192.168.1.100 or leave empty for mock"
              />
              <p className="text-xs text-slate-500 mt-1">Leave empty for mock/test mode</p>
            </div>

            <div>
              <label className="block text-sm text-slate-400 mb-2">RDP Port</label>
              <input
                type="number"
                value={config.rdpPort}
                onChange={(e) => setConfig({ ...config, rdpPort: parseInt(e.target.value) || 3389 })}
                className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-blue-500"
                placeholder="3389"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm text-slate-400 mb-2">Tunnel Port (optional)</label>
            <input
              type="text"
              value={config.tunnelPort || ''}
              onChange={(e) => setConfig({ ...config, tunnelPort: e.target.value || null })}
              className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-blue-500"
              placeholder="Leave empty if not using tunnel"
            />
            <p className="text-xs text-slate-500 mt-1">Use this when connecting through an SSH tunnel</p>
          </div>

          <div className="pt-4 border-t border-slate-700">
            <button
              type="submit"
              className="w-full bg-blue-600 hover:bg-blue-500 text-white font-medium py-3 rounded-lg transition flex items-center justify-center gap-2"
            >
              <Monitor className="w-5 h-5" />
              Launch RDP Session
            </button>
          </div>
        </form>

        {/* Quick Test Buttons */}
        <div className="mt-6 space-y-3">
          <h3 className="text-sm font-medium text-slate-400">Quick Test</h3>
          <div className="flex gap-3">
            <button
              onClick={() => {
                setConfig({
                  nodeId: 'mock-test',
                  nodeName: 'Mock RDP Server',
                  rdpHost: '',
                  rdpPort: 3389,
                  tunnelPort: null
                })
                setShowRDP(true)
              }}
              className="flex-1 bg-slate-800 hover:bg-slate-700 text-white py-2 px-4 rounded-lg transition text-sm"
            >
              Mock Mode (No Server)
            </button>
            <a
              href="/rdp.html"
              target="_blank"
              rel="noopener noreferrer"
              className="flex-1 bg-slate-800 hover:bg-slate-700 text-white py-2 px-4 rounded-lg transition text-sm text-center"
            >
              Open Standalone HTML
            </a>
          </div>
        </div>

        {/* Architecture Diagram */}
        <div className="mt-8 bg-slate-800 rounded-lg p-6">
          <h3 className="text-sm font-medium text-slate-400 mb-4">Architecture</h3>
          <pre className="text-xs text-slate-300 font-mono overflow-x-auto">
{`Browser (WebRDP.jsx)
    │ Canvas + WebSocket
    ▼
RDP Proxy (ws://hub:8766/rdp)
    │ node-rdpjs-2
    ▼
RDP Server (Windows)
    │ or SSH Tunnel
    ▼
Edge Node (via Orizon Tunnel)`}
          </pre>
        </div>
      </div>
    </div>
  )
}
