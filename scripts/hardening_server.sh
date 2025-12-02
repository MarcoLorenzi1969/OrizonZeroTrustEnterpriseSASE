#!/usr/bin/env bash
# ============================================================================
# HARDENING SERVER v3.0 - Enterprise Security Edition
# Orizon Zero Trust Connect - Security Hardening Script
# ============================================================================
# Changelog v3:
# - Fix status: mostra TUTTE le interfacce di rete
# - Fix status: mostra TUTTE le regole firewall
# - Fix status: corretto indicatore PermitRootLogin
# - Fix: accesso console DigitalOcean garantito
# - Fix: protezione database via UFW (non iptables)
# ============================================================================

set -e

##############################
#       COLORI ANSI
##############################
RED="\e[31m"
GREEN="\e[32m"
YELLOW="\e[33m"
BLUE="\e[34m"
CYAN="\e[36m"
MAGENTA="\e[35m"
BOLD="\e[1m"
RESET="\e[0m"

##############################
#       CONFIGURAZIONE
##############################
ALLOWED_SSH_IPS=("2.42.92.51" "95.230.154.144")

# Porte Orizon
ORIZON_WEB_PORT=80
ORIZON_SSL_PORT=443
ORIZON_TUNNEL_PORT=2222
ORIZON_TUNNEL_RANGE_START=23000
ORIZON_TUNNEL_RANGE_END=24000

# Paths
JAIL_LOCAL="/etc/fail2ban/jail.local"
JAIL_D="/etc/fail2ban/jail.d"
DEFAULT_WHITELIST_FILE="/etc/fail2ban/whitelist_default"
SSHD_CONFIG="/etc/ssh/sshd_config"

# Base whitelist per fail2ban
BASE_WHITELIST="127.0.0.0/8 ::1 172.16.0.0/12 10.0.0.0/8 192.168.0.0/16"
PROTECTED_ENTRIES=("127.0.0.0/8" "::1")

##############################
#       FUNZIONI UTILITY
##############################

log_info()    { echo -e "${CYAN}[INFO]${RESET} $1"; }
log_success() { echo -e "${GREEN}[OK]${RESET} $1"; }
log_warn()    { echo -e "${YELLOW}[WARN]${RESET} $1"; }
log_error()   { echo -e "${RED}[ERROR]${RESET} $1"; }
log_section() { echo -e "\n${BLUE}${BOLD}═══ $1 ═══${RESET}\n"; }

require_root() {
  if [[ $EUID -ne 0 ]]; then
    log_error "Devi eseguire questo script come root"
    exit 1
  fi
}

backup_file() {
  local file="$1"
  if [[ -f "$file" ]]; then
    cp "$file" "${file}.backup-$(date +%Y%m%d-%H%M%S)"
  fi
}

get_whitelist() {
  cat "$DEFAULT_WHITELIST_FILE" 2>/dev/null | xargs
}

##############################
#       USAGE
##############################

usage() {
  echo -e "${CYAN}${BOLD}"
  echo "╔═══════════════════════════════════════════════════════════════╗"
  echo "║     HARDENING SERVER v3.0 - Enterprise Security Edition       ║"
  echo "║              Orizon Zero Trust Connect                        ║"
  echo "╚═══════════════════════════════════════════════════════════════╝"
  echo -e "${RESET}"
  echo
  echo -e "${GREEN}Comandi disponibili:${RESET}"
  echo
  echo -e "  ${BOLD}install${RESET}          Installazione completa hardening"
  echo -e "  ${BOLD}firewall${RESET}         Configura UFW con regole restrittive"
  echo -e "  ${BOLD}ssh-harden${RESET}       Hardening SSH"
  echo -e "  ${BOLD}fail2ban${RESET}         Configura fail2ban multi-jail"
  echo -e "  ${BOLD}console-fix${RESET}      Abilita accesso console DigitalOcean"
  echo -e "  ${BOLD}ip-add <IP>${RESET}      Aggiunge IP alla whitelist SSH"
  echo -e "  ${BOLD}ip-del <IP>${RESET}      Rimuove IP dalla whitelist SSH"
  echo -e "  ${BOLD}status${RESET}           Mostra stato sicurezza completo"
  echo -e "  ${BOLD}audit${RESET}            Analisi vulnerabilità"
  echo
}

##############################
#    INSTALL PACKAGES
##############################

install_packages() {
  log_section "INSTALLAZIONE PACCHETTI"

  if command -v apt >/dev/null 2>&1; then
    apt update -qq
    apt install -y fail2ban ufw curl 2>/dev/null
    log_success "Pacchetti installati"
  else
    log_error "Package manager non supportato"
    exit 1
  fi
}

##############################
#    UFW FIREWALL
##############################

configure_firewall() {
  log_section "CONFIGURAZIONE FIREWALL UFW"

  # Reset UFW
  log_info "Reset regole UFW..."
  ufw --force reset >/dev/null 2>&1

  # Default policies
  ufw default deny incoming
  ufw default allow outgoing

  log_info "Politiche default: DENY incoming, ALLOW outgoing"

  # SSH solo da IP autorizzati
  log_info "Configurazione SSH restrittivo..."
  for ip in "${ALLOWED_SSH_IPS[@]}"; do
    ufw allow from "$ip" to any port 22 proto tcp comment "SSH from $ip"
    log_success "SSH permesso da: $ip"
  done

  # Porte Orizon pubbliche
  log_info "Apertura porte Orizon..."
  ufw allow ${ORIZON_WEB_PORT}/tcp comment "HTTP"
  ufw allow ${ORIZON_SSL_PORT}/tcp comment "HTTPS"
  ufw allow ${ORIZON_TUNNEL_PORT}/tcp comment "Orizon SSH Tunnel"
  ufw allow ${ORIZON_TUNNEL_RANGE_START}:${ORIZON_TUNNEL_RANGE_END}/tcp comment "Orizon Tunnels"

  # Traffico Docker interno (NON database pubblici)
  ufw allow from 172.16.0.0/12 comment "Docker networks"
  ufw allow from 10.0.0.0/8 comment "Internal/VPC networks"

  # BLOCCA esplicitamente database da esterno
  log_info "Blocco database da accesso esterno..."
  ufw deny 5432/tcp comment "Block PostgreSQL"
  ufw deny 6379/tcp comment "Block Redis"
  ufw deny 27017/tcp comment "Block MongoDB"
  ufw deny 3001/tcp comment "Block Script Generator"

  # Abilita UFW
  ufw --force enable

  log_success "Firewall UFW configurato"
}

##############################
#    SSH HARDENING
##############################

configure_ssh_hardening() {
  log_section "HARDENING SSH"

  backup_file "$SSHD_CONFIG"

  # Rimuovi override cloud
  for f in /etc/ssh/sshd_config.d/*.conf; do
    [[ -f "$f" ]] && mv "$f" "${f}.disabled" 2>/dev/null
  done

  # Pulisci config esistente
  sed -i '/^PermitRootLogin/d' "$SSHD_CONFIG"
  sed -i '/^MaxAuthTries/d' "$SSHD_CONFIG"
  sed -i '/^MaxSessions/d' "$SSHD_CONFIG"
  sed -i '/^ClientAliveInterval/d' "$SSHD_CONFIG"
  sed -i '/^ClientAliveCountMax/d' "$SSHD_CONFIG"
  sed -i '/^X11Forwarding/d' "$SSHD_CONFIG"
  sed -i '/^LogLevel/d' "$SSHD_CONFIG"
  sed -i '/^Banner/d' "$SSHD_CONFIG"
  sed -i '/# === HARDENING/d' "$SSHD_CONFIG"

  # Aggiungi hardening
  cat >> "$SSHD_CONFIG" << 'EOF'

# === HARDENING ORIZON v3 ===
# Root: solo chiave SSH (console DO usa TTY, non SSH)
PermitRootLogin prohibit-password
MaxAuthTries 3
MaxSessions 5
ClientAliveInterval 300
ClientAliveCountMax 2
X11Forwarding no
LogLevel VERBOSE
Banner /etc/ssh/banner
EOF

  # Banner
  cat > /etc/ssh/banner << 'EOF'
╔═══════════════════════════════════════════════════════════════╗
║                    ORIZON ZERO TRUST HUB                      ║
║  Accesso riservato - All activity is logged and monitored    ║
╚═══════════════════════════════════════════════════════════════╝
EOF

  # Reload SSH
  sshd -t && systemctl reload sshd
  log_success "SSH hardening applicato"
}

##############################
#    CONSOLE DIGITALOCEAN
##############################

fix_console_access() {
  log_section "FIX CONSOLE DIGITALOCEAN"

  # 1. Verifica/imposta password root
  if passwd -S root 2>/dev/null | grep -qE " L | NP "; then
    log_warn "Root non ha password - la console DO potrebbe non funzionare"
    log_info "Per impostare password root: sudo passwd root"
  else
    log_success "Root ha password impostata"
  fi

  # 2. Abilita getty su ttyS0
  systemctl enable serial-getty@ttyS0.service 2>/dev/null || true
  systemctl start serial-getty@ttyS0.service 2>/dev/null || true
  log_success "Serial getty abilitato"

  # 3. Rimuovi securetty se blocca
  if [[ -f /etc/securetty ]]; then
    if ! grep -q "^ttyS0" /etc/securetty; then
      echo "ttyS0" >> /etc/securetty
      echo "tty1" >> /etc/securetty
      log_success "ttyS0 aggiunto a securetty"
    fi
  fi

  # 4. Verifica PAM
  if grep -q "pam_securetty.so" /etc/pam.d/login 2>/dev/null; then
    sed -i 's/^auth.*pam_securetty.so/#&/' /etc/pam.d/login
    log_info "pam_securetty disabilitato"
  fi

  log_success "Console DO configurata"
  echo
  echo -e "${YELLOW}NOTA: Se ancora non funziona, imposta password root:${RESET}"
  echo -e "  sudo passwd root"
}

##############################
#    FAIL2BAN
##############################

configure_fail2ban() {
  log_section "CONFIGURAZIONE FAIL2BAN"

  # Disabilita override
  mkdir -p "$JAIL_D"
  for f in "$JAIL_D"/*.conf; do
    [[ -f "$f" ]] && mv "$f" "${f}.disabled" 2>/dev/null
  done

  # Whitelist
  local wl="$BASE_WHITELIST"
  for ip in "${ALLOWED_SSH_IPS[@]}"; do
    wl="$wl $ip"
  done
  echo "$wl" > "$DEFAULT_WHITELIST_FILE"
  chmod 600 "$DEFAULT_WHITELIST_FILE"

  backup_file "$JAIL_LOCAL"

  cat > "$JAIL_LOCAL" << EOF
# Fail2Ban v3 - Orizon Zero Trust

[DEFAULT]
ignoreip = $wl
bantime  = 1h
findtime = 10m
maxretry = 5
backend  = systemd

[sshd]
enabled  = true
port     = ssh
maxretry = 3
bantime  = 2h

[sshd-aggressive]
enabled  = true
port     = ssh
filter   = sshd[mode=aggressive]
logpath  = /var/log/auth.log
maxretry = 2
bantime  = 24h
findtime = 1h

[recidive]
enabled  = true
logpath  = /var/log/fail2ban.log
banaction = iptables-allports
bantime  = 1w
findtime = 1d
maxretry = 3

[nginx-http-auth]
enabled  = true
port     = http,https
filter   = nginx-http-auth
logpath  = /var/log/nginx/error.log
maxretry = 5

[nginx-limit-req]
enabled  = true
port     = http,https
filter   = nginx-limit-req
logpath  = /var/log/nginx/error.log
maxretry = 10
bantime  = 30m
EOF

  systemctl enable --now fail2ban
  systemctl restart fail2ban
  log_success "Fail2ban configurato"
}

##############################
#    IP MANAGEMENT
##############################

ip_add() {
  require_root
  local ip="$1"
  [[ -z "$ip" ]] && { log_error "Specifica un IP"; exit 1; }

  ufw allow from "$ip" to any port 22 proto tcp comment "SSH from $ip"

  local wl="$(get_whitelist) $ip"
  echo "$wl" > "$DEFAULT_WHITELIST_FILE"
  sed -i "s|^ignoreip = .*|ignoreip = $wl|" "$JAIL_LOCAL"
  systemctl reload fail2ban 2>/dev/null || true

  log_success "IP $ip aggiunto"
}

ip_del() {
  require_root
  local ip="$1"
  [[ -z "$ip" ]] && { log_error "Specifica un IP"; exit 1; }

  ufw delete allow from "$ip" to any port 22 proto tcp 2>/dev/null || true

  local wl=$(get_whitelist | tr ' ' '\n' | grep -v "^${ip}$" | xargs)
  echo "$wl" > "$DEFAULT_WHITELIST_FILE"
  sed -i "s|^ignoreip = .*|ignoreip = $wl|" "$JAIL_LOCAL"
  systemctl reload fail2ban 2>/dev/null || true

  log_success "IP $ip rimosso"
}

##############################
#    STATUS v3 - COMPLETO
##############################

status_mode() {
  echo -e "${CYAN}${BOLD}"
  echo "╔═══════════════════════════════════════════════════════════════╗"
  echo "║       SECURITY STATUS v3 - ORIZON ZERO TRUST HUB              ║"
  echo "╚═══════════════════════════════════════════════════════════════╝"
  echo -e "${RESET}"

  # ===== NETWORK INFO =====
  echo -e "${BLUE}${BOLD}📌 INTERFACCE DI RETE${RESET}"
  echo
  # Mostra tutte le interfacce con IP
  ip -4 addr show 2>/dev/null | grep -E "^[0-9]+:|inet " | while read line; do
    if echo "$line" | grep -q "^[0-9]"; then
      iface=$(echo "$line" | awk -F: '{print $2}' | awk '{print $1}')
      echo -e "  ${CYAN}${BOLD}$iface${RESET}"
    else
      ip_addr=$(echo "$line" | awk '{print $2}')
      echo -e "    └─ ${GREEN}$ip_addr${RESET}"
    fi
  done
  echo

  # IP Pubblico
  local pub_ip=$(curl -s --max-time 3 https://ipv4.icanhazip.com 2>/dev/null || echo "N/A")
  echo -e "  ${CYAN}IP Pubblico:${RESET} ${GREEN}${BOLD}$pub_ip${RESET}"
  echo

  # ===== FIREWALL UFW =====
  echo -e "${BLUE}${BOLD}🔥 FIREWALL UFW - TUTTE LE REGOLE${RESET}"
  echo
  if ufw status | grep -q "Status: active"; then
    echo -e "  ${GREEN}● ATTIVO${RESET}"
    echo
    ufw status numbered 2>/dev/null | grep -E "^\[" | while read line; do
      echo -e "  $line"
    done
  else
    echo -e "  ${RED}● DISATTIVO${RESET}"
  fi
  echo

  # ===== SSH CONFIG =====
  echo -e "${BLUE}${BOLD}🔐 SSH CONFIGURATION${RESET}"
  echo
  local pa=$(sshd -T 2>/dev/null | grep -i "^passwordauthentication" | awk '{print $2}')
  local prl=$(sshd -T 2>/dev/null | grep -i "^permitrootlogin" | awk '{print $2}')
  local mat=$(sshd -T 2>/dev/null | grep -i "^maxauthtries" | awk '{print $2}')
  local x11=$(sshd -T 2>/dev/null | grep -i "^x11forwarding" | awk '{print $2}')

  # PasswordAuth: yes è OK se SSH è ristretto via firewall
  if [[ "$pa" == "no" ]]; then
    printf "  ${CYAN}%-22s${RESET} ${GREEN}%-20s${RESET} %s\n" "PasswordAuth:" "$pa" "✓ Disabilitata"
  else
    printf "  ${CYAN}%-22s${RESET} ${YELLOW}%-20s${RESET} %s\n" "PasswordAuth:" "${pa:-yes}" "(protetta da firewall)"
  fi

  # PermitRootLogin: prohibit-password/without-password è SICURO
  if [[ "$prl" == "no" ]]; then
    printf "  ${CYAN}%-22s${RESET} ${GREEN}%-20s${RESET} %s\n" "PermitRootLogin:" "$prl" "✓ Completamente disabilitato"
  elif [[ "$prl" == "prohibit-password" || "$prl" == "without-password" ]]; then
    printf "  ${CYAN}%-22s${RESET} ${GREEN}%-20s${RESET} %s\n" "PermitRootLogin:" "$prl" "✓ Solo chiave SSH"
  else
    printf "  ${CYAN}%-22s${RESET} ${RED}%-20s${RESET} %s\n" "PermitRootLogin:" "${prl:-yes}" "✗ INSICURO"
  fi

  printf "  ${CYAN}%-22s${RESET} ${GREEN}%-20s${RESET}\n" "MaxAuthTries:" "${mat:-6}"
  printf "  ${CYAN}%-22s${RESET} ${GREEN}%-20s${RESET}\n" "X11Forwarding:" "${x11:-yes}"
  echo

  # ===== CONSOLE DO =====
  echo -e "${BLUE}${BOLD}🖥️ CONSOLE DIGITALOCEAN${RESET}"
  echo
  local root_status=$(passwd -S root 2>/dev/null | awk '{print $2}')
  local getty_status=$(systemctl is-active serial-getty@ttyS0.service 2>/dev/null || echo "inactive")

  if [[ "$root_status" == "P" ]]; then
    printf "  ${CYAN}%-22s${RESET} ${GREEN}%-20s${RESET} %s\n" "Password Root:" "Impostata" "✓"
  else
    printf "  ${CYAN}%-22s${RESET} ${RED}%-20s${RESET} %s\n" "Password Root:" "Non impostata" "✗ Esegui: sudo passwd root"
  fi

  if [[ "$getty_status" == "active" ]]; then
    printf "  ${CYAN}%-22s${RESET} ${GREEN}%-20s${RESET} %s\n" "Serial Getty:" "Attivo" "✓"
  else
    printf "  ${CYAN}%-22s${RESET} ${RED}%-20s${RESET} %s\n" "Serial Getty:" "Inattivo" "✗ Esegui: console-fix"
  fi
  echo

  # ===== FAIL2BAN =====
  echo -e "${BLUE}${BOLD}🛡️ FAIL2BAN${RESET}"
  echo
  if systemctl is-active --quiet fail2ban; then
    echo -e "  ${GREEN}● ATTIVO${RESET}"
    echo
    echo -e "  ${CYAN}Jail:${RESET}"
    fail2ban-client status 2>/dev/null | grep "Jail list" | sed 's/.*://' | tr ',' '\n' | sed 's/^[[:space:]]*/    - /'
    echo
    echo -e "  ${CYAN}IP Bannati:${RESET}"
    local total_banned=0
    for jail in sshd sshd-aggressive recidive; do
      local count=$(fail2ban-client status "$jail" 2>/dev/null | grep "Currently banned" | awk '{print $4}')
      [[ -n "$count" && "$count" != "0" ]] && {
        echo -e "    [$jail]: $count"
        ((total_banned += count))
      }
    done
    [[ $total_banned -eq 0 ]] && echo "    (nessuno)"
  else
    echo -e "  ${RED}● DISATTIVO${RESET}"
  fi
  echo

  # ===== WHITELIST =====
  echo -e "${BLUE}${BOLD}📋 WHITELIST SSH/FAIL2BAN${RESET}"
  echo
  if [[ -f "$DEFAULT_WHITELIST_FILE" ]]; then
    cat "$DEFAULT_WHITELIST_FILE" | tr ' ' '\n' | grep -v '^$' | while read ip; do
      echo -e "  - ${GREEN}$ip${RESET}"
    done
  fi
  echo

  # ===== PORTE =====
  echo -e "${BLUE}${BOLD}🔌 PORTE IN ASCOLTO${RESET}"
  echo
  printf "  ${CYAN}%-8s %-20s %-15s${RESET}\n" "PORTA" "SERVIZIO" "STATO"
  printf "  ${CYAN}%-8s %-20s %-15s${RESET}\n" "-----" "--------" "-----"

  ss -tlnp 2>/dev/null | grep -E "0\.0\.0\.0:|:::" | \
    awk '{print $4}' | sed 's/.*://' | sort -n | uniq | \
    while read port; do
      local svc="" status="${GREEN}OK${RESET}"
      case $port in
        22) svc="SSH" ;;
        80) svc="HTTP" ;;
        443) svc="HTTPS" ;;
        2222) svc="Orizon Tunnel" ;;
        5432) svc="PostgreSQL"; status="${YELLOW}Interno${RESET}" ;;
        6379) svc="Redis"; status="${YELLOW}Interno${RESET}" ;;
        27017) svc="MongoDB"; status="${YELLOW}Interno${RESET}" ;;
        8000) svc="Backend API" ;;
        3001) svc="Script Generator"; status="${YELLOW}Interno${RESET}" ;;
        9128|9129) svc="Socat Bridge" ;;
        23*) svc="Tunnel Range" ;;
        *) svc="-" ;;
      esac
      printf "  %-8s %-20s %b\n" "$port" "$svc" "$status"
    done
  echo

  # ===== DOCKER =====
  echo -e "${BLUE}${BOLD}🐳 CONTAINER DOCKER${RESET}"
  echo
  docker ps --format "  {{.Names}}: {{.Status}}" 2>/dev/null || echo "  Docker non disponibile"
  echo
}

##############################
#    AUDIT
##############################

audit_mode() {
  log_section "SECURITY AUDIT"

  local issues=0

  # UFW
  if ! ufw status | grep -q "Status: active"; then
    echo -e "${RED}[CRITICO]${RESET} Firewall UFW non attivo"
    ((issues++))
  else
    echo -e "${GREEN}[OK]${RESET} Firewall UFW attivo"
  fi

  # SSH aperto a tutti?
  if ufw status | grep -E "22/tcp.*ALLOW.*Anywhere" | grep -qv "from"; then
    echo -e "${RED}[CRITICO]${RESET} SSH aperto a tutti gli IP"
    ((issues++))
  else
    echo -e "${GREEN}[OK]${RESET} SSH ristretto a IP specifici"
  fi

  # Root login
  local prl=$(sshd -T 2>/dev/null | grep -i "^permitrootlogin" | awk '{print $2}')
  if [[ "$prl" == "yes" ]]; then
    echo -e "${RED}[CRITICO]${RESET} SSH Root Login completamente abilitato"
    ((issues++))
  else
    echo -e "${GREEN}[OK]${RESET} SSH Root Login ristretto ($prl)"
  fi

  # Fail2ban
  if ! systemctl is-active --quiet fail2ban; then
    echo -e "${YELLOW}[WARN]${RESET} Fail2ban non attivo"
    ((issues++))
  else
    echo -e "${GREEN}[OK]${RESET} Fail2ban attivo"
  fi

  # Database in UFW deny?
  for port in 5432 6379 27017; do
    if ufw status | grep -q "DENY.*$port"; then
      echo -e "${GREEN}[OK]${RESET} Porta $port bloccata in UFW"
    elif ufw status | grep -q "ALLOW.*$port"; then
      echo -e "${RED}[CRITICO]${RESET} Porta database $port aperta in UFW"
      ((issues++))
    fi
  done

  # Console DO
  if passwd -S root 2>/dev/null | grep -qE " L | NP "; then
    echo -e "${YELLOW}[WARN]${RESET} Root senza password - Console DO non funzionerà"
    ((issues++))
  else
    echo -e "${GREEN}[OK]${RESET} Console DO accessibile"
  fi

  echo
  if [[ $issues -eq 0 ]]; then
    echo -e "${GREEN}${BOLD}✓ Sistema sicuro${RESET}"
  else
    echo -e "${RED}${BOLD}✗ Trovate $issues vulnerabilità${RESET}"
  fi
}

##############################
#    INSTALL COMPLETO
##############################

install_mode() {
  require_root

  echo -e "${CYAN}${BOLD}"
  echo "╔═══════════════════════════════════════════════════════════════╗"
  echo "║     INSTALLAZIONE HARDENING v3 - ORIZON ZERO TRUST            ║"
  echo "╚═══════════════════════════════════════════════════════════════╝"
  echo -e "${RESET}"

  install_packages
  configure_firewall
  configure_ssh_hardening
  configure_fail2ban
  fix_console_access

  log_section "COMPLETATO"

  echo -e "${GREEN}${BOLD}✓ Hardening v3 completato!${RESET}"
  echo
  echo -e "${YELLOW}IP autorizzati SSH:${RESET}"
  for ip in "${ALLOWED_SSH_IPS[@]}"; do
    echo "  - $ip"
  done
  echo
  echo -e "${YELLOW}Esegui 'status' per verificare${RESET}"
}

##############################
#        MAIN
##############################

case "${1:-}" in
  install)       install_mode ;;
  firewall)      require_root; configure_firewall ;;
  ssh-harden)    require_root; configure_ssh_hardening ;;
  fail2ban)      require_root; configure_fail2ban ;;
  console-fix)   require_root; fix_console_access ;;
  ip-add)        require_root; ip_add "$2" ;;
  ip-del)        require_root; ip_del "$2" ;;
  status)        status_mode ;;
  audit)         audit_mode ;;
  *)             usage ;;
esac
