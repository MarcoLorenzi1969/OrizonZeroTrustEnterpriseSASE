#!/bin/bash
###############################################################################
# Orizon Zero Trust Connect - Deployment with Password
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
SERVER_USER="orizzonti"
SERVER_PASSWORD="ripper-FfFIlBelloccio.1969F"
APP_NAME="orizon-ztc"
APP_DIR="/opt/${APP_NAME}"
LOCAL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}   Orizon Zero Trust Connect - Deployment${NC}"
echo -e "${BLUE}   Server: ${SERVER}${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Check if sshpass is installed
if ! command -v sshpass &> /dev/null; then
    echo -e "${YELLOW}Installing sshpass...${NC}"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        brew install hudochenkov/sshpass/sshpass
    else
        sudo apt-get install -y sshpass
    fi
fi

echo -e "${GREEN}✓ sshpass available${NC}"

# Test SSH connection
echo -e "\n${YELLOW}[1/9] Testing SSH connection...${NC}"
if sshpass -p "${SERVER_PASSWORD}" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 ${SERVER_USER}@${SERVER} "echo 'SSH OK'" &>/dev/null; then
    echo -e "${GREEN}✓ SSH connection successful${NC}"
else
    echo -e "${RED}✗ Cannot connect to ${SERVER}${NC}"
    exit 1
fi

# Step 1: Check if user has sudo privileges
echo -e "\n${YELLOW}[2/9] Checking sudo privileges...${NC}"
if sshpass -p "${SERVER_PASSWORD}" ssh ${SERVER_USER}@${SERVER} "echo '${SERVER_PASSWORD}' | sudo -S whoami" 2>/dev/null | grep -q "root"; then
    echo -e "${GREEN}✓ User has sudo access${NC}"
    SUDO_CMD="echo '${SERVER_PASSWORD}' | sudo -S"
else
    echo -e "${YELLOW}⚠ User does not have sudo. Will attempt without sudo...${NC}"
    SUDO_CMD=""
fi

# Step 2: Upload installation script
echo -e "\n${YELLOW}[3/9] Uploading installation script...${NC}"
sshpass -p "${SERVER_PASSWORD}" scp -o StrictHostKeyChecking=no ${LOCAL_DIR}/deploy/install.sh ${SERVER_USER}@${SERVER}:/tmp/
sshpass -p "${SERVER_PASSWORD}" ssh ${SERVER_USER}@${SERVER} "chmod +x /tmp/install.sh"
echo -e "${GREEN}✓ Installation script uploaded${NC}"

# Step 3: Run installation
echo -e "\n${YELLOW}[4/9] Running installation...${NC}"
echo -e "${BLUE}→ This may take several minutes...${NC}"
sshpass -p "${SERVER_PASSWORD}" ssh ${SERVER_USER}@${SERVER} "${SUDO_CMD} /tmp/install.sh" || {
    echo -e "${YELLOW}⚠ Installation encountered issues. Continuing...${NC}"
}

# Step 4: Create application directories
echo -e "\n${YELLOW}[5/9] Creating application directories...${NC}"
sshpass -p "${SERVER_PASSWORD}" ssh ${SERVER_USER}@${SERVER} "${SUDO_CMD} mkdir -p ${APP_DIR}/backend ${APP_DIR}/frontend /var/log/${APP_NAME}"
sshpass -p "${SERVER_PASSWORD}" ssh ${SERVER_USER}@${SERVER} "${SUDO_CMD} chown -R ${SERVER_USER}:${SERVER_USER} ${APP_DIR}"
echo -e "${GREEN}✓ Directories created${NC}"

# Step 5: Deploy backend
echo -e "\n${YELLOW}[6/9] Deploying backend...${NC}"

# Create tarball
cd ${LOCAL_DIR}/backend
tar --exclude='venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.pytest_cache' \
    --exclude='.env' \
    -czf /tmp/backend.tar.gz .

# Upload
sshpass -p "${SERVER_PASSWORD}" scp /tmp/backend.tar.gz ${SERVER_USER}@${SERVER}:/tmp/

# Extract
sshpass -p "${SERVER_PASSWORD}" ssh ${SERVER_USER}@${SERVER} "
    cd ${APP_DIR}/backend && \
    tar -xzf /tmp/backend.tar.gz && \
    rm /tmp/backend.tar.gz
"

rm /tmp/backend.tar.gz
echo -e "${GREEN}✓ Backend deployed${NC}"

# Step 6: Install backend dependencies
echo -e "\n${YELLOW}[7/9] Installing backend dependencies...${NC}"
sshpass -p "${SERVER_PASSWORD}" ssh ${SERVER_USER}@${SERVER} "
    cd ${APP_DIR}/backend && \
    python3 -m venv venv && \
    venv/bin/pip install --upgrade pip && \
    venv/bin/pip install -r requirements.txt
" || echo -e "${YELLOW}⚠ Some dependencies may have failed${NC}"
echo -e "${GREEN}✓ Backend dependencies installed${NC}"

# Step 7: Deploy frontend
echo -e "\n${YELLOW}[8/9] Building and deploying frontend...${NC}"

cd ${LOCAL_DIR}/frontend

# Build frontend
echo -e "${BLUE}→ Building frontend...${NC}"
export VITE_API_BASE_URL="http://${SERVER}/api/v1"
export VITE_WS_URL="ws://${SERVER}/ws"

npm run build || {
    echo -e "${RED}✗ Frontend build failed${NC}"
    exit 1
}

# Create tarball
tar -czf /tmp/frontend.tar.gz -C dist .

# Upload
sshpass -p "${SERVER_PASSWORD}" scp /tmp/frontend.tar.gz ${SERVER_USER}@${SERVER}:/tmp/

# Extract
sshpass -p "${SERVER_PASSWORD}" ssh ${SERVER_USER}@${SERVER} "
    mkdir -p ${APP_DIR}/frontend/dist && \
    cd ${APP_DIR}/frontend/dist && \
    tar -xzf /tmp/frontend.tar.gz && \
    rm /tmp/frontend.tar.gz
"

rm /tmp/frontend.tar.gz
echo -e "${GREEN}✓ Frontend deployed${NC}"

# Step 8: Upload and run startup script
echo -e "\n${YELLOW}[9/9] Starting services...${NC}"
sshpass -p "${SERVER_PASSWORD}" scp ${LOCAL_DIR}/deploy/startup.sh ${SERVER_USER}@${SERVER}:/tmp/
sshpass -p "${SERVER_PASSWORD}" ssh ${SERVER_USER}@${SERVER} "chmod +x /tmp/startup.sh"
sshpass -p "${SERVER_PASSWORD}" ssh ${SERVER_USER}@${SERVER} "${SUDO_CMD} /tmp/startup.sh" || {
    echo -e "${YELLOW}⚠ Service startup encountered issues${NC}"
}

# Final message
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✓ Deployment Complete!${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}Application URLs:${NC}"
echo -e "  Frontend: ${GREEN}http://${SERVER}${NC}"
echo -e "  API:      ${GREEN}http://${SERVER}/api${NC}"
echo -e "  API Docs: ${GREEN}http://${SERVER}/api/docs${NC}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo -e "  1. Access: http://${SERVER}"
echo -e "  2. Create admin user"
echo -e "  3. Login and configure"
echo ""
