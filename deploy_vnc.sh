#!/bin/bash
###############################################################################
# Orizon Zero Trust Connect - VNC Feature Deployment Script
# For: Marco @ Syneto/Orizon
#
# This script deploys the VNC Remote Desktop feature to the production server
#
# Usage:
#   ./deploy_vnc.sh [--full|--backend|--frontend|--gateway|--agent]
#
# Server: 68.183.219.222 (lorenz / ripper-FfFIlBelloccio.1969F)
###############################################################################

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SERVER="68.183.219.222"
USER="lorenz"
SSH_KEY=""  # Add SSH key path if needed

# Print functions
print_header() {
    echo -e "${BLUE}=============================================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}=============================================================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Deployment mode
MODE="${1:-full}"

print_header "Orizon Zero Trust Connect - VNC Deployment"
echo "Mode: $MODE"
echo "Server: $SERVER"
echo "User: $USER"
echo ""

###############################################################################
# STEP 1: PRE-DEPLOYMENT CHECKS
###############################################################################

print_header "STEP 1: Pre-Deployment Checks"

# Check if server is reachable
if ! ping -c 1 "$SERVER" &> /dev/null; then
    print_error "Server $SERVER is not reachable"
    exit 1
fi
print_success "Server is reachable"

# Check if we can SSH
if ! ssh -o ConnectTimeout=5 ${USER}@${SERVER} "echo 'SSH OK'" &> /dev/null; then
    print_error "Cannot SSH to $SERVER"
    print_info "Run: ssh-copy-id ${USER}@${SERVER}"
    exit 1
fi
print_success "SSH connection OK"

###############################################################################
# STEP 2: DATABASE MIGRATION
###############################################################################

if [[ "$MODE" == "full" || "$MODE" == "backend" ]]; then
    print_header "STEP 2: Database Migration"

    print_info "Creating VNC sessions table..."

    # Create database migration
    cat > /tmp/vnc_migration.sql <<'EOF'
-- Orizon Zero Trust Connect - VNC Sessions Table Migration
-- Create vnc_sessions table

CREATE TABLE IF NOT EXISTS vnc_sessions (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description VARCHAR(500),
    status VARCHAR(50) NOT NULL DEFAULT 'pending',

    -- Connection
    tunnel_port INTEGER,
    websocket_path VARCHAR(500),
    session_token VARCHAR(1024),

    -- VNC config
    vnc_host VARCHAR(255) DEFAULT 'localhost',
    vnc_port INTEGER DEFAULT 5900,
    quality VARCHAR(20) DEFAULT 'medium',

    -- Display
    screen_width INTEGER DEFAULT 1920,
    screen_height INTEGER DEFAULT 1080,
    allow_resize BOOLEAN DEFAULT true,

    -- Security
    view_only BOOLEAN DEFAULT false,
    require_acl_validation BOOLEAN DEFAULT true,

    -- Timing
    max_duration_seconds INTEGER DEFAULT 300,
    expires_at TIMESTAMP,
    started_at TIMESTAMP,
    ended_at TIMESTAMP,

    -- Metrics
    bytes_sent BIGINT DEFAULT 0,
    bytes_received BIGINT DEFAULT 0,
    frames_sent INTEGER DEFAULT 0,
    latency_ms INTEGER,

    -- Health
    last_activity_at TIMESTAMP,
    last_error VARCHAR(500),
    error_count INTEGER DEFAULT 0,

    -- Client
    client_ip VARCHAR(45),
    client_user_agent VARCHAR(500),

    -- Relationships
    node_id VARCHAR(36) NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tunnel_id VARCHAR(36) REFERENCES tunnels(id) ON DELETE SET NULL,

    -- Metadata
    tags JSONB DEFAULT '[]'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_vnc_sessions_node_id ON vnc_sessions(node_id);
CREATE INDEX IF NOT EXISTS idx_vnc_sessions_user_id ON vnc_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_vnc_sessions_status ON vnc_sessions(status);
CREATE INDEX IF NOT EXISTS idx_vnc_sessions_expires_at ON vnc_sessions(expires_at);

-- Update timestamp trigger
CREATE OR REPLACE FUNCTION update_vnc_sessions_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER vnc_sessions_updated_at
    BEFORE UPDATE ON vnc_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_vnc_sessions_updated_at();

EOF

    # Copy and execute migration on server
    scp /tmp/vnc_migration.sql ${USER}@${SERVER}:/tmp/
    ssh ${USER}@${SERVER} "sudo -u postgres psql -d orizon -f /tmp/vnc_migration.sql"

    print_success "Database migration completed"
fi

###############################################################################
# STEP 3: DEPLOY BACKEND CODE
###############################################################################

if [[ "$MODE" == "full" || "$MODE" == "backend" ]]; then
    print_header "STEP 3: Deploy Backend Code"

    # Create deployment directory structure on server
    ssh ${USER}@${SERVER} "mkdir -p /opt/orizon/backend/{models,schemas,services,api/v1/endpoints}"

    # Upload backend files
    print_info "Uploading backend models..."
    scp backend/app/models/vnc_session.py ${USER}@${SERVER}:/opt/orizon/backend/models/

    print_info "Uploading backend schemas..."
    scp backend/app/schemas/vnc.py ${USER}@${SERVER}:/opt/orizon/backend/schemas/

    print_info "Uploading backend services..."
    scp backend/app/services/vnc_service.py ${USER}@${SERVER}:/opt/orizon/backend/services/

    print_info "Uploading backend endpoints..."
    scp backend/app/api/v1/endpoints/vnc.py ${USER}@${SERVER}:/opt/orizon/backend/api/v1/endpoints/

    # Update __init__ files
    scp backend/app/models/__init__.py ${USER}@${SERVER}:/opt/orizon/backend/models/
    scp backend/app/api/v1/router.py ${USER}@${SERVER}:/opt/orizon/backend/api/v1/

    # Restart backend service
    ssh ${USER}@${SERVER} "sudo systemctl restart orizon-backend"

    print_success "Backend code deployed"
fi

###############################################################################
# STEP 4: DEPLOY VNC GATEWAY
###############################################################################

if [[ "$MODE" == "full" || "$MODE" == "gateway" ]]; then
    print_header "STEP 4: Deploy VNC Gateway"

    # Create VNC Gateway directory
    ssh ${USER}@${SERVER} "mkdir -p /opt/orizon/vnc_gateway/logs"

    # Upload VNC Gateway files
    scp services/vnc_gateway/vnc_gateway.py ${USER}@${SERVER}:/opt/orizon/vnc_gateway/
    scp services/vnc_gateway/requirements.txt ${USER}@${SERVER}:/opt/orizon/vnc_gateway/

    # Install dependencies
    ssh ${USER}@${SERVER} "cd /opt/orizon/vnc_gateway && pip3 install -r requirements.txt"

    # Create systemd service
    cat > /tmp/orizon-vnc-gateway.service <<'EOF'
[Unit]
Description=Orizon VNC Gateway Service
After=network.target orizon-backend.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/orizon/vnc_gateway
Environment="JWT_SECRET_KEY=your-secret-key-change-me"
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

    scp /tmp/orizon-vnc-gateway.service ${USER}@${SERVER}:/tmp/
    ssh ${USER}@${SERVER} "sudo mv /tmp/orizon-vnc-gateway.service /etc/systemd/system/"
    ssh ${USER}@${SERVER} "sudo systemctl daemon-reload"
    ssh ${USER}@${SERVER} "sudo systemctl enable orizon-vnc-gateway"
    ssh ${USER}@${SERVER} "sudo systemctl restart orizon-vnc-gateway"

    print_success "VNC Gateway deployed"
fi

###############################################################################
# STEP 5: DEPLOY EDGE AGENT
###############################################################################

if [[ "$MODE" == "full" || "$MODE" == "agent" ]]; then
    print_header "STEP 5: Deploy Edge Agent with VNC Support"

    # Upload agent files
    ssh ${USER}@${SERVER} "mkdir -p /opt/orizon/agents"

    scp agents/vnc_tunnel_handler.py ${USER}@${SERVER}:/opt/orizon/agents/
    scp agents/orizon_agent_vnc.py ${USER}@${SERVER}:/opt/orizon/agents/

    # Install dependencies
    ssh ${USER}@${SERVER} "pip3 install websockets psutil"

    print_success "Edge Agent VNC support deployed"
fi

###############################################################################
# STEP 6: DEPLOY FRONTEND
###############################################################################

if [[ "$MODE" == "full" || "$MODE" == "frontend" ]]; then
    print_header "STEP 6: Deploy Frontend"

    # Build frontend locally
    print_info "Building frontend..."
    cd frontend
    npm install @novnc/novnc
    npm run build
    cd ..

    # Upload frontend build
    print_info "Uploading frontend build..."
    ssh ${USER}@${SERVER} "mkdir -p /var/www/orizon-ztc"
    scp -r frontend/dist/* ${USER}@${SERVER}:/var/www/orizon-ztc/

    # Reload Nginx
    ssh ${USER}@${SERVER} "sudo systemctl reload nginx"

    print_success "Frontend deployed"
fi

###############################################################################
# STEP 7: CONFIGURE FIREWALL
###############################################################################

print_header "STEP 7: Configure Firewall"

# Open VNC Gateway port
ssh ${USER}@${SERVER} "sudo ufw allow 6080/tcp comment 'VNC Gateway'"

# Open tunnel port range
ssh ${USER}@${SERVER} "sudo ufw allow 40000:59999/tcp comment 'VNC Tunnel Ports'"

print_success "Firewall configured"

###############################################################################
# STEP 8: VERIFICATION
###############################################################################

print_header "STEP 8: Verification"

# Check services status
print_info "Checking service status..."

ssh ${USER}@${SERVER} "sudo systemctl status orizon-backend --no-pager | head -3"
ssh ${USER}@${SERVER} "sudo systemctl status orizon-vnc-gateway --no-pager | head -3"

# Test endpoints
print_info "Testing API endpoints..."

HTTP_CODE=$(ssh ${USER}@${SERVER} "curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/api/v1/health")
if [ "$HTTP_CODE" == "200" ]; then
    print_success "Backend API is responding"
else
    print_error "Backend API is not responding (HTTP $HTTP_CODE)"
fi

# Test VNC Gateway
VNC_CODE=$(ssh ${USER}@${SERVER} "curl -s -o /dev/null -w '%{http_code}' http://localhost:6080")
if [ "$VNC_CODE" == "426" ] || [ "$VNC_CODE" == "400" ]; then
    print_success "VNC Gateway is running"
else
    print_warning "VNC Gateway might not be running (HTTP $VNC_CODE)"
fi

###############################################################################
# DEPLOYMENT COMPLETE
###############################################################################

print_header "DEPLOYMENT COMPLETE"

echo ""
print_success "VNC Remote Desktop feature deployed successfully!"
echo ""
echo "Next steps:"
echo "  1. Update frontend environment variables (VITE_VNC_GATEWAY_URL)"
echo "  2. Test VNC session creation from frontend"
echo "  3. Install VNC server on edge nodes (vncserver)"
echo "  4. Deploy edge agent with VNC support to edge nodes"
echo ""
echo "VNC Gateway WebSocket URL: wss://$SERVER:6080"
echo "API Documentation: https://$SERVER/docs"
echo ""

print_info "Checking logs:"
echo "  Backend: ssh ${USER}@${SERVER} 'sudo journalctl -u orizon-backend -f'"
echo "  VNC Gateway: ssh ${USER}@${SERVER} 'sudo journalctl -u orizon-vnc-gateway -f'"
echo ""

exit 0
