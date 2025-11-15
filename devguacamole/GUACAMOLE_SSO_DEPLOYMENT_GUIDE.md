# Guacamole SSO Integration - Deployment & Testing Guide

## 📊 Status Attuale: 95% Completato

### ✅ Componenti Completati

1. **Database PostgreSQL** ✓
   - 5 tabelle create e configurate
   - Server Guacamole hub registrato (167.71.33.70)

2. **Backend Services** ✓
   - `guacamole_sso_service.py` - Servizio SSO completo
   - `guacamole_endpoints_fixed.py` - API endpoints con JWT auth
   - Dipendenze installate (aiohttp, asyncpg)

3. **Frontend React** ✓
   - `GuacamolePage.jsx` - Componente Remote Access creato
   - Route `/guacamole` aggiunta in App.jsx
   - Menu "Remote Access" con icona Monitor aggiunto
   - **Frontend deployed su server**: https://46.101.189.126

4. **Libreria Node.js/TypeScript** ✓
   - Progetto completo in `devguacamole/`
   - CLI commands funzionanti
   - SSO integration implementata

---

## ⚠️ AZIONE RICHIESTA: Deploy File Endpoints Backend

### Problema
Il file `guacamole_endpoints.py` sul server ha errori di sintassi e non può essere deployato automaticamente.

### Soluzione - Deploy Manuale (OBBLIGATORIO)

#### Opzione 1: Deploy via SCP (Consigliato)

```bash
# Dalla tua macchina locale (nella directory del progetto)
cd /Users/marcolorenzi/Windsurf/MCP-Server-LocalModelCyber/OrizonZeroTrustConnect

# 1. Copia il file corretto sul server
scp devguacamole/integration/backend/guacamole_endpoints_fixed.py \
    orizonai@46.101.189.126:/tmp/guac_fixed.py

# 2. Connettiti al server e diventa root
ssh orizonai@46.101.189.126
sudo su -

# 3. Backup file attuale
cp /root/orizon-ztc/backend/app/api/v1/endpoints/guacamole_endpoints.py \
   /root/orizon-ztc/backend/app/api/v1/endpoints/guacamole_endpoints.py.broken

# 4. Deploy file corretto
mv /tmp/guac_fixed.py \
   /root/orizon-ztc/backend/app/api/v1/endpoints/guacamole_endpoints.py

# 5. Verifica sintassi Python
python3 -m py_compile \
   /root/orizon-ztc/backend/app/api/v1/endpoints/guacamole_endpoints.py

# Se nessun errore, procedi:

# 6. Pulisci cache Python
find /root/orizon-ztc/backend/app -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# 7. Riavvia backend
systemctl restart orizon-backend

# 8. Verifica status
systemctl status orizon-backend
```

#### Opzione 2: Copia/Incolla con nano

Se SCP fallisce:

```bash
ssh orizonai@46.101.189.126
sudo nano /root/orizon-ztc/backend/app/api/v1/endpoints/guacamole_endpoints.py
```

Copia TUTTO il contenuto da:
`devguacamole/integration/backend/guacamole_endpoints_fixed.py`

Salva (Ctrl+O, Enter, Ctrl+X) e riavvia:
```bash
sudo systemctl restart orizon-backend
```

---

## 🧪 Test End-to-End - Post Deployment

### Test 1: Verifica Backend

```bash
# Test health endpoint (non richiede auth)
curl -k https://46.101.189.126/api/v1/guacamole/health

# Expected output:
# {"status":"healthy","timestamp":"2025-11-09T..."}
# oppure
# {"status":"unhealthy",...}
```

**Se ricevi `{"detail":"Not Found"}`** → Il file endpoints NON è stato deployato correttamente. Ripeti il deployment.

### Test 2: Login Orizon e SSO Authentication

```bash
# 1. Login su Orizon per ottenere JWT token
TOKEN=$(curl -k -s -X POST https://46.101.189.126/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@orizon.local","password":"admin123"}' \
  | jq -r '.access_token')

# Verifica token
echo "Token: $TOKEN"

# 2. Test SSO Authentication con Guacamole
curl -k -s -X POST https://46.101.189.126/api/v1/guacamole/sso/authenticate \
  -H "Authorization: Bearer $TOKEN" | jq

# Expected output:
# {
#   "session_id": "uuid...",
#   "guacamole_token": "long-token-string",
#   "username": "orizonzerotrust",
#   "datasource": "mysql",
#   "expires_in": 3600
# }
```

### Test 3: Quick Access SSH

```bash
# 1. Ottieni lista nodi
curl -k -s https://46.101.189.126/api/v1/nodes \
  -H "Authorization: Bearer $TOKEN" | jq '.items[] | {id, name, status}'

# 2. Seleziona un nodo ONLINE e copia il suo ID

# 3. Quick access SSH (sostituisci NODE_ID)
NODE_ID="uuid-del-nodo-online"

curl -k -s -X POST \
  "https://46.101.189.126/api/v1/guacamole/nodes/$NODE_ID/access/ssh" \
  -H "Authorization: Bearer $TOKEN" | jq

# Expected output:
# {
#   "connection_id": "1",
#   "access_url": "https://167.71.33.70/guacamole/#/client/1?token=...",
#   "guacamole_token": "token...",
#   "protocol": "ssh"
# }
```

### Test 4: Accesso Web UI

1. **Apri browser**: https://46.101.189.126
2. **Login**: admin@orizon.local / admin123
3. **Vai al menu "Remote Access"** (icona Monitor nella sidebar)
4. **Verifica**:
   - Badge "Guacamole Hub Online" verde in alto
   - Lista nodi online visualizzata
   - Pulsanti "SSH Terminal" e "RDP Desktop" attivi

5. **Test connessione**:
   - Click su "SSH Terminal" per un nodo online
   - Dovrebbe:
     - Mostrare toast "Authenticating with Guacamole..."
     - Poi "Access granted! Opening terminal..."
     - Aprire nuova finestra con terminale Guacamole

---

## 📋 Verifica Database

Controlla che le sessioni vengano registrate:

```bash
ssh orizonai@46.101.189.126
sudo su - postgres
psql -d orizon_ztc

-- Verifica sessioni SSO
SELECT
  id,
  user_id,
  LEFT(guacamole_token, 50) as token_preview,
  expires_at,
  created_at
FROM guacamole_sessions
ORDER BY created_at DESC
LIMIT 5;

-- Verifica access logs
SELECT
  user_id,
  action,
  success,
  error_message,
  created_at
FROM guacamole_access_logs
ORDER BY created_at DESC
LIMIT 10;

-- Verifica connessioni create
SELECT
  gc.id,
  n.name as node_name,
  gc.protocol,
  gc.connection_name,
  gc.status,
  gc.created_at
FROM guacamole_connections gc
JOIN nodes n ON gc.node_id = n.id
ORDER BY gc.created_at DESC;

\q
exit
```

---

## 🔧 Troubleshooting

### Problema: Health check ritorna 404

**Causa**: File endpoints non deployato correttamente

**Soluzione**:
```bash
# Verifica import
sudo su -
cd /root/orizon-ztc/backend
source venv/bin/activate
python3 -c "from app.guacamole import router; print('OK')"

# Se errore, rideploya il file endpoints
```

### Problema: SSO authentication ritorna 401

**Causa**: Token JWT non valido o scaduto

**Soluzione**:
```bash
# Rigenera token
TOKEN=$(curl -k -s -X POST https://46.101.189.126/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@orizon.local","password":"admin123"}' \
  | jq -r '.access_token')
```

### Problema: Guacamole Hub Offline

**Causa**: Server Guacamole 167.71.33.70 non raggiungibile

**Verifica**:
```bash
# Test diretto Guacamole
curl -k https://167.71.33.70/guacamole/

# Verifica servizi Docker
ssh orizonzerotrust@167.71.33.70
sudo docker ps

# Riavvia se necessario
cd /root/guacamole
sudo docker-compose restart
```

### Problema: Quick access fallisce con errore

**Causa**: Credenziali nodo non corrette

**Verifica**:
```bash
# Le credenziali sono hardcoded in guacamole_endpoints.py:231-232
# username='parallels'
# password='profano.69'

# Se il nodo ha credenziali diverse, modifica il file endpoints
```

---

## 🎯 Checklist Finale

- [ ] File endpoints deployato con successo
- [ ] Backend riavviato senza errori
- [ ] Health check ritorna `{"status":"healthy"}`
- [ ] SSO authentication ritorna `session_id` e `guacamole_token`
- [ ] Quick access SSH ritorna `access_url` valido
- [ ] Frontend mostra menu "Remote Access"
- [ ] Click SSH apre terminale Guacamole
- [ ] Database registra sessioni e access logs

---

## 📚 Documentazione Completa

- **Integrazione Backend**: `devguacamole/integration/backend/INTEGRATION_INSTRUCTIONS.md`
- **Schema Database**: `devguacamole/integration/database/001_guacamole_tables.sql`
- **SSO Summary**: `devguacamole/SSO_INTEGRATION_SUMMARY.md`
- **Libreria Node.js**: `devguacamole/README.md`

---

## 🔐 Security Checklist (Post-Produzione)

Dopo i test, applica queste migliorie:

1. **Cambia password Guacamole admin**:
   ```bash
   ssh orizonzerotrust@167.71.33.70
   sudo docker exec guacamole-mysql mysql -u guacamole -p guacamole_db
   # Cambia password per orizonzerotrust
   ```

2. **Abilita TLS verification**:
   ```bash
   # Nel backend .env
   GUAC_VERIFY_TLS=true
   ```

3. **Implementa rotazione token**:
   - Configura cron job per cleanup sessioni scadute

4. **Usa secret manager**:
   - Sposta credenziali da environment variables a HashiCorp Vault

5. **Abilita MFA per admin Orizon**

---

**Creato**: 2025-11-09 19:30 UTC
**Versione**: 1.0
**Status**: Ready for deployment and testing

---

## 🆘 Support

Per problemi durante deployment:
1. Controlla logs backend: `sudo journalctl -u orizon-backend -n 100`
2. Verifica sintassi endpoints: `python3 -m py_compile guacamole_endpoints.py`
3. Testa import router: `python3 -c "from app.guacamole import router; print('OK')"`

**File critico da deployare**: `devguacamole/integration/backend/guacamole_endpoints_fixed.py`
