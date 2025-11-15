# 🚀 ISTRUZIONI DEPLOYMENT - Orizon Zero Trust Connect

**Server**: 46.101.189.126
**User**: orizzonti
**Password**: ripper-FfFIlBelloccio.1969F

---

## ⚡ DEPLOY IN 3 PASSI (5-10 minuti)

### PASSO 1: Connettiti al server

```bash
ssh orizzonti@46.101.189.126
```

### PASSO 2: Copia ed esegui lo script

**Opzione A - Da file locale:**
```bash
# Dal tuo Mac (in un altro terminale):
scp deploy/DEPLOY_ON_SERVER.sh orizzonti@46.101.189.126:~/

# Sul server (nella SSH già connessa):
bash ~/DEPLOY_ON_SERVER.sh
```

**Opzione B - Copia/Incolla diretto:**
```bash
# Sul server, apri l'editor:
nano deploy.sh

# Poi copia TUTTO il contenuto di deploy/DEPLOY_ON_SERVER.sh
# Incolla nell'editor, salva (Ctrl+O, Enter, Ctrl+X)

# Esegui:
bash deploy.sh
```

### PASSO 3: Verifica

```bash
# Sul server:
curl http://localhost:8000/health

# Dal tuo browser:
# Apri: http://46.101.189.126
```

---

## ✅ Cosa Installa lo Script

1. **Sistema**:
   - Python 3.11 + venv
   - Nginx web server
   - Node.js (per build frontend)

2. **Backend**:
   - FastAPI con Uvicorn
   - SQLAlchemy + async drivers
   - Redis client
   - MongoDB client
   - JWT authentication
   - TOTP 2FA support

3. **Configurazione**:
   - Systemd service (auto-start)
   - Nginx reverse proxy
   - Environment variables
   - Log directories

4. **Frontend**:
   - Placeholder HTML (temporaneo)
   - Full frontend sarà caricato dopo

---

## 📊 Dopo l'Installazione

### Verifica Servizi

```bash
# Check backend
sudo systemctl status orizon-backend

# Check nginx
sudo systemctl status nginx

# View logs
journalctl -u orizon-backend -f
```

### Test API

```bash
# Health check
curl http://localhost:8000/health

# API docs
curl http://localhost:8000/docs
```

### Accesso Web

- **Frontend**: http://46.101.189.126
- **API**: http://46.101.189.126:8000
- **Docs**: http://46.101.189.126/docs

---

## 🔄 Upload Full Application Code

Dopo l'installazione base, carica l'applicazione completa:

### Upload Backend

```bash
# Dal tuo Mac:
cd /Users/marcolorenzi/Windsurf/MCP-Server-LocalModelCyber/OrizonZeroTrustConnect/backend
tar --exclude='venv' --exclude='__pycache__' -czf /tmp/backend.tar.gz .
scp /tmp/backend.tar.gz orizzonti@46.101.189.126:~/orizon-ztc/backend/

# Sul server:
cd ~/orizon-ztc/backend
tar -xzf backend.tar.gz
rm backend.tar.gz
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart orizon-backend
```

### Build & Upload Frontend

```bash
# Dal tuo Mac:
cd /Users/marcolorenzi/Windsurf/MCP-Server-LocalModelCyber/OrizonZeroTrustConnect/frontend

# Install dependencies (if not done)
npm install

# Build for production
export VITE_API_BASE_URL="http://46.101.189.126/api/v1"
export VITE_WS_URL="ws://46.101.189.126/ws"
npm run build

# Upload
tar -czf /tmp/frontend.tar.gz -C dist .
scp /tmp/frontend.tar.gz orizzonti@46.101.189.126:~/orizon-ztc/frontend/

# Sul server:
cd ~/orizon-ztc/frontend
tar -xzf frontend.tar.gz
rm frontend.tar.gz
sudo systemctl restart nginx
```

---

## 👤 Crea Utente Admin

```bash
# Sul server:
cd ~/orizon-ztc/backend
source venv/bin/activate

# Crea utente (interattivo)
python3 << 'PYEOF'
import asyncio
from app.db.database import get_db
from app.models.user import User
from app.auth.security import get_password_hash

async def create_admin():
    async for db in get_db():
        admin = User(
            email="admin@orizon.syneto.net",
            full_name="Marco Lorenzi",
            hashed_password=get_password_hash("AdminPassword2025!"),
            role="superuser",
            is_active=True
        )
        db.add(admin)
        await db.commit()
        print("✓ Admin user created!")
        print(f"  Email: {admin.email}")
        print(f"  Password: AdminPassword2025!")

asyncio.run(create_admin())
PYEOF
```

---

## 🔧 Comandi Utili

```bash
# Restart services
sudo systemctl restart orizon-backend nginx

# View logs
journalctl -u orizon-backend -f
tail -f ~/orizon-ztc/logs/backend.log

# Stop/Start
sudo systemctl stop orizon-backend
sudo systemctl start orizon-backend

# Check listening ports
sudo ss -tlnp | grep -E ':(80|8000)'

# Test backend directly
curl -v http://localhost:8000/health
```

---

## 🐛 Troubleshooting

### Backend non si avvia

```bash
# Check logs
journalctl -u orizon-backend -n 50

# Run manually for debugging
cd ~/orizon-ztc/backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Nginx error

```bash
# Test configuration
sudo nginx -t

# Check logs
sudo tail -f /var/log/nginx/error.log
```

### Port già in uso

```bash
# Find process
sudo lsof -i :8000

# Kill if needed
sudo kill -9 <PID>
```

---

## 📞 Support

Se hai problemi:

1. Controlla i log: `journalctl -u orizon-backend -f`
2. Verifica porte: `sudo ss -tlnp | grep 8000`
3. Test health: `curl http://localhost:8000/health`

---

**Preparato da**: Claude Code
**Per**: Marco Lorenzi @ Syneto/Orizon
**Data**: 2025-01-06
