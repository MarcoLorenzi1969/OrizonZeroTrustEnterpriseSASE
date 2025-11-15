

# Orizon Zero Trust Connect - Guacamole Integration Guide

**Version:** 1.0
**Date:** 2025-11-09
**Status:** Production Ready

---

## Overview

This document describes the complete integration of Apache Guacamole as a dedicated SSH/RDP/VNC gateway hub for Orizon Zero Trust Connect. Guacamole provides clientless remote desktop access through a web browser, enabling secure SSH sessions without requiring local SSH clients.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Orizon Main Hub                          │
│                  46.101.189.126                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Backend (FastAPI)                                   │   │
│  │  - Guacamole API Integration                         │   │
│  │  - Node Sync Service                                 │   │
│  │  - Connection Management                             │   │
│  └──────────────────┬───────────────────────────────────┘   │
│                     │ HTTPS API Calls                       │
└─────────────────────┼───────────────────────────────────────┘
                      │
                      ↓
┌─────────────────────────────────────────────────────────────┐
│                 Guacamole Gateway Hub                       │
│                   167.71.33.70                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Apache Guacamole                                    │   │
│  │  - guacd (daemon)                                    │   │
│  │  - Tomcat 9 (web application)                        │   │
│  │  - MySQL (connection database)                       │   │
│  │  - Nginx (reverse proxy)                             │   │
│  └──────────────────┬───────────────────────────────────┘   │
└─────────────────────┼───────────────────────────────────────┘
                      │ SSH/RDP/VNC Protocols
                      ↓
┌─────────────────────────────────────────────────────────────┐
│                    Edge Nodes                               │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │ Kali Linux  │    │   Ubuntu    │    │   Windows   │     │
│  │ SSH:22      │    │   SSH:22    │    │   RDP:3389  │     │
│  └─────────────┘    └─────────────┘    └─────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

---

## Components

### 1. Guacamole Server (167.71.33.70)

**Services:**
- **guacd** - Guacamole proxy daemon (port 4822)
- **Tomcat 9** - Web application server (port 8080)
- **MySQL** - Connection database
- **Nginx** - Reverse proxy (ports 80, 443)

**Key Features:**
- Clientless remote desktop gateway
- Protocol support: SSH, RDP, VNC, Telnet
- Web-based access (no client software required)
- Session recording capabilities
- Multi-user support with permissions
- Clipboard and file transfer support

### 2. Backend Integration

**Location:** `guacamole/integration/`

**Files:**
- `guacamole_service.py` - Guacamole API client and integration service
- `guacamole_endpoints.py` - FastAPI endpoints for Guacamole management

**API Endpoints:**
- `GET /api/v1/guacamole/status` - Check Guacamole server status
- `GET /api/v1/guacamole/connections` - List all connections
- `POST /api/v1/guacamole/connections/ssh` - Create SSH connection
- `POST /api/v1/guacamole/connections/rdp` - Create RDP connection
- `GET /api/v1/guacamole/nodes/{node_id}/access-url` - Get access URL for node
- `POST /api/v1/guacamole/sync-all-nodes` - Sync all Orizon nodes to Guacamole
- `DELETE /api/v1/guacamole/connections/{id}` - Delete connection
- `GET /api/v1/guacamole/active-sessions` - Get active sessions

### 3. Frontend Components

**Location:** `guacamole/integration/`

**Components:**
- `GuacamolePage.jsx` - Guacamole management dashboard
- `GuacamoleButton.jsx` - SSH access button for nodes

**Features:**
- View Guacamole server status
- List configured connections
- Sync nodes to Guacamole
- One-click SSH access to nodes
- Active session monitoring

---

## Installation

### Prerequisites

- Ubuntu 22.04 LTS (on 167.71.33.70)
- Root or sudo access
- At least 2GB RAM, 20GB disk
- Internet connectivity

### Step 1: Prepare Deployment Files

On your local machine:

```bash
cd /Users/marcolorenzi/Windsurf/MCP-Server-LocalModelCyber/OrizonZeroTrustConnect/guacamole/deployment

# Make scripts executable
chmod +x install_guacamole.sh
chmod +x deploy_guacamole.sh
chmod +x register_guacamole_hub.py
```

### Step 2: Deploy Guacamole (Automated)

```bash
# Complete automated deployment
./deploy_guacamole.sh
```

This script will:
1. Upload installation script to Guacamole server
2. Install all dependencies (Tomcat, MySQL, Guacamole, Nginx)
3. Configure services
4. Generate SSL certificates
5. Register hub in Orizon database
6. Configure firewall
7. Verify deployment

**Duration:** 15-20 minutes

### Step 3: Verify Installation

```bash
# Check services on Guacamole server
ssh orizonzerotrust@167.71.33.70

sudo systemctl status guacd
sudo systemctl status tomcat9
sudo systemctl status nginx

# Test web interface
curl -k https://167.71.33.70/guacamole/
```

---

## Configuration

### Guacamole Server Configuration

**File:** `/etc/guacamole/guacamole.properties`

```properties
# MySQL Database
mysql-hostname: localhost
mysql-port: 3306
mysql-database: guacamole_db
mysql-username: guacamole_user
mysql-password: <generated>

# Guacamole Daemon
guacd-hostname: localhost
guacd-port: 4822

# Orizon Integration
orizon-hub-url: https://46.101.189.126/api/v1
orizon-hub-enabled: true

# Features
enable-clipboard-integration: true
enable-sftp: true
```

### Nginx Configuration

**File:** `/etc/nginx/sites-available/guacamole`

```nginx
server {
    listen 443 ssl http2;
    server_name 167.71.33.70;

    ssl_certificate /etc/nginx/ssl/guacamole-selfsigned.crt;
    ssl_certificate_key /etc/nginx/ssl/guacamole-selfsigned.key;

    # Guacamole proxy
    location /guacamole/ {
        proxy_pass http://localhost:8080/guacamole/;
        proxy_buffering off;
        proxy_http_version 1.1;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $http_connection;
        proxy_cookie_path /guacamole/ /;
    }

    # WebSocket support
    location /guacamole/websocket-tunnel {
        proxy_pass http://localhost:8080/guacamole/websocket-tunnel;
        proxy_buffering off;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### Database Schema

Guacamole automatically creates these tables:

- `guacamole_connection` - Connection definitions
- `guacamole_user` - User accounts
- `guacamole_connection_permission` - User permissions
- `guacamole_connection_parameter` - Connection parameters
- `guacamole_system_permission` - System permissions

**Orizon Database Extension:**

```sql
-- Add to nodes table
ALTER TABLE nodes
ADD COLUMN guacamole_connection_id VARCHAR(255),
ADD COLUMN guacamole_rdp_connection_id VARCHAR(255);
```

---

## Backend Integration

### Step 1: Add Integration Files

Copy files to backend:

```bash
# From project root
cp guacamole/integration/guacamole_service.py backend/app/services/
cp guacamole/integration/guacamole_endpoints.py backend/app/api/v1/endpoints/
```

### Step 2: Update Main App

Edit `backend/app/main_minimal.py`:

```python
# Add import
from app.api.v1.endpoints import guacamole_endpoints

# Include router
app.include_router(
    guacamole_endpoints.router,
    prefix="/api/v1",
    tags=["guacamole"]
)
```

### Step 3: Add Dependencies

Update `backend/requirements.txt`:

```
aiohttp>=3.9.0  # For Guacamole API client
```

### Step 4: Configure Environment

Update `backend/.env`:

```bash
# Guacamole Integration
GUACAMOLE_URL=https://167.71.33.70
GUACAMOLE_USERNAME=guacadmin
GUACAMOLE_PASSWORD=<change-this>  # Change from default!
```

### Step 5: Restart Backend

```bash
# On Orizon hub (46.101.189.126)
ssh orizonai@46.101.189.126

cd /root/orizon-ztc/backend
source venv/bin/activate
pip install -r requirements.txt

sudo systemctl restart orizon-backend
```

---

## Frontend Integration

### Step 1: Add Components

Copy files to frontend:

```bash
# From project root
cp guacamole/integration/GuacamolePage.jsx frontend/src/pages/
cp guacamole/integration/GuacamoleButton.jsx frontend/src/components/nodes/
```

### Step 2: Update Router

Edit `frontend/src/App.jsx`:

```jsx
import GuacamolePage from './pages/GuacamolePage'

// Add route
<Route path="/guacamole" element={<GuacamolePage />} />
```

### Step 3: Add Navigation Menu

Edit `frontend/src/components/layout/DashboardLayout.jsx`:

```jsx
// Add menu item
{
  name: 'Guacamole Gateway',
  path: '/guacamole',
  icon: FiMonitor
}
```

### Step 4: Update NodeCard

Edit `frontend/src/components/nodes/NodeCard.jsx`:

```jsx
import GuacamoleButton from './GuacamoleButton'

// Add button in actions section
<GuacamoleButton node={node} />
```

### Step 5: Rebuild Frontend

```bash
cd frontend
npm install
npm run build

# Deploy to Orizon hub
scp -r dist/* orizonai@46.101.189.126:/var/www/orizon-ztc/dist/
```

---

## Usage

### 1. Access Guacamole Admin Interface

1. Open browser: https://167.71.33.70/guacamole/
2. Login:
   - Username: `guacadmin`
   - Password: `guacadmin` (⚠️ CHANGE IMMEDIATELY!)

3. Change default password:
   - Settings → Users → guacadmin → Change Password

### 2. Sync Nodes from Orizon

**Option A - Via Orizon Dashboard:**

1. Login to Orizon: https://46.101.189.126
2. Navigate to: Guacamole Gateway page
3. Click: "Sync All Nodes"
4. Wait for confirmation

**Option B - Via API:**

```bash
curl -X POST https://46.101.189.126/api/v1/guacamole/sync-all-nodes \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Option C - Manually via Guacamole:**

1. Login to Guacamole
2. Settings → Connections → New Connection
3. Configure:
   - Name: `Orizon - Node Name`
   - Protocol: SSH
   - Hostname: `10.211.55.19`
   - Port: `22`
   - Username: `parallels`
   - Password: `profano.69`
4. Save

### 3. Access Node via SSH

**From Orizon Dashboard:**

1. Go to Nodes page
2. Find target node
3. Click "SSH Access" button
4. New window opens with terminal

**Direct Access:**

1. Login to Guacamole
2. Click on connection
3. Terminal opens in browser

---

## API Usage Examples

### Check Guacamole Status

```bash
curl -X GET https://46.101.189.126/api/v1/guacamole/status \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Response:
{
  "status": "online",
  "url": "https://167.71.33.70",
  "authenticated": true,
  "message": "Guacamole hub is operational"
}
```

### Create SSH Connection

```bash
curl -X POST https://46.101.189.126/api/v1/guacamole/connections/ssh \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "node_id": "fcf9ff58-8aee-4d69-8471-73f503ed8672",
    "name": "Kali Pentest",
    "username": "parallels",
    "password": "profano.69"
  }'

# Response:
{
  "id": "1",
  "name": "Kali Pentest",
  "protocol": "ssh",
  "hostname": "10.211.55.19",
  "port": 22,
  "node_id": "fcf9ff58-8aee-4d69-8471-73f503ed8672"
}
```

### Get Access URL for Node

```bash
curl -X GET https://46.101.189.126/api/v1/guacamole/nodes/fcf9ff58-8aee-4d69-8471-73f503ed8672/access-url \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Response:
{
  "url": "https://167.71.33.70/guacamole/#/client/1",
  "connection_id": "1",
  "protocol": "ssh"
}
```

### List Connections

```bash
curl -X GET https://46.101.189.126/api/v1/guacamole/connections \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Response:
[
  {
    "id": "1",
    "name": "Orizon - Kali Pentest",
    "protocol": "ssh",
    "hostname": "10.211.55.19",
    "port": 22
  },
  {
    "id": "2",
    "name": "Orizon - UbuntuSRV-Edge",
    "protocol": "ssh",
    "hostname": "10.211.55.20",
    "port": 22
  }
]
```

---

## Security

### SSL/TLS

**Current:** Self-signed certificate
**Production:** Use Let's Encrypt

```bash
# Install Let's Encrypt certificate
ssh orizonzerotrust@167.71.33.70

sudo certbot --nginx -d 167.71.33.70
sudo systemctl reload nginx
```

### Firewall

```bash
# Allow only necessary ports
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw deny 8080/tcp  # Block direct Tomcat access
sudo ufw deny 4822/tcp  # Block direct guacd access
sudo ufw enable
```

### Password Security

**Default Credentials (⚠️ CHANGE!):**
- Guacamole Admin: `guacadmin / guacadmin`
- MySQL Root: Saved in `/root/guacamole_credentials.txt`

**Best Practices:**
1. Change default Guacamole password immediately
2. Store SSH credentials encrypted in database
3. Use SSH keys instead of passwords where possible
4. Enable 2FA for Guacamole users
5. Rotate credentials regularly

### Access Control

**Guacamole Permissions:**
- Admin users: Full system access
- Regular users: Only assigned connections
- Read-only users: View-only access

**Integration with Orizon:**
- All API calls require JWT authentication
- Role-based access control (RBAC)
- Audit logging for all operations

---

## Troubleshooting

### Guacamole Service Not Starting

```bash
# Check guacd status
sudo systemctl status guacd

# Check logs
sudo journalctl -u guacd -n 50

# Restart service
sudo systemctl restart guacd
```

### Tomcat Errors

```bash
# Check Tomcat logs
sudo tail -f /var/log/tomcat9/catalina.out

# Restart Tomcat
sudo systemctl restart tomcat9

# Check web app deployment
ls -la /var/lib/tomcat9/webapps/guacamole/
```

### Database Connection Errors

```bash
# Test MySQL connection
sudo mysql -u guacamole_user -p guacamole_db

# Check database tables
sudo mysql -u root -p
> USE guacamole_db;
> SHOW TABLES;
```

### Nginx Configuration Issues

```bash
# Test nginx config
sudo nginx -t

# Check error logs
sudo tail -f /var/log/nginx/error.log

# Reload nginx
sudo systemctl reload nginx
```

### Cannot Access via Browser

1. **Check firewall:**
   ```bash
   sudo ufw status
   # Should show 80, 443 allowed
   ```

2. **Verify services:**
   ```bash
   sudo systemctl status guacd tomcat9 nginx
   ```

3. **Test locally:**
   ```bash
   curl -k https://localhost/guacamole/
   ```

4. **Check SSL certificate:**
   ```bash
   openssl s_client -connect 167.71.33.70:443
   ```

### Connection Fails in Guacamole

1. **Verify target reachable:**
   ```bash
   ssh parallels@10.211.55.19
   # Should connect successfully
   ```

2. **Check guacd logs:**
   ```bash
   sudo journalctl -u guacd -f
   # Look for connection attempts
   ```

3. **Verify credentials:**
   - Check username/password in connection settings
   - Test SSH manually first

### Integration Not Working

1. **Check backend logs:**
   ```bash
   ssh orizonai@46.101.189.126
   sudo journalctl -u orizon-backend -f | grep guacamole
   ```

2. **Verify API endpoint:**
   ```bash
   curl -k https://46.101.189.126/api/v1/guacamole/status \
     -H "Authorization: Bearer TOKEN"
   ```

3. **Check network connectivity:**
   ```bash
   # From Orizon hub
   curl -k https://167.71.33.70/guacamole/
   ```

---

## Performance Tuning

### Tomcat

Edit `/etc/tomcat9/server.xml`:

```xml
<Connector port="8080" protocol="HTTP/1.1"
           connectionTimeout="20000"
           maxThreads="200"
           minSpareThreads="10"
           enableLookups="false"
           acceptCount="100" />
```

### MySQL

Edit `/etc/mysql/my.cnf`:

```ini
[mysqld]
max_connections = 200
innodb_buffer_pool_size = 512M
query_cache_size = 64M
```

### guacd

Edit `/etc/guacamole/guacd.conf`:

```ini
[daemon]
pid_file = /var/run/guacd.pid
log_level = info  # Change to 'warning' in production

[server]
bind_host = 0.0.0.0
bind_port = 4822
```

---

## Monitoring

### Health Checks

```bash
# Guacamole web interface
curl -k https://167.71.33.70/guacamole/

# guacd daemon
sudo systemctl is-active guacd

# Tomcat
curl http://localhost:8080/guacamole/

# MySQL
sudo mysql -u guacamole_user -p -e "SELECT COUNT(*) FROM guacamole_connection;"
```

### Log Locations

- **guacd:** `journalctl -u guacd`
- **Tomcat:** `/var/log/tomcat9/catalina.out`
- **Nginx:** `/var/log/nginx/access.log`, `/var/log/nginx/error.log`
- **MySQL:** `/var/log/mysql/error.log`

### Metrics

Monitor these metrics:
- Active sessions count
- Connection success rate
- Average session duration
- Resource usage (CPU, RAM, disk)
- Network bandwidth

---

## Backup and Recovery

### Backup

```bash
#!/bin/bash
# Backup Guacamole configuration and database

BACKUP_DIR="/root/guacamole_backup_$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

# Backup MySQL database
sudo mysqldump -u root -p guacamole_db > $BACKUP_DIR/guacamole_db.sql

# Backup configuration
sudo cp -r /etc/guacamole $BACKUP_DIR/
sudo cp /etc/nginx/sites-available/guacamole $BACKUP_DIR/

# Create archive
tar -czf $BACKUP_DIR.tar.gz $BACKUP_DIR
rm -rf $BACKUP_DIR

echo "Backup saved to: $BACKUP_DIR.tar.gz"
```

### Recovery

```bash
# Restore database
sudo mysql -u root -p guacamole_db < guacamole_db.sql

# Restore configuration
sudo cp -r guacamole /etc/
sudo cp guacamole_nginx.conf /etc/nginx/sites-available/guacamole

# Restart services
sudo systemctl restart guacd tomcat9 nginx
```

---

## Advanced Features

### Session Recording

Enable session recording in Guacamole:

1. Admin → Connections → Edit Connection
2. Screen Recording section:
   - Recording Path: `/var/lib/guacamole/recordings`
   - Create Recording Path: Yes
   - Automatically Create Recording: Yes
3. Save

### File Transfer

SFTP is already enabled in SSH connections.

**Usage:**
1. Connect to SSH session
2. Press Ctrl+Alt+Shift (shows menu)
3. Click "Devices" → "File Transfer"
4. Drag and drop files

### Multi-Factor Authentication

Install TOTP extension:

```bash
wget https://downloads.apache.org/guacamole/1.5.5/binary/guacamole-auth-totp-1.5.5.jar
sudo mv guacamole-auth-totp-1.5.5.jar /etc/guacamole/extensions/
sudo systemctl restart tomcat9
```

---

## References

- **Guacamole Documentation:** https://guacamole.apache.org/doc/gug/
- **API Documentation:** https://guacamole.apache.org/api-documentation/
- **GitHub Repository:** https://github.com/apache/guacamole-server
- **Orizon ZTC Documentation:** `/Users/marcolorenzi/Windsurf/MCP-Server-LocalModelCyber/OrizonZeroTrustConnect/README.md`

---

## Changelog

### Version 1.0 - 2025-11-09
- ✅ Initial Guacamole integration
- ✅ Complete installation automation
- ✅ Backend API integration
- ✅ Frontend components
- ✅ Node synchronization
- ✅ SSH access via web
- ✅ Documentation complete

---

**Document Created:** 2025-11-09
**Last Updated:** 2025-11-09
**Author:** Orizon Development Team
**Status:** Production Ready
