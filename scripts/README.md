# Orizon Zero Trust Connect - Scripts di Deployment

Questa directory contiene gli script automatizzati per il deployment di nodi edge nel sistema Orizon Zero Trust Connect.

## Contenuto della Directory

### 📜 Script Bash

1. **`orizon_hub_add_edge.sh`** (Lato Hub Server)
   - Registra nuovi nodi edge nel database
   - Genera chiavi SSH (ed25519) e token JWT
   - Configura servizi parametrizzabili (SSH, RDP, VNC)
   - Output verboso con colori per ogni step
   - Funzione `--show-config` per visualizzare la configurazione

2. **`orizon_edge_setup.sh`** (Lato Edge Client)
   - Rileva automaticamente il sistema operativo (Debian/Ubuntu/Kali, Fedora/RHEL, Arch/Manjaro)
   - Installa i servizi richiesti (SSH, RDP, VNC)
   - Configura l'agent Orizon e il servizio systemd
   - Output verboso step-by-step
   - Funzione `--show-config` per visualizzare tunnel locali

### 📚 Documentazione

3. **`ORIZON_SCRIPTS_GUIDE.md`**
   - Guida completa all'utilizzo degli script (Italiano/Inglese)
   - Sintassi e parametri dettagliati
   - Esempi pratici per Kali, Ubuntu, Fedora
   - Diagrammi architetturali
   - Sezione troubleshooting
   - Comandi utili per il debugging

## Quick Start

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
  --hub-ip 46.101.189.126 \
  --token <JWT_TOKEN_FROM_HUB> \
  --services ssh,rdp,vnc \
  --ssh-pubkey "<PUBLIC_KEY_FROM_HUB>"
```

Visualizzare configurazione locale:

```bash
./orizon_edge_setup.sh --show-config
```

## Caratteristiche Principali

✅ **Parametrizzazione completa** - Servizi SSH/RDP/VNC configurabili
✅ **Multi-distribuzione** - Supporto Debian, RedHat, Arch families
✅ **Output verboso** - Step-by-step con codice colore
✅ **Gestione chiavi SSH** - Generazione automatica ed25519
✅ **Autenticazione JWT** - Token con validità 365 giorni
✅ **Integrazione systemd** - Avvio automatico dell'agent
✅ **Show configuration** - Visualizza tunnel e endpoint WebSocket

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
│                 │  WebSocket HTTPS   │                 │
│  SSH/RDP/VNC    │◄──────────────────►│  Backend API    │
│  (localhost)    │   wss://hub/ws    │  PostgreSQL DB  │
└─────────────────┘                    └─────────────────┘
```

- Nessuna porta pubblica esposta sugli edge
- Connessioni WebSocket sicure tramite HTTPS
- Autenticazione JWT per ogni sessione
- Tunnel reversi dal hub agli edge

## Requisiti

### Hub Server
- PostgreSQL installato e configurato
- Backend Orizon in esecuzione
- Python 3.8+
- Bash 4.0+

### Edge Node
- Python 3.8+
- Bash 4.0+
- Connessione internet verso il Hub
- Privilegi sudo/root per l'installazione

## Documentazione Completa

Per la guida completa con tutti gli esempi, troubleshooting e comandi avanzati:

```bash
cat ORIZON_SCRIPTS_GUIDE.md
```

## Note di Sicurezza

- Le chiavi SSH sono generate con algoritmo **ed25519**
- I token JWT hanno validità di **365 giorni**
- Le connessioni usano **WebSocket sicuri (wss://)**
- L'agent Orizon gira come servizio systemd con restart automatico
- Supporto chiavi SSH pubbliche per autenticazione passwordless

## Supporto e Troubleshooting

Per problemi comuni, consultare la sezione **Troubleshooting** in `ORIZON_SCRIPTS_GUIDE.md`.

---

**Orizon Zero Trust Connect v1.1**
Generated: 2025-11-11
