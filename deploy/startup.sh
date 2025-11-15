#!/bin/bash
###############################################################################
# Orizon Zero Trust Connect - Startup Script
# For: Marco @ Syneto/Orizon
# Ensures all services start in correct order
###############################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
APP_NAME="orizon-ztc"

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}   Orizon Zero Trust Connect - Startup${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Function to start service with retry
start_service() {
    local service=$1
    local max_retries=3
    local retry=0

    while [ $retry -lt $max_retries ]; do
        echo -e "${YELLOW}Starting ${service}...${NC}"

        if systemctl start ${service}; then
            sleep 2
            if systemctl is-active --quiet ${service}; then
                echo -e "${GREEN}✓ ${service} started${NC}"
                return 0
            fi
        fi

        retry=$((retry + 1))
        if [ $retry -lt $max_retries ]; then
            echo -e "${YELLOW}⚠ Retry ${retry}/${max_retries}...${NC}"
            sleep 3
        fi
    done

    echo -e "${RED}✗ Failed to start ${service} after ${max_retries} attempts${NC}"
    return 1
}

# Step 1: Start database services
echo -e "\n${YELLOW}[1/4] Starting database services...${NC}"
start_service "postgresql" || exit 1
start_service "redis-server" || exit 1
start_service "mongod" || exit 1

# Wait for databases to be ready
echo -e "${BLUE}→ Waiting for databases to be ready...${NC}"
sleep 5

# Test PostgreSQL
if sudo -u postgres psql -c "SELECT 1;" &>/dev/null; then
    echo -e "${GREEN}✓ PostgreSQL ready${NC}"
else
    echo -e "${RED}✗ PostgreSQL not responding${NC}"
    exit 1
fi

# Test Redis
if redis-cli ping &>/dev/null; then
    echo -e "${GREEN}✓ Redis ready${NC}"
else
    echo -e "${RED}✗ Redis not responding${NC}"
    exit 1
fi

# Test MongoDB
if mongosh --eval "db.runCommand({ ping: 1 })" --quiet &>/dev/null; then
    echo -e "${GREEN}✓ MongoDB ready${NC}"
else
    echo -e "${RED}✗ MongoDB not responding${NC}"
    exit 1
fi

# Step 2: Start backend
echo -e "\n${YELLOW}[2/4] Starting backend service...${NC}"
start_service "${APP_NAME}-backend" || exit 1

# Wait for backend to be healthy
echo -e "${BLUE}→ Waiting for backend API...${NC}"
max_wait=30
waited=0
while [ $waited -lt $max_wait ]; do
    if curl -s http://localhost:8000/health &>/dev/null; then
        echo -e "${GREEN}✓ Backend API ready${NC}"
        break
    fi
    sleep 1
    waited=$((waited + 1))
    echo -ne "${BLUE}→ Waiting... ${waited}s${NC}\r"
done

if [ $waited -ge $max_wait ]; then
    echo -e "${RED}✗ Backend API did not respond within ${max_wait}s${NC}"
    journalctl -u ${APP_NAME}-backend -n 50 --no-pager
    exit 1
fi

# Step 3: Start Nginx
echo -e "\n${YELLOW}[3/4] Starting Nginx...${NC}"
start_service "nginx" || exit 1

# Test Nginx
if curl -s http://localhost/ &>/dev/null; then
    echo -e "${GREEN}✓ Nginx ready${NC}"
else
    echo -e "${RED}✗ Nginx not responding${NC}"
    exit 1
fi

# Step 4: Verify everything
echo -e "\n${YELLOW}[4/4] Running health checks...${NC}"

# Check all services
all_ok=true

services=("postgresql" "redis-server" "mongod" "${APP_NAME}-backend" "nginx")
for service in "${services[@]}"; do
    if systemctl is-active --quiet ${service}; then
        echo -e "${GREEN}✓${NC} ${service}"
    else
        echo -e "${RED}✗${NC} ${service}"
        all_ok=false
    fi
done

echo ""

if [ "$all_ok" = true ]; then
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}✓ All services started successfully!${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${YELLOW}Application Status:${NC}"
    echo -e "  Frontend: ${GREEN}http://$(hostname -I | awk '{print $1}')${NC}"
    echo -e "  API:      ${GREEN}http://$(hostname -I | awk '{print $1}')/api${NC}"
    echo -e "  Metrics:  ${GREEN}http://$(hostname -I | awk '{print $1}')/metrics${NC}"
    echo ""
    echo -e "${YELLOW}Monitor logs:${NC}"
    echo -e "  journalctl -u ${APP_NAME}-backend -f"
    echo ""
else
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${RED}✗ Some services failed to start${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${YELLOW}Check logs:${NC}"
    echo -e "  journalctl -u ${APP_NAME}-backend -n 50"
    echo ""
    exit 1
fi
