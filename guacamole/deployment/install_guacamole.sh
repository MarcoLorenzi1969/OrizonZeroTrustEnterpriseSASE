#!/bin/bash

# Orizon Zero Trust Connect - Guacamole Hub Installation Script
# Server: 167.71.33.70
# User: orizonzerotrust
# Purpose: Deploy Apache Guacamole as dedicated SSH/RDP/VNC gateway

set -e

echo "========================================"
echo "Orizon Guacamole Hub Installation"
echo "Server: 167.71.33.70"
echo "========================================"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
GUAC_VERSION="1.5.5"
MYSQL_ROOT_PASSWORD="orizon_guacamole_root_$(openssl rand -hex 16)"
GUAC_DB_PASSWORD="orizon_guacamole_db_$(openssl rand -hex 16)"
ORIZON_HUB="46.101.189.126"

echo -e "${BLUE}Step 1: System Update${NC}"
sudo apt update
sudo apt upgrade -y

echo -e "${BLUE}Step 2: Install Dependencies${NC}"
sudo apt install -y \
    build-essential \
    libcairo2-dev \
    libjpeg-turbo8-dev \
    libpng-dev \
    libtool-bin \
    libossp-uuid-dev \
    libavcodec-dev \
    libavformat-dev \
    libavutil-dev \
    libswscale-dev \
    freerdp2-dev \
    libpango1.0-dev \
    libssh2-1-dev \
    libtelnet-dev \
    libvncserver-dev \
    libwebsockets-dev \
    libpulse-dev \
    libssl-dev \
    libvorbis-dev \
    libwebp-dev \
    tomcat9 \
    tomcat9-admin \
    tomcat9-common \
    tomcat9-user \
    mysql-server \
    nginx \
    certbot \
    python3-certbot-nginx \
    git \
    curl \
    wget

echo -e "${BLUE}Step 3: Download and Build Guacamole Server${NC}"
cd /tmp
wget https://downloads.apache.org/guacamole/${GUAC_VERSION}/source/guacamole-server-${GUAC_VERSION}.tar.gz
tar -xzf guacamole-server-${GUAC_VERSION}.tar.gz
cd guacamole-server-${GUAC_VERSION}

echo "Configuring Guacamole Server..."
./configure --with-init-dir=/etc/init.d \
    --enable-allow-freerdp-snapshots \
    --with-systemd-dir=/etc/systemd/system

echo "Building Guacamole Server (this may take 10-15 minutes)..."
make -j$(nproc)
sudo make install
sudo ldconfig

echo -e "${BLUE}Step 4: Download Guacamole Client (Web Application)${NC}"
cd /tmp
wget https://downloads.apache.org/guacamole/${GUAC_VERSION}/binary/guacamole-${GUAC_VERSION}.war
sudo mkdir -p /var/lib/guacamole
sudo mv guacamole-${GUAC_VERSION}.war /var/lib/guacamole/guacamole.war

# Create symbolic link for Tomcat
sudo ln -sf /var/lib/guacamole/guacamole.war /var/lib/tomcat9/webapps/guacamole.war

echo -e "${BLUE}Step 5: Configure MySQL Database${NC}"

# Secure MySQL and create database
sudo mysql -e "ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '${MYSQL_ROOT_PASSWORD}';"
sudo mysql -u root -p"${MYSQL_ROOT_PASSWORD}" -e "CREATE DATABASE guacamole_db;"
sudo mysql -u root -p"${MYSQL_ROOT_PASSWORD}" -e "CREATE USER 'guacamole_user'@'localhost' IDENTIFIED BY '${GUAC_DB_PASSWORD}';"
sudo mysql -u root -p"${MYSQL_ROOT_PASSWORD}" -e "GRANT SELECT,INSERT,UPDATE,DELETE ON guacamole_db.* TO 'guacamole_user'@'localhost';"
sudo mysql -u root -p"${MYSQL_ROOT_PASSWORD}" -e "FLUSH PRIVILEGES;"

echo -e "${BLUE}Step 6: Download and Install MySQL Connector${NC}"
cd /tmp
wget https://downloads.apache.org/guacamole/${GUAC_VERSION}/binary/guacamole-auth-jdbc-${GUAC_VERSION}.tar.gz
tar -xzf guacamole-auth-jdbc-${GUAC_VERSION}.tar.gz

# Install MySQL connector
sudo mkdir -p /etc/guacamole/extensions
sudo mkdir -p /etc/guacamole/lib
sudo cp guacamole-auth-jdbc-${GUAC_VERSION}/mysql/guacamole-auth-jdbc-mysql-${GUAC_VERSION}.jar /etc/guacamole/extensions/

# Download MySQL Java Connector
wget https://dev.mysql.com/get/Downloads/Connector-J/mysql-connector-j-8.2.0.tar.gz
tar -xzf mysql-connector-j-8.2.0.tar.gz
sudo cp mysql-connector-j-8.2.0/mysql-connector-j-8.2.0.jar /etc/guacamole/lib/

echo -e "${BLUE}Step 7: Initialize Guacamole Database Schema${NC}"
cat guacamole-auth-jdbc-${GUAC_VERSION}/mysql/schema/*.sql | \
    sudo mysql -u root -p"${MYSQL_ROOT_PASSWORD}" guacamole_db

echo -e "${BLUE}Step 8: Configure Guacamole${NC}"

# Create guacamole.properties
sudo tee /etc/guacamole/guacamole.properties > /dev/null <<EOF
# MySQL Database Configuration
mysql-hostname: localhost
mysql-port: 3306
mysql-database: guacamole_db
mysql-username: guacamole_user
mysql-password: ${GUAC_DB_PASSWORD}

# Guacamole Server Configuration
guacd-hostname: localhost
guacd-port: 4822

# Orizon Integration
orizon-hub-url: https://${ORIZON_HUB}/api/v1
orizon-hub-enabled: true

# Additional Settings
enable-clipboard-integration: true
enable-sftp: true
EOF

# Create guacd configuration
sudo tee /etc/guacamole/guacd.conf > /dev/null <<EOF
[daemon]
pid_file = /var/run/guacd.pid
log_level = info

[server]
bind_host = 0.0.0.0
bind_port = 4822
EOF

# Set permissions
sudo chmod 600 /etc/guacamole/guacamole.properties

# Link configurations for Tomcat
sudo ln -sf /etc/guacamole /usr/share/tomcat9/.guacamole

echo -e "${BLUE}Step 9: Configure Nginx Reverse Proxy${NC}"

sudo tee /etc/nginx/sites-available/guacamole > /dev/null <<'EOF'
server {
    listen 80;
    server_name 167.71.33.70;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name 167.71.33.70;

    # SSL Configuration (self-signed for now)
    ssl_certificate /etc/nginx/ssl/guacamole-selfsigned.crt;
    ssl_certificate_key /etc/nginx/ssl/guacamole-selfsigned.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Guacamole proxy
    location /guacamole/ {
        proxy_pass http://localhost:8080/guacamole/;
        proxy_buffering off;
        proxy_http_version 1.1;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $http_connection;
        proxy_cookie_path /guacamole/ /;
        access_log off;
    }

    # WebSocket support
    location /guacamole/websocket-tunnel {
        proxy_pass http://localhost:8080/guacamole/websocket-tunnel;
        proxy_buffering off;
        proxy_http_version 1.1;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        access_log off;
    }

    # Orizon Integration API
    location /api/ {
        proxy_pass http://localhost:5000/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Health check
    location /health {
        access_log off;
        return 200 "OK\n";
        add_header Content-Type text/plain;
    }
}
EOF

# Create SSL directory and self-signed certificate
sudo mkdir -p /etc/nginx/ssl
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/nginx/ssl/guacamole-selfsigned.key \
    -out /etc/nginx/ssl/guacamole-selfsigned.crt \
    -subj "/C=IT/ST=Tuscany/L=Florence/O=Orizon/CN=167.71.33.70"

# Enable site
sudo ln -sf /etc/nginx/sites-available/guacamole /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test nginx config
sudo nginx -t

echo -e "${BLUE}Step 10: Create Systemd Services${NC}"

# Enable and start guacd
sudo systemctl enable guacd
sudo systemctl start guacd

# Configure Tomcat
sudo systemctl enable tomcat9
sudo systemctl restart tomcat9

# Restart Nginx
sudo systemctl restart nginx

echo -e "${BLUE}Step 11: Create Default Admin User${NC}"

# Wait for Tomcat to fully start
sleep 10

# Create admin user via SQL
sudo mysql -u root -p"${MYSQL_ROOT_PASSWORD}" guacamole_db <<EOF
-- Create admin user (username: guacadmin, password: guacadmin)
INSERT INTO guacamole_entity (name, type) VALUES ('guacadmin', 'USER');
SET @entity_id = LAST_INSERT_ID();

INSERT INTO guacamole_user (entity_id, password_hash, password_salt, password_date)
VALUES (@entity_id,
    x'CA458A7D494E3BE824F5E1E175A1556C0F8EEF2C2D7DF3633BEC4A29C4411960',  -- password: guacadmin
    x'FE24ADC5E11E2B25288D1704ABE67A79E342ECC26064CE69C5B3177795A82264',
    NOW());

-- Grant all permissions
INSERT INTO guacamole_user_permission (entity_id, affected_entity_id, permission)
SELECT @entity_id, guacamole_entity.entity_id, permission
FROM (
    SELECT 'READ' AS permission
    UNION SELECT 'UPDATE'
    UNION SELECT 'DELETE'
    UNION SELECT 'ADMINISTER'
) permissions
CROSS JOIN guacamole_entity;

-- System permissions
INSERT INTO guacamole_system_permission (entity_id, permission)
VALUES
    (@entity_id, 'CREATE_CONNECTION'),
    (@entity_id, 'CREATE_CONNECTION_GROUP'),
    (@entity_id, 'CREATE_SHARING_PROFILE'),
    (@entity_id, 'CREATE_USER'),
    (@entity_id, 'CREATE_USER_GROUP'),
    (@entity_id, 'ADMINISTER');
EOF

echo -e "${BLUE}Step 12: Save Credentials${NC}"

# Save credentials to file
sudo tee /root/guacamole_credentials.txt > /dev/null <<EOF
=================================
Orizon Guacamole Hub Credentials
=================================

Guacamole Web Interface:
  URL: https://167.71.33.70/guacamole/
  Username: guacadmin
  Password: guacadmin

MySQL Database:
  Root Password: ${MYSQL_ROOT_PASSWORD}
  Guacamole DB User: guacamole_user
  Guacamole DB Password: ${GUAC_DB_PASSWORD}

Orizon Hub Connection:
  Main Hub: https://${ORIZON_HUB}

Service Ports:
  HTTPS: 443
  HTTP: 80 (redirects to HTTPS)
  Guacd: 4822 (internal)
  Tomcat: 8080 (internal)

Files:
  Config: /etc/guacamole/guacamole.properties
  Extensions: /etc/guacamole/extensions/
  Nginx: /etc/nginx/sites-available/guacamole

Important:
  - Change default password immediately!
  - Consider using Let's Encrypt for production SSL
  - Configure firewall to allow only 80, 443
EOF

sudo chmod 600 /root/guacamole_credentials.txt

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✓ Guacamole Hub Installation Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Access Guacamole at: https://167.71.33.70/guacamole/"
echo "Username: guacadmin"
echo "Password: guacadmin"
echo ""
echo "Credentials saved to: /root/guacamole_credentials.txt"
echo ""
echo "Next Steps:"
echo "1. Access web interface and change default password"
echo "2. Configure firewall: sudo ufw allow 80,443/tcp"
echo "3. Set up Let's Encrypt SSL (optional)"
echo "4. Configure connections to edge nodes"
echo ""
echo -e "${BLUE}Services Status:${NC}"
sudo systemctl status guacd --no-pager -l | head -5
sudo systemctl status tomcat9 --no-pager -l | head -5
sudo systemctl status nginx --no-pager -l | head -5
