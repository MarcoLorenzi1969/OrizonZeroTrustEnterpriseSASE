#!/bin/bash

# Orizon Zero Trust Connect - Guacamole Hub Docker Installation
# Server: 167.71.33.70
# Purpose: Quick deploy using Docker Compose

set -e

echo "========================================"
echo "Orizon Guacamole Hub - Docker Install"
echo "Server: 167.71.33.70"
echo "========================================"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}Step 1: Install Docker and Docker Compose${NC}"

# Update system
sudo apt update

# Install Docker
sudo apt install -y docker.io docker-compose
sudo systemctl enable docker
sudo systemctl start docker

# Add user to docker group
sudo usermod -aG docker $(whoami)

echo -e "${GREEN}✓ Docker installed${NC}"

echo -e "${BLUE}Step 2: Download Guacamole Database Schema${NC}"

# Create deployment directory
mkdir -p /opt/guacamole
cd /opt/guacamole

# Download schema initialization script
docker run --rm guacamole/guacamole /opt/guacamole/bin/initdb.sh --mysql > initdb.sql

echo -e "${GREEN}✓ Database schema downloaded${NC}"

echo -e "${BLUE}Step 3: Create Docker Compose Configuration${NC}"

# Create docker-compose.yml
cat > docker-compose.yml <<'EOF'
version: '3.8'

services:
  guacdb:
    container_name: guacdb
    image: mysql:8.0
    restart: always
    environment:
      MYSQL_ROOT_PASSWORD: orizon_guacamole_root_password
      MYSQL_DATABASE: guacamole_db
      MYSQL_USER: guacamole_user
      MYSQL_PASSWORD: orizon_guacamole_db_password
    volumes:
      - guacdb_data:/var/lib/mysql
      - ./initdb.sql:/docker-entrypoint-initdb.d/initdb.sql:ro
    networks:
      - guacnet

  guacd:
    container_name: guacd
    image: guacamole/guacd:latest
    restart: always
    networks:
      - guacnet

  guacamole:
    container_name: guacamole
    image: guacamole/guacamole:latest
    restart: always
    ports:
      - "8080:8080"
    environment:
      GUACD_HOSTNAME: guacd
      MYSQL_HOSTNAME: guacdb
      MYSQL_DATABASE: guacamole_db
      MYSQL_USER: guacamole_user
      MYSQL_PASSWORD: orizon_guacamole_db_password
    depends_on:
      - guacdb
      - guacd
    networks:
      - guacnet

networks:
  guacnet:
    driver: bridge

volumes:
  guacdb_data:
EOF

echo -e "${GREEN}✓ Docker Compose configuration created${NC}"

echo -e "${BLUE}Step 4: Start Guacamole Services${NC}"

# Start containers
docker-compose up -d

# Wait for services to be ready
echo "Waiting for services to start (30 seconds)..."
sleep 30

echo -e "${GREEN}✓ Guacamole services started${NC}"

echo -e "${BLUE}Step 5: Configure Nginx Reverse Proxy${NC}"

# Install Nginx
sudo apt install -y nginx

# Create nginx configuration
sudo tee /etc/nginx/sites-available/guacamole > /dev/null <<'NGINX_EOF'
server {
    listen 80;
    server_name 167.71.33.70;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name 167.71.33.70;

    ssl_certificate /etc/nginx/ssl/guacamole-selfsigned.crt;
    ssl_certificate_key /etc/nginx/ssl/guacamole-selfsigned.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location /guacamole/ {
        proxy_pass http://localhost:8080/guacamole/;
        proxy_buffering off;
        proxy_http_version 1.1;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $http_connection;
        proxy_cookie_path /guacamole/ /;
    }

    location /guacamole/websocket-tunnel {
        proxy_pass http://localhost:8080/guacamole/websocket-tunnel;
        proxy_buffering off;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    location /health {
        return 200 "OK\n";
        add_header Content-Type text/plain;
    }
}
NGINX_EOF

# Create SSL certificate
sudo mkdir -p /etc/nginx/ssl
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/nginx/ssl/guacamole-selfsigned.key \
    -out /etc/nginx/ssl/guacamole-selfsigned.crt \
    -subj "/C=IT/ST=Tuscany/L=Florence/O=Orizon/CN=167.71.33.70"

# Enable site
sudo ln -sf /etc/nginx/sites-available/guacamole /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test and restart nginx
sudo nginx -t
sudo systemctl restart nginx

echo -e "${GREEN}✓ Nginx configured${NC}"

echo -e "${BLUE}Step 6: Configure Firewall${NC}"

sudo apt install -y ufw
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 22/tcp
sudo ufw --force enable

echo -e "${GREEN}✓ Firewall configured${NC}"

echo -e "${BLUE}Step 7: Save Credentials${NC}"

sudo tee /root/guacamole_credentials.txt > /dev/null <<EOF
=================================
Orizon Guacamole Hub Credentials
=================================

Guacamole Web Interface:
  URL: https://167.71.33.70/guacamole/
  Username: guacadmin
  Password: guacadmin

MySQL Database:
  Root Password: orizon_guacamole_root_password
  Guacamole DB User: guacamole_user
  Guacamole DB Password: orizon_guacamole_db_password

Docker Containers:
  guacdb - MySQL database
  guacd - Guacamole daemon
  guacamole - Web application

Management Commands:
  View containers: docker ps
  View logs: docker logs guacamole
  Restart: cd /opt/guacamole && docker-compose restart
  Stop: cd /opt/guacamole && docker-compose stop
  Start: cd /opt/guacamole && docker-compose start

Files:
  Docker Compose: /opt/guacamole/docker-compose.yml
  Database Schema: /opt/guacamole/initdb.sql
  Nginx Config: /etc/nginx/sites-available/guacamole

IMPORTANT:
  - Change default password immediately!
  - Containers auto-start on boot
EOF

sudo chmod 600 /root/guacamole_credentials.txt

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✓ Guacamole Installation Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Access: https://167.71.33.70/guacamole/"
echo "Username: guacadmin"
echo "Password: guacadmin (CHANGE THIS!)"
echo ""
echo "Credentials: /root/guacamole_credentials.txt"
echo ""
echo "Containers Status:"
docker ps
