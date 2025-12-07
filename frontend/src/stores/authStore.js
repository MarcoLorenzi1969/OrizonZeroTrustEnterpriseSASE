import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { jwtDecode } from 'jwt-decode'
import api from '../services/api'

export const useAuthStore = create(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      
      login: async (email, password) => {
        try {
          const response = await api.post('/auth/login', { email, password })
          const { access_token } = response.data

          // Set token in API client immediately
          api.defaults.headers.common['Authorization'] = `Bearer ${access_token}`

          // Also store in localStorage for persistence
          localStorage.setItem('access_token', access_token)

          // Fetch user info from /auth/me or decode from token
          let user = null
          try {
            const userResponse = await api.get('/auth/me')
            user = userResponse.data
          } catch (e) {
            // Decode from token if /me fails
            const decoded = jwtDecode(access_token)
            user = {
              id: decoded.sub,
              email: decoded.email,
              role: decoded.role,
            }
          }

          set({
            user,
            token: access_token,
            isAuthenticated: true,
          })

          return { success: true }
        } catch (error) {
          return {
            success: false,
            error: error.response?.data?.detail || 'Login failed',
          }
        }
      },
      
      logout: () => {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        set({
          user: null,
          token: null,
          isAuthenticated: false,
        })
        delete api.defaults.headers.common['Authorization']
      },
      
      checkAuth: () => {
        const { token } = get()
        if (!token) return false
        
        try {
          const decoded = jwtDecode(token)
          const currentTime = Date.now() / 1000
          
          if (decoded.exp < currentTime) {
            get().logout()
            return false
          }
          
          api.defaults.headers.common['Authorization'] = `Bearer ${token}`
          return true
        } catch (error) {
          get().logout()
          return false
        }
      },
      
      updateUser: (userData) => {
        set((state) => ({
          user: { ...state.user, ...userData },
        }))
      },
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

// Check auth on app load
useAuthStore.getState().checkAuth()
