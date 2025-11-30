/**
 * Orizon Debug Logger - Complete debugging system
 * Tracks: API calls, React renders, State changes, Layout info
 */

const DEBUG_ENABLED = true
const LOG_TO_CONSOLE = true
const LOG_TO_PANEL = true

// Store logs for panel display
const debugLogs = []
const MAX_LOGS = 100

// Colors for different log types
const COLORS = {
  api: '#00d4ff',
  render: '#00ff88',
  state: '#ffaa00',
  error: '#ff4444',
  info: '#888888',
  layout: '#ff00ff',
  data: '#00ffff'
}

// Format timestamp
const timestamp = () => new Date().toISOString().split('T')[1].slice(0, 12)

// Main logger function
const log = (type, category, message, data = null) => {
  if (!DEBUG_ENABLED) return

  const logEntry = {
    id: Date.now() + Math.random(),
    time: timestamp(),
    type,
    category,
    message,
    data,
    color: COLORS[type] || COLORS.info
  }

  // Add to logs array
  debugLogs.unshift(logEntry)
  if (debugLogs.length > MAX_LOGS) {
    debugLogs.pop()
  }

  // Console output
  if (LOG_TO_CONSOLE) {
    const style = `color: ${logEntry.color}; font-weight: bold;`
    const prefix = `[${logEntry.time}] [${type.toUpperCase()}] [${category}]`

    if (data) {
      console.groupCollapsed(`%c${prefix} ${message}`, style)
      console.log('Data:', data)
      if (typeof data === 'object') {
        console.table(data)
      }
      console.groupEnd()
    } else {
      console.log(`%c${prefix} ${message}`, style)
    }
  }

  // Dispatch event for panel update
  if (LOG_TO_PANEL && typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent('debug-log', { detail: logEntry }))
  }
}

// API debugging
export const debugAPI = {
  request: (method, url, body = null) => {
    log('api', 'Request', `${method} ${url}`, { method, url, body })
  },
  response: (method, url, status, data, duration) => {
    const type = status >= 400 ? 'error' : 'api'
    log(type, 'Response', `${method} ${url} → ${status} (${duration}ms)`, {
      status,
      dataType: typeof data,
      dataLength: Array.isArray(data) ? data.length : (data?.length || 'N/A'),
      data: data
    })
  },
  error: (method, url, error) => {
    log('error', 'API Error', `${method} ${url} FAILED`, {
      error: error.message,
      stack: error.stack
    })
  }
}

// React component debugging
export const debugReact = {
  mount: (componentName, props = {}) => {
    log('render', componentName, 'Component MOUNTED', {
      props: Object.keys(props),
      propsValues: props
    })
  },
  render: (componentName, reason, data = null) => {
    log('render', componentName, `Render: ${reason}`, data)
  },
  unmount: (componentName) => {
    log('render', componentName, 'Component UNMOUNTED')
  },
  effect: (componentName, effectName, deps = []) => {
    log('state', componentName, `Effect: ${effectName}`, { dependencies: deps })
  }
}

// State debugging
export const debugState = {
  change: (componentName, stateName, oldValue, newValue) => {
    log('state', componentName, `State change: ${stateName}`, {
      from: oldValue,
      to: newValue,
      changed: JSON.stringify(oldValue) !== JSON.stringify(newValue)
    })
  },
  redux: (action, prevState, nextState) => {
    log('state', 'Redux', `Action: ${action.type}`, {
      payload: action.payload,
      prevState,
      nextState
    })
  }
}

// Layout debugging
export const debugLayout = {
  page: (pageName, layoutInfo) => {
    log('layout', pageName, 'Page Layout', layoutInfo)
  },
  component: (name, dimensions) => {
    log('layout', name, 'Component Layout', dimensions)
  }
}

// Data debugging
export const debugData = {
  received: (source, data) => {
    log('data', source, 'Data received', {
      type: typeof data,
      isArray: Array.isArray(data),
      length: Array.isArray(data) ? data.length : (data ? Object.keys(data).length : 0),
      sample: Array.isArray(data) ? data.slice(0, 2) : data,
      fullData: data
    })
  },
  transformed: (source, original, transformed) => {
    log('data', source, 'Data transformed', {
      original,
      transformed,
      changes: 'See data above'
    })
  }
}

// Get all logs
export const getLogs = () => [...debugLogs]

// Clear logs
export const clearLogs = () => {
  debugLogs.length = 0
}

// Export for global access
if (typeof window !== 'undefined') {
  window.orizonDebug = {
    api: debugAPI,
    react: debugReact,
    state: debugState,
    layout: debugLayout,
    data: debugData,
    getLogs,
    clearLogs,
    enable: () => { window.ORIZON_DEBUG = true },
    disable: () => { window.ORIZON_DEBUG = false }
  }
}

export default {
  api: debugAPI,
  react: debugReact,
  state: debugState,
  layout: debugLayout,
  data: debugData,
  getLogs,
  clearLogs
}
