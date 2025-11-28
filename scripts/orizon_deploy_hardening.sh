#!/bin/bash
# =============================================================================
# ORIZON DEPLOY HARDENING - Remote Deployment Script
# =============================================================================
# Deploy automatico dello script di hardening su edge nodes remoti
# For: Marco @ Syneto/Orizon
# =============================================================================

set -eo pipefail

# === CONFIGURAZIONE ===
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly HARDENING_SCRIPT="${SCRIPT_DIR}/orizon_edge_hardening.sh"

# Edge nodes configurati (formato: "user@ip:password")
declare -A EDGE_NODES
EDGE_NODES["edge-ubuntu"]="lorenz@10.211.55.21:profano.69"
# Aggiungere altri edge qui:
# EDGE_NODES["edge-name"]="user@ip:password"

# === COLORI OUTPUT ===
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly CYAN='\033[0;36m'
readonly BOLD='\033[1m'
readonly NC='\033[0m'

# === FUNZIONI DI LOGGING ===
log_info()    { echo -e "${BLUE}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}[✓]${NC} $*"; }
log_warning() { echo -e "${YELLOW}[!]${NC} $*"; }
log_error()   { echo -e "${RED}[✗]${NC} $*" >&2; }

print_banner() {
    echo -e "${CYAN}"
    echo "╔═══════════════════════════════════════════════════════════════════╗"
    echo "║      ORIZON DEPLOY HARDENING - Remote Deployment Tool             ║"
    echo "╚═══════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_usage() {
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Comandi:"
    echo "  --all                    Deploy su tutti gli edge configurati"
    echo "  --edge NAME              Deploy su edge specifico"
    echo "  --verify [NAME]          Verifica stato hardening"
    echo "  --list                   Lista edge configurati"
    echo "  --add NAME USER@IP:PWD   Aggiunge edge alla configurazione"
    echo "  --help                   Mostra questo messaggio"
    echo ""
    echo "Opzioni aggiuntive per deploy:"
    echo "  --node-id UUID           Specifica Node ID"
    echo "  --skip-nginx             Salta configurazione Nginx"
    echo "  --skip-fail2ban          Salta configurazione Fail2ban"
    echo ""
    echo "Esempi:"
    echo "  $0 --list"
    echo "  $0 --edge edge-ubuntu"
    echo "  $0 --edge edge-ubuntu --node-id abc123-def456"
    echo "  $0 --all"
    echo "  $0 --verify"
}

# === CHECK SSHPASS ===
check_sshpass() {
    if ! command -v sshpass &>/dev/null; then
        log_error "sshpass non installato"
        echo ""
        echo "Installa con:"
        echo "  macOS:  brew install hudochenkov/sshpass/sshpass"
        echo "  Ubuntu: sudo apt-get install sshpass"
        echo "  Fedora: sudo dnf install sshpass"
        exit 1
    fi
}

# === VERIFICA SCRIPT HARDENING ===
check_hardening_script() {
    if [[ ! -f "$HARDENING_SCRIPT" ]]; then
        log_error "Script hardening non trovato: $HARDENING_SCRIPT"
        exit 1
    fi
}

# === PARSE EDGE CONFIG ===
parse_edge_config() {
    local config="$1"
    # Formato: user@ip:password

    EDGE_USER=$(echo "$config" | cut -d@ -f1)
    EDGE_IP=$(echo "$config" | cut -d@ -f2 | cut -d: -f1)
    EDGE_PASSWORD=$(echo "$config" | cut -d: -f2)
}

# === TEST CONNESSIONE ===
test_connection() {
    local user="$1"
    local ip="$2"
    local password="$3"

    sshpass -p "$password" ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no \
        "$user@$ip" "echo OK" &>/dev/null
}

# === DEPLOY SU SINGOLO EDGE ===
deploy_to_edge() {
    local edge_name="$1"
    local extra_args="${2:-}"

    if [[ -z "${EDGE_NODES[$edge_name]:-}" ]]; then
        log_error "Edge '$edge_name' non trovato nella configurazione"
        echo ""
        echo "Edge disponibili:"
        for name in "${!EDGE_NODES[@]}"; do
            echo "  - $name"
        done
        return 1
    fi

    parse_edge_config "${EDGE_NODES[$edge_name]}"

    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}  DEPLOY: ${BOLD}$edge_name${NC} (${EDGE_USER}@${EDGE_IP})"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════════${NC}"
    echo ""

    # Step 1: Test connessione
    log_info "Test connessione SSH..."
    if ! test_connection "$EDGE_USER" "$EDGE_IP" "$EDGE_PASSWORD"; then
        log_error "Impossibile connettersi a $EDGE_USER@$EDGE_IP"
        return 1
    fi
    log_success "Connessione OK"

    # Step 2: Upload script
    log_info "Upload script hardening..."
    sshpass -p "$EDGE_PASSWORD" scp -o StrictHostKeyChecking=no \
        "$HARDENING_SCRIPT" "$EDGE_USER@$EDGE_IP:/tmp/orizon_edge_hardening.sh"
    log_success "Script uploadato"

    # Step 3: Esegui hardening
    log_info "Esecuzione hardening remoto..."
    echo ""

    # Determina NODE_ID
    local node_id_arg=""
    if [[ -n "${NODE_ID:-}" ]]; then
        node_id_arg="--node-id $NODE_ID"
    fi

    sshpass -p "$EDGE_PASSWORD" ssh -o StrictHostKeyChecking=no "$EDGE_USER@$EDGE_IP" \
        "echo '$EDGE_PASSWORD' | sudo -S bash /tmp/orizon_edge_hardening.sh $node_id_arg $extra_args"

    local exit_code=$?

    echo ""
    if [[ $exit_code -eq 0 ]]; then
        log_success "Deploy completato su $edge_name"
    else
        log_error "Deploy fallito su $edge_name (exit code: $exit_code)"
        return 1
    fi
}

# === DEPLOY SU TUTTI GLI EDGE ===
deploy_all() {
    local extra_args="${1:-}"
    local success=0
    local failed=0

    print_banner

    log_info "Deploy su ${#EDGE_NODES[@]} edge node(s)..."

    for edge_name in "${!EDGE_NODES[@]}"; do
        if deploy_to_edge "$edge_name" "$extra_args"; then
            ((success++))
        else
            ((failed++))
        fi
    done

    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}                        RIEPILOGO DEPLOY                           ${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "  ${GREEN}Successo:${NC} $success"
    echo -e "  ${RED}Falliti:${NC}  $failed"
    echo ""
}

# === VERIFICA STATO ===
verify_edge() {
    local edge_name="$1"

    if [[ -z "${EDGE_NODES[$edge_name]:-}" ]]; then
        log_error "Edge '$edge_name' non trovato"
        return 1
    fi

    parse_edge_config "${EDGE_NODES[$edge_name]}"

    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}  VERIFICA: ${BOLD}$edge_name${NC} (${EDGE_USER}@${EDGE_IP})"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════════${NC}"
    echo ""

    # Test connessione
    if ! test_connection "$EDGE_USER" "$EDGE_IP" "$EDGE_PASSWORD"; then
        log_error "Impossibile connettersi"
        return 1
    fi

    # Esegui verifica remota
    sshpass -p "$EDGE_PASSWORD" ssh -o StrictHostKeyChecking=no "$EDGE_USER@$EDGE_IP" \
        "orizon-hardening --status 2>/dev/null || echo 'Hardening non installato'"
}

# === VERIFICA TUTTI GLI EDGE ===
verify_all() {
    for edge_name in "${!EDGE_NODES[@]}"; do
        verify_edge "$edge_name"
    done
}

# === LISTA EDGE ===
list_edges() {
    echo ""
    echo -e "${CYAN}Edge Nodes Configurati:${NC}"
    echo ""

    for edge_name in "${!EDGE_NODES[@]}"; do
        parse_edge_config "${EDGE_NODES[$edge_name]}"
        echo -e "  ${BOLD}$edge_name${NC}"
        echo "    User: $EDGE_USER"
        echo "    IP:   $EDGE_IP"
        echo ""
    done

    echo "Totale: ${#EDGE_NODES[@]} edge(s)"
    echo ""
}

# === MAIN ===
main() {
    local command=""
    local edge_name=""
    local extra_args=""
    local NODE_ID=""

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --all)
                command="deploy_all"
                shift
                ;;
            --edge)
                command="deploy_edge"
                edge_name="$2"
                shift 2
                ;;
            --verify)
                command="verify"
                if [[ -n "${2:-}" && "${2:0:2}" != "--" ]]; then
                    edge_name="$2"
                    shift
                fi
                shift
                ;;
            --list)
                command="list"
                shift
                ;;
            --node-id)
                NODE_ID="$2"
                shift 2
                ;;
            --skip-nginx)
                extra_args="$extra_args --skip-nginx"
                shift
                ;;
            --skip-fail2ban)
                extra_args="$extra_args --skip-fail2ban"
                shift
                ;;
            --skip-firewall)
                extra_args="$extra_args --skip-firewall"
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

    # Verifica prerequisiti
    check_sshpass
    check_hardening_script

    # Esegui comando
    case "$command" in
        deploy_all)
            deploy_all "$extra_args"
            ;;
        deploy_edge)
            print_banner
            deploy_to_edge "$edge_name" "$extra_args"
            ;;
        verify)
            if [[ -n "$edge_name" ]]; then
                verify_edge "$edge_name"
            else
                verify_all
            fi
            ;;
        list)
            list_edges
            ;;
        *)
            print_usage
            exit 1
            ;;
    esac
}

main "$@"
