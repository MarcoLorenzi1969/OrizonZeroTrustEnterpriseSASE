/**
 * RDP Proxy Test Client
 * Simple WebSocket client to test the RDP proxy server
 *
 * Usage: node src/test-client.js [host] [port]
 */

import WebSocket from 'ws'
import jwt from 'jsonwebtoken'

const RDP_PROXY_URL = process.env.RDP_PROXY_URL || 'ws://localhost:8766/rdp'
const JWT_SECRET = process.env.JWT_SECRET_KEY || process.env.SECRET_KEY || 'dev-secret-key'

// Generate a test JWT token
function generateTestToken() {
  return jwt.sign(
    {
      sub: 'test-user',
      email: 'test@orizon.local',
      role: 'ADMIN',
      exp: Math.floor(Date.now() / 1000) + 3600 // 1 hour
    },
    JWT_SECRET
  )
}

// Parse command line arguments
const targetHost = process.argv[2] || 'localhost'
const targetPort = parseInt(process.argv[3]) || 3389

console.log('========================================')
console.log('  Orizon RDP Proxy Test Client')
console.log('========================================')
console.log(`Proxy URL: ${RDP_PROXY_URL}`)
console.log(`Target: ${targetHost}:${targetPort}`)
console.log('')

const ws = new WebSocket(RDP_PROXY_URL)

ws.on('open', () => {
  console.log('[OK] Connected to RDP Proxy')

  // Send connect request
  const connectRequest = {
    type: 'connect',
    token: generateTestToken(),
    nodeId: 'test-node-001',
    config: {
      host: targetHost,
      port: targetPort,
      width: 1280,
      height: 720,
      colorDepth: 24,
      username: 'test',
      password: '',
      domain: ''
    }
  }

  console.log('[->] Sending connect request...')
  ws.send(JSON.stringify(connectRequest))
})

ws.on('message', (data) => {
  // Check if binary or text
  if (Buffer.isBuffer(data) && data.length > 0 && data[0] === 0x01) {
    // Binary bitmap data
    const destLeft = data.readUInt16LE(1)
    const destTop = data.readUInt16LE(3)
    const width = data.readUInt16LE(5)
    const height = data.readUInt16LE(7)
    const bpp = data[9]
    const compressed = data[10] === 1

    console.log(`[<-] Bitmap: ${width}x${height} @ ${destLeft},${destTop} (${bpp}bpp, compressed=${compressed}, ${data.length} bytes)`)
  } else {
    // JSON message
    try {
      const message = JSON.parse(data.toString())
      console.log(`[<-] ${message.type}:`, JSON.stringify(message, null, 2))

      if (message.type === 'connected') {
        console.log('[OK] RDP Session established!')
        console.log(`     Session ID: ${message.sessionId}`)
        console.log('')
        console.log('Sending test events...')

        // Send a test mouse move
        setTimeout(() => {
          ws.send(JSON.stringify({
            type: 'mouse',
            event: 'move',
            x: 640,
            y: 360,
            button: 0
          }))
          console.log('[->] Mouse move to 640,360')
        }, 1000)

        // Send a test click
        setTimeout(() => {
          ws.send(JSON.stringify({
            type: 'mouse',
            event: 'down',
            x: 640,
            y: 360,
            button: 0
          }))
          ws.send(JSON.stringify({
            type: 'mouse',
            event: 'up',
            x: 640,
            y: 360,
            button: 0
          }))
          console.log('[->] Mouse click at 640,360')
        }, 2000)

        // Disconnect after 5 seconds
        setTimeout(() => {
          console.log('[->] Disconnecting...')
          ws.send(JSON.stringify({ type: 'disconnect' }))
          ws.close()
        }, 5000)
      }

      if (message.type === 'error') {
        console.error('[ERROR]', message.message)
      }

    } catch (e) {
      console.log('[<-] Raw:', data.toString().substring(0, 100))
    }
  }
})

ws.on('close', (code, reason) => {
  console.log(`[CLOSED] Code: ${code}, Reason: ${reason}`)
  console.log('')
  console.log('Test completed.')
  process.exit(0)
})

ws.on('error', (error) => {
  console.error('[ERROR] WebSocket error:', error.message)
  process.exit(1)
})

// Timeout after 30 seconds
setTimeout(() => {
  console.log('[TIMEOUT] Test timed out after 30 seconds')
  ws.close()
  process.exit(1)
}, 30000)
