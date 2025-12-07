#!/bin/bash
# Orizon Zero Trust Connect - Nginx Installer
# For: Marco @ Syneto/Orizon
#
# Usage: ./install.sh <IP_OR_DOMAIN>
# Example: ./install.sh 139.59.149.48

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Banner
echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║          ORIZON ZERO TRUST - NGINX INSTALLER                  ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check arguments
if [ -z "$1" ]; then
    echo -e "${RED}Error: Please provide IP address or domain${NC}"
    echo ""
    echo "Usage: $0 <IP_OR_DOMAIN>"
    echo "Example: $0 139.59.149.48"
    echo "Example: $0 orizon.syneto.eu"
    exit 1
fi

HUB_IP=$1

echo -e "${YELLOW}Installing Nginx for: $HUB_IP${NC}"
echo ""

# Step 1: Install Nginx
echo -e "${GREEN}[1/6] Installing Nginx...${NC}"
if ! command -v nginx &> /dev/null; then
    sudo apt update
    sudo apt install -y nginx
    sudo systemctl enable nginx
else
    echo "Nginx already installed"
fi

# Step 2: Generate SSL Certificate
echo -e "${GREEN}[2/6] Generating SSL certificate...${NC}"
sudo mkdir -p /etc/nginx/ssl
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/nginx/ssl/orizon.key \
    -out /etc/nginx/ssl/orizon.crt \
    -subj "/C=IT/ST=Italy/L=Milan/O=Orizon/OU=Zero Trust/CN=$HUB_IP" \
    -addext "subjectAltName=IP:$HUB_IP,DNS:$HUB_IP" 2>/dev/null
sudo chmod 600 /etc/nginx/ssl/orizon.key
sudo chmod 644 /etc/nginx/ssl/orizon.crt

# Step 3: Install configuration
echo -e "${GREEN}[3/6] Installing Nginx configuration...${NC}"
sed "s/\${HUB_IP}/$HUB_IP/g" "$SCRIPT_DIR/orizon.conf" | sudo tee /etc/nginx/sites-available/orizon > /dev/null

# Step 4: Enable site
echo -e "${GREEN}[4/6] Enabling Orizon site...${NC}"
sudo ln -sf /etc/nginx/sites-available/orizon /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Step 5: Install optional configs
echo -e "${GREEN}[5/6] Installing additional configurations...${NC}"
if [ -d "$SCRIPT_DIR/conf.d" ]; then
    sudo cp "$SCRIPT_DIR/conf.d/gzip.conf" /etc/nginx/conf.d/ 2>/dev/null || true
    # Note: rate-limit.conf requires additional setup in main config
fi

# Step 6: Test and reload
echo -e "${GREEN}[6/6] Testing and reloading Nginx...${NC}"
if sudo nginx -t; then
    sudo systemctl reload nginx
    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║              NGINX INSTALLATION COMPLETE!                     ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "Server configured for: https://$HUB_IP"
    echo ""
    echo "SSL Certificate: /etc/nginx/ssl/orizon.crt"
    echo "SSL Key:         /etc/nginx/ssl/orizon.key"
    echo "Site Config:     /etc/nginx/sites-available/orizon"
    echo ""
    echo -e "${YELLOW}Next steps:${NC}"
    echo "1. Deploy frontend: sudo rsync -av /opt/orizon-ztc/frontend/dist/ /var/www/html/"
    echo "2. Start backend:   cd /opt/orizon-ztc && docker compose up -d"
    echo "3. Access:          https://$HUB_IP"
else
    echo -e "${RED}Nginx configuration test failed!${NC}"
    exit 1
fi
