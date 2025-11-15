/**
 * Audit Logs Viewer Page
 * For: Marco @ Syneto/Orizon
 * Compliance: GDPR, NIS2, ISO 27001
 */

import { useState, useEffect } from 'react'
import { toast } from 'react-toastify'
import api from '../services/apiService'
import { FiDownload, FiRefreshCw, FiFilter, FiFileText } from 'react-icons/fi'
import AuditLogCard from '../components/audit/AuditLogCard'
import AuditFilters from '../components/audit/AuditFilters'

export default function AuditPage() {
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [showFilters, setShowFilters] = useState(false)
  const [showExportMenu, setShowExportMenu] = useState(false)
  const [filters, setFilters] = useState({
    action: '',
    user_id: '',
    start_date: '',
    end_date: '',
    ip_address: '',
    resource_type: '',
    limit: 100
  })
  const [stats, setStats] = useState(null)

  useEffect(() => {
    loadLogs()
    loadStats()
  }, [])

  // Close export menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (showExportMenu && !event.target.closest('.export-menu-container')) {
        setShowExportMenu(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [showExportMenu])

  const loadLogs = async (customFilters = null) => {
    try {
      setLoading(true)
      const filterParams = customFilters || filters

      // Remove empty filters
      const cleanFilters = Object.fromEntries(
        Object.entries(filterParams).filter(([_, v]) => v !== '' && v !== null)
      )

      const data = await api.getAuditLogs(cleanFilters)
      setLogs(data)
    } catch (error) {
      toast.error('Failed to load audit logs')
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  const loadStats = async () => {
    try {
      const data = await api.getAuditStatistics()
      setStats(data)
    } catch (error) {
      console.error('Failed to load statistics:', error)
    }
  }

  const handleApplyFilters = (newFilters) => {
    setFilters(newFilters)
    loadLogs(newFilters)
  }

  const handleExport = async (format) => {
    try {
      setShowExportMenu(false)
      toast.info(`Exporting audit logs as ${format.toUpperCase()}...`)

      const blob = await api.exportAuditLogs(format, filters)

      // Create download link
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `audit-logs-${new Date().toISOString()}.${format}`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)

      toast.success(`Audit logs exported successfully`)
    } catch (error) {
      toast.error('Failed to export audit logs')
      console.error(error)
    }
  }

  const statusCounts = logs.reduce((acc, log) => {
    acc[log.status] = (acc[log.status] || 0) + 1
    return acc
  }, {})

  if (loading && logs.length === 0) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-white flex items-center gap-3">
            <FiFileText className="w-8 h-8" />
            Audit Logs
          </h1>
          <p className="text-gray-400 mt-1">
            Compliance Logging: GDPR / NIS2 / ISO 27001 - Retention: 90 days
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`px-4 py-2 rounded-lg flex items-center gap-2 transition ${
              showFilters
                ? 'bg-blue-600 hover:bg-blue-700 text-white'
                : 'bg-gray-700 hover:bg-gray-600 text-white'
            }`}
          >
            <FiFilter className="w-4 h-4" />
            Filters
          </button>
          <button
            onClick={() => loadLogs()}
            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg flex items-center gap-2 transition"
          >
            <FiRefreshCw className="w-4 h-4" />
            Refresh
          </button>
          <div className="relative export-menu-container">
            <button
              onClick={() => setShowExportMenu(!showExportMenu)}
              className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg flex items-center gap-2 transition"
            >
              <FiDownload className="w-4 h-4" />
              Export
            </button>
            {showExportMenu && (
              <div className="absolute right-0 mt-1 w-48 bg-gray-800 border border-gray-700 rounded-lg shadow-lg z-10 animate-fadeIn">
                <button
                  onClick={() => handleExport('json')}
                  className="w-full px-4 py-2 text-left text-white hover:bg-gray-700 rounded-t-lg transition"
                >
                  Export as JSON
                </button>
                <button
                  onClick={() => handleExport('csv')}
                  className="w-full px-4 py-2 text-left text-white hover:bg-gray-700 transition"
                >
                  Export as CSV
                </button>
                <button
                  onClick={() => handleExport('siem')}
                  className="w-full px-4 py-2 text-left text-white hover:bg-gray-700 rounded-b-lg transition"
                >
                  Export for SIEM (CEF)
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Statistics Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <StatCard label="Total Events" value={logs.length} color="blue" />
          <StatCard label="Last 24h" value={stats.last_24h || 0} color="purple" />
          <StatCard label="Failed" value={stats.failed_actions || 0} color="red" />
          <StatCard label="Success" value={statusCounts.success || 0} color="green" />
        </div>
      )}

      {/* Filters Panel */}
      {showFilters && (
        <AuditFilters
          filters={filters}
          onApply={handleApplyFilters}
          onReset={() => {
            const resetFilters = {
              action: '',
              user_id: '',
              start_date: '',
              end_date: '',
              ip_address: '',
              resource_type: '',
              limit: 100
            }
            setFilters(resetFilters)
            loadLogs(resetFilters)
          }}
        />
      )}

      {/* Logs List */}
      {logs.length === 0 ? (
        <div className="text-center py-12 bg-gray-800 rounded-lg border border-gray-700">
          <FiFileText className="w-16 h-16 text-gray-600 mx-auto mb-4" />
          <p className="text-gray-400 text-lg">No audit logs found</p>
          <p className="text-gray-500 text-sm mt-2">
            Try adjusting your filters or refresh the page
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {logs.map(log => (
            <AuditLogCard key={log.id} log={log} />
          ))}
        </div>
      )}

      {/* Loading indicator */}
      {loading && logs.length > 0 && (
        <div className="text-center py-4">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto"></div>
        </div>
      )}
    </div>
  )
}

function StatCard({ label, value, color }) {
  const colorClasses = {
    blue: 'bg-blue-500 bg-opacity-20 border-blue-500',
    red: 'bg-red-500 bg-opacity-20 border-red-500',
    orange: 'bg-orange-500 bg-opacity-20 border-orange-500',
    yellow: 'bg-yellow-500 bg-opacity-20 border-yellow-500',
    green: 'bg-green-500 bg-opacity-20 border-green-500',
    purple: 'bg-purple-500 bg-opacity-20 border-purple-500',
  }

  return (
    <div className={`p-4 rounded-lg border ${colorClasses[color]}`}>
      <p className="text-gray-400 text-sm">{label}</p>
      <p className="text-2xl font-bold text-white mt-1">{value}</p>
    </div>
  )
}
