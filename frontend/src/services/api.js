import axios from 'axios'
import toast from 'react-hot-toast'
import debugService from './debugService'
import { debugAPI, debugData } from '../utils/debugLogger'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

debugService.info('API Service', { message: 'Initializing', baseURL: API_BASE_URL })

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
})

// Track request timing
const requestTimings = new Map()

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

    // Track request start time
    const requestId = `${config.method}-${config.url}-${Date.now()}`
    config._requestId = requestId
    requestTimings.set(requestId, Date.now())

    // Log API request with new debug system
    debugAPI.request(config.method?.toUpperCase() || 'GET', config.url, config.data)
    debugService.logApiRequest(config)

    return config
  },
  (error) => {
    debugAPI.error('REQUEST', '', error)
    debugService.error('API Request Error', { message: error.message, stack: error.stack })
    return Promise.reject(error)
  }
)

// Response interceptor
api.interceptors.response.use(
  (response) => {
    // Calculate duration
    const requestId = response.config._requestId
    const startTime = requestTimings.get(requestId)
    const duration = startTime ? Date.now() - startTime : 0
    requestTimings.delete(requestId)

    // Log successful API response with new debug system
    debugAPI.response(
      response.config.method?.toUpperCase() || 'GET',
      response.config.url,
      response.status,
      response.data,
      duration
    )

    // Log data details
    debugData.received(`API: ${response.config.url}`, response.data)

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
