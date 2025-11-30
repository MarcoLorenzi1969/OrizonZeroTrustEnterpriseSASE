# Orizon Zero Trust Connect - Documentation Index

## Overview

Orizon Zero Trust Connect is an enterprise-grade SD-WAN platform implementing Zero Trust security principles. It enables secure remote access to nodes (servers, workstations) through reverse SSH tunnels with comprehensive role-based access control.

## Quick Links

| Document | Description |
|----------|-------------|
| [Architecture](ARCHITECTURE.md) | System architecture and component overview |
| [API Reference](API_REFERENCE.md) | Complete REST API documentation |
| [User Hierarchy](USER_HIERARCHY.md) | 4-level RBAC hierarchy system |
| [Deployment](DEPLOYMENT.md) | Production deployment guide |
| [Security](SECURITY.md) | Security configuration and best practices |
| [Development](DEVELOPMENT.md) | Developer guide and contribution guidelines |
| [User Guide](USER_GUIDE.md) | End-user manual and feature overview |
| [Troubleshooting](TROUBLESHOOTING.md) | Common issues and solutions |

## Getting Started

### For Administrators

1. **First Login**: Access the system at `https://139.59.149.48` with your SUPERUSER credentials
2. **Create Users**: Navigate to Users → Create User to add SUPER_ADMIN, ADMIN, or USER accounts
3. **Create Groups**: Navigate to Groups → Create Group to organize node access
4. **Add Nodes**: Navigate to Nodes → Create Node to add servers/workstations
5. **Assign Permissions**: Add nodes to groups with specific access permissions (SSH, RDP, VNC, SSL Tunnel)

### For End Users

1. **Login**: Access `https://139.59.149.48` with your credentials
2. **View Nodes**: Navigate to Nodes to see assigned servers
3. **Connect**: Click on a node to establish a connection (based on permissions)

## System Requirements

### Production Server
- Ubuntu 22.04 or 24.04 LTS
- 2+ CPU cores
- 4GB+ RAM
- 40GB+ disk space
- Docker 24.x+
- Nginx 1.24+

### Client Nodes
- Linux, Windows, or macOS
- Network connectivity to port 2222 (SSH tunnel)
- Agent installation (auto-generated script)

## Key Features

### Zero Trust Security
- Never trust, always verify
- Least privilege access
- End-to-end encryption (TLS 1.2/1.3)
- JWT-based authentication

### Hierarchical Access Control
```
SUPERUSER (Platform Owner)
    └── SUPER_ADMIN (Distributors)
            └── ADMIN (Resellers)
                    └── USER (End Clients)
```

### Group-Based Node Access
- Users access nodes through group membership
- Granular permissions per node (SSH, RDP, VNC, SSL Tunnel)
- Flexible group management

### Real-Time Monitoring
- Node health monitoring (CPU, memory, disk)
- Heartbeat detection (30-second intervals)
- Automatic offline detection
- Audit logging

## Architecture Overview

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
│   Edge Nodes    │────▶ SSH Tunnel Server (Port 2222) ────▶ Reverse Tunnel
└─────────────────┘
```

## API Quick Reference

### Authentication
```bash
# Login
curl -X POST https://139.59.149.48/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password"}'

# Use token
curl https://139.59.149.48/api/v1/users \
  -H "Authorization: Bearer <access_token>"
```

### Common Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/login` | Authenticate user |
| GET | `/users` | List visible users |
| POST | `/users` | Create new user |
| GET | `/nodes` | List accessible nodes |
| POST | `/nodes` | Create new node |
| GET | `/groups` | List groups |
| POST | `/groups` | Create new group |

See [API Reference](API_REFERENCE.md) for complete documentation.

## Support & Contact

- **Documentation**: This folder (`/docs`)
- **API Docs**: `https://139.59.149.48/docs` (Swagger UI)
- **Email**: support@orizon.one

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.0.0 | November 2025 | Complete rewrite with 4-level hierarchy |
| 1.0.0 | October 2025 | Initial release |

## License

Proprietary - Orizon / Syneto

---

*Last updated: November 30, 2025*
