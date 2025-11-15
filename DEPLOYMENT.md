# Deployment Guide - Orizon Zero Trust Connect v2.0

**Complete deployment procedures for production and testing environments**

---

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Hub Server Deployment](#hub-server-deployment)
- [Edge Agent Deployment](#edge-agent-deployment)
- [Verification](#verification)
- [Post-Deployment Configuration](#post-deployment-configuration)
- [Troubleshooting](#troubleshooting)
- [Rollback Procedures](#rollback-procedures)

---

## Overview

This guide covers the deployment of Orizon Zero Trust Connect v2.0, including:
- Hub server components (Backend API, WebSocket Terminal Server, Frontend)
- Edge agent installation and configuration
- Security configuration and verification

**Deployment Architecture:**
```
┌─────────────────────────────────────────────────────────┐
│  Hub Server (68.183.219.222)                           │
│  ├── Backend API (Port 80/443)                         │
│  ├── WebSocket Terminal Server (Port 8765)             │
│  ├── PostgreSQL Database (Port 5432)                   │
│  └── Nginx Web Server                                  │
└─────────────────────────────────────────────────────────┘
                           ▲
                           │ SSH Reverse Tunnel
                           │
┌─────────────────────────────────────────────────────────┐
│  Edge Node (10.211.55.21)                              │
│  ├── Orizon Agent (Python)                            │
│  └── Local Services (SSH, HTTP, etc.)                 │
└─────────────────────────────────────────────────────────┘
```

---

## Prerequisites

### Hub Server Requirements

- **Operating System**: Ubuntu 20.04 LTS or later
- **CPU**: 2+ cores
- **RAM**: 4GB minimum, 8GB recommended
- **Disk**: 20GB minimum
- **Network**: Public IP address with firewall control
- **Domain**: Optional but recommended for HTTPS

### Edge Node Requirements

- **Operating System**: Any Linux distribution with SSH
- **CPU**: 1+ core
- **RAM**: 512MB minimum
- **Network**: Outbound internet access (port 22 to hub)
- **Python**: 3.9+ with pip

### Software Dependencies

**Hub Server:**
```bash
# System packages
sudo apt update
sudo apt install -y \
    python3-pip \
    python3-venv \
    postgresql \
    postgresql-contrib \
    nginx \
    ufw \
    git

# Python packages (installed in venv)
fastapi
uvicorn
asyncpg
psycopg2-binary
pyjwt
paramiko
websockets
python-multipart
```

**Edge Node:**
```bash
# System packages
sudo apt update
sudo apt install -y python3-pip openssh-client

# Python packages
paramiko
requests
```

---

## Hub Server Deployment

### Step 1: Database Setup

**1.1 Install and configure PostgreSQL:**

```bash
# Install PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# Start and enable service
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

**1.2 Create database and user:**

```bash
# Switch to postgres user
sudo -u postgres psql

# Execute SQL commands
CREATE DATABASE orizon;
CREATE USER orizon WITH ENCRYPTED PASSWORD 'your-secure-password';
GRANT ALL PRIVILEGES ON DATABASE orizon TO orizon;
\q
```

**1.3 Create database schema:**

```bash
# Connect to database
sudo -u postgres psql -d orizon

# Create tables (example schema)
CREATE TABLE users (
    user_id VARCHAR(100) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE nodes (
    node_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    hostname VARCHAR(255) NOT NULL,
    location VARCHAR(255),
    type VARCHAR(50) DEFAULT 'edge',
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE tunnels (
    tunnel_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    node_id UUID REFERENCES nodes(node_id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL,
    local_port INTEGER NOT NULL,
    remote_port INTEGER NOT NULL,
    protocol VARCHAR(20) DEFAULT 'tcp',
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE certificates (
    cert_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    node_id UUID REFERENCES nodes(node_id) ON DELETE CASCADE,
    public_key TEXT NOT NULL,
    signed_cert TEXT,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP
);

CREATE TABLE sessions (
    session_id VARCHAR(100) PRIMARY KEY,
    tunnel_id UUID REFERENCES tunnels(tunnel_id),
    user_email VARCHAR(255),
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    bytes_sent BIGINT DEFAULT 0,
    bytes_received BIGINT DEFAULT 0,
    commands_count INTEGER DEFAULT 0,
    errors_count INTEGER DEFAULT 0
);

\q
```

**1.4 Grant permissions:**

```bash
sudo -u postgres psql -d orizon -c "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO orizon;"
sudo -u postgres psql -d orizon -c "GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO orizon;"
sudo -u postgres psql -d orizon -c "GRANT ALL PRIVILEGES ON SCHEMA public TO orizon;"
```

### Step 2: SSH Certificate Authority Setup

**2.1 Create CA directory:**

```bash
sudo mkdir -p /etc/ssh/ca
sudo chmod 700 /etc/ssh/ca
```

**2.2 Generate CA key pair:**

```bash
sudo ssh-keygen -t rsa -b 4096 -f /etc/ssh/ca/orizon_ca -N "" -C "Orizon CA"
```

**2.3 Configure SSH server to trust CA:**

```bash
sudo bash -c 'echo "TrustedUserCAKeys /etc/ssh/ca/orizon_ca.pub" >> /etc/sshd_config'
sudo systemctl restart sshd
```

### Step 3: Backend API Deployment

**3.1 Create application directory:**

```bash
sudo mkdir -p /opt/orizon/backend
sudo chown -R $USER:$USER /opt/orizon
```

**3.2 Deploy backend code:**

```bash
# Copy backend files
sudo cp backend/simple_main.py /opt/orizon/backend/

# Create virtual environment
cd /opt/orizon
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install fastapi uvicorn asyncpg psycopg2-binary pyjwt paramiko websockets python-multipart
```

**3.3 Configure environment:**

```bash
# Create .env file
cat > /opt/orizon/.env << 'EOF'
ORIZON_DB_HOST=localhost
ORIZON_DB_NAME=orizon
ORIZON_DB_USER=orizon
ORIZON_DB_PASSWORD=your-secure-password
ORIZON_JWT_SECRET=your-secret-key-change-in-production-minimum-32-chars
ORIZON_WS_PORT=8765
EOF

# Secure the file
chmod 600 /opt/orizon/.env
```

**3.4 Create systemd service:**

```bash
sudo tee /etc/systemd/system/orizon-backend.service > /dev/null << 'EOF'
[Unit]
Description=Orizon Zero Trust Backend API
After=network.target postgresql.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/orizon
Environment="PATH=/opt/orizon/venv/bin"
EnvironmentFile=/opt/orizon/.env
ExecStart=/opt/orizon/venv/bin/uvicorn backend.simple_main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable orizon-backend.service
sudo systemctl start orizon-backend.service
```

**3.5 Verify backend is running:**

```bash
sudo systemctl status orizon-backend.service
curl http://localhost:8000/api/v1/health
```

### Step 4: WebSocket Terminal Server Deployment

**4.1 Deploy WebSocket server code:**

```bash
# Copy WebSocket server (v2.1 with urllib.parse fix)
sudo cp websocket_terminal_server.py /opt/orizon/
```

**4.2 Update JWT secret:**

```bash
# Edit websocket_terminal_server.py
sudo nano /opt/orizon/websocket_terminal_server.py

# Change line:
# JWT_SECRET = "your-secret-key-change-in-production-2024"
# To match your production secret (same as in .env)
```

**4.3 Create systemd service:**

```bash
sudo tee /etc/systemd/system/orizon-terminal.service > /dev/null << 'EOF'
[Unit]
Description=Orizon WebSocket Terminal Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/orizon
Environment="PATH=/opt/orizon/venv/bin"
ExecStart=/opt/orizon/venv/bin/python3 /opt/orizon/websocket_terminal_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable orizon-terminal.service
sudo systemctl start orizon-terminal.service
```

**4.4 Verify WebSocket server:**

```bash
sudo systemctl status orizon-terminal.service
sudo journalctl -u orizon-terminal.service -n 20
```

### Step 5: Frontend Deployment

**5.1 Create web directory:**

```bash
sudo mkdir -p /var/www/orizon-ztc
sudo chown -R www-data:www-data /var/www/orizon-ztc
```

**5.2 Deploy frontend files:**

```bash
# Copy HTML files
sudo cp frontend/dashboard.html /var/www/orizon-ztc/
sudo cp frontend/login.html /var/www/orizon-ztc/
sudo cp frontend/terminal.html /var/www/orizon-ztc/
sudo cp frontend/index.html /var/www/orizon-ztc/

# Create downloads directory for agent
sudo mkdir -p /var/www/orizon-ztc/downloads
sudo cp agents/orizon_agent.py /var/www/orizon-ztc/downloads/
sudo cp agents/install.sh /var/www/orizon-ztc/downloads/

# Set permissions
sudo chown -R www-data:www-data /var/www/orizon-ztc/
sudo chmod -R 644 /var/www/orizon-ztc/*.html
sudo chmod 755 /var/www/orizon-ztc/downloads/install.sh
```

**5.3 Update dashboard token (IMPORTANT):**

```bash
# Generate a production JWT token with 1-year expiration
python3 << 'PYTHON_SCRIPT'
import jwt
from datetime import datetime, timedelta

SECRET = "your-secret-key-change-in-production-minimum-32-chars"  # Match your production secret
expiry = datetime.utcnow() + timedelta(days=365)

token = jwt.encode({
    "user_id": "superuser-001",
    "email": "admin@orizon.io",  # Change to your admin email
    "role": "superuser",
    "exp": int(expiry.timestamp())
}, SECRET, algorithm="HS256")

print(f"Production Token (expires {expiry}):")
print(token)
PYTHON_SCRIPT

# Update dashboard.html with generated token
# Replace the token in line 1283 with your generated token
sudo nano /var/www/orizon-ztc/dashboard.html
# Find: &token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
# Replace with your generated token
```

### Step 6: Nginx Configuration

**6.1 Create Nginx site configuration:**

```bash
sudo tee /etc/nginx/sites-available/orizon-ztc > /dev/null << 'EOF'
server {
    listen 80;
    server_name your-hub-domain.com;  # Change to your domain or IP

    # Frontend static files
    location / {
        root /var/www/orizon-ztc;
        index index.html;
        try_files $uri $uri/ =404;
    }

    # Backend API proxy
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket proxy (optional, if using Nginx for WS)
    # location /ws/ {
    #     proxy_pass http://127.0.0.1:8765;
    #     proxy_http_version 1.1;
    #     proxy_set_header Upgrade $http_upgrade;
    #     proxy_set_header Connection "upgrade";
    #     proxy_set_header Host $host;
    #     proxy_set_header X-Real-IP $remote_addr;
    # }
}
EOF

# Enable site
sudo ln -s /etc/nginx/sites-available/orizon-ztc /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
```

### Step 7: Firewall Configuration

**7.1 Configure UFW firewall:**

```bash
# Reset firewall (CAREFUL if connected via SSH!)
sudo ufw --force reset

# Default policies
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH (IMPORTANT!)
sudo ufw allow 22/tcp comment 'SSH'

# Allow HTTP/HTTPS
sudo ufw allow 80/tcp comment 'HTTP'
sudo ufw allow 443/tcp comment 'HTTPS'

# Allow WebSocket Terminal Server
sudo ufw allow 8765/tcp comment 'Orizon WebSocket Terminal Server'

# Enable firewall
sudo ufw --force enable

# Verify rules
sudo ufw status numbered
```

Expected output:
```
Status: active

     To                         Action      From
     --                         ------      ----
[ 1] 22/tcp                     ALLOW IN    Anywhere                   # SSH
[ 2] 80/tcp                     ALLOW IN    Anywhere                   # HTTP
[ 3] 443/tcp                    ALLOW IN    Anywhere                   # HTTPS
[ 4] 8765/tcp                   ALLOW IN    Anywhere                   # Orizon WebSocket Terminal Server
```

### Step 8: Create Initial Admin User

**8.1 Insert admin user into database:**

```bash
# Generate password hash (using Python)
python3 << 'PYTHON_SCRIPT'
import hashlib
import secrets

password = "your-admin-password"  # Change this!
salt = secrets.token_hex(16)
password_hash = hashlib.sha256((password + salt).encode()).hexdigest()

print(f"Password: {password}")
print(f"Hash: {password_hash}")
print(f"\nSQL Command:")
print(f"INSERT INTO users (user_id, email, password_hash, role) VALUES ('superuser-001', 'admin@orizon.io', '{password_hash}', 'superuser');")
PYTHON_SCRIPT

# Execute SQL command from output above
sudo -u postgres psql -d orizon -c "INSERT INTO users ..."
```

---

## Edge Agent Deployment

### Method 1: Automated Installation (Recommended)

**From edge node:**

```bash
# Download and run install script
curl -sSL http://your-hub-ip/downloads/install.sh | sudo bash
```

The install script will:
1. Install Python dependencies
2. Download orizon_agent.py
3. Register node with hub
4. Generate SSH key pair
5. Get certificate signed by CA
6. Create systemd service
7. Start agent

### Method 2: Manual Installation

**1. Install dependencies:**

```bash
sudo apt update
sudo apt install -y python3-pip openssh-client
pip3 install paramiko requests
```

**2. Download agent:**

```bash
sudo mkdir -p /opt/orizon
cd /opt/orizon
sudo curl -O http://your-hub-ip/downloads/orizon_agent.py
sudo chmod +x orizon_agent.py
```

**3. Register node via API:**

```bash
# Get authentication token first
TOKEN=$(curl -s -X POST http://your-hub-ip/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@orizon.io","password":"your-admin-password"}' \
  | jq -r '.token')

# Create node
NODE_RESPONSE=$(curl -s -X POST http://your-hub-ip/api/v1/nodes \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Edge-Production-01",
    "hostname": "edge-prod-01.local",
    "location": "Production Data Center",
    "type": "edge"
  }')

# Extract node_id and certificate
NODE_ID=$(echo $NODE_RESPONSE | jq -r '.node_id')
CERT=$(echo $NODE_RESPONSE | jq -r '.certificate')
PRIVATE_KEY=$(echo $NODE_RESPONSE | jq -r '.private_key')

echo "Node ID: $NODE_ID"
```

**4. Save credentials:**

```bash
# Save private key
echo "$PRIVATE_KEY" | sudo tee /opt/orizon/edge_key
sudo chmod 600 /opt/orizon/edge_key

# Save certificate
echo "$CERT" | sudo tee /opt/orizon/edge_key-cert.pub
sudo chmod 644 /opt/orizon/edge_key-cert.pub
```

**5. Configure agent:**

```bash
# Create config file
sudo tee /opt/orizon/agent_config.json > /dev/null << EOF
{
  "node_id": "$NODE_ID",
  "hub_host": "your-hub-ip",
  "hub_port": 22,
  "hub_user": "orizonzerotrust",
  "ssh_key_path": "/opt/orizon/edge_key",
  "reconnect_interval": 30
}
EOF
```

**6. Create systemd service:**

```bash
sudo tee /etc/systemd/system/orizon-agent.service > /dev/null << 'EOF'
[Unit]
Description=Orizon Zero Trust Agent
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/orizon
ExecStart=/usr/bin/python3 /opt/orizon/orizon_agent.py
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable orizon-agent.service
sudo systemctl start orizon-agent.service
```

**7. Verify agent:**

```bash
sudo systemctl status orizon-agent.service
sudo journalctl -u orizon-agent.service -n 20
```

---

## Verification

### Hub Server Verification

**1. Check all services are running:**

```bash
sudo systemctl status orizon-backend.service
sudo systemctl status orizon-terminal.service
sudo systemctl status nginx.service
sudo systemctl status postgresql.service
```

**2. Test backend API:**

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Login test
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@orizon.io","password":"your-admin-password"}'
```

**3. Test WebSocket server:**

```bash
# Check listening
ss -tln | grep 8765

# Test connection (Python required)
python3 << 'PYTHON_TEST'
import asyncio
import websockets

async def test_ws():
    uri = "ws://localhost:8765/?tunnel_id=test&token=test"
    try:
        async with websockets.connect(uri) as ws:
            print("✅ WebSocket connection successful")
    except Exception as e:
        print(f"❌ WebSocket connection failed: {e}")

asyncio.run(test_ws())
PYTHON_TEST
```

**4. Test frontend access:**

```bash
# From external machine
curl -I http://your-hub-ip/
curl -I http://your-hub-ip/dashboard.html
curl -I http://your-hub-ip/terminal.html
```

**5. Check firewall:**

```bash
sudo ufw status numbered
```

### Edge Agent Verification

**1. Check agent service:**

```bash
sudo systemctl status orizon-agent.service
```

**2. Check tunnel establishment:**

```bash
# On hub server, check for reverse tunnel
ss -tln | grep 10001  # Or your configured remote_port
```

**3. Test tunnel connectivity:**

```bash
# On hub server, test SSH through tunnel
ssh -p 10001 -i /path/to/key localhost
```

### End-to-End Verification

**1. Create tunnel via dashboard:**
- Login to http://your-hub-ip/dashboard.html
- Navigate to Tunnels section
- Create new tunnel (SSH, port 22 → 10001)

**2. Test terminal access:**
- Click terminal icon (💻) next to tunnel
- Terminal should open in new window
- Verify connection in debug panel
- Execute test commands: `ls`, `whoami`, `uname -a`

**3. Check session logs:**

```bash
# On hub server
sudo -u postgres psql -d orizon -c "SELECT * FROM sessions ORDER BY started_at DESC LIMIT 5;"
```

---

## Post-Deployment Configuration

### Enable HTTPS (Recommended)

**Using Let's Encrypt:**

```bash
# Install certbot
sudo apt install -y certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d your-hub-domain.com

# Verify auto-renewal
sudo certbot renew --dry-run
```

### Upgrade to WSS (WebSocket Secure)

**After enabling HTTPS, proxy WebSocket through Nginx:**

```bash
# Edit Nginx config
sudo nano /etc/nginx/sites-available/orizon-ztc

# Uncomment the /ws/ location block
# Update terminal.html to use wss:// instead of ws://
sudo nano /var/www/orizon-ztc/terminal.html
# Change: ws://68.183.219.222:8765
# To: wss://your-hub-domain.com/ws
```

### Configure Backup

**Database backup cron job:**

```bash
# Create backup script
sudo tee /opt/orizon/backup_db.sh > /dev/null << 'EOF'
#!/bin/bash
BACKUP_DIR="/var/backups/orizon"
mkdir -p $BACKUP_DIR
pg_dump -U orizon orizon | gzip > $BACKUP_DIR/orizon_$(date +%Y%m%d_%H%M%S).sql.gz
# Keep only last 30 days
find $BACKUP_DIR -name "orizon_*.sql.gz" -mtime +30 -delete
EOF

sudo chmod +x /opt/orizon/backup_db.sh

# Add to crontab (daily at 2 AM)
echo "0 2 * * * /opt/orizon/backup_db.sh" | sudo crontab -
```

### Security Hardening

**1. Change all default secrets:**

```bash
# Generate strong secrets
openssl rand -base64 48

# Update .env file
sudo nano /opt/orizon/.env

# Update websocket_terminal_server.py
sudo nano /opt/orizon/websocket_terminal_server.py

# Restart services
sudo systemctl restart orizon-backend.service
sudo systemctl restart orizon-terminal.service
```

**2. Enable fail2ban:**

```bash
sudo apt install -y fail2ban

# Create jail for Orizon
sudo tee /etc/fail2ban/jail.d/orizon.conf > /dev/null << 'EOF'
[orizon-auth]
enabled = true
port = http,https
filter = orizon-auth
logpath = /var/log/nginx/access.log
maxretry = 5
bantime = 3600
EOF

# Create filter
sudo tee /etc/fail2ban/filter.d/orizon-auth.conf > /dev/null << 'EOF'
[Definition]
failregex = ^<HOST> .* "POST /api/v1/auth/login HTTP.*" 401
ignoreregex =
EOF

sudo systemctl restart fail2ban
```

---

## Troubleshooting

### Backend Service Won't Start

**Check logs:**
```bash
sudo journalctl -u orizon-backend.service -n 50 --no-pager
```

**Common issues:**
- Database connection failure → Check PostgreSQL is running and credentials are correct
- Port 8000 already in use → Check for other services on port 8000
- Import errors → Verify all Python dependencies are installed in venv

### WebSocket Server Connection Fails

**Check firewall:**
```bash
sudo ufw status | grep 8765
```

**Test local connection:**
```bash
telnet localhost 8765
```

**Check service logs:**
```bash
sudo journalctl -u orizon-terminal.service -f
```

### Terminal Shows Code 1008 (Invalid Token)

**Verify token format:**
```bash
# Decode JWT token
echo "YOUR_TOKEN" | cut -d'.' -f2 | base64 -d | python3 -m json.tool
```

**Check expiration:**
- Token must not be expired
- Secret must match between dashboard and WebSocket server

**Regenerate token:**
```bash
python3 /tmp/generate_terminal_token.py  # Use script from deployment
```

### Edge Agent Won't Connect

**Check network connectivity:**
```bash
# From edge node
nc -zv your-hub-ip 22
```

**Verify certificate:**
```bash
ssh-keygen -L -f /opt/orizon/edge_key-cert.pub
```

**Check agent logs:**
```bash
sudo journalctl -u orizon-agent.service -n 50
```

---

## Rollback Procedures

### Rollback Backend

```bash
# Stop current service
sudo systemctl stop orizon-backend.service

# Restore backup
sudo cp /opt/orizon/backend/simple_main.py.backup /opt/orizon/backend/simple_main.py

# Restart service
sudo systemctl start orizon-backend.service
sudo systemctl status orizon-backend.service
```

### Rollback WebSocket Server

```bash
# Stop service
sudo systemctl stop orizon-terminal.service

# Restore backup
sudo cp /opt/orizon/websocket_terminal_server.py.backup /opt/orizon/websocket_terminal_server.py

# Restart service
sudo systemctl start orizon-terminal.service
```

### Rollback Frontend

```bash
# Restore dashboard
sudo cp /var/www/orizon-ztc/dashboard.html.bak /var/www/orizon-ztc/dashboard.html

# Restore terminal
sudo cp /var/www/orizon-ztc/terminal.html.bak /var/www/orizon-ztc/terminal.html

# Set permissions
sudo chown www-data:www-data /var/www/orizon-ztc/*.html
```

### Database Rollback

```bash
# List available backups
ls -lh /var/backups/orizon/

# Restore from backup
gunzip < /var/backups/orizon/orizon_20251115_020000.sql.gz | sudo -u postgres psql orizon
```

---

## Deployment Checklist

### Pre-Deployment

- [ ] Hub server meets minimum requirements
- [ ] PostgreSQL installed and running
- [ ] Firewall rules planned and documented
- [ ] SSL certificate obtained (if using HTTPS)
- [ ] Secrets generated and securely stored
- [ ] Backup strategy defined

### Hub Deployment

- [ ] Database created and schema applied
- [ ] SSH CA configured
- [ ] Backend API deployed and running
- [ ] WebSocket server deployed and running
- [ ] Frontend files deployed
- [ ] Nginx configured and running
- [ ] Firewall rules applied
- [ ] Admin user created
- [ ] All services enabled and starting on boot

### Edge Deployment

- [ ] Agent installed on edge node
- [ ] Node registered in database
- [ ] Certificate signed by CA
- [ ] Agent service running
- [ ] Reverse tunnel established

### Verification

- [ ] Backend API health check passes
- [ ] WebSocket server accepts connections
- [ ] Frontend accessible from browser
- [ ] Login to dashboard successful
- [ ] Create test tunnel successful
- [ ] Terminal connection successful
- [ ] Commands execute on edge node
- [ ] Session logged in database

### Post-Deployment

- [ ] HTTPS enabled (production)
- [ ] WSS enabled for WebSocket (production)
- [ ] Backup cron job configured
- [ ] Monitoring configured
- [ ] Documentation updated with deployment details
- [ ] Team trained on system operation

---

## Support and Maintenance

### Log Locations

- Backend API: `sudo journalctl -u orizon-backend.service`
- WebSocket Server: `sudo journalctl -u orizon-terminal.service`
- Nginx: `/var/log/nginx/access.log`, `/var/log/nginx/error.log`
- PostgreSQL: `/var/log/postgresql/postgresql-13-main.log`
- Edge Agent: `sudo journalctl -u orizon-agent.service`

### Monitoring Commands

```bash
# Service status
sudo systemctl status orizon-backend orizon-terminal nginx postgresql

# Active connections
ss -tln | grep -E '8000|8765|5432'

# Database connections
sudo -u postgres psql -d orizon -c "SELECT count(*) FROM pg_stat_activity;"

# Active tunnels
sudo -u postgres psql -d orizon -c "SELECT * FROM tunnels WHERE status='active';"

# Recent sessions
sudo -u postgres psql -d orizon -c "SELECT session_id, user_email, started_at, ended_at FROM sessions ORDER BY started_at DESC LIMIT 10;"
```

### Updating Components

```bash
# Update backend
sudo systemctl stop orizon-backend.service
sudo cp new_simple_main.py /opt/orizon/backend/simple_main.py
sudo systemctl start orizon-backend.service

# Update WebSocket server
sudo systemctl stop orizon-terminal.service
sudo cp new_websocket_terminal_server.py /opt/orizon/
sudo systemctl start orizon-terminal.service

# Update frontend (no service restart needed)
sudo cp new_terminal.html /var/www/orizon-ztc/
sudo chown www-data:www-data /var/www/orizon-ztc/terminal.html
```

---

**Deployment Guide Version**: 2.0.0
**Last Updated**: 2025-11-15
**Author**: Orizon Team

For additional support, see [README-v2.md](./README-v2.md) and [TROUBLESHOOTING.md](./TROUBLESHOOTING.md).
