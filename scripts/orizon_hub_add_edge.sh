#!/bin/bash
#
# Orizon Hub - Add Edge Node Script
# Configura un nuovo edge node con servizi SSH, RDP, VNC
#
# Usage:
#   ./orizon_hub_add_edge.sh --name NOME --ip IP --services ssh,rdp,vnc
#   ./orizon_hub_add_edge.sh --show-config [NODE_NAME]
#

set -e

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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
    echo -e "\n${YELLOW}═══════════════════════════════════════════════════════${NC}"
    echo -e "${YELLOW}▶ STEP $1: $2${NC}"
    echo -e "${YELLOW}═══════════════════════════════════════════════════════${NC}\n"
}

# Configurazione
HUB_IP="46.101.189.126"
BACKEND_PATH="/root/orizon-ztc/backend"
SSH_KEYS_PATH="$BACKEND_PATH/ssh_keys"
DB_NAME="orizon_ztc"

# Variabili parametri
EDGE_NAME=""
EDGE_IP=""
SERVICES=""
SHOW_CONFIG=0

# Parse parametri
while [[ $# -gt 0 ]]; do
    case $1 in
        --name)
            EDGE_NAME="$2"
            shift 2
            ;;
        --ip)
            EDGE_IP="$2"
            shift 2
            ;;
        --services)
            SERVICES="$2"
            shift 2
            ;;
        --show-config)
            SHOW_CONFIG=1
            EDGE_NAME="${2:-}"
            shift
            if [[ -n "$EDGE_NAME" ]]; then
                shift
            fi
            ;;
        --help)
            echo "Usage:"
            echo "  $0 --name NOME --ip IP --services ssh,rdp,vnc"
            echo "  $0 --show-config [NODE_NAME]"
            echo ""
            echo "Options:"
            echo "  --name NAME          Nome del nodo edge (es: kali-edge)"
            echo "  --ip IP              Indirizzo IP del nodo edge"
            echo "  --services SERVICES  Servizi da abilitare: ssh,rdp,vnc (separati da virgola)"
            echo "  --show-config [NAME] Mostra la configurazione dei tunnel (opzionale: per un nodo specifico)"
            echo "  --help               Mostra questo messaggio"
            exit 0
            ;;
        *)
            log_error "Parametro sconosciuto: $1"
            exit 1
            ;;
    esac
done

# Funzione per mostrare la configurazione
show_configuration() {
    log_step "CONFIG" "Configurazione Tunnel Orizon Hub"

    if [[ -n "$1" ]]; then
        log_info "Configurazione per nodo: $1"

        # Query database per il nodo specifico
        NODE_INFO=$(sudo -u postgres psql -d "$DB_NAME" -t -c "
            SELECT id, name, ip_address, status, node_type
            FROM nodes
            WHERE name = '$1';" 2>/dev/null || echo "")

        if [[ -z "$NODE_INFO" ]]; then
            log_error "Nodo '$1' non trovato nel database"
            exit 1
        fi

        echo "$NODE_INFO" | while IFS='|' read -r id name ip status type; do
            id=$(echo "$id" | xargs)
            name=$(echo "$name" | xargs)
            ip=$(echo "$ip" | xargs)
            status=$(echo "$status" | xargs)
            type=$(echo "$type" | xargs)

            echo ""
            log_info "═══ Node Info ═══"
            echo "  ID:      $id"
            echo "  Name:    $name"
            echo "  IP:      $ip"
            echo "  Status:  $status"
            echo "  Type:    $type"
            echo ""

            # Verifica chiavi SSH
            log_info "═══ SSH Keys ═══"
            if [[ -f "$SSH_KEYS_PATH/${name}_key" ]]; then
                log_success "Private key: $SSH_KEYS_PATH/${name}_key"
                KEY_SIZE=$(stat -f%z "$SSH_KEYS_PATH/${name}_key" 2>/dev/null || stat -c%s "$SSH_KEYS_PATH/${name}_key" 2>/dev/null)
                echo "  Size: $KEY_SIZE bytes"
                if [[ -f "$SSH_KEYS_PATH/${name}_key.pub" ]]; then
                    log_success "Public key: $SSH_KEYS_PATH/${name}_key.pub"
                    echo "  Content: $(cat $SSH_KEYS_PATH/${name}_key.pub)"
                fi
            else
                log_warning "Nessuna chiave SSH trovata per questo nodo"
            fi

            echo ""
            log_info "═══ WebSocket Endpoints ═══"
            echo "  Agent Connection: wss://$HUB_IP/api/v1/agents/$id/connect"
            echo "  Terminal:         wss://$HUB_IP/api/v1/terminal/$id"
            echo "  RDP Session:      wss://$HUB_IP/api/v1/rdp/$id"
            echo "  VNC Session:      wss://$HUB_IP/api/v1/vnc/$id"

            echo ""
            log_info "═══ Tunnel Configuration ═══"
            echo "  SSH Tunnel (local): Edge connects to 127.0.0.1:22"
            echo "  RDP Tunnel (local): Edge connects to 127.0.0.1:3389"
            echo "  VNC Tunnel (local): Edge connects to 127.0.0.1:5900"
            echo ""
            echo "  Hub receives connections on:"
            echo "    - WebSocket: wss://$HUB_IP/api/v1/terminal/$id (SSH)"
            echo "    - WebSocket: wss://$HUB_IP/api/v1/rdp/$id (RDP)"
            echo "    - WebSocket: wss://$HUB_IP/api/v1/vnc/$id (VNC)"
        done

    else
        log_info "Configurazione di tutti i nodi edge"

        # Lista tutti i nodi
        sudo -u postgres psql -d "$DB_NAME" -c "
            SELECT name, ip_address, status, node_type, id
            FROM nodes
            ORDER BY name;" 2>/dev/null || {
            log_error "Impossibile leggere il database"
            exit 1
        }

        echo ""
        log_info "Per vedere i dettagli di un nodo specifico:"
        echo "  $0 --show-config NOME_NODO"
    fi

    echo ""
    log_info "═══ Backend Service Status ═══"
    systemctl status orizon-backend --no-pager | head -10

    echo ""
    log_info "═══ Active WebSocket Connections ═══"
    journalctl -u orizon-backend --since "10 minutes ago" --no-pager | \
        grep -E "Agent.*connected|WebSocket.*opened" | tail -10 || echo "  Nessuna connessione recente"
}

# Se richiesto solo show-config, esci
if [[ $SHOW_CONFIG -eq 1 ]]; then
    show_configuration "$EDGE_NAME"
    exit 0
fi

# Validazione parametri
if [[ -z "$EDGE_NAME" ]] || [[ -z "$EDGE_IP" ]] || [[ -z "$SERVICES" ]]; then
    log_error "Parametri mancanti!"
    echo "Usage: $0 --name NOME --ip IP --services ssh,rdp,vnc"
    echo "   or: $0 --show-config [NODE_NAME]"
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
echo -e "${GREEN}║         ORIZON HUB - ADD EDGE NODE                        ║${NC}"
echo -e "${GREEN}║         Zero Trust Connect Platform                       ║${NC}"
echo -e "${GREEN}║                                                           ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

log_info "Configurazione nuovo edge node:"
echo "  Nome:     $EDGE_NAME"
echo "  IP:       $EDGE_IP"
echo "  Servizi:  $SERVICES"
echo ""

# Step 1: Verifica prerequisiti
log_step "1" "Verifica Prerequisiti"

if ! command -v psql &> /dev/null; then
    log_error "PostgreSQL non installato"
    exit 1
fi
log_success "PostgreSQL installato"

if ! systemctl is-active --quiet orizon-backend; then
    log_warning "Backend Orizon non attivo"
    systemctl start orizon-backend
    sleep 2
fi
log_success "Backend Orizon attivo"

if [[ ! -d "$SSH_KEYS_PATH" ]]; then
    log_info "Creazione directory per chiavi SSH: $SSH_KEYS_PATH"
    mkdir -p "$SSH_KEYS_PATH"
    chmod 700 "$SSH_KEYS_PATH"
fi
log_success "Directory chiavi SSH: $SSH_KEYS_PATH"

# Step 2: Genera UUID per il nodo
log_step "2" "Generazione UUID per il nodo"

NODE_UUID=$(uuidgen | tr '[:upper:]' '[:lower:]')
log_success "UUID generato: $NODE_UUID"

# Step 3: Genera chiavi SSH
log_step "3" "Generazione Chiavi SSH"

SSH_KEY_FILE="$SSH_KEYS_PATH/${EDGE_NAME}_key"

if [[ -f "$SSH_KEY_FILE" ]]; then
    log_warning "Chiave SSH già esistente per $EDGE_NAME"
    read -p "Sovrascrivere? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Utilizzo chiave esistente"
    else
        rm -f "$SSH_KEY_FILE" "$SSH_KEY_FILE.pub"
    fi
fi

if [[ ! -f "$SSH_KEY_FILE" ]]; then
    log_info "Generazione coppia chiavi ed25519..."
    ssh-keygen -t ed25519 -f "$SSH_KEY_FILE" -C "orizon-hub-to-$EDGE_NAME" -N "" >/dev/null 2>&1
    chmod 600 "$SSH_KEY_FILE"
    chmod 644 "$SSH_KEY_FILE.pub"
    log_success "Chiavi generate:"
    echo "  Private: $SSH_KEY_FILE ($(stat -f%z "$SSH_KEY_FILE" 2>/dev/null || stat -c%s "$SSH_KEY_FILE") bytes)"
    echo "  Public:  $SSH_KEY_FILE.pub"
    echo "  Content: $(cat $SSH_KEY_FILE.pub)"
fi

PUBLIC_KEY=$(cat "$SSH_KEY_FILE.pub")
log_success "Chiave pubblica pronta per il deployment"

# Step 4: Registra nodo nel database
log_step "4" "Registrazione Nodo nel Database"

# Verifica se il nodo esiste già
EXISTING_NODE=$(sudo -u postgres psql -d "$DB_NAME" -t -c "SELECT id FROM nodes WHERE name = '$EDGE_NAME';" 2>/dev/null | xargs)

if [[ -n "$EXISTING_NODE" ]]; then
    log_warning "Nodo '$EDGE_NAME' già esistente nel database (ID: $EXISTING_NODE)"
    read -p "Vuoi aggiornare il nodo esistente? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sudo -u postgres psql -d "$DB_NAME" -c "
            UPDATE nodes
            SET ip_address = '$EDGE_IP',
                status = 'offline',
                updated_at = NOW()
            WHERE name = '$EDGE_NAME';" >/dev/null 2>&1
        NODE_UUID=$EXISTING_NODE
        log_success "Nodo aggiornato nel database"
    else
        log_info "Utilizzo nodo esistente"
        NODE_UUID=$EXISTING_NODE
    fi
else
    log_info "Inserimento nuovo nodo nel database..."
    sudo -u postgres psql -d "$DB_NAME" -c "
        INSERT INTO nodes (id, name, ip_address, status, node_type, created_at, updated_at)
        VALUES ('$NODE_UUID', '$EDGE_NAME', '$EDGE_IP', 'offline', 'edge', NOW(), NOW())
        ON CONFLICT (id) DO UPDATE
        SET ip_address = '$EDGE_IP', updated_at = NOW();" >/dev/null 2>&1

    if [[ $? -eq 0 ]]; then
        log_success "Nodo registrato nel database"
    else
        log_error "Errore durante la registrazione nel database"
        exit 1
    fi
fi

# Verifica inserimento
DB_CHECK=$(sudo -u postgres psql -d "$DB_NAME" -t -c "SELECT name, ip_address, status FROM nodes WHERE id = '$NODE_UUID';" 2>/dev/null)
log_info "Verifica database:"
echo "$DB_CHECK"

# Step 5: Genera token JWT
log_step "5" "Generazione Token JWT"

# Leggi la secret key dal file .env
JWT_SECRET=$(grep '^SECRET_KEY=' "$BACKEND_PATH/.env" | cut -d'=' -f2 | tr -d '"' | tr -d "'")

if [[ -z "$JWT_SECRET" ]]; then
    log_error "SECRET_KEY non trovata nel file .env"
    exit 1
fi

log_info "Generazione JWT token per il nodo..."

# Genera token con python
JWT_TOKEN=$(python3 -c "
import jwt
import datetime

payload = {
    'sub': '$NODE_UUID',
    'node_name': '$EDGE_NAME',
    'node_type': 'edge',
    'exp': datetime.datetime.utcnow() + datetime.timedelta(days=365)
}

token = jwt.encode(payload, '$JWT_SECRET', algorithm='HS256')
print(token)
")

if [[ -n "$JWT_TOKEN" ]]; then
    log_success "JWT Token generato"
    echo "  Token: ${JWT_TOKEN:0:50}..."
else
    log_error "Errore nella generazione del token"
    exit 1
fi

# Step 6: Prepara configurazione servizi
log_step "6" "Configurazione Servizi"

IFS=',' read -ra SERVICE_ARRAY <<< "$SERVICES"

SSH_ENABLED=0
RDP_ENABLED=0
VNC_ENABLED=0

for service in "${SERVICE_ARRAY[@]}"; do
    service=$(echo "$service" | xargs | tr '[:upper:]' '[:lower:]')
    case "$service" in
        ssh)
            SSH_ENABLED=1
            log_success "✓ SSH abilitato"
            ;;
        rdp)
            RDP_ENABLED=1
            log_success "✓ RDP abilitato"
            ;;
        vnc)
            VNC_ENABLED=1
            log_success "✓ VNC abilitato"
            ;;
        *)
            log_warning "Servizio sconosciuto: $service (ignorato)"
            ;;
    esac
done

# Step 7: Crea script di installazione per l'edge
log_step "7" "Generazione Script di Setup Edge"

SETUP_SCRIPT="/tmp/setup_${EDGE_NAME}.sh"

cat > "$SETUP_SCRIPT" << 'EDGE_SCRIPT_EOF'
#!/bin/bash
# Script generato automaticamente da Orizon Hub
# Configurazione edge node

EDGE_SCRIPT_EOF

cat >> "$SETUP_SCRIPT" << EDGE_SCRIPT_EOF
# Configurazione
EDGE_NAME="$EDGE_NAME"
NODE_UUID="$NODE_UUID"
HUB_URL="https://$HUB_IP"
JWT_TOKEN="$JWT_TOKEN"
SSH_ENABLED=$SSH_ENABLED
RDP_ENABLED=$RDP_ENABLED
VNC_ENABLED=$VNC_ENABLED

# Chiave pubblica SSH
SSH_PUBLIC_KEY="$PUBLIC_KEY"

EDGE_SCRIPT_EOF

cat >> "$SETUP_SCRIPT" << 'EDGE_SCRIPT_EOF'

# Output colorato
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     ORIZON EDGE - Node Setup Script                      ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

log_info "Node Name: $EDGE_NAME"
log_info "Node UUID: $NODE_UUID"
log_info "Hub URL: $HUB_URL"
echo ""

# Scarica e installa
log_info "Scaricamento ed esecuzione script di setup edge..."
curl -k -s "$HUB_URL/api/v1/downloads/orizon_agent.py" -o /tmp/setup_edge_installer.sh
chmod +x /tmp/setup_edge_installer.sh

# Passa i parametri
export EDGE_NAME="$EDGE_NAME"
export NODE_UUID="$NODE_UUID"
export HUB_URL="$HUB_URL"
export JWT_TOKEN="$JWT_TOKEN"
export SSH_ENABLED="$SSH_ENABLED"
export RDP_ENABLED="$RDP_ENABLED"
export VNC_ENABLED="$VNC_ENABLED"
export SSH_PUBLIC_KEY="$SSH_PUBLIC_KEY"

bash /tmp/setup_edge_installer.sh

EDGE_SCRIPT_EOF

chmod +x "$SETUP_SCRIPT"
log_success "Script di setup creato: $SETUP_SCRIPT"

# Step 8: Riepilogo finale
log_step "8" "Riepilogo Configurazione"

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              CONFIGURAZIONE COMPLETATA                    ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

log_info "═══ Node Information ═══"
echo "  Name:        $EDGE_NAME"
echo "  UUID:        $NODE_UUID"
echo "  IP Address:  $EDGE_IP"
echo "  Status:      offline (waiting for agent connection)"
echo ""

log_info "═══ Services Enabled ═══"
[[ $SSH_ENABLED -eq 1 ]] && echo "  ✓ SSH (port 22)"
[[ $RDP_ENABLED -eq 1 ]] && echo "  ✓ RDP (port 3389)"
[[ $VNC_ENABLED -eq 1 ]] && echo "  ✓ VNC (port 5900)"
echo ""

log_info "═══ SSH Keys ═══"
echo "  Private Key: $SSH_KEY_FILE"
echo "  Public Key:  $SSH_KEY_FILE.pub"
echo "  Key Type:    ed25519"
echo ""

log_info "═══ WebSocket Endpoints ═══"
echo "  Agent:    wss://$HUB_IP/api/v1/agents/$NODE_UUID/connect"
[[ $SSH_ENABLED -eq 1 ]] && echo "  SSH:      wss://$HUB_IP/api/v1/terminal/$NODE_UUID"
[[ $RDP_ENABLED -eq 1 ]] && echo "  RDP:      wss://$HUB_IP/api/v1/rdp/$NODE_UUID"
[[ $VNC_ENABLED -eq 1 ]] && echo "  VNC:      wss://$HUB_IP/api/v1/vnc/$NODE_UUID"
echo ""

log_info "═══ Tunnel Configuration ═══"
echo "  Hub Side (questo server):"
echo "    - Backend riceve connessioni WebSocket dalle porte sopra"
echo "    - I dati vengono proxy-ati attraverso il WebSocket verso l'edge"
echo ""
echo "  Edge Side (nodo remoto):"
[[ $SSH_ENABLED -eq 1 ]] && echo "    - SSH tunnel: Edge espone 127.0.0.1:22 verso Hub via WebSocket"
[[ $RDP_ENABLED -eq 1 ]] && echo "    - RDP tunnel: Edge espone 127.0.0.1:3389 verso Hub via WebSocket"
[[ $VNC_ENABLED -eq 1 ]] && echo "    - VNC tunnel: Edge espone 127.0.0.1:5900 verso Hub via WebSocket"
echo ""

log_info "═══ Next Steps ═══"
echo "  1. Copia lo script di setup sull'edge node:"
echo "     ${YELLOW}scp $SETUP_SCRIPT user@$EDGE_IP:/tmp/${NC}"
echo ""
echo "  2. Esegui lo script sull'edge node:"
echo "     ${YELLOW}ssh user@$EDGE_IP 'sudo bash /tmp/$(basename $SETUP_SCRIPT)'${NC}"
echo ""
echo "  3. Verifica la connessione:"
echo "     ${YELLOW}journalctl -u orizon-backend -f | grep '$EDGE_NAME'${NC}"
echo ""
echo "  4. Per vedere la configurazione dei tunnel:"
echo "     ${YELLOW}$0 --show-config $EDGE_NAME${NC}"
echo ""

log_success "Configurazione Hub completata con successo!"
echo ""
