import { useState, useEffect } from 'react'
import { Users, Plus, Settings, Trash2, X, UserPlus, Server, Lock, Terminal, Monitor } from 'lucide-react'
import api from '../services/api'
import toast from 'react-hot-toast'
import CreateGroupModal from '../components/groups/CreateGroupModal'
import ManageGroupModal from '../components/groups/ManageGroupModal'
import { debugReact, debugData } from '../utils/debugLogger'

function GroupsPage() {
  const [groups, setGroups] = useState([])
  const [loading, setLoading] = useState(true)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [selectedGroup, setSelectedGroup] = useState(null)
  const [showManageModal, setShowManageModal] = useState(false)

  useEffect(() => {
    loadGroups()
  }, [])

  const loadGroups = async () => {
    try {
      debugReact.render('GroupsPage', 'Loading groups')
      const response = await api.get('/groups')
      const groupsData = response.data.groups || []
      debugData.received('GroupsPage.loadGroups', groupsData)
      setGroups(groupsData)
    } catch (error) {
      console.error('Failed to load groups:', error)
      toast.error('Failed to load groups')
      setGroups([])
    } finally {
      setLoading(false)
    }
  }

  const handleCreateGroup = async (groupData) => {
    try {
      await api.post('/groups', groupData)
      toast.success('Group created successfully')
      setShowCreateModal(false)
      loadGroups()
    } catch (error) {
      console.error('Failed to create group:', error)
      toast.error(error.response?.data?.detail || 'Failed to create group')
    }
  }

  const handleDeleteGroup = async (groupId) => {
    if (!confirm('Are you sure you want to delete this group?')) {
      return
    }

    try {
      await api.delete(`/groups/${groupId}`)
      toast.success('Group deleted successfully')
      loadGroups()
    } catch (error) {
      console.error('Failed to delete group:', error)
      toast.error(error.response?.data?.detail || 'Failed to delete group')
    }
  }

  const handleManageGroup = (group) => {
    setSelectedGroup(group)
    setShowManageModal(true)
  }

  const handleCloseManageModal = () => {
    setShowManageModal(false)
    setSelectedGroup(null)
    loadGroups() // Refresh groups after managing
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white mb-2">Groups Management</h1>
          <p className="text-slate-400">Manage user and node groups for access control</p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
        >
          <Plus className="w-5 h-5" />
          Create Group
        </button>
      </div>

      {/* Groups Grid */}
      {groups.length === 0 ? (
        <div className="text-center py-12 bg-slate-800 border border-slate-700 rounded-xl">
          <Users className="w-16 h-16 text-slate-600 mx-auto mb-4" />
          <h3 className="text-xl font-semibold text-white mb-2">No Groups Yet</h3>
          <p className="text-slate-400 mb-4">Create your first group to organize users and nodes</p>
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
          >
            Create Group
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {groups.map((group) => (
            <div
              key={group.id}
              className="bg-slate-800 border border-slate-700 rounded-xl overflow-hidden hover:border-slate-600 transition-colors"
            >
              {/* Status bar */}
              <div className="h-1 bg-blue-500" />

              <div className="p-5">
                {/* Group Header */}
                <div className="flex items-start justify-between mb-4">
                  <div className="flex-1">
                    <h3 className="text-lg font-bold text-white mb-1">{group.name}</h3>
                    {group.description && (
                      <p className="text-sm text-slate-400">{group.description}</p>
                    )}
                  </div>
                  <button
                    onClick={() => handleDeleteGroup(group.id)}
                    className="p-2 text-red-400 hover:bg-red-500/20 rounded-lg transition-colors"
                    title="Delete group"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>

                {/* Stats */}
                <div className="grid grid-cols-2 gap-3 mb-4">
                  <div className="bg-slate-700/50 rounded-lg p-3">
                    <div className="flex items-center gap-2">
                      <UserPlus className="w-4 h-4 text-blue-400" />
                      <span className="text-2xl font-bold text-white">{group.member_count || 0}</span>
                    </div>
                    <p className="text-xs text-slate-400 mt-1">Members</p>
                  </div>
                  <div className="bg-slate-700/50 rounded-lg p-3">
                    <div className="flex items-center gap-2">
                      <Server className="w-4 h-4 text-green-400" />
                      <span className="text-2xl font-bold text-white">{group.node_count || 0}</span>
                    </div>
                    <p className="text-xs text-slate-400 mt-1">Nodes</p>
                  </div>
                </div>

                {/* Permission Flags */}
                {group.settings && (
                  <div className="flex flex-wrap gap-2 mb-4">
                    {group.settings.allow_terminal && (
                      <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-green-500/20 border border-green-500/50 rounded-lg text-green-400 text-sm font-medium">
                        <Terminal className="w-3.5 h-3.5" />
                        SSH
                      </span>
                    )}
                    {group.settings.allow_rdp && (
                      <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-blue-500/20 border border-blue-500/50 rounded-lg text-blue-400 text-sm font-medium">
                        <Monitor className="w-3.5 h-3.5" />
                        RDP
                      </span>
                    )}
                    {group.settings.allow_vnc && (
                      <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-purple-500/20 border border-purple-500/50 rounded-lg text-purple-400 text-sm font-medium">
                        <Monitor className="w-3.5 h-3.5" />
                        VNC
                      </span>
                    )}
                    {group.settings.allow_ssl_tunnel && (
                      <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-cyan-500/20 border border-cyan-500/50 rounded-lg text-cyan-400 text-sm font-medium">
                        <Lock className="w-3.5 h-3.5" />
                        SSL
                      </span>
                    )}
                  </div>
                )}

                {/* Manage Button */}
                <button
                  onClick={() => handleManageGroup(group)}
                  className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
                >
                  <Settings className="w-4 h-4" />
                  Manage Group
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Group Modal */}
      {showCreateModal && (
        <CreateGroupModal
          onClose={() => setShowCreateModal(false)}
          onCreate={handleCreateGroup}
        />
      )}

      {/* Manage Group Modal */}
      {showManageModal && selectedGroup && (
        <ManageGroupModal
          group={selectedGroup}
          onClose={handleCloseManageModal}
        />
      )}
    </div>
  )
}

export default GroupsPage
