# Orizon Zero Trust Connect - Architecture

## Overview

Orizon Zero Trust Connect is an enterprise-grade SD-WAN platform implementing Zero Trust security principles. The system enables secure remote access to nodes through reverse SSH tunnels, with a comprehensive role-based access control system.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              INTERNET                                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         NGINX REVERSE PROXY                                  │
│                     (HTTPS/SSL Termination)                                  │
│                        Port 443 (HTTPS)                                      │
│                        Port 80 → 443 redirect                                │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
            ┌───────────┐   ┌───────────┐   ┌───────────┐
            │  Frontend │   │  Backend  │   │    SSH    │
            │   (SPA)   │   │   (API)   │   │  Tunnel   │
            │  /assets  │   │   /api/   │   │  Server   │
            └───────────┘   └───────────┘   └───────────┘
                                    │               │
                    ┌───────────────┼───────────────┤
                    ▼               ▼               ▼
            ┌───────────┐   ┌───────────┐   ┌───────────┐
            │ PostgreSQL│   │   Redis   │   │  MongoDB  │
            │  (Users,  │   │  (Cache,  │   │  (Logs,   │
            │   Nodes)  │   │  Sessions)│   │  Metrics) │
            └───────────┘   └───────────┘   └───────────┘

                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         EDGE NODES (Remote Sites)                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   Linux     │  │   Windows   │  │   macOS     │  │   Linux     │        │
│  │   Server    │  │   Server    │  │   Server    │  │   Desktop   │        │
│  │  (Agent)    │  │  (Agent)    │  │  (Agent)    │  │  (Agent)    │        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Components

### 1. Frontend (React SPA)

- **Technology**: React 18, Vite, TailwindCSS
- **Location**: `/frontend`
- **Build Output**: `/frontend/dist`
- **Served from**: `/var/www/html` via Nginx

**Key Features**:
- Single Page Application with React Router
- Dark theme UI
- Real-time node status updates
- WebSocket support for terminal access

**Main Pages**:
| Page | Route | Description |
|------|-------|-------------|
| Dashboard | `/dashboard` | System overview and metrics |
| Nodes | `/nodes` | Node management and monitoring |
| Groups | `/groups` | Group-based access control |
| Users | `/users` | User management (hierarchical) |
| Tunnels | `/tunnels` | Active tunnel sessions |
| Audit | `/audit` | Access logs and audit trail |

### 2. Backend (FastAPI)

- **Technology**: Python 3.11, FastAPI, SQLAlchemy, AsyncIO
- **Location**: `/backend`
- **API Base**: `/api/v1`
- **Port**: 8000 (internal)

**Key Modules**:
```
backend/
├── app/
│   ├── api/v1/endpoints/     # API routes
│   │   ├── auth.py           # Authentication
│   │   ├── nodes.py          # Node management
│   │   ├── groups.py         # Group management
│   │   ├── user_management.py # User CRUD
│   │   └── tunnels.py        # Tunnel management
│   ├── models/               # SQLAlchemy models
│   ├── services/             # Business logic
│   │   ├── hierarchy_service.py  # User hierarchy
│   │   ├── group_service.py      # Group operations
│   │   └── node_visibility_service.py
│   ├── auth/                 # Authentication
│   └── core/                 # Configuration
```

### 3. SSH Tunnel Server

- **Technology**: AsyncSSH (Python)
- **Port**: 2222 (internal)
- **Purpose**: Accepts reverse SSH connections from edge nodes

**Tunnel Types**:
- SSH Terminal (port 22)
- HTTPS Proxy (port 443)
- RDP (port 3389)
- VNC (port 5900)

### 4. Databases

#### PostgreSQL
- **Purpose**: Primary data store
- **Contains**: Users, Nodes, Groups, Permissions
- **Port**: 5432

#### Redis
- **Purpose**: Caching and session storage
- **Contains**: JWT tokens, temporary proxy tokens
- **Port**: 6379

#### MongoDB
- **Purpose**: Logging and metrics
- **Contains**: Audit logs, access logs, metrics history
- **Port**: 27017

## Docker Compose Services

```yaml
services:
  backend:      # FastAPI application
  frontend:     # Nginx + React build
  postgres:     # PostgreSQL database
  redis:        # Redis cache
  mongodb:      # MongoDB for logs
  ssh-tunnel:   # SSH reverse tunnel server
```

## Network Architecture

### External Access
```
Internet → Nginx (443) → Backend API (8000)
                      → Frontend Static (files)
                      → WebSocket (/ws/)
```

### Internal Communication
```
Backend → PostgreSQL (5432)
       → Redis (6379)
       → MongoDB (27017)
       → SSH Tunnel Server (2222)
```

### Edge Node Communication
```
Edge Node → SSH Tunnel Server (2222) [Reverse Tunnel]
         → Backend API (heartbeat, metrics)
```

## Security Architecture

### Authentication Flow
```
1. User Login → POST /api/v1/auth/login
2. Validate credentials → PostgreSQL
3. Generate JWT → Return access_token + refresh_token
4. Client stores token → localStorage
5. API calls include → Authorization: Bearer <token>
```

### Role-Based Access Control (RBAC)
```
SUPERUSER (Level 4)
    └── Full system access
    └── Can create: SUPER_ADMIN, ADMIN, USER

SUPER_ADMIN (Level 3)
    └── Sees: self + subordinates
    └── Can create: ADMIN, USER

ADMIN (Level 2)
    └── Sees: self + subordinates
    └── Can create: USER only

USER (Level 1)
    └── Sees: self only
    └── Cannot create users
```

### Group-Based Node Access
```
User → Member of Group → Group has Nodes → User can access Nodes
                      → With specific permissions (SSH, RDP, VNC, SSL)
```

## Data Models

### User
```python
User:
  - id: UUID
  - email: String (unique)
  - username: String
  - full_name: String
  - hashed_password: String
  - role: Enum (SUPERUSER, SUPER_ADMIN, ADMIN, USER)
  - is_active: Boolean
  - created_by_id: UUID (FK → User)  # Hierarchy tracking
  - created_at: DateTime
  - last_login: DateTime
```

### Node
```python
Node:
  - id: UUID
  - name: String
  - hostname: String
  - node_type: String (linux, windows, macos)
  - status: Enum (ONLINE, OFFLINE, ERROR)
  - agent_token: String (unique)
  - owner_id: UUID (FK → User)
  - reverse_tunnel_type: String
  - exposed_applications: Array
  - application_ports: JSON
  - service_tunnel_port: Integer
```

### Group
```python
Group:
  - id: UUID
  - name: String (unique)
  - description: String
  - settings: JSON (allow_terminal, allow_rdp, allow_vnc)
  - created_by: UUID (FK → User)
  - is_active: Boolean

UserGroup (Many-to-Many):
  - user_id: UUID
  - group_id: UUID
  - role_in_group: Enum (OWNER, ADMIN, MEMBER)

NodeGroup (Many-to-Many):
  - node_id: UUID
  - group_id: UUID
  - permissions: JSON (ssh, rdp, vnc, ssl_tunnel)
```

## Deployment Architecture

### Production Server
- **IP**: 139.59.149.48
- **OS**: Ubuntu 24.04
- **Docker**: 24.x
- **Nginx**: 1.28.x

### Directory Structure
```
/opt/orizon-ztc/
├── backend/
├── frontend/
├── docker-compose.yml
├── .env
└── data/
    ├── postgres/
    ├── redis/
    └── mongodb/

/var/www/html/          # Frontend build (served by Nginx)
/etc/nginx/ssl/         # SSL certificates
/etc/nginx/sites-available/orizon  # Nginx config
```

### SSL/TLS Configuration
- Self-signed certificate for IP-based access
- TLS 1.2 and 1.3 supported
- HTTP automatically redirected to HTTPS

## Scalability Considerations

### Horizontal Scaling
- Backend can be scaled with multiple instances behind load balancer
- Redis for session sharing across instances
- PostgreSQL with read replicas for scaling reads

### Vertical Scaling
- Current single-server deployment
- Can upgrade server resources as needed
- Docker resource limits configurable

## Monitoring and Logging

### Application Logs
- Loguru for structured logging
- Logs stored in MongoDB
- Access logs in Nginx

### Metrics
- Node metrics (CPU, memory, disk)
- Heartbeat monitoring (30-second intervals)
- Automatic offline detection (90 seconds timeout)

## Version Information

- **Current Version**: 2.0.0
- **API Version**: v1
- **Last Updated**: November 2025
