# Orizon Zero Trust Connect v2.0

**Enterprise-Grade Zero Trust Network Access with Web-Based Terminal**

[![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)](./VERSION)
[![License](https://img.shields.io/badge/license-Proprietary-red.svg)]()
[![Python](https://img.shields.io/badge/python-3.9+-green.svg)]()

---

## 🎉 What's New in v2.0

**Major Release**: Complete web-based terminal integration with visual debugging

- ✅ **Interactive Web Terminal** - Full SSH access through your browser
- ✅ **Visual Debug Panel** - Real-time monitoring without F12 console
- ✅ **Critical Bug Fixes** - WebSocket connectivity, token management, firewall configuration
- ✅ **Dashboard Integration** - One-click terminal access from tunnel list
- ✅ **Enhanced Security** - JWT standard tokens with proper expiration handling

**[See Full Changelog](./CHANGELOG-v2.md)** for detailed changes and fixes.

---

## 📋 Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Multi-Tenant System](#multi-tenant)
- [Quick Start](#quick-start)
- [Components](#components)
- [Configuration](#configuration)
- [Usage](#usage)
- [Troubleshooting](#troubleshooting)
- [Security](#security)
- [Development](#development)
- [License](#license)

## 📖 Documentation

- **[Multi-Tenant System Guide](./docs/MULTI_TENANT_SYSTEM.md)** - Complete guide to tenant management, group associations, and hierarchical access control
- **[API Reference](./docs/API_REFERENCE.md)** - Full REST API documentation
- **[Architecture Guide](./docs/ARCHITECTURE.md)** - System architecture and design patterns
- **[Deployment Guide](./docs/DEPLOYMENT_GUIDE.md)** - Production deployment instructions

---

## ✨ Features

### Core Capabilities
- **Zero Trust Architecture** - Certificate-based authentication for all connections
- **Multi-Tenant System** - Complete organization isolation with hierarchical access control
- **SSH Reverse Tunnels** - Secure connectivity without exposing edge nodes
- **Web-Based Terminal** - Interactive shell access via browser (xterm.js v5.3.0)
- **Real-Time Monitoring** - Visual debug panel with categorized event logging
- **Group-Based Access Control** - Fine-grained permissions per user group with tenant associations
- **Remote Desktop Access** - Apache Guacamole integration for RDP/VNC
- **Multi-Protocol Support** - SSH, HTTP, RDP, VNC tunneling

### Web Terminal Features
- **Full Terminal Emulation** - Complete xterm.js integration with 256 colors
- **Automatic Sizing** - Responsive terminal that adapts to window size
- **Copy/Paste Support** - Clipboard integration (browser-dependent)
- **Session Persistence** - Maintains connection during page refresh
- **Debug Panel** - Integrated monitoring without developer tools:
  - Real-time event timeline with millisecond timestamps
  - Categorized statistics (INFO, SUCCESS, ERROR, WARNING, DEBUG, WEBSOCKET)
  - Tabbed filtering (ALL, ERRORS, WARNINGS, WEBSOCKET, PARAMS)
  - Export debug data as JSON
  - URL parameters validation

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Browser                             │
│  ┌──────────────────┐         ┌─────────────────────────────┐  │
│  │   Dashboard      │         │   Web Terminal              │  │
│  │  (dashboard.html)│◄────────┤  (terminal.html)            │  │
│  └────────┬─────────┘         │  + Visual Debug Panel       │  │
│           │                   └──────────┬──────────────────┘  │
│           │                              │                      │
└───────────┼──────────────────────────────┼──────────────────────┘
            │                              │
            │ HTTP                         │ WebSocket (ws://)
            │ (Port 80/443)                │ (Port 8765)
            │                              │
┌───────────▼──────────────────────────────▼──────────────────────┐
│                        Hub Server                               │
│  ┌──────────────────┐         ┌─────────────────────────────┐  │
│  │  Backend API     │         │  WebSocket Terminal Server  │  │
│  │  (FastAPI)       │         │  (Python asyncio)           │  │
│  │  Port 80/443     │         │  Port 8765                  │  │
│  └──────────────────┘         └──────────┬──────────────────┘  │
│                                           │                      │
│  ┌───────────────────────────────────────▼──────────────────┐  │
│  │         SSH Reverse Tunnel (Localhost)                    │  │
│  │         Port 10001, 10002, ... (one per edge)             │  │
│  └───────────────────────────────────────┬──────────────────┘  │
└────────────────────────────────────────────┼────────────────────┘
                                             │ SSH Reverse Tunnel
                                             │ (Established by Edge)
                                             │
┌────────────────────────────────────────────▼────────────────────┐
│                        Edge Node(s)                             │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Orizon Agent                                            │  │
│  │  - Establishes reverse SSH tunnel to hub                 │  │
│  │  - Certificate-based authentication                      │  │
│  │  - Auto-reconnect on failure                             │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Local Services (SSH, HTTP, RDP, VNC, etc.)             │  │
│  │  Port 22, 80, 3389, 5900, ...                            │  │
│  └──────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

### Data Flow: Terminal Session

1. **User clicks "Terminal" icon** in dashboard
2. **Dashboard generates URL** with tunnel_id, remote_port, and long-lived JWT token
3. **Browser opens terminal.html** with URL parameters
4. **Terminal page validates parameters** and displays them in debug panel
5. **WebSocket connection** established to `ws://hub:8765/?tunnel_id=xxx&token=xxx`
6. **WebSocket server**:
   - Parses URL parameters using `urllib.parse`
   - Validates JWT token (HS256)
   - Looks up tunnel in database
   - Tests connectivity to tunnel port
   - Establishes SSH connection through reverse tunnel
   - Opens interactive shell channel (PTY)
7. **Bidirectional I/O loop** begins:
   - User input → WebSocket → SSH → Edge shell
   - Edge output → SSH → WebSocket → Browser terminal
8. **Session logs** tracked for duration, bytes, commands, errors

---

## 🏢 Multi-Tenant System {#multi-tenant}

Orizon v2.0 includes a complete multi-tenant architecture for managing multiple isolated organizations:

### Hierarchy

```
Users → Groups → Tenants → Edge Nodes
```

### Key Features

- **Tenant Isolation**: Each organization (tenant) has completely isolated resources and configurations
- **Flexible Group Associations**: User groups can be associated with multiple tenants with granular permissions
- **Shared Infrastructure**: Edge nodes can be shared across multiple tenants with custom configurations
- **Hierarchical Access Control**:
  - `SUPERUSER`: Full system access, sees all tenants
  - `SUPER_ADMIN`: Manages own tenants and subordinate users
  - `ADMIN`: Manages groups and tenant associations
  - `USER`: Read-only access to assigned tenants

### Quick Example

```bash
# Create a new tenant
curl -X POST http://hub/api/v1/tenants \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "name": "acme-corp",
    "display_name": "Acme Corporation",
    "quota": {"max_nodes": 10, "max_users": 50}
  }'

# Associate group with tenant
curl -X POST http://hub/api/v1/tenants/{tenant_id}/groups \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "group_id": "...",
    "permissions": {"can_manage_nodes": true}
  }'

# Assign edge nodes to tenant
curl -X POST http://hub/api/v1/tenants/{tenant_id}/nodes \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "node_id": "...",
    "node_config": {"priority": 1, "max_tunnels": 100}
  }'
```

**[Complete Multi-Tenant Documentation →](./docs/MULTI_TENANT_SYSTEM.md)**

---

## 🚀 Quick Start

### Prerequisites

- **Hub Server**: Ubuntu 20.04+ with public IP
- **Edge Node**: Any Linux distribution with SSH
- **Python**: 3.9+ on both hub and edge
- **Database**: PostgreSQL 13+
- **Web Server**: Nginx or Apache

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-org/orizon-zero-trust.git
   cd orizon-zero-trust
   ```

2. **Deploy to hub server**:
   ```bash
   # See DEPLOYMENT-v2.md for detailed instructions
   ./deploy_hub.sh
   ```

3. **Install agent on edge node**:
   ```bash
   curl -sSL http://your-hub-ip/downloads/install.sh | sudo bash
   ```

4. **Access dashboard**:
   ```
   http://your-hub-ip/dashboard.html
   ```

5. **Launch terminal**:
   - Click terminal icon (💻) next to any active tunnel
   - Terminal opens in new window with visual debug panel

---

## 📦 Components

### Hub Components

#### 1. WebSocket Terminal Server
**File**: `/opt/orizon/websocket_terminal_server.py` (v2.1)

**Features**:
- Proper URL parameter parsing with `urllib.parse`
- 6-phase connection logging
- JWT token validation
- Session statistics tracking
- WebSocket close code explanations

**Service**: `orizon-terminal.service`
**Port**: 8765 (TCP)
**Protocol**: WebSocket (WS)

#### 2. Web Terminal Interface
**File**: `/var/www/orizon-ztc/terminal.html` (22KB)

**Features**:
- xterm.js v5.3.0 terminal emulator
- FitAddon for automatic sizing
- Integrated visual debug panel (450px width)
- Real-time event logging with filtering
- URL parameter validation
- Export debug data as JSON

#### 3. Dashboard
**File**: `/var/www/orizon-ztc/dashboard.html`

**Features**:
- Tunnel management interface
- One-click terminal launch
- Long-lived JWT token generation (1-year expiration)
- Tunnel status monitoring

#### 4. Backend API
**File**: `/opt/orizon/backend/simple_main.py`

**Features**:
- FastAPI-based REST API
- User authentication
- Node and tunnel management
- Certificate management
- Group-based access control

### Edge Components

#### Orizon Agent
**File**: `/opt/orizon/orizon_agent.py`

**Features**:
- Establishes SSH reverse tunnel to hub
- Certificate-based authentication
- Auto-reconnect with exponential backoff
- Health monitoring
- Tunnel keep-alive

---

## ⚙️ Configuration

### Environment Variables

```bash
# Hub Server
export ORIZON_DB_HOST=localhost
export ORIZON_DB_NAME=orizon
export ORIZON_DB_USER=orizon
export ORIZON_DB_PASSWORD=your-password
export ORIZON_JWT_SECRET=your-secret-key-change-in-production
export ORIZON_WS_PORT=8765

# Edge Agent
export ORIZON_HUB_HOST=your-hub-ip
export ORIZON_HUB_PORT=22
export ORIZON_AGENT_ID=auto
export ORIZON_RECONNECT_INTERVAL=30
```

### Firewall Rules

**Hub Server**:
```bash
sudo ufw allow 22/tcp          # SSH
sudo ufw allow 80/tcp          # HTTP
sudo ufw allow 443/tcp         # HTTPS
sudo ufw allow 8765/tcp        # WebSocket Terminal Server
```

**Edge Node**:
```bash
# No inbound ports required (reverse tunnel)
# Only outbound SSH (port 22) to hub
```

---

## 📖 Usage

### Opening a Terminal Session

**From Dashboard**:
1. Navigate to `http://your-hub-ip/dashboard.html`
2. Find the tunnel you want to access
3. Click the terminal icon (💻) next to the tunnel
4. Terminal opens in new window with debug panel

**Direct URL** (for testing):
```
http://your-hub-ip/terminal.html?tunnel_id=UUID&tunnel_name=NAME&remote_port=PORT&token=JWT_TOKEN
```

### Using the Debug Panel

**Stats Badges** (top of panel):
- `📘 INFO`: Informational messages
- `✅ SUCCESS`: Successful operations
- `❌ ERROR`: Error messages
- `⚠️ WARNING`: Warning messages
- `🔍 DEBUG`: Debug details
- `🌐 WS Events`: WebSocket lifecycle events

**Tabs**:
- **ALL**: Complete event timeline (most recent first)
- **ERRORS**: Error messages only
- **WARNINGS**: Warning messages only
- **WEBSOCKET**: WebSocket events (CREATED, OPEN, CLOSE, ERROR, MESSAGE)
- **PARAMS**: URL parameters with validation (✅ OK or ❌ NULL)

**Export Debug Data**:
1. Click "📋 Copy All" button
2. Paste into text editor or provide to support
3. Contains: params, stats, complete event timeline with timestamps

### Expected Event Sequence (Success)

```
[INFO] Script loaded and executing
[INFO] 1️⃣ Parsing URL parameters
[INFO] URL parameters parsed (all OK)
[INFO] 4️⃣ Window load event fired
[INFO] 2️⃣ Initializing terminal
[SUCCESS] Terminal initialized successfully
[INFO] 3️⃣ Connecting to WebSocket
[WEBSOCKET] CREATED (readyState: 0)
[SUCCESS] ✅ WebSocket connection established
[WEBSOCKET] OPEN (readyState: 1)
[SUCCESS] Terminal session established
[WEBSOCKET] MESSAGE (welcome banner received)
```

---

## 🔧 Troubleshooting

### Terminal Won't Connect

**Symptom**: WebSocket closes with code 1006
**Debug Panel Shows**: `❌ ERROR - WebSocket error occurred`

**Possible Causes**:
1. **Firewall blocking port 8765**
   ```bash
   # On hub server
   sudo ufw status | grep 8765
   # Should show: 8765/tcp ALLOW Anywhere
   ```

2. **WebSocket server not running**
   ```bash
   sudo systemctl status orizon-terminal.service
   # Should show: Active (running)
   ```

3. **Tunnel not active**
   - Check tunnel status in dashboard
   - Verify edge agent is running
   - Check hub server: `ss -tln | grep <remote_port>`

### Token Expired Error

**Symptom**: WebSocket closes with code 1008, "Invalid token"
**Debug Panel Shows**: `❌ ERROR - Server error: Invalid or expired token`

**Solutions**:
1. **Re-login to dashboard** (refreshes token)
2. **Use direct URL** with fresh token (see DEPLOYMENT-v2.md)
3. **Check token expiration**:
   ```bash
   # Decode JWT token (paste your token)
   echo "YOUR_TOKEN" | cut -d'.' -f2 | base64 -d | python3 -m json.tool
   ```

### Missing Parameters

**Symptom**: Debug panel shows `remotePort: NULL ❌`

**Solutions**:
1. **Check URL syntax** - Must have `&remote_port=PORT` (snake_case)
2. **Verify URL not truncated** - No spaces in URL
3. **Use "Copy All"** to verify what browser received

### Visual Debug Panel Not Showing

**Solutions**:
1. **Hard refresh**: Ctrl+Shift+R (Windows/Linux) or Cmd+Shift+R (Mac)
2. **Clear cache** and reload
3. **Check browser console** (F12) for JavaScript errors
4. **Verify file deployed**: `curl -s http://your-hub-ip/terminal.html | grep "debug-panel"`

---

## 🔐 Security

### Current Security Posture (v2.0)

#### ✅ Implemented
- JWT token authentication (HS256)
- Certificate-based SSH authentication for edge nodes
- Token expiration validation
- Session tracking and auditing
- No direct inbound ports on edge nodes (reverse tunnel architecture)

#### ⚠️ Recommendations for Production

1. **Upgrade to WSS** (WebSocket Secure):
   ```nginx
   # Nginx config
   location /ws/ {
       proxy_pass http://localhost:8765;
       proxy_http_version 1.1;
       proxy_set_header Upgrade $http_upgrade;
       proxy_set_header Connection "upgrade";
       proxy_set_header X-Real-IP $remote_addr;
   }
   ```

2. **Change Default Secrets**:
   ```python
   # /opt/orizon/websocket_terminal_server.py
   JWT_SECRET = "your-production-secret-key-minimum-32-characters"

   # /opt/orizon/backend/simple_main.py
   SECRET_KEY = "your-backend-secret-key-different-from-jwt"
   ```

3. **Implement Rate Limiting**:
   ```python
   # Add to WebSocket server
   from collections import defaultdict
   from time import time

   connection_attempts = defaultdict(list)
   MAX_ATTEMPTS_PER_MINUTE = 10
   ```

4. **Add Token Refresh Endpoint**:
   - Implement `/api/v1/auth/terminal-token` in backend
   - Dashboard calls endpoint for fresh token before opening terminal
   - Remove hardcoded 1-year token

5. **Enable HTTPS**:
   ```bash
   sudo certbot --nginx -d your-hub-domain.com
   ```

### Security Audit Checklist

- [ ] Change all default secrets and passwords
- [ ] Enable HTTPS/WSS
- [ ] Implement rate limiting
- [ ] Add token refresh mechanism
- [ ] Review firewall rules
- [ ] Enable audit logging
- [ ] Rotate SSH certificates regularly
- [ ] Implement 2FA for dashboard login
- [ ] Set up intrusion detection (fail2ban)
- [ ] Regular security updates

---

## 💻 Development

### Running Locally

```bash
# Start WebSocket server
cd /opt/orizon
python3 websocket_terminal_server.py

# Serve frontend (development)
cd /var/www/orizon-ztc
python3 -m http.server 8000

# Access terminal
http://localhost:8000/terminal.html?tunnel_id=xxx&...
```

### Testing

```bash
# Test WebSocket connection
python3 test_websocket_with_params.py

# Test URL parameter parsing
curl "http://localhost:8765/?tunnel_id=test&token=test"

# Check firewall
sudo ufw status numbered

# Verify service
sudo systemctl status orizon-terminal.service
sudo journalctl -u orizon-terminal.service -n 50
```

### Debug Mode

Enable verbose logging in WebSocket server:
```python
# Set at top of websocket_terminal_server.py
DEBUG = True
LOG_LEVEL = 'DEBUG'
```

---

## 📄 License

Proprietary - All Rights Reserved

Copyright (c) 2025 Orizon Zero Trust Connect

---

## 🤝 Support

- **Documentation**: See `docs/` directory
- **Issues**: Report bugs via GitHub Issues
- **Email**: support@orizon.io

---

## 📚 Additional Documentation

- **[CHANGELOG](./CHANGELOG-v2.md)** - Detailed release notes
- **[DEPLOYMENT](./DEPLOYMENT-v2.md)** - Deployment procedures
- **[TERMINAL_FIX_SUMMARY](./TERMINAL_FIX_SUMMARY.md)** - Technical deep-dive on v2.0 fixes

---

**Built with** ❤️ **by the Orizon Team**

_Last updated: 2025-11-15_
