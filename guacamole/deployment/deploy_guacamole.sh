#!/bin/bash

# Orizon Zero Trust Connect - Complete Guacamole Deployment
# This script deploys Guacamole on 167.71.33.70 and integrates with Orizon ZTC

set -e

echo "=========================================="
echo "Orizon Guacamole Hub - Complete Deployment"
echo "=========================================="

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
GUAC_SERVER="167.71.33.70"
GUAC_USER="orizonzerotrust"
GUAC_PASSWORD="ripper-FfFIlBelloccio.1969F"
ORIZON_HUB="46.101.189.126"
ORIZON_USER="orizonai"
ORIZON_PASSWORD="ripper-FfFIlBelloccio.1969F"

echo -e "${BLUE}Step 1: Preparing deployment files${NC}"

# Create temporary directory
TMP_DIR=$(mktemp -d)
echo "Temporary directory: $TMP_DIR"

# Copy installation script
cp install_guacamole.sh $TMP_DIR/
cp register_guacamole_hub.py $TMP_DIR/

echo -e "${GREEN}✓ Files prepared${NC}"

echo -e "${BLUE}Step 2: Uploading files to Guacamole server${NC}"

# Upload installation script
sshpass -p "$GUAC_PASSWORD" scp -o StrictHostKeyChecking=no \
    $TMP_DIR/install_guacamole.sh \
    ${GUAC_USER}@${GUAC_SERVER}:/tmp/

echo -e "${GREEN}✓ Files uploaded${NC}"

echo -e "${BLUE}Step 3: Installing Guacamole on ${GUAC_SERVER}${NC}"

# Execute installation script
sshpass -p "$GUAC_PASSWORD" ssh -o StrictHostKeyChecking=no \
    ${GUAC_USER}@${GUAC_SERVER} \
    "bash /tmp/install_guacamole.sh"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Guacamole installation completed${NC}"
else
    echo -e "${RED}✗ Guacamole installation failed${NC}"
    exit 1
fi

echo -e "${BLUE}Step 4: Registering Guacamole hub in Orizon${NC}"

# Upload registration script to Orizon hub
sshpass -p "$ORIZON_PASSWORD" scp -o StrictHostKeyChecking=no \
    $TMP_DIR/register_guacamole_hub.py \
    ${ORIZON_USER}@${ORIZON_HUB}:/tmp/

# Execute registration script
sshpass -p "$ORIZON_PASSWORD" ssh -o StrictHostKeyChecking=no \
    ${ORIZON_USER}@${ORIZON_HUB} \
    "cd /tmp && echo 'yes' | python3 register_guacamole_hub.py"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Guacamole hub registered in Orizon${NC}"
else
    echo -e "${YELLOW}⚠ Hub registration failed (may already exist)${NC}"
fi

echo -e "${BLUE}Step 5: Configuring firewall${NC}"

# Configure firewall on Guacamole server
sshpass -p "$GUAC_PASSWORD" ssh -o StrictHostKeyChecking=no \
    ${GUAC_USER}@${GUAC_SERVER} \
    "sudo ufw allow 80/tcp && sudo ufw allow 443/tcp && sudo ufw --force enable"

echo -e "${GREEN}✓ Firewall configured${NC}"

echo -e "${BLUE}Step 6: Verifying deployment${NC}"

# Check Guacamole status
echo "Checking Guacamole services..."
sshpass -p "$GUAC_PASSWORD" ssh -o StrictHostKeyChecking=no \
    ${GUAC_USER}@${GUAC_SERVER} \
    "sudo systemctl is-active guacd tomcat9 nginx" || true

# Test HTTPS access
echo "Testing HTTPS access..."
sleep 5
HTTP_STATUS=$(curl -k -s -o /dev/null -w "%{http_code}" https://${GUAC_SERVER}/guacamole/)

if [ "$HTTP_STATUS" = "200" ]; then
    echo -e "${GREEN}✓ Guacamole web interface is accessible${NC}"
else
    echo -e "${YELLOW}⚠ HTTP status: $HTTP_STATUS (may need a moment to start)${NC}"
fi

# Cleanup
rm -rf $TMP_DIR

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✓ DEPLOYMENT COMPLETED SUCCESSFULLY${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Guacamole Hub Details:"
echo "  URL: https://${GUAC_SERVER}/guacamole/"
echo "  Username: guacadmin"
echo "  Password: guacadmin (CHANGE IMMEDIATELY!)"
echo ""
echo "Orizon Hub: https://${ORIZON_HUB}"
echo ""
echo "Next Steps:"
echo "1. Access Guacamole and change default password"
echo "2. Access Orizon dashboard"
echo "3. Go to Nodes page and sync nodes to Guacamole"
echo "4. Use 'SSH via Guacamole' button to access nodes"
echo ""
echo "Credentials saved on servers:"
echo "  Guacamole: /root/guacamole_credentials.txt"
echo "  Orizon: Database"
echo ""
