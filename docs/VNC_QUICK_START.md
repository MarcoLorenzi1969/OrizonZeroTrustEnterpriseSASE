# VNC Remote Desktop - Quick Start Guide

**For: Marco @ Syneto/Orizon**

## 🚀 Deploy to Production Server

### Prerequisites

- Server: `68.183.219.222` (OrizonZeroTrust1)
- User: `lorenz`
- Password: `ripper-FfFIlBelloccio.1969F`

### Step 1: Deploy Backend & Services

```bash
# From your local machine
cd /path/to/OrizonZeroTrustSASE

# Run deployment script
./deploy_vnc.sh --full

# This will:
# ✅ Create database tables
# ✅ Deploy backend code
# ✅ Deploy VNC Gateway service
# ✅ Deploy frontend
# ✅ Configure firewall
```

### Step 2: Verify Services

```bash
# SSH to server
ssh lorenz@68.183.219.222

# Check backend status
sudo systemctl status orizon-backend

# Check VNC Gateway status
sudo systemctl status orizon-vnc-gateway

# Test API
curl http://localhost:8000/api/v1/health

# Test VNC Gateway (should return 426 Upgrade Required)
curl -I http://localhost:6080
```

### Step 3: Setup VNC Server on Edge Node

```bash
# SSH to edge node (e.g., Edge Kali or Edge Ubuntu)
ssh your-edge-node

# Install VNC server
sudo apt update
sudo apt install x11vnc

# Create VNC password
x11vnc -storepasswd ~/.vnc/passwd

# Start VNC server on localhost only
x11vnc -display :0 -auth ~/.Xauthority -forever -localhost -rfbauth ~/.vnc/passwd

# Or use systemd service:
cat > /tmp/x11vnc.service <<EOF
[Unit]
Description=x11vnc VNC Server
After=display-manager.service

[Service]
Type=simple
ExecStart=/usr/bin/x11vnc -display :0 -auth /home/YOUR_USER/.Xauthority -forever -localhost -shared -rfbauth /home/YOUR_USER/.vnc/passwd
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo mv /tmp/x11vnc.service /etc/systemd/system/
sudo systemctl enable x11vnc
sudo systemctl start x11vnc
```

### Step 4: Deploy Edge Agent with VNC Support

```bash
# On edge node
cd /opt/orizon/agents

# Download agent files (if not already present)
# These will be copied by deploy script

# Install dependencies
pip3 install websockets psutil

# Run agent
python3 orizon_agent_vnc.py \
  --hub-host 68.183.219.222 \
  --hub-port 8000 \
  --node-id $(hostname) \
  --token YOUR_NODE_TOKEN
```

### Step 5: Test VNC Session

```bash
# From frontend UI:
1. Navigate to https://68.183.219.222/vnc
2. Click "New Session"
3. Select edge node
4. Enter session name: "Test VNC Session"
5. Click "Create Session"
6. VNC viewer should open showing remote desktop

# Or via API:
curl -X POST https://68.183.219.222/api/v1/vnc/sessions \
  -H "Authorization: Bearer $YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "node_id": "your-node-id",
    "name": "Test Session",
    "quality": "medium",
    "max_duration_seconds": 300
  }'
```

## 📊 Quick Diagnostics

### Check Service Logs

```bash
# Backend logs
ssh lorenz@68.183.219.222 "sudo journalctl -u orizon-backend -n 50 --no-pager"

# VNC Gateway logs
ssh lorenz@68.183.219.222 "sudo journalctl -u orizon-vnc-gateway -n 50 --no-pager"

# Edge agent logs
ssh edge-node "tail -50 /var/log/orizon_agent_vnc.log"
```

### Check Active Sessions

```bash
ssh lorenz@68.183.219.222 "sudo -u postgres psql -d orizon -c \"SELECT id, name, status, tunnel_port FROM vnc_sessions WHERE status = 'active';\""
```

### Check Firewall

```bash
ssh lorenz@68.183.219.222 "sudo ufw status | grep -E '6080|50000:59999'"
```

## 🐛 Common Issues

### Issue: "VNC Gateway not starting"

```bash
# Check logs
sudo journalctl -u orizon-vnc-gateway -f

# Common fixes:
sudo systemctl restart orizon-vnc-gateway

# Verify port is not in use
sudo netstat -tln | grep 6080
```

### Issue: "Cannot create VNC session"

```bash
# Check node is online
curl http://localhost:8000/api/v1/nodes | jq '.[] | select(.status=="online")'

# Check VNC server on edge
ssh edge-node "ps aux | grep x11vnc"
ssh edge-node "nc -zv localhost 5900"
```

### Issue: "Black screen in VNC"

```bash
# On edge node, check X display
echo $DISPLAY

# Restart VNC server with correct display
x11vnc -display :0 -auth ~/.Xauthority -forever -localhost
```

## 📋 Configuration Summary

### Environment Variables

**Backend (.env):**
```bash
JWT_SECRET_KEY=your-256-bit-secret-key
DATABASE_URL=postgresql+asyncpg://orizon:password@localhost:5432/orizon
REDIS_URL=redis://localhost:6379/0
```

**VNC Gateway (/etc/systemd/system/orizon-vnc-gateway.service):**
```ini
Environment="JWT_SECRET_KEY=your-256-bit-secret-key"
Environment="VNC_GATEWAY_PORT=6080"
```

**Frontend (.env):**
```bash
VITE_VNC_GATEWAY_URL=wss://68.183.219.222:6080
```

### Ports

- `6080` - VNC Gateway (WebSocket)
- `8000` - FastAPI Backend
- `50000-59999` - VNC Tunnel Ports
- `5900` - VNC Server (localhost only on edge)

## 🔐 Security Checklist

- ✅ VNC server bound to localhost only
- ✅ JWT secret key is strong (256-bit random)
- ✅ Firewall allows only necessary ports
- ✅ TLS/SSL enabled for WebSocket (wss://)
- ✅ Session tokens expire after max_duration
- ✅ ACL rules configured for Zero Trust
- ✅ Audit logging enabled

## 📚 Next Steps

1. **Read full documentation**: `docs/VNC_REMOTE_DESKTOP.md`
2. **Configure ACL rules** for granular access control
3. **Setup monitoring** with Prometheus/Grafana
4. **Test failover** scenarios
5. **Performance tuning** based on usage patterns

## 🆘 Support

- **Documentation**: `docs/VNC_REMOTE_DESKTOP.md`
- **Troubleshooting**: See full docs section 9
- **Logs**: `/var/log/orizon_*.log` and `journalctl -u orizon-*`

---

**Quick Reference:**

| Component | Location | Command |
|-----------|----------|---------|
| Backend | Hub Server | `sudo systemctl status orizon-backend` |
| VNC Gateway | Hub Server | `sudo systemctl status orizon-vnc-gateway` |
| Edge Agent | Edge Node | `python3 orizon_agent_vnc.py --hub-host ...` |
| VNC Server | Edge Node | `x11vnc -display :0 -forever -localhost` |
| Frontend | Browser | `https://68.183.219.222/vnc` |

---

**Created:** 2025-11-15
**Author:** Marco Lorenzi @ Syneto/Orizon
