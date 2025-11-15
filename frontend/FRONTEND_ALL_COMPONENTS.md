# 🎨 ORIZON ZERO TRUST CONNECT - TUTTI I COMPONENTI FRONTEND

## Per: Marco Lorenzi @ Syneto/Orizon

**DOCUMENTO COMPLETO CON TUTTI I FILE RIMANENTI**

Questo documento contiene TUTTI i componenti frontend necessari per completare l'applicazione al 100%.

---

## 📁 INDICE COMPONENTI

1. [ACL Components](#1-acl-components)
2. [Audit Logs Components](#2-audit-logs-components)
3. [Settings Page](#3-settings-page)
4. [Navigation Layout](#4-navigation-layout)
5. [Dashboard Components](#5-dashboard-components)
6. [Nodes Page](#6-nodes-page)
7. [Redux Slices Complete](#7-redux-slices-complete)
8. [Utility Functions](#8-utility-functions)
9. [Package.json Updated](#9-packagejson-updated)

---

## 1. ACL COMPONENTS

### `src/components/acl/ACLRuleCard.jsx`

```jsx
import { FiTrash2, FiToggleLeft, FiToggleRight, FiArrowRight } from 'react-icons/fi'

export default function ACLRuleCard({ rule, onDelete, onToggle }) {
  const isAllow = rule.action === 'allow'

  return (
    <div className={`bg-gray-800 rounded-lg p-4 border-l-4 ${
      isAllow ? 'border-green-500' : 'border-red-500'
    }`}>
      <div className="flex items-center justify-between">
        {/* Left: Rule Info */}
        <div className="flex items-center gap-4 flex-1">
          {/* Priority Badge */}
          <div className="bg-gray-700 px-3 py-1 rounded text-sm font-mono">
            P{rule.priority}
          </div>

          {/* Source → Dest */}
          <div className="flex items-center gap-2 flex-1">
            <div className="bg-blue-500 bg-opacity-20 px-3 py-1 rounded text-sm">
              {rule.source_node_id === '*' ? 'ANY' : rule.source_node_id}
            </div>
            <FiArrowRight className="text-gray-500" />
            <div className="bg-purple-500 bg-opacity-20 px-3 py-1 rounded text-sm">
              {rule.dest_node_id === '*' ? 'ANY' : rule.dest_node_id}
            </div>
          </div>

          {/* Protocol:Port */}
          <div className="text-sm text-gray-300">
            <span className="font-mono">{rule.protocol || 'any'}</span>
            {rule.port > 0 && <span className="text-gray-500">:{rule.port}</span>}
          </div>

          {/* Action Badge */}
          <div className={`px-3 py-1 rounded-full text-sm font-semibold ${
            isAllow
              ? 'bg-green-500 bg-opacity-20 text-green-400'
              : 'bg-red-500 bg-opacity-20 text-red-400'
          }`}>
            {rule.action.toUpperCase()}
          </div>

          {/* Status */}
          <div className="flex items-center gap-1">
            {rule.is_active ? (
              <span className="text-xs text-green-500">● Active</span>
            ) : (
              <span className="text-xs text-gray-500">○ Inactive</span>
            )}
          </div>
        </div>

        {/* Right: Actions */}
        <div className="flex items-center gap-2">
          <button
            onClick={onToggle}
            className="p-2 text-gray-400 hover:text-blue-500 transition"
            title={rule.is_active ? 'Disable rule' : 'Enable rule'}
          >
            {rule.is_active ? (
              <FiToggleRight className="w-5 h-5" />
            ) : (
              <FiToggleLeft className="w-5 h-5" />
            )}
          </button>
          <button
            onClick={onDelete}
            className="p-2 text-gray-400 hover:text-red-500 transition"
            title="Delete rule"
          >
            <FiTrash2 className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Description */}
      {rule.description && (
        <div className="mt-2 pl-16 text-sm text-gray-400">
          {rule.description}
        </div>
      )}
    </div>
  )
}
```

### `src/components/acl/CreateACLModal.jsx`

```jsx
import { useState, useEffect } from 'react'
import { FiX } from 'react-icons/fi'
import api from '../../services/apiService'

export default function CreateACLModal({ onClose, onCreate }) {
  const [formData, setFormData] = useState({
    source_node_id: '',
    dest_node_id: '',
    protocol: 'tcp',
    port: 22,
    action: 'allow',
    priority: 50,
    description: ''
  })
  const [nodes, setNodes] = useState([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    loadNodes()
  }, [])

  const loadNodes = async () => {
    try {
      const data = await api.getNodes()
      setNodes(data)
    } catch (error) {
      console.error('Failed to load nodes:', error)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      await onCreate(formData)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-800 rounded-lg max-w-3xl w-full">
        <div className="flex justify-between items-center p-6 border-b border-gray-700">
          <h2 className="text-2xl font-bold text-white">Create ACL Rule</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-white">
            <FiX className="w-6 h-6" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {/* Source and Destination */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Source Node *
              </label>
              <select
                required
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white"
                value={formData.source_node_id}
                onChange={(e) => setFormData({ ...formData, source_node_id: e.target.value })}
              >
                <option value="">Select node</option>
                <option value="*">ANY (wildcard)</option>
                {nodes.map(node => (
                  <option key={node.id} value={node.id}>{node.name}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Destination Node *
              </label>
              <select
                required
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white"
                value={formData.dest_node_id}
                onChange={(e) => setFormData({ ...formData, dest_node_id: e.target.value })}
              >
                <option value="">Select node</option>
                <option value="*">ANY (wildcard)</option>
                {nodes.map(node => (
                  <option key={node.id} value={node.id}>{node.name}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Protocol and Port */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Protocol *
              </label>
              <select
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white"
                value={formData.protocol}
                onChange={(e) => setFormData({ ...formData, protocol: e.target.value })}
              >
                <option value="tcp">TCP</option>
                <option value="udp">UDP</option>
                <option value="ssh">SSH</option>
                <option value="https">HTTPS</option>
                <option value="any">ANY</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Port (0 = any)
              </label>
              <input
                type="number"
                min="0"
                max="65535"
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white"
                value={formData.port}
                onChange={(e) => setFormData({ ...formData, port: parseInt(e.target.value) })}
              />
            </div>
          </div>

          {/* Action */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Action *
            </label>
            <div className="grid grid-cols-2 gap-4">
              <button
                type="button"
                onClick={() => setFormData({ ...formData, action: 'allow' })}
                className={`p-4 rounded-lg border-2 transition ${
                  formData.action === 'allow'
                    ? 'border-green-500 bg-green-500 bg-opacity-20'
                    : 'border-gray-600 hover:border-gray-500'
                }`}
              >
                <div className="text-2xl mb-1">✅</div>
                <div className="text-white font-semibold">ALLOW</div>
                <div className="text-sm text-gray-400">Permit traffic</div>
              </button>
              <button
                type="button"
                onClick={() => setFormData({ ...formData, action: 'deny' })}
                className={`p-4 rounded-lg border-2 transition ${
                  formData.action === 'deny'
                    ? 'border-red-500 bg-red-500 bg-opacity-20'
                    : 'border-gray-600 hover:border-gray-500'
                }`}
              >
                <div className="text-2xl mb-1">🚫</div>
                <div className="text-white font-semibold">DENY</div>
                <div className="text-sm text-gray-400">Block traffic</div>
              </button>
            </div>
          </div>

          {/* Priority */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Priority (1 = highest, 100 = lowest) *
            </label>
            <input
              type="number"
              min="1"
              max="100"
              required
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white"
              value={formData.priority}
              onChange={(e) => setFormData({ ...formData, priority: parseInt(e.target.value) })}
            />
            <p className="text-xs text-gray-400 mt-1">
              Lower numbers = higher priority. Rules are evaluated in priority order.
            </p>
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Description
            </label>
            <textarea
              rows="2"
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white"
              placeholder="Optional description for this rule..."
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            />
          </div>

          {/* Buttons */}
          <div className="flex justify-end gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-6 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg disabled:opacity-50"
            >
              {loading ? 'Creating...' : 'Create Rule'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
```

---

## 2. AUDIT LOGS COMPONENTS

### `src/pages/AuditPage.jsx`

```jsx
import { useState, useEffect } from 'react'
import { toast } from 'react-toastify'
import api from '../services/apiService'
import { FiDownload, FiFilter, FiRefreshCw } from 'react-icons/fi'
import AuditFilters from '../components/audit/AuditFilters'
import AuditLogCard from '../components/audit/AuditLogCard'

export default function AuditPage() {
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [showFilters, setShowFilters] = useState(false)
  const [filters, setFilters] = useState({
    user_id: '',
    action: '',
    start_date: '',
    end_date: '',
    severity: '',
    search: ''
  })
  const [pagination, setPagination] = useState({
    skip: 0,
    limit: 50,
    total: 0
  })

  useEffect(() => {
    loadLogs()
  }, [filters, pagination.skip])

  const loadLogs = async () => {
    try {
      setLoading(true)
      const { logs: data, total } = await api.getAuditLogs({
        ...filters,
        skip: pagination.skip,
        limit: pagination.limit
      })
      setLogs(data)
      setPagination(prev => ({ ...prev, total }))
    } catch (error) {
      toast.error('Failed to load audit logs')
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  const handleExport = async (format) => {
    try {
      const blob = await api.exportAuditLogs(format, filters)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `audit_logs_${Date.now()}.${format}`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
      toast.success(`Exported ${format.toUpperCase()} successfully`)
    } catch (error) {
      toast.error('Failed to export logs')
      console.error(error)
    }
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-white">Audit Logs</h1>
          <p className="text-gray-400 mt-1">
            Security and compliance audit trail
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg flex items-center gap-2"
          >
            <FiFilter className="w-4 h-4" />
            Filters
          </button>
          <button
            onClick={loadLogs}
            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg flex items-center gap-2"
          >
            <FiRefreshCw className="w-4 h-4" />
            Refresh
          </button>
          <div className="relative group">
            <button className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg flex items-center gap-2">
              <FiDownload className="w-4 h-4" />
              Export
            </button>
            <div className="absolute right-0 mt-2 w-48 bg-gray-800 rounded-lg shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all">
              <button
                onClick={() => handleExport('json')}
                className="w-full px-4 py-2 text-left text-white hover:bg-gray-700 rounded-t-lg"
              >
                Export JSON
              </button>
              <button
                onClick={() => handleExport('csv')}
                className="w-full px-4 py-2 text-left text-white hover:bg-gray-700"
              >
                Export CSV
              </button>
              <button
                onClick={() => handleExport('siem')}
                className="w-full px-4 py-2 text-left text-white hover:bg-gray-700 rounded-b-lg"
              >
                Export SIEM (CEF)
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Filters */}
      {showFilters && (
        <AuditFilters
          filters={filters}
          onChange={setFilters}
          onReset={() => setFilters({
            user_id: '',
            action: '',
            start_date: '',
            end_date: '',
            severity: '',
            search: ''
          })}
        />
      )}

      {/* Logs List */}
      {loading ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
        </div>
      ) : logs.length === 0 ? (
        <div className="text-center py-12 bg-gray-800 rounded-lg">
          <p className="text-gray-400">No audit logs found</p>
        </div>
      ) : (
        <div className="space-y-2">
          {logs.map(log => (
            <AuditLogCard key={log.id} log={log} />
          ))}
        </div>
      )}

      {/* Pagination */}
      {pagination.total > pagination.limit && (
        <div className="flex justify-center gap-2">
          <button
            disabled={pagination.skip === 0}
            onClick={() => setPagination(prev => ({ ...prev, skip: Math.max(0, prev.skip - prev.limit) }))}
            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg disabled:opacity-50"
          >
            Previous
          </button>
          <span className="px-4 py-2 text-gray-400">
            {pagination.skip + 1} - {Math.min(pagination.skip + pagination.limit, pagination.total)} of {pagination.total}
          </span>
          <button
            disabled={pagination.skip + pagination.limit >= pagination.total}
            onClick={() => setPagination(prev => ({ ...prev, skip: prev.skip + prev.limit }))}
            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg disabled:opacity-50"
          >
            Next
          </button>
        </div>
      )}
    </div>
  )
}
```

---

**NOTA:** Il file è troppo lungo per un singolo messaggio. Ho creato i componenti principali.

Vuoi che:
1. **Continui nel prossimo messaggio** con Settings, Navigation e Redux slices rimanenti?
2. Oppure **procediamo al testing** di quanto fatto?

Dimmi come preferisci procedere! 🚀
