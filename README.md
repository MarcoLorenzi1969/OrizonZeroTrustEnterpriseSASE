# Orizon Zero Trust Enterprise SASE

**Enterprise-Grade Zero Trust Network Access with Multi-Hub Architecture**

[![Version](https://img.shields.io/badge/version-3.0.1-blue.svg)](./CHANGELOG.md)
[![License](https://img.shields.io/badge/license-Proprietary-red.svg)]()
[![Python](https://img.shields.io/badge/python-3.11+-green.svg)]()
[![React](https://img.shields.io/badge/react-18.x-61dafb.svg)]()
[![FastAPI](https://img.shields.io/badge/fastapi-0.104+-009688.svg)]()

---

## What's New in v3.0.1

**Sync Release**: Complete environment synchronization and enterprise hardening

- **Multi-Hub Architecture** - Redundant hub infrastructure (HUB 1 + HUB 2)
- **Node Hardening Analysis** - Security posture assessment for all edge nodes
- **RDP Direct Connections** - Native Remote Desktop Protocol support
- **GeoLite2 Geolocation** - Local IP geolocation without external APIs
- **SSO Integration** - Single Sign-On authentication support
- **Enhanced Installation Scripts** - Platform-specific hardening wizard
- **Complete Nginx Configuration** - Production-ready reverse proxy setup

**[See Full Architecture Documentation](./ARCHITECTURE.md)**

---

## Features

### Core Capabilities

| Feature | Description |
|---------|-------------|
| **Zero Trust Architecture** | No implicit trust, verify every connection |
| **Multi-Hub Support** | Redundant infrastructure for high availability |
| **Reverse SSH Tunnels** | Secure connectivity without inbound firewall rules |
| **Web Terminal** | Browser-based SSH access via xterm.js |
| **RDP Direct** | Native Remote Desktop Protocol connections |
| **Role-Based Access Control** | 5-level hierarchical permission system |
| **Multi-Tenant Support** | Isolated environments per organization |
| **Two-Factor Authentication** | TOTP-based 2FA security |
| **SSO Integration** | Single Sign-On capabilities |
| **Real-time Monitoring** | Node metrics, status, and geolocation |
| **Hardening Analysis** | Firewall, antivirus, ports, security modules |

### Supported Platforms

| Platform | Agent | Hardening Scanner |
|----------|:-----:|:-----------------:|
| Ubuntu/Debian | ✅ | ✅ |
| RHEL/CentOS | ✅ | ✅ |
| macOS (Intel/Apple Silicon) | ✅ | ✅ |
| Windows 10/11 | ✅ | ✅ |

---

## Architecture

```
                                ┌─────────────────┐
                                │     GitHub      │
                                │   Repository    │
                                └────────┬────────┘
                                         │
                ┌────────────────────────┼────────────────────────┐
                │                        │                        │
                ▼                        ▼                        ▼
       ┌───────────────┐        ┌───────────────┐        ┌───────────────┐
       │  LOCAL DEV    │        │    HUB 1      │        │    HUB 2      │
       │   (macOS)     │        │139.59.149.48  │        │68.183.219.222 │
       └───────────────┘        └───────┬───────┘        └───────┬───────┘
                                        │                        │
                                        │    Reverse Tunnels     │
                                ┌───────┴────────────────────────┴───────┐
                                │                                        │
                                ▼                                        ▼
                       ┌─────────────────┐                      ┌─────────────────┐
                       │  Windows Edge   │                      │   Linux Edge    │
                       │    Nodes        │                      │     Nodes       │
                       └─────────────────┘                      └─────────────────┘
```

### Technology Stack

| Layer | Technology | Version |
|-------|------------|---------|
| Backend | FastAPI + Python | 3.11+ |
| Frontend | React + Vite | 18.x / 5.x |
| Database | PostgreSQL | 15 |
| Cache | Redis | 7 |
| Logs | MongoDB | 7 |
| Containers | Docker Compose | 24.x |
| Proxy | Nginx | 1.24+ |
| SSH | OpenSSH | 9.x |

---

## Quick Start

### Prerequisites

- Ubuntu 22.04/24.04 LTS (for hub servers)
- Docker 24.x + Docker Compose v2
- Public IP address
- Ports: 80, 443, 2222, 3000

### 1. Clone Repository

```bash
git clone https://github.com/MarcoLorenzi1969/OrizonZeroTrustEnterpriseSASE.git
cd OrizonZeroTrustEnterpriseSASE
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your settings
nano .env
```

### 3. Start Services

```bash
docker compose up -d
```

### 4. Install Nginx

```bash
cd nginx
chmod +x install.sh
sudo ./install.sh YOUR_SERVER_IP
```

### 5. Deploy Frontend

```bash
cd frontend
npm install
npm run build
sudo rsync -av dist/ /var/www/html/
```

### 6. Access Dashboard

```
https://YOUR_SERVER_IP
Default: marco@syneto.eu / Syneto2601AA
```

---

## Project Structure

```
OrizonZeroTrustEnterpriseSASE/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── api/v1/endpoints/  # 15 API modules
│   │   ├── models/            # 9 SQLAlchemy models
│   │   ├── schemas/           # 7 Pydantic schemas
│   │   ├── services/          # 14 business services
│   │   └── core/              # 7 core components
│   ├── alembic/               # Database migrations
│   └── Dockerfile
├── frontend/                # React/Vite frontend
│   ├── src/
│   │   ├── pages/             # 8 page components
│   │   ├── components/        # 4 UI components
│   │   └── stores/            # Zustand state
│   └── package.json
├── nginx/                   # Nginx configuration
│   ├── orizon.conf            # Main site config
│   ├── install.sh             # Auto installer
│   ├── conf.d/                # Additional configs
│   └── ssl/                   # SSL generator
├── script-generator/        # Node.js provisioning
├── ssh-tunnel-server/       # SSH tunnel Docker
├── packages/                # Multi-platform agents
├── deploy/                  # Deployment scripts
├── docs/                    # Documentation
├── docker-compose.yml       # Service orchestration
├── ARCHITECTURE.md          # Architecture docs
├── ARCHITECTURE_EN.html     # HTML docs (English)
└── ARCHITECTURE_IT.html     # HTML docs (Italian)
```

---

## API Endpoints

### Authentication
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/auth/login` | POST | JWT authentication |
| `/api/v1/auth/refresh` | POST | Token refresh |
| `/api/v1/auth/logout` | POST | Session logout |

### Nodes
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/nodes` | GET | List all nodes |
| `/api/v1/nodes/{id}` | GET | Get node details |
| `/api/v1/nodes/{id}/hardening` | GET | Get hardening info |
| `/api/v1/nodes/{id}/metrics` | POST | Update metrics |

### Tunnels
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/tunnels/dashboard` | GET | Active tunnels |
| `/api/v1/tunnels/{id}` | GET | Tunnel details |

### Users
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/users` | GET | List users |
| `/api/v1/users` | POST | Create user |
| `/api/v1/users/{id}` | PUT | Update user |

**Full API Documentation**: `https://YOUR_SERVER/docs`

---

## Role Hierarchy

```
SUPERUSER (System Owner)
    └── SUPER_ADMIN (Platform Admin)
            └── ADMIN (Tenant Admin)
                    └── USER (Standard User)
                            └── VIEWER (Read-Only)
```

| Role | Create Users | Manage Nodes | View All | System Config |
|------|:------------:|:------------:|:--------:|:-------------:|
| SUPERUSER | ✅ All | ✅ All | ✅ | ✅ |
| SUPER_ADMIN | ✅ Admin- | ✅ Assigned | ✅ | ❌ |
| ADMIN | ✅ User- | ✅ Group | Tenant | ❌ |
| USER | ❌ | ❌ | Assigned | ❌ |
| VIEWER | ❌ | ❌ | Assigned | ❌ |

---

## Node Hardening

The platform collects security information from each edge node:

| Field | Linux | Windows | macOS |
|-------|:-----:|:-------:|:-----:|
| Firewall Status | UFW/iptables | Windows Firewall | pf |
| Antivirus | ClamAV | Defender | XProtect |
| Open Ports | ss/netstat | netstat | lsof |
| Security Modules | SELinux/AppArmor | - | Gatekeeper |
| SSH Config | sshd_config | OpenSSH | sshd_config |
| Pending Updates | apt/yum | Windows Update | softwareupdate |

---

## Deployment Environments

| Environment | IP | Purpose | Status |
|-------------|-----|---------|:------:|
| LOCAL | macOS | Development | ✅ |
| HUB 1 | 139.59.149.48 | Production Primary | ✅ |
| HUB 2 | 68.183.219.222 | Production Secondary | ✅ |
| GitHub | Cloud | Source Control | ✅ |

---

## Documentation

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Complete architecture documentation |
| [ARCHITECTURE_EN.html](./ARCHITECTURE_EN.html) | Interactive HTML docs (English) |
| [ARCHITECTURE_IT.html](./ARCHITECTURE_IT.html) | Interactive HTML docs (Italian) |
| [docs/DEPLOYMENT.md](./docs/DEPLOYMENT.md) | Deployment guide |
| [nginx/README.md](./nginx/README.md) | Nginx configuration guide |

---

## Version History

| Version | Date | Highlights |
|---------|------|------------|
| 3.0.1 | 2025-12-07 | Environment sync, hardening schema, Nginx config |
| 3.0.0 | 2025-12-06 | Enhanced installation scripts with hardening wizard |
| 2.1.1 | 2025-12-04 | Enterprise hardening, SSO endpoint |
| 2.1.0 | 2025-12-03 | Multi-hub packages, bilingual docs |
| 2.0.0 | 2025-11-30 | Initial SASE release |

---

## Security

### Implemented
- JWT authentication with RS256/HS256
- TOTP-based two-factor authentication
- Role-based access control (RBAC)
- Reverse tunnel architecture (no inbound ports on edges)
- SSL/TLS encryption
- Audit logging

### Recommendations
- Change default credentials immediately
- Use Let's Encrypt for production SSL
- Enable rate limiting in Nginx
- Regular security updates
- Rotate SSH keys periodically

---

## Support

- **Documentation**: See `docs/` directory
- **Issues**: [GitHub Issues](https://github.com/MarcoLorenzi1969/OrizonZeroTrustEnterpriseSASE/issues)
- **Email**: marco@syneto.eu

---

## License

Proprietary - All Rights Reserved

Copyright (c) 2025 Syneto / Orizon

---

**Built with** FastAPI, React, PostgreSQL, Redis, MongoDB, Docker

_Last updated: 2025-12-07 | Version 3.0.1_
