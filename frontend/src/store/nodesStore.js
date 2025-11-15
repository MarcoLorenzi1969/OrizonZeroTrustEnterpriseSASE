import { create } from 'zustand'
import api from '../services/api'

export const useNodesStore = create((set, get) => ({
  nodes: [],
  selectedNode: null,
  loading: false,
  error: null,
  
  // Fetch all nodes
  fetchNodes: async () => {
    set({ loading: true, error: null })
    try {
      const response = await api.get('/nodes')
      set({ nodes: response.data, loading: false })
    } catch (error) {
      set({
        error: error.response?.data?.detail || 'Failed to fetch nodes',
        loading: false,
      })
    }
  },
  
  // Add node
  addNode: async (nodeData) => {
    try {
      const response = await api.post('/nodes', nodeData)
      set((state) => ({
        nodes: [...state.nodes, response.data],
      }))
      return { success: true, node: response.data }
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.detail || 'Failed to add node',
      }
    }
  },
  
  // Update node
  updateNode: async (nodeId, nodeData) => {
    try {
      const response = await api.patch(`/nodes/${nodeId}`, nodeData)
      set((state) => ({
        nodes: state.nodes.map((node) =>
          node.id === nodeId ? response.data : node
        ),
      }))
      return { success: true, node: response.data }
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.detail || 'Failed to update node',
      }
    }
  },
  
  // Delete node
  deleteNode: async (nodeId) => {
    try {
      await api.delete(`/nodes/${nodeId}`)
      set((state) => ({
        nodes: state.nodes.filter((node) => node.id !== nodeId),
      }))
      return { success: true }
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.detail || 'Failed to delete node',
      }
    }
  },
  
  // Select node
  selectNode: (node) => set({ selectedNode: node }),
  
  // Update node status (via WebSocket)
  updateNodeStatus: (nodeId, status) => {
    set((state) => ({
      nodes: state.nodes.map((node) =>
        node.id === nodeId ? { ...node, status, last_seen: new Date().toISOString() } : node
      ),
    }))
  },
  
  // Clear error
  clearError: () => set({ error: null }),
}))
