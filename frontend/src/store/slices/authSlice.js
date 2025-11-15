/**
 * Auth Slice - Authentication State Management
 */

import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'
import api from '../../services/apiService'

// Async thunks
export const login = createAsyncThunk(
  'auth/login',
  async ({ email, password }, { rejectWithValue }) => {
    try {
      const data = await api.login(email, password)
      return data
    } catch (error) {
      return rejectWithValue(error.response?.data || 'Login failed')
    }
  }
)

export const getCurrentUser = createAsyncThunk(
  'auth/getCurrentUser',
  async (_, { rejectWithValue }) => {
    try {
      const user = await api.getCurrentUser()
      return user
    } catch (error) {
      return rejectWithValue(error.response?.data)
    }
  }
)

export const logout = createAsyncThunk('auth/logout', async () => {
  await api.logout()
})

const authSlice = createSlice({
  name: 'auth',
  initialState: {
    user: null,
    isAuthenticated: !!localStorage.getItem('access_token'),
    loading: false,
    error: null,
    require2FA: false,
  },
  reducers: {
    setRequire2FA: (state, action) => {
      state.require2FA = action.payload
    },
    clearError: (state) => {
      state.error = null
    },
  },
  extraReducers: (builder) => {
    builder
      // Login
      .addCase(login.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(login.fulfilled, (state, action) => {
        state.loading = false
        state.isAuthenticated = true
        state.user = action.payload.user
        state.require2FA = action.payload.require_2fa || false
      })
      .addCase(login.rejected, (state, action) => {
        state.loading = false
        state.error = action.payload
      })
      // Get current user
      .addCase(getCurrentUser.fulfilled, (state, action) => {
        state.user = action.payload
        state.isAuthenticated = true
      })
      .addCase(getCurrentUser.rejected, (state) => {
        state.isAuthenticated = false
        state.user = null
      })
      // Logout
      .addCase(logout.fulfilled, (state) => {
        state.user = null
        state.isAuthenticated = false
        state.require2FA = false
      })
  },
})

export const { setRequire2FA, clearError } = authSlice.actions
export default authSlice.reducer
