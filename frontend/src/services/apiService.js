/**
 * Orizon Zero Trust Connect - Complete API Service
 * For: Marco @ Syneto/Orizon
 *
 * Complete integration with backend API
 */

import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://46.101.189.126/api/v1'

class APIService {
  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 30000,
    })

    this.isLoggingOut = false

    // Request interceptor - add JWT token
    this.client.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('access_token')
        if (token) {
          config.headers.Authorization = `Bearer ${token}`
        }
        return config
      },
      (error) => Promise.reject(error)
    )

    // Response interceptor - handle errors
    this.client.interceptors.response.use(
      (response) => response,
      async (error) => {
        const originalRequest = error.config

        // Handle 401 - try to refresh token
        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true

          // Prevent multiple simultaneous logout attempts
          if (this.isLoggingOut) {
            return Promise.reject(error)
          }

          try {
            const refreshToken = localStorage.getItem('refresh_token')
            if (refreshToken) {
              const { data } = await this.client.post('/auth/refresh', {
                refresh_token: refreshToken
              })

              localStorage.setItem('access_token', data.access_token)

              // Retry original request
              originalRequest.headers.Authorization = `Bearer ${data.access_token}`
              return this.client(originalRequest)
            } else {
              // No refresh token - logout silently
              this.handleLogout()
              return Promise.reject(error)
            }
          } catch (refreshError) {
            // Refresh failed - logout
            this.handleLogout()
            return Promise.reject(refreshError)
          }
        }

        // Don't log expected errors
        if (error.response?.status === 403 && error.config?.url === '/users') {
          // Silently handle 403 on /users endpoint (non-admin access)
          return Promise.reject(error)
        }

        return Promise.reject(error)
      }
    )
  }

  handleLogout() {
    if (this.isLoggingOut) return

    this.isLoggingOut = true
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')

    // Delay to allow any pending requests to complete
    setTimeout(() => {
      if (!window.location.pathname.includes('/login')) {
        window.location.href = '/login'
      }
    }, 100)
  }

  // ============================================================================
  // AUTHENTICATION
  // ============================================================================

  async login(email, password) {
    const { data } = await this.client.post('/auth/login', { email, password })
    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)
    return data
  }

  async register(userData) {
    const { data } = await this.client.post('/auth/register', userData)
    return data
  }

  async logout() {
    try {
      await this.client.post('/auth/logout')
    } finally {
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
    }
  }

  async getCurrentUser() {
    const { data } = await this.client.get('/auth/me')
    return data
  }

  async changePassword(currentPassword, newPassword) {
    const { data } = await this.client.post('/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword
    })
    return data
  }

  // ============================================================================
  // TWO-FACTOR AUTHENTICATION (2FA)
  // ============================================================================

  async setup2FA() {
    const { data } = await this.client.post('/2fa/setup')
    return data // { secret, qr_code }
  }

  async verify2FA(token, enableOnSuccess = true) {
    const { data } = await this.client.post('/2fa/verify', {
      token,
    }, {
      params: { enable_on_success: enableOnSuccess }
    })
    return data
  }

  async disable2FA(token) {
    const { data } = await this.client.post('/2fa/disable', { token })
    return data
  }

  async generateBackupCodes() {
    const { data } = await this.client.post('/2fa/backup-codes')
    return data // { codes: [...] }
  }

  async verifyBackupCode(code) {
    const { data } = await this.client.post('/2fa/backup-codes/verify', {
      token: code
    })
    return data
  }

  // ============================================================================
  // TUNNELS
  // ============================================================================

  async getTunnels() {
    const { data } = await this.client.get('/tunnels')
    return data.tunnels || data || []
  }

  async getTunnel(tunnelId) {
    const { data } = await this.client.get(`/tunnels/${tunnelId}`)
    return data
  }

  async createTunnel(tunnelData) {
    const { data } = await this.client.post('/tunnels', tunnelData)
    return data
  }

  async closeTunnel(tunnelId) {
    await this.client.delete(`/tunnels/${tunnelId}`)
  }

  async getTunnelsHealth() {
    const { data } = await this.client.get('/tunnels/health/all')
    return data
  }

  // ============================================================================
  // NODES
  // ============================================================================

  async getNodes(params = {}) {
    const { data } = await this.client.get('/nodes', { params })
    return data.items || data || []
  }

  async getNode(nodeId) {
    const { data } = await this.client.get(`/nodes/${nodeId}`)
    return data
  }

  async createNode(nodeData) {
    const { data } = await this.client.post('/nodes', nodeData)
    return data
  }

  async updateNode(nodeId, nodeData) {
    const { data } = await this.client.put(`/nodes/${nodeId}`, nodeData)
    return data
  }

  async deleteNode(nodeId) {
    await this.client.delete(`/nodes/${nodeId}`)
  }

  async getNodeMetrics(nodeId) {
    const { data } = await this.client.get(`/nodes/${nodeId}/metrics`)
    return data
  }

  // ============================================================================
  // ACL RULES
  // ============================================================================

  async getACLRules(params = {}) {
    const { data } = await this.client.get('/acl', { params })
    return data.rules || data || []
  }

  async getACLRule(ruleId) {
    const { data } = await this.client.get(`/acl/${ruleId}`)
    return data
  }

  async getNodeACLRules(nodeId) {
    const { data } = await this.client.get(`/acl/node/${nodeId}`)
    return data
  }

  async createACLRule(ruleData) {
    const { data } = await this.client.post('/acl', ruleData)
    return data
  }

  async deleteACLRule(ruleId) {
    await this.client.delete(`/acl/${ruleId}`)
  }

  async enableACLRule(ruleId) {
    const { data } = await this.client.post(`/acl/${ruleId}/enable`)
    return data
  }

  async disableACLRule(ruleId) {
    const { data } = await this.client.post(`/acl/${ruleId}/disable`)
    return data
  }

  // ============================================================================
  // AUDIT LOGS
  // ============================================================================

  async getAuditLogs(params = {}) {
    const { data } = await this.client.get('/audit', { params })
    return data.logs || data || []
  }

  async getAuditStatistics(params = {}) {
    const { data } = await this.client.get('/audit/stats', { params })
    return data
  }

  async exportAuditLogs(format = 'json', params = {}) {
    const response = await this.client.get('/audit/export', {
      params: { format, ...params },
      responseType: 'blob'
    })
    return response.data
  }

  // ============================================================================
  // USERS (Admin)
  // ============================================================================

  async getUsers(params = {}) {
    const { data } = await this.client.get('/users', { params })
    return data
  }

  async getUser(userId) {
    const { data } = await this.client.get(`/users/${userId}`)
    return data
  }

  async createUser(userData) {
    const { data } = await this.client.post('/users', userData)
    return data
  }

  async updateUser(userId, userData) {
    const { data } = await this.client.put(`/users/${userId}`, userData)
    return data
  }

  async deleteUser(userId) {
    await this.client.delete(`/users/${userId}`)
  }

  // ============================================================================
  // METRICS
  // ============================================================================

  async getMetrics() {
    const { data } = await this.client.get('/metrics')
    return data
  }

  // ============================================================================
  // DASHBOARD STATS
  // ============================================================================

  async getDashboardStats() {
    const { data } = await this.client.get('/dashboard/stats')
    return data
  }
}

export default new APIService()
