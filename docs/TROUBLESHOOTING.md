# Orizon Zero Trust Connect - Troubleshooting Guide

## Overview

This guide covers common issues, error messages, and their solutions for the Orizon Zero Trust Connect platform.

---

## Table of Contents

1. [Authentication Issues](#authentication-issues)
2. [Tunnel Connectivity](#tunnel-connectivity)
3. [Node Problems](#node-problems)
4. [Backend/API Errors](#backendapi-errors)
5. [Frontend Issues](#frontend-issues)
6. [Database Problems](#database-problems)
7. [Docker/Container Issues](#dockercontainer-issues)

---

## Authentication Issues

### JWT Token Expired

**Symptom**: API returns 401 with "Token expired" message

**Solution**:
```bash
# Get new token via login
curl -X POST https://139.59.149.48/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password"}'
```

### Invalid Credentials

**Symptom**: Login fails with 401 error

**Checklist**:
1. Verify email is correct (case-sensitive)
2. Check password hasn't been changed
3. Verify user account is not disabled
4. Check database for user existence:
```bash
docker compose exec backend python -c "
from app.core.database import SessionLocal
from app.models.user import User
from sqlalchemy import select

db = SessionLocal()
result = db.execute(select(User).where(User.email == 'user@example.com'))
user = result.scalar_one_or_none()
print(f'User found: {user is not None}')
if user:
    print(f'User ID: {user.id}')
    print(f'Is Active: {user.is_active}')
"
```

### Permission Denied

**Symptom**: 403 Forbidden error when accessing resources

**Cause**: User role insufficient for the action

**Solution**:
1. Verify user role hierarchy:
   - `SUPERUSER` > `SUPER_ADMIN` > `ADMIN` > `USER`
2. Check API endpoint required role in `API_REFERENCE.md`
3. Verify group membership if accessing nodes

---

## Tunnel Connectivity

### Tunnel Shows "Offline"

**Symptoms**:
- Node shows offline in dashboard
- No heartbeat received

**Diagnostic Steps**:
```bash
# 1. Check tunnel service on Edge node
ssh edge-node
systemctl status orizon-tunnel

# 2. Check if SSH connection is established
ss -tnp | grep 2222

# 3. Check tunnel logs
journalctl -u orizon-tunnel -n 50

# 4. Verify SSH key is authorized on Hub
ssh hub-server
grep "edge-node-id" /home/tunnel_user/.ssh/authorized_keys
```

**Common Fixes**:
```bash
# Restart tunnel service
sudo systemctl restart orizon-tunnel

# If autossh process is stuck
pkill -f autossh
sudo systemctl start orizon-tunnel

# Regenerate SSH keys if corrupted
rm -f /opt/orizon-agent/.ssh/id_ed25519*
ssh-keygen -t ed25519 -f /opt/orizon-agent/.ssh/id_ed25519 -N ""
```

### Tunnel Keeps Disconnecting

**Symptom**: Tunnel connects but disconnects after a few minutes

**Solution**: Check keep-alive settings in systemd service:
```ini
# /etc/systemd/system/orizon-tunnel.service
[Service]
ExecStart=/usr/bin/autossh -M 0 -N \
    -o ServerAliveInterval=15 \
    -o ServerAliveCountMax=3 \
    -o TCPKeepAlive=yes \
    -o ConnectTimeout=10 \
    ...
```

### Port Already in Use

**Symptom**: Tunnel fails with "Address already in use"

**Solution**:
```bash
# Find process using the port
lsof -i :23200

# Kill stale SSH connections
pkill -f "ssh.*-R 23200"

# Restart tunnel
sudo systemctl restart orizon-tunnel
```

---

## Node Problems

### Node Not Appearing in Dashboard

**Checklist**:
1. Verify agent is installed on node
2. Check tunnel connectivity (see above)
3. Verify node is registered in database:
```bash
curl -s https://139.59.149.48/api/v1/nodes \
  -H "Authorization: Bearer $TOKEN" | jq '.[] | {id, name, status}'
```

### Node Health Metrics Missing

**Symptom**: CPU/Memory/Disk metrics show "N/A"

**Cause**: Heartbeat service not sending metrics

**Solution**:
```bash
# On Edge node, check heartbeat service
systemctl status orizon-heartbeat

# Check heartbeat logs
journalctl -u orizon-heartbeat -n 20

# Manual heartbeat test
curl -X POST https://139.59.149.48/api/v1/nodes/<node-id>/heartbeat \
  -H "Content-Type: application/json" \
  -d '{"cpu_usage": 25, "memory_usage": 40, "disk_usage": 60}'
```

---

## Backend/API Errors

### 500 Internal Server Error

**Diagnostic Steps**:
```bash
# 1. Check backend logs
docker compose logs backend --tail=100

# 2. Check for Python exceptions
docker compose logs backend 2>&1 | grep -A 5 "Exception"

# 3. Verify database connectivity
docker compose exec backend python -c "
from app.core.database import SessionLocal
db = SessionLocal()
db.execute('SELECT 1')
print('Database OK')
"
```

### Database Connection Error

**Symptom**: "Connection refused" or "Cannot connect to PostgreSQL"

**Solutions**:
```bash
# 1. Check PostgreSQL container
docker compose ps postgres

# 2. Restart PostgreSQL
docker compose restart postgres

# 3. Verify connection settings in .env
cat .env | grep DATABASE

# 4. Manual connection test
docker compose exec postgres psql -U orizon -d orizondb -c "SELECT 1"
```

### Rate Limit Exceeded

**Symptom**: 429 Too Many Requests

**Solution**: Wait for rate limit window to reset (typically 1 minute)

**For testing, disable rate limiting temporarily**:
```python
# In backend/app/middleware/rate_limit.py
# Comment out the @rate_limit decorator on specific endpoints
```

---

## Frontend Issues

### Blank White Screen

**Diagnostic Steps**:
1. Check browser console (F12) for JavaScript errors
2. Verify frontend build:
```bash
cd frontend
npm run build
ls -la dist/
```

3. Check Nginx serving correctly:
```bash
curl -I https://139.59.149.48/
```

### API Calls Failing (CORS Error)

**Symptom**: "Access-Control-Allow-Origin" error in console

**Solution**: Verify Nginx CORS headers:
```nginx
# In /etc/nginx/sites-enabled/orizon
location /api/ {
    add_header 'Access-Control-Allow-Origin' '*' always;
    add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, OPTIONS' always;
    add_header 'Access-Control-Allow-Headers' 'Authorization, Content-Type' always;

    if ($request_method = 'OPTIONS') {
        return 204;
    }

    proxy_pass http://127.0.0.1:8000/api/;
}
```

### Login Redirect Loop

**Symptom**: After login, keeps redirecting back to login page

**Checklist**:
1. Clear browser localStorage
2. Check token storage in browser DevTools
3. Verify JWT token format is valid

---

## Database Problems

### Migration Errors

**Symptom**: Alembic migration fails

**Solutions**:
```bash
# 1. Check current revision
docker compose exec backend alembic current

# 2. Show migration history
docker compose exec backend alembic history

# 3. Manually resolve conflicts
docker compose exec backend alembic stamp head

# 4. Regenerate migrations
docker compose exec backend alembic revision --autogenerate -m "description"
```

### Data Inconsistency

**Symptom**: Orphan records or foreign key violations

**Diagnostic**:
```sql
-- Check for orphan tunnels (node doesn't exist)
SELECT t.* FROM tunnels t
LEFT JOIN nodes n ON t.node_id = n.id
WHERE n.id IS NULL;

-- Check for orphan group members (user doesn't exist)
SELECT gm.* FROM group_members gm
LEFT JOIN users u ON gm.user_id = u.id
WHERE u.id IS NULL;
```

---

## Docker/Container Issues

### Container Won't Start

**Diagnostic**:
```bash
# Check container status
docker compose ps

# Check logs for failing container
docker compose logs <service_name>

# Rebuild container
docker compose build <service_name> --no-cache
docker compose up -d <service_name>
```

### Out of Disk Space

**Symptom**: "No space left on device" errors

**Solution**:
```bash
# Clean Docker resources
docker system prune -a --volumes

# Check disk usage
df -h
du -sh /var/lib/docker/*
```

### Memory Issues

**Symptom**: Container keeps restarting (OOMKilled)

**Solution**: Increase memory limits in docker-compose.yml:
```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 512M
```

---

## Log Locations

| Component | Log Location |
|-----------|--------------|
| Backend | `docker compose logs backend` |
| PostgreSQL | `docker compose logs postgres` |
| Nginx | `/var/log/nginx/error.log` |
| Tunnel Service | `journalctl -u orizon-tunnel` |
| Watchdog | `/var/log/orizon-tunnel-watchdog.log` |

---

## Getting Help

If issues persist after trying these solutions:

1. Collect relevant logs
2. Note the exact error message
3. Document steps to reproduce
4. Contact support@orizon.one

---

*Last updated: November 30, 2025*
