/**
 * Audit Logs Redux Slice
 * For: Marco @ Syneto/Orizon
 */

import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'
import api from '../../services/apiService'

export const fetchAuditLogs = createAsyncThunk(
  'audit/fetchAuditLogs',
  async (filters = {}, { rejectWithValue }) => {
    try {
      const data = await api.getAuditLogs(filters)
      return data
    } catch (error) {
      return rejectWithValue(error.response?.data || 'Failed to fetch audit logs')
    }
  }
)

export const exportAuditLogs = createAsyncThunk(
  'audit/exportAuditLogs',
  async ({ format, filters }, { rejectWithValue }) => {
    try {
      const blob = await api.exportAuditLogs(format, filters)
      return blob
    } catch (error) {
      return rejectWithValue(error.response?.data || 'Failed to export audit logs')
    }
  }
)

export const fetchAuditStatistics = createAsyncThunk(
  'audit/fetchAuditStatistics',
  async (_, { rejectWithValue }) => {
    try {
      const data = await api.getAuditStatistics()
      return data
    } catch (error) {
      return rejectWithValue(error.response?.data || 'Failed to fetch statistics')
    }
  }
)

const auditSlice = createSlice({
  name: 'audit',
  initialState: {
    logs: [],
    statistics: null,
    loading: false,
    error: null,
    filters: {
      action: '',
      user_id: '',
      start_date: '',
      end_date: '',
      ip_address: '',
      severity: '',
      limit: 100
    }
  },
  reducers: {
    clearError: (state) => {
      state.error = null
    },
    setFilters: (state, action) => {
      state.filters = { ...state.filters, ...action.payload }
    },
    resetFilters: (state) => {
      state.filters = {
        action: '',
        user_id: '',
        start_date: '',
        end_date: '',
        ip_address: '',
        severity: '',
        limit: 100
      }
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch audit logs
      .addCase(fetchAuditLogs.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(fetchAuditLogs.fulfilled, (state, action) => {
        state.loading = false
        state.logs = action.payload
      })
      .addCase(fetchAuditLogs.rejected, (state, action) => {
        state.loading = false
        state.error = action.payload
      })
      // Export audit logs
      .addCase(exportAuditLogs.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(exportAuditLogs.fulfilled, (state) => {
        state.loading = false
      })
      .addCase(exportAuditLogs.rejected, (state, action) => {
        state.loading = false
        state.error = action.payload
      })
      // Fetch statistics
      .addCase(fetchAuditStatistics.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(fetchAuditStatistics.fulfilled, (state, action) => {
        state.loading = false
        state.statistics = action.payload
      })
      .addCase(fetchAuditStatistics.rejected, (state, action) => {
        state.loading = false
        state.error = action.payload
      })
  },
})

export const { clearError, setFilters, resetFilters } = auditSlice.actions
export default auditSlice.reducer
