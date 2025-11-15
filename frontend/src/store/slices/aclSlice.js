/**
 * ACL Rules Redux Slice
 * For: Marco @ Syneto/Orizon
 */

import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'
import api from '../../services/apiService'

export const fetchACLRules = createAsyncThunk(
  'acl/fetchACLRules',
  async (_, { rejectWithValue }) => {
    try {
      const data = await api.getACLRules()
      return data
    } catch (error) {
      return rejectWithValue(error.response?.data || 'Failed to fetch ACL rules')
    }
  }
)

export const createACLRule = createAsyncThunk(
  'acl/createACLRule',
  async (ruleData, { rejectWithValue }) => {
    try {
      const data = await api.createACLRule(ruleData)
      return data
    } catch (error) {
      return rejectWithValue(error.response?.data || 'Failed to create ACL rule')
    }
  }
)

export const deleteACLRule = createAsyncThunk(
  'acl/deleteACLRule',
  async (ruleId, { rejectWithValue }) => {
    try {
      await api.deleteACLRule(ruleId)
      return ruleId
    } catch (error) {
      return rejectWithValue(error.response?.data || 'Failed to delete ACL rule')
    }
  }
)

export const toggleACLRule = createAsyncThunk(
  'acl/toggleACLRule',
  async ({ ruleId, isActive }, { rejectWithValue }) => {
    try {
      if (isActive) {
        await api.disableACLRule(ruleId)
      } else {
        await api.enableACLRule(ruleId)
      }
      return { ruleId, isActive: !isActive }
    } catch (error) {
      return rejectWithValue(error.response?.data || 'Failed to toggle ACL rule')
    }
  }
)

const aclSlice = createSlice({
  name: 'acl',
  initialState: {
    rules: [],
    loading: false,
    error: null,
  },
  reducers: {
    clearError: (state) => {
      state.error = null
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch ACL rules
      .addCase(fetchACLRules.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(fetchACLRules.fulfilled, (state, action) => {
        state.loading = false
        state.rules = action.payload
      })
      .addCase(fetchACLRules.rejected, (state, action) => {
        state.loading = false
        state.error = action.payload
      })
      // Create ACL rule
      .addCase(createACLRule.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(createACLRule.fulfilled, (state, action) => {
        state.loading = false
        state.rules.push(action.payload)
      })
      .addCase(createACLRule.rejected, (state, action) => {
        state.loading = false
        state.error = action.payload
      })
      // Delete ACL rule
      .addCase(deleteACLRule.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(deleteACLRule.fulfilled, (state, action) => {
        state.loading = false
        state.rules = state.rules.filter(r => r.id !== action.payload)
      })
      .addCase(deleteACLRule.rejected, (state, action) => {
        state.loading = false
        state.error = action.payload
      })
      // Toggle ACL rule
      .addCase(toggleACLRule.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(toggleACLRule.fulfilled, (state, action) => {
        state.loading = false
        const { ruleId, isActive } = action.payload
        const rule = state.rules.find(r => r.id === ruleId)
        if (rule) {
          rule.is_active = isActive
        }
      })
      .addCase(toggleACLRule.rejected, (state, action) => {
        state.loading = false
        state.error = action.payload
      })
  },
})

export const { clearError } = aclSlice.actions
export default aclSlice.reducer
