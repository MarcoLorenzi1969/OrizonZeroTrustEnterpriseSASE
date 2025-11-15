# Orizon Edge Setup Complete - Guida Completa

## 📋 Indice

1. [Panoramica](#panoramica)
2. [Caratteristiche Principali](#caratteristiche-principali)
3. [Prerequisiti](#prerequisiti)
4. [Sintassi e Parametri](#sintassi-e-parametri)
5. [Funzionamento Step-by-Step](#funzionamento-step-by-step)
6. [Esempi Pratici](#esempi-pratici)
7. [Logging e Report](#logging-e-report)
8. [Troubleshooting](#troubleshooting)

---

## 📖 Panoramica

**`orizon_edge_setup_complete.sh`** è lo script **completamente automatizzato** per il setup di edge nodes nel sistema Orizon Zero Trust Connect.

A differenza degli altri script che richiedono configurazione manuale, questo script:
- Si connette automaticamente al server HUB
- Recupera tutte le configurazioni necessarie
- Installa i servizi richiesti
- Crea e verifica i tunnel
- Testa che tutto funzioni correttamente
- Genera un report finale dettagliato
- Crea un file di log completo

## ✨ Caratteristiche Principali

### 🔄 Completamente Automatizzato
- **Zero configurazione manuale** - Tutto viene fatto dallo script
- **Auto-recovery** - Recupera chiavi SSH e token dal HUB
- **Auto-installazione** - Installa automaticamente tutti i servizi necessari

### 📊 Output Verboso e Colorato
- **12 Step dettagliati** con indicatori di progresso
- **Codice colore** per successo (verde), errore (rosso), warning (giallo)
- **Output sia a terminale che su file di log**
- **Contatori** di successi, errori e warning

### 🔍 Test e Verifica Completi
- **Test connessione HUB** prima di iniziare
- **Verifica servizi locali** (SSH, RDP, VNC)
- **Test tunnel** per ogni protocollo
- **Verifica traffico** attraverso i tunnel
- **Report finale** con statistiche complete

### 📝 Logging Dettagliato
- **File di log timestampato** salvato in `/var/log/orizon_edge_setup_YYYYMMDD_HHMMSS.log`
- **Dual output** - tutto viene mostrato a video E salvato su log
- **Comandi utili** mostrati nel report finale

---

## 🔧 Prerequisiti

### Sul Server HUB
1. L'edge node deve essere **già registrato** nel database HUB usando `orizon_hub_add_edge.sh`
2. SSH abilitato e accessibile
3. PostgreSQL con database `orizon_ztc` configurato
4. Backend Orizon in esecuzione

### Sull'Edge Node
1. **Root/sudo access** (lo script deve essere eseguito come root)
2. Sistema operativo supportato:
   - Debian/Ubuntu/Kali Linux
   - Fedora/RHEL/CentOS
   - Arch/Manjaro
3. Connessione internet verso il HUB
4. Python 3.8+ (verrà installato se mancante)

---

## 🎯 Sintassi e Parametri

### Sintassi Base

```bash
sudo ./orizon_edge_setup_complete.sh \
  --hub-ip <IP_OR_FQDN> \
  --hub-user <USERNAME> \
  --hub-password <PASSWORD> \
  --edge-name <EDGE_NAME> \
  --services <SERVICES> \
  [--edge-location <LOCATION>]
```

### Parametri Obbligatori

| Parametro | Descrizione | Esempio |
|-----------|-------------|---------|
| `--hub-ip` | IP o FQDN del server HUB | `46.101.189.126` o `hub.example.com` |
| `--hub-user` | Username SSH per accedere al HUB | `orizonai` o `root` |
| `--hub-password` | Password SSH per accedere al HUB | `'MySecurePassword123'` |
| `--edge-name` | Nome dell'edge node (deve esistere nel database HUB) | `KaliEdge` o `UbuntuServer01` |
| `--services` | Lista servizi da configurare (separati da virgola) | `ssh`, `rdp`, `vnc` o `ssh,rdp,vnc` |

### Parametri Opzionali

| Parametro | Descrizione | Default | Esempio |
|-----------|-------------|---------|---------|
| `--edge-location` | Descrizione geografica/logica dell'edge | `"Unknown Location"` | `"Data Center Amsterdam"` |

### Servizi Disponibili

- **`ssh`** - OpenSSH Server (porta 22)
- **`rdp`** - xrdp Remote Desktop (porta 3389)
- **`vnc`** - TigerVNC Server (porta 5901)

---

## 🔄 Funzionamento Step-by-Step

Lo script esegue **12 step principali**, ognuno con output verboso:

### STEP 1: Verifica Prerequisiti
- Controlla privilegi root
- Rileva sistema operativo
- Identifica package manager
- Mostra informazioni sistema

```
[INFO] Rilevamento sistema operativo...
[✓] Sistema rilevato: Kali GNU/Linux Rolling
  - Famiglia: debian
  - Package Manager: apt
  - SSH Service: ssh
```

### STEP 2: Test Connessione al Server HUB
- Test ping al HUB
- Verifica connessione SSH
- Valida credenziali
- Test firewall

```
[INFO] Test connessione al server HUB 46.101.189.126...
[✓] Server HUB raggiungibile (ping)
[✓] Connessione SSH al HUB funzionante
```

### STEP 3: Recupero Configurazione dal HUB
- Query database PostgreSQL per Node UUID
- Recupero JWT token
- Download chiave SSH pubblica/privata
- Validazione configurazione

```
[✓] Node UUID recuperato: fcf9ff58-8aee-4d69-8471-73f503ed8672
[✓] JWT token recuperato (287 caratteri)
[✓] Chiave SSH pubblica recuperata dal HUB
```

### STEP 4: Aggiornamento Sistema e Installazione Dipendenze
- Update package list
- Installazione Python3, pip, curl, sshpass
- Installazione librerie Python (websockets, paramiko, pyjwt)

```
[✓] Lista pacchetti aggiornata
[✓] Dipendenze base installate
[✓] Librerie Python installate (websockets, paramiko, pyjwt)
```

### STEP 5: Installazione Servizi Richiesti
- Installazione SSH server (se richiesto)
- Installazione RDP/xrdp (se richiesto)
- Installazione VNC/TigerVNC (se richiesto)
- Abilitazione e avvio servizi

```
[✓] SSH server già installato e attivo
[INFO] Installazione RDP server (xrdp)...
[✓] xrdp installato e avviato
[✓] xrdp verificato attivo su porta 3389
```

### STEP 6: Verifica Servizi Locali
- Test porta SSH (22)
- Test porta RDP (3389)
- Test porta VNC (5901)
- Verifica che rispondano

```
[INFO] Test SSH locale (porta 22)...
[✓] SSH risponde su porta 22
[INFO] Test RDP locale (porta 3389)...
[✓] RDP risponde su porta 3389
```

### STEP 7: Download e Configurazione Agent Orizon
- Download agent da HUB (HTTPS/HTTP/SCP fallback)
- Verifica integrità agent
- Creazione directory `/opt/orizon`
- Impostazione permessi

```
[✓] Agent scaricato via HTTPS
[✓] Agent verificato (1847 righe)
```

### STEP 8: Creazione File di Configurazione
- Generazione `config.json` con tutte le impostazioni
- Node ID, JWT token, servizi abilitati
- WebSocket URL al HUB

```
[✓] File di configurazione creato: /opt/orizon/config.json
  - Node ID: fcf9ff58-8aee-4d69-8471-73f503ed8672
  - Node Name: KaliEdge
  - Location: Data Center Amsterdam
  - Hub URL: wss://46.101.189.126
  - Services: SSH=true, RDP=true, VNC=false
```

### STEP 9: Creazione Servizio Systemd
- Creazione file `/etc/systemd/system/orizon-agent.service`
- Daemon reload
- Enable service per auto-start

```
[✓] Servizio systemd creato e abilitato
```

### STEP 10: Avvio Agent Orizon
- Start servizio `orizon-agent`
- Verifica status
- Check logs per errori

```
[✓] Agent avviato
[✓] Agent verificato attivo
● orizon-agent.service - Orizon Zero Trust Connect Agent
     Loaded: loaded
     Active: active (running) since...
```

### STEP 11: Test Connessione e Tunnel
- Aspetta connessione agent al HUB
- Verifica log per "Connected to hub"
- Test comunicazione HUB → Edge
- Query status endpoint

```
[✓] Agent connesso al HUB
[✓] HUB può comunicare con l'edge
```

### STEP 12: Verifica Traffico attraverso Tunnel
- Test traffico SSH attraverso tunnel
- Test traffico RDP attraverso tunnel
- Test traffico VNC attraverso tunnel
- Verifica nei log dell'agent

```
[INFO] Verifica traffico attraverso tunnel SSH (porta 22)...
[✓] Servizio SSH risponde localmente su porta 22
[✓] Traffico SSH rilevato nei log dell'agent
```

### STEP 13: Report Finale
- Statistiche complete dell'esecuzione
- Informazioni edge node
- Status servizi
- Comandi utili
- Percorso file di log

```
╔═══════════════════════════════════════════════════════════════════╗
║                      REPORT FINALE SETUP                          ║
╚═══════════════════════════════════════════════════════════════════╝

Edge Node Information:
  Nome:           KaliEdge
  Location:       Data Center Amsterdam
  Node UUID:      fcf9ff58-8aee-4d69-8471-73f503ed8672

Statistiche Esecuzione:
  Successi:  45
  Errori:    0
  Warning:   2

✅ SETUP COMPLETATO CON SUCCESSO!
```

---

## 💡 Esempi Pratici

### Esempio 1: Setup Kali Linux con SSH + RDP

```bash
sudo ./orizon_edge_setup_complete.sh \
  --hub-ip 46.101.189.126 \
  --hub-user orizonai \
  --hub-password 'ripper-FfFIlBelloccio.1969F' \
  --edge-name KaliEdge \
  --edge-location "Kali Lab - Amsterdam DC" \
  --services ssh,rdp
```

**Output:**
```
╔═══════════════════════════════════════════════════════════════════╗
║         ORIZON ZERO TRUST CONNECT - EDGE SETUP COMPLETE          ║
║              Automated Edge Node Configuration v1.0              ║
╚═══════════════════════════════════════════════════════════════════╝

[INFO] Inizio setup edge node - 2025-11-11 09:54:32
[INFO] Log file: /var/log/orizon_edge_setup_20251111_095432.log

═══════════════════════════════════════════════════════════════════
  STEP 1: Verifica Prerequisiti
═══════════════════════════════════════════════════════════════════
[INFO] Rilevamento sistema operativo...
[✓] Sistema rilevato: Kali GNU/Linux Rolling
...
```

### Esempio 2: Setup Ubuntu Server con Tutti i Servizi

```bash
sudo ./orizon_edge_setup_complete.sh \
  --hub-ip hub.orizon.local \
  --hub-user admin \
  --hub-password 'SecurePass123!' \
  --edge-name UbuntuServer01 \
  --edge-location "Production Server - London" \
  --services ssh,rdp,vnc
```

### Esempio 3: Setup Fedora con Solo SSH

```bash
sudo ./orizon_edge_setup_complete.sh \
  --hub-ip 192.168.1.100 \
  --hub-user orizon \
  --hub-password 'MyPassword' \
  --edge-name FedoraEdge \
  --services ssh
```

---

## 📝 Logging e Report

### File di Log

Ogni esecuzione crea un file di log timestampato:
```
/var/log/orizon_edge_setup_YYYYMMDD_HHMMSS.log
```

Esempio: `/var/log/orizon_edge_setup_20251111_095432.log`

### Contenuto del Log

Il log contiene:
- **Timestamp** per ogni operazione
- **Output completo** di tutti i comandi eseguiti
- **Errori e warning** con dettagli
- **Test e verifiche** eseguiti
- **Report finale** con statistiche

### Visualizzare il Log

```bash
# Visualizza log completo
cat /var/log/orizon_edge_setup_20251111_095432.log

# Ultimi 50 righe
tail -50 /var/log/orizon_edge_setup_20251111_095432.log

# Cerca errori
grep -i "error\|✗" /var/log/orizon_edge_setup_20251111_095432.log

# Cerca warning
grep -i "warning\|⚠" /var/log/orizon_edge_setup_20251111_095432.log
```

### Report Finale

Il report finale include:

1. **Edge Node Information**
   - Nome, Location, UUID, Sistema operativo

2. **Hub Connection**
   - IP HUB, WebSocket URL

3. **Servizi Configurati**
   - Status di ogni servizio (SSH, RDP, VNC)
   - Porte in ascolto

4. **Agent Status**
   - Stato attivo/non attivo
   - Avvio automatico abilitato
   - Uptime

5. **File Creati**
   - Percorsi di config, agent, service, log

6. **Statistiche Esecuzione**
   - Numero successi, errori, warning
   - Status finale (successo/errori)

7. **Comandi Utili**
   - Comandi per gestire l'agent
   - Comandi per visualizzare log e config

---

## 🔧 Troubleshooting

### Problema: "Impossibile connettersi al HUB via SSH"

**Causa:** Credenziali errate o SSH non raggiungibile

**Soluzione:**
```bash
# Test manuale connessione SSH
ssh orizonai@46.101.189.126

# Verifica che SSH sia attivo sul HUB
ssh orizonai@46.101.189.126 "systemctl status sshd"

# Verifica firewall
ssh orizonai@46.101.189.126 "sudo ufw status"
```

### Problema: "Edge 'XYZ' non trovato nel database del HUB"

**Causa:** L'edge non è stato registrato sul HUB

**Soluzione:**
```bash
# Sul HUB, registrare prima l'edge
./orizon_hub_add_edge.sh \
  --name KaliEdge \
  --ip 10.211.55.19 \
  --services ssh,rdp,vnc

# Poi eseguire lo script sull'edge
```

### Problema: "Servizio RDP non risponde su porta 3389"

**Causa:** xrdp non installato o non avviato

**Soluzione:**
```bash
# Verifica status xrdp
systemctl status xrdp

# Verifica porta in ascolto
netstat -tlnp | grep 3389

# Restart xrdp
systemctl restart xrdp

# Check log
journalctl -u xrdp -n 50
```

### Problema: "Agent avviato ma non attivo"

**Causa:** Errore nella configurazione o dipendenze mancanti

**Soluzione:**
```bash
# Verifica log agent
journalctl -u orizon-agent -f

# Verifica config
cat /opt/orizon/config.json

# Test manuale agent
cd /opt/orizon
python3 orizon_agent.py -c config.json

# Verifica dipendenze Python
pip3 list | grep -E "websockets|paramiko|pyjwt"
```

### Problema: "JWT token non trovato"

**Causa:** Token non generato sul HUB o percorso errato

**Soluzione:**
```bash
# Sul HUB, verifica token
ls -la /root/.ssh/orizon_edge_*_token.jwt

# Rigenera token se necessario
./orizon_hub_add_edge.sh --name KaliEdge --services ssh,rdp
```

### Problema: "Permission denied" durante l'esecuzione

**Causa:** Script non eseguito come root

**Soluzione:**
```bash
# Esegui con sudo
sudo ./orizon_edge_setup_complete.sh [parametri...]

# Oppure come root
su -
./orizon_edge_setup_complete.sh [parametri...]
```

---

## 📊 Codici di Colore Output

- 🟢 **Verde** `[✓]` - Operazione completata con successo
- 🔴 **Rosso** `[✗]` - Errore critico, operazione fallita
- 🟡 **Giallo** `[⚠]` - Warning, operazione completata con note
- 🔵 **Blu** `[INFO]` - Informazione, status o progresso
- 🟣 **Magenta** - Header e separatori
- 🔷 **Cyan** - Step e sezioni principali

---

## 🎯 Best Practices

### Prima dell'Esecuzione

1. **Registrare l'edge sul HUB** usando `orizon_hub_add_edge.sh`
2. **Verificare connettività** SSH al HUB manualmente
3. **Backup** di configurazioni esistenti se presenti
4. **Controllare spazio disco** disponibile (almeno 500MB)

### Durante l'Esecuzione

1. **Non interrompere** lo script durante l'esecuzione
2. **Monitorare output** per eventuali warning
3. **Attendere** il completamento di tutti i 12 step
4. **Salvare** il percorso del file di log mostrato all'inizio

### Dopo l'Esecuzione

1. **Verificare report finale** per eventuali errori
2. **Controllare file di log** per dettagli
3. **Testare connettività** ai servizi
4. **Verificare status agent** con `systemctl status orizon-agent`
5. **Monitorare log agent** con `journalctl -u orizon-agent -f`

---

## 🔗 Comandi Utili Post-Setup

```bash
# Verifica status agent
systemctl status orizon-agent

# Visualizza log agent in tempo reale
journalctl -u orizon-agent -f

# Restart agent
systemctl restart orizon-agent

# Stop agent
systemctl stop orizon-agent

# Start agent
systemctl start orizon-agent

# Visualizza configurazione
cat /opt/orizon/config.json | jq '.'

# Verifica servizi locali
netstat -tlnp | grep -E ":(22|3389|5901)"

# Test connettività al HUB
curl -k https://46.101.189.126:8000/api/v1/health
```

---

## 📚 Riferimenti

- **Script HUB:** `orizon_hub_add_edge.sh` - Registra edge sul HUB
- **Script Edge Manuale:** `orizon_edge_setup.sh` - Setup manuale step-by-step
- **Documentazione Completa:** `ORIZON_SCRIPTS_GUIDE.md`
- **README Generale:** `README.md`

---

**Orizon Zero Trust Connect v1.1**
*Script di automazione per deployment edge nodes*

Generated: 2025-11-11
Version: 1.0
