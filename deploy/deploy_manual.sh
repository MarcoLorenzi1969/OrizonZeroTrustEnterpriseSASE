#!/bin/bash
###############################################################################
# Orizon Zero Trust Connect - Manual Deployment Script
# For: Marco @ Syneto/Orizon
#
# INSTRUCTIONS:
# 1. SSH to your server: ssh orizzonti@46.101.189.126
# 2. Copy this entire script to the server
# 3. Run: bash deploy_manual.sh
###############################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}   Orizon Zero Trust Connect - Manual Deployment${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Configuration
APP_DIR="/home/orizzonti/orizon-ztc"
BACKEND_PORT=8000

# Step 1: Update system
echo -e "${YELLOW}[1/10] Updating system packages...${NC}"
sudo apt-get update -qq
echo -e "${GREEN}✓ System updated${NC}"

# Step 2: Install dependencies
echo -e "\n${YELLOW}[2/10] Installing dependencies...${NC}"
sudo apt-get install -y python3.11 python3.11-venv python3-pip nginx git curl build-essential

echo -e "${GREEN}✓ Dependencies installed${NC}"

# Step 3: Create application directory
echo -e "\n${YELLOW}[3/10] Creating application directories...${NC}"
mkdir -p ${APP_DIR}/{backend,frontend/dist}
mkdir -p ~/logs

echo -e "${GREEN}✓ Directories created${NC}"

# Step 4: Setup backend environment
echo -e "\n${YELLOW}[4/10] Setting up backend...${NC}"

# You'll need to upload backend files separately
# For now, we create the structure
cd ${APP_DIR}/backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install base packages
pip install --upgrade pip
pip install fastapi uvicorn sqlalchemy asyncpg redis pymongo python-jose[cryptography] passlib[argon2] python-multipart pyotp qrcode

echo -e "${GREEN}✓ Backend environment ready${NC}"

# Step 5: Create environment file
echo -e "\n${YELLOW}[5/10] Creating configuration...${NC}"

cat > ${APP_DIR}/backend/.env << 'ENVEOF'
# Database Configuration (update these!)
DATABASE_URL=postgresql://user:password@localhost:5432/orizon_ztc
REDIS_URL=redis://localhost:6379/0
MONGODB_URL=mongodb://localhost:27017/orizon_audit

# Security
SECRET_KEY=$(openssl rand -hex 32)
JWT_SECRET=$(openssl rand -hex 32)
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Server
HOST=0.0.0.0
PORT=8000
DEBUG=false
ENVEOF

chmod 600 ${APP_DIR}/backend/.env

echo -e "${GREEN}✓ Configuration created${NC}"

# Step 6: Create systemd service
echo -e "\n${YELLOW}[6/10] Creating systemd service...${NC}"

sudo tee /etc/systemd/system/orizon-backend.service > /dev/null << SERVICEEOF
[Unit]
Description=Orizon Zero Trust Connect Backend
After=network.target

[Service]
Type=simple
User=orizzonti
WorkingDirectory=${APP_DIR}/backend
Environment="PATH=${APP_DIR}/backend/venv/bin"
ExecStart=${APP_DIR}/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port ${BACKEND_PORT}
Restart=always

[Install]
WantedBy=multi-user.target
SERVICEEOF

sudo systemctl daemon-reload

echo -e "${GREEN}✓ Service created${NC}"

# Step 7: Configure Nginx
echo -e "\n${YELLOW}[7/10] Configuring Nginx...${NC}"

sudo tee /etc/nginx/sites-available/orizon > /dev/null << 'NGINXEOF'
server {
    listen 80;
    server_name _;

    # Frontend
    root /home/orizzonti/orizon-ztc/frontend/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    # API
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # WebSocket
    location /ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
NGINXEOF

sudo ln -sf /etc/nginx/sites-available/orizon /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t

echo -e "${GREEN}✓ Nginx configured${NC}"

# Step 8: Create upload instructions
echo -e "\n${YELLOW}[8/10] Creating upload instructions...${NC}"

cat > ${APP_DIR}/UPLOAD_FILES.txt << 'UPLOADEOF'
=================================================================
       FILES TO UPLOAD FROM YOUR LOCAL MACHINE
=================================================================

From your Mac, run these commands:

# 1. Upload backend files
cd /Users/marcolorenzi/Windsurf/MCP-Server-LocalModelCyber/OrizonZeroTrustConnect/backend
tar --exclude='venv' --exclude='__pycache__' -czf /tmp/backend.tar.gz .
scp /tmp/backend.tar.gz orizzonti@46.101.189.126:/home/orizzonti/orizon-ztc/backend/
ssh orizzonti@46.101.189.126 "cd /home/orizzonti/orizon-ztc/backend && tar -xzf backend.tar.gz && rm backend.tar.gz"

# 2. Build and upload frontend
cd /Users/marcolorenzi/Windsurf/MCP-Server-LocalModelCyber/OrizonZeroTrustConnect/frontend
export VITE_API_BASE_URL="http://46.101.189.126/api/v1"
export VITE_WS_URL="ws://46.101.189.126/ws"
npm run build
tar -czf /tmp/frontend.tar.gz -C dist .
scp /tmp/frontend.tar.gz orizzonti@46.101.189.126:/home/orizzonti/orizon-ztc/frontend/
ssh orizzonti@46.101.189.126 "cd /home/orizzonti/orizon-ztc/frontend && tar -xzf frontend.tar.gz && rm frontend.tar.gz"

# 3. Install backend dependencies
ssh orizzonti@46.101.189.126 "cd /home/orizzonti/orizon-ztc/backend && venv/bin/pip install -r requirements.txt"

# 4. Start services
ssh orizzonti@46.101.189.126 "sudo systemctl start orizon-backend && sudo systemctl restart nginx"

=================================================================
UPLOADEOF

echo -e "${GREEN}✓ Upload instructions created at: ${APP_DIR}/UPLOAD_FILES.txt${NC}"

# Step 9: Prepare startup
echo -e "\n${YELLOW}[9/10] Preparing startup script...${NC}"

cat > ${APP_DIR}/start.sh << 'STARTEOF'
#!/bin/bash
echo "Starting Orizon Zero Trust Connect..."

# Start backend
sudo systemctl start orizon-backend

# Restart nginx
sudo systemctl restart nginx

# Show status
sleep 2
sudo systemctl status orizon-backend --no-pager

echo ""
echo "✓ Application started!"
echo "  Frontend: http://$(hostname -I | awk '{print $1}')"
echo "  Backend: http://$(hostname -I | awk '{print $1}'):8000"
STARTEOF

chmod +x ${APP_DIR}/start.sh

echo -e "${GREEN}✓ Startup script created${NC}"

# Step 10: Final instructions
echo -e "\n${YELLOW}[10/10] Setup complete!${NC}"

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✓ Server Setup Complete!${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo -e "  1. Read upload instructions: cat ${APP_DIR}/UPLOAD_FILES.txt"
echo -e "  2. Upload backend and frontend files from your Mac"
echo -e "  3. Start application: ${APP_DIR}/start.sh"
echo -e "  4. Access: http://46.101.189.126"
echo ""
echo -e "${YELLOW}Quick Commands:${NC}"
echo -e "  Start:   ${APP_DIR}/start.sh"
echo -e "  Logs:    journalctl -u orizon-backend -f"
echo -e "  Status:  sudo systemctl status orizon-backend"
echo ""
