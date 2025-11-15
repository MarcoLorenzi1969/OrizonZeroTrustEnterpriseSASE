#!/bin/bash
#
# Orizon Zero Trust Connect - Agent Installer
# For: Linux and macOS
# Version: 1.0.0
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
AGENT_NAME="orizon-agent"
AGENT_VERSION="1.0.0"
HUB_HOST="${HUB_HOST:-46.101.189.126}"
NODE_TOKEN="${NODE_TOKEN:-}"
INSTALL_DIR="/opt/orizon"
CONFIG_DIR="/etc/orizon"
LOG_DIR="/var/log/orizon"
SERVICE_NAME="orizon-agent"

# Detect OS
OS=$(uname -s)
ARCH=$(uname -m)

echo -e "${BLUE}╔════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     Orizon Zero Trust Connect - Agent Installer    ║${NC}"
echo -e "${BLUE}║              For Syneto/Orizon Security            ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Version:${NC} $AGENT_VERSION"
echo -e "${GREEN}System:${NC} $OS $ARCH"
echo -e "${GREEN}Hub:${NC} $HUB_HOST"
echo ""

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}Error: This script must be run as root${NC}"
   echo "Please run: sudo $0"
   exit 1
fi

# Function to check dependencies
check_dependencies() {
    echo -e "${YELLOW}Checking dependencies...${NC}"
    
    local deps=("python3" "pip3" "ssh" "curl")
    local missing_deps=()
    
    for dep in "${deps[@]}"; do
        if ! command -v $dep &> /dev/null; then
            missing_deps+=($dep)
        else
            echo -e "  ✅ $dep found"
        fi
    done
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        echo -e "${RED}Missing dependencies: ${missing_deps[*]}${NC}"
        echo -e "${YELLOW}Installing missing dependencies...${NC}"
        
        if [ "$OS" == "Linux" ]; then
            if command -v apt-get &> /dev/null; then
                apt-get update
                apt-get install -y python3 python3-pip openssh-client curl
            elif command -v yum &> /dev/null; then
                yum install -y python3 python3-pip openssh-clients curl
            else
                echo -e "${RED}Unsupported Linux distribution${NC}"
                exit 1
            fi
        elif [ "$OS" == "Darwin" ]; then
            if ! command -v brew &> /dev/null; then
                echo -e "${RED}Homebrew is required on macOS${NC}"
                echo "Install from: https://brew.sh"
                exit 1
            fi
            brew install python3 openssh curl
        fi
    fi
}

# Function to create directories
create_directories() {
    echo -e "${YELLOW}Creating directories...${NC}"
    
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$CONFIG_DIR"
    mkdir -p "$LOG_DIR"
    
    echo -e "  ✅ Created $INSTALL_DIR"
    echo -e "  ✅ Created $CONFIG_DIR"
    echo -e "  ✅ Created $LOG_DIR"
}

# Function to install Python dependencies
install_python_deps() {
    echo -e "${YELLOW}Installing Python dependencies...${NC}"
    
    pip3 install --upgrade pip
    pip3 install requests websocket-client psutil
    
    echo -e "  ✅ Python dependencies installed"
}

# Function to download and install agent
install_agent() {
    echo -e "${YELLOW}Installing agent...${NC}"
    
    # Copy agent file (in production would download from server)
    if [ -f "orizon_agent.py" ]; then
        cp orizon_agent.py "$INSTALL_DIR/orizon_agent.py"
    else
        # Download from hub
        curl -sSL "https://$HUB_HOST/downloads/agent/orizon_agent.py" -o "$INSTALL_DIR/orizon_agent.py" || {
            echo -e "${RED}Failed to download agent${NC}"
            # Use embedded version as fallback
            cat > "$INSTALL_DIR/orizon_agent.py" << 'EMBEDDED_AGENT'
# Embedded agent code would go here
# This is a placeholder - actual code would be embedded
EMBEDDED_AGENT
        }
    fi
    
    chmod +x "$INSTALL_DIR/orizon_agent.py"
    
    # Create wrapper script
    cat > "$INSTALL_DIR/orizon-agent" << EOF
#!/bin/bash
exec /usr/bin/python3 $INSTALL_DIR/orizon_agent.py "\$@"
EOF
    chmod +x "$INSTALL_DIR/orizon-agent"
    
    # Create symlink
    ln -sf "$INSTALL_DIR/orizon-agent" /usr/local/bin/orizon-agent
    
    echo -e "  ✅ Agent installed to $INSTALL_DIR"
}

# Function to generate configuration
generate_config() {
    echo -e "${YELLOW}Generating configuration...${NC}"
    
    # Prompt for node token if not provided
    if [ -z "$NODE_TOKEN" ]; then
        read -p "Enter Node Token (press Enter to skip): " NODE_TOKEN
    fi
    
    cat > "$CONFIG_DIR/agent.json" << EOF
{
    "hub_host": "$HUB_HOST",
    "hub_ssh_port": 2222,
    "hub_https_port": 8443,
    "api_endpoint": "https://$HUB_HOST:8443/api/v1",
    "node_token": "$NODE_TOKEN",
    "reconnect_delay": 5,
    "max_reconnect_delay": 300,
    "health_check_interval": 30,
    "log_level": "INFO",
    "log_file": "$LOG_DIR/agent.log"
}
EOF
    
    chmod 600 "$CONFIG_DIR/agent.json"
    
    echo -e "  ✅ Configuration saved to $CONFIG_DIR/agent.json"
}

# Function to setup SSH keys
setup_ssh_keys() {
    echo -e "${YELLOW}Setting up SSH keys...${NC}"
    
    SSH_DIR="$INSTALL_DIR/.ssh"
    mkdir -p "$SSH_DIR"
    
    if [ ! -f "$SSH_DIR/id_rsa" ]; then
        ssh-keygen -t rsa -b 4096 -f "$SSH_DIR/id_rsa" -N "" -C "orizon-agent@$(hostname)"
        echo -e "  ✅ SSH key generated"
    else
        echo -e "  ℹ️  SSH key already exists"
    fi
    
    # Display public key
    echo ""
    echo -e "${GREEN}SSH Public Key (add this to hub authorized_keys):${NC}"
    echo "----------------------------------------"
    cat "$SSH_DIR/id_rsa.pub"
    echo "----------------------------------------"
}

# Function to install systemd service (Linux)
install_systemd_service() {
    echo -e "${YELLOW}Installing systemd service...${NC}"
    
    cat > "/etc/systemd/system/$SERVICE_NAME.service" << EOF
[Unit]
Description=Orizon Zero Trust Connect Agent
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/orizon-agent -c $CONFIG_DIR/agent.json
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=orizon-agent

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$LOG_DIR

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    systemctl enable "$SERVICE_NAME"
    
    echo -e "  ✅ Systemd service installed"
}

# Function to install launchd service (macOS)
install_launchd_service() {
    echo -e "${YELLOW}Installing launchd service...${NC}"
    
    cat > "/Library/LaunchDaemons/com.orizon.agent.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.orizon.agent</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/orizon-agent</string>
        <string>-c</string>
        <string>$CONFIG_DIR/agent.json</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>
    <key>StandardOutPath</key>
    <string>$LOG_DIR/agent.log</string>
    <key>StandardErrorPath</key>
    <string>$LOG_DIR/agent.error.log</string>
</dict>
</plist>
EOF
    
    launchctl load "/Library/LaunchDaemons/com.orizon.agent.plist"
    
    echo -e "  ✅ Launchd service installed"
}

# Function to start the service
start_service() {
    echo -e "${YELLOW}Starting service...${NC}"
    
    if [ "$OS" == "Linux" ]; then
        systemctl start "$SERVICE_NAME"
        systemctl status "$SERVICE_NAME" --no-pager | head -10
    elif [ "$OS" == "Darwin" ]; then
        launchctl start com.orizon.agent
        launchctl list | grep orizon
    fi
    
    echo -e "  ✅ Service started"
}

# Function to show status
show_status() {
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║           Installation Completed Successfully!       ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BLUE}Service Commands:${NC}"
    if [ "$OS" == "Linux" ]; then
        echo "  Start:   systemctl start $SERVICE_NAME"
        echo "  Stop:    systemctl stop $SERVICE_NAME"
        echo "  Status:  systemctl status $SERVICE_NAME"
        echo "  Logs:    journalctl -u $SERVICE_NAME -f"
    elif [ "$OS" == "Darwin" ]; then
        echo "  Start:   launchctl start com.orizon.agent"
        echo "  Stop:    launchctl stop com.orizon.agent"
        echo "  Status:  launchctl list | grep orizon"
        echo "  Logs:    tail -f $LOG_DIR/agent.log"
    fi
    echo ""
    echo -e "${BLUE}Configuration:${NC} $CONFIG_DIR/agent.json"
    echo -e "${BLUE}Logs:${NC} $LOG_DIR/agent.log"
    echo ""
    echo -e "${GREEN}Agent is now running and connected to hub!${NC}"
}

# Main installation flow
main() {
    echo -e "${YELLOW}Starting installation...${NC}"
    echo ""
    
    check_dependencies
    create_directories
    install_python_deps
    install_agent
    generate_config
    setup_ssh_keys
    
    if [ "$OS" == "Linux" ]; then
        install_systemd_service
    elif [ "$OS" == "Darwin" ]; then
        install_launchd_service
    else
        echo -e "${RED}Unsupported OS: $OS${NC}"
        exit 1
    fi
    
    start_service
    show_status
}

# Uninstall function
uninstall() {
    echo -e "${RED}Uninstalling Orizon Agent...${NC}"
    
    if [ "$OS" == "Linux" ]; then
        systemctl stop "$SERVICE_NAME" 2>/dev/null || true
        systemctl disable "$SERVICE_NAME" 2>/dev/null || true
        rm -f "/etc/systemd/system/$SERVICE_NAME.service"
        systemctl daemon-reload
    elif [ "$OS" == "Darwin" ]; then
        launchctl unload "/Library/LaunchDaemons/com.orizon.agent.plist" 2>/dev/null || true
        rm -f "/Library/LaunchDaemons/com.orizon.agent.plist"
    fi
    
    rm -rf "$INSTALL_DIR"
    rm -rf "$CONFIG_DIR"
    rm -rf "$LOG_DIR"
    rm -f /usr/local/bin/orizon-agent
    
    echo -e "${GREEN}Uninstall completed${NC}"
}

# Parse arguments
case "${1:-}" in
    uninstall|remove)
        uninstall
        ;;
    *)
        main
        ;;
esac
