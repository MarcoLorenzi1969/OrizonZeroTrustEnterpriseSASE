# Hub Server Configuration Guide / Guida Configurazione Server Hub

## Version / Versione: 2.0.3
## Last Updated / Ultimo Aggiornamento: 2025-12-01

---

## Overview / Panoramica

This document describes the required configuration for Orizon Hub servers to properly handle SSH reverse tunnels from Edge nodes. It includes critical lessons learned from production debugging.

*Questo documento descrive la configurazione necessaria per i server Hub Orizon per gestire correttamente i tunnel SSH inversi dai nodi Edge. Include lezioni critiche apprese dal debug in produzione.*

---

## Architecture / Architettura

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           HUB SERVER                                     │
│                                                                          │
│  ┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐ │
│  │  SSHD Container │      │  Socat Bridge   │      │ Backend Container│ │
│  │  (Port 2222)    │──────│  (Docker GW)    │──────│  (Python/FastAPI)│ │
│  │                 │      │                 │      │                  │ │
│  │ Listens on:     │      │ 172.18.0.1:19028│      │ Connects to:     │ │
│  │ 0.0.0.0:9028    │◄────►│ → localhost:9028│◄────►│ SSH_TUNNEL_HOST  │ │
│  │ 0.0.0.0:9029    │      │ 172.18.0.1:19029│      │ :19028, :19029   │ │
│  │                 │      │ → localhost:9029│      │                  │ │
│  └─────────────────┘      └─────────────────┘      └─────────────────┘ │
│                                    ▲                                     │
│                                    │                                     │
│                              UFW Firewall                               │
│                         (Allow 172.18.0.0/16)                           │
└─────────────────────────────────────────────────────────────────────────┘
                                    ▲
                                    │ SSH Reverse Tunnel
                                    │ (-R 9028:localhost:22)
                                    │
┌─────────────────────────────────────────────────────────────────────────┐
│                          EDGE NODE (Windows/Linux)                       │
│                                                                          │
│  ┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐ │
│  │  SSH Tunnel     │      │  SSH Server     │      │  nginx/IIS      │ │
│  │  Service        │      │  (Port 22)      │      │  (Port 443)     │ │
│  └─────────────────┘      └─────────────────┘      └─────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Critical Configuration: Socat Bridge / Configurazione Critica: Bridge Socat

### The Problem / Il Problema

When SSHD handles reverse tunnels with `GatewayPorts yes`, it binds on `0.0.0.0`. Docker containers CANNOT reach `localhost` of the host, and the Docker bridge IP (172.18.0.1) is already used by SSHD.

*Quando SSHD gestisce tunnel inversi con `GatewayPorts yes`, fa bind su `0.0.0.0`. I container Docker NON POSSONO raggiungere il `localhost` dell'host, e l'IP del bridge Docker (172.18.0.1) è già usato da SSHD.*

### The Solution / La Soluzione

Use `socat` to create a bridge on alternative ports (19xxx) that forwards to the SSHD tunnel ports (9xxx).

*Usare `socat` per creare un bridge su porte alternative (19xxx) che inoltra alle porte tunnel di SSHD (9xxx).*

### Socat Bridge Service / Servizio Bridge Socat

Create `/etc/systemd/system/orizon-socat-bridge.service`:

```ini
[Unit]
Description=Orizon Socat Bridge for Docker Tunnel Access
After=docker.service network.target sshd.service
Wants=docker.service

[Service]
Type=forking
ExecStart=/bin/bash -c '\
    socat TCP-LISTEN:19028,bind=172.18.0.1,fork,reuseaddr TCP:127.0.0.1:9028 & \
    socat TCP-LISTEN:19029,bind=172.18.0.1,fork,reuseaddr TCP:127.0.0.1:9029 & \
    socat TCP-LISTEN:19128,bind=172.18.0.1,fork,reuseaddr TCP:127.0.0.1:9128 &'
ExecStop=/usr/bin/pkill -f "socat TCP-LISTEN:19"
RemainAfterExit=yes
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable orizon-socat-bridge.service
sudo systemctl start orizon-socat-bridge.service
```

---

## UFW Firewall Configuration / Configurazione Firewall UFW

**CRITICAL**: Docker containers use the Docker bridge network. UFW may block this traffic by default.

*CRITICO: I container Docker usano la rete bridge Docker. UFW potrebbe bloccare questo traffico di default.*

```bash
# Allow Docker network traffic / Permetti traffico rete Docker
sudo ufw allow from 172.18.0.0/16 to any comment "Docker network access"

# Verify / Verifica
sudo ufw status verbose
```

---

## Backend .env Configuration / Configurazione .env Backend

The `SSH_TUNNEL_HOST` must point to the Docker bridge gateway IP, NOT localhost or the public IP.

*`SSH_TUNNEL_HOST` deve puntare all'IP del gateway bridge Docker, NON a localhost o all'IP pubblico.*

```bash
# In /opt/orizon-ztc/backend/.env
SSH_TUNNEL_HOST=172.18.0.1
```

**Finding the Docker Bridge IP / Trovare l'IP Bridge Docker:**
```bash
# Method 1: From docker network
docker network inspect orizon-ztc_default --format '{{range .IPAM.Config}}{{.Gateway}}{{end}}'

# Method 2: From ip route
ip route | grep docker0
```

**After changing .env, FORCE RECREATE the container:**
```bash
cd /opt/orizon-ztc
docker compose up -d --force-recreate backend
```

> **Note**: `docker compose restart` does NOT reload environment variables!
>
> **Nota**: `docker compose restart` NON ricarica le variabili d'ambiente!

---

## Database Configuration / Configurazione Database

### application_ports Column / Colonna application_ports

Each node in the `nodes` table has an `application_ports` JSONB column that maps service types to port configurations:

```json
{
    "TERMINAL": {"local": 22, "remote": 19028},
    "HTTPS": {"local": 443, "remote": 19029}
}
```

**Important Keys / Chiavi Importanti:**
- `TERMINAL` - Used for web terminal access (SSH)
- `HTTPS` - Used for HTTPS proxy (web page access)
- ~~`SSL`~~ - **DEPRECATED** - Use `HTTPS` instead

**Update SQL / SQL di Aggiornamento:**
```sql
UPDATE nodes
SET application_ports = '{"TERMINAL": {"local": 22, "remote": 19028}, "HTTPS": {"local": 443, "remote": 19029}}'::jsonb
WHERE id = 'YOUR_NODE_ID';
```

---

## SSHD Configuration / Configurazione SSHD

### Required Settings / Impostazioni Richieste

In `/etc/ssh/sshd_config` (or container config):

```bash
GatewayPorts yes
AllowTcpForwarding yes
PermitTunnel yes
ClientAliveInterval 30
ClientAliveCountMax 3
```

After changes:
```bash
sudo systemctl restart ssh
# Or for container:
docker restart orizon-ssh-tunnel
```

---

## Verification Commands / Comandi di Verifica

### 1. Check Tunnel Ports Are Listening / Verifica Porte Tunnel in Ascolto

```bash
# Check SSHD tunnel ports
ss -tlnp | grep -E ':(90[12][89]|19)'

# Expected output:
# LISTEN 0.0.0.0:9028 (sshd)
# LISTEN 0.0.0.0:9029 (sshd)
# LISTEN 172.18.0.1:19028 (socat)
# LISTEN 172.18.0.1:19029 (socat)
```

### 2. Test Backend Container Connectivity / Test Connettività Container Backend

```bash
# Get backend container name
BACKEND=$(docker ps --format '{{.Names}}' | grep -i backend | head -1)

# Test SSH tunnel port
docker exec $BACKEND python3 -c "
import socket
s = socket.socket()
s.settimeout(3)
s.connect(('172.18.0.1', 19028))
print('Banner:', s.recv(100).decode()[:50])
s.close()
"

# Test HTTPS tunnel port
docker exec $BACKEND python3 -c "
import socket, ssl
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
s = socket.create_connection(('172.18.0.1', 19029), timeout=5)
ss = ctx.wrap_socket(s)
ss.send(b'GET / HTTP/1.0\r\nHost: localhost\r\n\r\n')
print('Response:', ss.recv(100).decode()[:50])
"
```

### 3. Verify Environment Variables / Verifica Variabili Ambiente

```bash
docker exec $BACKEND env | grep SSH_TUNNEL
# Should show: SSH_TUNNEL_HOST=172.18.0.1
```

---

## Common Issues / Problemi Comuni

### Issue: "SSH connection error: [Errno 111] Connection refused"

**Cause / Causa**: Backend cannot reach tunnel port

**Solutions / Soluzioni**:
1. Check socat bridge is running: `ps aux | grep socat`
2. Check UFW allows Docker: `sudo ufw status`
3. Verify SSH_TUNNEL_HOST: `docker exec backend env | grep SSH_TUNNEL`
4. Force recreate after .env change: `docker compose up -d --force-recreate backend`

### Issue: "HTTPS service not configured for this node"

**Cause / Causa**: Database has wrong key (`SSL` instead of `HTTPS`)

**Solution / Soluzione**:
```sql
UPDATE nodes SET application_ports =
  jsonb_set(application_ports, '{HTTPS}', application_ports->'SSL')
  - 'SSL'
WHERE application_ports ? 'SSL';
```

### Issue: Tunnel connects but web terminal doesn't work

**Cause / Causa**: SSH_TUNNEL_HOST pointing to wrong IP (e.g., 172.17.0.1 instead of 172.18.0.1)

**Solution / Soluzione**:
1. Find correct Docker bridge gateway: `docker network inspect orizon-ztc_default`
2. Update backend/.env
3. **Force recreate** container (restart is not enough)

---

## Production Servers / Server di Produzione

| Server | IP | Role | Docker Bridge |
|--------|-----|------|---------------|
| Hub1 | 139.59.149.48 | Primary Hub | 172.18.0.1 |
| Hub2 | 68.183.219.222 | Secondary Hub | 172.18.0.1 (verify) |

---

## Quick Setup Checklist / Checklist Rapida Setup

- [ ] SSHD configured with GatewayPorts yes
- [ ] UFW allows 172.18.0.0/16
- [ ] socat bridge service installed and running
- [ ] SSH_TUNNEL_HOST set to Docker bridge IP (172.18.0.1)
- [ ] Backend container force-recreated after .env changes
- [ ] Database application_ports uses "HTTPS" key (not "SSL")
- [ ] Tunnel ports verified from container

---

*Document generated from production debugging session on 2025-12-01*
