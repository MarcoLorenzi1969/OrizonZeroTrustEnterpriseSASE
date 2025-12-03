/**
 * Orizon RDP Proxy Server
 * WebSocket-to-RDP bridge for web-based Remote Desktop access
 *
 * Architecture:
 * Browser (WebRDP.jsx) <-> WebSocket <-> This Proxy <-> RDP Protocol <-> Windows Server
 *
 * Author: Marco @ Syneto/Orizon
 * Version: 1.0.0
 */

import { WebSocketServer, WebSocket } from 'ws'
import { createServer } from 'http'
import { v4 as uuidv4 } from 'uuid'
import jwt from 'jsonwebtoken'
import winston from 'winston'
import dotenv from 'dotenv'

// Load environment variables
dotenv.config()

// Configuration
const CONFIG = {
  port: parseInt(process.env.RDP_PROXY_PORT || '8766'),
  host: process.env.RDP_PROXY_HOST || '0.0.0.0',
  jwtSecret: process.env.JWT_SECRET_KEY || process.env.SECRET_KEY || 'dev-secret-key',
  maxSessions: parseInt(process.env.RDP_MAX_SESSIONS || '100'),
  sessionTimeout: parseInt(process.env.RDP_SESSION_TIMEOUT || '3600000'), // 1 hour
  heartbeatInterval: 30000, // 30 seconds
  allowedOrigins: (process.env.RDP_ALLOWED_ORIGINS || '*').split(',')
}

// Logger setup
const logger = winston.createLogger({
  level: process.env.LOG_LEVEL || 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.colorize(),
    winston.format.printf(({ timestamp, level, message, ...meta }) => {
      return `${timestamp} [RDP-Proxy] ${level}: ${message} ${Object.keys(meta).length ? JSON.stringify(meta) : ''}`
    })
  ),
  transports: [
    new winston.transports.Console()
  ]
})

// Active RDP sessions
const sessions = new Map()

// Session class to manage individual RDP connections
class RDPSession {
  constructor(sessionId, wsClient, config) {
    this.sessionId = sessionId
    this.wsClient = wsClient
    this.config = config
    this.rdpClient = null
    this.connected = false
    this.lastActivity = Date.now()
    this.bytesReceived = 0
    this.bytesSent = 0
    this.frameCount = 0
  }

  async connect() {
    logger.info(`Connecting RDP session ${this.sessionId} to ${this.config.host}:${this.config.port}`)

    // Use mock mode if host is empty or 'mock'
    if (!this.config.host || this.config.host === 'mock' || this.config.host === 'localhost') {
      logger.info('Using mock RDP mode (no real RDP server)')
      return this.connectMock()
    }

    try {
      // Dynamic import of node-rdpjs-2 (may not be installed)
      let rdp
      try {
        rdp = await import('node-rdpjs-2')
      } catch (importError) {
        // If node-rdpjs-2 is not available, use mock mode
        logger.warn('node-rdpjs-2 not available, using mock RDP mode')
        return this.connectMock()
      }

      // Create RDP client
      this.rdpClient = rdp.createClient({
        domain: this.config.domain || '',
        userName: this.config.username || 'Administrator',
        password: this.config.password || '',
        enablePerf: true,
        autoLogin: true,
        screen: {
          width: this.config.width || 1280,
          height: this.config.height || 720
        },
        locale: this.config.locale || 'en',
        logLevel: 'INFO'
      })

      // Handle RDP events
      this.rdpClient.on('connect', () => {
        this.connected = true
        logger.info(`RDP session ${this.sessionId} connected`)
        this.sendToClient({ type: 'connected', sessionId: this.sessionId })
      })

      this.rdpClient.on('bitmap', (bitmap) => {
        this.handleBitmap(bitmap)
      })

      this.rdpClient.on('close', () => {
        this.connected = false
        logger.info(`RDP session ${this.sessionId} closed`)
        this.sendToClient({ type: 'close' })
        this.cleanup()
      })

      this.rdpClient.on('error', (err) => {
        logger.error(`RDP session ${this.sessionId} error:`, err)
        this.sendToClient({ type: 'error', message: err.message })
      })

      // Connect to RDP server
      this.rdpClient.connect(this.config.host, this.config.port)

    } catch (error) {
      logger.error(`Failed to create RDP session ${this.sessionId}:`, error)
      this.sendToClient({ type: 'error', message: error.message })
      throw error
    }
  }

  // Mock connection for testing without actual RDP server
  async connectMock() {
    logger.info(`Starting mock RDP session ${this.sessionId}`)

    this.connected = true
    this.sendToClient({ type: 'connected', sessionId: this.sessionId })

    // Send initial "desktop" frame
    setTimeout(() => {
      this.sendMockDesktop()
    }, 500)

    return true
  }

  // Generate mock desktop for testing
  sendMockDesktop() {
    if (!this.connected || this.wsClient.readyState !== WebSocket.OPEN) return

    const width = this.config.width || 1280
    const height = this.config.height || 720

    // Create a simple gradient desktop
    const pixels = new Uint8Array(width * height * 3)
    for (let y = 0; y < height; y++) {
      for (let x = 0; x < width; x++) {
        const idx = (y * width + x) * 3
        // Dark blue gradient background
        pixels[idx] = 30 + Math.floor((x / width) * 20)     // R
        pixels[idx + 1] = 41 + Math.floor((y / height) * 20) // G
        pixels[idx + 2] = 59 + Math.floor(((x + y) / (width + height)) * 40) // B
      }
    }

    // Add a simple text banner (simulated)
    const message = 'Orizon RDP Test Mode'
    const textY = Math.floor(height / 2)
    const textX = Math.floor(width / 2) - 100

    // Draw text area (white rectangle)
    for (let y = textY - 30; y < textY + 30; y++) {
      for (let x = textX - 20; x < textX + 220; x++) {
        if (x >= 0 && x < width && y >= 0 && y < height) {
          const idx = (y * width + x) * 3
          pixels[idx] = 255
          pixels[idx + 1] = 255
          pixels[idx + 2] = 255
        }
      }
    }

    // Create binary message
    const header = Buffer.alloc(11)
    header.writeUInt8(0x01, 0)           // type: bitmap
    header.writeUInt16LE(0, 1)           // destLeft
    header.writeUInt16LE(0, 3)           // destTop
    header.writeUInt16LE(width, 5)       // width
    header.writeUInt16LE(height, 7)      // height
    header.writeUInt8(24, 9)             // bitsPerPixel
    header.writeUInt8(0, 10)             // isCompressed

    const data = Buffer.concat([header, Buffer.from(pixels)])
    this.wsClient.send(data)

    this.frameCount++
    this.bytesSent += data.length
  }

  handleBitmap(bitmap) {
    if (this.wsClient.readyState !== WebSocket.OPEN) return

    this.lastActivity = Date.now()

    // Convert RDP bitmap to binary message format
    const header = Buffer.alloc(11)
    header.writeUInt8(0x01, 0)                          // type: bitmap
    header.writeUInt16LE(bitmap.destLeft || 0, 1)       // destLeft
    header.writeUInt16LE(bitmap.destTop || 0, 3)        // destTop
    header.writeUInt16LE(bitmap.width, 5)               // width
    header.writeUInt16LE(bitmap.height, 7)              // height
    header.writeUInt8(bitmap.bitsPerPixel || 24, 9)     // bitsPerPixel
    header.writeUInt8(bitmap.isCompressed ? 1 : 0, 10)  // isCompressed

    const data = Buffer.concat([header, Buffer.from(bitmap.data)])

    try {
      this.wsClient.send(data)
      this.frameCount++
      this.bytesSent += data.length
    } catch (error) {
      logger.error(`Failed to send bitmap for session ${this.sessionId}:`, error)
    }
  }

  handleMouseEvent(event) {
    if (!this.rdpClient || !this.connected) {
      // Mock mode - just acknowledge
      return
    }

    this.lastActivity = Date.now()

    try {
      switch (event.event) {
        case 'move':
          this.rdpClient.sendPointerEvent(event.x, event.y, 0, false)
          break
        case 'down':
          this.rdpClient.sendPointerEvent(event.x, event.y, this.buttonToFlag(event.button), true)
          break
        case 'up':
          this.rdpClient.sendPointerEvent(event.x, event.y, this.buttonToFlag(event.button), false)
          break
      }
    } catch (error) {
      logger.error(`Mouse event error for session ${this.sessionId}:`, error)
    }
  }

  handleKeyboardEvent(event) {
    if (!this.rdpClient || !this.connected) {
      // Mock mode - just acknowledge
      return
    }

    this.lastActivity = Date.now()

    try {
      const isDown = event.event === 'down'
      this.rdpClient.sendKeyEventScancode(event.scanCode, isDown, event.isExtended)
    } catch (error) {
      logger.error(`Keyboard event error for session ${this.sessionId}:`, error)
    }
  }

  handleWheelEvent(event) {
    if (!this.rdpClient || !this.connected) return

    this.lastActivity = Date.now()

    try {
      // RDP wheel events
      const delta = event.deltaY > 0 ? -120 : 120
      this.rdpClient.sendWheelEvent(event.x, event.y, delta, false)
    } catch (error) {
      logger.error(`Wheel event error for session ${this.sessionId}:`, error)
    }
  }

  buttonToFlag(button) {
    // Convert JavaScript mouse button to RDP flag
    switch (button) {
      case 0: return 1  // Left button
      case 1: return 4  // Middle button
      case 2: return 2  // Right button
      default: return 0
    }
  }

  sendToClient(message) {
    if (this.wsClient.readyState === WebSocket.OPEN) {
      try {
        this.wsClient.send(JSON.stringify(message))
      } catch (error) {
        logger.error(`Failed to send to client for session ${this.sessionId}:`, error)
      }
    }
  }

  getStats() {
    return {
      sessionId: this.sessionId,
      connected: this.connected,
      bytesReceived: this.bytesReceived,
      bytesSent: this.bytesSent,
      frameCount: this.frameCount,
      lastActivity: this.lastActivity,
      uptime: Date.now() - (this.createdAt || Date.now())
    }
  }

  cleanup() {
    if (this.rdpClient) {
      try {
        this.rdpClient.close()
      } catch (error) {
        // Ignore cleanup errors
      }
      this.rdpClient = null
    }
    this.connected = false
    sessions.delete(this.sessionId)
    logger.info(`Session ${this.sessionId} cleaned up`)
  }
}

// JWT token verification
function verifyToken(token) {
  try {
    if (!token) return null
    const decoded = jwt.verify(token, CONFIG.jwtSecret)
    return decoded
  } catch (error) {
    logger.warn('JWT verification failed:', error.message)
    return null
  }
}

// Create HTTP server
const server = createServer((req, res) => {
  // Health check endpoint
  if (req.url === '/health') {
    res.writeHead(200, { 'Content-Type': 'application/json' })
    res.end(JSON.stringify({
      status: 'ok',
      activeSessions: sessions.size,
      maxSessions: CONFIG.maxSessions,
      uptime: process.uptime()
    }))
    return
  }

  // Stats endpoint
  if (req.url === '/stats') {
    const stats = Array.from(sessions.values()).map(s => s.getStats())
    res.writeHead(200, { 'Content-Type': 'application/json' })
    res.end(JSON.stringify({
      activeSessions: sessions.size,
      sessions: stats
    }))
    return
  }

  res.writeHead(404)
  res.end('Not Found')
})

// Create WebSocket server
const wss = new WebSocketServer({
  server,
  path: '/rdp'
})

// Handle WebSocket connections
wss.on('connection', (ws, req) => {
  const clientIp = req.socket.remoteAddress
  logger.info(`New WebSocket connection from ${clientIp}`)

  let session = null
  let authenticated = false

  // Handle messages
  ws.on('message', async (data) => {
    try {
      // Try to parse as JSON
      const message = JSON.parse(data.toString())

      switch (message.type) {
        case 'connect':
          // Verify JWT token
          const user = verifyToken(message.token)
          if (!user) {
            ws.send(JSON.stringify({ type: 'error', message: 'Authentication failed' }))
            ws.close(4001, 'Unauthorized')
            return
          }

          authenticated = true

          // Check session limit
          if (sessions.size >= CONFIG.maxSessions) {
            ws.send(JSON.stringify({ type: 'error', message: 'Maximum sessions reached' }))
            ws.close(4002, 'Session limit')
            return
          }

          // Create new RDP session
          const sessionId = uuidv4()
          session = new RDPSession(sessionId, ws, message.config)
          sessions.set(sessionId, session)

          logger.info(`Creating RDP session ${sessionId} for user ${user.sub || user.email || 'unknown'}`)

          try {
            await session.connect()
          } catch (error) {
            session.cleanup()
            ws.send(JSON.stringify({ type: 'error', message: `Connection failed: ${error.message}` }))
          }
          break

        case 'mouse':
          if (session && authenticated) {
            session.handleMouseEvent(message)
          }
          break

        case 'keyboard':
          if (session && authenticated) {
            session.handleKeyboardEvent(message)
          }
          break

        case 'wheel':
          if (session && authenticated) {
            session.handleWheelEvent(message)
          }
          break

        case 'disconnect':
          if (session) {
            session.cleanup()
          }
          break

        default:
          logger.warn(`Unknown message type: ${message.type}`)
      }

    } catch (error) {
      logger.error('Message handling error:', error)
    }
  })

  // Handle close
  ws.on('close', (code, reason) => {
    logger.info(`WebSocket closed: ${code} ${reason}`)
    if (session) {
      session.cleanup()
    }
  })

  // Handle error
  ws.on('error', (error) => {
    logger.error('WebSocket error:', error)
    if (session) {
      session.cleanup()
    }
  })

  // Send ping to keep connection alive
  const pingInterval = setInterval(() => {
    if (ws.readyState === WebSocket.OPEN) {
      ws.ping()
    } else {
      clearInterval(pingInterval)
    }
  }, CONFIG.heartbeatInterval)
})

// Session cleanup timer
setInterval(() => {
  const now = Date.now()
  for (const [sessionId, session] of sessions) {
    if (now - session.lastActivity > CONFIG.sessionTimeout) {
      logger.info(`Session ${sessionId} timed out`)
      session.cleanup()
    }
  }
}, 60000) // Check every minute

// Start server
server.listen(CONFIG.port, CONFIG.host, () => {
  logger.info(`Orizon RDP Proxy Server started on ${CONFIG.host}:${CONFIG.port}`)
  logger.info(`WebSocket endpoint: ws://${CONFIG.host}:${CONFIG.port}/rdp`)
  logger.info(`Health check: http://${CONFIG.host}:${CONFIG.port}/health`)
  logger.info(`Max sessions: ${CONFIG.maxSessions}`)
})

// Graceful shutdown
process.on('SIGTERM', () => {
  logger.info('Received SIGTERM, shutting down...')
  for (const session of sessions.values()) {
    session.cleanup()
  }
  server.close(() => {
    logger.info('Server closed')
    process.exit(0)
  })
})

process.on('SIGINT', () => {
  logger.info('Received SIGINT, shutting down...')
  for (const session of sessions.values()) {
    session.cleanup()
  }
  server.close(() => {
    logger.info('Server closed')
    process.exit(0)
  })
})
