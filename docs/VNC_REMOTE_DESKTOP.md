# Orizon Zero Trust Connect - VNC Remote Desktop

**Version:** 1.1
**Author:** Marco Lorenzi @ Syneto/Orizon
**Date:** November 2025

---

## 📖 Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Components](#components)
4. [Security Model](#security-model)
5. [Installation](#installation)
6. [Configuration](#configuration)
7. [Usage](#usage)
8. [API Reference](#api-reference)
9. [Troubleshooting](#troubleshooting)
10. [Performance](#performance)

---

## 🎯 Overview

### What is VNC Remote Desktop?

The VNC Remote Desktop feature adds secure, Zero Trust remote desktop access to Orizon Zero Trust Connect. It allows users to access the desktop of any edge node through a web browser without exposing VNC ports to the Internet.

### Key Features

- ✅ **Zero Trust Architecture**: No VNC ports exposed, all connections originate from edge
- ✅ **Web-Based**: Full desktop access via browser (HTML5 noVNC client)
- ✅ **JWT Authentication**: Secure session tokens with expiration
- ✅ **RBAC Integration**: Role-based access control (SuperUser/Admin/User)
- ✅ **ACL Validation**: Access control lists enforce Zero Trust policies
- ✅ **Quality Settings**: Low/Medium/High/Lossless quality presets
- ✅ **Session Management**: Create, monitor, and terminate sessions
- ✅ **Audit Logging**: Complete audit trail in MongoDB
- ✅ **Auto-Reconnect**: Resilient connections with automatic retry
- ✅ **Metrics**: Real-time bandwidth and latency monitoring

### Use Cases

1. **Remote Administration**: Access server desktops for maintenance
2. **Technical Support**: Help users by viewing their desktop
3. **Development**: Access remote development environments
4. **Training**: Remote desktop sharing for training sessions
5. **Emergency Access**: Quick desktop access during incidents

---

## 🏗️ Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CLIENT (Browser)                            │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │  React Frontend                                              │   │
│  │  • VncViewer Component (noVNC integration)                  │   │
│  │  • Session Management UI                                    │   │
│  │  • Quality Controls                                         │   │
│  └────────────────────────────────────────────────────────────┘   │
│                            │                                        │
│                            │ HTTPS/WSS                              │
└────────────────────────────┼────────────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────────────┐
│                         HUB SERVER                                   │
│                                                                      │
│  ┌────────────────────┐         ┌────────────────────────────┐    │
│  │  FastAPI Backend   │         │  VNC Gateway Service       │    │
│  │                    │         │                            │    │
│  │  • Session Mgmt    │◄────────┤  • WebSocket Server        │    │
│  │  • JWT Generation  │         │  • JWT Validation          │    │
│  │  • RBAC/ACL        │         │  • WS ↔ TCP Proxy          │    │
│  │  • Audit Logging   │         │  • Metrics Reporting       │    │
│  └────────────────────┘         └────────────────────────────┘    │
│         │                                   │                       │
│         │ WebSocket                         │ TCP (tunnel port)     │
│         │ Command                           │                       │
└─────────┼───────────────────────────────────┼───────────────────────┘
          │                                   │
          │                                   │
          ↓                                   │
┌─────────────────────────────────────────────┼───────────────────────┐
│                      EDGE NODE              │                       │
│                                             │                       │
│  ┌─────────────────────────────┐            │                       │
│  │  Orizon Agent (VNC Support) │            │                       │
│  │                             │            │                       │
│  │  • WebSocket Client         │            │                       │
│  │  • Command Handler          │            │                       │
│  │  • VNC Tunnel Manager       │◄───────────┘                       │
│  └─────────────────────────────┘                                   │
│                │                                                    │
│                │ TCP (localhost:5900)                               │
│                ↓                                                    │
│  ┌─────────────────────────────┐                                   │
│  │  VNC Server (X11vnc/TigerVNC)                                  │
│  │  • Desktop Sharing          │                                   │
│  │  • RFB Protocol             │                                   │
│  └─────────────────────────────┘                                   │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### Data Flow

#### Session Creation Flow

```
1. User clicks "New Session" in UI
   ↓
2. Frontend → POST /api/v1/vnc/sessions
   {
     "node_id": "uuid",
     "name": "Production Server",
     "quality": "medium",
     "max_duration_seconds": 300
   }
   ↓
3. Backend (FastAPI):
   • Validates RBAC (user has access to node)
   • Checks node status (must be online)
   • Validates ACL (Zero Trust policy)
   • Allocates tunnel port (50000-59999)
   • Creates session in PostgreSQL
   • Generates JWT session token (exp: 5 min)
   • Sends WebSocket command to Edge Agent:
     {
       "action": "create_vnc_tunnel",
       "session_id": "uuid",
       "tunnel_port": 50123,
       "vnc_host": "localhost",
       "vnc_port": 5900
     }
   ↓
4. Edge Agent:
   • Receives command via WebSocket
   • Creates reverse TCP tunnel:
     Hub:50123 ←→ Edge:localhost:5900
   • Sends confirmation to Backend
   ↓
5. Backend:
   • Updates session status to "connecting"
   • Returns session to Frontend:
     {
       "id": "uuid",
       "websocket_url": "wss://hub:6080/vnc/uuid?token=jwt...",
       "session_token": "jwt...",
       "status": "connecting"
     }
   ↓
6. Frontend:
   • Navigates to VncViewer page
   • Initializes noVNC with websocket_url
```

#### VNC Streaming Flow

```
1. noVNC Client (Browser):
   • Connects to wss://hub:6080/vnc/{session_id}?token={jwt}
   ↓
2. VNC Gateway:
   • Validates JWT token
   • Extracts tunnel_port from token
   • Opens TCP connection to localhost:tunnel_port
   • Starts bidirectional forwarding:
     WebSocket (Client) ↔ TCP (Tunnel)
   ↓
3. Edge Agent Tunnel:
   • Receives data from hub:tunnel_port
   • Forwards to localhost:5900 (VNC server)
   • Forwards responses back to hub
   ↓
4. VNC Server:
   • Sends RFB (VNC protocol) frames
   • Receives keyboard/mouse input
   ↓
5. Data flows back through same path:
   VNC Server → Edge Tunnel → Hub Tunnel → VNC Gateway → noVNC Client
```

---

## 🧩 Components

### 1. Backend (FastAPI)

**Location:** `backend/app/`

#### Files Added/Modified

- `models/vnc_session.py` - SQLAlchemy model for VNC sessions
- `schemas/vnc.py` - Pydantic schemas for API requests/responses
- `services/vnc_service.py` - VNC session management logic
- `api/v1/endpoints/vnc.py` - REST API endpoints
- `api/v1/router.py` - Router registration (MODIFIED)

#### Key Features

- Session CRUD operations
- JWT token generation (HS256, 5 min expiration)
- RBAC validation
- ACL enforcement
- Port allocation with Redis locking
- WebSocket commands to agents
- Audit logging to MongoDB
- Background session cleanup task

#### Database Schema

**Table:** `vnc_sessions`

| Column | Type | Description |
|--------|------|-------------|
| id | VARCHAR(36) | Primary key (UUID) |
| name | VARCHAR(255) | Session display name |
| status | VARCHAR(50) | pending/connecting/active/disconnected/expired/error/terminated |
| tunnel_port | INTEGER | Allocated tunnel port on hub |
| websocket_path | VARCHAR(500) | WebSocket endpoint path |
| session_token | VARCHAR(1024) | JWT for session auth |
| vnc_host | VARCHAR(255) | VNC server host (default: localhost) |
| vnc_port | INTEGER | VNC server port (default: 5900) |
| quality | VARCHAR(20) | low/medium/high/lossless |
| screen_width | INTEGER | Screen width in pixels |
| screen_height | INTEGER | Screen height in pixels |
| max_duration_seconds | INTEGER | Session max duration |
| expires_at | TIMESTAMP | Session expiration time |
| bytes_sent | BIGINT | Total bytes sent |
| bytes_received | BIGINT | Total bytes received |
| node_id | VARCHAR(36) | FK to nodes table |
| user_id | VARCHAR(36) | FK to users table |
| created_at | TIMESTAMP | Creation timestamp |

### 2. VNC Gateway Service

**Location:** `services/vnc_gateway/`

#### Files

- `vnc_gateway.py` - WebSocket server and TCP proxy
- `requirements.txt` - Python dependencies
- `Dockerfile` - Container image definition

#### Responsibilities

1. Accept WebSocket connections from browsers
2. Validate JWT session tokens
3. Extract tunnel port from token
4. Open TCP connection to tunnel port
5. Forward RFB protocol bidirectionally:
   - WebSocket (binary) → TCP (tunnel)
   - TCP (tunnel) → WebSocket (binary)
6. Track connection metrics
7. Handle disconnections gracefully

#### Configuration

Environment variables:

- `JWT_SECRET_KEY` - Secret for JWT validation (must match backend)
- `BACKEND_URL` - Backend API URL (for future enhancements)
- `VNC_GATEWAY_HOST` - Listen host (default: 0.0.0.0)
- `VNC_GATEWAY_PORT` - Listen port (default: 6080)
- `TUNNEL_HOST` - Tunnel host (default: localhost)

### 3. Edge Agent (VNC Support)

**Location:** `agents/`

#### Files

- `vnc_tunnel_handler.py` - VNC tunnel management module
- `orizon_agent_vnc.py` - Enhanced agent with VNC support

#### Features

- WebSocket connection to hub
- Command handler for VNC operations:
  - `create_vnc_tunnel` - Create reverse tunnel
  - `close_vnc_tunnel` - Close tunnel
  - `get_vnc_status` - Get tunnel status
- Reverse TCP tunnel creation
- Bidirectional traffic forwarding
- VNC server connectivity check
- Auto-reconnect with exponential backoff
- Metrics collection and reporting

#### Commands

**Create VNC Tunnel:**
```json
{
  "action": "create_vnc_tunnel",
  "session_id": "uuid",
  "tunnel_port": 50123,
  "vnc_host": "localhost",
  "vnc_port": 5900
}
```

**Close VNC Tunnel:**
```json
{
  "action": "close_vnc_tunnel",
  "session_id": "uuid"
}
```

### 4. Frontend (React)

**Location:** `frontend/src/`

#### Files

- `components/VncViewer.jsx` - noVNC integration component
- `pages/VncSessions.jsx` - Session management page
- `pages/VncViewer.jsx` - Full-screen viewer page

#### Features

- noVNC HTML5 VNC client
- Quality controls (low/medium/high/lossless)
- Fullscreen mode
- Connection status monitoring
- Auto-reconnect on disconnect
- Ctrl+Alt+Del sending
- View-only mode support
- Session creation wizard
- Active sessions dashboard

#### Dependencies

- `@novnc/novnc` - HTML5 VNC client
- `lucide-react` - Icons
- `axios` - HTTP client
- `react-router-dom` - Routing

---

## 🔐 Security Model

### Zero Trust Principles Applied

#### 1. Never Trust, Always Verify

- **JWT Validation**: Every WebSocket connection validates JWT token
- **Token Expiration**: Sessions expire after max_duration (default 5 min)
- **No Persistent Credentials**: VNC server credentials not stored

#### 2. Least Privilege Access

- **RBAC Enforcement**: Users can only access their own nodes
  - `USER`: Own nodes only
  - `ADMIN`: Can access clients' nodes
  - `SUPER_ADMIN`: Can access resellers' nodes
  - `SUPERUSER`: Full access

- **View-Only Mode**: Optional read-only access without input

#### 3. Micro-Segmentation

- **ACL Validation**: Each session creation validates ACL rules
- **Zero Trust Default**: If no ACL rule matches, deny access
- **IP-Based Rules**: ACL can restrict by source IP

#### 4. Encryption

- **Transport Layer**:
  - Frontend ↔ Hub: HTTPS/WSS (TLS 1.3)
  - Hub ↔ Edge: WebSocket over SSH tunnel (optional)
  - VNC Gateway ↔ Tunnel: TCP (localhost only)

- **No VNC Encryption**: VNC protocol itself not encrypted (traffic stays local)

#### 5. Audit Trail

- **Complete Logging**:
  - Session creation (user, node, time, duration)
  - Session termination (reason, duration)
  - ACL decisions (allow/deny with details)
  - All stored in MongoDB with 90-day retention

### Attack Surface Reduction

#### No VNC Ports Exposed

- VNC server (port 5900) only listens on localhost
- No direct Internet access to VNC
- All connections reverse-tunneled from edge

#### Tunnel Port Isolation

- Tunnel ports dynamically allocated (50000-59999)
- Ports bound to localhost only (not 0.0.0.0)
- Ports released after session termination

#### JWT Security

```python
# JWT Payload Example
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "user-uuid",
  "node_id": "node-uuid",
  "tunnel_port": 50123,
  "exp": 1731676500,  # Expiration timestamp
  "iat": 1731676200   # Issued at timestamp
}
```

- Algorithm: HS256
- Expiration: 5 minutes (configurable)
- Secret: 256-bit random key
- Signature verification required

### Threat Model

| Threat | Mitigation |
|--------|-----------|
| **Port Scanning** | No VNC ports exposed to Internet |
| **Brute Force** | JWT token required, 5-min expiration |
| **Man-in-the-Middle** | TLS encryption for all external traffic |
| **Session Hijacking** | JWT tied to session_id, expires quickly |
| **Privilege Escalation** | RBAC + ACL double validation |
| **Data Exfiltration** | Audit logging, session time limits |
| **DoS** | Rate limiting (5 sessions/user, 3/node) |

---

## 📦 Installation

### Prerequisites

- **Hub Server**:
  - Ubuntu 22.04 LTS or newer
  - Python 3.10+
  - PostgreSQL 15
  - Redis 7
  - MongoDB 7
  - Nginx (reverse proxy)

- **Edge Nodes**:
  - Linux with X11/Wayland
  - VNC server (x11vnc, TigerVNC, or similar)
  - Python 3.10+

### Installation Steps

#### 1. Hub Server Installation

```bash
# Navigate to project directory
cd /opt/orizon

# Run deployment script
./deploy_vnc.sh --full

# Or deploy components individually:
./deploy_vnc.sh --backend
./deploy_vnc.sh --gateway
./deploy_vnc.sh --frontend
```

#### 2. Database Migration

```bash
# SSH to server
ssh lorenz@68.183.219.222

# Run migration
sudo -u postgres psql -d orizon -f /tmp/vnc_migration.sql

# Verify table created
sudo -u postgres psql -d orizon -c "\d vnc_sessions"
```

#### 3. VNC Gateway Service

```bash
# Install dependencies
cd /opt/orizon/vnc_gateway
pip3 install -r requirements.txt

# Configure systemd service
sudo systemctl enable orizon-vnc-gateway
sudo systemctl start orizon-vnc-gateway

# Check status
sudo systemctl status orizon-vnc-gateway
```

#### 4. Edge Node Setup

```bash
# Install VNC server
sudo apt update
sudo apt install x11vnc

# Configure VNC server to start on boot
cat > ~/.vnc/xstartup <<EOF
#!/bin/sh
unset SESSION_MANAGER
unset DBUS_SESSION_BUS_ADDRESS
exec startxfce4
EOF

chmod +x ~/.vnc/xstartup

# Start VNC server
x11vnc -display :0 -auth ~/.Xauthority -forever -loop -noxdamage -repeat -rfbauth ~/.vnc/passwd -shared -localhost

# Or use systemd service:
sudo systemctl enable x11vnc
sudo systemctl start x11vnc
```

#### 5. Deploy Edge Agent

```bash
# Copy agent files
scp agents/vnc_tunnel_handler.py edge-node:/opt/orizon/agents/
scp agents/orizon_agent_vnc.py edge-node:/opt/orizon/agents/

# SSH to edge node
ssh edge-node

# Install dependencies
pip3 install websockets psutil

# Run agent
python3 /opt/orizon/agents/orizon_agent_vnc.py \
  --hub-host 46.101.189.126 \
  --hub-port 8000 \
  --node-id your-node-id \
  --token your-auth-token
```

#### 6. Frontend Deployment

```bash
# Build frontend
cd frontend
npm install @novnc/novnc
npm run build

# Deploy to Nginx
sudo cp -r dist/* /var/www/orizon-ztc/

# Reload Nginx
sudo systemctl reload nginx
```

---

## ⚙️ Configuration

### Backend Configuration

**File:** `backend/.env`

```bash
# VNC Settings
VNC_SESSION_MAX_DURATION=3600  # Max 1 hour
VNC_SESSION_DEFAULT_DURATION=300  # Default 5 minutes
VNC_MAX_SESSIONS_PER_USER=5
VNC_MAX_SESSIONS_PER_NODE=3

# Port Allocation
VNC_TUNNEL_PORT_MIN=50000
VNC_TUNNEL_PORT_MAX=59999

# JWT Settings
JWT_SECRET_KEY=your-256-bit-secret-key-change-me
JWT_ALGORITHM=HS256
```

### VNC Gateway Configuration

**File:** `/etc/systemd/system/orizon-vnc-gateway.service`

```ini
[Service]
Environment="JWT_SECRET_KEY=your-256-bit-secret-key-change-me"
Environment="VNC_GATEWAY_HOST=0.0.0.0"
Environment="VNC_GATEWAY_PORT=6080"
Environment="TUNNEL_HOST=localhost"
```

### Frontend Configuration

**File:** `frontend/.env`

```bash
VITE_API_URL=https://46.101.189.126/api/v1
VITE_VNC_GATEWAY_URL=wss://46.101.189.126:6080
```

### Edge Agent Configuration

**Command-line arguments:**

```bash
--hub-host 46.101.189.126      # Hub server hostname/IP
--hub-port 8000                 # Hub WebSocket port
--node-id your-node-id         # Node identifier
--token your-auth-token         # Authentication token
```

### Firewall Configuration

```bash
# Hub Server
sudo ufw allow 6080/tcp         # VNC Gateway
sudo ufw allow 50000:59999/tcp  # Tunnel ports

# Edge Nodes
# No incoming ports needed (Zero Trust!)
```

---

## 📘 Usage

### Creating a VNC Session

#### Via Web UI

1. Navigate to **VNC Remote Desktop** page
2. Click **New Session** button
3. Fill out the form:
   - **Node**: Select target edge node (must be online)
   - **Session Name**: Descriptive name
   - **Description**: Optional notes
   - **Quality**: Low/Medium/High/Lossless
   - **Duration**: 60-3600 seconds
   - **View Only**: Check for read-only access
4. Click **Create Session**
5. VNC viewer opens automatically

#### Via API

```bash
# Create session
curl -X POST https://hub/api/v1/vnc/sessions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "node_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Production Server Desktop",
    "description": "Emergency maintenance",
    "quality": "medium",
    "screen_width": 1920,
    "screen_height": 1080,
    "view_only": false,
    "max_duration_seconds": 300
  }'

# Response
{
  "id": "session-uuid",
  "websocket_url": "wss://hub:6080/vnc/session-uuid?token=jwt...",
  "session_token": "eyJhbGciOiJIUzI1NiIs...",
  "status": "connecting",
  "expires_at": "2025-11-15T10:35:00Z",
  ...
}
```

### Using VNC Viewer

#### Keyboard Shortcuts

- **Ctrl+Alt+Del**: Send Ctrl+Alt+Del to remote desktop
- **F11**: Toggle fullscreen
- **Esc**: Exit fullscreen (when in fullscreen mode)

#### Quality Settings

- **Low**: 8-bit color, high compression (for slow networks)
- **Medium**: 16-bit color, medium compression (default)
- **High**: 24-bit color, low compression (for LAN)
- **Lossless**: 32-bit color, no compression (very fast network)

#### View-Only Mode

When enabled:
- Mouse and keyboard input disabled
- Remote desktop visible but not interactive
- Useful for monitoring or screen sharing

### Managing Sessions

#### List Sessions

```bash
curl https://hub/api/v1/vnc/sessions \
  -H "Authorization: Bearer $TOKEN"
```

#### Get Session Details

```bash
curl https://hub/api/v1/vnc/sessions/{session_id} \
  -H "Authorization: Bearer $TOKEN"
```

#### Terminate Session

```bash
curl -X DELETE https://hub/api/v1/vnc/sessions/{session_id} \
  -H "Authorization: Bearer $TOKEN"
```

#### Get Statistics

```bash
curl https://hub/api/v1/vnc/stats \
  -H "Authorization: Bearer $TOKEN"

# Response
{
  "total_sessions": 150,
  "active_sessions": 3,
  "total_bytes_sent": 1073741824,
  "total_bytes_received": 52428800,
  "avg_latency_ms": 18.5,
  "sessions_by_status": {
    "active": 3,
    "disconnected": 120,
    "expired": 25,
    "error": 2
  }
}
```

---

## 🔧 Troubleshooting

### Common Issues

#### 1. "VNC session creation failed"

**Symptoms:**
- Session creation returns error
- Session status stuck on "pending"

**Possible Causes:**
- Node is offline
- VNC server not running on edge
- Edge agent not connected
- ACL rule denying access

**Solutions:**
```bash
# Check node status
curl https://hub/api/v1/nodes/{node_id} \
  -H "Authorization: Bearer $TOKEN"

# Check edge agent logs
ssh edge-node "journalctl -u orizon-agent -f"

# Check VNC server is running
ssh edge-node "ps aux | grep vnc"

# Test VNC server locally
ssh edge-node "nc -zv localhost 5900"

# Check ACL rules
curl https://hub/api/v1/acl/rules \
  -H "Authorization: Bearer $TOKEN"
```

#### 2. "WebSocket connection failed"

**Symptoms:**
- noVNC shows "Disconnected"
- Browser console shows WebSocket error

**Possible Causes:**
- VNC Gateway not running
- Firewall blocking port 6080
- Invalid JWT token
- Session expired

**Solutions:**
```bash
# Check VNC Gateway status
ssh hub "sudo systemctl status orizon-vnc-gateway"

# Check VNC Gateway logs
ssh hub "sudo journalctl -u orizon-vnc-gateway -f"

# Test WebSocket connectivity
wscat -c wss://hub:6080/vnc/test-session?token=test

# Check firewall
ssh hub "sudo ufw status | grep 6080"
```

#### 3. "Black screen" or "No display"

**Symptoms:**
- VNC connects but shows black screen
- No desktop visible

**Possible Causes:**
- VNC server not attached to X display
- X server not running
- Display number mismatch

**Solutions:**
```bash
# Check X server running
ssh edge-node "ps aux | grep Xorg"

# Check VNC server display
ssh edge-node "ps aux | grep vnc"
# Look for -display :0 or similar

# Restart VNC server
ssh edge-node "x11vnc -display :0 -auth ~/.Xauthority -forever -localhost"

# Check xauth
ssh edge-node "xauth list"
```

#### 4. "Tunnel creation failed"

**Symptoms:**
- Agent logs show tunnel error
- Session stuck in "connecting"

**Possible Causes:**
- Port already in use
- Firewall blocking tunnel ports
- Agent cannot reach hub

**Solutions:**
```bash
# Check tunnel port is available
ssh hub "netstat -tln | grep :50123"

# Check agent can reach hub
ssh edge-node "telnet hub 50123"

# Check agent logs
ssh edge-node "tail -f /var/log/orizon_agent_vnc.log"

# Verify firewall allows tunnel ports
ssh hub "sudo ufw status | grep 50000:59999"
```

### Debugging Tips

#### Enable Debug Logging

**Backend:**
```python
# backend/app/core/config.py
DEBUG = True
LOG_LEVEL = "DEBUG"
```

**VNC Gateway:**
```python
# services/vnc_gateway/vnc_gateway.py
logger.add(sys.stdout, level="DEBUG")
```

**Edge Agent:**
```bash
# Run agent with debug logging
python3 orizon_agent_vnc.py --hub-host hub --debug
```

#### Monitor Network Traffic

```bash
# On hub: Monitor VNC Gateway traffic
sudo tcpdump -i any port 6080 -nn

# On edge: Monitor tunnel traffic
sudo tcpdump -i any port 5900 -nn

# Check WebSocket frames
wscat -c wss://hub:6080/vnc/session-id?token=jwt -x
```

#### Check Database State

```bash
# Check active sessions
sudo -u postgres psql -d orizon -c "
  SELECT id, name, status, tunnel_port, expires_at
  FROM vnc_sessions
  WHERE status IN ('active', 'connecting')
  ORDER BY created_at DESC;
"

# Check expired sessions
sudo -u postgres psql -d orizon -c "
  SELECT id, name, status, expires_at
  FROM vnc_sessions
  WHERE expires_at < NOW() AND status = 'active';
"
```

---

## 🚀 Performance

### Benchmarks

| Metric | Value | Conditions |
|--------|-------|-----------|
| **Session Creation Time** | < 2s | From API call to ready |
| **Connection Latency** | 10-30ms | LAN (< 10ms RTT) |
| **Connection Latency** | 50-150ms | WAN (< 100ms RTT) |
| **Frame Rate (Low Quality)** | 15-30 FPS | 1920x1080, 8-bit color |
| **Frame Rate (Medium Quality)** | 10-20 FPS | 1920x1080, 16-bit color |
| **Frame Rate (High Quality)** | 5-15 FPS | 1920x1080, 24-bit color |
| **Bandwidth (Low Quality)** | 100-500 KB/s | Desktop with light activity |
| **Bandwidth (Medium Quality)** | 500 KB - 2 MB/s | Desktop with light activity |
| **Bandwidth (High Quality)** | 2-5 MB/s | Desktop with heavy activity |
| **Max Concurrent Sessions** | 100+ | Per hub server (4 vCPU, 8GB RAM) |

### Optimization Tips

#### 1. Quality Settings

```javascript
// For slow networks (< 1 Mbps)
quality: "low"  // 8-bit color, high compression

// For normal networks (1-10 Mbps)
quality: "medium"  // 16-bit color, medium compression

// For fast networks (> 10 Mbps)
quality: "high"  // 24-bit color, low compression

// For LAN (> 100 Mbps)
quality: "lossless"  // 32-bit color, no compression
```

#### 2. VNC Server Tuning

```bash
# x11vnc optimization flags
x11vnc \
  -display :0 \
  -auth ~/.Xauthority \
  -forever \
  -localhost \
  -noxdamage \      # Disable damage tracking (reduces CPU)
  -repeat \         # Enable key repeat
  -shared \         # Allow multiple clients
  -ncache 10 \      # Enable client-side caching
  -ncache_cr \      # Copy-rect for cached windows
  -threads          # Use threading for better performance
```

#### 3. Network Tuning

```bash
# Increase TCP buffer sizes
sudo sysctl -w net.core.rmem_max=16777216
sudo sysctl -w net.core.wmem_max=16777216
sudo sysctl -w net.ipv4.tcp_rmem="4096 87380 16777216"
sudo sysctl -w net.ipv4.tcp_wmem="4096 65536 16777216"

# Enable TCP BBR congestion control
sudo sysctl -w net.core.default_qdisc=fq
sudo sysctl -w net.ipv4.tcp_congestion_control=bbr
```

#### 4. Hub Scaling

For high load (> 100 concurrent sessions):

```yaml
# docker-compose.vnc.yml
services:
  vnc-gateway:
    deploy:
      replicas: 3  # Scale to 3 instances
      resources:
        limits:
          cpus: '2'
          memory: 2G

  backend:
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '4'
          memory: 4G
```

### Monitoring

#### Key Metrics to Monitor

1. **VNC Gateway**:
   - Active WebSocket connections
   - Bytes sent/received per session
   - Connection errors
   - CPU/memory usage

2. **Backend**:
   - Active sessions count
   - Session creation rate
   - API response times
   - Database query times

3. **Edge Nodes**:
   - VNC server CPU usage
   - Network bandwidth
   - Tunnel health
   - Connection stability

#### Prometheus Metrics

```bash
# VNC Gateway metrics
vnc_gateway_active_connections
vnc_gateway_bytes_sent_total
vnc_gateway_bytes_received_total
vnc_gateway_connection_errors_total

# Backend metrics
vnc_sessions_active
vnc_sessions_created_total
vnc_sessions_failed_total
vnc_api_request_duration_seconds

# Query Prometheus
curl http://hub:9090/api/v1/query?query=vnc_sessions_active
```

#### Grafana Dashboard

Import dashboard: `monitoring/grafana/dashboards/vnc_dashboard.json`

**Panels:**
- Active Sessions (gauge)
- Session Creation Rate (graph)
- Bandwidth Usage (graph)
- Average Latency (graph)
- Error Rate (graph)
- Top Nodes by Sessions (table)

---

## 📚 Additional Resources

### Related Documentation

- [Orizon Zero Trust Connect - Main README](../README.md)
- [API Reference](../API_Reference.md)
- [Security Guide](../SECURITY_GUIDE.md)
- [Deployment Guide](../DEPLOYMENT_GUIDE.md)

### External Documentation

- [noVNC Documentation](https://github.com/novnc/noVNC)
- [RFB Protocol](https://www.rfc-editor.org/rfc/rfc6143.html)
- [x11vnc Manual](http://www.karlrunge.com/x11vnc/)
- [TigerVNC](https://tigervnc.org/)

### Support

- **GitHub Issues**: https://github.com/orizon/zero-trust-connect/issues
- **Email**: support@orizon.io
- **Documentation**: https://docs.orizon.io

---

**Document Version:** 1.0
**Last Updated:** 2025-11-15
**Author:** Marco Lorenzi @ Syneto/Orizon
