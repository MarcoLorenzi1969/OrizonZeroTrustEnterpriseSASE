# Orizon Zero Trust Connect - Scripts di Deployment

Questa directory contiene gli script automatizzati per il deployment e hardening di Orizon Zero Trust Connect.

## Contenuto della Directory

### Script Bash

1. **`hardening_server.sh`** (Hub Server Security)
   - Script completo di hardening enterprise per Hub servers
   - Configurazione UFW firewall con IP whitelisting
   - SSH hardening (chiavi ed25519, no root password)
   - Fail2ban multi-jail (sshd, aggressive, recidive, nginx)
   - Protezione database (PostgreSQL, Redis, MongoDB)
   - Fix console DigitalOcean
   - Status dashboard completo con tutte le interfacce e regole
   - Comandi: `install`, `firewall`, `ssh-harden`, `fail2ban`, `console-fix`, `ip-add`, `ip-del`, `status`, `audit`

2. **`orizon_hub_add_edge.sh`** (Lato Hub Server)
   - Registra nuovi nodi edge nel database
   - Genera chiavi SSH (ed25519) e token JWT
   - Configura servizi parametrizzabili (SSH, RDP, VNC)
   - Output verboso con colori per ogni step
   - Funzione `--show-config` per visualizzare la configurazione

3. **`orizon_edge_setup.sh`** (Lato Edge Client)
   - Rileva automaticamente il sistema operativo (Debian/Ubuntu/Kali, Fedora/RHEL, Arch/Manjaro)
   - Installa i servizi richiesti (SSH, RDP, VNC)
   - Configura l'agent Orizon e il servizio systemd
   - Output verboso step-by-step
   - Funzione `--show-config` per visualizzare tunnel locali

4. **`orizon_edge_setup_complete.sh`** (Setup Completo Edge)
   - Versione estesa di orizon_edge_setup.sh
   - Include configurazione completa con tutti i parametri
   - Supporto multi-hub

## Quick Start

### Hardening Hub Server (RACCOMANDATO)

Prima installazione completa:

```bash
sudo ./hardening_server.sh install
```

Solo firewall con IP whitelist:

```bash
sudo ./hardening_server.sh firewall
```

Visualizza stato sicurezza:

```bash
sudo ./hardening_server.sh status
```

Aggiungere IP alla whitelist SSH:

```bash
sudo ./hardening_server.sh ip-add 203.0.113.50
```

### Lato Hub (Orizon Server)

Aggiungere un nuovo edge node con servizi SSH + RDP + VNC:

```bash
./orizon_hub_add_edge.sh \
  --name KaliEdge \
  --ip 10.211.55.19 \
  --services ssh,rdp,vnc
```

Visualizzare configurazione di un nodo esistente:

```bash
./orizon_hub_add_edge.sh --show-config KaliEdge
```

### Lato Edge (Nodo Client)

Setup automatico con rilevamento OS:

```bash
./orizon_edge_setup.sh \
  --name KaliEdge \
  --hub-ip 139.59.149.48 \
  --token <JWT_TOKEN_FROM_HUB> \
  --services ssh,rdp,vnc \
  --ssh-pubkey "<PUBLIC_KEY_FROM_HUB>"
```

Visualizzare configurazione locale:

```bash
./orizon_edge_setup.sh --show-config
```

## Caratteristiche Principali

- **Hardening Enterprise** - Firewall, Fail2ban, SSH hardening completo
- **Parametrizzazione completa** - Servizi SSH/RDP/VNC configurabili
- **Multi-distribuzione** - Supporto Debian, RedHat, Arch families
- **Multi-Hub** - Supporto per Hub1 (139.59.149.48) e Hub2 (68.183.219.222)
- **Output verboso** - Step-by-step con codice colore
- **Gestione chiavi SSH** - Generazione automatica ed25519
- **Autenticazione JWT** - Token con validità 365 giorni
- **Integrazione systemd** - Avvio automatico dell'agent
- **Show configuration** - Visualizza tunnel e endpoint WebSocket

## Sistemi Operativi Supportati

### Famiglia Debian
- Ubuntu 20.04, 22.04, 24.04
- Debian 11, 12
- Kali Linux
- Linux Mint
- Pop!_OS
- Parrot OS

### Famiglia RedHat
- Fedora 38, 39, 40
- RHEL 8, 9
- CentOS Stream
- Rocky Linux
- AlmaLinux

### Famiglia Arch
- Arch Linux
- Manjaro

## Servizi Configurabili

- **SSH** - OpenSSH Server (porta 22)
- **RDP** - xrdp (porta 3389)
- **VNC** - TigerVNC Server (porta 5901)

## Architettura Zero Trust

Gli script implementano il pattern **Zero Trust Network Access (ZTNA)**:

```
┌─────────────────┐                    ┌─────────────────┐
│   EDGE NODE     │                    │   ORIZON HUB    │
│                 │  SSH Reverse       │                 │
│  SSH/RDP/VNC    │◄──────────────────►│  Backend API    │
│  (localhost)    │   Tunnel autossh   │  PostgreSQL DB  │
└─────────────────┘                    └─────────────────┘
```

- Nessuna porta pubblica esposta sugli edge
- Tunnel SSH reverse con autossh (keep-alive)
- Autenticazione JWT per ogni sessione
- Firewall con IP whitelisting sugli Hub

## Requisiti

### Hub Server
- Ubuntu 22.04/24.04 o Debian 12
- PostgreSQL installato e configurato
- Backend Orizon in esecuzione (Docker)
- UFW firewall
- Privilegi root per hardening

### Edge Node
- Python 3.8+
- Bash 4.0+
- autossh installato
- Connessione internet verso il Hub
- Privilegi sudo/root per l'installazione

## Note di Sicurezza

- Le chiavi SSH sono generate con algoritmo **ed25519**
- I token JWT hanno validità di **365 giorni**
- SSH limitato solo a IP autorizzati (whitelist UFW)
- Database protetti con regole UFW DENY
- Fail2ban con ban progressivo (10min → 1h → 1 settimana)
- Controllo accessi console DigitalOcean con password root

## Script Obsoleti

Gli script precedenti di hardening sono stati archiviati in `backup_code/obsolete_scripts_2025-12-03/`:
- `orizon_deploy_hardening.sh` - Sostituito da hardening_server.sh
- `orizon_edge_hardening.sh` - Sostituito da hardening_server.sh
- `manual_tunnel.sh` - Non più necessario

---

**Orizon Zero Trust Connect v2.1.1**
Updated: 2025-12-03
