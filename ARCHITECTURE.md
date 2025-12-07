# Orizon Zero Trust Enterprise SASE - Architecture Documentation

**Version:** 3.0.1
**Last Updated:** 2025-12-07
**Author:** Marco Lorenzi @ Syneto/Orizon

---

## Table of Contents

1. [Overview](#overview)
2. [Development Environment](#development-environment)
3. [Infrastructure Topology](#infrastructure-topology)
4. [Backend Architecture](#backend-architecture)
5. [Frontend Architecture](#frontend-architecture)
6. [Services & Microservices](#services--microservices)
7. [Database Layer](#database-layer)
8. [Security Components](#security-components)
9. [Software Distribution Matrix](#software-distribution-matrix)
10. [Edge Nodes](#edge-nodes)

---

## Overview

Orizon Zero Trust Enterprise SASE is a comprehensive Zero Trust Network Access (ZTNA) solution that provides secure remote access to enterprise resources through reverse SSH tunnels, web terminals, and RDP connections. The platform implements a hub-and-spoke architecture where edge nodes connect to central hubs via encrypted tunnels.

### Key Features

- **Zero Trust Architecture**: No implicit trust, verify every connection
- **Reverse SSH Tunnels**: Secure connectivity without inbound firewall rules
- **Multi-Hub Support**: Redundant hub infrastructure for high availability
- **Web Terminal**: Browser-based SSH access to remote nodes
- **RDP Direct**: Native Remote Desktop Protocol support
- **Role-Based Access Control**: Granular permissions with hierarchical roles
- **Multi-Tenant Support**: Isolated environments for different organizations
- **Two-Factor Authentication**: TOTP-based 2FA for enhanced security
- **SSO Integration**: Single Sign-On capabilities
- **Real-time Monitoring**: Node status, metrics, and geolocation tracking
- **Hardening Analysis**: Security posture assessment for edge nodes

---

## Development Environment

### Technology Stack

| Layer | Technology | Version |
|-------|------------|---------|
| **Backend Framework** | FastAPI | 0.104+ |
| **Python Runtime** | Python | 3.11+ |
| **Frontend Framework** | React + Vite | 18.x / 5.x |
| **Primary Database** | PostgreSQL | 15 |
| **Cache Layer** | Redis | 7 |
| **Log Storage** | MongoDB | 7 |
| **Containerization** | Docker + Compose | 24.x |
| **Web Server** | Nginx | 1.24+ |
| **SSH Server** | OpenSSH | 9.x |

### Local Development Setup

```
/Users/marcolorenzi/Windsurf/OrizonZeroTrustEnterpriseSASE/
├── backend/              # FastAPI backend application
├── frontend/             # React/Vite frontend application
├── script-generator/     # Node.js provisioning script generator
├── ssh-tunnel-server/    # Docker SSH tunnel server
├── packages/             # Multi-platform agent packages
├── deploy/               # Deployment scripts
├── docs/                 # Documentation
├── kubernetes/           # K8s manifests (future)
└── tests/                # Integration tests
```

---

## Infrastructure Topology

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
                           │ Windows11-Edge  │                      │ Edge-Ubuntu     │
                           │     Test        │                      │     Test        │
                           │  (Parallels)    │                      │   (VM/Cloud)    │
                           └─────────────────┘                      └─────────────────┘
```

### Environment Details

| Environment | IP/Location | Purpose | OS |
|-------------|-------------|---------|-----|
| **LOCAL** | macOS Sequoia | Development & Testing | macOS 15.x |
| **HUB 1** | 139.59.149.48 | Production Hub (Primary) | Ubuntu 24.04 |
| **HUB 2** | 68.183.219.222 | Production Hub (Secondary) | Ubuntu 24.04 |
| **GitHub** | Cloud | Source Control | - |
| **Windows11-Edge-Test** | Parallels VM | Windows Edge Testing | Windows 11 Pro |
| **Edge-Ubuntu-Test** | 192.168.x.x | Linux Edge Testing | Ubuntu 22.04 |

---

## Backend Architecture

### API Endpoints (`backend/app/api/v1/endpoints/`)

| Module | File | Description |
|--------|------|-------------|
| **Authentication** | `auth.py` | JWT login, token refresh, logout |
| **User Management** | `user_management.py` | CRUD users, role assignment, hierarchy |
| **Nodes** | `nodes.py` | Edge node registration, status, hardening |
| **Tunnels** | `tunnels.py` | Tunnel management, dashboard, keep-alive |
| **Network** | `network.py` | Topology, connectivity status |
| **Groups** | `groups.py` | Node grouping, member management |
| **Tenants** | `tenants.py` | Multi-tenant organization management |
| **ACL** | `acl.py` | Access Control Lists, permissions |
| **Provision** | `provision.py` | Node provisioning, script generation |
| **Terminal** | `terminal.py` | WebSocket terminal proxy |
| **Metrics** | `metrics.py` | Node health metrics collection |
| **Audit** | `audit.py` | Audit logging, activity tracking |
| **2FA** | `twofa.py` | TOTP setup, verification |
| **SSO** | `sso.py` | Single Sign-On integration |

### Data Models (`backend/app/models/`)

| Model | Description |
|-------|-------------|
| `user.py` | User accounts with roles and permissions |
| `user_permissions.py` | Granular permission assignments |
| `node.py` | Edge node with hardening fields |
| `tunnel.py` | SSH tunnel configurations |
| `group.py` | Node groups with hierarchies |
| `tenant.py` | Multi-tenant organizations |
| `access_rule.py` | ACL rules and policies |
| `audit_log.py` | Activity logging schema |

### Business Services (`backend/app/services/`)

| Service | Description |
|---------|-------------|
| `user_service.py` | User CRUD operations |
| `permission_service.py` | Permission evaluation engine |
| `hierarchy_service.py` | Role hierarchy management |
| `node_provision_service.py` | Provisioning workflow |
| `node_visibility_service.py` | Node access control |
| `tunnel_service.py` | Tunnel lifecycle management |
| `group_service.py` | Group operations |
| `tenant_service.py` | Tenant isolation |
| `acl_service.py` | ACL rule processing |
| `audit_service.py` | Audit log operations |
| `totp_service.py` | 2FA TOTP implementation |
| `sso_service.py` | SSO protocol handling |
| `geolocation_service.py` | IP geolocation (GeoLite2) |

### Core Components (`backend/app/core/`)

| Component | Description |
|-----------|-------------|
| `config.py` | Environment configuration |
| `security.py` | JWT, password hashing, auth |
| `database.py` | PostgreSQL async connection |
| `redis.py` | Redis cache configuration |
| `redis_client.py` | Redis operations wrapper |
| `mongodb.py` | MongoDB log connection |

---

## Frontend Architecture

### Pages (`frontend/src/pages/`)

| Page | Description |
|------|-------------|
| `LoginPage.jsx` | Authentication with 2FA support |
| `DashboardPage.jsx` | Overview with stats and maps |
| `NodesPage.jsx` | Node management with hardening info |
| `TunnelsDashboard.jsx` | Active tunnels monitoring |
| `UsersPage.jsx` | User administration |
| `GroupsPage.jsx` | Group management |
| `EdgeProvisioningPage.jsx` | Node onboarding wizard |
| `RDPDirectPage.jsx` | RDP connection manager |

### Components (`frontend/src/components/`)

| Component | Description |
|-----------|-------------|
| `WebTerminal.jsx` | Xterm.js SSH terminal |
| `RDPDirectTest.jsx` | RDP connection component |
| `DebugPanel.jsx` | Developer debugging tools |
| `DebugOverlay.jsx` | Floating debug information |

### State Management (`frontend/src/stores/`)

| Store | Description |
|-------|-------------|
| `authStore.js` | Zustand auth state with persistence |

---

## Services & Microservices

### Docker Compose Stack

| Service | Container | Port | Description |
|---------|-----------|------|-------------|
| **Backend** | orizon-backend | 8000 | FastAPI application |
| **PostgreSQL** | orizon-postgres | 5432 | Primary database |
| **Redis** | orizon-redis | 6379 | Session/cache store |
| **MongoDB** | orizon-mongodb | 27017 | Audit log storage |
| **SSH Tunnel** | orizon-ssh-tunnel | 2222 | Reverse tunnel server |
| **Script Generator** | orizon-script-generator | 3000 | Provisioning scripts |

### Script Generator (`script-generator/`)

Node.js service that generates platform-specific installation scripts:
- Linux (Debian/Ubuntu, RHEL/CentOS)
- macOS (Intel/Apple Silicon)
- Windows (PowerShell)

Features hardening wizard for security assessment during installation.

---

## Database Layer

### PostgreSQL Schema

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   users     │────▶│   groups    │────▶│   nodes     │
└─────────────┘     └─────────────┘     └─────────────┘
       │                   │                   │
       ▼                   ▼                   ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ permissions │     │access_rules │     │   tunnels   │
└─────────────┘     └─────────────┘     └─────────────┘
       │
       ▼
┌─────────────┐
│   tenants   │
└─────────────┘
```

### MongoDB Collections

- `audit_logs`: User activity tracking
- `node_metrics`: Historical performance data
- `tunnel_events`: Connection logs

---

## Security Components

### Authentication Flow

1. **Login**: Email/password → JWT access + refresh tokens
2. **2FA**: Optional TOTP verification
3. **SSO**: External IdP integration
4. **Token Refresh**: Automatic token renewal

### Role Hierarchy

```
SUPERUSER (System Owner)
    └── SUPER_ADMIN (Platform Admin)
            └── ADMIN (Tenant Admin)
                    └── USER (Standard User)
                            └── VIEWER (Read-Only)
```

### Node Hardening Fields

| Field | Description |
|-------|-------------|
| `hardening_firewall` | Firewall status and rules |
| `hardening_antivirus` | AV/Defender status |
| `hardening_open_ports` | Listening ports list |
| `hardening_security_modules` | SELinux/AppArmor status |
| `hardening_ssh_config` | SSH security settings |
| `hardening_ssl_info` | TLS configuration |
| `hardening_audit` | Audit logging status |
| `hardening_updates` | Pending security updates |

---

## Software Distribution Matrix

### Backend Modules

| Module | LOCAL | HUB 1 | HUB 2 | GitHub | Status |
|--------|:-----:|:-----:|:-----:|:------:|:------:|
| `auth.py` | ✅ | ✅ | ✅ | ✅ | Aligned |
| `user_management.py` | ✅ | ✅ | ✅ | ✅ | Aligned |
| `nodes.py` | ✅ | ✅ | ✅ | ✅ | Aligned |
| `tunnels.py` | ✅ | ✅ | ✅ | ✅ | Aligned |
| `network.py` | ✅ | ✅ | ✅ | ✅ | Aligned |
| `groups.py` | ✅ | ✅ | ✅ | ✅ | Aligned |
| `tenants.py` | ✅ | ✅ | ✅ | ✅ | Aligned |
| `acl.py` | ✅ | ✅ | ✅ | ✅ | Aligned |
| `provision.py` | ✅ | ✅ | ✅ | ✅ | Aligned |
| `terminal.py` | ✅ | ✅ | ✅ | ✅ | Aligned |
| `metrics.py` | ✅ | ✅ | ✅ | ✅ | Aligned |
| `audit.py` | ✅ | ✅ | ✅ | ✅ | Aligned |
| `twofa.py` | ✅ | ✅ | ✅ | ✅ | Aligned |
| `sso.py` | ✅ | ✅ | ✅ | ✅ | Aligned |

### Frontend Pages

| Page | LOCAL | HUB 1 | HUB 2 | GitHub | Status |
|------|:-----:|:-----:|:-----:|:------:|:------:|
| `DashboardPage.jsx` | ✅ | ✅ | ✅ | ✅ | Aligned |
| `NodesPage.jsx` | ✅ | ✅ | ✅ | ✅ | Aligned |
| `TunnelsDashboard.jsx` | ✅ | ✅ | ✅ | ✅ | Aligned |
| `UsersPage.jsx` | ✅ | ✅ | ✅ | ✅ | Aligned |
| `GroupsPage.jsx` | ✅ | ✅ | ✅ | ✅ | Aligned |
| `LoginPage.jsx` | ✅ | ✅ | ✅ | ✅ | Aligned |
| `EdgeProvisioningPage.jsx` | ✅ | ✅ | ✅ | ✅ | Aligned |
| `RDPDirectPage.jsx` | ✅ | ✅ | ✅ | ✅ | Aligned |

### Infrastructure Services

| Service | LOCAL | HUB 1 | HUB 2 | Description |
|---------|:-----:|:-----:|:-----:|-------------|
| PostgreSQL | ✅ | ✅ | ✅ | Primary database |
| Redis | ✅ | ✅ | ✅ | Cache/sessions |
| MongoDB | ✅ | ✅ | ✅ | Audit logs |
| SSH Tunnel Server | ✅ | ✅ | ✅ | Port 2222 |
| Script Generator | ✅ | ✅ | ✅ | Port 3000 |
| Nginx | ✅ | ✅ | ✅ | Reverse proxy (config in /nginx) |

---

## Edge Nodes

### Test Environment

| Node | Type | OS | Hub Connection | Agent Status |
|------|------|-----|----------------|--------------|
| **Windows11-Edge-Test** | Windows | Windows 11 Pro | HUB 1 + HUB 2 | Installed |
| **Edge-Ubuntu-Test** | Linux | Ubuntu 22.04 | HUB 1 + HUB 2 | Installed |

### Edge Agent Components

| Component | Windows | Linux | macOS |
|-----------|---------|-------|-------|
| AutoSSH | ✅ | ✅ | ✅ |
| Tunnel Service | ✅ | ✅ | ✅ |
| Heartbeat Agent | ✅ | ✅ | ✅ |
| Hardening Scanner | ✅ | ✅ | ✅ |
| SSH Key Pair | ✅ | ✅ | ✅ |

### Exposed Applications

| Application | Port (Default) | Description |
|-------------|----------------|-------------|
| TERMINAL | 22 | SSH access |
| RDP | 3389 | Remote Desktop |
| VNC | 5900 | VNC viewer |
| WEB_SERVER | 80/443 | HTTP(S) proxy |

### Tunnel Ports Allocation

| Port Range | Purpose |
|------------|---------|
| 20000-29999 | Application tunnels |
| 30000-39999 | Service tunnels (heartbeat/metrics) |
| 40000-49999 | Reserved for future use |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 3.0.1 | 2025-12-07 | Sync environments, hardening schema |
| 3.0.0 | 2025-12-06 | Enhanced installation scripts |
| 2.1.1 | 2025-12-04 | Enterprise hardening, SSO |
| 2.1.0 | 2025-12-03 | Multi-hub packages |
| 2.0.0 | 2025-11-30 | Initial SASE release |

---

## Contact

**Project Owner:** Marco Lorenzi
**Organization:** Syneto / Orizon
**Repository:** https://github.com/MarcoLorenzi1969/OrizonZeroTrustEnterpriseSASE
