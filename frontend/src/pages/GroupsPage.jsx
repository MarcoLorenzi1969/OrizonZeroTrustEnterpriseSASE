import { useState, useEffect } from 'react'
import { Users, Plus, Settings, Trash2, X, UserPlus, Server } from 'lucide-react'
import api from '../services/api'
import toast from 'react-hot-toast'
import CreateGroupModal from '../components/groups/CreateGroupModal'
import ManageGroupModal from '../components/groups/ManageGroupModal'

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
      const response = await api.get('/groups')
      setGroups(response.data.groups || [])
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
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    )
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <Users className="w-8 h-8" />
            Groups
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">
            Manage user and node groups for access control
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          <Plus className="w-5 h-5" />
          Create Group
        </button>
      </div>

      {/* Groups Grid */}
      {groups.length === 0 ? (
        <div className="text-center py-12 bg-white dark:bg-gray-800 rounded-lg shadow">
          <Users className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
            No Groups Yet
          </h3>
          <p className="text-gray-600 dark:text-gray-400 mb-4">
            Create your first group to organize users and nodes
          </p>
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Create Group
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {groups.map((group) => (
            <div
              key={group.id}
              className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 hover:shadow-xl transition-shadow"
            >
              {/* Group Header */}
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-1">
                    {group.name}
                  </h3>
                  {group.description && (
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      {group.description}
                    </p>
                  )}
                </div>
                <button
                  onClick={() => handleDeleteGroup(group.id)}
                  className="p-2 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
                  title="Delete group"
                >
                  <Trash2 className="w-5 h-5" />
                </button>
              </div>

              {/* Stats */}
              <div className="space-y-2 mb-4">
                <div className="flex items-center gap-2 text-sm">
                  <UserPlus className="w-4 h-4 text-blue-500" />
                  <span className="text-gray-700 dark:text-gray-300">
                    {group.member_count || 0} members
                  </span>
                </div>
                <div className="flex items-center gap-2 text-sm">
                  <Server className="w-4 h-4 text-green-500" />
                  <span className="text-gray-700 dark:text-gray-300">
                    {group.node_count || 0} nodes
                  </span>
                </div>
              </div>

              {/* Settings Badge */}
              {group.settings && Object.keys(group.settings).length > 0 && (
                <div className="mb-4">
                  <div className="flex flex-wrap gap-1">
                    {group.settings.allow_terminal && (
                      <span className="px-2 py-1 text-xs bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 rounded">
                        SSH
                      </span>
                    )}
                    {group.settings.allow_rdp && (
                      <span className="px-2 py-1 text-xs bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 rounded">
                        RDP
                      </span>
                    )}
                    {group.settings.allow_vnc && (
                      <span className="px-2 py-1 text-xs bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400 rounded">
                        VNC
                      </span>
                    )}
                  </div>
                </div>
              )}

              {/* Manage Button */}
              <button
                onClick={() => handleManageGroup(group)}
                className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
              >
                <Settings className="w-4 h-4" />
                Manage
              </button>
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
