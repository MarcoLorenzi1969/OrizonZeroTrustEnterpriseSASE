#!/bin/bash
###############################################################################
# Orizon Zero Trust Connect - Single Script Deployment
# For: Marco @ Syneto/Orizon
#
# INSTRUCTIONS:
# 1. SSH to server: ssh orizzonti@46.101.189.126
# 2. Run: curl -sSL https://raw.githubusercontent.com/.../deploy.sh | bash
# OR copy this entire script and run: bash
###############################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}   Orizon Zero Trust Connect - Installation${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Configuration
APP_DIR="$HOME/orizon-ztc"
BACKEND_PORT=8000

# Step 1: Update system
echo -e "${YELLOW}[1/8] Updating system...${NC}"
sudo apt-get update -qq
sudo apt-get install -y python3.11 python3.11-venv python3-pip nginx git curl build-essential nodejs npm
echo -e "${GREEN}✓ System updated${NC}"

# Step 2: Create directories
echo -e "\n${YELLOW}[2/8] Creating directories...${NC}"
mkdir -p ${APP_DIR}/{backend,frontend/dist}
mkdir -p ${APP_DIR}/logs
echo -e "${GREEN}✓ Directories created${NC}"

# Step 3: Setup Python environment
echo -e "\n${YELLOW}[3/8] Setting up Python environment...${NC}"
cd ${APP_DIR}/backend
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip -q
pip install fastapi uvicorn[standard] sqlalchemy asyncpg redis pymongo \
    python-jose[cryptography] passlib[argon2] python-multipart \
    pyotp qrcode pillow python-dotenv aiofiles httpx -q
echo -e "${GREEN}✓ Python environment ready${NC}"

# Step 4: Create environment file
echo -e "\n${YELLOW}[4/8] Creating configuration...${NC}"
cat > ${APP_DIR}/backend/.env << 'ENVEOF'
# Orizon Zero Trust Connect - Configuration
DATABASE_URL=sqlite:///${APP_DIR}/backend/orizon.db
REDIS_URL=redis://localhost:6379/0
MONGODB_URL=mongodb://localhost:27017/orizon_audit

SECRET_KEY=$(openssl rand -hex 32)
JWT_SECRET=$(openssl rand -hex 32)
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=30

ALLOWED_ORIGINS=http://46.101.189.126,https://46.101.189.126

HOST=0.0.0.0
PORT=8000
DEBUG=false
LOG_LEVEL=INFO
ENVEOF

chmod 600 ${APP_DIR}/backend/.env
echo -e "${GREEN}✓ Configuration created${NC}"

# Step 5: Create minimal backend app
echo -e "\n${YELLOW}[5/8] Creating backend application...${NC}"
mkdir -p ${APP_DIR}/backend/app
cat > ${APP_DIR}/backend/app/main.py << 'PYEOF'
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Orizon Zero Trust Connect")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok", "service": "orizon-ztc"}

@app.get("/api/v1/health")
def api_health():
    return {"status": "ok", "version": "1.0.0"}

@app.get("/")
def root():
    return {"message": "Orizon Zero Trust Connect API", "docs": "/docs"}
PYEOF

cat > ${APP_DIR}/backend/app/__init__.py << 'EOF'
# Orizon ZTC Backend
EOF

echo -e "${GREEN}✓ Backend created${NC}"

# Step 6: Create systemd service
echo -e "\n${YELLOW}[6/8] Creating systemd service...${NC}"
sudo tee /etc/systemd/system/orizon-backend.service > /dev/null << SERVICEEOF
[Unit]
Description=Orizon Zero Trust Connect Backend
After=network.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=${APP_DIR}/backend
Environment="PATH=${APP_DIR}/backend/venv/bin"
ExecStart=${APP_DIR}/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port ${BACKEND_PORT}
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SERVICEEOF

sudo systemctl daemon-reload
sudo systemctl enable orizon-backend
sudo systemctl start orizon-backend
echo -e "${GREEN}✓ Backend service started${NC}"

# Step 7: Configure Nginx
echo -e "\n${YELLOW}[7/8] Configuring Nginx...${NC}"
sudo tee /etc/nginx/sites-available/orizon > /dev/null << 'NGINXEOF'
server {
    listen 80 default_server;
    server_name _;

    root /home/orizzonti/orizon-ztc/frontend/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    location /docs {
        proxy_pass http://127.0.0.1:8000/docs;
    }

    location /health {
        proxy_pass http://127.0.0.1:8000/health;
    }
}
NGINXEOF

sudo rm -f /etc/nginx/sites-enabled/default
sudo ln -sf /etc/nginx/sites-available/orizon /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
echo -e "${GREEN}✓ Nginx configured${NC}"

# Step 8: Create placeholder frontend
echo -e "\n${YELLOW}[8/8] Creating placeholder frontend...${NC}"
cat > ${APP_DIR}/frontend/dist/index.html << 'HTMLEOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Orizon Zero Trust Connect</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            color: white;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .container {
            text-align: center;
            padding: 2rem;
        }
        h1 {
            font-size: 3rem;
            margin-bottom: 1rem;
            background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        p {
            font-size: 1.2rem;
            color: #94a3b8;
            margin-bottom: 2rem;
        }
        .status {
            display: inline-block;
            padding: 0.5rem 1rem;
            background: rgba(34, 197, 94, 0.2);
            border: 1px solid #22c55e;
            border-radius: 0.5rem;
            color: #22c55e;
            margin-bottom: 2rem;
        }
        .links {
            display: flex;
            gap: 1rem;
            justify-content: center;
            flex-wrap: wrap;
        }
        a {
            padding: 0.75rem 1.5rem;
            background: #3b82f6;
            color: white;
            text-decoration: none;
            border-radius: 0.5rem;
            transition: all 0.3s;
        }
        a:hover {
            background: #2563eb;
            transform: translateY(-2px);
        }
        .info {
            margin-top: 3rem;
            padding: 1.5rem;
            background: rgba(255,255,255,0.05);
            border-radius: 1rem;
            border: 1px solid rgba(255,255,255,0.1);
        }
        .info p {
            font-size: 0.9rem;
            margin: 0.5rem 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Orizon Zero Trust Connect</h1>
        <p>Enterprise SD-WAN & Zero Trust Platform</p>
        <div class="status">✓ System Running</div>
        <div class="links">
            <a href="/docs">📚 API Documentation</a>
            <a href="/health">🏥 Health Check</a>
        </div>
        <div class="info">
            <p><strong>Status:</strong> Backend installed and running</p>
            <p><strong>Next Step:</strong> Upload full frontend build</p>
            <p><strong>Backend API:</strong> Port 8000</p>
            <p><strong>Version:</strong> 1.0.0</p>
        </div>
    </div>
</body>
</html>
HTMLEOF

echo -e "${GREEN}✓ Placeholder frontend created${NC}"

# Final status check
sleep 2
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✓ INSTALLATION COMPLETE!${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}Application Status:${NC}"
if systemctl is-active --quiet orizon-backend; then
    echo -e "  Backend: ${GREEN}✓ Running${NC}"
else
    echo -e "  Backend: ${RED}✗ Not Running${NC}"
fi
if systemctl is-active --quiet nginx; then
    echo -e "  Nginx:   ${GREEN}✓ Running${NC}"
else
    echo -e "  Nginx:   ${RED}✗ Not Running${NC}"
fi

echo ""
echo -e "${YELLOW}Access URLs:${NC}"
echo -e "  Frontend:    ${GREEN}http://46.101.189.126${NC}"
echo -e "  Backend API: ${GREEN}http://46.101.189.126:8000${NC}"
echo -e "  API Docs:    ${GREEN}http://46.101.189.126/docs${NC}"
echo -e "  Health:      ${GREEN}http://46.101.189.126/health${NC}"
echo ""
echo -e "${YELLOW}Useful Commands:${NC}"
echo -e "  Check status: sudo systemctl status orizon-backend"
echo -e "  View logs:    journalctl -u orizon-backend -f"
echo -e "  Restart:      sudo systemctl restart orizon-backend nginx"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo -e "  1. Test access: curl http://localhost:8000/health"
echo -e "  2. Upload full application code"
echo -e "  3. Create admin user"
echo ""
