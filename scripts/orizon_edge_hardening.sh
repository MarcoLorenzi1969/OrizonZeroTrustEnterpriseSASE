#!/bin/bash
# =============================================================================
# ORIZON EDGE NODE HARDENING SCRIPT v1.0
# =============================================================================
# Enterprise Zero Trust Connect - Security Hardening
# For: Marco @ Syneto/Orizon
#
# Features:
#   - Tunnel SSH persistente verso Hub (autossh)
#   - Server Nginx HTTPS con pagina demo
#   - Firewall nftables (default DENY)
#   - Fail2ban con whitelist (Hub + rete locale)
#   - Comando CLI nel PATH + MOTD terminale
# =============================================================================

set -euo pipefail

# === VERSIONE E METADATA ===
readonly SCRIPT_VERSION="1.0.0"
readonly SCRIPT_NAME="orizon-edge-hardening"
readonly SCRIPT_DATE="2025-11-28"

# === CONFIGURAZIONE DEFAULT ===
HUB_SSH_HOST="${HUB_SSH_HOST:-139.59.149.48}"
HUB_SSH_PORT="${HUB_SSH_PORT:-2222}"
ORIZON_DIR="/opt/orizon-agent"
HARDENING_DIR="/opt/orizon-hardening"
SSH_KEY_PATH="${ORIZON_DIR}/.ssh/id_ed25519"
LOG_FILE="/var/log/orizon/hardening.log"

# Parametri configurabili
NODE_ID=""
LOCAL_NETWORK=""
LOCAL_GATEWAY=""
SKIP_NGINX=false
SKIP_FAIL2BAN=false
SKIP_FIREWALL=false
DRY_RUN=false
SHOW_STATUS=false
UNINSTALL=false

# === COLORI OUTPUT ===
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly CYAN='\033[0;36m'
readonly MAGENTA='\033[0;35m'
readonly BOLD='\033[1m'
readonly NC='\033[0m'

# === FUNZIONI DI LOGGING ===
log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
    [[ -f "$LOG_FILE" ]] && echo "[$(date '+%Y-%m-%d %H:%M:%S')] [INFO] $*" >> "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $*"
    [[ -f "$LOG_FILE" ]] && echo "[$(date '+%Y-%m-%d %H:%M:%S')] [OK] $*" >> "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[!]${NC} $*"
    [[ -f "$LOG_FILE" ]] && echo "[$(date '+%Y-%m-%d %H:%M:%S')] [WARN] $*" >> "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[✗]${NC} $*" >&2
    [[ -f "$LOG_FILE" ]] && echo "[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR] $*" >> "$LOG_FILE"
}

log_step() {
    local step_num="$1"
    local step_desc="$2"
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}  STEP ${step_num}: ${step_desc}${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════════${NC}"
    echo ""
}

print_banner() {
    echo -e "${CYAN}"
    echo "╔═══════════════════════════════════════════════════════════════════╗"
    echo "║                                                                   ║"
    echo "║      ORIZON ZERO TRUST CONNECT - EDGE NODE HARDENING v${SCRIPT_VERSION}       ║"
    echo "║                                                                   ║"
    echo "║           Enterprise SASE Security Configuration                  ║"
    echo "║                                                                   ║"
    echo "╚═══════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Opzioni:"
    echo "  --node-id UUID        Node ID (obbligatorio per nuovo setup)"
    echo "  --hub-host IP         Override Hub IP (default: ${HUB_SSH_HOST})"
    echo "  --hub-port PORT       Override Hub SSH port (default: ${HUB_SSH_PORT})"
    echo "  --local-network CIDR  Rete locale whitelist (es: 10.211.55.0/24)"
    echo "  --skip-nginx          Salta configurazione Nginx"
    echo "  --skip-fail2ban       Salta configurazione Fail2ban"
    echo "  --skip-firewall       Salta configurazione nftables"
    echo "  --dry-run             Simula senza applicare modifiche"
    echo "  --status              Mostra stato servizi hardening"
    echo "  --uninstall           Rimuove configurazione hardening"
    echo "  --help                Mostra questo messaggio"
    echo ""
    echo "Esempi:"
    echo "  $0 --node-id eba77c68-6ef0-469a-9166-685829a4fa48"
    echo "  $0 --status"
    echo "  $0 --node-id UUID --local-network 10.211.55.0/24"
}

# === FUNZIONI DI SISTEMA ===
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "Questo script deve essere eseguito come root (sudo)"
        exit 1
    fi
    log_success "Root privileges OK"
}

detect_os() {
    if [[ ! -f /etc/os-release ]]; then
        log_error "Sistema operativo non riconosciuto"
        exit 1
    fi

    source /etc/os-release

    case "$ID" in
        ubuntu|debian|kali|linuxmint|pop)
            OS_FAMILY="debian"
            PKG_INSTALL="DEBIAN_FRONTEND=noninteractive apt-get install -y"
            PKG_UPDATE="apt-get update -qq"
            ;;
        fedora|centos|rhel|rocky|alma)
            OS_FAMILY="redhat"
            PKG_INSTALL="dnf install -y"
            PKG_UPDATE="dnf check-update || true"
            ;;
        *)
            log_error "Distribuzione $ID non supportata"
            exit 1
            ;;
    esac

    log_success "Sistema: $PRETTY_NAME ($OS_FAMILY)"
}

detect_network() {
    log_info "Auto-rilevamento configurazione rete..."

    # Rileva gateway
    if [[ -z "$LOCAL_GATEWAY" ]]; then
        LOCAL_GATEWAY=$(ip route | grep default | awk '{print $3}' | head -1)
    fi

    # Rileva rete locale basandosi sul gateway
    if [[ -z "$LOCAL_NETWORK" ]]; then
        if [[ -n "$LOCAL_GATEWAY" ]]; then
            # Estrai i primi 3 ottetti e aggiungi .0/24
            LOCAL_NETWORK=$(echo "$LOCAL_GATEWAY" | sed 's/\.[0-9]*$/.0\/24/')
        else
            LOCAL_NETWORK="192.168.0.0/16"
        fi
    fi

    log_success "Gateway: ${LOCAL_GATEWAY:-N/A}"
    log_success "Rete locale: $LOCAL_NETWORK"
}

check_ssh_key() {
    log_info "Verifica chiavi SSH..."

    if [[ ! -f "$SSH_KEY_PATH" ]]; then
        log_warning "Chiave SSH non trovata in $SSH_KEY_PATH"

        # Prova path alternativi
        for alt_path in "/root/.ssh/id_ed25519" "/root/.ssh/id_rsa" "${ORIZON_DIR}/.ssh/id_rsa"; do
            if [[ -f "$alt_path" ]]; then
                SSH_KEY_PATH="$alt_path"
                log_success "Trovata chiave alternativa: $SSH_KEY_PATH"
                return 0
            fi
        done

        log_error "Nessuna chiave SSH trovata. Eseguire prima orizon_edge_setup.sh"
        exit 1
    fi

    log_success "Chiave SSH: $SSH_KEY_PATH"
}

detect_node_id() {
    log_info "Rilevamento Node ID..."

    # Se non specificato, prova a leggere da config esistente
    if [[ -z "$NODE_ID" ]]; then
        # Prova config Orizon
        if [[ -f "${ORIZON_DIR}/config.json" ]]; then
            NODE_ID=$(grep -oP '"node_id"\s*:\s*"\K[^"]+' "${ORIZON_DIR}/config.json" 2>/dev/null || true)
        fi

        # Prova file dedicato
        if [[ -z "$NODE_ID" && -f "/etc/orizon/node_id" ]]; then
            NODE_ID=$(cat /etc/orizon/node_id)
        fi

        # Genera da machine-id
        if [[ -z "$NODE_ID" && -f "/etc/machine-id" ]]; then
            NODE_ID=$(cat /etc/machine-id | md5sum | cut -c1-8)-$(hostname | md5sum | cut -c1-4)-$(date +%s | md5sum | cut -c1-4)-$(cat /etc/machine-id | md5sum | cut -c9-12)-$(cat /etc/machine-id | md5sum | cut -c13-24)
        fi
    fi

    if [[ -z "$NODE_ID" ]]; then
        log_error "Node ID non specificato. Usa --node-id UUID"
        exit 1
    fi

    log_success "Node ID: $NODE_ID"

    # Salva Node ID
    mkdir -p /etc/orizon
    echo "$NODE_ID" > /etc/orizon/node_id
}

# === INSTALLAZIONE PACCHETTI ===
install_packages() {
    log_info "Installazione pacchetti necessari..."

    $PKG_UPDATE &>/dev/null || true

    local packages="autossh openssl curl"

    [[ "$SKIP_NGINX" != "true" ]] && packages="$packages nginx"
    [[ "$SKIP_FAIL2BAN" != "true" ]] && packages="$packages fail2ban"
    [[ "$SKIP_FIREWALL" != "true" ]] && packages="$packages nftables"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY-RUN] Installerebbe: $packages"
    else
        $PKG_INSTALL $packages &>/dev/null
        log_success "Pacchetti installati: $packages"
    fi
}

# === BACKUP CONFIGURAZIONE ===
backup_config() {
    local backup_dir="/var/backups/orizon-hardening-$(date +%Y%m%d-%H%M%S)"

    log_info "Backup configurazione in $backup_dir..."

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY-RUN] Creerebbe backup in $backup_dir"
        return 0
    fi

    mkdir -p "$backup_dir"

    # Backup nginx
    [[ -d /etc/nginx ]] && cp -r /etc/nginx "$backup_dir/" 2>/dev/null || true

    # Backup fail2ban
    [[ -d /etc/fail2ban ]] && cp -r /etc/fail2ban "$backup_dir/" 2>/dev/null || true

    # Backup nftables
    [[ -f /etc/nftables.conf ]] && cp /etc/nftables.conf "$backup_dir/" 2>/dev/null || true

    # Backup servizio tunnel esistente
    [[ -f /etc/systemd/system/orizon-tunnel.service ]] && \
        cp /etc/systemd/system/orizon-tunnel.service "$backup_dir/" 2>/dev/null || true

    log_success "Backup creato: $backup_dir"
}

# === CONFIGURAZIONE FIREWALL NFTABLES ===
setup_firewall() {
    if [[ "$SKIP_FIREWALL" == "true" ]]; then
        log_warning "Configurazione firewall saltata (--skip-firewall)"
        return 0
    fi

    log_info "Configurazione firewall nftables..."

    mkdir -p "$HARDENING_DIR/config"

    local nftables_conf="$HARDENING_DIR/config/nftables.conf"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY-RUN] Creerebbe $nftables_conf"
        return 0
    fi

    cat > "$nftables_conf" << NFTEOF
#!/usr/sbin/nft -f
# =============================================================================
# ORIZON EDGE NODE - NFTABLES FIREWALL RULES
# Generato da: orizon_edge_hardening.sh v${SCRIPT_VERSION}
# Data: $(date '+%Y-%m-%d %H:%M:%S')
# =============================================================================

flush ruleset

define HUB_IP = ${HUB_SSH_HOST}
define HUB_SSH_PORT = ${HUB_SSH_PORT}
define LOCAL_NET = ${LOCAL_NETWORK}

table inet filter {
    # === INPUT: Traffico in ingresso ===
    chain input {
        type filter hook input priority 0; policy drop;

        # Connessioni stabilite/correlate
        ct state established,related accept

        # Loopback
        iif lo accept

        # ICMP limitato (ping)
        ip protocol icmp icmp type { echo-request, echo-reply } limit rate 10/second accept

        # SSH solo dalla rete locale
        ip saddr \$LOCAL_NET tcp dport 22 ct state new limit rate 3/minute accept

        # HTTP/HTTPS per Nginx
        tcp dport { 80, 443 } accept

        # Log e drop resto
        log prefix "[ORIZON-DROP-IN] " flags all counter drop
    }

    # === OUTPUT: Traffico in uscita ===
    chain output {
        type filter hook output priority 0; policy drop;

        # Connessioni stabilite/correlate
        ct state established,related accept

        # Loopback
        oif lo accept

        # CRITICO: Tunnel SSH verso Hub
        ip daddr \$HUB_IP tcp dport \$HUB_SSH_PORT accept

        # DNS
        udp dport 53 accept
        tcp dport 53 accept

        # NTP (sincronizzazione orario)
        udp dport 123 accept

        # HTTPS per aggiornamenti
        tcp dport { 80, 443 } accept

        # Rete locale
        ip daddr \$LOCAL_NET accept

        # Log e drop resto
        log prefix "[ORIZON-DROP-OUT] " flags all counter drop
    }

    # === FORWARD: Routing (disabilitato) ===
    chain forward {
        type filter hook forward priority 0; policy drop;
    }
}
NFTEOF

    # Applica regole
    nft -f "$nftables_conf"

    # Copia in /etc per persistenza
    cp "$nftables_conf" /etc/nftables.conf

    # Abilita servizio
    systemctl enable nftables &>/dev/null
    systemctl restart nftables

    log_success "Firewall nftables configurato (default DENY)"
}

# === CONFIGURAZIONE FAIL2BAN ===
setup_fail2ban() {
    if [[ "$SKIP_FAIL2BAN" == "true" ]]; then
        log_warning "Configurazione fail2ban saltata (--skip-fail2ban)"
        return 0
    fi

    log_info "Configurazione fail2ban..."

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY-RUN] Configurerebbe fail2ban"
        return 0
    fi

    mkdir -p "$HARDENING_DIR/config/fail2ban"

    cat > /etc/fail2ban/jail.local << F2BEOF
# =============================================================================
# ORIZON EDGE NODE - FAIL2BAN CONFIGURATION
# Generato da: orizon_edge_hardening.sh v${SCRIPT_VERSION}
# =============================================================================

[DEFAULT]
# Ban per 24 ore
bantime = 86400
# Finestra di osservazione: 10 minuti
findtime = 600
# Max 3 tentativi
maxretry = 3
# Backend
backend = systemd
# Azione: nftables
banaction = nftables-multiport
banaction_allports = nftables-allports

# Whitelist: Hub + Rete locale
ignoreip = 127.0.0.1/8 ::1 ${HUB_SSH_HOST} ${LOCAL_NETWORK}

# === JAIL SSH ===
[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 86400

# === JAIL NGINX ===
[nginx-http-auth]
enabled = true
port = http,https
filter = nginx-http-auth
logpath = /var/log/nginx/error.log
maxretry = 5
bantime = 3600

[nginx-limit-req]
enabled = true
port = http,https
filter = nginx-limit-req
logpath = /var/log/nginx/error.log
maxretry = 10
bantime = 3600
F2BEOF

    # Copia config in hardening dir
    cp /etc/fail2ban/jail.local "$HARDENING_DIR/config/fail2ban/"

    # Restart fail2ban
    systemctl enable fail2ban &>/dev/null
    systemctl restart fail2ban

    log_success "Fail2ban configurato (whitelist: Hub + ${LOCAL_NETWORK})"
}

# === GENERAZIONE CERTIFICATI SSL ===
generate_ssl_certs() {
    local ssl_dir="$HARDENING_DIR/nginx/ssl"

    log_info "Generazione certificati SSL self-signed..."

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY-RUN] Genererebbe certificati in $ssl_dir"
        return 0
    fi

    mkdir -p "$ssl_dir"

    # Genera certificato self-signed (validita 365 giorni)
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout "$ssl_dir/orizon-edge.key" \
        -out "$ssl_dir/orizon-edge.crt" \
        -subj "/CN=orizon-edge-${NODE_ID:0:8}/O=Orizon/C=IT" \
        &>/dev/null

    # Permessi restrittivi
    chmod 600 "$ssl_dir/orizon-edge.key"
    chmod 644 "$ssl_dir/orizon-edge.crt"

    log_success "Certificati SSL generati (validita 365 giorni)"
}

# === CONFIGURAZIONE NGINX ===
setup_nginx() {
    if [[ "$SKIP_NGINX" == "true" ]]; then
        log_warning "Configurazione Nginx saltata (--skip-nginx)"
        return 0
    fi

    log_info "Configurazione Nginx HTTPS..."

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY-RUN] Configurerebbe Nginx"
        return 0
    fi

    # Genera certificati se necessario
    generate_ssl_certs

    # Crea directory HTML
    mkdir -p "$HARDENING_DIR/nginx/html"

    # Configurazione Nginx
    cat > /etc/nginx/sites-available/orizon-edge << 'NGINXEOF'
# =============================================================================
# ORIZON EDGE NODE - NGINX HTTPS CONFIGURATION
# =============================================================================

# HTTP -> HTTPS redirect
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;
    return 301 https://$host$request_uri;
}

# HTTPS Server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name _;

    # SSL Configuration
    ssl_certificate /opt/orizon-hardening/nginx/ssl/orizon-edge.crt;
    ssl_certificate_key /opt/orizon-hardening/nginx/ssl/orizon-edge.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;

    # Security Headers
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Root directory
    root /opt/orizon-hardening/nginx/html;
    index index.html;

    # Location
    location / {
        try_files $uri $uri/ =404;
    }

    # Health check
    location /health {
        access_log off;
        return 200 "OK\n";
        add_header Content-Type text/plain;
    }

    # Logging
    access_log /var/log/nginx/orizon-access.log;
    error_log /var/log/nginx/orizon-error.log;
}
NGINXEOF

    # Pagina HTML demo
    cat > "$HARDENING_DIR/nginx/html/index.html" << HTMLEOF
<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Orizon Edge Node - Secure Access</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #e0e0e0;
        }
        .container {
            text-align: center;
            padding: 40px;
            background: rgba(255,255,255,0.05);
            border-radius: 20px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.1);
            max-width: 500px;
        }
        .logo { font-size: 64px; margin-bottom: 20px; }
        h1 { font-size: 1.8rem; margin-bottom: 10px; color: #00d9ff; }
        .subtitle { color: #888; margin-bottom: 30px; }
        .status {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            padding: 15px 30px;
            background: rgba(0, 217, 255, 0.1);
            border-radius: 10px;
            margin-bottom: 20px;
        }
        .status-dot {
            width: 12px; height: 12px;
            background: #00ff88;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.5; transform: scale(1.2); }
        }
        .info {
            text-align: left;
            background: rgba(0,0,0,0.3);
            padding: 15px;
            border-radius: 10px;
            font-family: monospace;
            font-size: 0.85rem;
        }
        .info-row {
            display: flex;
            justify-content: space-between;
            padding: 5px 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        .info-row:last-child { border: none; }
        .info-label { color: #888; }
        .info-value { color: #00d9ff; }
        .footer { margin-top: 20px; font-size: 0.75rem; color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">&#128274;</div>
        <h1>Orizon Edge Node</h1>
        <p class="subtitle">Zero Trust Secure Access Point</p>

        <div class="status">
            <span class="status-dot"></span>
            <span>Tunnel SSL Attivo</span>
        </div>

        <div class="info">
            <div class="info-row">
                <span class="info-label">Node ID:</span>
                <span class="info-value">${NODE_ID:0:8}...</span>
            </div>
            <div class="info-row">
                <span class="info-label">Hub:</span>
                <span class="info-value">${HUB_SSH_HOST}:${HUB_SSH_PORT}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Protocollo:</span>
                <span class="info-value">TLS 1.2/1.3</span>
            </div>
            <div class="info-row">
                <span class="info-label">Firewall:</span>
                <span class="info-value">nftables</span>
            </div>
        </div>

        <p class="footer">Orizon Zero Trust Connect &copy; 2025</p>
    </div>
</body>
</html>
HTMLEOF

    # Abilita site
    rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true
    ln -sf /etc/nginx/sites-available/orizon-edge /etc/nginx/sites-enabled/

    # Test e restart
    nginx -t &>/dev/null && systemctl restart nginx
    systemctl enable nginx &>/dev/null

    log_success "Nginx HTTPS configurato (porta 443)"
}

# === SETUP TUNNEL AUTOSSH ===
setup_autossh_tunnel() {
    log_info "Configurazione tunnel SSH persistente (autossh)..."

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY-RUN] Creerebbe servizio orizon-tunnel.service"
        return 0
    fi

    # Determina porte remote
    # Usa hash del NODE_ID per porte consistenti
    local hash=$(echo -n "$NODE_ID" | md5sum | cut -c1-4)
    local remote_ssh_port=$((10000 + 16#$hash % 50000))
    local remote_https_port=$((remote_ssh_port + 1000))

    # Crea servizio systemd
    cat > /etc/systemd/system/orizon-tunnel.service << SVCEOF
[Unit]
Description=Orizon Zero Trust Connect - SSH Tunnel
Documentation=https://orizon.syneto.net
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
Environment="AUTOSSH_GATETIME=0"
ExecStart=/usr/bin/autossh -M 0 -N \\
    -o "ServerAliveInterval=30" \\
    -o "ServerAliveCountMax=3" \\
    -o "ExitOnForwardFailure=yes" \\
    -o "StrictHostKeyChecking=no" \\
    -o "UserKnownHostsFile=/dev/null" \\
    -i ${SSH_KEY_PATH} \\
    -p ${HUB_SSH_PORT} \\
    -R ${remote_ssh_port}:localhost:22 \\
    -R ${remote_https_port}:localhost:443 \\
    ${NODE_ID}@${HUB_SSH_HOST}

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SVCEOF

    # Reload e avvia
    systemctl daemon-reload
    systemctl enable orizon-tunnel &>/dev/null
    systemctl restart orizon-tunnel

    # Salva info porte
    mkdir -p /etc/orizon
    cat > /etc/orizon/tunnel_config << CFGEOF
NODE_ID=${NODE_ID}
HUB_HOST=${HUB_SSH_HOST}
HUB_PORT=${HUB_SSH_PORT}
REMOTE_SSH_PORT=${remote_ssh_port}
REMOTE_HTTPS_PORT=${remote_https_port}
CFGEOF

    log_success "Tunnel autossh configurato"
    log_info "  SSH:   localhost:22 -> Hub:${remote_ssh_port}"
    log_info "  HTTPS: localhost:443 -> Hub:${remote_https_port}"
}

# === SETUP PATH E MOTD ===
setup_path_and_motd() {
    log_info "Configurazione comando CLI e MOTD..."

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY-RUN] Creerebbe symlink e MOTD"
        return 0
    fi

    # Crea symlink nel PATH
    ln -sf "$(readlink -f "$0")" /usr/local/bin/orizon-hardening 2>/dev/null || \
    cp "$0" /usr/local/bin/orizon-hardening
    chmod +x /usr/local/bin/orizon-hardening

    # Crea script MOTD
    cat > /etc/profile.d/orizon-motd.sh << 'MOTDEOF'
#!/bin/bash
# Orizon Edge Node - MOTD

# Solo per sessioni interattive
[[ $- != *i* ]] && return

# Colori
G='\033[0;32m'; R='\033[0;31m'; Y='\033[1;33m'; C='\033[0;36m'; N='\033[0m'; B='\033[1m'

echo ""
echo -e "${C}╔═══════════════════════════════════════╗${N}"
echo -e "${C}║   ORIZON ZERO TRUST - EDGE NODE       ║${N}"
echo -e "${C}╚═══════════════════════════════════════╝${N}"
echo ""

# Stato servizi
tunnel_status=$(systemctl is-active orizon-tunnel 2>/dev/null || echo "inactive")
nginx_status=$(systemctl is-active nginx 2>/dev/null || echo "inactive")
f2b_status=$(systemctl is-active fail2ban 2>/dev/null || echo "inactive")
fw_status=$(systemctl is-active nftables 2>/dev/null || echo "inactive")

[[ "$tunnel_status" == "active" ]] && echo -e " Tunnel:    ${G}ACTIVE${N}" || echo -e " Tunnel:    ${R}INACTIVE${N}"
[[ "$nginx_status" == "active" ]] && echo -e " Nginx:     ${G}ACTIVE${N}" || echo -e " Nginx:     ${Y}INACTIVE${N}"
[[ "$f2b_status" == "active" ]] && echo -e " Fail2ban:  ${G}ACTIVE${N}" || echo -e " Fail2ban:  ${Y}INACTIVE${N}"
[[ "$fw_status" == "active" ]] && echo -e " Firewall:  ${G}ACTIVE${N}" || echo -e " Firewall:  ${Y}INACTIVE${N}"

echo ""
echo -e " Comando: ${B}orizon-hardening --status${N}"
echo ""
MOTDEOF

    chmod +x /etc/profile.d/orizon-motd.sh

    log_success "Comando 'orizon-hardening' disponibile nel PATH"
    log_success "MOTD configurato per avvio terminale"
}

# === VERIFICA FINALE ===
verify_setup() {
    local errors=0

    echo ""
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║                      VERIFICA CONFIGURAZIONE                      ║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    # Check servizi
    for svc in orizon-tunnel nginx fail2ban nftables; do
        if systemctl is-active --quiet "$svc" 2>/dev/null; then
            echo -e "  ${GREEN}[✓]${NC} $svc: ACTIVE"
        else
            if [[ "$svc" == "nginx" && "$SKIP_NGINX" == "true" ]] || \
               [[ "$svc" == "fail2ban" && "$SKIP_FAIL2BAN" == "true" ]] || \
               [[ "$svc" == "nftables" && "$SKIP_FIREWALL" == "true" ]]; then
                echo -e "  ${YELLOW}[!]${NC} $svc: SKIPPED"
            else
                echo -e "  ${RED}[✗]${NC} $svc: INACTIVE"
                ((errors++))
            fi
        fi
    done

    # Check HTTPS
    if [[ "$SKIP_NGINX" != "true" ]]; then
        if curl -sk --max-time 3 https://localhost/health 2>/dev/null | grep -q "OK"; then
            echo -e "  ${GREEN}[✓]${NC} HTTPS: RESPONDING"
        else
            echo -e "  ${YELLOW}[!]${NC} HTTPS: NOT RESPONDING"
        fi
    fi

    # Check comando PATH
    if command -v orizon-hardening &>/dev/null; then
        echo -e "  ${GREEN}[✓]${NC} CLI: AVAILABLE"
    else
        echo -e "  ${RED}[✗]${NC} CLI: NOT FOUND"
        ((errors++))
    fi

    echo ""
    if [[ $errors -eq 0 ]]; then
        echo -e "${GREEN}  HARDENING COMPLETATO CON SUCCESSO!${NC}"
    else
        echo -e "${YELLOW}  Hardening completato con $errors warning${NC}"
    fi
    echo ""
    echo -e "  Comando: ${BOLD}orizon-hardening --status${NC}"
    echo ""
}

# === MOSTRA STATO ===
show_status() {
    echo ""
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║              ORIZON EDGE NODE - STATO HARDENING                   ║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    # Info nodo
    echo -e "${BOLD}Node Information:${NC}"
    [[ -f /etc/orizon/node_id ]] && echo "  ID:       $(cat /etc/orizon/node_id)" || echo "  ID:       N/A"
    echo "  Hostname: $(hostname)"
    echo "  IP:       $(hostname -I 2>/dev/null | awk '{print $1}')"
    echo ""

    # Servizi
    echo -e "${BOLD}Servizi:${NC}"
    for svc in orizon-tunnel nginx fail2ban nftables; do
        status=$(systemctl is-active "$svc" 2>/dev/null || echo "not-found")
        case "$status" in
            active)   echo -e "  $svc:\t${GREEN}ACTIVE${NC}" ;;
            inactive) echo -e "  $svc:\t${YELLOW}INACTIVE${NC}" ;;
            *)        echo -e "  $svc:\t${RED}NOT INSTALLED${NC}" ;;
        esac
    done
    echo ""

    # Tunnel config
    if [[ -f /etc/orizon/tunnel_config ]]; then
        echo -e "${BOLD}Tunnel Configuration:${NC}"
        source /etc/orizon/tunnel_config
        echo "  Hub:        ${HUB_HOST}:${HUB_PORT}"
        echo "  Remote SSH: ${REMOTE_SSH_PORT}"
        echo "  Remote SSL: ${REMOTE_HTTPS_PORT}"
        echo ""
    fi

    # Fail2ban status
    if systemctl is-active --quiet fail2ban 2>/dev/null; then
        echo -e "${BOLD}Fail2ban:${NC}"
        fail2ban-client status sshd 2>/dev/null | grep -E "Currently|Total" | sed 's/^/  /'
        echo ""
    fi

    # Comandi utili
    echo -e "${BOLD}Comandi Utili:${NC}"
    echo "  journalctl -u orizon-tunnel -f    # Log tunnel"
    echo "  systemctl restart orizon-tunnel   # Riavvia tunnel"
    echo "  curl -k https://localhost         # Test HTTPS"
    echo "  fail2ban-client status            # Stato fail2ban"
    echo ""
}

# === UNINSTALL ===
uninstall_hardening() {
    log_warning "Rimozione configurazione hardening..."

    # Stop servizi
    systemctl stop orizon-tunnel 2>/dev/null || true
    systemctl disable orizon-tunnel 2>/dev/null || true

    # Rimuovi servizio
    rm -f /etc/systemd/system/orizon-tunnel.service
    systemctl daemon-reload

    # Rimuovi config nginx
    rm -f /etc/nginx/sites-enabled/orizon-edge
    rm -f /etc/nginx/sites-available/orizon-edge
    systemctl restart nginx 2>/dev/null || true

    # Rimuovi fail2ban config
    rm -f /etc/fail2ban/jail.local
    systemctl restart fail2ban 2>/dev/null || true

    # Ripristina firewall default
    nft flush ruleset 2>/dev/null || true
    rm -f /etc/nftables.conf

    # Rimuovi directory hardening
    rm -rf "$HARDENING_DIR"

    # Rimuovi MOTD e comando
    rm -f /etc/profile.d/orizon-motd.sh
    rm -f /usr/local/bin/orizon-hardening

    log_success "Configurazione hardening rimossa"
}

# === PARSING ARGOMENTI ===
parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --node-id)
                NODE_ID="$2"
                shift 2
                ;;
            --hub-host)
                HUB_SSH_HOST="$2"
                shift 2
                ;;
            --hub-port)
                HUB_SSH_PORT="$2"
                shift 2
                ;;
            --local-network)
                LOCAL_NETWORK="$2"
                shift 2
                ;;
            --skip-nginx)
                SKIP_NGINX=true
                shift
                ;;
            --skip-fail2ban)
                SKIP_FAIL2BAN=true
                shift
                ;;
            --skip-firewall)
                SKIP_FIREWALL=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --status|-s)
                SHOW_STATUS=true
                shift
                ;;
            --uninstall)
                UNINSTALL=true
                shift
                ;;
            --help|-h)
                print_usage
                exit 0
                ;;
            *)
                log_error "Opzione sconosciuta: $1"
                print_usage
                exit 1
                ;;
        esac
    done
}

# === MAIN ===
main() {
    parse_args "$@"

    # Crea directory log
    mkdir -p /var/log/orizon
    touch "$LOG_FILE"

    # Modalita' status
    if [[ "$SHOW_STATUS" == "true" ]]; then
        show_status
        exit 0
    fi

    # Modalita' uninstall
    if [[ "$UNINSTALL" == "true" ]]; then
        check_root
        uninstall_hardening
        exit 0
    fi

    # Hardening completo
    print_banner

    [[ "$DRY_RUN" == "true" ]] && log_warning "MODALITA' DRY-RUN: Nessuna modifica sara' applicata"

    log_step "1" "Verifica Prerequisiti"
    check_root
    detect_os
    detect_network
    check_ssh_key
    detect_node_id

    log_step "2" "Backup Configurazione"
    backup_config

    log_step "3" "Installazione Pacchetti"
    install_packages

    log_step "4" "Configurazione Firewall (nftables)"
    setup_firewall

    log_step "5" "Configurazione Fail2ban"
    setup_fail2ban

    log_step "6" "Configurazione Nginx HTTPS"
    setup_nginx

    log_step "7" "Configurazione Tunnel SSH (autossh)"
    setup_autossh_tunnel

    log_step "8" "Configurazione PATH e MOTD"
    setup_path_and_motd

    log_step "9" "Verifica Finale"
    verify_setup

    log_info "Log completo: $LOG_FILE"
}

main "$@"
