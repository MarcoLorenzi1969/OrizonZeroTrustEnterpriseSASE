import { useState, useEffect } from 'react'
import { X, Users, Server, UserPlus, Trash2, Settings as SettingsIcon, Lock, Terminal, Monitor, Globe } from 'lucide-react'
import api from '../../services/api'
import toast from 'react-hot-toast'
import { debugData } from '../../utils/debugLogger'

function ManageGroupModal({ group, onClose }) {
  const [activeTab, setActiveTab] = useState('members')
  const [members, setMembers] = useState([])
  const [nodes, setNodes] = useState([])
  const [allUsers, setAllUsers] = useState([])
  const [allNodes, setAllNodes] = useState([])
  const [loading, setLoading] = useState(true)
  const [showAddMemberModal, setShowAddMemberModal] = useState(false)
  const [showAddNodeModal, setShowAddNodeModal] = useState(false)
  const [selectedUsers, setSelectedUsers] = useState([])
  const [selectedNodes, setSelectedNodes] = useState([])

  useEffect(() => {
    loadGroupData()
    loadAllUsers()
    loadAllNodes()
  }, [group.id])

  const loadGroupData = async () => {
    try {
      const [membersRes, nodesRes] = await Promise.all([
        api.get(`/groups/${group.id}/members`),
        api.get(`/groups/${group.id}/nodes`)
      ])
      setMembers(membersRes.data.members || [])
      setNodes(nodesRes.data.nodes || [])
    } catch (error) {
      console.error('Failed to load group data:', error)
      toast.error('Failed to load group data')
    } finally {
      setLoading(false)
    }
  }

  const loadAllUsers = async () => {
    try {
      const response = await api.get('/users')
      // API returns array directly or object with users property
      const usersData = Array.isArray(response.data) ? response.data : (response.data.users || [])
      debugData.received('ManageGroupModal.loadAllUsers', usersData)
      setAllUsers(usersData)
    } catch (error) {
      console.error('Failed to load users:', error)
    }
  }

  const loadAllNodes = async () => {
    try {
      const response = await api.get('/nodes')
      // API returns nodes or items
      const nodesData = response.data.nodes || response.data.items || []
      debugData.received('ManageGroupModal.loadAllNodes', nodesData)
      setAllNodes(nodesData)
    } catch (error) {
      console.error('Failed to load nodes:', error)
    }
  }

  const handleAddMembers = async () => {
    if (selectedUsers.length === 0) {
      toast.error('Please select at least one user')
      return
    }

    try {
      for (const userId of selectedUsers) {
        await api.post(`/groups/${group.id}/members`, {
          user_id: userId,
          role_in_group: 'member',
          permissions: {}
        })
      }
      toast.success(`Added ${selectedUsers.length} member(s)`)
      setShowAddMemberModal(false)
      setSelectedUsers([])
      loadGroupData()
    } catch (error) {
      console.error('Failed to add members:', error)
      toast.error(error.response?.data?.detail || 'Failed to add members')
    }
  }

  const handleRemoveMember = async (userId) => {
    if (!confirm('Remove this member from the group?')) return

    try {
      await api.delete(`/groups/${group.id}/members/${userId}`)
      toast.success('Member removed')
      loadGroupData()
    } catch (error) {
      console.error('Failed to remove member:', error)
      toast.error('Failed to remove member')
    }
  }

  const handleAddNodes = async () => {
    if (selectedNodes.length === 0) {
      toast.error('Please select at least one node')
      return
    }

    try {
      for (const nodeId of selectedNodes) {
        await api.post(`/groups/${group.id}/nodes`, {
          node_id: nodeId,
          permissions: { ssh: true, rdp: false, vnc: false, ssl_tunnel: true }
        })
      }
      toast.success(`Added ${selectedNodes.length} node(s)`)
      setShowAddNodeModal(false)
      setSelectedNodes([])
      loadGroupData()
    } catch (error) {
      console.error('Failed to add nodes:', error)
      toast.error(error.response?.data?.detail || 'Failed to add nodes')
    }
  }

  const handleRemoveNode = async (nodeId) => {
    if (!confirm('Remove this node from the group?')) return

    try {
      await api.delete(`/groups/${group.id}/nodes/${nodeId}`)
      toast.success('Node removed')
      loadGroupData()
    } catch (error) {
      console.error('Failed to remove node:', error)
      toast.error('Failed to remove node')
    }
  }

  const handleUpdateNodePermissions = async (nodeId, permissions) => {
    try {
      await api.put(`/groups/${group.id}/nodes/${nodeId}`, { permissions })
      toast.success('Permissions updated')
      loadGroupData()
    } catch (error) {
      console.error('Failed to update permissions:', error)
      toast.error('Failed to update permissions')
    }
  }

  const toggleUserSelection = (userId) => {
    setSelectedUsers(prev =>
      prev.includes(userId)
        ? prev.filter(id => id !== userId)
        : [...prev, userId]
    )
  }

  const toggleNodeSelection = (nodeId) => {
    setSelectedNodes(prev =>
      prev.includes(nodeId)
        ? prev.filter(id => id !== nodeId)
        : [...prev, nodeId]
    )
  }

  // Filter out users/nodes already in group
  const availableUsers = allUsers.filter(
    user => !members.some(m => m.user_id === user.id)
  )
  const availableNodes = allNodes.filter(
    node => !nodes.some(n => n.node_id === node.id)
  )

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-slate-800 border border-slate-700 rounded-xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-slate-700">
          <div>
            <h2 className="text-xl font-bold text-white">
              Manage Group: {group.name}
            </h2>
            <p className="text-sm text-slate-400 mt-1">
              {group.description || 'No description'}
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-slate-400" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-slate-700 px-6">
          <button
            onClick={() => setActiveTab('members')}
            className={`px-4 py-3 font-medium transition-colors border-b-2 ${
              activeTab === 'members'
                ? 'border-blue-500 text-blue-400'
                : 'border-transparent text-slate-400 hover:text-white'
            }`}
          >
            <div className="flex items-center gap-2">
              <Users className="w-4 h-4" />
              Members ({members.length})
            </div>
          </button>
          <button
            onClick={() => setActiveTab('nodes')}
            className={`px-4 py-3 font-medium transition-colors border-b-2 ${
              activeTab === 'nodes'
                ? 'border-blue-500 text-blue-400'
                : 'border-transparent text-slate-400 hover:text-white'
            }`}
          >
            <div className="flex items-center gap-2">
              <Server className="w-4 h-4" />
              Nodes ({nodes.length})
            </div>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
            </div>
          ) : activeTab === 'members' ? (
            <div>
              {/* Add Member Button */}
              <button
                onClick={() => setShowAddMemberModal(true)}
                className="mb-4 flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
              >
                <UserPlus className="w-4 h-4" />
                Add Members
              </button>

              {/* Members List */}
              {members.length === 0 ? (
                <div className="text-center py-12 text-slate-500">
                  No members yet. Add some to get started.
                </div>
              ) : (
                <div className="space-y-2">
                  {members.map((member) => (
                    <div
                      key={member.user_id}
                      className="flex items-center justify-between p-4 bg-slate-700/50 border border-slate-600 rounded-lg"
                    >
                      <div>
                        <div className="font-medium text-white">
                          {member.full_name || member.email}
                        </div>
                        <div className="text-sm text-slate-400">
                          {member.email}
                        </div>
                        <div className="text-xs text-slate-500 mt-1">
                          Role: <span className="font-medium text-blue-400">{member.role_in_group}</span>
                        </div>
                      </div>
                      <button
                        onClick={() => handleRemoveMember(member.user_id)}
                        className="p-2 text-red-400 hover:bg-red-500/20 rounded-lg transition-colors"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div>
              {/* Add Node Button */}
              <button
                onClick={() => setShowAddNodeModal(true)}
                className="mb-4 flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
              >
                <Server className="w-4 h-4" />
                Add Nodes
              </button>

              {/* Nodes List */}
              {nodes.length === 0 ? (
                <div className="text-center py-12 text-slate-500">
                  No nodes yet. Add some to get started.
                </div>
              ) : (
                <div className="space-y-2">
                  {nodes.map((node) => (
                    <div
                      key={node.node_id}
                      className="p-4 bg-slate-700/50 border border-slate-600 rounded-lg"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div>
                          <div className="font-medium text-white">
                            {node.name}
                          </div>
                          <div className="text-sm text-slate-400">
                            {node.hostname || node.ip_address || 'No IP'} • {node.node_type}
                          </div>
                        </div>
                        <button
                          onClick={() => handleRemoveNode(node.node_id)}
                          className="p-2 text-red-400 hover:bg-red-500/20 rounded-lg transition-colors"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>

                      {/* Permissions */}
                      <div className="flex flex-wrap gap-3 mt-3">
                        <label className="flex items-center gap-2 text-sm cursor-pointer">
                          <input
                            type="checkbox"
                            checked={node.permissions?.ssh || false}
                            onChange={(e) =>
                              handleUpdateNodePermissions(node.node_id, {
                                ...node.permissions,
                                ssh: e.target.checked
                              })
                            }
                            className="rounded text-green-600"
                          />
                          <Terminal className="w-4 h-4 text-green-400" />
                          <span className="text-slate-300">SSH</span>
                        </label>
                        <label className="flex items-center gap-2 text-sm cursor-pointer">
                          <input
                            type="checkbox"
                            checked={node.permissions?.ssl_tunnel || false}
                            onChange={(e) =>
                              handleUpdateNodePermissions(node.node_id, {
                                ...node.permissions,
                                ssl_tunnel: e.target.checked
                              })
                            }
                            className="rounded text-cyan-600"
                          />
                          <Lock className="w-4 h-4 text-cyan-400" />
                          <span className="text-slate-300">SSL/HTTPS</span>
                        </label>
                        <label className="flex items-center gap-2 text-sm cursor-pointer">
                          <input
                            type="checkbox"
                            checked={node.permissions?.rdp || false}
                            onChange={(e) =>
                              handleUpdateNodePermissions(node.node_id, {
                                ...node.permissions,
                                rdp: e.target.checked
                              })
                            }
                            className="rounded text-blue-600"
                          />
                          <Monitor className="w-4 h-4 text-blue-400" />
                          <span className="text-slate-300">RDP</span>
                        </label>
                        <label className="flex items-center gap-2 text-sm cursor-pointer">
                          <input
                            type="checkbox"
                            checked={node.permissions?.vnc || false}
                            onChange={(e) =>
                              handleUpdateNodePermissions(node.node_id, {
                                ...node.permissions,
                                vnc: e.target.checked
                              })
                            }
                            className="rounded text-purple-600"
                          />
                          <Monitor className="w-4 h-4 text-purple-400" />
                          <span className="text-slate-300">VNC</span>
                        </label>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-slate-700">
          <button
            onClick={onClose}
            className="w-full px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
          >
            Close
          </button>
        </div>
      </div>

      {/* Add Members Modal */}
      {showAddMemberModal && (
        <div className="fixed inset-0 bg-black/75 backdrop-blur-sm flex items-center justify-center z-[60] p-4">
          <div className="bg-slate-800 border border-slate-700 rounded-xl max-w-md w-full max-h-[80vh] overflow-hidden flex flex-col">
            <div className="p-4 border-b border-slate-700 flex items-center justify-between">
              <h3 className="text-lg font-bold text-white">Add Members</h3>
              <button onClick={() => setShowAddMemberModal(false)} className="p-1 hover:bg-slate-700 rounded">
                <X className="w-5 h-5 text-slate-400" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-4 space-y-2">
              {availableUsers.length === 0 ? (
                <div className="text-center py-8 text-slate-500">
                  All users are already members
                </div>
              ) : (
                availableUsers.map((user) => (
                  <label
                    key={user.id}
                    className="flex items-center gap-3 p-3 hover:bg-slate-700/50 border border-transparent hover:border-slate-600 rounded-lg cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={selectedUsers.includes(user.id)}
                      onChange={() => toggleUserSelection(user.id)}
                      className="rounded text-blue-600 bg-slate-700 border-slate-600"
                    />
                    <div>
                      <div className="font-medium text-white">
                        {user.full_name || user.email}
                      </div>
                      <div className="text-sm text-slate-400">
                        {user.email} • <span className="text-blue-400">{user.role}</span>
                      </div>
                    </div>
                  </label>
                ))
              )}
            </div>
            <div className="p-4 border-t border-slate-700 flex gap-2">
              <button
                onClick={() => setShowAddMemberModal(false)}
                className="flex-1 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleAddMembers}
                className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
              >
                Add Selected ({selectedUsers.length})
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add Nodes Modal */}
      {showAddNodeModal && (
        <div className="fixed inset-0 bg-black/75 backdrop-blur-sm flex items-center justify-center z-[60] p-4">
          <div className="bg-slate-800 border border-slate-700 rounded-xl max-w-md w-full max-h-[80vh] overflow-hidden flex flex-col">
            <div className="p-4 border-b border-slate-700 flex items-center justify-between">
              <h3 className="text-lg font-bold text-white">Add Nodes</h3>
              <button onClick={() => setShowAddNodeModal(false)} className="p-1 hover:bg-slate-700 rounded">
                <X className="w-5 h-5 text-slate-400" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-4 space-y-2">
              {availableNodes.length === 0 ? (
                <div className="text-center py-8 text-slate-500">
                  All nodes are already in this group
                </div>
              ) : (
                availableNodes.map((node) => (
                  <label
                    key={node.id}
                    className="flex items-center gap-3 p-3 hover:bg-slate-700/50 border border-transparent hover:border-slate-600 rounded-lg cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={selectedNodes.includes(node.id)}
                      onChange={() => toggleNodeSelection(node.id)}
                      className="rounded text-blue-600 bg-slate-700 border-slate-600"
                    />
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-white">{node.name}</span>
                        <span className={`w-2 h-2 rounded-full ${node.status === 'online' ? 'bg-green-500' : 'bg-slate-500'}`}></span>
                      </div>
                      <div className="text-sm text-slate-400">
                        {node.hostname || node.private_ip || 'No IP'} • {node.node_type}
                      </div>
                      {/* Show available services */}
                      <div className="flex gap-1 mt-1">
                        {node.exposed_applications?.includes('TERMINAL') && (
                          <span className="px-1.5 py-0.5 text-xs bg-green-500/20 text-green-400 rounded">SSH</span>
                        )}
                        {(node.exposed_applications?.includes('HTTPS') || node.exposed_applications?.includes('WEB_SERVER')) && (
                          <span className="px-1.5 py-0.5 text-xs bg-cyan-500/20 text-cyan-400 rounded">SSL</span>
                        )}
                        {node.exposed_applications?.includes('RDP') && (
                          <span className="px-1.5 py-0.5 text-xs bg-blue-500/20 text-blue-400 rounded">RDP</span>
                        )}
                        {node.exposed_applications?.includes('VNC') && (
                          <span className="px-1.5 py-0.5 text-xs bg-purple-500/20 text-purple-400 rounded">VNC</span>
                        )}
                      </div>
                    </div>
                  </label>
                ))
              )}
            </div>
            <div className="p-4 border-t border-slate-700 flex gap-2">
              <button
                onClick={() => setShowAddNodeModal(false)}
                className="flex-1 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleAddNodes}
                className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
              >
                Add Selected ({selectedNodes.length})
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default ManageGroupModal
