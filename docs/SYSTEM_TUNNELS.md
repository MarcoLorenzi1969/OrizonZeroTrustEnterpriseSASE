# System Tunnels - Orizon Zero Trust Connect

## Panoramica / Overview

I System Tunnels sono tunnel SSH persistenti che ogni nodo edge stabilisce automaticamente con l'Hub centrale. Questi tunnel sono fondamentali per il funzionamento della piattaforma e permettono l'accesso remoto sicuro ai nodi.

*System Tunnels are persistent SSH tunnels that each edge node automatically establishes with the central Hub. These tunnels are essential for the platform's operation and enable secure remote access to nodes.*

---

## Architettura / Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              HUB SERVER                                       │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                     SSH Tunnel Server (porta 2222)                       │ │
│  │                                                                          │ │
│  │   ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐       │ │
│  │   │  Node A         │   │  Node B         │   │  Node C         │       │ │
│  │   │  System: 9100   │   │  System: 9200   │   │  System: 9300   │       │ │
│  │   │  Term: 9101     │   │  Term: 9201     │   │  Term: 9301     │       │ │
│  │   │  HTTPS: 9102    │   │  HTTPS: 9202    │   │  HTTPS: 9302    │       │ │
│  │   └─────────────────┘   └─────────────────┘   └─────────────────┘       │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘
                │                    │                    │
                │ SSH Reverse Tunnel │ SSH Reverse Tunnel │ SSH Reverse Tunnel
                │ (autossh)          │ (autossh)          │ (autossh)
                ▼                    ▼                    ▼
┌───────────────────┐   ┌───────────────────┐   ┌───────────────────┐
│    EDGE NODE A    │   │    EDGE NODE B    │   │    EDGE NODE C    │
│   (Linux/Windows) │   │   (Linux/Windows) │   │   (Linux/Windows) │
│                   │   │                   │   │                   │
│   SSH: 22         │   │   SSH: 22         │   │   SSH: 22         │
│   HTTPS: 443      │   │   HTTPS: 443      │   │   HTTPS: 443      │
└───────────────────┘   └───────────────────┘   └───────────────────┘
```

---

## Tipi di Tunnel / Tunnel Types

### 1. System Tunnel (Tunnel di Sistema)

- **Porta locale**: 22 (SSH)
- **Scopo**: Accesso SSH al terminale del nodo
- **Uso**: Gestione remota, comandi, file transfer

### 2. Terminal Tunnel (Tunnel Terminale)

- **Porta locale**: 22 (SSH) - stesso del System
- **Scopo**: Sessioni terminale web via WebSocket
- **Uso**: Accesso browser-based al terminale

### 3. HTTPS Tunnel

- **Porta locale**: 443 (HTTPS)
- **Scopo**: Proxy HTTPS verso servizi web del nodo
- **Uso**: Accesso a pagine di stato, applicazioni web interne

---

## Configurazione Hardened Keep-Alive

I tunnel utilizzano una configurazione hardened per garantire connessioni stabili e veloci riconnessioni:

*Tunnels use a hardened configuration to ensure stable connections and fast reconnections:*

```bash
# Parametri SSH ottimizzati / Optimized SSH parameters
ServerAliveInterval=15      # Ping ogni 15 secondi / Ping every 15 seconds
ServerAliveCountMax=3       # Max 3 ping falliti / Max 3 failed pings
ExitOnForwardFailure=yes    # Esci se il forward fallisce / Exit if forward fails
StrictHostKeyChecking=no    # Skip verifica host (interno) / Skip host verification (internal)
BatchMode=yes               # Nessun prompt interattivo / No interactive prompts
```

### Autossh Configuration

```bash
AUTOSSH_GATETIME=0          # Nessun delay iniziale / No initial delay
AUTOSSH_POLL=60             # Check connessione ogni 60s / Check connection every 60s
```

### Timeout Detection

- **Rilevamento disconnessione**: 45 secondi (15s x 3)
- **Riconnessione automatica**: Immediata tramite autossh
- **Massimo downtime**: ~50 secondi

---

## Gestione Porte / Port Management

Ogni nodo riceve porte univoche calcolate dall'Hub:

*Each node receives unique ports calculated by the Hub:*

| Parametro | Formula | Esempio |
|-----------|---------|---------|
| Base Port | `9000 + (node_index * 100)` | 9100, 9200, 9300... |
| System Tunnel | `base_port + 0` | 9100 |
| Terminal Tunnel | `base_port + 1` | 9101 |
| HTTPS Tunnel | `base_port + 2` | 9102 |

### Esempio Configurazione / Configuration Example

```json
{
  "node_id": "d637330a-4b5b-46d5-b8ab-41d19de9d8e4",
  "node_name": "Windows11-Edge",
  "tunnels": {
    "system": {
      "local_port": 22,
      "remote_port": 9128,
      "status": "online"
    },
    "terminal": {
      "local_port": 22,
      "remote_port": 9129,
      "status": "online"
    },
    "https": {
      "local_port": 443,
      "remote_port": 9130,
      "status": "online"
    }
  }
}
```

---

## Flag is_system / is_system Flag

I System Tunnels sono identificati dal flag `is_system=true` nel database:

*System Tunnels are identified by the `is_system=true` flag in the database:*

```python
class Tunnel(Base):
    __tablename__ = "tunnels"

    id = Column(UUID, primary_key=True)
    node_id = Column(UUID, ForeignKey("nodes.id"))
    name = Column(String)
    local_port = Column(Integer)
    remote_port = Column(Integer)
    tunnel_type = Column(String)  # 'ssh', 'https', 'rdp', 'vnc'
    is_system = Column(Boolean, default=False)  # True per system tunnels
    status = Column(String, default="pending")
```

### Caratteristiche is_system=true

- **Non eliminabili**: Non possono essere cancellati dall'utente
- **Auto-creati**: Generati automaticamente all'installazione dell'agent
- **Persistenti**: Sempre attivi quando il nodo è online
- **Dashboard**: Visualizzati con badge "System" nella dashboard

---

## Dashboard Visualization

La dashboard mostra i System Tunnels con stile distintivo:

*The dashboard displays System Tunnels with distinctive styling:*

```html
<!-- Badge System Tunnel -->
<span class="badge badge-system">
  <span class="badge-icon">SYSTEM</span>
</span>

<!-- Stile CSS -->
<style>
.badge-system {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: bold;
}
</style>
```

---

## Monitoraggio / Monitoring

### API Endpoints

```bash
# Lista tunnel di un nodo / List node tunnels
GET /api/v1/nodes/{node_id}/tunnels

# Dashboard tunnel attivi / Active tunnels dashboard
GET /api/v1/tunnels/dashboard

# Stato specifico tunnel / Specific tunnel status
GET /api/v1/tunnels/{tunnel_id}/status
```

### Metriche Heartbeat / Heartbeat Metrics

Ogni 30 secondi, l'agent invia:

```json
{
  "agent_token": "agt_xxx...",
  "timestamp": "2025-11-30T16:14:17Z",
  "tunnels_status": {
    "system": "connected",
    "terminal": "connected",
    "https": "connected"
  },
  "tunnel_latency_ms": 45
}
```

---

## Troubleshooting

### Tunnel Non Si Connette / Tunnel Won't Connect

1. **Verifica servizio SSH sull'Hub**:
   ```bash
   systemctl status sshd
   ss -tln | grep 2222
   ```

2. **Verifica chiave SSH del nodo**:
   ```bash
   # Linux
   cat /opt/orizon-agent/.ssh/id_ed25519.pub

   # Windows
   type C:\ProgramData\Orizon\.ssh\id_ed25519.pub
   ```

3. **Test connessione manuale**:
   ```bash
   ssh -v -p 2222 -i /opt/orizon-agent/.ssh/id_ed25519 \
     NODE_ID@HUB_IP
   ```

### Disconnessioni Frequenti / Frequent Disconnections

1. **Verifica parametri keep-alive**:
   ```bash
   # Nel servizio systemd
   grep ServerAliveInterval /etc/systemd/system/orizon-tunnel*.service
   ```

2. **Controlla logs autossh**:
   ```bash
   journalctl -u orizon-tunnel-system -n 50
   ```

3. **Verifica firewall**:
   ```bash
   # Sull'Hub
   ufw status | grep 2222
   ```

---

## Sicurezza / Security

### Autenticazione

- **Chiave ED25519**: Ogni nodo genera una chiave univoca
- **Authorized Keys**: L'Hub autorizza solo chiavi registrate
- **No Password**: Autenticazione esclusivamente via chiave

### Hardening

- **Bind localhost**: I tunnel fanno bind solo su localhost dell'Hub
- **Port Isolation**: Ogni nodo ha porte dedicate
- **No Shell**: L'utente SSH del tunnel non ha shell interattiva

### Best Practices

1. **Rotazione chiavi**: Rigenerare chiavi ogni 12 mesi
2. **Monitoraggio accessi**: Audit log su ogni connessione
3. **Firewall restrittivo**: Solo porta 2222 aperta per tunnels

---

## Riferimenti / References

- [Architecture](ARCHITECTURE.md) - Architettura generale
- [Security](SECURITY.md) - Configurazioni di sicurezza
- [Windows Agent](WINDOWS_AGENT.md) - Installazione su Windows
- [API Reference](API_REFERENCE.md) - Documentazione API

---

*Ultimo aggiornamento / Last updated: 30 Novembre 2025*
