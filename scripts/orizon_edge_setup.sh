#!/bin/bash
#
# Orizon Edge - Node Setup Script
# Configura un nodo edge con servizi SSH, RDP, VNC
#
# Usage:
#   ./orizon_edge_setup.sh --name NOME --hub-ip IP --token TOKEN --services ssh,rdp,vnc
#   ./orizon_edge_setup.sh --show-config
#

set -e

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Funzioni di output
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[⚠]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

log_step() {
    echo -e "\n${CYAN}═══════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}▶ STEP $1: $2${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}\n"
}

# Variabili
EDGE_NAME=""
HUB_IP=""
JWT_TOKEN=""
SERVICES=""
SSH_PUBLIC_KEY=""
SHOW_CONFIG=0

# Configurazione
AGENT_DIR="/opt/orizon"
AGENT_FILE="$AGENT_DIR/orizon_agent.py"
CONFIG_FILE="$AGENT_DIR/config.json"
SSH_KEYS_DIR="$AGENT_DIR/ssh_keys"
SERVICE_FILE="/etc/systemd/system/orizon-agent.service"

# Parse parametri
while [[ $# -gt 0 ]]; do
    case $1 in
        --name)
            EDGE_NAME="$2"
            shift 2
            ;;
        --hub-ip)
            HUB_IP="$2"
            shift 2
            ;;
        --token)
            JWT_TOKEN="$2"
            shift 2
            ;;
        --services)
            SERVICES="$2"
            shift 2
            ;;
        --ssh-pubkey)
            SSH_PUBLIC_KEY="$2"
            shift 2
            ;;
        --show-config)
            SHOW_CONFIG=1
            shift
            ;;
        --help)
            echo "Usage:"
            echo "  $0 --name NOME --hub-ip IP --token TOKEN --services ssh,rdp,vnc [--ssh-pubkey KEY]"
            echo "  $0 --show-config"
            echo ""
            echo "Options:"
            echo "  --name NAME          Nome del nodo edge"
            echo "  --hub-ip IP          Indirizzo IP dell'Orizon Hub"
            echo "  --token TOKEN        JWT token per l'autenticazione"
            echo "  --services SERVICES  Servizi da abilitare: ssh,rdp,vnc"
            echo "  --ssh-pubkey KEY     Chiave pubblica SSH da installare"
            echo "  --show-config        Mostra la configurazione attuale"
            echo "  --help               Mostra questo messaggio"
            exit 0
            ;;
        *)
            log_error "Parametro sconosciuto: $1"
            exit 1
            ;;
    esac
done

# Funzione per rilevare il sistema operativo
detect_os() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        OS_NAME=$ID
        OS_VERSION=$VERSION_ID
        OS_PRETTY=$PRETTY_NAME
    else
        OS_NAME="unknown"
        OS_VERSION="unknown"
        OS_PRETTY="Unknown OS"
    fi

    case "$OS_NAME" in
        ubuntu|debian|kali|mint|pop|parrot)
            OS_FAMILY="debian"
            PKG_MANAGER="apt"
            ;;
        fedora|rhel|centos|rocky|alma)
            OS_FAMILY="redhat"
            PKG_MANAGER="dnf"
            ;;
        arch|manjaro)
            OS_FAMILY="arch"
            PKG_MANAGER="pacman"
            ;;
        *)
            OS_FAMILY="unknown"
            PKG_MANAGER="unknown"
            ;;
    esac
}

# Funzione per mostrare la configurazione
show_configuration() {
    log_step "CONFIG" "Configurazione Orizon Edge Node"

    detect_os

    echo ""
    log_info "═══ System Information ═══"
    echo "  OS:            $OS_PRETTY"
    echo "  OS Family:     $OS_FAMILY"
    echo "  Pkg Manager:   $PKG_MANAGER"
    echo "  Hostname:      $(hostname)"
    echo "  IP Addresses:  $(hostname -I 2>/dev/null || echo 'N/A')"
    echo ""

    if [[ -f "$CONFIG_FILE" ]]; then
        log_info "═══ Agent Configuration ═══"
        echo "  Config File:   $CONFIG_FILE"

        NODE_ID=$(grep -oP '"node_id":\s*"\K[^"]+' "$CONFIG_FILE" 2>/dev/null || echo "N/A")
        HUB_URL=$(grep -oP '"hub_url":\s*"\K[^"]+' "$CONFIG_FILE" 2>/dev/null || echo "N/A")

        echo "  Node ID:       $NODE_ID"
        echo "  Hub URL:       $HUB_URL"
        echo ""

        log_info "═══ WebSocket Endpoints ═══"
        echo "  Agent:         $HUB_URL/api/v1/agents/$NODE_ID/connect"
        echo "  Terminal:      $HUB_URL/api/v1/terminal/$NODE_ID"
        echo "  RDP:           $HUB_URL/api/v1/rdp/$NODE_ID"
        echo "  VNC:           $HUB_URL/api/v1/vnc/$NODE_ID"
        echo ""
    else
        log_warning "Agent non configurato (file config.json non trovato)"
    fi

    log_info "═══ Installed Services ═══"

    # SSH
    if systemctl is-active --quiet sshd || systemctl is-active --quiet ssh; then
        log_success "SSH - ACTIVE"
        echo "    Port: $(ss -tlnp | grep -E ':22\s' | head -1 | awk '{print $4}' || echo '22')"
        echo "    Users: $(getent passwd | grep -E '/home|/root' | cut -d: -f1 | tr '\n' ' ')"
    else
        echo "  SSH - not installed"
    fi

    # RDP
    if systemctl is-active --quiet xrdp; then
        log_success "RDP (xrdp) - ACTIVE"
        echo "    Port: $(ss -tlnp | grep -E ':3389\s' | head -1 | awk '{print $4}' || echo '3389')"
    else
        echo "  RDP (xrdp) - not installed"
    fi

    # VNC
    if systemctl list-units --type=service | grep -q vnc; then
        log_success "VNC - ACTIVE"
        echo "    Port: $(ss -tlnp | grep -E ':590[0-9]\s' | head -1 | awk '{print $4}' || echo '5900')"
    elif command -v vncserver &> /dev/null; then
        log_warning "VNC - INSTALLED (not running)"
    else
        echo "  VNC - not installed"
    fi

    echo ""
    log_info "═══ Agent Status ═══"
    if systemctl is-active --quiet orizon-agent; then
        log_success "Orizon Agent - RUNNING"
        systemctl status orizon-agent --no-pager | grep -E "Active:|Main PID:|Memory:|CPU:"
    else
        log_warning "Orizon Agent - NOT RUNNING"
    fi

    echo ""
    log_info "═══ Local Tunnel Configuration ═══"
    echo "  L'agent crea tunnel WebSocket inversi verso l'Hub:"
    echo ""
    echo "  [Edge Node] ←→ WebSocket ←→ [Orizon Hub]"
    echo ""
    echo "  Servizi locali esposti attraverso i tunnel:"
    [[ $(systemctl is-active sshd ssh 2>/dev/null) == "active" ]] && \
        echo "    • SSH:  127.0.0.1:22   → wss://HUB/api/v1/terminal/NODE_ID"
    [[ $(systemctl is-active xrdp 2>/dev/null) == "active" ]] && \
        echo "    • RDP:  127.0.0.1:3389 → wss://HUB/api/v1/rdp/NODE_ID"
    command -v vncserver &>/dev/null && \
        echo "    • VNC:  127.0.0.1:5900 → wss://HUB/api/v1/vnc/NODE_ID"
    echo ""

    log_info "═══ SSH Keys ═══"
    if [[ -d "$SSH_KEYS_DIR" ]]; then
        echo "  Keys Directory: $SSH_KEYS_DIR"
        ls -lh "$SSH_KEYS_DIR" 2>/dev/null || echo "  (empty)"
    else
        echo "  No SSH keys directory found"
    fi

    # Authorized keys per utenti
    echo ""
    echo "  Authorized Keys:"
    for user in $(getent passwd | grep -E '/home|/root' | cut -d: -f1); do
        user_home=$(getent passwd "$user" | cut -d: -f6)
        if [[ -f "$user_home/.ssh/authorized_keys" ]]; then
            key_count=$(wc -l < "$user_home/.ssh/authorized_keys")
            echo "    $user: $key_count key(s)"
        fi
    done

    echo ""
    log_info "═══ Network Information ═══"
    echo "  Active Connections:"
    ss -tn | grep ESTAB | grep -E ':(22|3389|5900|443)' || echo "  (none)"

    echo ""
    log_info "═══ Recent Agent Logs ═══"
    if systemctl is-active --quiet orizon-agent; then
        journalctl -u orizon-agent --no-pager -n 10 | tail -5
    else
        echo "  Agent not running"
    fi

    echo ""
}

# Se richiesto solo show-config, esci
if [[ $SHOW_CONFIG -eq 1 ]]; then
    show_configuration
    exit 0
fi

# Validazione parametri
if [[ -z "$EDGE_NAME" ]] || [[ -z "$HUB_IP" ]] || [[ -z "$JWT_TOKEN" ]] || [[ -z "$SERVICES" ]]; then
    log_error "Parametri mancanti!"
    echo "Usage: $0 --name NOME --hub-ip IP --token TOKEN --services ssh,rdp,vnc"
    echo "   or: $0 --show-config"
    exit 1
fi

# Verifica se eseguito come root
if [[ $EUID -ne 0 ]]; then
   log_error "Questo script deve essere eseguito come root"
   exit 1
fi

# Banner
echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                           ║${NC}"
echo -e "${GREEN}║         ORIZON EDGE - Node Setup                          ║${NC}"
echo -e "${GREEN}║         Zero Trust Connect Platform                       ║${NC}"
echo -e "${GREEN}║                                                           ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Step 1: Rileva sistema operativo
log_step "1" "Rilevamento Sistema Operativo"

detect_os

log_info "Sistema Rilevato:"
echo "  OS:            $OS_PRETTY"
echo "  OS Name:       $OS_NAME"
echo "  OS Version:    $OS_VERSION"
echo "  OS Family:     $OS_FAMILY"
echo "  Pkg Manager:   $PKG_MANAGER"
echo ""

if [[ "$OS_FAMILY" == "unknown" ]]; then
    log_error "Sistema operativo non supportato"
    exit 1
fi

log_success "Sistema operativo riconosciuto"

# Step 2: Aggiorna sistema e installa dipendenze base
log_step "2" "Aggiornamento Sistema e Dipendenze Base"

log_info "Aggiornamento package manager..."

case "$PKG_MANAGER" in
    apt)
        apt-get update -qq
        log_success "apt-get update completato"

        log_info "Installazione dipendenze base..."
        DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
            python3 python3-pip curl wget gnupg2 ca-certificates \
            openssh-client net-tools >/dev/null 2>&1
        ;;
    dnf)
        dnf check-update -q || true
        log_success "dnf check-update completato"

        log_info "Installazione dipendenze base..."
        dnf install -y -q \
            python3 python3-pip curl wget gnupg2 ca-certificates \
            openssh-clients net-tools >/dev/null 2>&1
        ;;
    pacman)
        pacman -Sy --noconfirm >/dev/null 2>&1
        log_success "pacman -Sy completato"

        log_info "Installazione dipendenze base..."
        pacman -S --noconfirm --needed \
            python python-pip curl wget gnupg ca-certificates \
            openssh net-tools >/dev/null 2>&1
        ;;
esac

log_success "Dipendenze base installate"

# Step 3: Installa librerie Python
log_step "3" "Installazione Librerie Python"

log_info "Installazione librerie Python richieste..."
pip3 install --quiet --upgrade pip >/dev/null 2>&1
pip3 install --quiet websockets paramiko pyjwt >/dev/null 2>&1

log_success "Librerie Python installate"
python3 --version
pip3 list | grep -E "websockets|paramiko|pyjwt"

# Step 4: Configura servizi richiesti
log_step "4" "Configurazione Servizi"

IFS=',' read -ra SERVICE_ARRAY <<< "$SERVICES"

SSH_ENABLED=0
RDP_ENABLED=0
VNC_ENABLED=0

for service in "${SERVICE_ARRAY[@]}"; do
    service=$(echo "$service" | xargs | tr '[:upper:]' '[:lower:]')

    case "$service" in
        ssh)
            SSH_ENABLED=1
            log_info "Configurazione SSH..."

            case "$PKG_MANAGER" in
                apt)
                    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq openssh-server >/dev/null 2>&1
                    systemctl enable ssh >/dev/null 2>&1
                    systemctl start ssh >/dev/null 2>&1
                    ;;
                dnf)
                    dnf install -y -q openssh-server >/dev/null 2>&1
                    systemctl enable sshd >/dev/null 2>&1
                    systemctl start sshd >/dev/null 2>&1
                    ;;
                pacman)
                    pacman -S --noconfirm --needed openssh >/dev/null 2>&1
                    systemctl enable sshd >/dev/null 2>&1
                    systemctl start sshd >/dev/null 2>&1
                    ;;
            esac

            if systemctl is-active --quiet sshd || systemctl is-active --quiet ssh; then
                log_success "✓ SSH installato e attivo (porta 22)"

                # Installa chiave pubblica se fornita
                if [[ -n "$SSH_PUBLIC_KEY" ]]; then
                    log_info "Installazione chiave pubblica SSH..."

                    # Installa per root
                    mkdir -p /root/.ssh
                    chmod 700 /root/.ssh
                    echo "$SSH_PUBLIC_KEY" >> /root/.ssh/authorized_keys
                    chmod 600 /root/.ssh/authorized_keys

                    # Installa per primo utente non-root
                    FIRST_USER=$(getent passwd | grep -E '/home' | head -1 | cut -d: -f1)
                    if [[ -n "$FIRST_USER" ]]; then
                        USER_HOME=$(getent passwd "$FIRST_USER" | cut -d: -f6)
                        mkdir -p "$USER_HOME/.ssh"
                        echo "$SSH_PUBLIC_KEY" >> "$USER_HOME/.ssh/authorized_keys"
                        chown -R "$FIRST_USER:$FIRST_USER" "$USER_HOME/.ssh"
                        chmod 700 "$USER_HOME/.ssh"
                        chmod 600 "$USER_HOME/.ssh/authorized_keys"
                        log_success "Chiave installata per utenti: root, $FIRST_USER"
                    else
                        log_success "Chiave installata per utente: root"
                    fi
                fi
            else
                log_error "Errore nell'installazione di SSH"
            fi
            ;;

        rdp)
            RDP_ENABLED=1
            log_info "Configurazione RDP (xrdp)..."

            case "$PKG_MANAGER" in
                apt)
                    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq xrdp xorgxrdp >/dev/null 2>&1

                    # Installa ambiente desktop se necessario
                    if ! dpkg -l | grep -qE 'xfce4|mate-desktop|gnome-core'; then
                        log_info "Installazione ambiente desktop XFCE4 (richiesto per RDP)..."
                        DEBIAN_FRONTEND=noninteractive apt-get install -y -qq xfce4 xfce4-goodies >/dev/null 2>&1
                    fi

                    systemctl enable xrdp >/dev/null 2>&1
                    systemctl start xrdp >/dev/null 2>&1
                    ;;
                dnf)
                    dnf install -y -q xrdp >/dev/null 2>&1

                    # Installa ambiente desktop se necessario
                    if ! rpm -qa | grep -qE 'xfce|mate|gnome'; then
                        log_info "Installazione gruppo desktop..."
                        dnf groupinstall -y -q "Xfce Desktop" >/dev/null 2>&1 || \
                        dnf groupinstall -y -q "MATE Desktop" >/dev/null 2>&1
                    fi

                    systemctl enable xrdp >/dev/null 2>&1
                    systemctl start xrdp >/dev/null 2>&1
                    ;;
                pacman)
                    pacman -S --noconfirm --needed xrdp xorgxrdp >/dev/null 2>&1

                    if ! pacman -Qi xfce4 >/dev/null 2>&1; then
                        log_info "Installazione XFCE4..."
                        pacman -S --noconfirm --needed xfce4 xfce4-goodies >/dev/null 2>&1
                    fi

                    systemctl enable xrdp >/dev/null 2>&1
                    systemctl start xrdp >/dev/null 2>&1
                    ;;
            esac

            if systemctl is-active --quiet xrdp; then
                log_success "✓ RDP (xrdp) installato e attivo (porta 3389)"
            else
                log_warning "RDP installato ma non attivo (potrebbe richiedere configurazione manuale)"
            fi
            ;;

        vnc)
            VNC_ENABLED=1
            log_info "Configurazione VNC..."

            case "$PKG_MANAGER" in
                apt)
                    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq tigervnc-standalone-server tigervnc-common >/dev/null 2>&1
                    ;;
                dnf)
                    dnf install -y -q tigervnc-server >/dev/null 2>&1
                    ;;
                pacman)
                    pacman -S --noconfirm --needed tigervnc >/dev/null 2>&1
                    ;;
            esac

            if command -v vncserver &> /dev/null; then
                log_success "✓ VNC (TigerVNC) installato (porta 5900)"
                log_info "Nota: VNC richiede configurazione per utente (vncserver :1)"
            else
                log_error "Errore nell'installazione di VNC"
            fi
            ;;

        *)
            log_warning "Servizio sconosciuto: $service (ignorato)"
            ;;
    esac
done

# Step 5: Crea directory agent
log_step "5" "Preparazione Directory Agent"

log_info "Creazione directory $AGENT_DIR..."
mkdir -p "$AGENT_DIR"
mkdir -p "$SSH_KEYS_DIR"
chmod 700 "$AGENT_DIR"
chmod 700 "$SSH_KEYS_DIR"

log_success "Directory agent create"
ls -lhd "$AGENT_DIR" "$SSH_KEYS_DIR"

# Step 6: Scarica agent
log_step "6" "Download Agent Orizon"

HUB_URL="https://$HUB_IP"
AGENT_DOWNLOAD_URL="$HUB_URL/api/v1/downloads/orizon_agent.py"

log_info "Scaricamento agent da: $AGENT_DOWNLOAD_URL"

curl -k -s "$AGENT_DOWNLOAD_URL" -o "$AGENT_FILE" 2>&1 | grep -v "InsecureRequestWarning" || true

if [[ -f "$AGENT_FILE" ]] && [[ $(stat -f%z "$AGENT_FILE" 2>/dev/null || stat -c%s "$AGENT_FILE" 2>/dev/null) -gt 1000 ]]; then
    chmod +x "$AGENT_FILE"
    log_success "Agent scaricato: $AGENT_FILE"
    log_info "Dimensione: $(stat -f%z "$AGENT_FILE" 2>/dev/null || stat -c%s "$AGENT_FILE") bytes"
    log_info "Prime righe:"
    head -3 "$AGENT_FILE"
else
    log_error "Errore nel download dell'agent"
    exit 1
fi

# Step 7: Genera configurazione
log_step "7" "Generazione File di Configurazione"

log_info "Creazione config.json..."

# Estrai NODE_ID dal token JWT
NODE_ID=$(python3 -c "
import jwt
import sys
try:
    token = '$JWT_TOKEN'
    decoded = jwt.decode(token, options={'verify_signature': False})
    print(decoded.get('sub', ''))
except:
    sys.exit(1)
" 2>/dev/null)

if [[ -z "$NODE_ID" ]]; then
    log_error "Impossibile estrarre NODE_ID dal token JWT"
    exit 1
fi

log_info "Node ID estratto: $NODE_ID"

cat > "$CONFIG_FILE" << EOF
{
    "node_id": "$NODE_ID",
    "node_name": "$EDGE_NAME",
    "hub_url": "wss://$HUB_IP",
    "jwt_token": "$JWT_TOKEN",
    "services": {
        "ssh": $([[ $SSH_ENABLED -eq 1 ]] && echo "true" || echo "false"),
        "rdp": $([[ $RDP_ENABLED -eq 1 ]] && echo "true" || echo "false"),
        "vnc": $([[ $VNC_ENABLED -eq 1 ]] && echo "true" || echo "false")
    },
    "reconnect_interval": 5,
    "heartbeat_interval": 30
}
EOF

chmod 600 "$CONFIG_FILE"
log_success "File di configurazione creato: $CONFIG_FILE"

# Step 8: Crea servizio systemd
log_step "8" "Creazione Servizio Systemd"

log_info "Creazione orizon-agent.service..."

cat > "$SERVICE_FILE" << EOF
[Unit]
Description=Orizon Zero Trust Connect Agent
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=$AGENT_DIR
ExecStart=/usr/bin/python3 $AGENT_FILE -c $CONFIG_FILE
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

log_success "File servizio creato: $SERVICE_FILE"

log_info "Ricaricamento systemd e avvio servizio..."
systemctl daemon-reload
systemctl enable orizon-agent >/dev/null 2>&1
systemctl start orizon-agent

sleep 3

if systemctl is-active --quiet orizon-agent; then
    log_success "✓ Servizio orizon-agent attivo"
    systemctl status orizon-agent --no-pager | head -10
else
    log_error "Servizio orizon-agent non attivo"
    log_info "Log del servizio:"
    journalctl -u orizon-agent --no-pager -n 20
    exit 1
fi

# Step 9: Verifica connessione
log_step "9" "Verifica Connessione al Hub"

log_info "Attesa connessione al hub (10 secondi)..."
sleep 10

log_info "Ultimi log dell'agent:"
journalctl -u orizon-agent --no-pager -n 20 | tail -10

if journalctl -u orizon-agent --since "1 minute ago" --no-pager | grep -q "Connected to hub"; then
    log_success "✓ Agent connesso all'hub!"
else
    log_warning "Connessione all'hub non confermata nei log"
    log_info "Verifica manualmente con: journalctl -u orizon-agent -f"
fi

# Step 10: Riepilogo finale
log_step "10" "Riepilogo Configurazione"

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              CONFIGURAZIONE COMPLETATA                    ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

log_info "═══ System Information ═══"
echo "  Hostname:      $(hostname)"
echo "  OS:            $OS_PRETTY"
echo "  IP Addresses:  $(hostname -I 2>/dev/null)"
echo ""

log_info "═══ Node Configuration ═══"
echo "  Node Name:     $EDGE_NAME"
echo "  Node ID:       $NODE_ID"
echo "  Hub URL:       wss://$HUB_IP"
echo ""

log_info "═══ Services Installed ═══"
[[ $SSH_ENABLED -eq 1 ]] && echo "  ✓ SSH   - Port 22   - $(systemctl is-active sshd ssh 2>/dev/null)"
[[ $RDP_ENABLED -eq 1 ]] && echo "  ✓ RDP   - Port 3389 - $(systemctl is-active xrdp 2>/dev/null)"
[[ $VNC_ENABLED -eq 1 ]] && echo "  ✓ VNC   - Port 5900 - $(command -v vncserver >/dev/null && echo 'installed' || echo 'not found')"
echo ""

log_info "═══ Local Tunnel Endpoints ═══"
echo "  I seguenti servizi locali sono ora accessibili tramite l'Hub:"
echo ""
[[ $SSH_ENABLED -eq 1 ]] && echo "  • SSH Terminal:"
[[ $SSH_ENABLED -eq 1 ]] && echo "      Local:  127.0.0.1:22"
[[ $SSH_ENABLED -eq 1 ]] && echo "      Remote: wss://$HUB_IP/api/v1/terminal/$NODE_ID"
[[ $SSH_ENABLED -eq 1 ]] && echo ""
[[ $RDP_ENABLED -eq 1 ]] && echo "  • RDP Desktop:"
[[ $RDP_ENABLED -eq 1 ]] && echo "      Local:  127.0.0.1:3389"
[[ $RDP_ENABLED -eq 1 ]] && echo "      Remote: wss://$HUB_IP/api/v1/rdp/$NODE_ID"
[[ $RDP_ENABLED -eq 1 ]] && echo ""
[[ $VNC_ENABLED -eq 1 ]] && echo "  • VNC Desktop:"
[[ $VNC_ENABLED -eq 1 ]] && echo "      Local:  127.0.0.1:5900"
[[ $VNC_ENABLED -eq 1 ]] && echo "      Remote: wss://$HUB_IP/api/v1/vnc/$NODE_ID"
[[ $VNC_ENABLED -eq 1 ]] && echo ""

log_info "═══ Agent Service ═══"
echo "  Status:  $(systemctl is-active orizon-agent)"
echo "  Logs:    journalctl -u orizon-agent -f"
echo "  Restart: systemctl restart orizon-agent"
echo "  Stop:    systemctl stop orizon-agent"
echo ""

log_info "═══ Files Created ═══"
echo "  Agent:   $AGENT_FILE"
echo "  Config:  $CONFIG_FILE"
echo "  Service: $SERVICE_FILE"
echo "  SSH Keys: $SSH_KEYS_DIR"
echo ""

log_info "═══ Commands ═══"
echo "  Mostra configurazione:"
echo "    ${YELLOW}$0 --show-config${NC}"
echo ""
echo "  Verifica connessione:"
echo "    ${YELLOW}journalctl -u orizon-agent -f${NC}"
echo ""
echo "  Test servizi locali:"
[[ $SSH_ENABLED -eq 1 ]] && echo "    ${YELLOW}ssh localhost${NC}"
[[ $RDP_ENABLED -eq 1 ]] && echo "    ${YELLOW}xfreerdp /v:localhost:3389${NC}"
[[ $VNC_ENABLED -eq 1 ]] && echo "    ${YELLOW}vncviewer localhost:5900${NC}"
echo ""

log_success "Setup Edge Node completato con successo!"
echo ""
