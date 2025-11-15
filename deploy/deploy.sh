#!/bin/bash
###############################################################################
# Orizon Zero Trust Connect - Deployment Script
# For: Marco @ Syneto/Orizon
# Server: 46.101.189.126
###############################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
SERVER="46.101.189.126"
SERVER_USER="root"
APP_NAME="orizon-ztc"
APP_DIR="/opt/${APP_NAME}"
LOCAL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}   Orizon Zero Trust Connect - Deployment${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Check if SSH key exists
if [ ! -f ~/.ssh/id_rsa ] && [ ! -f ~/.ssh/id_ed25519 ]; then
    echo -e "${RED}✗ SSH key not found. Please configure SSH access to ${SERVER}${NC}"
    exit 1
fi

echo -e "${GREEN}✓ SSH key found${NC}"

# Test SSH connection
echo -e "\n${YELLOW}[1/8] Testing SSH connection to ${SERVER}...${NC}"
if ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no ${SERVER_USER}@${SERVER} "echo 'SSH OK'" &>/dev/null; then
    echo -e "${GREEN}✓ SSH connection successful${NC}"
else
    echo -e "${RED}✗ Cannot connect to ${SERVER}. Check your SSH configuration.${NC}"
    exit 1
fi

# Step 1: Upload installation script
echo -e "\n${YELLOW}[2/8] Uploading installation script...${NC}"
scp -o StrictHostKeyChecking=no ${LOCAL_DIR}/deploy/install.sh ${SERVER_USER}@${SERVER}:/tmp/
ssh ${SERVER_USER}@${SERVER} "chmod +x /tmp/install.sh"
echo -e "${GREEN}✓ Installation script uploaded${NC}"

# Step 2: Run installation on server
echo -e "\n${YELLOW}[3/8] Running installation on server...${NC}"
ssh ${SERVER_USER}@${SERVER} "/tmp/install.sh"
echo -e "${GREEN}✓ Installation completed${NC}"

# Step 3: Deploy backend
echo -e "\n${YELLOW}[4/8] Deploying backend...${NC}"

# Create tarball of backend (exclude venv, __pycache__, etc.)
cd ${LOCAL_DIR}/backend
tar --exclude='venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.pytest_cache' \
    --exclude='.env' \
    -czf /tmp/backend.tar.gz .

# Upload backend
scp /tmp/backend.tar.gz ${SERVER_USER}@${SERVER}:/tmp/

# Extract on server
ssh ${SERVER_USER}@${SERVER} "
    cd ${APP_DIR}/backend && \
    tar -xzf /tmp/backend.tar.gz && \
    chown -R orizon:orizon ${APP_DIR}/backend && \
    rm /tmp/backend.tar.gz
"

# Clean up local tarball
rm /tmp/backend.tar.gz

echo -e "${GREEN}✓ Backend deployed${NC}"

# Step 4: Setup Python virtual environment and install dependencies
echo -e "\n${YELLOW}[5/8] Installing backend dependencies...${NC}"
ssh ${SERVER_USER}@${SERVER} "
    cd ${APP_DIR}/backend && \
    python3.11 -m venv venv && \
    venv/bin/pip install --upgrade pip && \
    venv/bin/pip install -r requirements.txt && \
    chown -R orizon:orizon venv
"
echo -e "${GREEN}✓ Backend dependencies installed${NC}"

# Step 5: Run database migrations
echo -e "\n${YELLOW}[6/8] Running database migrations...${NC}"
ssh ${SERVER_USER}@${SERVER} "
    cd ${APP_DIR}/backend && \
    sudo -u orizon venv/bin/alembic upgrade head
"
echo -e "${GREEN}✓ Database migrations completed${NC}"

# Step 6: Deploy frontend
echo -e "\n${YELLOW}[7/8] Deploying frontend...${NC}"

# Build frontend locally
cd ${LOCAL_DIR}/frontend
echo -e "${BLUE}→ Building frontend...${NC}"

# Set production API URL
export VITE_API_BASE_URL="http://${SERVER}/api/v1"
export VITE_WS_URL="ws://${SERVER}/ws"

npm run build

# Create tarball of dist
tar -czf /tmp/frontend.tar.gz -C dist .

# Upload frontend
scp /tmp/frontend.tar.gz ${SERVER_USER}@${SERVER}:/tmp/

# Extract on server
ssh ${SERVER_USER}@${SERVER} "
    mkdir -p ${APP_DIR}/frontend/dist && \
    cd ${APP_DIR}/frontend/dist && \
    tar -xzf /tmp/frontend.tar.gz && \
    chown -R www-data:www-data ${APP_DIR}/frontend/dist && \
    rm /tmp/frontend.tar.gz
"

# Clean up local tarball
rm /tmp/frontend.tar.gz

echo -e "${GREEN}✓ Frontend deployed${NC}"

# Step 7: Start services
echo -e "\n${YELLOW}[8/8] Starting services...${NC}"
ssh ${SERVER_USER}@${SERVER} "
    systemctl enable ${APP_NAME}-backend && \
    systemctl restart ${APP_NAME}-backend && \
    systemctl restart nginx
"

# Wait for backend to start
echo -e "${BLUE}→ Waiting for backend to start...${NC}"
sleep 5

# Check service status
ssh ${SERVER_USER}@${SERVER} "systemctl status ${APP_NAME}-backend --no-pager" || true

echo -e "${GREEN}✓ Services started${NC}"

# Final message
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✓ Deployment Complete!${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}Application URLs:${NC}"
echo -e "  Frontend: ${GREEN}http://${SERVER}${NC}"
echo -e "  API Docs: ${GREEN}http://${SERVER}/api/docs${NC}"
echo -e "  Metrics:  ${GREEN}http://${SERVER}/metrics${NC}"
echo ""
echo -e "${YELLOW}Useful Commands:${NC}"
echo -e "  View logs:    ${BLUE}ssh ${SERVER_USER}@${SERVER} 'journalctl -u ${APP_NAME}-backend -f'${NC}"
echo -e "  Restart:      ${BLUE}ssh ${SERVER_USER}@${SERVER} 'systemctl restart ${APP_NAME}-backend'${NC}"
echo -e "  Check status: ${BLUE}ssh ${SERVER_USER}@${SERVER} 'systemctl status ${APP_NAME}-backend'${NC}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo -e "  1. Test the application at http://${SERVER}"
echo -e "  2. Create first admin user via API"
echo -e "  3. Configure SSL: ssh ${SERVER_USER}@${SERVER} 'certbot --nginx -d your-domain.com'"
echo ""
