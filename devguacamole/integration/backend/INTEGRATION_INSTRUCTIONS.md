# Integrazione Backend Guacamole - Istruzioni

## File da Copiare sul Server Orizon

### 1. Copiare i servizi Python

```bash
# Dalla tua macchina locale
cd /Users/marcolorenzi/Windsurf/MCP-Server-LocalModelCyber/OrizonZeroTrustConnect/devguacamole

# Copia servizio SSO
sshpass -p 'ripper-FfFIlBelloccio.1969F' scp -o StrictHostKeyChecking=no \
  integration/backend/guacamole_sso_service.py \
  orizonai@46.101.189.126:/root/orizon-ztc/backend/app/services/

# Copia endpoints API
sshpass -p 'ripper-FfFIlBelloccio.1969F' scp -o StrictHostKeyChecking=no \
  integration/backend/guacamole_endpoints.py \
  orizonai@46.101.189.126:/root/orizon-ztc/backend/app/api/v1/endpoints/
```

### 2. Modificare main_minimal.py

Aggiungi questa riga nell'area degli import (circa linea 30):

```python
from app.api.v1.endpoints.guacamole_endpoints import router as guacamole_router
```

Aggiungi questa riga nell'area dove vengono inclusi i router (cerca `app.include_router`):

```python
app.include_router(guacamole_router)
```

### 3. Aggiungere Variabili d'Ambiente

Sul server Orizon, aggiungi al file `.env`:

```bash
# Guacamole Configuration
GUAC_URL=https://167.71.33.70/guacamole
GUAC_DATASOURCE=mysql
GUAC_ADMIN_USER=orizonzerotrust
GUAC_ADMIN_PASS=ripper-FfFIlBelloccio.1969F-web
GUAC_VERIFY_TLS=false

# Database (già presenti, verifica)
ORIZON_DB_HOST=46.101.189.126
ORIZON_DB_PORT=5432
ORIZON_DB_USER=postgres
ORIZON_DB_NAME=orizon_ztc
```

### 4. Installare Dipendenze Python

```bash
ssh orizonai@46.101.189.126
cd /root/orizon-ztc/backend
source venv/bin/activate
pip install aiohttp asyncpg
```

### 5. Riavviare Backend

```bash
sudo systemctl restart orizon-backend
sudo systemctl status orizon-backend
```

### 6. Verificare Installazione

```bash
# Test health check
curl -k https://46.101.189.126/api/v1/guacamole/health

# Dovrebbe rispondere con:
# {"status":"healthy","timestamp":"..."}
```

## Endpoint API Disponibili

### Health Check
```
GET /api/v1/guacamole/health
```

### SSO Authentication
```
POST /api/v1/guacamole/sso/authenticate
Headers: Authorization: Bearer <JWT_TOKEN>
```

### Create Connection for Node
```
POST /api/v1/guacamole/nodes/{node_id}/connections
Body: {
  "node_id": "uuid",
  "protocol": "ssh|rdp|vnc",
  "connection_name": "optional"
}
```

### Get Node Connections
```
GET /api/v1/guacamole/nodes/{node_id}/connections
```

### Quick Access
```
POST /api/v1/guacamole/nodes/{node_id}/access/{protocol}
```

### List All Connections
```
GET /api/v1/guacamole/connections
```

### Delete Connection
```
DELETE /api/v1/guacamole/connections/{connection_id}
```

## Note Importanti

1. **Autenticazione**: Tutti gli endpoint richiedono JWT token Orizon valido
2. **SSO**: Gli admin/superuser ottengono accesso completo Guacamole
3. **Database**: Le tabelle sono già create (vedi 001_guacamole_tables.sql)
4. **Logging**: Tutti gli accessi vengono registrati in `guacamole_access_logs`

## Troubleshooting

### Backend non parte

```bash
# Controlla errori
sudo journalctl -u orizon-backend -n 50

# Verifica import
cd /root/orizon-ztc/backend
source venv/bin/activate
python3 -c "from app.api.v1.endpoints.guacamole_endpoints import router"
```

### Errore di connessione al database

```bash
# Verifica postgres
sudo -u postgres psql -d orizon_ztc -c "\dt guacamole*"
```

### Guacamole non raggiungibile

```bash
# Test connessione
curl -k https://167.71.33.70/guacamole/api/tokens -X POST \
  -d "username=orizonzerotrust&password=ripper-FfFIlBelloccio.1969F-web"
```
