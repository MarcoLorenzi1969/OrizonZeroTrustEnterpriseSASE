/**
 * Debug Service - Centralized Logging & Debugging
 * For: Marco @ Syneto/Orizon
 */

class DebugService {
  constructor() {
    this.logs = []
    this.maxLogs = 500 // Keep last 500 logs
    this.enabled = true
    this.logToConsole = true

    // Load persisted logs
    this.loadLogs()

    // Capture console errors
    this.captureConsoleErrors()

    // Capture unhandled errors
    this.captureUnhandledErrors()
  }

  captureConsoleErrors() {
    const originalError = console.error
    console.error = (...args) => {
      this.log('error', 'Console Error', { message: args.join(' ') })
      originalError.apply(console, args)
    }

    const originalWarn = console.warn
    console.warn = (...args) => {
      this.log('warn', 'Console Warning', { message: args.join(' ') })
      originalWarn.apply(console, args)
    }
  }

  captureUnhandledErrors() {
    window.addEventListener('error', (event) => {
      this.log('error', 'Unhandled Error', {
        message: event.message,
        filename: event.filename,
        lineno: event.lineno,
        colno: event.colno,
        error: event.error?.stack || event.error
      })
    })

    window.addEventListener('unhandledrejection', (event) => {
      this.log('error', 'Unhandled Promise Rejection', {
        reason: event.reason,
        promise: event.promise
      })
    })
  }

  log(level, category, data) {
    if (!this.enabled) return

    const logEntry = {
      timestamp: new Date().toISOString(),
      level,
      category,
      data,
      url: window.location.href,
      userAgent: navigator.userAgent
    }

    // Add to logs array
    this.logs.push(logEntry)

    // Keep only last N logs
    if (this.logs.length > this.maxLogs) {
      this.logs = this.logs.slice(-this.maxLogs)
    }

    // Persist to localStorage
    this.saveLogs()

    // Log to console if enabled
    if (this.logToConsole) {
      const style = this.getConsoleStyle(level)
      console.log(
        `%c[${level.toUpperCase()}] ${category}`,
        style,
        data
      )
    }
  }

  getConsoleStyle(level) {
    const styles = {
      debug: 'color: #6b7280; font-weight: bold',
      info: 'color: #3b82f6; font-weight: bold',
      warn: 'color: #f59e0b; font-weight: bold',
      error: 'color: #ef4444; font-weight: bold',
      success: 'color: #10b981; font-weight: bold'
    }
    return styles[level] || styles.info
  }

  debug(category, data) {
    this.log('debug', category, data)
  }

  info(category, data) {
    this.log('info', category, data)
  }

  warn(category, data) {
    this.log('warn', category, data)
  }

  error(category, data) {
    this.log('error', category, data)
  }

  success(category, data) {
    this.log('success', category, data)
  }

  // API Request/Response logging
  logApiRequest(config) {
    this.debug('API Request', {
      method: config.method?.toUpperCase(),
      url: config.url,
      headers: this.sanitizeHeaders(config.headers),
      data: config.data,
      params: config.params
    })
  }

  logApiResponse(response) {
    this.info('API Response', {
      status: response.status,
      statusText: response.statusText,
      url: response.config?.url,
      data: response.data,
      headers: this.sanitizeHeaders(response.headers)
    })
  }

  logApiError(error) {
    this.error('API Error', {
      message: error.message,
      url: error.config?.url,
      method: error.config?.method?.toUpperCase(),
      status: error.response?.status,
      statusText: error.response?.statusText,
      data: error.response?.data,
      stack: error.stack
    })
  }

  // Redux action logging
  logReduxAction(action, prevState, nextState) {
    this.debug('Redux Action', {
      type: action.type,
      payload: action.payload,
      prevState: this.sanitizeState(prevState),
      nextState: this.sanitizeState(nextState)
    })
  }

  sanitizeHeaders(headers) {
    if (!headers) return {}
    const sanitized = { ...headers }
    // Remove sensitive headers
    if (sanitized.Authorization) {
      sanitized.Authorization = '***REDACTED***'
    }
    return sanitized
  }

  sanitizeState(state) {
    // Only log relevant parts of state
    return {
      auth: {
        isAuthenticated: state.auth?.isAuthenticated,
        hasUser: !!state.auth?.user,
        loading: state.auth?.loading
      },
      // Add other relevant state slices
    }
  }

  // Get system info
  getSystemInfo() {
    return {
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent,
      platform: navigator.platform,
      language: navigator.language,
      screenResolution: `${window.screen.width}x${window.screen.height}`,
      windowSize: `${window.innerWidth}x${window.innerHeight}`,
      localStorage: {
        hasToken: !!localStorage.getItem('access_token'),
        tokenLength: localStorage.getItem('access_token')?.length || 0
      },
      cookies: document.cookie ? 'present' : 'none',
      online: navigator.onLine,
      memory: performance.memory ? {
        used: Math.round(performance.memory.usedJSHeapSize / 1024 / 1024) + 'MB',
        total: Math.round(performance.memory.totalJSHeapSize / 1024 / 1024) + 'MB'
      } : 'not available'
    }
  }

  // Export logs
  exportLogs() {
    const exportData = {
      exportTime: new Date().toISOString(),
      systemInfo: this.getSystemInfo(),
      logs: this.logs,
      totalLogs: this.logs.length
    }

    const blob = new Blob([JSON.stringify(exportData, null, 2)], {
      type: 'application/json'
    })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `orizon-debug-${Date.now()}.json`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)

    this.success('Debug Export', { message: 'Logs exported successfully' })
  }

  // Copy logs to clipboard
  copyLogsToClipboard() {
    const exportData = {
      exportTime: new Date().toISOString(),
      systemInfo: this.getSystemInfo(),
      logs: this.logs.slice(-50), // Last 50 logs
      totalLogs: this.logs.length
    }

    const text = JSON.stringify(exportData, null, 2)

    // Try modern clipboard API first
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text)
        .then(() => {
          this.success('Debug Copy', { message: 'Last 50 logs copied to clipboard' })
        })
        .catch((err) => {
          this.error('Debug Copy', { message: 'Failed to copy logs', error: err.message })
          this.fallbackCopy(text)
        })
    } else {
      // Fallback for HTTP or older browsers
      this.fallbackCopy(text)
    }
  }

  // Fallback copy method using textarea
  fallbackCopy(text) {
    try {
      const textarea = document.createElement('textarea')
      textarea.value = text
      textarea.style.position = 'fixed'
      textarea.style.opacity = '0'
      document.body.appendChild(textarea)
      textarea.select()
      const success = document.execCommand('copy')
      document.body.removeChild(textarea)

      if (success) {
        this.success('Debug Copy', { message: 'Last 50 logs copied to clipboard (fallback method)' })
      } else {
        this.warn('Debug Copy', { message: 'Copy failed. Please use Download button instead.' })
      }
    } catch (err) {
      this.error('Debug Copy', {
        message: 'Copy not supported. Please use Download button instead.',
        error: err.message
      })
    }
  }

  // Clear logs
  clearLogs() {
    this.logs = []
    this.saveLogs()
    this.info('Debug Clear', { message: 'All logs cleared' })
  }

  // Get logs filtered by level
  getLogsByLevel(level) {
    return this.logs.filter(log => log.level === level)
  }

  // Get recent logs
  getRecentLogs(count = 50) {
    return this.logs.slice(-count)
  }

  // Persistence
  saveLogs() {
    try {
      localStorage.setItem('debug_logs', JSON.stringify(this.logs.slice(-100))) // Save last 100
    } catch (err) {
      console.error('Failed to save logs to localStorage:', err)
    }
  }

  loadLogs() {
    try {
      const saved = localStorage.getItem('debug_logs')
      if (saved) {
        this.logs = JSON.parse(saved)
      }
    } catch (err) {
      console.error('Failed to load logs from localStorage:', err)
      this.logs = []
    }
  }

  // Performance monitoring
  startPerformanceMark(name) {
    performance.mark(`${name}-start`)
  }

  endPerformanceMark(name) {
    performance.mark(`${name}-end`)
    try {
      performance.measure(name, `${name}-start`, `${name}-end`)
      const measure = performance.getEntriesByName(name)[0]
      this.debug('Performance', {
        name,
        duration: `${measure.duration.toFixed(2)}ms`
      })
    } catch (err) {
      this.warn('Performance', { message: 'Failed to measure performance', error: err })
    }
  }
}

export default new DebugService()
