# Integrazione SSO Guacamole - Riepilogo Completo

## ✅ Completato

### 1. Database
- ✅ **5 tabelle create** in PostgreSQL (`orizon_ztc`):
  - `guacamole_servers` - Server Guacamole
  - `guacamole_connections` - Connessioni nodi → Guacamole
  - `guacamole_user_mappings` - Mapping utenti SSO
  - `guacamole_sessions` - Sessioni attive SSO
  - `guacamole_access_logs` - Audit log
- ✅ **Server primario registrato**: Primary Guacamole Hub (167.71.33.70)

### 2. Backend Python
- ✅ **Servizio SSO**: `/root/orizon-ztc/backend/app/services/guacamole_sso_service.py`
  - Autenticazione admin Guacamole
  - Gestione token
  - CRUD connessioni
  - Grant permessi
- ✅ **Endpoints API**: `/root/orizon-ztc/backend/app/api/v1/endpoints/guacamole_endpoints.py`
  - Health check
  - SSO authentication
  - Node connections management
  - Quick access
- ✅ **Router wrapper**: `/root/orizon-ztc/backend/app/guacamole.py`
- ✅ **Dipendenze installate**: aiohttp, asyncpg

### 3. Libreria Node.js
- ✅ **Progetto TypeScript completo**: `devguacamole/`
  - API client con retry/logging
  - Secret store pluggable
  - SSO integration
  - CLI comandi
  - Tests

---

## 🔧 Da Completare

### 1. Fix Autenticazione Endpoint (PRIORITÀ ALTA)

Il problema attuale: gli endpoint non hanno la dependency `get_current_user` corretta.

**Soluzione**:

Modifica `/root/orizon-ztc/backend/app/api/v1/endpoints/guacamole_endpoints.py`:

1. Importa la dependency:
```python
from app.main_minimal import get_current_user
```

2. Modifica tutti i metodi sostituendo `current_user: dict` con:
```python
current_user: dict = Depends(get_current_user)
```

3. Endpoint `/health` non richiede auth, modificalo così:
```python
@router.get("/health")
async def health_check(guac_service=Depends(get_guac_service)):
    # ... resto del codice invariato
```

4. Riavvia backend:
```bash
sudo systemctl restart orizon-backend
```

5. Testa:
```bash
curl -k https://46.101.189.126/api/v1/guacamole/health
```

### 2. Frontend React Components

Crea i seguenti componenti in `/var/www/orizon-ztc-source/frontend/src/`:

#### A. Menu Guacamole (`pages/GuacamolePage.jsx`)
```jsx
import { useState, useEffect } from 'react';
import axios from 'axios';

export default function GuacamolePage() {
  const [nodes, setNodes] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchNodes();
  }, []);

  const fetchNodes = async () => {
    try {
      const response = await axios.get('/api/v1/nodes', {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
      });
      setNodes(response.data);
    } catch (error) {
      console.error('Error fetching nodes:', error);
    } finally {
      setLoading(false);
    }
  };

  const quickAccess = async (nodeId, protocol) => {
    try {
      const response = await axios.post(
        `/api/v1/guacamole/nodes/${nodeId}/access/${protocol}`,
        {},
        { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } }
      );

      // Apri Guacamole in nuova finestra
      window.open(response.data.access_url, '_blank');
    } catch (error) {
      console.error('Error accessing node:', error);
      alert('Errore nell\'accesso al nodo');
    }
  };

  return (
    <div className="container mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">Guacamole Remote Access</h1>

      {loading ? (
        <div>Caricamento...</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {nodes.map(node => (
            <div key={node.id} className="border rounded-lg p-4 shadow">
              <h3 className="text-xl font-semibold mb-2">{node.name}</h3>
              <p className="text-gray-600 mb-4">{node.ip_address}</p>

              <div className="space-y-2">
                <button
                  onClick={() => quickAccess(node.id, 'ssh')}
                  className="w-full bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600"
                >
                  SSH Access
                </button>
                <button
                  onClick={() => quickAccess(node.id, 'rdp')}
                  className="w-full bg-green-500 text-white px-4 py-2 rounded hover:bg-green-600"
                >
                  RDP Access
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

#### B. Aggiungi Route in App
In `/var/www/orizon-ztc-source/frontend/src/App.jsx`:

```jsx
import GuacamolePage from './pages/GuacamolePage';

// Dentro il Router:
<Route path="/guacamole" element={<GuacamolePage />} />
```

#### C. Aggiungi Menu Item
Nel componente navigation/menu:

```jsx
<NavLink to="/guacamole" icon={<TerminalIcon />}>
  Remote Access
</NavLink>
```

### 3. Build e Deploy Frontend

```bash
ssh orizonai@46.101.189.126
cd /var/www/orizon-ztc-source/frontend
npm run build
sudo cp -r dist/* /var/www/orizon-ztc/dist/
```

---

## 🧪 Test End-to-End SSO

### Test 1: Health Check
```bash
curl -k https://46.101.189.126/api/v1/guacamole/health
```

**Atteso**: `{"status":"healthy","timestamp":"..."}`

### Test 2: SSO Authentication
```bash
# Login Orizon
TOKEN=$(curl -k -s -X POST https://46.101.189.126/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@orizon.local","password":"admin123"}' \
  | jq -r '.access_token')

# SSO Guacamole
curl -k -s -X POST https://46.101.189.126/api/v1/guacamole/sso/authenticate \
  -H "Authorization: Bearer $TOKEN" | jq
```

**Atteso**: `{"session_id":"...","guacamole_token":"...","username":"orizonzerotrust",...}`

### Test 3: Quick Access SSH
```bash
# Ottieni ID nodo Edge Ubuntu
NODE_ID=$(curl -k -s https://46.101.189.126/api/v1/nodes \
  -H "Authorization: Bearer $TOKEN" \
  | jq -r '.[] | select(.name | contains("Edge Ubuntu")) | .id')

# Quick Access SSH
curl -k -s -X POST "https://46.101.189.126/api/v1/guacamole/nodes/$NODE_ID/access/ssh" \
  -H "Authorization: Bearer $TOKEN" | jq
```

**Atteso**: `{"connection_id":"1","access_url":"https://167.71.33.70/guacamole/#/client/1?token=...","protocol":"ssh"}`

### Test 4: Accesso Web
1. Login su https://46.101.189.126/login
2. Vai a menu "Remote Access" o `/guacamole`
3. Clicca "SSH Access" su un nodo
4. Verifica che si apre il terminale Guacamole

---

## 📋 Endpoint API Disponibili

| Endpoint | Method | Auth | Descrizione |
|----------|--------|------|-------------|
| `/api/v1/guacamole/health` | GET | ❌ | Health check server |
| `/api/v1/guacamole/sso/authenticate` | POST | ✅ | Autenticazione SSO |
| `/api/v1/guacamole/nodes/{id}/connections` | POST | ✅ | Crea connessione |
| `/api/v1/guacamole/nodes/{id}/connections` | GET | ✅ | Lista connessioni nodo |
| `/api/v1/guacamole/nodes/{id}/access/{protocol}` | POST | ✅ | Quick access (SSO) |
| `/api/v1/guacamole/connections` | GET | ✅ | Lista tutte connessioni |
| `/api/v1/guacamole/connections/{id}` | DELETE | ✅ | Elimina connessione |

---

## 🔐 Security Checklist

- [ ] Cambia password Guacamole (guacadmin/guacadmin)
- [ ] Abilita TLS verification in produzione
- [ ] Implementa rotazione token
- [ ] Aggiungi rate limiting
- [ ] Abilita audit logging completo
- [ ] Usa vault per password (non environment variables)
- [ ] Implementa MFA per admin
- [ ] Configura session timeout

---

## 📝 Variabili d'Ambiente (.env backend)

```bash
# Guacamole
GUAC_URL=https://167.71.33.70/guacamole
GUAC_DATASOURCE=mysql
GUAC_ADMIN_USER=orizonzerotrust
GUAC_ADMIN_PASS=ripper-FfFIlBelloccio.1969F-web
GUAC_VERIFY_TLS=false

# Database (verifica siano presenti)
ORIZON_DB_HOST=46.101.189.126
ORIZON_DB_PORT=5432
ORIZON_DB_USER=postgres
ORIZON_DB_NAME=orizon_ztc
```

---

## 🚀 Deployment Checklist

- [x] Database tables created
- [x] Backend services copied
- [x] Dependencies installed
- [ ] Auth dependency fixed
- [ ] Backend restarted and tested
- [ ] Frontend components created
- [ ] Frontend built and deployed
- [ ] End-to-end SSO test passed
- [ ] Production credentials secured

---

## 📚 Documentazione

- **Progetto Node.js**: `devguacamole/README.md`
- **Backend Integration**: `devguacamole/integration/backend/INTEGRATION_INSTRUCTIONS.md`
- **Database Schema**: `devguacamole/integration/database/001_guacamole_tables.sql`
- **Guacamole API**: https://guacamole.apache.org/api-documentation/

---

## 🆘 Troubleshooting

### Backend Errors
```bash
sudo journalctl -u orizon-backend -n 100 --no-pager
```

### Test Imports
```bash
cd /root/orizon-ztc/backend
source venv/bin/activate
python3 -c "from app.guacamole import router; print('OK')"
```

### Database Queries
```bash
sudo -u postgres psql -d orizon_ztc -c "SELECT * FROM guacamole_servers;"
```

---

## ⚠️  DEPLOYMENT MANUALE NECESSARIO

### Problema Identificato
Il file `guacamole_endpoints.py` sul server ha un errore di indentazione (linea 77) e usa codice incompatibile con il nuovo servizio SSO.

### Soluzione - Deployment Manuale

**Metodo 1: Copia File Fixed (Consigliato)**

Dal tuo computer locale:

```bash
# 1. Connettiti al server come root o con utente che ha permessi completi
ssh orizonai@46.101.189.126

# 2. Diventa root
sudo su -

# 3. Backup file attuale
cp /root/orizon-ztc/backend/app/api/v1/endpoints/guacamole_endpoints.py \
   /root/orizon-ztc/backend/app/api/v1/endpoints/guacamole_endpoints.py.broken

# 4. Copia il file fixed dalla tua macchina locale
# Sul tuo computer:
scp devguacamole/integration/backend/guacamole_endpoints_fixed.py \
    orizonai@46.101.189.126:/tmp/guac_fixed.py

# Di nuovo sul server come root:
mv /tmp/guac_fixed.py /root/orizon-ztc/backend/app/api/v1/endpoints/guacamole_endpoints.py

# 5. Verifica sintassi
python3 -m py_compile /root/orizon-ztc/backend/app/api/v1/endpoints/guacamole_endpoints.py

# 6. Riavvia backend
systemctl restart orizon-backend

# 7. Testa
curl -k https://46.101.189.126/api/v1/guacamole/health
```

**Metodo 2: Editor Manuale**

Se il Metodo 1 fallisce per problemi di permessi:

```bash
ssh orizonai@46.101.189.126
sudo nano /root/orizon-ztc/backend/app/api/v1/endpoints/guacamole_endpoints.py
```

Il file deve contenere esattamente:
- Import da `app.main_minimal` (NON da app.db.database o app.auth.security)
- Router con prefix="/guacamole"
- Dependency `get_guac_service()` che istanzia GuacamoleSSO
- Tutti gli endpoint con `current_user = Depends(get_current_user)`

Il file corretto completo è disponibile in:
`devguacamole/integration/backend/guacamole_endpoints_fixed.py`

### Verifica Post-Deployment

```bash
# Test 1: Sintassi Python
sudo python3 -m py_compile /root/orizon-ztc/backend/app/api/v1/endpoints/guacamole_endpoints.py

# Test 2: Import router
sudo -u orizonai bash -c 'cd /root/orizon-ztc/backend && source venv/bin/activate && python3 -c "from app.guacamole import router; print(f\"Routes: {len(router.routes)}\")"'

# Test 3: Backend running
sudo systemctl status orizon-backend

# Test 4: Health endpoint
curl -k https://46.101.189.126/api/v1/guacamole/health
# Expected: {"status":"healthy"|"unhealthy","timestamp":"..."}

# Test 5: SSO Authentication
TOKEN=$(curl -k -s -X POST https://46.101.189.126/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@orizon.local","password":"admin123"}' | jq -r '.access_token')

curl -k -X POST https://46.101.189.126/api/v1/guacamole/sso/authenticate \
  -H "Authorization: Bearer $TOKEN" | jq
# Expected: {"session_id":"...","guacamole_token":"..."}
```

---

**Status**: 85% Complete - Deployment manuale endpoints richiesto, poi frontend
**Aggiornato**: 2025-11-09 18:10 UTC
**Versione**: 1.1
