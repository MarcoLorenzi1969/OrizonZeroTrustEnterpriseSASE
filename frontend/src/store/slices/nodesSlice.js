/**
 * Nodes Redux Slice
 * For: Marco @ Syneto/Orizon
 */

import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'
import api from '../../services/apiService'

export const fetchNodes = createAsyncThunk(
  'nodes/fetchNodes',
  async (_, { rejectWithValue }) => {
    try {
      const data = await api.getNodes()
      return data
    } catch (error) {
      return rejectWithValue(error.response?.data || 'Failed to fetch nodes')
    }
  }
)

export const createNode = createAsyncThunk(
  'nodes/createNode',
  async (nodeData, { rejectWithValue }) => {
    try {
      const data = await api.createNode(nodeData)
      return data
    } catch (error) {
      return rejectWithValue(error.response?.data || 'Failed to create node')
    }
  }
)

export const deleteNode = createAsyncThunk(
  'nodes/deleteNode',
  async (nodeId, { rejectWithValue }) => {
    try {
      await api.deleteNode(nodeId)
      return nodeId
    } catch (error) {
      return rejectWithValue(error.response?.data || 'Failed to delete node')
    }
  }
)

const nodesSlice = createSlice({
  name: 'nodes',
  initialState: {
    nodes: [],
    loading: false,
    error: null,
  },
  reducers: {
    clearError: (state) => {
      state.error = null
    },
    updateNodeStatus: (state, action) => {
      const { nodeId, status } = action.payload
      const node = state.nodes.find(n => n.id === nodeId)
      if (node) {
        node.status = status
      }
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch nodes
      .addCase(fetchNodes.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(fetchNodes.fulfilled, (state, action) => {
        state.loading = false
        state.nodes = action.payload
      })
      .addCase(fetchNodes.rejected, (state, action) => {
        state.loading = false
        state.error = action.payload
      })
      // Create node
      .addCase(createNode.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(createNode.fulfilled, (state, action) => {
        state.loading = false
        state.nodes.push(action.payload)
      })
      .addCase(createNode.rejected, (state, action) => {
        state.loading = false
        state.error = action.payload
      })
      // Delete node
      .addCase(deleteNode.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(deleteNode.fulfilled, (state, action) => {
        state.loading = false
        state.nodes = state.nodes.filter(n => n.id !== action.payload)
      })
      .addCase(deleteNode.rejected, (state, action) => {
        state.loading = false
        state.error = action.payload
      })
  },
})

export const { clearError, updateNodeStatus } = nodesSlice.actions
export default nodesSlice.reducer
