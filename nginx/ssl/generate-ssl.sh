#!/bin/bash
# Orizon Zero Trust Connect - SSL Certificate Generator
# For: Marco @ Syneto/Orizon
#
# Usage: ./generate-ssl.sh <IP_OR_DOMAIN>
# Example: ./generate-ssl.sh 139.59.149.48
# Example: ./generate-ssl.sh orizon.syneto.eu

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check arguments
if [ -z "$1" ]; then
    echo -e "${RED}Error: Please provide IP address or domain${NC}"
    echo "Usage: $0 <IP_OR_DOMAIN>"
    echo "Example: $0 139.59.149.48"
    exit 1
fi

SERVER_NAME=$1
SSL_DIR="/etc/nginx/ssl"
CERT_FILE="$SSL_DIR/orizon.crt"
KEY_FILE="$SSL_DIR/orizon.key"

echo -e "${YELLOW}=== Orizon SSL Certificate Generator ===${NC}"
echo ""

# Create SSL directory
echo -e "${GREEN}Creating SSL directory...${NC}"
sudo mkdir -p $SSL_DIR
sudo chmod 700 $SSL_DIR

# Generate self-signed certificate
echo -e "${GREEN}Generating self-signed SSL certificate for: $SERVER_NAME${NC}"
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout $KEY_FILE \
    -out $CERT_FILE \
    -subj "/C=IT/ST=Italy/L=Milan/O=Orizon/OU=Zero Trust/CN=$SERVER_NAME" \
    -addext "subjectAltName=IP:$SERVER_NAME,DNS:$SERVER_NAME"

# Set permissions
sudo chmod 600 $KEY_FILE
sudo chmod 644 $CERT_FILE

echo ""
echo -e "${GREEN}SSL Certificate generated successfully!${NC}"
echo ""
echo "Certificate: $CERT_FILE"
echo "Private Key: $KEY_FILE"
echo ""
echo "Certificate details:"
openssl x509 -in $CERT_FILE -noout -subject -dates
echo ""
echo -e "${YELLOW}Note: This is a self-signed certificate.${NC}"
echo "For production, consider using Let's Encrypt:"
echo "  sudo apt install certbot python3-certbot-nginx"
echo "  sudo certbot --nginx -d yourdomain.com"
