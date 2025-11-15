import axios from 'axios'
import toast from 'react-hot-toast'
import debugService from './debugService'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://46.101.189.126/api/v1'

debugService.info('API Service', { message: 'Initializing', baseURL: API_BASE_URL })

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
})

// Request interceptor
api.interceptors.request.use(
  (config) => {
    // Add JWT token to Authorization header
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }

    // Add timestamp to prevent caching
    config.params = {
      ...config.params,
      _t: Date.now(),
    }

    // Log API request
    debugService.logApiRequest(config)

    return config
  },
  (error) => {
    debugService.error('API Request Error', { message: error.message, stack: error.stack })
    return Promise.reject(error)
  }
)

// Response interceptor
api.interceptors.response.use(
  (response) => {
    // Log successful API response
    debugService.logApiResponse(response)
    return response
  },
  (error) => {
    // Log API error
    debugService.logApiError(error)
    if (error.response) {
      // Server responded with error
      const { status, data } = error.response

      switch (status) {
        case 401:
          // Only redirect to login if not already on login page
          if (!window.location.pathname.includes('/login')) {
            console.error('[API] 401 Unauthorized - clearing tokens and redirecting to login')
            localStorage.removeItem('access_token')
            localStorage.removeItem('refresh_token')
            toast.error('Session expired. Please login again.')
            // Use setTimeout to avoid redirect loops
            setTimeout(() => {
              window.location.href = '/login'
            }, 100)
          }
          break
        case 403:
          console.error('[API] 403 Forbidden')
          // Don't show toast for every 403, let components handle it
          break
        case 404:
          console.warn('[API] 404 Not Found:', error.config?.url)
          // Don't show toast for 404, let components handle missing endpoints
          break
        case 500:
          console.error('[API] 500 Server Error')
          toast.error('Server error. Please try again later.')
          break
        default:
          if (data?.detail) {
            console.error('[API] Error:', data.detail)
            toast.error(data.detail)
          }
      }
    } else if (error.request) {
      // Request made but no response
      console.error('[API] Network error')
      toast.error('Network error. Please check your connection.')
    } else {
      // Other errors
      console.error('[API] Unexpected error:', error.message)
      toast.error('An unexpected error occurred')
    }

    return Promise.reject(error)
  }
)

export default api
