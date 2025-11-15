#!/bin/bash
###############################################################################
# Orizon Zero Trust Connect - Installation Script
# For: Marco @ Syneto/Orizon
# Server: 46.101.189.126
###############################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="orizon-ztc"
APP_DIR="/opt/${APP_NAME}"
BACKEND_DIR="${APP_DIR}/backend"
FRONTEND_DIR="${APP_DIR}/frontend"
VENV_DIR="${BACKEND_DIR}/venv"
NGINX_CONF="/etc/nginx/sites-available/${APP_NAME}"
DOMAIN="46.101.189.126"  # Can be changed to custom domain later

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}   Orizon Zero Trust Connect - Installation${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}✗ This script must be run as root (use sudo)${NC}"
   exit 1
fi

echo -e "${GREEN}✓ Running as root${NC}"

# Step 1: Update system packages
echo -e "\n${YELLOW}[1/10] Updating system packages...${NC}"
apt-get update -qq
apt-get upgrade -y -qq
echo -e "${GREEN}✓ System updated${NC}"

# Step 2: Install dependencies
echo -e "\n${YELLOW}[2/10] Installing system dependencies...${NC}"
apt-get install -y -qq \
    python3.11 \
    python3.11-venv \
    python3-pip \
    nginx \
    redis-server \
    postgresql-15 \
    postgresql-contrib \
    mongodb-org \
    git \
    curl \
    build-essential \
    libpq-dev \
    supervisor \
    certbot \
    python3-certbot-nginx

echo -e "${GREEN}✓ Dependencies installed${NC}"

# Step 3: Create application directory
echo -e "\n${YELLOW}[3/10] Creating application directory...${NC}"
mkdir -p ${APP_DIR}
mkdir -p ${BACKEND_DIR}
mkdir -p ${FRONTEND_DIR}
mkdir -p /var/log/${APP_NAME}

echo -e "${GREEN}✓ Directory structure created${NC}"

# Step 4: Create orizon user
echo -e "\n${YELLOW}[4/10] Creating application user...${NC}"
if ! id "orizon" &>/dev/null; then
    useradd -r -s /bin/bash -d ${APP_DIR} -m orizon
    echo -e "${GREEN}✓ User 'orizon' created${NC}"
else
    echo -e "${BLUE}→ User 'orizon' already exists${NC}"
fi

# Step 5: Setup PostgreSQL
echo -e "\n${YELLOW}[5/10] Configuring PostgreSQL...${NC}"
sudo -u postgres psql -c "CREATE DATABASE orizon_ztc;" 2>/dev/null || echo "Database already exists"
sudo -u postgres psql -c "CREATE USER orizon WITH PASSWORD 'OrizonSecure2025!';" 2>/dev/null || echo "User already exists"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE orizon_ztc TO orizon;"
sudo -u postgres psql -c "ALTER USER orizon WITH SUPERUSER;"

echo -e "${GREEN}✓ PostgreSQL configured${NC}"

# Step 6: Setup Redis
echo -e "\n${YELLOW}[6/10] Configuring Redis...${NC}"
systemctl enable redis-server
systemctl start redis-server

# Configure Redis for rate limiting
cat > /etc/redis/redis.conf.d/orizon.conf << 'EOF'
# Orizon Zero Trust Connect - Redis Configuration
maxmemory 256mb
maxmemory-policy allkeys-lru
bind 127.0.0.1
protected-mode yes
EOF

systemctl restart redis-server
echo -e "${GREEN}✓ Redis configured${NC}"

# Step 7: Setup MongoDB
echo -e "\n${YELLOW}[7/10] Configuring MongoDB...${NC}"
systemctl enable mongod
systemctl start mongod

# Create MongoDB database and user
mongo --eval "
use orizon_audit;
db.createUser({
  user: 'orizon',
  pwd: 'OrizonSecure2025!',
  roles: [{ role: 'readWrite', db: 'orizon_audit' }]
});
" 2>/dev/null || echo "MongoDB user already exists"

echo -e "${GREEN}✓ MongoDB configured${NC}"

# Step 8: Create environment file
echo -e "\n${YELLOW}[8/10] Creating environment configuration...${NC}"
cat > ${BACKEND_DIR}/.env << EOF
# Orizon Zero Trust Connect - Environment Configuration
# Generated: $(date)

# Database Configuration
DATABASE_URL=postgresql://orizon:OrizonSecure2025!@localhost:5432/orizon_ztc
REDIS_URL=redis://localhost:6379/0
MONGODB_URL=mongodb://orizon:OrizonSecure2025!@localhost:27017/orizon_audit

# Security
SECRET_KEY=$(openssl rand -hex 32)
JWT_SECRET=$(openssl rand -hex 32)
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=30

# CORS
ALLOWED_ORIGINS=http://${DOMAIN},https://${DOMAIN},http://localhost:3000

# Server
HOST=0.0.0.0
PORT=8000
DEBUG=false

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/${APP_NAME}/backend.log

# Email (configure later if needed)
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=noreply@orizon.syneto.net
EOF

chmod 600 ${BACKEND_DIR}/.env
chown orizon:orizon ${BACKEND_DIR}/.env

echo -e "${GREEN}✓ Environment configured${NC}"

# Step 9: Setup Nginx
echo -e "\n${YELLOW}[9/10] Configuring Nginx...${NC}"
cat > ${NGINX_CONF} << 'NGINXEOF'
# Orizon Zero Trust Connect - Nginx Configuration

upstream backend {
    server 127.0.0.1:8000;
    keepalive 64;
}

# HTTP -> HTTPS redirect (uncomment when SSL is configured)
# server {
#     listen 80;
#     listen [::]:80;
#     server_name _;
#     return 301 https://$host$request_uri;
# }

server {
    listen 80;
    listen [::]:80;
    server_name _;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;

    # Frontend (static files)
    root /opt/orizon-ztc/frontend/dist;
    index index.html;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/json application/xml+rss;

    # Frontend routes (SPA)
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API proxy
    location /api/ {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # WebSocket endpoint
    location /ws {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket timeouts
        proxy_connect_timeout 7d;
        proxy_send_timeout 7d;
        proxy_read_timeout 7d;
    }

    # Prometheus metrics (optional, restrict access)
    location /metrics {
        proxy_pass http://backend;
        # allow 127.0.0.1;
        # deny all;
    }

    # Static assets cache
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Logs
    access_log /var/log/nginx/orizon-ztc-access.log;
    error_log /var/log/nginx/orizon-ztc-error.log;
}
NGINXEOF

# Enable site
ln -sf ${NGINX_CONF} /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Test nginx configuration
nginx -t

systemctl enable nginx
systemctl restart nginx

echo -e "${GREEN}✓ Nginx configured${NC}"

# Step 10: Create systemd services
echo -e "\n${YELLOW}[10/10] Creating systemd services...${NC}"

# Backend service
cat > /etc/systemd/system/${APP_NAME}-backend.service << 'SYSTEMDEOF'
[Unit]
Description=Orizon Zero Trust Connect - Backend API
After=network.target postgresql.service redis-server.service mongodb.service
Wants=postgresql.service redis-server.service mongodb.service

[Service]
Type=simple
User=orizon
Group=orizon
WorkingDirectory=/opt/orizon-ztc/backend
Environment="PATH=/opt/orizon-ztc/backend/venv/bin"
EnvironmentFile=/opt/orizon-ztc/backend/.env
ExecStart=/opt/orizon-ztc/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=10
StandardOutput=append:/var/log/orizon-ztc/backend.log
StandardError=append:/var/log/orizon-ztc/backend-error.log

# Security
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/log/orizon-ztc /opt/orizon-ztc/backend

[Install]
WantedBy=multi-user.target
SYSTEMDEOF

# Reload systemd
systemctl daemon-reload

echo -e "${GREEN}✓ Systemd services created${NC}"

# Final message
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✓ Installation Complete!${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo -e "  1. Deploy application code to ${APP_DIR}"
echo -e "  2. Run database migrations: cd ${BACKEND_DIR} && venv/bin/alembic upgrade head"
echo -e "  3. Start services: systemctl start ${APP_NAME}-backend"
echo -e "  4. Check logs: journalctl -u ${APP_NAME}-backend -f"
echo ""
echo -e "${YELLOW}Database Credentials:${NC}"
echo -e "  PostgreSQL: orizon / OrizonSecure2025!"
echo -e "  MongoDB: orizon / OrizonSecure2025!"
echo ""
echo -e "${YELLOW}Access:${NC}"
echo -e "  Frontend: http://${DOMAIN}"
echo -e "  API: http://${DOMAIN}/api"
echo -e "  Metrics: http://${DOMAIN}/metrics"
echo ""
echo -e "${BLUE}For SSL/HTTPS, run: certbot --nginx -d your-domain.com${NC}"
echo ""
