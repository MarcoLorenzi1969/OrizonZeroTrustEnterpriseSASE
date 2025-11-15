#!/bin/bash
###############################################################################
# Orizon Zero Trust Connect - Monitoring Script
# For: Marco @ Syneto/Orizon
# Monitors application health, performance, and alerts
###############################################################################

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
APP_NAME="orizon-ztc"
API_URL="http://localhost:8000"
ALERT_EMAIL="marco@syneto.net"
LOG_FILE="/var/log/${APP_NAME}/monitor.log"

# Thresholds
CPU_THRESHOLD=80
MEMORY_THRESHOLD=85
DISK_THRESHOLD=90
RESPONSE_TIME_THRESHOLD=2000  # milliseconds

# Helper functions
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a ${LOG_FILE}
}

alert() {
    local message="$1"
    log "ALERT: ${message}"
    # Send email alert (requires mailutils)
    # echo "${message}" | mail -s "Orizon ZTC Alert" ${ALERT_EMAIL}
}

# Check service status
check_service() {
    local service=$1
    if systemctl is-active --quiet ${service}; then
        echo -e "${GREEN}✓${NC} ${service}"
        return 0
    else
        echo -e "${RED}✗${NC} ${service}"
        alert "${service} is not running!"
        return 1
    fi
}

# Check API health
check_api_health() {
    local start=$(date +%s%3N)
    local response=$(curl -s -o /dev/null -w "%{http_code}" ${API_URL}/health 2>/dev/null)
    local end=$(date +%s%3N)
    local duration=$((end - start))

    if [ "$response" == "200" ]; then
        if [ $duration -gt $RESPONSE_TIME_THRESHOLD ]; then
            echo -e "${YELLOW}⚠${NC} API Health (${duration}ms - SLOW)"
            log "WARNING: API response time ${duration}ms exceeds threshold ${RESPONSE_TIME_THRESHOLD}ms"
        else
            echo -e "${GREEN}✓${NC} API Health (${duration}ms)"
        fi
        return 0
    else
        echo -e "${RED}✗${NC} API Health (HTTP ${response})"
        alert "API health check failed with HTTP ${response}"
        return 1
    fi
}

# Check database connectivity
check_database() {
    local db_name="orizon_ztc"
    if sudo -u postgres psql -d ${db_name} -c "SELECT 1;" &>/dev/null; then
        echo -e "${GREEN}✓${NC} PostgreSQL"
        return 0
    else
        echo -e "${RED}✗${NC} PostgreSQL"
        alert "PostgreSQL database connection failed!"
        return 1
    fi
}

# Check Redis
check_redis() {
    if redis-cli ping &>/dev/null; then
        echo -e "${GREEN}✓${NC} Redis"
        return 0
    else
        echo -e "${RED}✗${NC} Redis"
        alert "Redis connection failed!"
        return 1
    fi
}

# Check MongoDB
check_mongodb() {
    if mongosh --eval "db.runCommand({ ping: 1 })" --quiet &>/dev/null; then
        echo -e "${GREEN}✓${NC} MongoDB"
        return 0
    else
        echo -e "${RED}✗${NC} MongoDB"
        alert "MongoDB connection failed!"
        return 1
    fi
}

# Check system resources
check_cpu() {
    local cpu_usage=$(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1}')
    cpu_usage=${cpu_usage%.*}  # Convert to integer

    if [ $cpu_usage -gt $CPU_THRESHOLD ]; then
        echo -e "${RED}✗${NC} CPU: ${cpu_usage}% (CRITICAL)"
        alert "CPU usage ${cpu_usage}% exceeds threshold ${CPU_THRESHOLD}%"
    elif [ $cpu_usage -gt $((CPU_THRESHOLD - 10)) ]; then
        echo -e "${YELLOW}⚠${NC} CPU: ${cpu_usage}% (WARNING)"
    else
        echo -e "${GREEN}✓${NC} CPU: ${cpu_usage}%"
    fi
}

check_memory() {
    local mem_usage=$(free | grep Mem | awk '{print int(($3/$2) * 100)}')

    if [ $mem_usage -gt $MEMORY_THRESHOLD ]; then
        echo -e "${RED}✗${NC} Memory: ${mem_usage}% (CRITICAL)"
        alert "Memory usage ${mem_usage}% exceeds threshold ${MEMORY_THRESHOLD}%"
    elif [ $mem_usage -gt $((MEMORY_THRESHOLD - 10)) ]; then
        echo -e "${YELLOW}⚠${NC} Memory: ${mem_usage}% (WARNING)"
    else
        echo -e "${GREEN}✓${NC} Memory: ${mem_usage}%"
    fi
}

check_disk() {
    local disk_usage=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')

    if [ $disk_usage -gt $DISK_THRESHOLD ]; then
        echo -e "${RED}✗${NC} Disk: ${disk_usage}% (CRITICAL)"
        alert "Disk usage ${disk_usage}% exceeds threshold ${DISK_THRESHOLD}%"
    elif [ $disk_usage -gt $((DISK_THRESHOLD - 10)) ]; then
        echo -e "${YELLOW}⚠${NC} Disk: ${disk_usage}% (WARNING)"
    else
        echo -e "${GREEN}✓${NC} Disk: ${disk_usage}%"
    fi
}

# Check active tunnels
check_tunnels() {
    local count=$(curl -s ${API_URL}/api/v1/tunnels 2>/dev/null | jq '. | length' 2>/dev/null || echo "0")
    echo -e "${BLUE}ℹ${NC} Active Tunnels: ${count}"
}

# Check active nodes
check_nodes() {
    local count=$(curl -s ${API_URL}/api/v1/nodes 2>/dev/null | jq '. | length' 2>/dev/null || echo "0")
    echo -e "${BLUE}ℹ${NC} Active Nodes: ${count}"
}

# Check log errors
check_errors() {
    local error_count=$(journalctl -u ${APP_NAME}-backend --since "5 minutes ago" | grep -i error | wc -l)

    if [ $error_count -gt 10 ]; then
        echo -e "${RED}✗${NC} Errors in last 5 min: ${error_count}"
        alert "High error rate detected: ${error_count} errors in last 5 minutes"
    elif [ $error_count -gt 0 ]; then
        echo -e "${YELLOW}⚠${NC} Errors in last 5 min: ${error_count}"
    else
        echo -e "${GREEN}✓${NC} No recent errors"
    fi
}

# Main monitoring function
main() {
    clear
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}   Orizon Zero Trust Connect - System Monitor${NC}"
    echo -e "${BLUE}   $(date '+%Y-%m-%d %H:%M:%S')${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    echo -e "${YELLOW}Services:${NC}"
    check_service "${APP_NAME}-backend"
    check_service "nginx"
    check_service "postgresql"
    check_service "redis-server"
    check_service "mongod"
    echo ""

    echo -e "${YELLOW}Health Checks:${NC}"
    check_api_health
    check_database
    check_redis
    check_mongodb
    echo ""

    echo -e "${YELLOW}System Resources:${NC}"
    check_cpu
    check_memory
    check_disk
    echo ""

    echo -e "${YELLOW}Application Stats:${NC}"
    check_tunnels
    check_nodes
    check_errors
    echo ""

    # Uptime
    echo -e "${YELLOW}System Uptime:${NC}"
    uptime | awk '{print "  " $0}'
    echo ""

    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# Run in watch mode or once
if [ "$1" == "--watch" ]; then
    while true; do
        main
        echo -e "\n${YELLOW}Refreshing in 30 seconds... (Ctrl+C to exit)${NC}"
        sleep 30
    done
else
    main
fi
