# Orizon Zero Trust Connect - Documentation Index
# Indice Documentazione

## Version / Versione: 2.1.0
## Last Updated / Ultimo Aggiornamento: 2025-12-01

---

## Overview / Panoramica

**EN**: Orizon Zero Trust Connect is an enterprise-grade SD-WAN platform implementing Zero Trust security principles. It enables secure remote access to nodes (servers, workstations) through reverse SSH tunnels with comprehensive role-based access control and multi-hub redundancy.

**IT**: Orizon Zero Trust Connect è una piattaforma SD-WAN enterprise che implementa i principi di sicurezza Zero Trust. Consente l'accesso remoto sicuro ai nodi (server, workstation) attraverso tunnel SSH inversi con controllo degli accessi basato sui ruoli e ridondanza multi-hub.

---

## Quick Links / Link Rapidi

| Document / Documento | Description / Descrizione |
|---------------------|---------------------------|
| [Architecture](ARCHITECTURE.md) | System architecture / Architettura sistema |
| [API Reference](API_REFERENCE.md) | REST API documentation / Documentazione API REST |
| [System Tunnels](SYSTEM_TUNNELS.md) | System tunnels guide / Guida tunnel di sistema |
| [Windows Agent](WINDOWS_AGENT.md) | Windows agent installation / Installazione agent Windows |
| [Hub Configuration](HUB_CONFIGURATION.md) | **Hub server setup & tunnel bridge / Configurazione Hub e bridge tunnel** |
| [User Hierarchy](USER_HIERARCHY.md) | 4-level RBAC hierarchy / Gerarchia RBAC a 4 livelli |
| [Deployment](DEPLOYMENT.md) | Production deployment / Deploy in produzione |
| [Security](SECURITY.md) | Security configuration / Configurazione sicurezza |
| [Development](DEVELOPMENT.md) | Developer guide / Guida sviluppatori |
| [User Guide](USER_GUIDE.md) | End-user manual / Manuale utente finale |
| [Troubleshooting](TROUBLESHOOTING.md) | Common issues / Problemi comuni |
| [Installation Packages](../packages/README.md) | **Edge agent packages / Pacchetti agent Edge** |

---

## Getting Started / Per Iniziare

### For Administrators / Per Amministratori

1. **First Login / Primo Accesso**: Access the system at `https://hub.orizon.one` with SUPERUSER credentials
2. **Create Users / Crea Utenti**: Navigate to Users → Create User
3. **Create Groups / Crea Gruppi**: Navigate to Groups → Create Group
4. **Add Nodes / Aggiungi Nodi**: Navigate to Nodes → Create Node
5. **Install Agent / Installa Agent**: Download package from Nodes page

### For End Users / Per Utenti Finali

1. **Login / Accedi**: Access `https://hub.orizon.one` with your credentials
2. **View Nodes / Visualizza Nodi**: Navigate to Nodes to see assigned servers
3. **Connect / Connetti**: Click on a node to establish a connection

---

## System Requirements / Requisiti di Sistema

### Hub Server

| Component | Requirement / Requisito |
|-----------|------------------------|
| OS | Ubuntu 22.04 or 24.04 LTS |
| CPU | 2+ cores / 2+ core |
| RAM | 4GB+ |
| Disk | 40GB+ |
| Docker | 24.x+ |
| Nginx | 1.24+ |

### Edge Nodes / Nodi Edge

| Platform | Requirements / Requisiti |
|----------|-------------------------|
| Linux | Debian 10+, Ubuntu 20.04+, RHEL 8+, Fedora 35+ |
| macOS | 12+ (Monterey, Ventura, Sonoma) |
| Windows | 10/11, Server 2019/2022/2025 |
| Network | Outbound port 2222 (SSH tunnel) |

---

## Key Features / Funzionalità Principali

### Zero Trust Security / Sicurezza Zero Trust

- **Never trust, always verify** / Mai fidarsi, sempre verificare
- **Least privilege access** / Accesso con privilegi minimi
- **End-to-end encryption (TLS 1.2/1.3)** / Crittografia end-to-end
- **JWT-based authentication** / Autenticazione basata su JWT

### Multi-Hub Architecture / Architettura Multi-Hub

```
┌─────────────────┐     ┌─────────────────┐
│   Hub 1         │     │   Hub 2         │
│ (Primary)       │     │ (Secondary)     │
│ 139.59.149.48   │     │ 68.183.219.222  │
└────────┬────────┘     └────────┬────────┘
         │                       │
         └───────────┬───────────┘
                     │
              ┌──────▼──────┐
              │  Edge Node  │
              │  (3 tunnels │
              │  per hub)   │
              └─────────────┘
```

### Hierarchical Access Control / Controllo Accessi Gerarchico

```
SUPERUSER (Platform Owner / Proprietario Piattaforma)
    └── SUPER_ADMIN (Distributors / Distributori)
            └── ADMIN (Resellers / Rivenditori)
                    └── USER (End Clients / Clienti Finali)
```

### Group-Based Node Access / Accesso Nodi Basato su Gruppi

- Users access nodes through group membership / Gli utenti accedono ai nodi tramite appartenenza ai gruppi
- Granular permissions per node (SSH, RDP, VNC, SSL Tunnel) / Permessi granulari per nodo
- Flexible group management / Gestione flessibile dei gruppi

---

## Architecture Overview / Panoramica Architettura

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Web Browser   │────▶│  Nginx (HTTPS)  │────▶│  FastAPI Backend│
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                         │
                         ┌───────────────────────────────┼───────────────────────────────┐
                         ▼                               ▼                               ▼
                 ┌───────────────┐             ┌───────────────┐             ┌───────────────┐
                 │  PostgreSQL   │             │     Redis     │             │    MongoDB    │
                 │  (Data Store) │             │    (Cache)    │             │    (Logs)     │
                 └───────────────┘             └───────────────┘             └───────────────┘

┌─────────────────┐
│   Edge Nodes    │────▶ SSH Tunnel Server (Port 2222) ────▶ 3 Reverse Tunnels per Hub
│                 │      - System Tunnel (metrics collection)
│                 │      - Terminal Tunnel (SSH/shell access)
│                 │      - HTTPS Tunnel (web services proxy)
└─────────────────┘
```

---

## Installation Packages / Pacchetti di Installazione

### Quick Start / Avvio Rapido

| Platform / Piattaforma | Command / Comando |
|------------------------|-------------------|
| **Debian/Ubuntu** | `sudo dpkg -i orizon-agent_2.1.0_all.deb && sudo orizon-setup` |
| **RedHat/Fedora** | `sudo rpm -i orizon-agent-2.1.0-1.noarch.rpm && sudo orizon-setup` |
| **macOS** | `sudo bash orizon-installer.sh` |
| **Windows** | Run `orizon-installer.ps1` as Administrator |

See [Installation Packages](../packages/README.md) for detailed instructions.

---

## API Quick Reference / Riferimento Rapido API

### Authentication / Autenticazione

```bash
# Login
curl -X POST https://hub.orizon.one/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password"}'

# Use token / Usa token
curl https://hub.orizon.one/api/v1/users \
  -H "Authorization: Bearer <access_token>"
```

### Common Endpoints / Endpoint Comuni

| Method | Endpoint | Description / Descrizione |
|--------|----------|--------------------------|
| POST | `/auth/login` | Authenticate user / Autentica utente |
| GET | `/users` | List visible users / Lista utenti visibili |
| POST | `/users` | Create new user / Crea nuovo utente |
| GET | `/nodes` | List accessible nodes / Lista nodi accessibili |
| POST | `/nodes` | Create new node / Crea nuovo nodo |
| GET | `/groups` | List groups / Lista gruppi |
| POST | `/groups` | Create new group / Crea nuovo gruppo |
| GET | `/tunnels/dashboard` | Tunnel dashboard data / Dati dashboard tunnel |

See [API Reference](API_REFERENCE.md) for complete documentation.

---

## Production Servers / Server di Produzione

| Server | IP | Role / Ruolo | Status / Stato |
|--------|-----|-------------|----------------|
| Hub 1 | 139.59.149.48 | Primary Hub / Hub Primario | Active / Attivo |
| Hub 2 | 68.183.219.222 | Secondary Hub / Hub Secondario | Active / Attivo |

---

## Support & Contact / Supporto e Contatti

- **Documentation / Documentazione**: This folder (`/docs`)
- **API Docs**: `https://hub.orizon.one/docs` (Swagger UI)
- **Email**: support@orizon.one
- **Website**: https://orizon.one

---

## Version History / Cronologia Versioni

| Version | Date / Data | Changes / Modifiche |
|---------|-------------|---------------------|
| 2.1.0 | December 2025 | Multi-hub redundancy, installation packages, socat bridge / Ridondanza multi-hub, pacchetti installazione, bridge socat |
| 2.0.2 | November 2025 | System tunnels, Windows agent hardening / Tunnel di sistema, hardening agent Windows |
| 2.0.0 | November 2025 | Complete rewrite with 4-level hierarchy / Riscrittura completa con gerarchia a 4 livelli |
| 1.0.0 | October 2025 | Initial release / Rilascio iniziale |

---

## License / Licenza

Proprietary - Orizon / Syneto

---

*Last updated / Ultimo aggiornamento: 2025-12-01*
