#!/bin/bash
#
# Orizon Zero Trust Connect - Manual Reverse Tunnel Script
# For testing purposes
#
# Usage: ./manual_tunnel.sh
#
# This script creates reverse SSH tunnels from the edge node to the hub server.
# The tunnels allow:
# 1. Service tunnel: For heartbeat and metrics
# 2. Terminal tunnel: For SSH access from web terminal
#

set -e

# Configuration - EDIT THESE VALUES
HUB_HOST="139.59.149.48"
HUB_SSH_PORT="2222"
NODE_ID="eba77c68-6ef0-469a-9166-685829a4fa48"

# Port mappings (from database)
SERVICE_PORT="9000"       # Service tunnel for heartbeat/metrics
TERMINAL_PORT="10000"     # Terminal tunnel (SSH) - local 22 -> remote 10000

echo "╔════════════════════════════════════════════════════════════╗"
echo "║   Orizon Zero Trust Connect - Manual Tunnel Setup         ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Check if running as root
if [ "$(id -u)" != "0" ]; then
    echo "❌ This script must be run as root (sudo)"
    exit 1
fi

# Install autossh if not present
echo "📦 Checking dependencies..."
if ! command -v autossh &> /dev/null; then
    echo "Installing autossh..."
    if command -v apt-get &> /dev/null; then
        apt-get update -qq && apt-get install -y autossh
    elif command -v yum &> /dev/null; then
        yum install -y autossh
    else
        echo "❌ Please install autossh manually"
        exit 1
    fi
fi

# Generate SSH key if not exists
SSH_KEY="/root/.ssh/id_orizon"
if [ ! -f "$SSH_KEY" ]; then
    echo "🔑 Generating SSH key..."
    ssh-keygen -t ed25519 -f "$SSH_KEY" -N "" -C "orizon-agent-${NODE_ID}"
    echo ""
    echo "⚠️  IMPORTANT: You need to register this public key on the hub server!"
    echo ""
    echo "Public key:"
    cat "${SSH_KEY}.pub"
    echo ""
    echo "Add this key to: /etc/orizon/authorized_keys/${NODE_ID}"
    echo "on the hub server (${HUB_HOST})"
    echo ""
    read -p "Press Enter after registering the key..."
fi

# Test SSH connection
echo "🔍 Testing SSH connection to hub..."
if ! ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
    -p "$HUB_SSH_PORT" "${NODE_ID}@${HUB_HOST}" exit 2>/dev/null; then
    echo "❌ SSH connection failed. Make sure the public key is registered on the hub."
    echo ""
    echo "Run this on the hub server (139.59.149.48):"
    echo ""
    echo "  sudo mkdir -p /etc/orizon/authorized_keys"
    echo "  sudo tee /etc/orizon/authorized_keys/${NODE_ID} << 'EOF'"
    cat "${SSH_KEY}.pub"
    echo "EOF"
    echo ""
    exit 1
fi

echo "✅ SSH connection successful!"

# Create systemd service for reverse tunnels
echo ""
echo "🚀 Creating systemd service..."

cat > /etc/systemd/system/orizon-tunnels.service << EOF
[Unit]
Description=Orizon Zero Trust Reverse Tunnels
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=root

# Create reverse tunnels:
# -R remote:localhost:local = expose local port on remote
# Service tunnel: expose this node's service endpoint
# Terminal tunnel: expose this node's SSH (22) on hub's port 10000
ExecStart=/usr/bin/autossh -M 0 -N \
    -o "ServerAliveInterval=30" \
    -o "ServerAliveCountMax=3" \
    -o "ExitOnForwardFailure=yes" \
    -o "StrictHostKeyChecking=no" \
    -i ${SSH_KEY} \
    -p ${HUB_SSH_PORT} \
    -R ${TERMINAL_PORT}:localhost:22 \
    ${NODE_ID}@${HUB_HOST}

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable orizon-tunnels
systemctl restart orizon-tunnels

echo ""
echo "⏳ Waiting for tunnel to establish..."
sleep 5

# Check status
if systemctl is-active --quiet orizon-tunnels; then
    echo "✅ Tunnels are active!"
    echo ""
    echo "📊 Tunnel status:"
    echo "   Terminal: localhost:22 -> ${HUB_HOST}:${TERMINAL_PORT}"
    echo ""
    echo "You can now access this node via the Orizon web terminal!"
else
    echo "❌ Tunnel service failed to start"
    echo "Check logs with: journalctl -u orizon-tunnels -n 50"
    exit 1
fi

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║  ✅ TUNNEL SETUP COMPLETE                                  ║"
echo "╠════════════════════════════════════════════════════════════╣"
echo "║  Useful commands:                                          ║"
echo "║  - Check status: systemctl status orizon-tunnels           ║"
echo "║  - View logs: journalctl -u orizon-tunnels -f              ║"
echo "║  - Restart: systemctl restart orizon-tunnels               ║"
echo "╚════════════════════════════════════════════════════════════╝"
