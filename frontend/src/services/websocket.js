class WebSocketService {
  constructor() {
    this.ws = null
    this.reconnectInterval = 5000
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = 5
    this.listeners = new Map()
    this.isConnecting = false
  }

  connect(token) {
    if (this.ws?.readyState === WebSocket.OPEN || this.isConnecting) {
      return
    }

    this.isConnecting = true
    // Auto-detect WebSocket protocol based on page protocol
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = import.meta.env.VITE_WS_URL || `${protocol}//${window.location.host}`
    
    try {
      this.ws = new WebSocket(`${wsUrl}/ws?token=${token}`)
      
      this.ws.onopen = () => {
        console.log('WebSocket connected')
        this.isConnecting = false
        this.reconnectAttempts = 0
        this.emit('connected', {})
        
        // Send ping every 30 seconds
        this.pingInterval = setInterval(() => {
          this.send({ type: 'ping', timestamp: Date.now() })
        }, 30000)
      }
      
      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          this.emit(data.type, data)
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error)
        }
      }
      
      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        this.emit('error', error)
      }
      
      this.ws.onclose = () => {
        console.log('WebSocket disconnected')
        this.isConnecting = false
        this.emit('disconnected', {})
        
        if (this.pingInterval) {
          clearInterval(this.pingInterval)
        }
        
        // Attempt to reconnect
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
          this.reconnectAttempts++
          console.log(`Reconnecting... Attempt ${this.reconnectAttempts}`)
          setTimeout(() => this.connect(token), this.reconnectInterval)
        }
      }
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error)
      this.isConnecting = false
    }
  }

  disconnect() {
    if (this.pingInterval) {
      clearInterval(this.pingInterval)
    }
    
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
    
    this.listeners.clear()
    this.reconnectAttempts = this.maxReconnectAttempts // Prevent reconnect
  }

  send(data) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data))
    } else {
      console.warn('WebSocket is not connected')
    }
  }

  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, [])
    }
    this.listeners.get(event).push(callback)
  }

  off(event, callback) {
    if (this.listeners.has(event)) {
      const callbacks = this.listeners.get(event)
      const index = callbacks.indexOf(callback)
      if (index > -1) {
        callbacks.splice(index, 1)
      }
    }
  }

  emit(event, data) {
    if (this.listeners.has(event)) {
      this.listeners.get(event).forEach((callback) => callback(data))
    }
  }

  subscribe(nodeId) {
    this.send({
      type: 'subscribe',
      node_id: nodeId,
    })
  }
}

export default new WebSocketService()
