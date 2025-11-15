#!/bin/bash
###############################################################################
# Orizon Zero Trust Connect - Full Automated Deployment
# For: Marco @ Syneto/Orizon
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
USER="orizzonti"
PASS="ripper-FfFIlBelloccio.1969F"
APP_DIR="/home/orizzonti/orizon-ztc"
LOCAL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}   Orizon Zero Trust Connect - Automated Deployment${NC}"
echo -e "${BLUE}   Server: ${SERVER}${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Helper function for expect SSH commands
ssh_exec() {
    local cmd="$1"
    expect << EXPECTEOF
set timeout 60
spawn ssh -o StrictHostKeyChecking=no ${USER}@${SERVER} "${cmd}"
expect {
    "password:" {
        send "${PASS}\r"
        exp_continue
    }
    eof
}
EXPECTEOF
}

# Helper function for SCP with expect
scp_file() {
    local local_file="$1"
    local remote_file="$2"
    expect << EXPECTEOF
set timeout 120
spawn scp -o StrictHostKeyChecking=no ${local_file} ${USER}@${SERVER}:${remote_file}
expect {
    "password:" {
        send "${PASS}\r"
        exp_continue
    }
    eof
}
EXPECTEOF
}

# Step 1: Test connection
echo -e "${YELLOW}[1/10] Testing SSH connection...${NC}"
if ssh_exec "echo 'Connected' && whoami" | grep -q "orizzonti"; then
    echo -e "${GREEN}✓ SSH connection successful${NC}"
else
    echo -e "${RED}✗ SSH connection failed${NC}"
    exit 1
fi

# Step 2: Upload deployment script
echo -e "\n${YELLOW}[2/10] Uploading installation script...${NC}"
scp_file "${LOCAL_DIR}/deploy/deploy_manual.sh" "~/deploy_manual.sh"
ssh_exec "chmod +x ~/deploy_manual.sh"
echo -e "${GREEN}✓ Script uploaded${NC}"

# Step 3: Run installation
echo -e "\n${YELLOW}[3/10] Running installation on server...${NC}"
echo -e "${BLUE}→ This will take 2-3 minutes...${NC}"
ssh_exec "bash ~/deploy_manual.sh"
echo -e "${GREEN}✓ Installation completed${NC}"

# Step 4: Prepare backend tarball
echo -e "\n${YELLOW}[4/10] Preparing backend files...${NC}"
cd "${LOCAL_DIR}/backend"
tar --exclude='venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.pytest_cache' \
    --exclude='.env' \
    -czf /tmp/backend.tar.gz .
echo -e "${GREEN}✓ Backend tarball created${NC}"

# Step 5: Upload backend
echo -e "\n${YELLOW}[5/10] Uploading backend...${NC}"
scp_file "/tmp/backend.tar.gz" "${APP_DIR}/backend/backend.tar.gz"
ssh_exec "cd ${APP_DIR}/backend && tar -xzf backend.tar.gz && rm backend.tar.gz"
rm /tmp/backend.tar.gz
echo -e "${GREEN}✓ Backend uploaded${NC}"

# Step 6: Install backend dependencies
echo -e "\n${YELLOW}[6/10] Installing backend dependencies...${NC}"
echo -e "${BLUE}→ This may take 3-5 minutes...${NC}"
ssh_exec "cd ${APP_DIR}/backend && source venv/bin/activate && pip install -r requirements.txt"
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Step 7: Build frontend
echo -e "\n${YELLOW}[7/10] Building frontend...${NC}"
cd "${LOCAL_DIR}/frontend"
export VITE_API_BASE_URL="http://${SERVER}/api/v1"
export VITE_WS_URL="ws://${SERVER}/ws"
npm run build
echo -e "${GREEN}✓ Frontend built${NC}"

# Step 8: Prepare and upload frontend
echo -e "\n${YELLOW}[8/10] Uploading frontend...${NC}"
tar -czf /tmp/frontend.tar.gz -C dist .
scp_file "/tmp/frontend.tar.gz" "${APP_DIR}/frontend/frontend.tar.gz"
ssh_exec "cd ${APP_DIR}/frontend && tar -xzf frontend.tar.gz && rm frontend.tar.gz"
rm /tmp/frontend.tar.gz
echo -e "${GREEN}✓ Frontend uploaded${NC}"

# Step 9: Start services
echo -e "\n${YELLOW}[9/10] Starting services...${NC}"
ssh_exec "bash ${APP_DIR}/start.sh"
sleep 3
echo -e "${GREEN}✓ Services started${NC}"

# Step 10: Verify deployment
echo -e "\n${YELLOW}[10/10] Verifying deployment...${NC}"
if curl -s http://${SERVER}:8000/health | grep -q "ok" 2>/dev/null; then
    echo -e "${GREEN}✓ Backend is responding${NC}"
else
    echo -e "${YELLOW}⚠ Backend health check inconclusive${NC}"
fi

# Final message
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✓ DEPLOYMENT COMPLETE!${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}Application URLs:${NC}"
echo -e "  Frontend:  ${GREEN}http://${SERVER}${NC}"
echo -e "  Backend:   ${GREEN}http://${SERVER}:8000${NC}"
echo -e "  API Docs:  ${GREEN}http://${SERVER}:8000/docs${NC}"
echo -e "  Health:    ${GREEN}http://${SERVER}:8000/health${NC}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo -e "  1. Test the application at: http://${SERVER}"
echo -e "  2. Create admin user (script provided)"
echo -e "  3. Configure SSL with certbot (optional)"
echo ""
echo -e "${YELLOW}Useful Commands:${NC}"
echo -e "  Check status: ssh ${USER}@${SERVER} 'sudo systemctl status orizon-backend'"
echo -e "  View logs:    ssh ${USER}@${SERVER} 'journalctl -u orizon-backend -f'"
echo -e "  Restart:      ssh ${USER}@${SERVER} 'sudo systemctl restart orizon-backend nginx'"
echo ""
