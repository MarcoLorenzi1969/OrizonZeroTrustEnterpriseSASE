/**
 * Orizon Zero Trust Connect - RDP Direct Test Component
 * Placeholder for RDP connection testing
 */

import { useState } from 'react'
import { Monitor, Play, Loader2 } from 'lucide-react'

function RDPDirectTest({ nodeId, nodeName, onClose }) {
  const [connecting, setConnecting] = useState(false)

  const handleConnect = () => {
    setConnecting(true)
    // TODO: Implement actual RDP connection
    setTimeout(() => {
      setConnecting(false)
    }, 2000)
  }

  return (
    <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-10 h-10 bg-blue-500/20 rounded-lg flex items-center justify-center">
          <Monitor className="w-5 h-5 text-blue-400" />
        </div>
        <div>
          <h3 className="text-white font-semibold">RDP Connection</h3>
          <p className="text-sm text-slate-400">{nodeName || 'Remote Desktop'}</p>
        </div>
      </div>

      <div className="bg-slate-900 rounded-lg aspect-video flex items-center justify-center mb-4">
        {connecting ? (
          <div className="text-center">
            <Loader2 className="w-8 h-8 text-blue-400 animate-spin mx-auto mb-2" />
            <p className="text-slate-400">Connecting...</p>
          </div>
        ) : (
          <div className="text-center">
            <Monitor className="w-12 h-12 text-slate-600 mx-auto mb-2" />
            <p className="text-slate-500">Click Connect to start RDP session</p>
          </div>
        )}
      </div>

      <div className="flex gap-3">
        <button
          onClick={handleConnect}
          disabled={connecting}
          className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-600 text-white rounded-lg transition-colors"
        >
          <Play className="w-4 h-4" />
          {connecting ? 'Connecting...' : 'Connect'}
        </button>
        {onClose && (
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
          >
            Close
          </button>
        )}
      </div>
    </div>
  )
}

export default RDPDirectTest
