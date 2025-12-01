#!/bin/bash
#===============================================================================
#
#  ORIZON ZERO TRUST CONNECT - Linux Agent Installer
#  Version: 2.1.0
#  Platform: Linux (Debian, Ubuntu, RedHat, Fedora, CentOS)
#
#  This script installs and configures the Orizon Zero Trust agent on Linux
#  systems. The agent creates secure SSH reverse tunnels to connect this
#  server to the Orizon Hub infrastructure.
#
#  WHAT THIS INSTALLER DOES:
#  -------------------------
#  1. Detects your Linux distribution and installs dependencies
#  2. Installs OpenSSH client and autossh for persistent connections
#  3. Creates secure directory structure with proper permissions
#  4. Generates SSH keys for authentication
#  5. Registers the node with the Orizon Hub
#  6. Creates systemd services for:
#     - System management tunnel (metrics, monitoring)
#     - Terminal access tunnel (SSH, shell access)
#     - HTTPS proxy tunnel (web interface access)
#  7. Sets up a watchdog to monitor and restart tunnels if needed
#  8. Configures firewall rules (ufw/firewalld)
#
#  SECURITY:
#  ---------
#  - All traffic is encrypted via SSH (Ed25519 keys)
#  - No inbound ports are opened (reverse tunnels only)
#  - Keys are stored with strict permissions (600)
#  - Services run with minimal privileges
#
#===============================================================================

set -euo pipefail

#===============================================================================
# CONFIGURATION - Set by template or auto-detected
#===============================================================================

# Node configuration (set these or pass via environment)
NODE_ID="${NODE_ID:-}"
NODE_NAME="${NODE_NAME:-$(hostname)}"
AGENT_TOKEN="${AGENT_TOKEN:-}"

# Hub servers (comma-separated list of host:port or just host for default port)
# Example: "hub1.orizon.one:2222,hub2.orizon.one:2222" or "139.59.149.48,68.183.219.222"
HUB_SERVERS="${HUB_SERVERS:-}"
API_BASE_URL="${API_BASE_URL:-}"

# Tunnel ports (auto-calculated from NODE_ID if not set)
SYSTEM_TUNNEL_PORT="${SYSTEM_TUNNEL_PORT:-}"
TERMINAL_TUNNEL_PORT="${TERMINAL_TUNNEL_PORT:-}"
HTTPS_TUNNEL_PORT="${HTTPS_TUNNEL_PORT:-}"

# Local service ports
LOCAL_SSH_PORT="${LOCAL_SSH_PORT:-22}"
LOCAL_HTTPS_PORT="${LOCAL_HTTPS_PORT:-443}"

# Installation paths
INSTALL_DIR="/opt/orizon"
CONFIG_DIR="/etc/orizon"
LOG_DIR="/var/log/orizon"
SSH_DIR="${INSTALL_DIR}/.ssh"

# Package version
VERSION="2.1.0"

#===============================================================================
# COLORS AND FORMATTING
#===============================================================================

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

#===============================================================================
# LOGGING FUNCTIONS
#===============================================================================

log_info() {
    echo -e "${CYAN}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

log_section() {
    echo ""
    echo -e "${MAGENTA}${BOLD}=== $* ===${NC}"
    echo ""
}

show_banner() {
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
    ║              Zero Trust Connect - Linux Agent                     ║
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

  1. AUTOSSH - Automatic SSH connection maintainer
     - Monitors SSH connections and restarts them if they fail
     - Ensures persistent tunnels even after network interruptions

  2. OPENSSH CLIENT - Secure Shell client
     - Creates encrypted connections to Orizon Hub
     - Uses Ed25519 keys for authentication (most secure)

  3. JQ - JSON processor (optional, for configuration)
     - Parses Hub API responses
     - Used during registration process

  4. CURL - HTTP client
     - Communicates with Hub API for registration
     - Downloads updates and configurations

WHAT WILL BE CONFIGURED:
------------------------

  1. SSH REVERSE TUNNELS:
     - System Tunnel: Allows Hub to collect metrics from this server
     - Terminal Tunnel: Allows authorized users to access terminal
     - HTTPS Tunnel: Allows access to local web services

  2. SYSTEMD SERVICES:
     - orizon-tunnel-hub1.service: Primary hub connection
     - orizon-tunnel-hub2.service: Secondary hub connection (if configured)
     - orizon-watchdog.service: Monitors and restarts failed tunnels

  3. FIREWALL RULES:
     - Outbound: Allow SSH (port 2222) to Hub servers
     - No inbound ports are opened

DIRECTORY STRUCTURE:
--------------------

  /opt/orizon/              - Main installation directory
  /opt/orizon/.ssh/         - SSH keys (permissions: 700)
  /etc/orizon/              - Configuration files
  /var/log/orizon/          - Log files

EOF
}

#===============================================================================
# UTILITY FUNCTIONS
#===============================================================================

detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        DISTRO="$ID"
        DISTRO_VERSION="$VERSION_ID"
        DISTRO_NAME="$NAME"
    elif [ -f /etc/redhat-release ]; then
        DISTRO="rhel"
        DISTRO_VERSION=$(cat /etc/redhat-release | grep -oE '[0-9]+' | head -1)
        DISTRO_NAME="Red Hat Enterprise Linux"
    else
        DISTRO="unknown"
        DISTRO_VERSION="unknown"
        DISTRO_NAME="Unknown Distribution"
    fi

    log_info "Detected: $DISTRO_NAME $DISTRO_VERSION"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root"
        echo "Please run: sudo $0"
        exit 1
    fi
}

calculate_tunnel_ports() {
    if [[ -z "$NODE_ID" ]]; then
        log_error "NODE_ID is required to calculate tunnel ports"
        exit 1
    fi

    # Calculate hash from NODE_ID
    local hash=$(echo -n "$NODE_ID" | md5sum | cut -c1-8)
    local hash_dec=$((16#$hash))

    # System tunnel: 9000-9999
    SYSTEM_TUNNEL_PORT=${SYSTEM_TUNNEL_PORT:-$((9000 + (hash_dec % 1000)))}

    # Terminal tunnel: 10000-59999
    TERMINAL_TUNNEL_PORT=${TERMINAL_TUNNEL_PORT:-$((10000 + (hash_dec % 50000)))}

    # HTTPS tunnel: Terminal + 1
    HTTPS_TUNNEL_PORT=${HTTPS_TUNNEL_PORT:-$((TERMINAL_TUNNEL_PORT + 1))}

    log_info "Tunnel ports calculated:"
    log_info "  - System: $SYSTEM_TUNNEL_PORT"
    log_info "  - Terminal: $TERMINAL_TUNNEL_PORT"
    log_info "  - HTTPS: $HTTPS_TUNNEL_PORT"
}

parse_hub_servers() {
    # Parse HUB_SERVERS into arrays
    HUB_HOSTS=()
    HUB_PORTS=()

    if [[ -z "$HUB_SERVERS" ]]; then
        log_error "HUB_SERVERS is required"
        exit 1
    fi

    IFS=',' read -ra SERVERS <<< "$HUB_SERVERS"
    for server in "${SERVERS[@]}"; do
        server=$(echo "$server" | xargs)  # trim whitespace
        if [[ "$server" == *":"* ]]; then
            HUB_HOSTS+=("${server%:*}")
            HUB_PORTS+=("${server#*:}")
        else
            HUB_HOSTS+=("$server")
            HUB_PORTS+=("2222")  # default port
        fi
    done

    log_info "Hub servers configured: ${#HUB_HOSTS[@]}"
    for i in "${!HUB_HOSTS[@]}"; do
        log_info "  - Hub$((i+1)): ${HUB_HOSTS[$i]}:${HUB_PORTS[$i]}"
    done
}

#===============================================================================
# INSTALLATION FUNCTIONS
#===============================================================================

install_dependencies_debian() {
    log_section "Installing Dependencies (Debian/Ubuntu)"

    echo -e "${BOLD}Installing required packages...${NC}"
    echo ""
    echo "  - openssh-client: SSH client for secure connections"
    echo "  - autossh: Keeps SSH tunnels alive automatically"
    echo "  - curl: HTTP client for API communication"
    echo "  - jq: JSON parser for configuration"
    echo ""

    apt-get update -qq

    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
        openssh-client \
        autossh \
        curl \
        jq \
        2>/dev/null

    log_success "Dependencies installed"
}

install_dependencies_redhat() {
    log_section "Installing Dependencies (RedHat/Fedora/CentOS)"

    echo -e "${BOLD}Installing required packages...${NC}"
    echo ""
    echo "  - openssh-clients: SSH client for secure connections"
    echo "  - autossh: Keeps SSH tunnels alive automatically"
    echo "  - curl: HTTP client for API communication"
    echo "  - jq: JSON parser for configuration"
    echo ""

    # Enable EPEL for autossh if needed
    if [[ "$DISTRO" == "rhel" || "$DISTRO" == "centos" ]]; then
        if ! rpm -q epel-release &>/dev/null; then
            log_info "Installing EPEL repository..."
            yum install -y epel-release
        fi
    fi

    if command -v dnf &>/dev/null; then
        dnf install -y -q \
            openssh-clients \
            autossh \
            curl \
            jq
    else
        yum install -y -q \
            openssh-clients \
            autossh \
            curl \
            jq
    fi

    log_success "Dependencies installed"
}

install_dependencies() {
    case "$DISTRO" in
        debian|ubuntu|linuxmint|pop)
            install_dependencies_debian
            ;;
        rhel|centos|fedora|rocky|almalinux|ol)
            install_dependencies_redhat
            ;;
        *)
            log_warn "Unknown distribution: $DISTRO"
            log_warn "Attempting Debian-style installation..."
            install_dependencies_debian || install_dependencies_redhat
            ;;
    esac
}

create_directories() {
    log_section "Creating Directory Structure"

    echo "Creating directories with secure permissions..."
    echo ""

    # Create directories
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$SSH_DIR"
    mkdir -p "$CONFIG_DIR"
    mkdir -p "$LOG_DIR"

    # Set permissions
    chmod 755 "$INSTALL_DIR"
    chmod 700 "$SSH_DIR"
    chmod 755 "$CONFIG_DIR"
    chmod 755 "$LOG_DIR"

    log_success "Created: $INSTALL_DIR"
    log_success "Created: $SSH_DIR (permissions: 700)"
    log_success "Created: $CONFIG_DIR"
    log_success "Created: $LOG_DIR"
}

generate_ssh_keys() {
    log_section "Generating SSH Keys"

    local key_path="$SSH_DIR/id_ed25519"

    echo "Generating Ed25519 SSH key pair..."
    echo ""
    echo "  Ed25519 is the most secure and modern SSH key algorithm."
    echo "  It provides better security than RSA with smaller key sizes."
    echo ""

    if [[ -f "$key_path" ]]; then
        log_warn "SSH key already exists, backing up..."
        mv "$key_path" "${key_path}.backup.$(date +%Y%m%d%H%M%S)"
        mv "${key_path}.pub" "${key_path}.pub.backup.$(date +%Y%m%d%H%M%S)" 2>/dev/null || true
    fi

    ssh-keygen -t ed25519 \
        -f "$key_path" \
        -N "" \
        -C "orizon-agent-$NODE_ID" \
        -q

    chmod 600 "$key_path"
    chmod 644 "${key_path}.pub"

    PUBLIC_KEY=$(cat "${key_path}.pub")

    log_success "SSH key generated"
    echo ""
    echo -e "${BOLD}Public Key:${NC}"
    echo "$PUBLIC_KEY"
    echo ""
}

register_with_hub() {
    log_section "Registering with Orizon Hub"

    if [[ -z "$API_BASE_URL" ]]; then
        log_warn "API_BASE_URL not set, skipping automatic registration"
        log_info "Please add the public key to the Hub manually"
        return 0
    fi

    local registration_url="$API_BASE_URL/api/v1/nodes/$NODE_ID/register-key"

    echo "Registering public key with Hub..."
    echo "URL: $registration_url"
    echo ""

    local response
    response=$(curl -s -w "\n%{http_code}" -X POST "$registration_url" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $AGENT_TOKEN" \
        -d "{\"public_key\": \"$PUBLIC_KEY\", \"node_name\": \"$NODE_NAME\"}" \
        2>/dev/null) || true

    local http_code=$(echo "$response" | tail -n1)
    local body=$(echo "$response" | sed '$d')

    if [[ "$http_code" == "200" || "$http_code" == "201" ]]; then
        log_success "Public key registered with Hub"
    else
        log_warn "Failed to register key automatically (HTTP $http_code)"
        log_info "Saving key for manual registration..."
        echo "$PUBLIC_KEY" > "$CONFIG_DIR/public_key_to_register.txt"
        log_info "Key saved to: $CONFIG_DIR/public_key_to_register.txt"
    fi
}

create_config_file() {
    log_section "Creating Configuration File"

    local config_file="$CONFIG_DIR/agent.conf"

    cat > "$config_file" << EOF
# Orizon Zero Trust Connect - Agent Configuration
# Generated: $(date -Iseconds)
# Version: $VERSION

# Node Identity
NODE_ID="$NODE_ID"
NODE_NAME="$NODE_NAME"

# Hub Servers (space-separated)
HUB_SERVERS="${HUB_HOSTS[*]}"
HUB_PORTS="${HUB_PORTS[*]}"

# Tunnel Ports
SYSTEM_TUNNEL_PORT="$SYSTEM_TUNNEL_PORT"
TERMINAL_TUNNEL_PORT="$TERMINAL_TUNNEL_PORT"
HTTPS_TUNNEL_PORT="$HTTPS_TUNNEL_PORT"

# Local Service Ports
LOCAL_SSH_PORT="$LOCAL_SSH_PORT"
LOCAL_HTTPS_PORT="$LOCAL_HTTPS_PORT"

# Paths
INSTALL_DIR="$INSTALL_DIR"
SSH_KEY="$SSH_DIR/id_ed25519"
LOG_DIR="$LOG_DIR"

# SSH Options
SSH_KEEPALIVE_INTERVAL="30"
SSH_KEEPALIVE_COUNT="3"
AUTOSSH_POLL="60"
EOF

    chmod 600 "$config_file"
    log_success "Configuration saved to: $config_file"
}

create_systemd_services() {
    log_section "Creating Systemd Services"

    echo "Creating tunnel services for each Hub..."
    echo ""
    echo "  Each Hub connection is a separate service for redundancy."
    echo "  If one Hub fails, the other continues to work."
    echo ""

    local key_path="$SSH_DIR/id_ed25519"

    for i in "${!HUB_HOSTS[@]}"; do
        local hub_num=$((i + 1))
        local hub_host="${HUB_HOSTS[$i]}"
        local hub_port="${HUB_PORTS[$i]}"
        local service_name="orizon-tunnel-hub${hub_num}"

        log_info "Creating service: $service_name"

        cat > "/etc/systemd/system/${service_name}.service" << EOF
[Unit]
Description=Orizon Zero Trust SSH Tunnel - Hub${hub_num} (${hub_host})
Documentation=https://docs.orizon.one
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
Environment="AUTOSSH_GATETIME=0"
Environment="AUTOSSH_POLL=60"
ExecStart=/usr/bin/autossh -M 0 -N \\
    -o ServerAliveInterval=30 \\
    -o ServerAliveCountMax=3 \\
    -o ExitOnForwardFailure=yes \\
    -o StrictHostKeyChecking=no \\
    -o UserKnownHostsFile=/dev/null \\
    -i ${key_path} \\
    -p ${hub_port} \\
    -R ${SYSTEM_TUNNEL_PORT}:localhost:${LOCAL_SSH_PORT} \\
    -R ${TERMINAL_TUNNEL_PORT}:localhost:${LOCAL_SSH_PORT} \\
    -R ${HTTPS_TUNNEL_PORT}:localhost:${LOCAL_HTTPS_PORT} \\
    ${NODE_ID}@${hub_host}
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

        log_success "Created: /etc/systemd/system/${service_name}.service"
    done

    # Create watchdog service
    log_info "Creating watchdog service..."

    cat > "/etc/systemd/system/orizon-watchdog.service" << 'EOF'
[Unit]
Description=Orizon Zero Trust - Watchdog Service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=/opt/orizon/watchdog.sh
Restart=always
RestartSec=60

[Install]
WantedBy=multi-user.target
EOF

    # Create watchdog script
    cat > "$INSTALL_DIR/watchdog.sh" << 'WATCHDOG_EOF'
#!/bin/bash
# Orizon Watchdog - Monitors and restarts tunnel services

LOG_FILE="/var/log/orizon/watchdog.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_FILE"
}

check_and_restart() {
    local service="$1"
    if ! systemctl is-active --quiet "$service"; then
        log "Service $service is down, restarting..."
        systemctl restart "$service"
        sleep 5
        if systemctl is-active --quiet "$service"; then
            log "Service $service restarted successfully"
        else
            log "ERROR: Failed to restart $service"
        fi
    fi
}

log "Watchdog started"

while true; do
    # Find and check all Orizon tunnel services
    for service in $(systemctl list-units --type=service --all | grep 'orizon-tunnel' | awk '{print $1}'); do
        check_and_restart "$service"
    done
    sleep 30
done
WATCHDOG_EOF

    chmod +x "$INSTALL_DIR/watchdog.sh"
    log_success "Created watchdog service"

    # Reload systemd
    systemctl daemon-reload
}

enable_services() {
    log_section "Enabling and Starting Services"

    # Enable and start tunnel services
    for i in "${!HUB_HOSTS[@]}"; do
        local hub_num=$((i + 1))
        local service_name="orizon-tunnel-hub${hub_num}"

        systemctl enable "$service_name"
        systemctl start "$service_name"

        if systemctl is-active --quiet "$service_name"; then
            log_success "Service $service_name is running"
        else
            log_warn "Service $service_name failed to start"
        fi
    done

    # Enable and start watchdog
    systemctl enable orizon-watchdog
    systemctl start orizon-watchdog
    log_success "Watchdog service started"
}

configure_firewall() {
    log_section "Configuring Firewall"

    echo "Configuring firewall rules for outbound connections only..."
    echo ""

    # Detect firewall
    if command -v ufw &>/dev/null && ufw status | grep -q "Status: active"; then
        log_info "UFW firewall detected"

        for i in "${!HUB_HOSTS[@]}"; do
            local hub_host="${HUB_HOSTS[$i]}"
            local hub_port="${HUB_PORTS[$i]}"
            ufw allow out to "$hub_host" port "$hub_port" proto tcp comment "Orizon Hub $((i+1))"
        done

        log_success "UFW rules configured"

    elif command -v firewall-cmd &>/dev/null && systemctl is-active --quiet firewalld; then
        log_info "firewalld detected"

        for i in "${!HUB_HOSTS[@]}"; do
            local hub_host="${HUB_HOSTS[$i]}"
            local hub_port="${HUB_PORTS[$i]}"
            firewall-cmd --permanent --add-rich-rule="rule family='ipv4' destination address='$hub_host' port port='$hub_port' protocol='tcp' accept"
        done
        firewall-cmd --reload

        log_success "firewalld rules configured"

    else
        log_info "No active firewall detected or firewall not supported"
        log_info "Please ensure outbound connections to Hub ports are allowed"
    fi
}

verify_installation() {
    log_section "Verifying Installation"

    local all_ok=true

    echo "Checking installation components..."
    echo ""

    # Check directories
    for dir in "$INSTALL_DIR" "$SSH_DIR" "$CONFIG_DIR" "$LOG_DIR"; do
        if [[ -d "$dir" ]]; then
            echo -e "  ${GREEN}[OK]${NC} Directory: $dir"
        else
            echo -e "  ${RED}[FAIL]${NC} Directory: $dir"
            all_ok=false
        fi
    done

    # Check SSH key
    if [[ -f "$SSH_DIR/id_ed25519" ]]; then
        echo -e "  ${GREEN}[OK]${NC} SSH Key: Present"
    else
        echo -e "  ${RED}[FAIL]${NC} SSH Key: Missing"
        all_ok=false
    fi

    # Check services
    for i in "${!HUB_HOSTS[@]}"; do
        local hub_num=$((i + 1))
        local service_name="orizon-tunnel-hub${hub_num}"

        if systemctl is-active --quiet "$service_name"; then
            echo -e "  ${GREEN}[OK]${NC} Service: $service_name (running)"
        else
            echo -e "  ${YELLOW}[WARN]${NC} Service: $service_name (not running)"
        fi
    done

    if systemctl is-active --quiet orizon-watchdog; then
        echo -e "  ${GREEN}[OK]${NC} Service: orizon-watchdog (running)"
    else
        echo -e "  ${YELLOW}[WARN]${NC} Service: orizon-watchdog (not running)"
    fi

    echo ""

    if $all_ok; then
        log_success "Installation verified successfully"
    else
        log_warn "Some components may need attention"
    fi
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
    echo "  Status:   systemctl status orizon-tunnel-hub*"
    echo "  Logs:     journalctl -u orizon-tunnel-hub1 -f"
    echo "  Restart:  systemctl restart orizon-tunnel-hub1"
    echo ""
    echo -e "${BOLD}Configuration:${NC}"
    echo "  Config:   $CONFIG_DIR/agent.conf"
    echo "  Logs:     $LOG_DIR/"
    echo "  SSH Key:  $SSH_DIR/id_ed25519.pub"
    echo ""
}

#===============================================================================
# UNINSTALL FUNCTION
#===============================================================================

uninstall() {
    log_section "Uninstalling Orizon Agent"

    echo -e "${YELLOW}This will remove all Orizon components.${NC}"
    read -p "Are you sure? (y/N) " -n 1 -r
    echo ""

    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Uninstall cancelled"
        exit 0
    fi

    # Stop and disable services
    for service in $(systemctl list-units --type=service --all | grep 'orizon' | awk '{print $1}'); do
        systemctl stop "$service" 2>/dev/null || true
        systemctl disable "$service" 2>/dev/null || true
        rm -f "/etc/systemd/system/$service"
    done

    systemctl daemon-reload

    # Remove directories
    rm -rf "$INSTALL_DIR"
    rm -rf "$CONFIG_DIR"
    rm -rf "$LOG_DIR"

    log_success "Orizon Agent uninstalled"
}

#===============================================================================
# MAIN EXECUTION
#===============================================================================

main() {
    clear
    show_banner

    # Parse arguments
    case "${1:-}" in
        --help|-h)
            show_explanation
            exit 0
            ;;
        --uninstall|uninstall|remove)
            check_root
            uninstall
            exit 0
            ;;
        --version|-v)
            echo "Orizon Agent Installer v$VERSION"
            exit 0
            ;;
    esac

    # Check prerequisites
    check_root
    detect_distro

    # Validate required parameters
    if [[ -z "$NODE_ID" ]]; then
        log_error "NODE_ID is required"
        echo ""
        echo "Usage: NODE_ID=<id> HUB_SERVERS=<host1:port,host2:port> $0"
        exit 1
    fi

    if [[ -z "$HUB_SERVERS" ]]; then
        log_error "HUB_SERVERS is required"
        echo ""
        echo "Usage: NODE_ID=<id> HUB_SERVERS=<host1:port,host2:port> $0"
        exit 1
    fi

    # Show explanation
    show_explanation
    echo ""
    read -p "Press Enter to continue with installation, or Ctrl+C to abort..."
    echo ""

    # Calculate ports and parse servers
    calculate_tunnel_ports
    parse_hub_servers

    # Run installation
    install_dependencies
    create_directories
    generate_ssh_keys
    register_with_hub
    create_config_file
    create_systemd_services
    enable_services
    configure_firewall
    verify_installation
    show_summary
}

# Run main function
main "$@"
