# Orizon RDP Proxy

WebSocket-to-RDP bridge for web-based Remote Desktop access.

## Architecture

```
Browser (WebRDP.jsx) <-> WebSocket <-> RDP Proxy <-> RDP Protocol <-> Windows Server
          |                                 |
      Canvas rendering            node-rdpjs-2 client
      Mouse/Keyboard events       Bitmap encoding
```

## Quick Start

### Development Mode

```bash
# Install dependencies
npm install

# Start the server
npm run dev

# Run test client
npm test
```

### Docker Mode

```bash
# Build image
docker build -t orizon-rdp-proxy .

# Run container
docker run -p 8766:8766 \
  -e JWT_SECRET_KEY=your-secret-key \
  orizon-rdp-proxy
```

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `RDP_PROXY_PORT` | 8766 | WebSocket server port |
| `RDP_PROXY_HOST` | 0.0.0.0 | Bind address |
| `JWT_SECRET_KEY` | dev-secret-key | JWT verification secret |
| `RDP_MAX_SESSIONS` | 100 | Maximum concurrent sessions |
| `RDP_SESSION_TIMEOUT` | 3600000 | Session timeout (ms) |
| `LOG_LEVEL` | info | Log level (debug, info, warn, error) |

## API

### WebSocket Endpoint

`ws://host:8766/rdp`

### Message Protocol

**Connect Request:**
```json
{
  "type": "connect",
  "token": "JWT_TOKEN",
  "nodeId": "node-uuid",
  "config": {
    "host": "rdp-server-ip",
    "port": 3389,
    "width": 1280,
    "height": 720,
    "colorDepth": 24,
    "username": "Administrator",
    "password": "password",
    "domain": "WORKGROUP"
  }
}
```

**Mouse Event:**
```json
{
  "type": "mouse",
  "event": "move|down|up",
  "x": 640,
  "y": 360,
  "button": 0
}
```

**Keyboard Event:**
```json
{
  "type": "keyboard",
  "event": "down|up",
  "keyCode": 65,
  "scanCode": 30,
  "isExtended": false
}
```

**Bitmap Response (Binary):**
```
[type:1][destLeft:2][destTop:2][width:2][height:2][bpp:1][compressed:1][data:...]
```

### HTTP Endpoints

- `GET /health` - Health check
- `GET /stats` - Session statistics

## Integration with Orizon

Add to `docker-compose.yml`:

```yaml
rdp-proxy:
  build: ./rdp-proxy
  ports:
    - "8766:8766"
  environment:
    - JWT_SECRET_KEY=${SECRET_KEY}
    - RDP_MAX_SESSIONS=50
  restart: unless-stopped
```

Add to frontend `.env`:

```
VITE_RDP_PROXY_URL=ws://localhost:8766
```

## Testing

```bash
# Test with mock RDP (no actual RDP server needed)
npm test

# Test with real RDP server
node src/test-client.js 192.168.1.100 3389
```

## License

MIT - Marco @ Syneto/Orizon
