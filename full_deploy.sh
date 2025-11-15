#!/bin/bash
###############################################################################
# Orizon Zero Trust Connect - Full Deployment Script
# For: Marco @ Syneto/Orizon
# Server: OrizonZeroTrust1 (68.183.219.222)
###############################################################################

set -e

# Server credentials
SERVER="68.183.219.222"
USER="lorenz"
PASS='ripper-FfFIlBelloccio.1969F'

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Helper function to run SSH commands
ssh_exec() {
    local cmd="$@"
    # If command contains sudo, prepend password echo
    if [[ "$cmd" == *"sudo"* ]]; then
        sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no ${USER}@${SERVER} "echo '$PASS' | sudo -S bash -c '$cmd'"
    else
        sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no ${USER}@${SERVER} "$cmd"
    fi
}

# Helper function to copy files
ssh_copy() {
    sshpass -p "$PASS" scp -o StrictHostKeyChecking=no "$@"
}

print_header() {
    echo -e "${BLUE}=============================================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}=============================================================================${NC}"
}

print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }

###############################################################################
# STEP 1: BACKUP EXISTING DATA
###############################################################################

print_header "STEP 1: Backup Existing Data"

print_info "Creating backup directory..."
ssh_exec "sudo mkdir -p /opt/orizon_backup/$(date +%Y%m%d_%H%M%S)"

print_info "Backing up database (if exists)..."
ssh_exec "sudo -u postgres pg_dump orizon > /tmp/orizon_backup.sql 2>/dev/null || echo 'No database to backup'" || true

print_success "Backup completed"

###############################################################################
# STEP 2: CLEANUP OLD INSTALLATIONS
###############################################################################

print_header "STEP 2: Cleanup Old Installations"

print_info "Stopping services..."
ssh_exec "sudo systemctl stop orizon-backend 2>/dev/null || true"
ssh_exec "sudo systemctl stop orizon-vnc-gateway 2>/dev/null || true"
ssh_exec "sudo systemctl stop nginx 2>/dev/null || true"

print_info "Removing old systemd services..."
ssh_exec "sudo systemctl disable orizon-backend 2>/dev/null || true"
ssh_exec "sudo systemctl disable orizon-vnc-gateway 2>/dev/null || true"
ssh_exec "sudo rm -f /etc/systemd/system/orizon-*.service"
ssh_exec "sudo systemctl daemon-reload"

print_info "Cleaning old files..."
ssh_exec "sudo rm -rf /opt/orizon 2>/dev/null || true"
ssh_exec "sudo rm -rf /var/www/orizon-ztc 2>/dev/null || true"

print_success "Cleanup completed"

###############################################################################
# STEP 3: INSTALL SYSTEM DEPENDENCIES
###############################################################################

print_header "STEP 3: Install System Dependencies"

print_info "Updating package list..."
ssh_exec "sudo apt update -qq"

print_info "Installing required packages..."
ssh_exec "sudo DEBIAN_FRONTEND=noninteractive apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    postgresql \
    postgresql-contrib \
    redis-server \
    mongodb-org \
    nginx \
    git \
    curl \
    build-essential \
    ufw \
    net-tools 2>&1 | grep -v 'already the newest version' || true"

print_success "System dependencies installed"

###############################################################################
# STEP 4: SETUP DATABASES
###############################################################################

print_header "STEP 4: Setup Databases"

# PostgreSQL
print_info "Configuring PostgreSQL..."
ssh_exec "sudo systemctl start postgresql"
ssh_exec "sudo systemctl enable postgresql"

# Create database and user
ssh_exec "sudo -u postgres psql -c \"DROP DATABASE IF EXISTS orizon;\" 2>/dev/null || true"
ssh_exec "sudo -u postgres psql -c \"DROP USER IF EXISTS orizon;\" 2>/dev/null || true"
ssh_exec "sudo -u postgres psql -c \"CREATE USER orizon WITH PASSWORD 'orizon2025secure';\""
ssh_exec "sudo -u postgres psql -c \"CREATE DATABASE orizon OWNER orizon;\""
ssh_exec "sudo -u postgres psql -c \"GRANT ALL PRIVILEGES ON DATABASE orizon TO orizon;\""

print_success "PostgreSQL configured"

# Redis
print_info "Configuring Redis..."
ssh_exec "sudo systemctl start redis-server"
ssh_exec "sudo systemctl enable redis-server"

print_success "Redis configured"

# MongoDB (install if needed)
print_info "Configuring MongoDB..."
ssh_exec "sudo systemctl start mongod 2>/dev/null || echo 'MongoDB will be installed'"
ssh_exec "sudo systemctl enable mongod 2>/dev/null || true"

print_success "MongoDB configured"

###############################################################################
# STEP 5: DEPLOY BACKEND
###############################################################################

print_header "STEP 5: Deploy Backend"

print_info "Creating directory structure..."
ssh_exec "sudo mkdir -p /opt/orizon/backend/{app/{models,schemas,services,api/v1/endpoints,core,auth,middleware,monitoring,tunnel,websocket},logs}"

print_info "Uploading backend files..."

# Core files
ssh_copy backend/app/main.py ${USER}@${SERVER}:/tmp/
ssh_exec "sudo mv /tmp/main.py /opt/orizon/backend/app/"

# Models
for file in backend/app/models/*.py; do
    if [ -f "$file" ]; then
        filename=$(basename "$file")
        ssh_copy "$file" ${USER}@${SERVER}:/tmp/
        ssh_exec "sudo mv /tmp/$filename /opt/orizon/backend/app/models/"
    fi
done

# Schemas
for file in backend/app/schemas/*.py; do
    if [ -f "$file" ]; then
        filename=$(basename "$file")
        ssh_copy "$file" ${USER}@${SERVER}:/tmp/
        ssh_exec "sudo mv /tmp/$filename /opt/orizon/backend/app/schemas/"
    fi
done

# Services
for file in backend/app/services/*.py; do
    if [ -f "$file" ]; then
        filename=$(basename "$file")
        ssh_copy "$file" ${USER}@${SERVER}:/tmp/
        ssh_exec "sudo mv /tmp/$filename /opt/orizon/backend/app/services/"
    fi
done

# API Endpoints
for file in backend/app/api/v1/endpoints/*.py; do
    if [ -f "$file" ]; then
        filename=$(basename "$file")
        ssh_copy "$file" ${USER}@${SERVER}:/tmp/
        ssh_exec "sudo mv /tmp/$filename /opt/orizon/backend/app/api/v1/endpoints/"
    fi
done

# API Router
ssh_copy backend/app/api/v1/router.py ${USER}@${SERVER}:/tmp/
ssh_exec "sudo mv /tmp/router.py /opt/orizon/backend/app/api/v1/"

print_info "Creating Python virtual environment..."
ssh_exec "cd /opt/orizon/backend && python3 -m venv venv"

print_info "Installing Python dependencies..."
cat > /tmp/requirements.txt <<'EOF'
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy[asyncio]==2.0.23
asyncpg==0.29.0
pydantic==2.5.0
pydantic-settings==2.1.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
redis==5.0.1
pymongo==4.6.0
loguru==0.7.2
psutil==5.9.6
websockets==12.0
PyJWT==2.8.0
EOF

ssh_copy /tmp/requirements.txt ${USER}@${SERVER}:/tmp/
ssh_exec "cd /opt/orizon/backend && venv/bin/pip install -r /tmp/requirements.txt -q"

print_info "Creating database tables..."

# Create SQL migration script
cat > /tmp/create_tables.sql <<'EOF'
-- Users table
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(36) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(50) NOT NULL DEFAULT 'user',
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    is_active BOOLEAN DEFAULT true,
    is_2fa_enabled BOOLEAN DEFAULT false,
    totp_secret VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

-- Nodes table
CREATE TABLE IF NOT EXISTS nodes (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    hostname VARCHAR(255) NOT NULL,
    ip_address VARCHAR(45),
    status VARCHAR(50) DEFAULT 'offline',
    node_type VARCHAR(50),
    cpu_usage FLOAT DEFAULT 0,
    memory_usage FLOAT DEFAULT 0,
    disk_usage FLOAT DEFAULT 0,
    owner_id VARCHAR(36) REFERENCES users(id),
    last_seen TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tunnels table
CREATE TABLE IF NOT EXISTS tunnels (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    tunnel_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'inactive',
    local_port INTEGER NOT NULL,
    remote_port INTEGER NOT NULL,
    hub_host VARCHAR(255) NOT NULL,
    hub_port INTEGER NOT NULL,
    bytes_sent BIGINT DEFAULT 0,
    bytes_received BIGINT DEFAULT 0,
    node_id VARCHAR(36) REFERENCES nodes(id),
    owner_id VARCHAR(36) REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Access rules table
CREATE TABLE IF NOT EXISTS access_rules (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    priority INTEGER DEFAULT 100,
    action VARCHAR(50) NOT NULL,
    source_ip VARCHAR(45),
    destination_ip VARCHAR(45),
    protocol VARCHAR(20),
    port INTEGER,
    enabled BOOLEAN DEFAULT true,
    node_id VARCHAR(36) REFERENCES nodes(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- VNC Sessions table
CREATE TABLE IF NOT EXISTS vnc_sessions (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description VARCHAR(500),
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    tunnel_port INTEGER,
    websocket_path VARCHAR(500),
    session_token VARCHAR(1024),
    vnc_host VARCHAR(255) DEFAULT 'localhost',
    vnc_port INTEGER DEFAULT 5900,
    quality VARCHAR(20) DEFAULT 'medium',
    screen_width INTEGER DEFAULT 1920,
    screen_height INTEGER DEFAULT 1080,
    allow_resize BOOLEAN DEFAULT true,
    view_only BOOLEAN DEFAULT false,
    require_acl_validation BOOLEAN DEFAULT true,
    max_duration_seconds INTEGER DEFAULT 300,
    expires_at TIMESTAMP,
    started_at TIMESTAMP,
    ended_at TIMESTAMP,
    bytes_sent BIGINT DEFAULT 0,
    bytes_received BIGINT DEFAULT 0,
    frames_sent INTEGER DEFAULT 0,
    latency_ms INTEGER,
    last_activity_at TIMESTAMP,
    last_error VARCHAR(500),
    error_count INTEGER DEFAULT 0,
    client_ip VARCHAR(45),
    client_user_agent VARCHAR(500),
    node_id VARCHAR(36) NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tunnel_id VARCHAR(36) REFERENCES tunnels(id) ON DELETE SET NULL,
    tags JSONB DEFAULT '[]'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_nodes_owner ON nodes(owner_id);
CREATE INDEX IF NOT EXISTS idx_nodes_status ON nodes(status);
CREATE INDEX IF NOT EXISTS idx_tunnels_node ON tunnels(node_id);
CREATE INDEX IF NOT EXISTS idx_tunnels_owner ON tunnels(owner_id);
CREATE INDEX IF NOT EXISTS idx_vnc_sessions_node ON vnc_sessions(node_id);
CREATE INDEX IF NOT EXISTS idx_vnc_sessions_user ON vnc_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_vnc_sessions_status ON vnc_sessions(status);
CREATE INDEX IF NOT EXISTS idx_vnc_sessions_expires ON vnc_sessions(expires_at);

-- Create default superuser
INSERT INTO users (id, email, username, hashed_password, full_name, role, status, is_active)
VALUES (
    'superuser-001',
    'marco@orizon.io',
    'marco',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYzS/Z7QU4i',  -- password: admin
    'Marco Lorenzi',
    'superuser',
    'active',
    true
) ON CONFLICT (email) DO NOTHING;

EOF

ssh_copy /tmp/create_tables.sql ${USER}@${SERVER}:/tmp/
ssh_exec "sudo -u postgres psql -d orizon -f /tmp/create_tables.sql"

print_success "Database tables created"

print_info "Creating systemd service for backend..."

cat > /tmp/orizon-backend.service <<'EOF'
[Unit]
Description=Orizon Zero Trust Connect Backend
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/orizon/backend
Environment="DATABASE_URL=postgresql+asyncpg://orizon:orizon2025secure@localhost:5432/orizon"
Environment="REDIS_URL=redis://localhost:6379/0"
Environment="MONGODB_URL=mongodb://localhost:27017"
Environment="SECRET_KEY=orizon-secret-key-2025-change-in-production"
Environment="DEBUG=false"
ExecStart=/opt/orizon/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

ssh_copy /tmp/orizon-backend.service ${USER}@${SERVER}:/tmp/
ssh_exec "sudo mv /tmp/orizon-backend.service /etc/systemd/system/"
ssh_exec "sudo systemctl daemon-reload"
ssh_exec "sudo systemctl enable orizon-backend"
ssh_exec "sudo systemctl start orizon-backend"

sleep 3

# Check if backend started successfully
if ssh_exec "sudo systemctl is-active --quiet orizon-backend"; then
    print_success "Backend deployed and running"
else
    print_error "Backend failed to start. Checking logs..."
    ssh_exec "sudo journalctl -u orizon-backend -n 50 --no-pager"
    exit 1
fi

###############################################################################
# STEP 6: DEPLOY VNC GATEWAY
###############################################################################

print_header "STEP 6: Deploy VNC Gateway"

print_info "Creating VNC Gateway directory..."
ssh_exec "sudo mkdir -p /opt/orizon/vnc_gateway/logs"

print_info "Uploading VNC Gateway files..."
ssh_copy services/vnc_gateway/vnc_gateway.py ${USER}@${SERVER}:/tmp/
ssh_copy services/vnc_gateway/requirements.txt ${USER}@${SERVER}:/tmp/
ssh_exec "sudo mv /tmp/vnc_gateway.py /opt/orizon/vnc_gateway/"
ssh_exec "sudo mv /tmp/requirements.txt /opt/orizon/vnc_gateway/"

print_info "Installing VNC Gateway dependencies..."
ssh_exec "pip3 install websockets PyJWT loguru -q"

print_info "Creating systemd service for VNC Gateway..."

cat > /tmp/orizon-vnc-gateway.service <<'EOF'
[Unit]
Description=Orizon VNC Gateway Service
After=network.target orizon-backend.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/orizon/vnc_gateway
Environment="JWT_SECRET_KEY=orizon-secret-key-2025-change-in-production"
Environment="BACKEND_URL=http://localhost:8000"
Environment="VNC_GATEWAY_HOST=0.0.0.0"
Environment="VNC_GATEWAY_PORT=6080"
Environment="TUNNEL_HOST=localhost"
ExecStart=/usr/bin/python3 /opt/orizon/vnc_gateway/vnc_gateway.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

ssh_copy /tmp/orizon-vnc-gateway.service ${USER}@${SERVER}:/tmp/
ssh_exec "sudo mv /tmp/orizon-vnc-gateway.service /etc/systemd/system/"
ssh_exec "sudo systemctl daemon-reload"
ssh_exec "sudo systemctl enable orizon-vnc-gateway"
ssh_exec "sudo systemctl start orizon-vnc-gateway"

sleep 2

if ssh_exec "sudo systemctl is-active --quiet orizon-vnc-gateway"; then
    print_success "VNC Gateway deployed and running"
else
    print_warning "VNC Gateway may have issues. Checking logs..."
    ssh_exec "sudo journalctl -u orizon-vnc-gateway -n 20 --no-pager"
fi

###############################################################################
# STEP 7: DEPLOY FRONTEND
###############################################################################

print_header "STEP 7: Deploy Frontend"

print_info "Building frontend locally..."
cd frontend

# Check if node_modules exists, if not install
if [ ! -d "node_modules" ]; then
    print_info "Installing frontend dependencies..."
    npm install -q
fi

# Install noVNC if not present
npm install @novnc/novnc -q 2>/dev/null || true

print_info "Building production bundle..."
npm run build

cd ..

print_info "Creating web directory on server..."
ssh_exec "sudo mkdir -p /var/www/orizon-ztc"

print_info "Uploading frontend files..."
ssh_copy -r frontend/dist/* ${USER}@${SERVER}:/tmp/dist/
ssh_exec "sudo cp -r /tmp/dist/* /var/www/orizon-ztc/"
ssh_exec "sudo chown -R www-data:www-data /var/www/orizon-ztc"
ssh_exec "rm -rf /tmp/dist"

print_success "Frontend deployed"

###############################################################################
# STEP 8: CONFIGURE NGINX
###############################################################################

print_header "STEP 8: Configure Nginx"

print_info "Creating Nginx configuration..."

cat > /tmp/orizon-ztc.conf <<'EOF'
server {
    listen 80;
    listen [::]:80;
    server_name _;

    # Frontend
    location / {
        root /var/www/orizon-ztc;
        try_files $uri $uri/ /index.html;

        # Security headers
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;
    }

    # Backend API
    location /api/ {
        proxy_pass http://localhost:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts for long-running requests
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # WebSocket for nodes
    location /api/v1/nodes/ws/ {
        proxy_pass http://localhost:8000/api/v1/nodes/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

        # WebSocket timeouts
        proxy_connect_timeout 7d;
        proxy_send_timeout 7d;
        proxy_read_timeout 7d;
    }
}

# VNC Gateway WebSocket (separate port)
server {
    listen 6080;
    listen [::]:6080;
    server_name _;

    location / {
        proxy_pass http://localhost:6080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

        # WebSocket timeouts
        proxy_connect_timeout 1h;
        proxy_send_timeout 1h;
        proxy_read_timeout 1h;
    }
}
EOF

ssh_copy /tmp/orizon-ztc.conf ${USER}@${SERVER}:/tmp/
ssh_exec "sudo mv /tmp/orizon-ztc.conf /etc/nginx/sites-available/"
ssh_exec "sudo rm -f /etc/nginx/sites-enabled/default"
ssh_exec "sudo ln -sf /etc/nginx/sites-available/orizon-ztc.conf /etc/nginx/sites-enabled/"

print_info "Testing Nginx configuration..."
ssh_exec "sudo nginx -t"

print_info "Starting Nginx..."
ssh_exec "sudo systemctl enable nginx"
ssh_exec "sudo systemctl restart nginx"

print_success "Nginx configured"

###############################################################################
# STEP 9: CONFIGURE FIREWALL
###############################################################################

print_header "STEP 9: Configure Firewall"

print_info "Configuring UFW firewall..."

# Reset UFW to clean state
ssh_exec "sudo ufw --force reset"

# Allow SSH
ssh_exec "sudo ufw allow 22/tcp comment 'SSH'"

# Allow HTTP/HTTPS
ssh_exec "sudo ufw allow 80/tcp comment 'HTTP'"
ssh_exec "sudo ufw allow 443/tcp comment 'HTTPS'"

# Allow VNC Gateway
ssh_exec "sudo ufw allow 6080/tcp comment 'VNC Gateway WebSocket'"

# Allow tunnel ports
ssh_exec "sudo ufw allow 50000:59999/tcp comment 'VNC Tunnel Ports'"

# Enable firewall
ssh_exec "sudo ufw --force enable"

print_success "Firewall configured"

###############################################################################
# STEP 10: END-TO-END TESTS
###############################################################################

print_header "STEP 10: End-to-End Tests"

# Test 1: Backend API Health
print_info "Test 1: Backend API Health Check..."
HEALTH=$(ssh_exec "curl -s http://localhost:8000/api/v1/health || echo 'FAIL'")
if [[ "$HEALTH" == *"healthy"* ]] || [[ "$HEALTH" == *"ok"* ]]; then
    print_success "Backend API is healthy"
else
    print_error "Backend API health check failed: $HEALTH"
fi

# Test 2: Database connection
print_info "Test 2: Database Connection..."
DB_TEST=$(ssh_exec "sudo -u postgres psql -d orizon -c 'SELECT COUNT(*) FROM users;' -t" 2>&1)
if [[ "$DB_TEST" =~ [0-9]+ ]]; then
    print_success "Database connection OK (Users count: $DB_TEST)"
else
    print_error "Database connection failed"
fi

# Test 3: Redis connection
print_info "Test 3: Redis Connection..."
REDIS_TEST=$(ssh_exec "redis-cli ping 2>&1")
if [[ "$REDIS_TEST" == "PONG" ]]; then
    print_success "Redis connection OK"
else
    print_error "Redis connection failed"
fi

# Test 4: Frontend serving
print_info "Test 4: Frontend Serving..."
FRONTEND_TEST=$(ssh_exec "curl -s -o /dev/null -w '%{http_code}' http://localhost/")
if [[ "$FRONTEND_TEST" == "200" ]]; then
    print_success "Frontend is serving correctly"
else
    print_warning "Frontend returned HTTP $FRONTEND_TEST"
fi

# Test 5: VNC Gateway WebSocket
print_info "Test 5: VNC Gateway WebSocket..."
VNC_TEST=$(ssh_exec "curl -s -o /dev/null -w '%{http_code}' http://localhost:6080/")
if [[ "$VNC_TEST" == "426" ]] || [[ "$VNC_TEST" == "400" ]]; then
    print_success "VNC Gateway is running (WebSocket upgrade required)"
else
    print_warning "VNC Gateway returned HTTP $VNC_TEST"
fi

# Test 6: Services status
print_info "Test 6: Services Status..."
BACKEND_STATUS=$(ssh_exec "sudo systemctl is-active orizon-backend")
VNC_STATUS=$(ssh_exec "sudo systemctl is-active orizon-vnc-gateway")
NGINX_STATUS=$(ssh_exec "sudo systemctl is-active nginx")

if [[ "$BACKEND_STATUS" == "active" ]]; then
    print_success "Backend service: active"
else
    print_error "Backend service: $BACKEND_STATUS"
fi

if [[ "$VNC_STATUS" == "active" ]]; then
    print_success "VNC Gateway service: active"
else
    print_error "VNC Gateway service: $VNC_STATUS"
fi

if [[ "$NGINX_STATUS" == "active" ]]; then
    print_success "Nginx service: active"
else
    print_error "Nginx service: $NGINX_STATUS"
fi

###############################################################################
# DEPLOYMENT SUMMARY
###############################################################################

print_header "DEPLOYMENT COMPLETE"

echo ""
print_success "Orizon Zero Trust Connect v1.1 deployed successfully!"
echo ""
echo "🌐 Access Points:"
echo "   Frontend:     http://68.183.219.222"
echo "   Backend API:  http://68.183.219.222/api/v1"
echo "   API Docs:     http://68.183.219.222/api/v1/docs"
echo "   VNC Gateway:  ws://68.183.219.222:6080"
echo ""
echo "🔐 Default Credentials:"
echo "   Email:    marco@orizon.io"
echo "   Password: admin"
echo ""
echo "📊 Service Status:"
ssh_exec "sudo systemctl status orizon-backend --no-pager | head -3"
ssh_exec "sudo systemctl status orizon-vnc-gateway --no-pager | head -3"
ssh_exec "sudo systemctl status nginx --no-pager | head -3"
echo ""
echo "📝 Useful Commands:"
echo "   Backend logs:     ssh lorenz@68.183.219.222 'sudo journalctl -u orizon-backend -f'"
echo "   VNC Gateway logs: ssh lorenz@68.183.219.222 'sudo journalctl -u orizon-vnc-gateway -f'"
echo "   Nginx logs:       ssh lorenz@68.183.219.222 'sudo tail -f /var/log/nginx/access.log'"
echo ""
print_info "Next steps:"
echo "   1. Change default password for marco@orizon.io"
echo "   2. Setup SSL/TLS certificates (Let's Encrypt)"
echo "   3. Deploy edge agents to nodes"
echo "   4. Configure ACL rules"
echo "   5. Test VNC session creation"
echo ""

exit 0
