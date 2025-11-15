/**
 * ACL Rules Management Page
 * For: Marco @ Syneto/Orizon
 */

import { useState, useEffect } from 'react'
import { toast } from 'react-toastify'
import api from '../services/apiService'
import { FiPlus, FiRefreshCw, FiShield } from 'react-icons/fi'
import CreateACLModal from '../components/acl/CreateACLModal'
import ACLRuleCard from '../components/acl/ACLRuleCard'

export default function ACLPage() {
  const [rules, setRules] = useState([])
  const [loading, setLoading] = useState(true)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [filter, setFilter] = useState('all') // all, allow, deny, active, inactive

  useEffect(() => {
    loadRules()
  }, [])

  const loadRules = async () => {
    try {
      setLoading(true)
      const data = await api.getACLRules()
      setRules(data)
    } catch (error) {
      toast.error('Failed to load ACL rules')
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  const handleCreateRule = async (ruleData) => {
    try {
      const newRule = await api.createACLRule(ruleData)
      setRules(prev => [...prev, newRule])
      setShowCreateModal(false)
      toast.success('ACL rule created successfully')
    } catch (error) {
      toast.error('Failed to create ACL rule')
      console.error(error)
    }
  }

  const handleDeleteRule = async (ruleId) => {
    if (!confirm('Are you sure you want to delete this rule?')) return

    try {
      await api.deleteACLRule(ruleId)
      setRules(prev => prev.filter(r => r.id !== ruleId))
      toast.success('Rule deleted successfully')
    } catch (error) {
      toast.error('Failed to delete rule')
      console.error(error)
    }
  }

  const handleToggleRule = async (ruleId, currentlyActive) => {
    try {
      if (currentlyActive) {
        await api.disableACLRule(ruleId)
        toast.success('Rule disabled')
      } else {
        await api.enableACLRule(ruleId)
        toast.success('Rule enabled')
      }

      setRules(prev => prev.map(r =>
        r.id === ruleId ? { ...r, is_active: !currentlyActive } : r
      ))
    } catch (error) {
      toast.error('Failed to toggle rule')
      console.error(error)
    }
  }

  const filteredRules = rules.filter(rule => {
    if (filter === 'all') return true
    if (filter === 'allow') return rule.action === 'allow'
    if (filter === 'deny') return rule.action === 'deny'
    if (filter === 'active') return rule.is_active
    if (filter === 'inactive') return !rule.is_active
    return true
  })

  // Sort by priority
  const sortedRules = [...filteredRules].sort((a, b) => a.priority - b.priority)

  const stats = {
    total: rules.length,
    active: rules.filter(r => r.is_active).length,
    allow: rules.filter(r => r.action === 'allow').length,
    deny: rules.filter(r => r.action === 'deny').length,
  }

  if (loading) {
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
            <FiShield className="w-8 h-8" />
            Access Control Rules
          </h1>
          <p className="text-gray-400 mt-1">
            Zero Trust Network Access - Default Policy: DENY ALL
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={loadRules}
            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg flex items-center gap-2 transition"
          >
            <FiRefreshCw className="w-4 h-4" />
            Refresh
          </button>
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg flex items-center gap-2 transition"
          >
            <FiPlus className="w-4 h-4" />
            Create Rule
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatCard label="Total Rules" value={stats.total} color="blue" />
        <StatCard label="Active" value={stats.active} color="green" />
        <StatCard label="Allow Rules" value={stats.allow} color="emerald" />
        <StatCard label="Deny Rules" value={stats.deny} color="red" />
      </div>

      {/* Filter Tabs */}
      <div className="flex gap-2 border-b border-gray-700">
        {['all', 'active', 'inactive', 'allow', 'deny'].map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-4 py-2 capitalize transition ${
              filter === f
                ? 'text-blue-500 border-b-2 border-blue-500'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            {f}
          </button>
        ))}
      </div>

      {/* Rules List */}
      {sortedRules.length === 0 ? (
        <div className="text-center py-12 bg-gray-800 rounded-lg border border-gray-700">
          <FiShield className="w-16 h-16 text-gray-600 mx-auto mb-4" />
          <p className="text-gray-400 text-lg">No ACL rules found</p>
          <p className="text-gray-500 text-sm mt-2">
            Default policy: DENY ALL (Zero Trust)
          </p>
          <button
            onClick={() => setShowCreateModal(true)}
            className="mt-4 px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg"
          >
            Create your first rule
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {sortedRules.map(rule => (
            <ACLRuleCard
              key={rule.id}
              rule={rule}
              onDelete={() => handleDeleteRule(rule.id)}
              onToggle={() => handleToggleRule(rule.id, rule.is_active)}
            />
          ))}
        </div>
      )}

      {/* Create Modal */}
      {showCreateModal && (
        <CreateACLModal
          onClose={() => setShowCreateModal(false)}
          onCreate={handleCreateRule}
        />
      )}
    </div>
  )
}

function StatCard({ label, value, color }) {
  const colorClasses = {
    blue: 'bg-blue-500 bg-opacity-20 border-blue-500',
    green: 'bg-green-500 bg-opacity-20 border-green-500',
    emerald: 'bg-emerald-500 bg-opacity-20 border-emerald-500',
    red: 'bg-red-500 bg-opacity-20 border-red-500',
  }

  return (
    <div className={`p-4 rounded-lg border ${colorClasses[color]}`}>
      <p className="text-gray-400 text-sm">{label}</p>
      <p className="text-3xl font-bold text-white mt-1">{value}</p>
    </div>
  )
}
