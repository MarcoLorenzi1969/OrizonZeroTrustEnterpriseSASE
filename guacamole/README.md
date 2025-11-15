# Orizon Zero Trust Connect - Guacamole Gateway Integration

**Server:** 167.71.33.70
**Status:** Ready for Deployment

---

## Quick Start

### 1. Deploy Guacamole Server

From this directory, run:

```bash
cd deployment
chmod +x *.sh
./deploy_guacamole.sh
```

This will:
- Install Apache Guacamole on 167.71.33.70
- Configure all services (guacd, Tomcat, MySQL, Nginx)
- Register hub in Orizon database
- Set up SSL and firewall

**Duration:** 15-20 minutes

### 2. Access Guacamole

- **URL:** https://167.71.33.70/guacamole/
- **Username:** guacadmin
- **Password:** guacadmin (⚠️ CHANGE IMMEDIATELY!)

### 3. Integrate with Orizon

**Backend Integration:**

```bash
# On Orizon hub (46.101.189.126)
ssh orizonai@46.101.189.126

# Copy files
scp guacamole/integration/guacamole_service.py \
    orizonai@46.101.189.126:/root/orizon-ztc/backend/app/services/

scp guacamole/integration/guacamole_endpoints.py \
    orizonai@46.101.189.126:/root/orizon-ztc/backend/app/api/v1/endpoints/

# Install dependencies
cd /root/orizon-ztc/backend
source venv/bin/activate
pip install aiohttp

# Update main app (add router import and include)
# Restart backend
sudo systemctl restart orizon-backend
```

**Frontend Integration:**

```bash
# Copy components
scp guacamole/integration/GuacamolePage.jsx \
    orizonai@46.101.189.126:/var/www/orizon-ztc-source/frontend/src/pages/

scp guacamole/integration/GuacamoleButton.jsx \
    orizonai@46.101.189.126:/var/www/orizon-ztc-source/frontend/src/components/nodes/

# Rebuild and deploy frontend
cd /var/www/orizon-ztc-source/frontend
npm run build
cp -r dist/* /var/www/orizon-ztc/dist/
```

### 4. Sync Nodes

From Orizon dashboard:
1. Login: https://46.101.189.126
2. Go to: Guacamole Gateway
3. Click: "Sync All Nodes"

Or via API:

```bash
curl -X POST https://46.101.189.126/api/v1/guacamole/sync-all-nodes \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

## Directory Structure

```
guacamole/
├── deployment/
│   ├── install_guacamole.sh          # Guacamole installation script
│   ├── register_guacamole_hub.py     # Register in Orizon database
│   └── deploy_guacamole.sh           # Complete deployment automation
├── integration/
│   ├── guacamole_service.py          # Backend API client
│   ├── guacamole_endpoints.py        # FastAPI endpoints
│   ├── GuacamolePage.jsx             # Frontend management page
│   └── GuacamoleButton.jsx           # SSH access button
├── docs/
│   └── GUACAMOLE_INTEGRATION.md      # Complete documentation
└── README.md                          # This file
```

---

## Features

✅ **Web-Based SSH Access** - No client software required
✅ **Multi-Protocol Support** - SSH, RDP, VNC, Telnet
✅ **Node Synchronization** - Auto-sync Orizon nodes
✅ **One-Click Access** - Direct SSH from Orizon dashboard
✅ **Session Recording** - Optional session capture
✅ **File Transfer** - SFTP integration
✅ **Multi-User Support** - User permissions and access control

---

## Configuration

### Servers

- **Orizon Hub:** 46.101.189.126 (Main ZTC hub)
- **Guacamole Hub:** 167.71.33.70 (SSH/RDP gateway)

### Credentials

**Guacamole (167.71.33.70):**
- SSH: `orizonzerotrust / ripper-FfFIlBelloccio.1969F`
- Web Admin: `guacadmin / guacadmin` (change this!)
- Saved in: `/root/guacamole_credentials.txt`

**Orizon Hub (46.101.189.126):**
- SSH: `orizonai / ripper-FfFIlBelloccio.1969F`
- Database: `orizonuser / orizonpass`

---

## API Endpoints

All endpoints are under `/api/v1/guacamole/`:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/status` | GET | Check Guacamole server status |
| `/connections` | GET | List all connections |
| `/connections/ssh` | POST | Create SSH connection |
| `/connections/rdp` | POST | Create RDP connection |
| `/nodes/{id}/access-url` | GET | Get access URL for node |
| `/sync-all-nodes` | POST | Sync all Orizon nodes |
| `/active-sessions` | GET | Get active sessions |
| `/connections/{id}` | DELETE | Delete connection |

---

## Troubleshooting

### Guacamole Not Accessible

```bash
# Check services
ssh orizonzerotrust@167.71.33.70
sudo systemctl status guacd tomcat9 nginx

# Check logs
sudo journalctl -u guacd -n 50
sudo tail -f /var/log/tomcat9/catalina.out
```

### Integration Not Working

```bash
# Check backend
ssh orizonai@46.101.189.126
sudo journalctl -u orizon-backend -f | grep guacamole

# Test API
curl -k https://46.101.189.126/api/v1/guacamole/status
```

### Cannot Connect to Nodes

1. Verify node is online in Orizon
2. Check SSH credentials in connection settings
3. Test SSH manually: `ssh parallels@10.211.55.19`
4. Check guacd logs for connection errors

---

## Documentation

**Full Documentation:** `docs/GUACAMOLE_INTEGRATION.md`

Includes:
- Complete architecture
- Detailed installation steps
- Configuration reference
- API usage examples
- Security best practices
- Performance tuning
- Monitoring and troubleshooting

---

## Quick Commands

```bash
# Deploy everything
cd deployment && ./deploy_guacamole.sh

# Check Guacamole status
curl -k https://167.71.33.70/guacamole/

# Restart services
ssh orizonzerotrust@167.71.33.70
sudo systemctl restart guacd tomcat9 nginx

# View logs
ssh orizonzerotrust@167.71.33.70
sudo journalctl -u guacd -f
```

---

## Support

For issues or questions:
1. Check `docs/GUACAMOLE_INTEGRATION.md`
2. Review Guacamole logs
3. Test services individually
4. Verify network connectivity

---

**Created:** 2025-11-09
**Status:** Production Ready
**Version:** 1.0
