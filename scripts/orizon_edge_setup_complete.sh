#!/bin/bash
#############################################################################
# Orizon Edge Setup Complete - Script Automatizzato di Setup Edge Node
#
# Questo script si connette automaticamente al server HUB, recupera le
# configurazioni necessarie, installa i servizi richiesti, crea i reverse
# tunnel e verifica che tutto funzioni correttamente.
#
# Autore: Orizon Zero Trust Connect Team
# Versione: 1.0
# Data: 2025-11-11
#############################################################################

# Note: Removed set -e to allow script to continue and handle errors explicitly

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURAZIONE E VARIABILI GLOBALI
# ═══════════════════════════════════════════════════════════════════════════

SCRIPT_VERSION="1.0"
SCRIPT_NAME="orizon_edge_setup_complete.sh"
LOG_FILE="/var/log/orizon_edge_setup_$(date +%Y%m%d_%H%M%S).log"
TEMP_DIR="/tmp/orizon_setup_$$"
AGENT_DIR="/opt/orizon"
CONFIG_FILE="$AGENT_DIR/config.json"
SSH_KEY_FILE="$AGENT_DIR/id_ed25519"

# Parametri da input
HUB_IP=""
HUB_USER=""
HUB_PASSWORD=""
EDGE_NAME=""
EDGE_IP=""
EDGE_LOCATION=""
SERVICES=""
NODE_UUID=""
JWT_TOKEN=""
JWT_SECRET=""

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Contatori per report finale
SUCCESS_COUNT=0
FAILED_COUNT=0
WARNING_COUNT=0

# ═══════════════════════════════════════════════════════════════════════════
# FUNZIONI DI LOGGING E OUTPUT
# ═══════════════════════════════════════════════════════════════════════════

log_and_echo() {
    local message="$1"
    echo -e "$message" | tee -a "$LOG_FILE"
}

log_info() {
    local message="[INFO] $1"
    log_and_echo "${BLUE}${message}${NC}"
}

log_success() {
    local message="[✓] $1"
    log_and_echo "${GREEN}${message}${NC}"
    ((SUCCESS_COUNT++))
}

log_error() {
    local message="[✗] $1"
    log_and_echo "${RED}${message}${NC}"
    ((FAILED_COUNT++))
}

log_warning() {
    local message="[⚠] $1"
    log_and_echo "${YELLOW}${message}${NC}"
    ((WARNING_COUNT++))
}

log_step() {
    local step_num="$1"
    local step_desc="$2"
    log_and_echo "\n${CYAN}${BOLD}═══════════════════════════════════════════════════════════════════${NC}"
    log_and_echo "${CYAN}${BOLD}  STEP $step_num: $step_desc${NC}"
    log_and_echo "${CYAN}${BOLD}═══════════════════════════════════════════════════════════════════${NC}"
}

print_banner() {
    log_and_echo ""
    log_and_echo "${MAGENTA}${BOLD}╔═══════════════════════════════════════════════════════════════════╗${NC}"
    log_and_echo "${MAGENTA}${BOLD}║                                                                   ║${NC}"
    log_and_echo "${MAGENTA}${BOLD}║         ORIZON ZERO TRUST CONNECT - EDGE SETUP COMPLETE          ║${NC}"
    log_and_echo "${MAGENTA}${BOLD}║                                                                   ║${NC}"
    log_and_echo "${MAGENTA}${BOLD}║              Automated Edge Node Configuration v$SCRIPT_VERSION             ║${NC}"
    log_and_echo "${MAGENTA}${BOLD}║                                                                   ║${NC}"
    log_and_echo "${MAGENTA}${BOLD}╚═══════════════════════════════════════════════════════════════════╝${NC}"
    log_and_echo ""
}

# ═══════════════════════════════════════════════════════════════════════════
# FUNZIONI DI UTILITÀ
# ═══════════════════════════════════════════════════════════════════════════

cleanup() {
    log_info "Pulizia file temporanei..."
    rm -rf "$TEMP_DIR" 2>/dev/null || true
}

trap cleanup EXIT

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "Questo script deve essere eseguito come root o con sudo"
        exit 1
    fi
}

detect_os() {
    log_info "Rilevamento sistema operativo..."

    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        OS_NAME=$ID
        OS_VERSION=${VERSION_ID:-"unknown"}
        OS_PRETTY=$PRETTY_NAME

        case "$OS_NAME" in
            ubuntu|debian|kali|mint|pop|parrot)
                OS_FAMILY="debian"
                PKG_MANAGER="apt"
                PKG_UPDATE="apt-get update -qq"
                PKG_INSTALL="DEBIAN_FRONTEND=noninteractive apt-get install -y -qq"
                SSH_SERVICE="ssh"
                ;;
            fedora|rhel|centos|rocky|alma)
                OS_FAMILY="redhat"
                PKG_MANAGER="dnf"
                PKG_UPDATE="dnf check-update -q"
                PKG_INSTALL="dnf install -y -q"
                SSH_SERVICE="sshd"
                ;;
            arch|manjaro)
                OS_FAMILY="arch"
                PKG_MANAGER="pacman"
                PKG_UPDATE="pacman -Sy"
                PKG_INSTALL="pacman -S --noconfirm"
                SSH_SERVICE="sshd"
                ;;
            *)
                log_error "Sistema operativo non supportato: $OS_NAME"
                exit 1
                ;;
        esac

        log_success "Sistema rilevato: $OS_PRETTY"
        log_info "  - Famiglia: $OS_FAMILY"
        log_info "  - Package Manager: $PKG_MANAGER"
        log_info "  - SSH Service: $SSH_SERVICE"
    else
        log_error "Impossibile rilevare il sistema operativo"
        exit 1
    fi
}

# ═══════════════════════════════════════════════════════════════════════════
# FUNZIONI DI CONNESSIONE AL HUB
# ═══════════════════════════════════════════════════════════════════════════

test_hub_connection() {
    log_info "Test connessione al server HUB $HUB_IP..."

    # Test ping
    if ping -c 2 -W 3 "$HUB_IP" &>/dev/null; then
        log_success "Server HUB raggiungibile (ping)"
    else
        log_warning "Server HUB non risponde al ping (potrebbe essere normale se ICMP è bloccato)"
    fi

    # Test SSH
    if timeout 5 sshpass -p "$HUB_PASSWORD" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 "$HUB_USER@$HUB_IP" "echo 'test'" &>/dev/null; then
        log_success "Connessione SSH al HUB funzionante"
        return 0
    else
        log_error "Impossibile connettersi al HUB via SSH"
        log_error "  - Verificare credenziali (user: $HUB_USER)"
        log_error "  - Verificare che SSH sia attivo sul HUB"
        log_error "  - Verificare firewall"
        return 1
    fi
}

get_jwt_secret_from_hub() {
    log_info "Recupero JWT secret dal HUB..."

    JWT_SECRET=$(sshpass -p "$HUB_PASSWORD" ssh -o StrictHostKeyChecking=no "$HUB_USER@$HUB_IP" \
        "grep -oP 'JWT_SECRET_KEY=\K.*' /root/orizon-ztc/backend/.env 2>/dev/null || \
         echo 'orizon-secret-key-change-in-production'")

    if [[ -n "$JWT_SECRET" && "$JWT_SECRET" != "orizon-secret-key-change-in-production" ]]; then
        log_success "JWT secret recuperato dal HUB"
    else
        log_warning "JWT secret non trovato, uso default (NON sicuro in produzione!)"
        JWT_SECRET="orizon-secret-key-change-in-production"
    fi
}

create_node_on_hub() {
    log_info "Edge '$EDGE_NAME' non trovato - Creazione automatica sul HUB..."

    # [1/5] Genera UUID
    log_info "Generazione UUID..."
    NODE_UUID=$(uuidgen | tr '[:upper:]' '[:lower:]')
    log_success "UUID generato: $NODE_UUID"

    # [2/5] Genera chiavi SSH
    log_info "Generazione chiavi SSH ed25519..."
    sshpass -p "$HUB_PASSWORD" ssh -o StrictHostKeyChecking=no "$HUB_USER@$HUB_IP" \
        "mkdir -p /root/.ssh && \
         ssh-keygen -t ed25519 -f /root/.ssh/orizon_edge_${EDGE_NAME}_key \
         -C 'orizon-hub-to-$EDGE_NAME' -N '' >/dev/null 2>&1" || {
        log_error "Errore generazione chiavi SSH"
        return 1
    }
    log_success "Chiavi SSH generate"

    # [3/5] Genera JWT token
    log_info "Generazione JWT token..."
    JWT_TOKEN=$(sshpass -p "$HUB_PASSWORD" ssh -o StrictHostKeyChecking=no "$HUB_USER@$HUB_IP" \
        "python3 -c \"
import jwt
import datetime
payload = {
    'sub': '$NODE_UUID',
    'node_name': '$EDGE_NAME',
    'node_type': 'edge',
    'exp': datetime.datetime.utcnow() + datetime.timedelta(days=365)
}
token = jwt.encode(payload, '$JWT_SECRET', algorithm='HS256')
print(token if isinstance(token, str) else token.decode())
        \"" 2>/dev/null)

    if [[ -z "$JWT_TOKEN" || "$JWT_TOKEN" == *"error"* ]]; then
        log_error "Errore generazione JWT token"
        return 1
    fi
    log_success "JWT token generato"

    # [4/5] Inserisce nel database
    log_info "Registrazione nel database PostgreSQL..."
    sshpass -p "$HUB_PASSWORD" ssh -o StrictHostKeyChecking=no "$HUB_USER@$HUB_IP" \
        "sudo -u postgres psql -d orizon_ztc -c \"
INSERT INTO nodes (id, name, ip_address, status, node_type, created_at, updated_at)
VALUES ('$NODE_UUID', '$EDGE_NAME', '$EDGE_IP', 'offline', 'edge', NOW(), NOW())
ON CONFLICT (id) DO UPDATE SET ip_address = '$EDGE_IP', updated_at = NOW();
        \"" &>/dev/null || {
        log_error "Errore registrazione nel database"
        return 1
    }
    log_success "Edge registrato nel database"

    # [5/5] Salva token su file
    log_info "Salvataggio JWT token su HUB..."
    sshpass -p "$HUB_PASSWORD" ssh -o StrictHostKeyChecking=no "$HUB_USER@$HUB_IP" \
        "echo '$JWT_TOKEN' > /root/.ssh/orizon_edge_${EDGE_NAME}_token.jwt" || {
        log_error "Errore salvataggio token"
        return 1
    }
    log_success "Token salvato"

    log_success "Edge '$EDGE_NAME' creato automaticamente sul HUB!"
}

fetch_ssh_key_from_hub() {
    log_info "Recupero chiave SSH dal server HUB..."

    mkdir -p "$TEMP_DIR"

    # Recupera la chiave pubblica dal HUB per questo edge
    local ssh_key=$(sshpass -p "$HUB_PASSWORD" ssh -o StrictHostKeyChecking=no "$HUB_USER@$HUB_IP" \
        "cat /root/.ssh/orizon_edge_${EDGE_NAME}_key.pub 2>/dev/null || echo 'NOT_FOUND'")

    if [[ "$ssh_key" == "NOT_FOUND" ]]; then
        log_warning "Chiave SSH non trovata sul HUB per edge '$EDGE_NAME'"
        log_info "  - Probabilmente l'edge non è ancora registrato sul HUB"
        log_info "  - Verrà creata una nuova coppia di chiavi localmente"
        return 1
    fi

    # Salva la chiave pubblica
    echo "$ssh_key" > "$TEMP_DIR/hub_key.pub"
    log_success "Chiave SSH pubblica recuperata dal HUB"

    # Recupera anche la chiave privata se disponibile (con permessi appropriati)
    log_info "Tentativo di recupero chiave privata..."
    if sshpass -p "$HUB_PASSWORD" ssh -o StrictHostKeyChecking=no "$HUB_USER@$HUB_IP" \
        "test -f /root/.ssh/orizon_edge_${EDGE_NAME}_key" &>/dev/null; then

        sshpass -p "$HUB_PASSWORD" scp -o StrictHostKeyChecking=no \
            "$HUB_USER@$HUB_IP:/root/.ssh/orizon_edge_${EDGE_NAME}_key" \
            "$TEMP_DIR/hub_key" &>/dev/null

        chmod 600 "$TEMP_DIR/hub_key"
        log_success "Chiave SSH privata recuperata dal HUB"
        return 0
    else
        log_warning "Chiave privata non disponibile sul HUB"
        return 1
    fi
}

fetch_node_info_from_hub() {
    log_info "Recupero informazioni node dal database HUB..."

    # Query per ottenere NODE_UUID dal HUB
    local node_info=$(sshpass -p "$HUB_PASSWORD" ssh -o StrictHostKeyChecking=no "$HUB_USER@$HUB_IP" \
        "sudo -u postgres psql -d orizon_ztc -t -c \"SELECT id FROM nodes WHERE name = '$EDGE_NAME' LIMIT 1;\" 2>/dev/null || echo 'NOT_FOUND'")

    NODE_UUID=$(echo "$node_info" | tr -d ' \n\r')

    if [[ "$NODE_UUID" == "NOT_FOUND" || -z "$NODE_UUID" ]]; then
        log_warning "Edge '$EDGE_NAME' non trovato nel database del HUB"

        # ✅ NUOVA LOGICA: Crea automaticamente se non esiste
        if [[ -z "$EDGE_IP" ]]; then
            log_error "Parametro --edge-ip richiesto per auto-registrazione"
            log_error "  - Fornire: --edge-ip <IP_ADDRESS>"
            return 1
        fi

        # Recupera JWT secret prima di creare il nodo
        get_jwt_secret_from_hub || return 1

        # Crea il nodo automaticamente
        create_node_on_hub || return 1

        # Dopo la creazione, NODE_UUID e JWT_TOKEN sono già impostati
        log_success "Node UUID: $NODE_UUID"
        log_success "JWT token generato (${#JWT_TOKEN} caratteri)"
        return 0
    fi

    log_success "Node UUID recuperato: $NODE_UUID"

    # Recupera il JWT token esistente
    log_info "Recupero JWT token..."
    JWT_TOKEN=$(sshpass -p "$HUB_PASSWORD" ssh -o StrictHostKeyChecking=no "$HUB_USER@$HUB_IP" \
        "cat /root/.ssh/orizon_edge_${EDGE_NAME}_token.jwt 2>/dev/null || echo 'NOT_FOUND'")

    if [[ "$JWT_TOKEN" == "NOT_FOUND" || -z "$JWT_TOKEN" ]]; then
        log_error "JWT token non trovato per edge '$EDGE_NAME'"
        return 1
    fi

    log_success "JWT token recuperato (${#JWT_TOKEN} caratteri)"
    return 0
}

# ═══════════════════════════════════════════════════════════════════════════
# FUNZIONI DI INSTALLAZIONE SERVIZI
# ═══════════════════════════════════════════════════════════════════════════

update_system() {
    log_info "Aggiornamento lista pacchetti..."
    if eval "$PKG_UPDATE" &>/dev/null; then
        log_success "Lista pacchetti aggiornata"
    else
        log_warning "Errore aggiornamento lista pacchetti (continuo comunque)"
    fi
}

install_dependencies() {
    log_info "Installazione dipendenze base..."

    local packages="python3 python3-pip curl openssh-client sshpass"

    if eval "$PKG_INSTALL $packages" &>/dev/null; then
        log_success "Dipendenze base installate"
    else
        log_error "Errore installazione dipendenze"
        return 1
    fi

    # Installa librerie Python
    log_info "Installazione librerie Python..."
    if pip3 install --quiet websockets paramiko pyjwt &>/dev/null; then
        log_success "Librerie Python installate (websockets, paramiko, pyjwt)"
    else
        log_error "Errore installazione librerie Python"
        return 1
    fi
}

check_service_installed() {
    local service=$1
    local service_name=$2

    case "$service" in
        ssh)
            if systemctl is-active --quiet "$SSH_SERVICE" 2>/dev/null; then
                log_success "$service_name già installato e attivo"
                return 0
            fi
            ;;
        rdp)
            if systemctl is-active --quiet xrdp 2>/dev/null; then
                log_success "$service_name già installato e attivo"
                return 0
            fi
            ;;
        vnc)
            if command -v vncserver &>/dev/null; then
                log_success "$service_name già installato"
                return 0
            fi
            ;;
    esac
    return 1
}

install_ssh_service() {
    log_info "Verifica servizio SSH..."

    if check_service_installed "ssh" "SSH Server"; then
        return 0
    fi

    log_info "Installazione SSH server..."

    case "$PKG_MANAGER" in
        apt)
            if eval "$PKG_INSTALL openssh-server" &>/dev/null; then
                systemctl enable "$SSH_SERVICE" &>/dev/null
                systemctl start "$SSH_SERVICE" &>/dev/null
                log_success "SSH server installato e avviato"
            else
                log_error "Errore installazione SSH server"
                return 1
            fi
            ;;
        dnf)
            if eval "$PKG_INSTALL openssh-server" &>/dev/null; then
                systemctl enable "$SSH_SERVICE" &>/dev/null
                systemctl start "$SSH_SERVICE" &>/dev/null
                log_success "SSH server installato e avviato"
            else
                log_error "Errore installazione SSH server"
                return 1
            fi
            ;;
        pacman)
            if eval "$PKG_INSTALL openssh" &>/dev/null; then
                systemctl enable "$SSH_SERVICE" &>/dev/null
                systemctl start "$SSH_SERVICE" &>/dev/null
                log_success "SSH server installato e avviato"
            else
                log_error "Errore installazione SSH server"
                return 1
            fi
            ;;
    esac

    # Verifica che sia attivo
    sleep 2
    if systemctl is-active --quiet "$SSH_SERVICE"; then
        log_success "SSH server verificato attivo su porta 22"
        netstat -tlnp | grep ":22 " | head -1 | tee -a "$LOG_FILE"
    else
        log_error "SSH server installato ma non attivo"
        systemctl status "$SSH_SERVICE" --no-pager | tee -a "$LOG_FILE"
        return 1
    fi
}

install_rdp_service() {
    log_info "Verifica servizio RDP (xrdp)..."

    if check_service_installed "rdp" "RDP Server (xrdp)"; then
        return 0
    fi

    log_info "Installazione RDP server (xrdp)..."

    case "$PKG_MANAGER" in
        apt)
            if eval "$PKG_INSTALL xrdp" &>/dev/null; then
                systemctl enable xrdp &>/dev/null
                systemctl start xrdp &>/dev/null
                log_success "xrdp installato e avviato"
            else
                log_error "Errore installazione xrdp"
                return 1
            fi
            ;;
        dnf)
            if eval "$PKG_INSTALL xrdp" &>/dev/null; then
                systemctl enable xrdp &>/dev/null
                systemctl start xrdp &>/dev/null
                log_success "xrdp installato e avviato"
            else
                log_error "Errore installazione xrdp"
                return 1
            fi
            ;;
        pacman)
            log_warning "xrdp deve essere installato manualmente su Arch Linux"
            log_info "  - Eseguire: yay -S xrdp"
            return 1
            ;;
    esac

    # Verifica che sia attivo
    sleep 2
    if systemctl is-active --quiet xrdp; then
        log_success "xrdp verificato attivo su porta 3389"
        netstat -tlnp | grep ":3389 " | head -1 | tee -a "$LOG_FILE"
    else
        log_error "xrdp installato ma non attivo"
        systemctl status xrdp --no-pager | tee -a "$LOG_FILE"
        return 1
    fi
}

install_vnc_service() {
    log_info "Verifica servizio VNC..."

    if check_service_installed "vnc" "VNC Server"; then
        return 0
    fi

    log_info "Installazione VNC server (TigerVNC)..."

    case "$PKG_MANAGER" in
        apt)
            if eval "$PKG_INSTALL tigervnc-standalone-server" &>/dev/null; then
                log_success "TigerVNC installato"
            else
                log_error "Errore installazione TigerVNC"
                return 1
            fi
            ;;
        dnf)
            if eval "$PKG_INSTALL tigervnc-server" &>/dev/null; then
                log_success "TigerVNC installato"
            else
                log_error "Errore installazione TigerVNC"
                return 1
            fi
            ;;
        pacman)
            if eval "$PKG_INSTALL tigervnc" &>/dev/null; then
                log_success "TigerVNC installato"
            else
                log_error "Errore installazione TigerVNC"
                return 1
            fi
            ;;
    esac

    log_info "VNC richiede configurazione manuale"
    log_info "  - Eseguire: vncserver per configurare la password"
    log_info "  - VNC sarà disponibile dopo la configurazione"
}

install_services() {
    IFS=',' read -ra SERVICE_ARRAY <<< "$SERVICES"

    for service in "${SERVICE_ARRAY[@]}"; do
        service=$(echo "$service" | tr '[:upper:]' '[:lower:]' | xargs)

        case "$service" in
            ssh)
                install_ssh_service || return 1
                ;;
            rdp)
                install_rdp_service || return 1
                ;;
            vnc)
                install_vnc_service || return 1
                ;;
            *)
                log_warning "Servizio sconosciuto: $service (ignorato)"
                ;;
        esac
    done
}

# ═══════════════════════════════════════════════════════════════════════════
# FUNZIONI DI CONFIGURAZIONE AGENT
# ═══════════════════════════════════════════════════════════════════════════

download_agent() {
    log_info "Download Orizon agent dal HUB..."

    mkdir -p "$AGENT_DIR"

    # Download via HTTP/HTTPS
    if curl -k -s "https://$HUB_IP:8000/api/v1/downloads/orizon_agent.py" -o "$AGENT_DIR/orizon_agent.py" 2>/dev/null; then
        log_success "Agent scaricato via HTTPS"
    elif curl -s "http://$HUB_IP:8000/api/v1/downloads/orizon_agent.py" -o "$AGENT_DIR/orizon_agent.py" 2>/dev/null; then
        log_success "Agent scaricato via HTTP"
    else
        # Fallback: copia via SCP
        log_info "Tentativo download via SCP..."
        if sshpass -p "$HUB_PASSWORD" scp -o StrictHostKeyChecking=no \
            "$HUB_USER@$HUB_IP:/root/orizon-ztc/agents/orizon_agent.py" \
            "$AGENT_DIR/orizon_agent.py" &>/dev/null; then
            log_success "Agent copiato via SCP"
        else
            log_error "Impossibile scaricare l'agent dal HUB"
            return 1
        fi
    fi

    chmod +x "$AGENT_DIR/orizon_agent.py"

    # Verifica che l'agent sia valido
    if grep -q "class OrizonAgent" "$AGENT_DIR/orizon_agent.py"; then
        log_success "Agent verificato ($(wc -l < "$AGENT_DIR/orizon_agent.py") righe)"
    else
        log_error "Agent scaricato ma sembra corrotto"
        return 1
    fi
}

create_config_file() {
    log_info "Creazione file di configurazione..."

    # Determina quali servizi sono attivi
    local ssh_enabled="false"
    local rdp_enabled="false"
    local vnc_enabled="false"

    IFS=',' read -ra SERVICE_ARRAY <<< "$SERVICES"
    for service in "${SERVICE_ARRAY[@]}"; do
        service=$(echo "$service" | tr '[:upper:]' '[:lower:]' | xargs)
        case "$service" in
            ssh) ssh_enabled="true" ;;
            rdp) rdp_enabled="true" ;;
            vnc) vnc_enabled="true" ;;
        esac
    done

    cat > "$CONFIG_FILE" << EOF
{
    "node_id": "$NODE_UUID",
    "node_name": "$EDGE_NAME",
    "node_location": "$EDGE_LOCATION",
    "hub_url": "wss://$HUB_IP",
    "jwt_token": "$JWT_TOKEN",
    "services": {
        "ssh": $ssh_enabled,
        "rdp": $rdp_enabled,
        "vnc": $vnc_enabled
    },
    "reconnect_interval": 5,
    "heartbeat_interval": 30,
    "log_level": "INFO"
}
EOF

    chmod 600 "$CONFIG_FILE"
    log_success "File di configurazione creato: $CONFIG_FILE"
    log_info "  - Node ID: $NODE_UUID"
    log_info "  - Node Name: $EDGE_NAME"
    log_info "  - Location: $EDGE_LOCATION"
    log_info "  - Hub URL: wss://$HUB_IP"
    log_info "  - Services: SSH=$ssh_enabled, RDP=$rdp_enabled, VNC=$vnc_enabled"
}

create_systemd_service() {
    log_info "Creazione servizio systemd..."

    cat > /etc/systemd/system/orizon-agent.service << EOF
[Unit]
Description=Orizon Zero Trust Connect Agent
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=$AGENT_DIR
ExecStart=/usr/bin/python3 $AGENT_DIR/orizon_agent.py -c $CONFIG_FILE
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload

    if systemctl enable orizon-agent &>/dev/null; then
        log_success "Servizio systemd creato e abilitato"
    else
        log_error "Errore creazione servizio systemd"
        return 1
    fi
}

start_agent() {
    log_info "Avvio Orizon agent..."

    if systemctl start orizon-agent; then
        log_success "Agent avviato"
        sleep 3

        if systemctl is-active --quiet orizon-agent; then
            log_success "Agent verificato attivo"
            systemctl status orizon-agent --no-pager --lines=5 | tee -a "$LOG_FILE"
        else
            log_error "Agent avviato ma non è attivo"
            journalctl -u orizon-agent -n 20 --no-pager | tee -a "$LOG_FILE"
            return 1
        fi
    else
        log_error "Errore avvio agent"
        journalctl -u orizon-agent -n 20 --no-pager | tee -a "$LOG_FILE"
        return 1
    fi
}

# ═══════════════════════════════════════════════════════════════════════════
# FUNZIONI DI TEST E VERIFICA TUNNEL
# ═══════════════════════════════════════════════════════════════════════════

test_local_services() {
    log_info "Test servizi locali..."

    local all_ok=true

    IFS=',' read -ra SERVICE_ARRAY <<< "$SERVICES"
    for service in "${SERVICE_ARRAY[@]}"; do
        service=$(echo "$service" | tr '[:upper:]' '[:lower:]' | xargs)

        case "$service" in
            ssh)
                log_info "Test SSH locale (porta 22)..."
                if timeout 5 bash -c "</dev/tcp/127.0.0.1/22" 2>/dev/null; then
                    log_success "SSH risponde su porta 22"
                else
                    log_error "SSH NON risponde su porta 22"
                    all_ok=false
                fi
                ;;
            rdp)
                log_info "Test RDP locale (porta 3389)..."
                if timeout 5 bash -c "</dev/tcp/127.0.0.1/3389" 2>/dev/null; then
                    log_success "RDP risponde su porta 3389"
                else
                    log_error "RDP NON risponde su porta 3389"
                    all_ok=false
                fi
                ;;
            vnc)
                log_info "Test VNC locale (porta 5901)..."
                if timeout 5 bash -c "</dev/tcp/127.0.0.1/5901" 2>/dev/null; then
                    log_success "VNC risponde su porta 5901"
                else
                    log_warning "VNC NON risponde su porta 5901 (potrebbe non essere configurato)"
                fi
                ;;
        esac
    done

    $all_ok && return 0 || return 1
}

test_agent_connection() {
    log_info "Test connessione agent al HUB..."

    # Aspetta che l'agent si connetta
    sleep 5

    # Verifica nei log se l'agent si è connesso
    if journalctl -u orizon-agent --since "1 minute ago" --no-pager | grep -q "Connected to hub"; then
        log_success "Agent connesso al HUB"
        return 0
    else
        log_warning "Agent non ancora connesso (potrebbe richiedere più tempo)"
        log_info "Ultimi log dell'agent:"
        journalctl -u orizon-agent --since "1 minute ago" --no-pager -n 10 | tee -a "$LOG_FILE"
        return 1
    fi
}

test_tunnel_from_hub() {
    log_info "Test tunnel dal HUB verso l'edge..."

    # Chiedi al HUB di testare la connettività verso questo edge
    local test_result=$(sshpass -p "$HUB_PASSWORD" ssh -o StrictHostKeyChecking=no "$HUB_USER@$HUB_IP" \
        "curl -s http://127.0.0.1:8000/api/v1/nodes/$NODE_UUID/status 2>/dev/null || echo 'FAILED'")

    if [[ "$test_result" != "FAILED" && -n "$test_result" ]]; then
        log_success "HUB può comunicare con l'edge"
        echo "$test_result" | jq '.' 2>/dev/null | tee -a "$LOG_FILE" || echo "$test_result" | tee -a "$LOG_FILE"
    else
        log_warning "Test comunicazione HUB->Edge fallito (normale se l'agent non è ancora completamente connesso)"
    fi
}

verify_tunnel_traffic() {
    local service=$1
    local port=$2

    log_info "Verifica traffico attraverso tunnel $service (porta $port)..."

    # Test 1: Verifica che il servizio locale risponda
    if ! timeout 3 bash -c "</dev/tcp/127.0.0.1/$port" 2>/dev/null; then
        log_error "Servizio $service non risponde localmente su porta $port"
        return 1
    fi

    log_success "Servizio $service risponde localmente su porta $port"

    # Test 2: Verifica nei log dell'agent se ci sono connessioni per questo servizio
    sleep 2
    if journalctl -u orizon-agent --since "2 minutes ago" --no-pager | grep -qi "$service"; then
        log_success "Traffico $service rilevato nei log dell'agent"
        return 0
    else
        log_warning "Nessun traffico $service ancora rilevato nei log (potrebbe essere normale)"
        return 0
    fi
}

# ═══════════════════════════════════════════════════════════════════════════
# FUNZIONE DI REPORT FINALE
# ═══════════════════════════════════════════════════════════════════════════

print_final_report() {
    log_and_echo ""
    log_and_echo "${MAGENTA}${BOLD}╔═══════════════════════════════════════════════════════════════════╗${NC}"
    log_and_echo "${MAGENTA}${BOLD}║                      REPORT FINALE SETUP                          ║${NC}"
    log_and_echo "${MAGENTA}${BOLD}╚═══════════════════════════════════════════════════════════════════╝${NC}"
    log_and_echo ""

    log_and_echo "${BOLD}Edge Node Information:${NC}"
    log_and_echo "  Nome:           $EDGE_NAME"
    log_and_echo "  Location:       $EDGE_LOCATION"
    log_and_echo "  Node UUID:      $NODE_UUID"
    log_and_echo "  Sistema:        $OS_PRETTY"
    log_and_echo ""

    log_and_echo "${BOLD}Hub Connection:${NC}"
    log_and_echo "  HUB IP:         $HUB_IP"
    log_and_echo "  WebSocket:      wss://$HUB_IP/api/v1/agents/$NODE_UUID/connect"
    log_and_echo ""

    log_and_echo "${BOLD}Servizi Configurati:${NC}"
    IFS=',' read -ra SERVICE_ARRAY <<< "$SERVICES"
    for service in "${SERVICE_ARRAY[@]}"; do
        service=$(echo "$service" | tr '[:upper:]' '[:lower:]' | xargs)
        case "$service" in
            ssh)
                local ssh_status="❌ NON ATTIVO"
                systemctl is-active --quiet "$SSH_SERVICE" && ssh_status="✅ ATTIVO"
                log_and_echo "  SSH Server:     $ssh_status (porta 22)"
                ;;
            rdp)
                local rdp_status="❌ NON ATTIVO"
                systemctl is-active --quiet xrdp && rdp_status="✅ ATTIVO"
                log_and_echo "  RDP Server:     $rdp_status (porta 3389)"
                ;;
            vnc)
                local vnc_status="⚠️  DA CONFIGURARE"
                command -v vncserver &>/dev/null && vnc_status="✅ INSTALLATO"
                log_and_echo "  VNC Server:     $vnc_status (porta 5901)"
                ;;
        esac
    done
    log_and_echo ""

    log_and_echo "${BOLD}Agent Status:${NC}"
    if systemctl is-active --quiet orizon-agent; then
        log_and_echo "  Stato:          ${GREEN}✅ ATTIVO${NC}"
        log_and_echo "  Avvio auto:     $(systemctl is-enabled orizon-agent)"
        log_and_echo "  Uptime:         $(systemctl show orizon-agent -p ActiveEnterTimestamp --value | cut -d' ' -f2-)"
    else
        log_and_echo "  Stato:          ${RED}❌ NON ATTIVO${NC}"
    fi
    log_and_echo ""

    log_and_echo "${BOLD}File Creati:${NC}"
    log_and_echo "  Config:         $CONFIG_FILE"
    log_and_echo "  Agent:          $AGENT_DIR/orizon_agent.py"
    log_and_echo "  Service:        /etc/systemd/system/orizon-agent.service"
    log_and_echo "  Log:            $LOG_FILE"
    log_and_echo ""

    log_and_echo "${BOLD}Statistiche Esecuzione:${NC}"
    log_and_echo "  ${GREEN}Successi:  $SUCCESS_COUNT${NC}"
    log_and_echo "  ${RED}Errori:    $FAILED_COUNT${NC}"
    log_and_echo "  ${YELLOW}Warning:   $WARNING_COUNT${NC}"
    log_and_echo ""

    if [[ $FAILED_COUNT -eq 0 ]]; then
        log_and_echo "${GREEN}${BOLD}✅ SETUP COMPLETATO CON SUCCESSO!${NC}"
    elif [[ $FAILED_COUNT -le 2 ]]; then
        log_and_echo "${YELLOW}${BOLD}⚠️  SETUP COMPLETATO CON ALCUNI WARNING${NC}"
    else
        log_and_echo "${RED}${BOLD}❌ SETUP COMPLETATO CON ERRORI${NC}"
    fi
    log_and_echo ""

    log_and_echo "${BOLD}Comandi Utili:${NC}"
    log_and_echo "  Stato agent:           systemctl status orizon-agent"
    log_and_echo "  Log agent:             journalctl -u orizon-agent -f"
    log_and_echo "  Restart agent:         systemctl restart orizon-agent"
    log_and_echo "  Stop agent:            systemctl stop orizon-agent"
    log_and_echo "  View config:           cat $CONFIG_FILE"
    log_and_echo "  View setup log:        cat $LOG_FILE"
    log_and_echo ""
}

# ═══════════════════════════════════════════════════════════════════════════
# FUNZIONI DI PARSING PARAMETRI
# ═══════════════════════════════════════════════════════════════════════════

usage() {
    cat << EOF
Uso: $SCRIPT_NAME [OPZIONI]

OPZIONI OBBLIGATORIE:
  --hub-ip <IP>           IP o FQDN del server HUB
  --hub-user <USER>       Username per SSH sul server HUB
  --hub-password <PWD>    Password per SSH sul server HUB
  --edge-name <NAME>      Nome dell'edge node
  --services <LIST>       Servizi da configurare (ssh,rdp,vnc)

OPZIONI FACOLTATIVE:
  --edge-ip <IP>          IP dell'edge (auto-rilevato se omesso)
  --edge-location <LOC>   Location geografica dell'edge (default: "Unknown")
  --help                  Mostra questo messaggio di aiuto

NOTA: Se l'edge non esiste nel database HUB, verrà creato automaticamente.

ESEMPI:
  # Setup completo con auto-registrazione e SSH/RDP
  sudo $SCRIPT_NAME \\
    --hub-ip 46.101.189.126 \\
    --hub-user orizonai \\
    --hub-password 'password' \\
    --edge-name UbuntuBot \\
    --edge-ip 192.168.3.101 \\
    --services ssh,rdp

  # Setup con IP auto-rilevato
  sudo $SCRIPT_NAME \\
    --hub-ip 46.101.189.126 \\
    --hub-user orizonai \\
    --hub-password 'password' \\
    --edge-name KaliEdge \\
    --services ssh,rdp,vnc

  # Setup completo con location personalizzata
  sudo $SCRIPT_NAME \\
    --hub-ip hub.example.com \\
    --hub-user admin \\
    --hub-password 'secret' \\
    --edge-name EdgeNode1 \\
    --edge-location "Data Center Amsterdam" \\
    --services ssh,rdp

EOF
    exit 1
}

parse_parameters() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --hub-ip)
                HUB_IP="$2"
                shift 2
                ;;
            --hub-user)
                HUB_USER="$2"
                shift 2
                ;;
            --hub-password)
                HUB_PASSWORD="$2"
                shift 2
                ;;
            --edge-name)
                EDGE_NAME="$2"
                shift 2
                ;;
            --edge-ip)
                EDGE_IP="$2"
                shift 2
                ;;
            --edge-location)
                EDGE_LOCATION="$2"
                shift 2
                ;;
            --services)
                SERVICES="$2"
                shift 2
                ;;
            --help)
                usage
                ;;
            *)
                echo "Opzione sconosciuta: $1"
                usage
                ;;
        esac
    done

    # Valida parametri obbligatori
    if [[ -z "$HUB_IP" || -z "$HUB_USER" || -z "$HUB_PASSWORD" || -z "$EDGE_NAME" || -z "$SERVICES" ]]; then
        echo "ERRORE: Parametri obbligatori mancanti"
        echo ""
        usage
    fi

    # ✅ NUOVO: Auto-rileva IP se non fornito
    if [[ -z "$EDGE_IP" ]]; then
        EDGE_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
        if [[ -z "$EDGE_IP" ]]; then
            EDGE_IP="0.0.0.0"
        fi
    fi

    # Default location
    EDGE_LOCATION="${EDGE_LOCATION:-Unknown Location}"
}

# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

main() {
    # Crea directory temporanea
    mkdir -p "$TEMP_DIR"

    # Inizia logging
    touch "$LOG_FILE"
    chmod 600 "$LOG_FILE"

    print_banner

    log_info "Inizio setup edge node - $(date)"
    log_info "Log file: $LOG_FILE"
    log_info "Edge IP: $EDGE_IP"
    log_and_echo ""

    # STEP 1: Verifica prerequisiti
    log_step "1" "Verifica Prerequisiti"
    check_root
    detect_os

    # STEP 2: Aggiornamento sistema e installazione dipendenze (MOVED HERE - sshpass needed for next steps)
    log_step "2" "Aggiornamento Sistema e Installazione Dipendenze"
    update_system
    install_dependencies || exit 1

    # STEP 3: Test connessione HUB (MOVED FROM STEP 2 - now sshpass is available)
    log_step "3" "Test Connessione al Server HUB"
    test_hub_connection || exit 1

    # STEP 4: Recupero informazioni dal HUB (MOVED FROM STEP 3 - now sshpass is available)
    log_step "4" "Recupero Configurazione dal HUB"
    fetch_node_info_from_hub || exit 1
    fetch_ssh_key_from_hub

    # STEP 5: Installazione servizi
    log_step "5" "Installazione Servizi Richiesti"
    install_services || exit 1

    # STEP 6: Test servizi locali
    log_step "6" "Verifica Servizi Locali"
    test_local_services

    # STEP 7: Download agent
    log_step "7" "Download e Configurazione Agent Orizon"
    download_agent || exit 1
    create_config_file || exit 1

    # STEP 8: Creazione servizio systemd
    log_step "8" "Creazione Servizio Systemd"
    create_systemd_service || exit 1

    # STEP 9: Avvio agent
    log_step "9" "Avvio Agent Orizon"
    start_agent || exit 1

    # STEP 10: Test connessione
    log_step "10" "Test Connessione e Tunnel"
    test_agent_connection
    test_tunnel_from_hub

    # STEP 11: Verifica traffico tunnel per ogni servizio
    log_step "11" "Verifica Traffico attraverso Tunnel"
    IFS=',' read -ra SERVICE_ARRAY <<< "$SERVICES"
    for service in "${SERVICE_ARRAY[@]}"; do
        service=$(echo "$service" | tr '[:upper:]' '[:lower:]' | xargs)
        case "$service" in
            ssh)
                verify_tunnel_traffic "SSH" "22"
                ;;
            rdp)
                verify_tunnel_traffic "RDP" "3389"
                ;;
            vnc)
                verify_tunnel_traffic "VNC" "5901"
                ;;
        esac
    done

    # STEP 12: Report finale
    log_step "12" "Report Finale"
    print_final_report

    log_info "Setup completato - $(date)"
}

# ═══════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════

parse_parameters "$@"
main

exit 0
