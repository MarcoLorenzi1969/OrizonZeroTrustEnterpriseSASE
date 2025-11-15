# 📘 Guida Script Orizon Hub & Edge

Questa guida descrive come utilizzare gli script di configurazione per aggiungere nodi edge alla piattaforma Orizon Zero Trust Connect.

## 📋 Indice

1. [Panoramica](#panoramica)
2. [Script Hub](#script-hub-orizon_hub_add_edgesh)
3. [Script Edge](#script-edge-orizon_edge_setupsh)
4. [Esempi Pratici](#esempi-pratici)
5. [Risoluzione Problemi](#risoluzione-problemi)

---

## 🔍 Panoramica

Il sistema Orizon utilizza due script complementari:

### **Script Hub** (`orizon_hub_add_edge.sh`)
Eseguito sul server **Orizon Hub** (46.101.189.126)
- Genera chiavi SSH
- Registra il nodo nel database
- Crea configurazione e token JWT
- Mostra gli endpoint WebSocket

### **Script Edge** (`orizon_edge_setup.sh`)
Eseguito sul nodo **Edge** (client remoto)
- Rileva il sistema operativo automaticamente
- Installa servizi richiesti (SSH/RDP/VNC)
- Configura e avvia l'agent
- Mostra i tunnel locali

---

## 🖥️ Script Hub: `orizon_hub_add_edge.sh`

### Sintassi

```bash
# Aggiungere un nuovo edge node
sudo ./orizon_hub_add_edge.sh --name NOME --ip IP --services ssh,rdp,vnc

# Visualizzare configurazione
sudo ./orizon_hub_add_edge.sh --show-config [NODE_NAME]
```

### Parametri

| Parametro | Descrizione | Esempio |
|-----------|-------------|---------|
| `--name` | Nome del nodo edge | `kali-edge` |
| `--ip` | Indirizzo IP del nodo | `10.211.55.19` |
| `--services` | Servizi da abilitare (separati da virgola) | `ssh,rdp,vnc` |
| `--show-config` | Mostra configurazione tunnel | Opzionale: nome nodo |
| `--help` | Mostra messaggio di aiuto | - |

### Servizi Supportati

- **ssh** - Terminale SSH remoto (porta 22)
- **rdp** - Desktop remoto RDP (porta 3389)
- **vnc** - Desktop remoto VNC (porta 5900)

### Output Script Hub

Lo script esegue questi step:

1. ✅ **Verifica Prerequisiti** - PostgreSQL, Backend Orizon
2. ✅ **Generazione UUID** - Identificativo univoco per il nodo
3. ✅ **Chiavi SSH** - Coppia ed25519 (419 bytes)
4. ✅ **Registrazione DB** - Inserimento in tabella `nodes`
5. ✅ **Token JWT** - Generazione token con validità 365 giorni
6. ✅ **Config Servizi** - Configurazione SSH/RDP/VNC
7. ✅ **Script Setup** - Creazione script per l'edge
8. ✅ **Riepilogo** - Informazioni complete e comandi per il deploy

### File Generati (Hub)

```
/root/orizon-ztc/backend/ssh_keys/
├── {nome_nodo}_key           # Chiave privata SSH
└── {nome_nodo}_key.pub       # Chiave pubblica SSH

/tmp/
└── setup_{nome_nodo}.sh      # Script da copiare sull'edge
```

---

## 💻 Script Edge: `orizon_edge_setup.sh`

### Sintassi

```bash
# Configurare un edge node
sudo ./orizon_edge_setup.sh --name NOME --hub-ip IP --token TOKEN --services ssh,rdp,vnc [--ssh-pubkey KEY]

# Visualizzare configurazione
sudo ./orizon_edge_setup.sh --show-config
```

### Parametri

| Parametro | Descrizione | Obbligatorio |
|-----------|-------------|--------------|
| `--name` | Nome del nodo edge | Sì |
| `--hub-ip` | IP dell'Orizon Hub | Sì |
| `--token` | Token JWT per autenticazione | Sì |
| `--services` | Servizi da installare | Sì |
| `--ssh-pubkey` | Chiave pubblica SSH da installare | No |
| `--show-config` | Mostra configurazione attuale | - |
| `--help` | Mostra messaggio di aiuto | - |

### Sistemi Operativi Supportati

Lo script rileva automaticamente:

| OS Family | Distribuzione | Package Manager |
|-----------|---------------|-----------------|
| **Debian** | Ubuntu, Debian, Kali Linux, Linux Mint, Pop!_OS, Parrot | apt |
| **RedHat** | Fedora, RHEL, CentOS, Rocky Linux, AlmaLinux | dnf |
| **Arch** | Arch Linux, Manjaro | pacman |

### Output Script Edge

Lo script esegue questi step:

1. ✅ **Rilevamento OS** - Identifica sistema e package manager
2. ✅ **Aggiornamento Sistema** - Update package manager
3. ✅ **Dipendenze Python** - websockets, paramiko, pyjwt
4. ✅ **Installazione Servizi** - SSH/RDP/VNC secondo richiesta
5. ✅ **Directory Agent** - `/opt/orizon/`
6. ✅ **Download Agent** - Da `https://HUB_IP/api/v1/downloads/orizon_agent.py`
7. ✅ **Config JSON** - File configurazione con node_id e servizi
8. ✅ **Servizio Systemd** - `orizon-agent.service`
9. ✅ **Verifica Connessione** - Test connessione WebSocket all'hub
10. ✅ **Riepilogo** - Stato servizi e comandi utili

### File Generati (Edge)

```
/opt/orizon/
├── orizon_agent.py           # Agent principale
├── config.json               # Configurazione nodo
└── ssh_keys/                 # Directory chiavi SSH

/etc/systemd/system/
└── orizon-agent.service      # Servizio systemd

/root/.ssh/
└── authorized_keys           # Chiave pubblica hub

/home/{user}/.ssh/
└── authorized_keys           # Chiave pubblica hub
```

---

## 🎯 Esempi Pratici

### Esempio 1: Edge Kali Linux con SSH + RDP

#### Sul Server Hub

```bash
cd /tmp
chmod +x orizon_hub_add_edge.sh

# Aggiungi nodo Kali con SSH e RDP
sudo ./orizon_hub_add_edge.sh \
  --name kali-edge \
  --ip 10.211.55.19 \
  --services ssh,rdp
```

**Output atteso:**
```
╔═══════════════════════════════════════════════════════════╗
║         ORIZON HUB - ADD EDGE NODE                        ║
╚═══════════════════════════════════════════════════════════╝

[INFO] Configurazione nuovo edge node:
  Nome:     kali-edge
  IP:       10.211.55.19
  Servizi:  ssh,rdp

▶ STEP 1: Verifica Prerequisiti
[✓] PostgreSQL installato
[✓] Backend Orizon attivo
[✓] Directory chiavi SSH: /root/orizon-ztc/backend/ssh_keys

▶ STEP 2: Generazione UUID per il nodo
[✓] UUID generato: abc12345-6789-...

▶ STEP 3: Generazione Chiavi SSH
[INFO] Generazione coppia chiavi ed25519...
[✓] Chiavi generate:
  Private: /root/orizon-ztc/backend/ssh_keys/kali-edge_key (419 bytes)
  Public:  /root/orizon-ztc/backend/ssh_keys/kali-edge_key.pub

...

▶ STEP 8: Riepilogo Configurazione

═══ Next Steps ═══
  1. Copia lo script di setup sull'edge node:
     scp /tmp/setup_kali-edge.sh user@10.211.55.19:/tmp/

  2. Esegui lo script sull'edge node:
     ssh user@10.211.55.19 'sudo bash /tmp/setup_kali-edge.sh'
```

#### Sul Nodo Edge (Kali Linux)

```bash
# Ricevi lo script
# (Viene copiato dal comando scp sopra)

# Esegui setup
sudo bash /tmp/setup_kali-edge.sh
```

**Output atteso:**
```
╔═══════════════════════════════════════════════════════════╗
║         ORIZON EDGE - Node Setup                          ║
╚═══════════════════════════════════════════════════════════╝

▶ STEP 1: Rilevamento Sistema Operativo
[INFO] Sistema Rilevato:
  OS:            Kali GNU/Linux Rolling
  OS Family:     debian
  Pkg Manager:   apt
[✓] Sistema operativo riconosciuto

▶ STEP 2: Aggiornamento Sistema e Dipendenze Base
[✓] apt-get update completato
[✓] Dipendenze base installate

▶ STEP 4: Configurazione Servizi
[INFO] Configurazione SSH...
[✓] ✓ SSH installato e attivo (porta 22)
[INFO] Configurazione RDP (xrdp)...
[✓] ✓ RDP (xrdp) installato e attivo (porta 3389)

...

╔═══════════════════════════════════════════════════════════╗
║              CONFIGURAZIONE COMPLETATA                    ║
╚═══════════════════════════════════════════════════════════╝

═══ Local Tunnel Endpoints ═══
  • SSH Terminal:
      Local:  127.0.0.1:22
      Remote: wss://46.101.189.126/api/v1/terminal/abc12345-6789-...

  • RDP Desktop:
      Local:  127.0.0.1:3389
      Remote: wss://46.101.189.126/api/v1/rdp/abc12345-6789-...

[✓] Setup Edge Node completato con successo!
```

### Esempio 2: Edge Ubuntu Server con solo SSH

#### Sul Server Hub

```bash
sudo ./orizon_hub_add_edge.sh \
  --name ubuntu-server \
  --ip 192.168.3.101 \
  --services ssh
```

#### Sul Nodo Edge

```bash
# Dopo aver ricevuto lo script
sudo bash /tmp/setup_ubuntu-server.sh
```

### Esempio 3: Edge Fedora con tutti i servizi

#### Sul Server Hub

```bash
sudo ./orizon_hub_add_edge.sh \
  --name fedora-workstation \
  --ip 192.168.1.50 \
  --services ssh,rdp,vnc
```

---

## 🔧 Visualizzare Configurazione

### Sul Server Hub

```bash
# Mostra tutti i nodi
sudo ./orizon_hub_add_edge.sh --show-config

# Mostra un nodo specifico
sudo ./orizon_hub_add_edge.sh --show-config kali-edge
```

**Output:**
```
▶ STEP CONFIG: Configurazione Tunnel Orizon Hub

[INFO] Configurazione per nodo: kali-edge

[INFO] ═══ Node Info ═══
  ID:      abc12345-6789-...
  Name:    kali-edge
  IP:      10.211.55.19
  Status:  online
  Type:    edge

[INFO] ═══ SSH Keys ═══
[✓] Private key: /root/orizon-ztc/backend/ssh_keys/kali-edge_key
  Size: 419 bytes
[✓] Public key: /root/orizon-ztc/backend/ssh_keys/kali-edge_key.pub
  Content: ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA...

[INFO] ═══ WebSocket Endpoints ═══
  Agent Connection: wss://46.101.189.126/api/v1/agents/abc12345-6789-.../connect
  Terminal:         wss://46.101.189.126/api/v1/terminal/abc12345-6789-...
  RDP Session:      wss://46.101.189.126/api/v1/rdp/abc12345-6789-...
  VNC Session:      wss://46.101.189.126/api/v1/vnc/abc12345-6789-...

[INFO] ═══ Tunnel Configuration ═══
  SSH Tunnel (local): Edge connects to 127.0.0.1:22
  RDP Tunnel (local): Edge connects to 127.0.0.1:3389
  VNC Tunnel (local): Edge connects to 127.0.0.1:5900

  Hub receives connections on:
    - WebSocket: wss://46.101.189.126/api/v1/terminal/abc12345-6789-... (SSH)
    - WebSocket: wss://46.101.189.126/api/v1/rdp/abc12345-6789-... (RDP)
    - WebSocket: wss://46.101.189.126/api/v1/vnc/abc12345-6789-... (VNC)
```

### Sul Nodo Edge

```bash
sudo ./orizon_edge_setup.sh --show-config
```

**Output:**
```
▶ STEP CONFIG: Configurazione Orizon Edge Node

[INFO] ═══ System Information ═══
  OS:            Kali GNU/Linux Rolling
  OS Family:     debian
  Hostname:      kali-edge
  IP Addresses:  10.211.55.19

[INFO] ═══ Agent Configuration ═══
  Config File:   /opt/orizon/config.json
  Node ID:       abc12345-6789-...
  Hub URL:       wss://46.101.189.126

[INFO] ═══ Installed Services ═══
[✓] SSH - ACTIVE
    Port: 0.0.0.0:22
[✓] RDP (xrdp) - ACTIVE
    Port: 0.0.0.0:3389

[INFO] ═══ Agent Status ═══
[✓] Orizon Agent - RUNNING
  Active: active (running) since Mon 2025-11-10 20:30:15 CET
  Main PID: 123456
  Memory: 25.3M

[INFO] ═══ Local Tunnel Configuration ═══
  L'agent crea tunnel WebSocket inversi verso l'Hub:

  [Edge Node] ←→ WebSocket ←→ [Orizon Hub]

  Servizi locali esposti attraverso i tunnel:
    • SSH:  127.0.0.1:22   → wss://HUB/api/v1/terminal/NODE_ID
    • RDP:  127.0.0.1:3389 → wss://HUB/api/v1/rdp/NODE_ID
```

---

## 🔍 Comandi Utili

### Verificare lo stato dell'agent

```bash
# Sul nodo Edge
sudo systemctl status orizon-agent

# Logs in tempo reale
sudo journalctl -u orizon-agent -f

# Ultimi 50 log
sudo journalctl -u orizon-agent -n 50
```

### Riavviare l'agent

```bash
sudo systemctl restart orizon-agent
```

### Testare connettività

```bash
# Test SSH locale
ssh localhost

# Test RDP locale (con xfreerdp)
xfreerdp /v:localhost:3389 /u:username

# Test VNC locale
vncviewer localhost:5900
```

### Verificare tunnel attivi

```bash
# Connessioni stabilite
sudo ss -tn | grep ESTAB

# Porte in ascolto
sudo ss -tlnp | grep -E ':(22|3389|5900)'
```

---

## ❗ Risoluzione Problemi

### Problema: Agent non si connette all'hub

**Sintomo:**
```
[✗] Connessione all'hub non confermata nei log
```

**Soluzione:**

1. Verifica connettività hub:
   ```bash
   ping 46.101.189.126
   curl -k https://46.101.189.126/api/v1/health
   ```

2. Controlla token JWT:
   ```bash
   cat /opt/orizon/config.json | grep jwt_token
   ```

3. Verifica firewall:
   ```bash
   # Debian/Ubuntu
   sudo ufw status
   sudo ufw allow 443/tcp

   # Fedora
   sudo firewall-cmd --list-all
   sudo firewall-cmd --add-port=443/tcp --permanent
   ```

4. Controlla logs agent:
   ```bash
   sudo journalctl -u orizon-agent -n 100
   ```

### Problema: SSH non funziona

**Sintomo:**
```
Failed to connect to local SSH
```

**Soluzione:**

1. Verifica servizio SSH:
   ```bash
   sudo systemctl status sshd  # o ssh
   sudo systemctl start sshd
   ```

2. Controlla chiavi autorizzate:
   ```bash
   cat /root/.ssh/authorized_keys
   cat /home/$(whoami)/.ssh/authorized_keys
   ```

3. Verifica permessi:
   ```bash
   chmod 700 ~/.ssh
   chmod 600 ~/.ssh/authorized_keys
   ```

4. Test manuale SSH:
   ```bash
   ssh localhost
   ```

### Problema: RDP non funziona

**Sintomo:**
```
RDP installato ma non attivo
```

**Soluzione:**

1. Verifica xrdp:
   ```bash
   sudo systemctl status xrdp
   sudo systemctl start xrdp
   ```

2. Verifica ambiente desktop:
   ```bash
   # Debian/Ubuntu
   dpkg -l | grep -E 'xfce|mate|gnome'

   # Se mancante, installa
   sudo apt install xfce4 xfce4-goodies
   ```

3. Test connessione locale:
   ```bash
   xfreerdp /v:localhost:3389 /u:$(whoami)
   ```

### Problema: Database connection error

**Sintomo:**
```
[✗] Impossibile leggere il database
```

**Soluzione:**

1. Verifica PostgreSQL:
   ```bash
   sudo systemctl status postgresql
   sudo systemctl start postgresql
   ```

2. Verifica database:
   ```bash
   sudo -u postgres psql -d orizon_ztc -c "SELECT * FROM nodes LIMIT 1;"
   ```

3. Verifica permessi utente postgres:
   ```bash
   sudo -u postgres psql -c "\du"
   ```

---

## 📊 Architettura Tunnel

```
┌─────────────────┐                    ┌─────────────────┐
│   EDGE NODE     │                    │   ORIZON HUB    │
│                 │                    │                 │
│  ┌───────────┐  │  WebSocket HTTPS  │  ┌───────────┐  │
│  │  SSH      │  │◄──────────────────┤  │ Backend   │  │
│  │  :22      │  │      wss://       │  │ FastAPI   │  │
│  └───────────┘  │                    │  └───────────┘  │
│                 │                    │                 │
│  ┌───────────┐  │                    │  ┌───────────┐  │
│  │  RDP      │  │◄──────────────────┤  │ Terminal  │  │
│  │  :3389    │  │                    │  │ Endpoint  │  │
│  └───────────┘  │                    │  └───────────┘  │
│                 │                    │                 │
│  ┌───────────┐  │                    │  ┌───────────┐  │
│  │  VNC      │  │◄──────────────────┤  │ RDP       │  │
│  │  :5900    │  │                    │  │ Endpoint  │  │
│  └───────────┘  │                    │  └───────────┘  │
│                 │                    │                 │
│  ┌───────────┐  │                    │  ┌───────────┐  │
│  │  Agent    │  │───────────────────►│  │ VNC       │  │
│  │  Python   │  │    Heartbeat      │  │ Endpoint  │  │
│  └───────────┘  │                    │  └───────────┘  │
└─────────────────┘                    └─────────────────┘
   127.0.0.1                              46.101.189.126
   (locale)                               (remoto)
```

### Flusso di Connessione

1. **Edge → Hub**: Agent si connette via WebSocket
2. **Hub → Backend**: Backend gestisce autenticazione JWT
3. **User → Hub**: Utente accede via browser/client
4. **Hub → Edge**: Tunnel proxy traffico attraverso WebSocket
5. **Edge → Service**: Agent inoltra al servizio locale (SSH/RDP/VNC)

---

## 📝 Note Importanti

1. **Sicurezza**: Gli script richiedono privilegi root (`sudo`)
2. **Token JWT**: Validità di 365 giorni, poi va rigenerato
3. **Chiavi SSH**: Formato ed25519 (419 bytes, sicuro e veloce)
4. **Firewall**: Assicurarsi che la porta 443 sia aperta per HTTPS/WebSocket
5. **Backup**: Conservare copie delle chiavi SSH generate

---

## 📞 Supporto

Per problemi o domande:
- Logs Hub: `sudo journalctl -u orizon-backend -f`
- Logs Edge: `sudo journalctl -u orizon-agent -f`
- Database: `sudo -u postgres psql -d orizon_ztc`

---

**Versione:** 1.0
**Data:** 10 Novembre 2025
**Piattaforma:** Orizon Zero Trust Connect
