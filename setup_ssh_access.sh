#!/bin/bash

#############################################
# Orizon ZTC Hub - SSH Access Setup Script
# For: Marco @ Syneto/Orizon
#############################################

set -e

HUB_IP="46.101.189.126"
HUB_USER="root"
SSH_KEY_PATH="$HOME/.ssh/orizon_hub_key"
SSH_CONFIG="$HOME/.ssh/config"

echo "=========================================="
echo "🔐 Orizon ZTC Hub - SSH Access Setup"
echo "=========================================="
echo ""

# Check if SSH key already exists
if [ -f "$SSH_KEY_PATH" ]; then
    echo "⚠️  SSH key already exists at: $SSH_KEY_PATH"
    read -p "Do you want to use the existing key? (y/n): " use_existing
    if [ "$use_existing" != "y" ]; then
        echo "❌ Aborted. Remove the old key or use a different name."
        exit 1
    fi
else
    echo "📝 Generating new SSH key..."
    ssh-keygen -t ed25519 -C "admin@orizon-ztc" -f "$SSH_KEY_PATH"
    echo "✅ SSH key generated!"
    echo ""
fi

# Show public key
echo "=========================================="
echo "📋 Your SSH Public Key:"
echo "=========================================="
cat "${SSH_KEY_PATH}.pub"
echo ""
echo "=========================================="
echo ""

# Instructions
echo "📌 NEXT STEPS:"
echo ""
echo "1️⃣  Copy the public key above to clipboard"
echo ""
echo "2️⃣  Add it to the server using ONE of these methods:"
echo ""
echo "   Method A - Via DigitalOcean Console:"
echo "   • Go to: https://cloud.digitalocean.com"
echo "   • Droplets → Your Droplet → Access → Launch Console"
echo "   • Run: mkdir -p ~/.ssh && nano ~/.ssh/authorized_keys"
echo "   • Paste the public key, save (Ctrl+X, Y, Enter)"
echo "   • Run: chmod 600 ~/.ssh/authorized_keys"
echo ""
echo "   Method B - Via ssh-copy-id (if you have password):"
echo "   • Run: ssh-copy-id -i ${SSH_KEY_PATH}.pub $HUB_USER@$HUB_IP"
echo ""
echo "   Method C - Via DigitalOcean Dashboard:"
echo "   • Account → Settings → Security → SSH Keys → Add SSH Key"
echo "   • Paste the public key, then add to your droplet"
echo ""

read -p "Press Enter when you've added the key to the server..."

# Test connection
echo ""
echo "🧪 Testing SSH connection..."
if ssh -i "$SSH_KEY_PATH" -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$HUB_USER@$HUB_IP" "echo 'SSH connection successful!'" 2>/dev/null; then
    echo "✅ SSH connection works!"
    echo ""

    # Add to SSH config
    if ! grep -q "Host orizon-hub" "$SSH_CONFIG" 2>/dev/null; then
        echo "📝 Adding SSH config..."
        mkdir -p ~/.ssh
        cat >> "$SSH_CONFIG" <<EOF

# Orizon ZTC Hub
Host orizon-hub
    HostName $HUB_IP
    User $HUB_USER
    Port 22
    IdentityFile $SSH_KEY_PATH
    ServerAliveInterval 60
    ServerAliveCountMax 3
EOF
        echo "✅ SSH config added!"
    else
        echo "⚠️  SSH config already exists for 'orizon-hub'"
    fi

    echo ""
    echo "=========================================="
    echo "🎉 Setup Complete!"
    echo "=========================================="
    echo ""
    echo "You can now connect using:"
    echo ""
    echo "  ssh orizon-hub"
    echo ""
    echo "Or directly:"
    echo ""
    echo "  ssh -i $SSH_KEY_PATH $HUB_USER@$HUB_IP"
    echo ""

else
    echo "❌ SSH connection failed!"
    echo ""
    echo "Troubleshooting:"
    echo "1. Make sure you've added the public key to the server"
    echo "2. Check DigitalOcean firewall allows SSH (port 22)"
    echo "3. Try connecting via DigitalOcean Console"
    echo ""
    echo "For detailed help, see: SSH_ACCESS_GUIDE.md"
    exit 1
fi

# Security recommendations
echo "=========================================="
echo "🔒 Security Recommendations"
echo "=========================================="
echo ""
echo "After first login, run these commands on the server:"
echo ""
echo "1. Disable password authentication:"
echo "   sudo nano /etc/ssh/sshd_config"
echo "   # Set: PasswordAuthentication no"
echo "   sudo systemctl restart sshd"
echo ""
echo "2. Install Fail2Ban (brute-force protection):"
echo "   sudo apt update && sudo apt install fail2ban -y"
echo "   sudo systemctl enable fail2ban"
echo ""
echo "3. Setup firewall:"
echo "   sudo ufw allow 22/tcp"
echo "   sudo ufw allow 8000/tcp  # Backend API"
echo "   sudo ufw allow 3000/tcp  # Frontend"
echo "   sudo ufw enable"
echo ""
echo "=========================================="
