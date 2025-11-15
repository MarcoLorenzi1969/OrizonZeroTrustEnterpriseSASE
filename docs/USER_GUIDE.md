# 📖 User Guide - Orizon Zero Trust Connect

**Versione:** 1.0.0
**Last Updated:** Gennaio 2025
**Target Audience:** End Users, Admins, Distributori

---

## 📋 Indice

1. [Introduzione](#introduzione)
2. [Getting Started](#getting-started)
3. [Dashboard Overview](#dashboard-overview)
4. [Gestione Nodi](#gestione-nodi)
5. [Gestione Tunnel](#gestione-tunnel)
6. [Access Control (ACL)](#access-control-acl)
7. [Audit e Sicurezza](#audit-e-sicurezza)
8. [Gestione Utenti (Admin)](#gestione-utenti-admin)
9. [Impostazioni Profilo](#impostazioni-profilo)
10. [FAQ e Troubleshooting](#faq-e-troubleshooting)

---

## 🎯 Introduzione

### Cos'è Orizon Zero Trust Connect?

Orizon Zero Trust Connect (ZTC) è una piattaforma **SD-WAN** (Software-Defined Wide Area Network) con architettura **Zero Trust** che permette di:

- **Connettere** dispositivi remoti in modo sicuro
- **Gestire** tunnel SSH/HTTPS per accesso remoto
- **Monitorare** lo stato della rete in tempo reale
- **Controllare** gli accessi con regole ACL granulari
- **Tracciare** tutte le attività con audit completo

### A chi è destinato?

| Ruolo | Descrizione | Cosa può fare |
|-------|-------------|---------------|
| **SuperUser** | Proprietario piattaforma (Marco) | Accesso completo, gestione di tutto |
| **Super Admin** | Distributori | Gestione clienti enterprise, creazione Admin |
| **Admin** | Rivenditori | Gestione clienti finali, creazione User |
| **User** | Cliente finale | Gestione propri nodi e tunnel |

### Come Funziona?

```
1. Installi l'Agent su un dispositivo remoto
       ↓
2. L'Agent si connette al Hub centrale
       ↓
3. Crei tunnel SSH o HTTPS dal Dashboard
       ↓
4. Accedi al dispositivo remoto tramite tunnel
       ↓
5. Monitora metriche e logs in tempo reale
```

---

## 🚀 Getting Started

### 1. Primo Accesso

#### Login alla Piattaforma

1. Apri il browser e vai su: **https://orizon.syneto.net**
2. Inserisci le tue credenziali:
   - **Email**: La tua email registrata
   - **Password**: La password fornita (cambiarla al primo login!)
3. Se hai 2FA attivo:
   - Inserisci il codice a 6 cifre da Google Authenticator
   - Oppure usa un backup code se non hai accesso all'app

![Login Screen](../screenshots/login-page.png)

#### Primo Login - Cambio Password

Al primo accesso, ti verrà chiesto di **cambiare la password**:

1. Vai su **Impostazioni** (icona ingranaggio in alto a destra)
2. Clicca su **Cambia Password**
3. Inserisci:
   - Password corrente (quella temporanea)
   - Nuova password (min 12 caratteri, complessa)
   - Conferma nuova password
4. Clicca **Salva**

**Requisiti password:**
- ✅ Almeno 12 caratteri
- ✅ Almeno una maiuscola
- ✅ Almeno una minuscola
- ✅ Almeno un numero
- ✅ Almeno un carattere speciale (!@#$%^&*)

### 2. Setup Two-Factor Authentication (Consigliato)

Per maggiore sicurezza, **abilita la 2FA**:

1. Vai su **Impostazioni** → **Sicurezza**
2. Clicca su **Abilita 2FA**
3. Scansiona il QR code con **Google Authenticator** o **Authy**
4. Inserisci il codice a 6 cifre per confermare
5. **IMPORTANTE**: Salva i 10 backup codes in un posto sicuro!
   - Usa questi codici se perdi accesso all'app 2FA
   - Ogni codice è usa-e-getta

![2FA Setup](../screenshots/2fa-setup.png)

---

## 📊 Dashboard Overview

### Interfaccia Principale

Il **Dashboard** è la tua home page e mostra:

![Dashboard](../screenshots/dashboard.png)

#### 1. **Statistics Cards** (in alto)

| Stat | Descrizione |
|------|-------------|
| **Nodi Totali** | Numero dispositivi registrati |
| **Nodi Online** | Dispositivi connessi in questo momento |
| **Tunnel Attivi** | Tunnel SSH/HTTPS aperti |
| **Utenti Online** | Utenti connessi (solo Admin+) |

#### 2. **Network Map 3D** (centro)

Visualizzazione 3D della tua rete:

- **Hub centrale** (blu) = Server principale
- **Nodi periferici** (sfere colorate):
  - 🟢 **Verde** = Online
  - 🟡 **Giallo** = Warning (alto utilizzo risorse)
  - 🔴 **Rosso** = Offline
- **Linee** = Tunnel attivi tra hub e nodi

**Interazioni:**
- **Click** su un nodo per vedere dettagli
- **Scroll** per zoom in/out
- **Drag** per ruotare la vista
- **Doppio click** su nodo per aprire pagina dettagli

#### 3. **Quick Actions** (sidebar destra)

Azioni rapide:
- ➕ **Aggiungi Nodo**
- 🔀 **Crea Tunnel**
- 🛡️ **Nuova Regola ACL**

#### 4. **Recent Activity** (in basso)

Ultime azioni sulla piattaforma:
- Login/logout
- Creazione tunnel
- Modifiche regole ACL
- Alerts di sistema

---

## 🖥️ Gestione Nodi

### Cos'è un Nodo?

Un **Nodo** è un dispositivo (server, PC, Raspberry Pi, etc.) su cui hai installato l'**Orizon Agent** per connetterlo al hub centrale.

### Installare l'Agent su un Nodo

#### Linux/macOS

```bash
# Download e installazione automatica
curl -sSL https://orizon.syneto.net/downloads/install.sh | sudo bash

# Durante l'installazione ti verrà chiesto:
# - Nome del nodo (es: "production-server-01")
# - Token di autenticazione (lo trovi nel Dashboard dopo aver creato il nodo)
```

#### Windows

```powershell
# PowerShell come Amministratore
Invoke-WebRequest https://orizon.syneto.net/downloads/install.ps1 -OutFile install.ps1
.\install.ps1

# Segui le istruzioni a schermo
```

### Registrare un Nuovo Nodo

1. **Nel Dashboard**, clicca su **➕ Aggiungi Nodo**
2. Compila il form:
   - **Nome**: Nome descrittivo (es: "Server Produzione Milano")
   - **Tipo**: Seleziona OS (Linux, macOS, Windows, Docker, Kubernetes)
   - **Indirizzo IP**: IP privato del nodo (es: 192.168.1.100)
   - **Location** (opzionale): Città/Paese per geolocalizzazione
   - **Tags** (opzionale): Tag per organizzare nodi (es: "production", "dev")
3. Clicca **Crea Nodo**
4. **IMPORTANTE**: Copia e salva l'**Agent Token** mostrato (lo vedrai solo ora!)
5. Usa questo token durante l'installazione dell'agent

![Create Node](../screenshots/create-node.png)

### Visualizzare Dettagli Nodo

1. Vai su **Nodi** nel menu laterale
2. Clicca su un nodo dalla lista
3. Visualizzi:
   - **Status**: Online, Offline, Degraded
   - **Metriche Real-time**:
     - CPU Usage (%)
     - RAM Usage (%)
     - Disk Usage (%)
     - Network Traffic (upload/download)
   - **Tunnel attivi** su questo nodo
   - **Geolocation** (se configurata)
   - **Last Seen**: Ultima connessione

![Node Details](../screenshots/node-details.png)

### Modificare un Nodo

1. Nella pagina dettagli nodo, clicca **✏️ Modifica**
2. Puoi cambiare:
   - Nome
   - Location
   - Tags
3. Clicca **Salva Modifiche**

### Rimuovere un Nodo

1. Nella pagina dettagli nodo, clicca **🗑️ Elimina**
2. **Conferma** l'eliminazione
3. ⚠️ **Attenzione**: Verranno chiusi anche tutti i tunnel associati!

---

## 🔀 Gestione Tunnel

### Cos'è un Tunnel?

Un **Tunnel** è una connessione sicura (cifrata) che permette di accedere a un servizio sul nodo remoto come se fosse locale.

**Tipi di tunnel:**
- **SSH Tunnel**: Accesso shell remoto sicuro
- **HTTPS Tunnel**: Accesso a servizi web (HTTP/HTTPS)

### Come Funziona un Tunnel?

```
Tuo Computer → Hub (46.101.189.126:porta_remota) → Tunnel cifrato → Nodo:porta_locale

Esempio SSH:
ssh -p 10025 user@46.101.189.126 → collega a → nodo_remoto:22
```

### Creare un Tunnel SSH

1. Vai su **Tunnel** → **➕ Nuovo Tunnel**
2. Compila:
   - **Nodo**: Seleziona il nodo di destinazione
   - **Tipo**: SSH
   - **Porta Locale**: 22 (porta SSH sul nodo, di solito 22)
   - **Auto-reconnect**: ✅ Abilita (consigliato)
3. Clicca **Crea Tunnel**
4. Il sistema assegna automaticamente una **Porta Remota** (es: 10025)
5. Status diventa **Connecting** → **Active** quando pronto

![Create Tunnel](../screenshots/create-tunnel.png)

### Usare il Tunnel SSH

Una volta creato, vedi la **Connection String**:

```bash
ssh -p 10025 user@46.101.189.126
```

**Dove:**
- `10025` = Porta remota assegnata
- `46.101.189.126` = Hub centrale
- `user` = Username sul nodo remoto

**Esempio:**
```bash
# Connessione SSH al nodo remoto
ssh -p 10025 ubuntu@46.101.189.126

# Trasferire file (SCP)
scp -P 10025 file.txt ubuntu@46.101.189.126:~/

# Port forwarding
ssh -p 10025 -L 8080:localhost:80 ubuntu@46.101.189.126
```

### Creare un Tunnel HTTPS

1. Vai su **Tunnel** → **➕ Nuovo Tunnel**
2. Compila:
   - **Nodo**: Seleziona il nodo
   - **Tipo**: HTTPS
   - **Porta Locale**: Porta del servizio web sul nodo (es: 80, 443, 8080)
3. Clicca **Crea Tunnel**
4. Porta remota assegnata (range 60001-65000)

**Accesso:**
```
https://46.101.189.126:60123
```

### Monitorare Tunnel

Nella pagina **Tunnel**, vedi per ogni tunnel:

- **Status**:
  - 🟢 **Active**: Tunnel funzionante
  - 🟡 **Connecting**: In connessione
  - 🔴 **Error**: Problema di connessione
  - ⚫ **Inactive**: Tunnel chiuso

- **Statistiche**:
  - Bytes Sent/Received
  - Latency (ms)
  - Uptime
  - Reconnects Count (quante volte si è riconnesso)

### Chiudere un Tunnel

1. Nella lista tunnel, clicca **🗑️** sul tunnel
2. Conferma chiusura
3. La porta remota viene liberata e può essere riutilizzata

---

## 🛡️ Access Control (ACL)

### Cos'è una Regola ACL?

Una **ACL Rule** (Access Control List) è una regola di sicurezza che decide se permettere o bloccare una connessione di rete.

**Filosofia Zero Trust:**
- **Default DENY**: Se nessuna regola permette, blocca
- **Explicit ALLOW**: Devi creare regole che permettono connessioni specifiche

### Visualizzare Regole ACL

1. Vai su **ACL** nel menu
2. Vedi lista di tutte le regole, ordinate per **Priority** (priorità)

**Colonne:**
- **Priority**: 1-100 (1 = massima priorità, viene valutata per prima)
- **Name**: Nome descrittivo regola
- **Action**: ALLOW (permetti) o DENY (blocca)
- **Source → Destination**: IP sorgente → IP destinazione
- **Protocol/Port**: TCP/UDP/ICMP e porta
- **Enabled**: ✅ Abilitata / ❌ Disabilitata

### Creare una Regola ACL

#### Esempio: Permettere SSH solo dall'ufficio

1. Clicca **➕ Nuova Regola ACL**
2. Compila:
   - **Nome**: "Allow SSH from office"
   - **Priority**: 10 (bassa = alta priorità)
   - **Action**: ALLOW
   - **Source IP**: 203.0.113.0/24 (range IP ufficio)
   - **Destination IP**: 192.168.1.0/24 (range server produzione)
   - **Protocol**: TCP
   - **Destination Port**: 22 (SSH)
   - **Time Restrictions** (opzionale):
     - Days: Lun-Ven
     - Hours: 08:00-18:00
3. Clicca **Crea Regola**

![Create ACL](../screenshots/create-acl.png)

#### Esempio: Bloccare tutto il traffico esterno

```json
{
  "name": "Default Deny All",
  "priority": 100,
  "action": "DENY",
  "source_ip": "0.0.0.0/0",
  "destination_ip": "0.0.0.0/0",
  "protocol": "ALL"
}
```

### Priority nelle Regole ACL

Le regole sono valutate **in ordine di priority (ASC)**:

```
Priority 1  → Valutata per prima
Priority 10
Priority 50
Priority 100 → Valutata per ultima
```

**Prima regola che matcha vince!**

**Esempio:**
```
1. Priority 10: ALLOW SSH from 203.0.113.50 → 192.168.1.100:22
2. Priority 20: DENY all from 203.0.113.0/24 → 192.168.1.0/24

Risultato:
- Connessione da 203.0.113.50 → 192.168.1.100:22 = ✅ ALLOWED (regola 1)
- Connessione da 203.0.113.60 → 192.168.1.100:22 = ❌ DENIED (regola 2)
```

### Time-Based ACL

Puoi creare regole attive solo in determinati orari:

**Esempio: Accesso solo durante orario lavorativo**
```json
{
  "name": "Business hours only",
  "time_restrictions": {
    "days_of_week": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
    "time_range": {
      "start": "08:00",
      "end": "18:00"
    }
  }
}
```

### Testare una Regola (Dry-Run)

Prima di applicare, **testa la regola**:

1. Nella pagina ACL, clicca **🧪 Test Regola**
2. Inserisci:
   - Source IP: 203.0.113.50
   - Destination IP: 192.168.1.100
   - Protocol: TCP
   - Port: 22
3. Clicca **Valuta**
4. Vedi risultato:
   - ✅ **ALLOW** (matched rule: "Allow SSH from office")
   - ❌ **DENY** (matched rule: "Default Deny")
   - ❌ **DEFAULT DENY** (no matching rule)

### Abilitare/Disabilitare Regole

Per disabilitare temporaneamente una regola senza eliminarla:

1. Nella lista ACL, toggle **switch** sulla regola
2. Regola disabilitata = non viene valutata

### Eliminare una Regola

1. Clicca **🗑️** sulla regola
2. Conferma eliminazione

---

## 📜 Audit e Sicurezza

### Audit Logs

Gli **Audit Logs** registrano **ogni azione** sulla piattaforma per:
- Compliance (GDPR/NIS2/ISO 27001)
- Security monitoring
- Troubleshooting

### Visualizzare Audit Logs

1. Vai su **Audit** nel menu
2. Vedi lista di tutti gli eventi

**Informazioni per evento:**
- **Timestamp**: Data/ora precisa
- **Action**: Tipo azione (LOGIN, CREATE_TUNNEL, DELETE_USER, etc.)
- **User**: Chi ha eseguito l'azione
- **Resource**: Su cosa (nodo, tunnel, utente)
- **IP Address**: Da dove
- **Geolocation**: Città/Paese (basato su IP)
- **Result**: Success / Failed

![Audit Logs](../screenshots/audit-logs.png)

### Filtrare Audit Logs

Usa i filtri per trovare eventi specifici:

**Filtri disponibili:**
- **Action**: Seleziona tipo azione
- **User**: Filtra per utente specifico
- **Date Range**: Da data → A data
- **Severity**: INFO, WARNING, ERROR, CRITICAL
- **IP Address**: Cerca per IP
- **Search**: Full-text search

**Esempi:**
```
# Tutti i login falliti oggi
Action: LOGIN_FAILED
Date: Oggi

# Tutte le azioni di un utente
User: john@example.com
Date: Ultima settimana

# Tutti gli errori critici
Severity: CRITICAL
Date: Ultimo mese
```

### Esportare Audit Logs

Per compliance o analisi:

1. Imposta i filtri desiderati
2. Clicca **📥 Export**
3. Seleziona formato:
   - **JSON**: Strutturato, per analisi programmatica
   - **CSV**: Excel-compatible, per spreadsheet
   - **SIEM (CEF)**: Per SIEM (Splunk, ELK)
4. Download file

### Statistiche Audit

Nella sezione **Statistics**, vedi:

- **Top Actions**: Azioni più frequenti
- **Top Users**: Utenti più attivi
- **Failed Logins**: Tentativi login falliti (security alert!)
- **Timeline**: Grafico attività nel tempo

---

## 👥 Gestione Utenti (Admin)

> **Nota**: Questa sezione è visibile solo a **Admin**, **Super Admin** e **SuperUser**.

### Visualizzare Utenti

1. Vai su **Utenti** nel menu
2. Vedi lista di tutti gli utenti che puoi gestire

**Hierarchy:**
- **SuperUser**: Vede tutti
- **Super Admin**: Vede utenti creati da sé + sotto-utenti
- **Admin**: Vede solo utenti creati da sé

### Creare un Nuovo Utente

1. Clicca **➕ Nuovo Utente**
2. Compila:
   - **Email**: Email utente (username)
   - **Password**: Password temporanea (l'utente la cambierà al primo login)
   - **Role**: Ruolo (puoi creare solo ruoli inferiori al tuo)
3. Clicca **Crea Utente**
4. Invia le credenziali all'utente via email sicura

**Ruoli creabili:**
```
SuperUser può creare: SuperAdmin, Admin, User
SuperAdmin può creare: Admin, User
Admin può creare: User
User non può creare altri utenti
```

![Create User](../screenshots/create-user.png)

### Modificare Utente

1. Clicca su utente dalla lista
2. Puoi modificare:
   - Email
   - Status (Attivo/Disattivo)
3. Clicca **Salva Modifiche**

### Cambiare Ruolo Utente

1. Nella pagina dettagli utente, clicca **Cambia Ruolo**
2. Seleziona nuovo ruolo (solo inferiori al tuo)
3. Conferma cambio

### Disabilitare Utente

Per disabilitare temporaneamente un utente (senza eliminarlo):

1. Nella pagina dettagli utente, toggle **Status**
2. Utente disabilitato:
   - ❌ Non può fare login
   - ❌ Token JWT esistenti invalidati
   - ✅ Nodi e tunnel rimangono (ma inaccessibili)

### Eliminare Utente

> **⚠️ Solo SuperUser può eliminare utenti**

1. Nella pagina dettagli utente, clicca **🗑️ Elimina Utente**
2. Conferma eliminazione
3. **Attenzione**: Verranno eliminati anche:
   - Tutti i nodi dell'utente
   - Tutti i tunnel
   - Tutte le regole ACL create dall'utente
   - (Audit logs vengono anonimizzati per compliance)

---

## ⚙️ Impostazioni Profilo

### Accedere alle Impostazioni

Clicca sull'**icona profilo** (in alto a destra) → **Impostazioni**

### Tabs Disponibili

#### 1. **Profilo**

- **Email**: Visualizzazione (non modificabile)
- **Ruolo**: Visualizzazione
- **Account creato**: Data registrazione
- **Ultimo accesso**: Timestamp

#### 2. **Sicurezza**

**Cambio Password:**
1. Inserisci password corrente
2. Inserisci nuova password (min 12 caratteri)
3. Conferma nuova password
4. Clicca **Cambia Password**

**Two-Factor Authentication:**
- **Se disabilitato**: Pulsante "Abilita 2FA"
- **Se abilitato**:
  - Stato: ✅ Attivo
  - Backup codes rimanenti: X/10
  - Pulsante "Genera nuovi backup codes"
  - Pulsante "Disabilita 2FA" (richiede password)

![Settings Security](../screenshots/settings-security.png)

#### 3. **Sessioni Attive**

Vedi tutte le sessioni (dispositivi) attivi:

| Dispositivo | IP Address | Location | Last Activity | Azioni |
|-------------|------------|----------|---------------|--------|
| Chrome (Windows) | 203.0.113.50 | Milan, IT | 2 min ago | Corrente |
| Safari (macOS) | 203.0.113.51 | Milan, IT | 1h ago | 🗑️ Termina |

**Termina sessione:**
- Clicca **🗑️** per terminare una sessione sospetta
- Invalida il token JWT di quella sessione

#### 4. **Notifiche**

Configura preferenze notifiche:

- ✉️ **Email notifications**:
  - [ ] Login da nuovo dispositivo
  - [ ] Tunnel creati/chiusi
  - [ ] Regole ACL modificate
  - [ ] Alerts di sicurezza

- 🔔 **In-app notifications**:
  - [ ] Nodi offline
  - [ ] Tunnel error
  - [ ] High resource usage

---

## ❓ FAQ e Troubleshooting

### Login & Autenticazione

#### Q: Ho dimenticato la password, come la recupero?

1. Nella pagina di login, clicca **Password dimenticata?**
2. Inserisci la tua email
3. Riceverai un'email con link di reset (valido 1 ora)
4. Clicca sul link e inserisci nuova password

#### Q: Ho perso accesso all'app 2FA, come faccio?

Usa un **backup code**:
1. Nel login, dopo email/password, clicca **Usa backup code**
2. Inserisci uno dei 10 backup codes che hai salvato
3. ⚠️ Il codice viene consumato (one-time use)
4. Se finisci i backup codes, contatta admin per reset 2FA

#### Q: Il login è lento, perché?

Possibili cause:
- Rate limiting attivo (troppi tentativi falliti)
- Server sotto carico
- Connessione internet lenta

**Soluzione**: Aspetta 1-2 minuti e riprova

---

### Nodi & Agent

#### Q: Il nodo risulta "Offline" ma è acceso

**Troubleshooting:**

```bash
# 1. Verifica che agent sia running
sudo systemctl status orizon-agent  # Linux
launchctl list | grep orizon         # macOS

# 2. Check logs agent
sudo journalctl -u orizon-agent -f   # Linux
tail -f /var/log/orizon/agent.log    # macOS

# 3. Test connettività al hub
ping 46.101.189.126
telnet 46.101.189.126 2222

# 4. Restart agent
sudo systemctl restart orizon-agent  # Linux
sudo launchctl kickstart -k system/com.orizon.agent  # macOS
```

#### Q: Agent non si installa

**Linux/macOS:**
```bash
# Verifica requisiti
python3 --version  # >= 3.7
pip3 --version

# Installa manualmente dependencies
pip3 install requests websocket-client psutil

# Download agent
wget https://orizon.syneto.net/downloads/orizon_agent.py

# Run manuale
python3 orizon_agent.py --config config.json
```

**Windows:**
- Verifica Python 3.7+ installato
- Esegui PowerShell come **Amministratore**
- Disabilita antivirus temporaneamente (potrebbe bloccare)

#### Q: Metriche non si aggiornano

1. Verifica che agent sia online (status = 🟢 Online)
2. Check logs per errori
3. Verifica firewall non blocchi traffico

---

### Tunnel

#### Q: Tunnel è "Active" ma non riesco a connettermi

**Troubleshooting:**

```bash
# 1. Verifica porta remota assegnata
ssh -p <PORTA_REMOTA> -v user@46.101.189.126

# 2. Test connettività
telnet 46.101.189.126 <PORTA_REMOTA>

# 3. Check firewall locale
# Assicurati nessun firewall blocchi connessioni in uscita

# 4. Verifica servizio sul nodo remoto
# Sul nodo, verifica che SSH sia running
sudo systemctl status ssh  # Linux
```

#### Q: Tunnel si disconnette spesso

Possibili cause:
- Connessione internet instabile sul nodo
- Firewall chiude connessioni idle
- Resource limits

**Soluzione:**
1. Abilita **Auto-reconnect** (già abilitato di default)
2. Sul nodo, configura SSH keepalive:
```bash
# /etc/ssh/sshd_config
ClientAliveInterval 60
ClientAliveCountMax 3
```

#### Q: "Porta non disponibile" quando creo tunnel

Tutte le porte nel range sono occupate.

**Soluzione:**
- Chiudi tunnel non usati
- Contatta admin per aumentare range porte
- Aspetta che qualcuno chiuda tunnel

---

### ACL Rules

#### Q: Regola non funziona

**Checklist:**
1. ✅ Regola è **Enabled**?
2. ✅ Priority corretta? (regole con priority minore vengono valutate prima)
3. ✅ IP sorgente/destinazione corretti? (usa CIDR notation)
4. ✅ Porta corretta?
5. ✅ Time restrictions rispettate? (giorno/ora)

**Debug:**
- Usa **Test Regola** per vedere cosa matcha
- Check audit logs per vedere decisioni ACL
- Verifica non ci sia regola con priority inferiore che nega

#### Q: Come blocco un IP specifico?

```json
{
  "name": "Block malicious IP",
  "priority": 1,
  "action": "DENY",
  "source_ip": "198.51.100.50/32",
  "destination_ip": "0.0.0.0/0",
  "protocol": "ALL"
}
```

---

### Performance

#### Q: Dashboard lento a caricare

**Soluzioni:**
- Riduci numero nodi visualizzati (usa filtri)
- Disabilita animazioni 3D (Settings → Performance)
- Usa browser moderno (Chrome, Firefox, Safari)
- Chiudi tab non usate

#### Q: Network map 3D non si carica

**Troubleshooting:**
1. Verifica browser supporti WebGL:
   - Vai su: https://get.webgl.org/
   - Dovrebbe vedere un cubo 3D
2. Abilita hardware acceleration nel browser
3. Aggiorna driver GPU
4. Fallback: Usa vista 2D (toggle in alto a destra)

---

### Altro

#### Q: Come posso vedere i logs di debug?

1. Apri browser console (F12)
2. Vai su tab **Console**
3. Filtra per "Orizon" per vedere solo logs app

#### Q: Posso usare API programmaticamente?

Sì! API completa disponibile.

**Docs:** https://orizon.syneto.net/docs
**Swagger UI:** https://orizon.syneto.net/api/docs

**Esempio:**
```bash
# Login
curl -X POST https://orizon.syneto.net/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password"}'

# Get nodes
curl https://orizon.syneto.net/api/v1/nodes \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### Q: Chi contattare per supporto?

- **Email**: support@orizon.syneto.net
- **Slack** (interno): #orizon-ztc
- **Telefono**: +39 02 1234 5678 (solo emergenze)
- **Wiki**: https://wiki.orizon.internal/ztc

---

## 📚 Risorse Aggiuntive

### Documentazione Tecnica

- [Architecture Guide](./ARCHITECTURE.md)
- [API Reference](./API_REFERENCE.md)
- [Security Guide](./SECURITY_GUIDE.md)
- [Deployment Guide](./DEPLOYMENT_GUIDE.md)

### Video Tutorial

- 🎥 Getting Started (10 min)
- 🎥 Creating your first tunnel (5 min)
- 🎥 ACL Rules explained (15 min)
- 🎥 2FA Setup (3 min)

### Community

- **Forum**: https://community.orizon.syneto.net
- **Blog**: https://blog.orizon.syneto.net
- **GitHub**: https://github.com/orizon/ztc (issues)

---

## 🎓 Best Practices

### Sicurezza

✅ **DO:**
- Abilita 2FA per tutti gli account
- Usa password forti e uniche
- Cambia password regolarmente (ogni 3-6 mesi)
- Salva backup codes in posto sicuro
- Monitora audit logs per attività sospette
- Usa ACL rules per limitare accessi

❌ **DON'T:**
- Condividere credenziali con altri
- Usare stessa password per più account
- Disabilitare 2FA senza motivo valido
- Ignorare security alerts
- Creare regole ACL troppo permissive

### Gestione Nodi

✅ **DO:**
- Dare nomi descrittivi ai nodi
- Usare tags per organizzare
- Monitorare metriche regolarmente
- Mantenere agent aggiornato
- Configurare alerts per nodi offline

### Gestione Tunnel

✅ **DO:**
- Chiudere tunnel quando non usati
- Abilita auto-reconnect
- Monitora latency e bandwidth
- Usa SSH key-based auth (non password)

### ACL Rules

✅ **DO:**
- Usa priority per ordinare regole logicamente
- Testa regole prima di applicare
- Documenta regole con nomi descrittivi
- Review regole periodicamente
- Usa time restrictions per security addizionale

---

**Guida creata da:** Marco Lorenzi @ Syneto/Orizon
**Versione:** 1.0.0
**Ultimo aggiornamento:** Gennaio 2025
**Feedback:** documentation@orizon.syneto.net
