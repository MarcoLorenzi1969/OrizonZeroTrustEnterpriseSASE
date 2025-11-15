/**
 * Tunnels Redux Slice
 * For: Marco @ Syneto/Orizon
 */

import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'
import api from '../../services/apiService'

export const fetchTunnels = createAsyncThunk(
  'tunnels/fetchTunnels',
  async (_, { rejectWithValue }) => {
    try {
      const data = await api.getTunnels()
      return data
    } catch (error) {
      return rejectWithValue(error.response?.data || 'Failed to fetch tunnels')
    }
  }
)

export const createTunnel = createAsyncThunk(
  'tunnels/createTunnel',
  async (tunnelData, { rejectWithValue }) => {
    try {
      const data = await api.createTunnel(tunnelData)
      return data
    } catch (error) {
      return rejectWithValue(error.response?.data || 'Failed to create tunnel')
    }
  }
)

export const closeTunnel = createAsyncThunk(
  'tunnels/closeTunnel',
  async (tunnelId, { rejectWithValue }) => {
    try {
      await api.closeTunnel(tunnelId)
      return tunnelId
    } catch (error) {
      return rejectWithValue(error.response?.data || 'Failed to close tunnel')
    }
  }
)

const tunnelsSlice = createSlice({
  name: 'tunnels',
  initialState: {
    tunnels: [],
    loading: false,
    error: null,
  },
  reducers: {
    clearError: (state) => {
      state.error = null
    },
    updateTunnelStatus: (state, action) => {
      const { tunnelId, status } = action.payload
      const tunnel = state.tunnels.find(t => t.id === tunnelId || t.tunnel_id === tunnelId)
      if (tunnel) {
        tunnel.status = status
      }
    },
    addTunnel: (state, action) => {
      state.tunnels.push(action.payload)
    },
    removeTunnel: (state, action) => {
      state.tunnels = state.tunnels.filter(
        t => t.id !== action.payload && t.tunnel_id !== action.payload
      )
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch tunnels
      .addCase(fetchTunnels.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(fetchTunnels.fulfilled, (state, action) => {
        state.loading = false
        state.tunnels = action.payload
      })
      .addCase(fetchTunnels.rejected, (state, action) => {
        state.loading = false
        state.error = action.payload
      })
      // Create tunnel
      .addCase(createTunnel.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(createTunnel.fulfilled, (state, action) => {
        state.loading = false
        state.tunnels.push(action.payload)
      })
      .addCase(createTunnel.rejected, (state, action) => {
        state.loading = false
        state.error = action.payload
      })
      // Close tunnel
      .addCase(closeTunnel.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(closeTunnel.fulfilled, (state, action) => {
        state.loading = false
        state.tunnels = state.tunnels.filter(
          t => t.id !== action.payload && t.tunnel_id !== action.payload
        )
      })
      .addCase(closeTunnel.rejected, (state, action) => {
        state.loading = false
        state.error = action.payload
      })
  },
})

export const { clearError, updateTunnelStatus, addTunnel, removeTunnel } = tunnelsSlice.actions
export default tunnelsSlice.reducer
