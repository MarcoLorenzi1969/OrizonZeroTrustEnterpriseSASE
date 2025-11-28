/**
 * Orizon Zero Trust Connect - Guacamole Remote Desktop Page
 * Placeholder for Apache Guacamole integration
 */

import { Monitor, Construction } from 'lucide-react'

function GuacamolePage() {
  return (
    <div className="flex flex-col items-center justify-center h-96">
      <div className="bg-slate-800 border border-slate-700 rounded-xl p-8 text-center max-w-md">
        <div className="w-16 h-16 bg-blue-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
          <Monitor className="w-8 h-8 text-blue-400" />
        </div>
        <h2 className="text-xl font-bold text-white mb-2">Remote Desktop</h2>
        <p className="text-slate-400 mb-4">
          Apache Guacamole integration for browser-based remote desktop access.
        </p>
        <div className="flex items-center justify-center gap-2 text-yellow-400 text-sm">
          <Construction className="w-4 h-4" />
          <span>Coming soon</span>
        </div>
      </div>
    </div>
  )
}

export default GuacamolePage
