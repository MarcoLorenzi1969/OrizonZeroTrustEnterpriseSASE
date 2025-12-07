# Infrastructure Documentation / Documentazione Infrastruttura

**Orizon Zero Trust Enterprise SASE v3.0.1**

---

## System Hierarchy / Gerarchia Sistema

```
┌─────────────────────────────────────────────────────────────────────┐
│                    LOCAL REPOSITORY (MASTER)                        │
│                 Source of truth for all code                        │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
              ▼               ▼               ▼
       ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
       │   GitHub    │ │   HUB 1     │ │   HUB 2     │
       │  (Backup)   │ │ (Primary)   │ │ (Secondary) │
       └─────────────┘ └──────┬──────┘ └──────┬──────┘
                              │               │
                      ┌───────┴───────────────┴───────┐
                      │      EDGE NODES               │
                      │  (Windows, Linux, macOS)      │
                      └───────────────────────────────┘
```

---

## Environment Details / Dettagli Ambienti

### 1. Local Repository (Master)

| Property | Value |
|----------|-------|
| **Role** | Master repository, source of truth |
| **Platform** | macOS Sequoia 15.x |
| **Path** | `/Users/marcolorenzi/Windsurf/OrizonZeroTrustEnterpriseSASE` |
| **Purpose** | Development, testing, deployment source |

### 2. GitHub Repository

| Property | Value |
|----------|-------|
| **URL** | https://github.com/MarcoLorenzi1969/OrizonZeroTrustEnterpriseSASE |
| **Branch** | main |
| **Role** | Version control, backup, collaboration |

### 3. HUB 1 - Primary Production

| Property | Value |
|----------|-------|
| **Name** | OrizonZeroTrust1 |
| **IP** | 139.59.149.48 |
| **OS** | Ubuntu 24.04 LTS |
| **Role** | Primary production hub |
| **Provider** | DigitalOcean |

### 4. HUB 2 - Secondary Production

| Property | Value |
|----------|-------|
| **Name** | OrizonZeroTrust2 |
| **IP** | 68.183.219.222 |
| **OS** | Ubuntu 24.04 LTS |
| **Role** | Secondary production hub |
| **Provider** | DigitalOcean |

### 5. Edge Windows 11 (Test)

| Property | Value |
|----------|-------|
| **IP** | 10.211.55.22 |
| **OS** | Windows 11 Pro |
| **Type** | Parallels VM |
| **Purpose** | Windows agent testing |

### 6. Edge Ubuntu (Test)

| Property | Value |
|----------|-------|
| **IP** | 10.211.55.21 |
| **OS** | Ubuntu 22.04 |
| **Type** | Parallels VM |
| **Purpose** | Linux agent testing |

---

## Network Ports / Porte di Rete

### Hub Services

| Port | Service | Protocol | Description |
|------|---------|----------|-------------|
| 22 | SSH | TCP | System administration |
| 80 | HTTP | TCP | Redirect to HTTPS |
| 443 | HTTPS | TCP | Web interface & API |
| 2222 | SSH Tunnel | TCP | Edge node reverse tunnels |
| 3000 | Script Gen | TCP | Provisioning scripts |
| 5432 | PostgreSQL | TCP | Database (internal) |
| 6379 | Redis | TCP | Cache (internal) |
| 8000 | Backend | TCP | FastAPI (internal) |
| 27017 | MongoDB | TCP | Logs (internal) |

### Tunnel Port Ranges

| Range | Purpose |
|-------|---------|
| 20000-29999 | Application tunnels (SSH, RDP, HTTP) |
| 30000-39999 | Service tunnels (heartbeat, metrics) |
| 40000-49999 | Reserved for future use |

---

## Credentials Management / Gestione Credenziali

### Security Policy

1. **Credentials are stored ONLY in `.env.local`** on the local repository
2. **`.env.local` is in `.gitignore`** - never pushed to GitHub
3. **Hubs use environment variables** set during deployment
4. **Edge nodes use SSH key authentication** - no passwords stored

### Credential Locations

| System | Credential Storage |
|--------|-------------------|
| Local Repository | `.env.local` (git ignored) |
| GitHub | No credentials |
| HUB 1 | `/opt/orizon-ztc/.env` (not in repo) |
| HUB 2 | `/opt/orizon-ztc/.env` (not in repo) |
| Edge Nodes | SSH keys in `/opt/orizon-agent/.ssh/` |

---

## Deployment Workflow / Flusso Deployment

### From Local to HUB

```bash
# 1. Test locally
docker compose up -d
npm run build

# 2. Push to GitHub
git add . && git commit -m "Update" && git push

# 3. Deploy to HUB
rsync -avz --exclude 'node_modules' --exclude '.git' \
  --exclude '.env.local' --exclude 'backup_code' \
  ./ user@HUB_IP:/opt/orizon-ztc/

# 4. Rebuild on HUB
ssh user@HUB_IP "cd /opt/orizon-ztc && \
  docker compose build backend && \
  docker compose up -d && \
  cd frontend && npm run build && \
  sudo rsync -av dist/ /var/www/html/"
```

### Edge Node Registration

1. **Generate provisioning script** via web UI
2. **Download script** on edge node
3. **Execute script** with sudo privileges
4. **Script automatically**:
   - Generates SSH key pair
   - Registers public key on hub
   - Creates systemd service
   - Establishes reverse tunnel

---

## Backup Strategy / Strategia Backup

| Component | Backup Location | Frequency |
|-----------|----------------|-----------|
| Source Code | GitHub | Every commit |
| Database | `/opt/orizon-ztc/backups/` | Daily |
| Configuration | Local `.env.local` | Manual |
| Old Code | `backup_code/` | As needed |
| Old Docs | `backup_code/docs_archive/` | As needed |

---

## Monitoring / Monitoraggio

### Health Checks

```bash
# Backend health
curl https://HUB_IP/health

# Docker services
docker compose ps

# Nginx status
sudo systemctl status nginx

# Active tunnels
ss -tln | grep -E '2[0-9]{4}'
```

### Logs

```bash
# Backend logs
docker compose logs backend -f

# Nginx logs
tail -f /var/log/nginx/orizon_*.log

# System logs
journalctl -u orizon-* -f
```

---

## Security Checklist / Checklist Sicurezza

- [x] JWT authentication with expiration
- [x] HTTPS/TLS encryption
- [x] Role-based access control (5 levels)
- [x] Reverse tunnel architecture (no inbound ports on edges)
- [x] Credentials isolated in `.env.local`
- [x] SSH key authentication for edges
- [ ] Rate limiting (configured, activate as needed)
- [ ] 2FA (available, enable per user)
- [ ] Audit logging (MongoDB)

---

© 2025 Syneto / Orizon - All Rights Reserved
