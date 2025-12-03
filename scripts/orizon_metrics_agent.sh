#!/bin/bash
# ============================================================================
# Orizon Zero Trust Connect - Metrics Agent
# Collects system metrics and sends to Hub servers
# For: Marco @ Syneto/Orizon
# ============================================================================

set -e

# Configuration - these should be set as environment variables or in config file
CONFIG_FILE="/opt/orizon-agent/config.env"

# Default values
AGENT_TOKEN="${AGENT_TOKEN:-}"
HUB1_URL="${HUB1_URL:-https://139.59.149.48}"
HUB2_URL="${HUB2_URL:-https://68.183.219.222}"
METRICS_INTERVAL="${METRICS_INTERVAL:-30}"

# Load config if exists
if [[ -f "$CONFIG_FILE" ]]; then
    source "$CONFIG_FILE"
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ============================================================================
# Collect System Metrics
# ============================================================================

collect_metrics() {
    # CPU Usage (average over 1 second)
    CPU_USAGE=$(top -bn2 -d1 | grep "Cpu(s)" | tail -1 | awk '{print $2}' | cut -d'%' -f1)
    if [[ -z "$CPU_USAGE" ]]; then
        CPU_USAGE=$(vmstat 1 2 | tail -1 | awk '{print 100-$15}')
    fi

    # Memory Usage
    MEM_INFO=$(free -m)
    MEM_TOTAL=$(echo "$MEM_INFO" | awk '/Mem:/ {print $2}')
    MEM_USED=$(echo "$MEM_INFO" | awk '/Mem:/ {print $3}')
    MEM_USAGE=$(awk "BEGIN {printf \"%.1f\", ($MEM_USED / $MEM_TOTAL) * 100}")

    # Disk Usage (root partition)
    DISK_INFO=$(df -h / | tail -1)
    DISK_TOTAL=$(echo "$DISK_INFO" | awk '{print $2}' | sed 's/G//')
    DISK_USAGE=$(echo "$DISK_INFO" | awk '{print $5}' | sed 's/%//')

    # CPU Cores
    CPU_CORES=$(nproc)

    # Active Processes
    ACTIVE_PROCESSES=$(ps aux | wc -l)

    # Active Connections
    ACTIVE_CONNECTIONS=$(ss -s | grep "estab" | head -1 | awk '{print $4}' | tr -d ',')
    if [[ -z "$ACTIVE_CONNECTIONS" ]]; then
        ACTIVE_CONNECTIONS=$(netstat -an 2>/dev/null | grep ESTABLISHED | wc -l)
    fi

    # Network bytes (since boot)
    NET_RX=$(cat /sys/class/net/*/statistics/rx_bytes 2>/dev/null | awk '{sum+=$1} END {print sum}')
    NET_TX=$(cat /sys/class/net/*/statistics/tx_bytes 2>/dev/null | awk '{sum+=$1} END {print sum}')

    # Top 5 processes by CPU
    TOP_PROCESSES=$(ps aux --sort=-%cpu | head -6 | tail -5 | awk '{printf "{\"pid\":%s,\"cpu\":%.1f,\"mem\":%.1f,\"cmd\":\"%s\"},", $2, $3, $4, $11}' | sed 's/,$//')

    # Build JSON payload
    TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

    cat <<EOF
{
    "agent_token": "$AGENT_TOKEN",
    "cpu_usage": ${CPU_USAGE:-0},
    "memory_usage": ${MEM_USAGE:-0},
    "disk_usage": ${DISK_USAGE:-0},
    "cpu_cores": ${CPU_CORES:-1},
    "memory_mb": ${MEM_TOTAL:-0},
    "disk_gb": ${DISK_TOTAL:-0},
    "network_rx_bytes": ${NET_RX:-0},
    "network_tx_bytes": ${NET_TX:-0},
    "active_connections": ${ACTIVE_CONNECTIONS:-0},
    "active_processes": ${ACTIVE_PROCESSES:-0},
    "top_processes": [${TOP_PROCESSES}],
    "timestamp": "$TIMESTAMP"
}
EOF
}

# ============================================================================
# Send Metrics to Hub
# ============================================================================

send_metrics() {
    local HUB_URL="$1"
    local METRICS_JSON="$2"

    # Send to Hub
    RESPONSE=$(curl -s -k -X POST "${HUB_URL}/api/v1/nodes/metrics" \
        -H "Content-Type: application/json" \
        -d "$METRICS_JSON" \
        --connect-timeout 5 \
        --max-time 10 \
        2>/dev/null)

    if echo "$RESPONSE" | grep -q '"status":"ok"'; then
        return 0
    else
        return 1
    fi
}

# ============================================================================
# Main Loop
# ============================================================================

run_once() {
    if [[ -z "$AGENT_TOKEN" ]]; then
        log_error "AGENT_TOKEN not set. Please configure /opt/orizon-agent/config.env"
        exit 1
    fi

    log_info "Collecting metrics..."
    METRICS=$(collect_metrics)

    log_info "Sending metrics to Hub1 ($HUB1_URL)..."
    if send_metrics "$HUB1_URL" "$METRICS"; then
        log_info "Hub1: OK"
    else
        log_warn "Hub1: Failed"
    fi

    log_info "Sending metrics to Hub2 ($HUB2_URL)..."
    if send_metrics "$HUB2_URL" "$METRICS"; then
        log_info "Hub2: OK"
    else
        log_warn "Hub2: Failed"
    fi
}

run_daemon() {
    log_info "Starting Orizon Metrics Agent (interval: ${METRICS_INTERVAL}s)"

    while true; do
        run_once
        sleep "$METRICS_INTERVAL"
    done
}

show_status() {
    echo "============================================"
    echo "Orizon Metrics Agent Status"
    echo "============================================"
    echo "Config file: $CONFIG_FILE"
    echo "Agent Token: ${AGENT_TOKEN:0:20}..."
    echo "Hub1 URL: $HUB1_URL"
    echo "Hub2 URL: $HUB2_URL"
    echo "Interval: ${METRICS_INTERVAL}s"
    echo ""
    echo "Current Metrics:"
    collect_metrics | python3 -m json.tool 2>/dev/null || collect_metrics
}

install_service() {
    log_info "Installing Orizon Metrics Agent service..."

    # Create systemd service
    cat > /etc/systemd/system/orizon-metrics.service << 'EOFSERVICE'
[Unit]
Description=Orizon Zero Trust Connect - Metrics Agent
Documentation=https://orizon.syneto.eu
After=network-online.target orizon-tunnel-hub1.service orizon-tunnel-hub2.service
Wants=network-online.target

[Service]
Type=simple
EnvironmentFile=/opt/orizon-agent/config.env
ExecStart=/opt/orizon-agent/orizon_metrics_agent.sh daemon
Restart=always
RestartSec=30
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOFSERVICE

    # Create config directory
    mkdir -p /opt/orizon-agent

    # Copy script
    cp "$0" /opt/orizon-agent/orizon_metrics_agent.sh
    chmod +x /opt/orizon-agent/orizon_metrics_agent.sh

    # Create config template if not exists
    if [[ ! -f /opt/orizon-agent/config.env ]]; then
        cat > /opt/orizon-agent/config.env << 'EOFCONFIG'
# Orizon Metrics Agent Configuration
# Get AGENT_TOKEN from Hub admin panel

AGENT_TOKEN=your-agent-token-here
HUB1_URL=https://139.59.149.48
HUB2_URL=https://68.183.219.222
METRICS_INTERVAL=30
EOFCONFIG
        log_warn "Created config template at /opt/orizon-agent/config.env"
        log_warn "Please edit and set AGENT_TOKEN"
    fi

    # Enable and start service
    systemctl daemon-reload
    systemctl enable orizon-metrics.service

    log_info "Service installed. Start with: systemctl start orizon-metrics"
}

# ============================================================================
# CLI
# ============================================================================

case "${1:-}" in
    daemon)
        run_daemon
        ;;
    once)
        run_once
        ;;
    status)
        show_status
        ;;
    install)
        install_service
        ;;
    *)
        echo "Usage: $0 {daemon|once|status|install}"
        echo ""
        echo "Commands:"
        echo "  daemon   - Run as background daemon"
        echo "  once     - Collect and send metrics once"
        echo "  status   - Show current configuration and metrics"
        echo "  install  - Install as systemd service"
        exit 1
        ;;
esac
