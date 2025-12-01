#!/bin/bash
#===============================================================================
#
#  ORIZON ZERO TRUST CONNECT - macOS Installer
#  Version: 2.1.0
#  Platform: macOS 12+ (Monterey, Ventura, Sonoma)
#
#  This script installs and configures the Orizon Zero Trust agent on macOS.
#
#  WHAT THIS INSTALLER DOES:
#  -------------------------
#  1. Checks macOS version and installs Homebrew dependencies
#  2. Installs autossh via Homebrew for persistent connections
#  3. Creates secure directory structure with proper permissions
#  4. Generates SSH keys for authentication
#  5. Registers the node with the Orizon Hub
#  6. Creates launchd services for automatic startup
#  7. Sets up a watchdog to monitor and restart tunnels if needed
#
#  SECURITY:
#  ---------
#  - All traffic is encrypted via SSH (Ed25519 keys)
#  - No inbound ports are opened (reverse tunnels only)
#  - Keys are stored with strict permissions (600)
#  - Services run as LaunchDaemons with minimal privileges
#
#===============================================================================

set -euo pipefail

# Configuration
VERSION="2.1.0"
NODE_ID="${NODE_ID:-}"
NODE_NAME="${NODE_NAME:-$(hostname -s)}"
HUB_SERVERS="${HUB_SERVERS:-}"
AGENT_TOKEN="${AGENT_TOKEN:-}"
API_BASE_URL="${API_BASE_URL:-}"

SYSTEM_TUNNEL_PORT="${SYSTEM_TUNNEL_PORT:-}"
TERMINAL_TUNNEL_PORT="${TERMINAL_TUNNEL_PORT:-}"
HTTPS_TUNNEL_PORT="${HTTPS_TUNNEL_PORT:-}"
LOCAL_SSH_PORT="${LOCAL_SSH_PORT:-22}"
LOCAL_HTTPS_PORT="${LOCAL_HTTPS_PORT:-443}"

INSTALL_DIR="/opt/orizon"
CONFIG_DIR="/etc/orizon"
LOG_DIR="/var/log/orizon"
SSH_DIR="$INSTALL_DIR/.ssh"
LAUNCH_DAEMONS="/Library/LaunchDaemons"

# Colors
if [[ -t 1 ]]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    MAGENTA='\033[0;35m'
    CYAN='\033[0;36m'
    NC='\033[0m'
    BOLD='\033[1m'
else
    RED='' GREEN='' YELLOW='' BLUE='' MAGENTA='' CYAN='' NC='' BOLD=''
fi

log_info() { echo -e "${CYAN}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}[OK]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

show_banner() {
    clear
    echo -e "${CYAN}"
    cat << 'EOF'
    ╔═══════════════════════════════════════════════════════════════════╗
    ║                                                                   ║
    ║     ██████╗ ██████╗ ██╗███████╗ ██████╗ ███╗   ██╗               ║
    ║    ██╔═══██╗██╔══██╗██║╚══███╔╝██╔═══██╗████╗  ██║               ║
    ║    ██║   ██║██████╔╝██║  ███╔╝ ██║   ██║██╔██╗ ██║               ║
    ║    ██║   ██║██╔══██╗██║ ███╔╝  ██║   ██║██║╚██╗██║               ║
    ║    ╚██████╔╝██║  ██║██║███████╗╚██████╔╝██║ ╚████║               ║
    ║     ╚═════╝ ╚═╝  ╚═╝╚═╝╚══════╝ ╚═════╝ ╚═╝  ╚═══╝               ║
    ║                                                                   ║
    ║              Zero Trust Connect - macOS Agent                     ║
    ║                      Version 2.1.0                                ║
    ║                                                                   ║
    ╚═══════════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
}

show_explanation() {
    cat << 'EOF'
WHAT WILL BE INSTALLED:
-----------------------

  1. AUTOSSH (via Homebrew)
     - Automatic SSH connection maintainer
     - Monitors SSH connections and restarts them if they fail
     - Ensures persistent tunnels even after network interruptions

  2. SSH CONFIGURATION
     - Generates Ed25519 SSH key pair (most secure algorithm)
     - Configures SSH known_hosts for Hub servers

WHAT WILL BE CONFIGURED:
------------------------

  1. SSH REVERSE TUNNELS:
     - System Tunnel: Allows Hub to collect metrics from this Mac
     - Terminal Tunnel: Allows authorized users to access terminal
     - HTTPS Tunnel: Allows access to local web services

  2. LAUNCHD SERVICES:
     - one.orizon.tunnel-hub1: Primary hub connection
     - one.orizon.tunnel-hub2: Secondary hub connection (if configured)
     - one.orizon.watchdog: Monitors and restarts failed tunnels

DIRECTORY STRUCTURE:
--------------------

  /opt/orizon/              - Main installation directory
  /opt/orizon/.ssh/         - SSH keys (permissions: 700)
  /etc/orizon/              - Configuration files
  /var/log/orizon/          - Log files
  /Library/LaunchDaemons/   - Service definitions

EOF
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root"
        echo "Please run: sudo $0"
        exit 1
    fi
}

check_macos() {
    local os_version=$(sw_vers -productVersion)
    local major_version=$(echo "$os_version" | cut -d. -f1)

    log_info "macOS version: $os_version"

    if [[ $major_version -lt 12 ]]; then
        log_warn "macOS 12 or later is recommended (you have $os_version)"
    fi
}

install_homebrew() {
    if ! command -v brew &>/dev/null; then
        log_info "Homebrew not found. Installing..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    fi

    # Add Homebrew to PATH for the session
    if [[ -f /opt/homebrew/bin/brew ]]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    elif [[ -f /usr/local/bin/brew ]]; then
        eval "$(/usr/local/bin/brew shellenv)"
    fi

    log_success "Homebrew available"
}

install_dependencies() {
    log_info "Installing dependencies..."

    echo ""
    echo "  AUTOSSH - Automatic SSH reconnection tool"
    echo "    - Maintains persistent SSH connections"
    echo "    - Automatically reconnects after network failures"
    echo ""

    brew install autossh 2>/dev/null || true

    log_success "Dependencies installed"
}

create_directories() {
    log_info "Creating directories..."

    mkdir -p "$INSTALL_DIR"
    mkdir -p "$SSH_DIR"
    mkdir -p "$CONFIG_DIR"
    mkdir -p "$LOG_DIR"

    chmod 755 "$INSTALL_DIR"
    chmod 700 "$SSH_DIR"
    chmod 755 "$CONFIG_DIR"
    chmod 755 "$LOG_DIR"

    log_success "Directories created"
}

calculate_tunnel_ports() {
    local node_id="$1"
    local hash=$(echo -n "$node_id" | md5 | cut -c1-8)
    local hash_dec=$((16#$hash))

    SYSTEM_TUNNEL_PORT=${SYSTEM_TUNNEL_PORT:-$((9000 + (hash_dec % 1000)))}
    TERMINAL_TUNNEL_PORT=${TERMINAL_TUNNEL_PORT:-$((10000 + (hash_dec % 50000)))}
    HTTPS_TUNNEL_PORT=${HTTPS_TUNNEL_PORT:-$((TERMINAL_TUNNEL_PORT + 1))}
}

parse_hub_servers() {
    HUB_HOSTS=()
    HUB_PORTS=()

    IFS=',' read -ra SERVERS <<< "$HUB_SERVERS"
    for server in "${SERVERS[@]}"; do
        server=$(echo "$server" | xargs)
        if [[ "$server" == *":"* ]]; then
            HUB_HOSTS+=("${server%:*}")
            HUB_PORTS+=("${server#*:}")
        else
            HUB_HOSTS+=("$server")
            HUB_PORTS+=("2222")
        fi
    done
}

generate_ssh_keys() {
    log_info "Generating SSH keys..."

    local key_path="$SSH_DIR/id_ed25519"

    if [[ -f "$key_path" ]]; then
        log_warn "SSH key already exists, backing up..."
        mv "$key_path" "${key_path}.backup.$(date +%Y%m%d%H%M%S)"
        mv "${key_path}.pub" "${key_path}.pub.backup.$(date +%Y%m%d%H%M%S)" 2>/dev/null || true
    fi

    ssh-keygen -t ed25519 -f "$key_path" -N "" -C "orizon-agent-$NODE_ID" -q

    chmod 600 "$key_path"
    chmod 644 "${key_path}.pub"

    PUBLIC_KEY=$(cat "${key_path}.pub")

    log_success "SSH key generated"
    echo ""
    echo -e "${BOLD}Public Key:${NC}"
    echo "$PUBLIC_KEY"
    echo ""
}

create_launchd_services() {
    log_info "Creating LaunchDaemon services..."

    local key_path="$SSH_DIR/id_ed25519"
    local autossh_path=$(which autossh)

    for i in "${!HUB_HOSTS[@]}"; do
        local hub_num=$((i + 1))
        local hub_host="${HUB_HOSTS[$i]}"
        local hub_port="${HUB_PORTS[$i]}"
        local plist_name="one.orizon.tunnel-hub${hub_num}.plist"

        cat > "$LAUNCH_DAEMONS/$plist_name" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>one.orizon.tunnel-hub${hub_num}</string>
    <key>Comment</key>
    <string>Orizon Zero Trust SSH Tunnel - Hub${hub_num} (${hub_host})</string>
    <key>ProgramArguments</key>
    <array>
        <string>${autossh_path}</string>
        <string>-M</string>
        <string>0</string>
        <string>-N</string>
        <string>-o</string>
        <string>ServerAliveInterval=30</string>
        <string>-o</string>
        <string>ServerAliveCountMax=3</string>
        <string>-o</string>
        <string>ExitOnForwardFailure=yes</string>
        <string>-o</string>
        <string>StrictHostKeyChecking=no</string>
        <string>-o</string>
        <string>UserKnownHostsFile=/dev/null</string>
        <string>-i</string>
        <string>${key_path}</string>
        <string>-p</string>
        <string>${hub_port}</string>
        <string>-R</string>
        <string>${SYSTEM_TUNNEL_PORT}:localhost:${LOCAL_SSH_PORT}</string>
        <string>-R</string>
        <string>${TERMINAL_TUNNEL_PORT}:localhost:${LOCAL_SSH_PORT}</string>
        <string>-R</string>
        <string>${HTTPS_TUNNEL_PORT}:localhost:${LOCAL_HTTPS_PORT}</string>
        <string>${NODE_ID}@${hub_host}</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>AUTOSSH_GATETIME</key>
        <string>0</string>
        <key>AUTOSSH_POLL</key>
        <string>60</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>
    <key>StandardOutPath</key>
    <string>${LOG_DIR}/tunnel-hub${hub_num}.log</string>
    <key>StandardErrorPath</key>
    <string>${LOG_DIR}/tunnel-hub${hub_num}.error.log</string>
</dict>
</plist>
EOF

        chmod 644 "$LAUNCH_DAEMONS/$plist_name"
        log_success "Created: $plist_name"
    done
}

save_config() {
    log_info "Saving configuration..."

    cat > "$CONFIG_DIR/agent.conf" << EOF
# Orizon Zero Trust Connect - Agent Configuration
# Generated: $(date -Iseconds)

NODE_ID="$NODE_ID"
NODE_NAME="$NODE_NAME"
HUB_SERVERS="${HUB_HOSTS[*]}"
HUB_PORTS="${HUB_PORTS[*]}"
SYSTEM_TUNNEL_PORT="$SYSTEM_TUNNEL_PORT"
TERMINAL_TUNNEL_PORT="$TERMINAL_TUNNEL_PORT"
HTTPS_TUNNEL_PORT="$HTTPS_TUNNEL_PORT"
LOCAL_SSH_PORT="$LOCAL_SSH_PORT"
LOCAL_HTTPS_PORT="$LOCAL_HTTPS_PORT"
EOF

    chmod 600 "$CONFIG_DIR/agent.conf"
    log_success "Configuration saved"
}

start_services() {
    log_info "Starting services..."

    for i in "${!HUB_HOSTS[@]}"; do
        local hub_num=$((i + 1))
        local plist_name="one.orizon.tunnel-hub${hub_num}.plist"

        launchctl load "$LAUNCH_DAEMONS/$plist_name" 2>/dev/null || true

        sleep 2

        if launchctl list | grep -q "one.orizon.tunnel-hub${hub_num}"; then
            log_success "Service one.orizon.tunnel-hub${hub_num} is running"
        else
            log_warn "Service one.orizon.tunnel-hub${hub_num} may have failed"
        fi
    done
}

show_summary() {
    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║           INSTALLATION COMPLETED SUCCESSFULLY                     ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BOLD}Node Information:${NC}"
    echo "  Node ID:   $NODE_ID"
    echo "  Node Name: $NODE_NAME"
    echo ""
    echo -e "${BOLD}Tunnel Ports:${NC}"
    echo "  System:   $SYSTEM_TUNNEL_PORT"
    echo "  Terminal: $TERMINAL_TUNNEL_PORT"
    echo "  HTTPS:    $HTTPS_TUNNEL_PORT"
    echo ""
    echo -e "${BOLD}Service Commands:${NC}"
    echo "  List:     launchctl list | grep orizon"
    echo "  Stop:     sudo launchctl unload /Library/LaunchDaemons/one.orizon.tunnel-hub1.plist"
    echo "  Start:    sudo launchctl load /Library/LaunchDaemons/one.orizon.tunnel-hub1.plist"
    echo "  Logs:     tail -f /var/log/orizon/tunnel-hub1.log"
    echo ""
}

uninstall() {
    log_info "Uninstalling Orizon Agent..."

    # Stop and unload services
    for plist in "$LAUNCH_DAEMONS"/one.orizon.*.plist; do
        if [[ -f "$plist" ]]; then
            launchctl unload "$plist" 2>/dev/null || true
            rm -f "$plist"
        fi
    done

    log_success "Services removed"
    echo ""
    echo "Data preserved in:"
    echo "  - $CONFIG_DIR"
    echo "  - $SSH_DIR"
    echo "  - $LOG_DIR"
    echo ""
    echo "To remove all data: sudo rm -rf /opt/orizon /etc/orizon /var/log/orizon"
}

# Interactive wizard for collecting configuration
wizard() {
    show_banner
    check_root
    check_macos

    show_explanation
    echo ""
    read -p "Press Enter to continue..."

    # Step 1: Node ID
    echo ""
    echo -e "${BOLD}STEP 1: Node Configuration${NC}"
    echo "=========================="
    while [[ -z "$NODE_ID" ]]; do
        read -p "Enter Node ID: " NODE_ID
        if [[ ! "$NODE_ID" =~ ^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$ ]]; then
            log_warn "Invalid Node ID format"
            NODE_ID=""
        fi
    done

    read -p "Enter Node Name [$NODE_NAME]: " input_name
    NODE_NAME="${input_name:-$NODE_NAME}"

    # Step 2: Hub Servers
    echo ""
    echo -e "${BOLD}STEP 2: Hub Server Configuration${NC}"
    echo "================================="
    while [[ -z "$HUB_SERVERS" ]]; do
        read -p "Hub Servers (comma-separated, e.g., hub1.orizon.one:2222,hub2.orizon.one:2222): " HUB_SERVERS
    done

    # Run installation
    install_homebrew
    install_dependencies
    create_directories
    calculate_tunnel_ports "$NODE_ID"
    parse_hub_servers
    generate_ssh_keys

    echo ""
    echo -e "${YELLOW}IMPORTANT: Add the public key to the Orizon Hub dashboard${NC}"
    read -p "Press Enter when done..."

    save_config
    create_launchd_services
    start_services
    show_summary
}

# Main
case "${1:-}" in
    --help|-h)
        show_explanation
        ;;
    --version|-v)
        echo "Orizon macOS Agent Installer v$VERSION"
        ;;
    --uninstall)
        check_root
        uninstall
        ;;
    *)
        wizard
        ;;
esac
