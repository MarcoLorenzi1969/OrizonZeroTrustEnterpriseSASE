import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import api from '../services/api'

export const useAuthStore = create(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      loading: false,
      error: null,

      // Login
      login: async (email, password) => {
        set({ loading: true, error: null })
        try {
          const response = await api.post('/auth/login', { email, password })
          const { access_token, user } = response.data
          
          set({
            user,
            token: access_token,
            isAuthenticated: true,
            loading: false,
            error: null,
          })
          
          // Set token in API client
          api.defaults.headers.common['Authorization'] = `Bearer ${access_token}`
          
          return { success: true }
        } catch (error) {
          set({
            loading: false,
            error: error.response?.data?.detail || 'Login failed',
          })
          return { success: false, error: error.response?.data?.detail }
        }
      },

      // Logout
      logout: () => {
        set({
          user: null,
          token: null,
          isAuthenticated: false,
          error: null,
        })
        delete api.defaults.headers.common['Authorization']
      },

      // Refresh user data
      refreshUser: async () => {
        const token = get().token
        if (!token) return

        try {
          const response = await api.get('/users/me')
          set({ user: response.data })
        } catch (error) {
          console.error('Failed to refresh user:', error)
          get().logout()
        }
      },

      // Clear error
      clearError: () => set({ error: null }),
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
)

// Initialize token in API client on page load
const token = useAuthStore.getState().token
if (token) {
  api.defaults.headers.common['Authorization'] = `Bearer ${token}`
}
