# 📚 API Reference - Orizon Zero Trust Connect

**Versione:** 1.0.0
**Base URL:** `http://localhost:8000/api/v1`
**Last Updated:** Gennaio 2025
**Autore:** Marco Lorenzi @ Syneto/Orizon

---

## 📋 Indice

1. [Introduzione](#introduzione)
2. [Autenticazione](#autenticazione)
3. [Endpoints Auth](#endpoints-auth)
4. [Endpoints 2FA](#endpoints-2fa)
5. [Endpoints Users](#endpoints-users)
6. [Endpoints Nodes](#endpoints-nodes)
7. [Endpoints Tunnels](#endpoints-tunnels)
8. [Endpoints ACL](#endpoints-acl)
9. [Endpoints Audit](#endpoints-audit)
10. [Endpoints Metrics](#endpoints-metrics)
11. [WebSocket](#websocket)
12. [Error Handling](#error-handling)
13. [Rate Limiting](#rate-limiting)

---

## 🎯 Introduzione

L'API di Orizon Zero Trust Connect è una REST API basata su FastAPI che utilizza JSON per request e response.

### Caratteristiche

- **REST Architecture** - Endpoint RESTful con metodi HTTP standard
- **JSON Format** - Tutti i dati in formato JSON
- **JWT Authentication** - Token-based authentication
- **Rate Limiting** - Rate limiting basato su ruoli
- **Versioning** - API versionata (v1)
- **OpenAPI/Swagger** - Documentazione interattiva su `/docs`

### Base URLs

| Ambiente | Base URL |
|----------|----------|
| Development | `http://localhost:8000/api/v1` |
| Staging | `https://api.staging.orizon.syneto.net/api/v1` |
| Production | `https://api.orizon.syneto.net/api/v1` |

### Content Type

Tutte le richieste e risposte utilizzano:
```
Content-Type: application/json
```

---

## 🔐 Autenticazione

### JWT Token Authentication

L'API utilizza JWT (JSON Web Tokens) per l'autenticazione.

#### Flow di Autenticazione

```
1. POST /auth/login (email + password)
   → Ricevi: requires_2fa (true/false)

2a. Se 2FA non abilitato:
    → Ricevi: access_token + refresh_token
    → Salva tokens

2b. Se 2FA abilitato:
    → POST /auth/verify-2fa (totp_code)
    → Ricevi: access_token + refresh_token
    → Salva tokens

3. Usa access_token in header Authorization:
   Authorization: Bearer <access_token>

4. Quando access_token scade (24h):
   → POST /auth/refresh (refresh_token)
   → Ricevi: nuovo access_token
```

#### Header Authentication

Per tutte le richieste autenticate:

```http
GET /api/v1/nodes HTTP/1.1
Host: api.orizon.syneto.net
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json
```

#### Token Expiration

| Token Type | Validity | Renewable |
|------------|----------|-----------|
| Access Token | 24 ore | No (usa refresh) |
| Refresh Token | 7 giorni | Sì (rolling) |

---

## 🔑 Endpoints Auth

### POST /auth/login

Login con email e password (step 1).

**Request:**
```http
POST /api/v1/auth/login HTTP/1.1
Content-Type: application/json

{
  "email": "admin@orizon.local",
  "password": "changeme123"
}
```

**Response (2FA non abilitato):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {
    "id": "uuid-here",
    "email": "admin@orizon.local",
    "role": "SuperUser",
    "is_2fa_enabled": false
  }
}
```

**Response (2FA abilitato):**
```json
{
  "requires_2fa": true,
  "message": "2FA verification required",
  "temp_token": "temp-token-for-2fa-verification"
}
```

**Errori:**
- `400` - Email o password mancanti
- `401` - Credenziali non valide
- `403` - Account disabilitato o bloccato

---

### POST /auth/verify-2fa

Verifica codice 2FA TOTP (step 2).

**Request:**
```http
POST /api/v1/auth/verify-2fa HTTP/1.1
Content-Type: application/json

{
  "temp_token": "temp-token-from-login",
  "totp_code": "123456"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {
    "id": "uuid-here",
    "email": "admin@orizon.local",
    "role": "SuperUser",
    "is_2fa_enabled": true
  }
}
```

**Errori:**
- `400` - Codice TOTP non valido
- `401` - Temp token scaduto
- `429` - Troppi tentativi (rate limit)

---

### POST /auth/refresh

Rinnova access token con refresh token.

**Request:**
```http
POST /api/v1/auth/refresh HTTP/1.1
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

**Errori:**
- `401` - Refresh token non valido o scaduto

---

### POST /auth/logout

Logout e invalidazione token.

**Request:**
```http
POST /api/v1/auth/logout HTTP/1.1
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "message": "Successfully logged out"
}
```

---

### GET /auth/me

Ottieni profilo utente corrente.

**Request:**
```http
GET /api/v1/auth/me HTTP/1.1
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "admin@orizon.local",
  "role": "SuperUser",
  "is_active": true,
  "is_2fa_enabled": true,
  "created_at": "2025-01-01T10:00:00Z",
  "last_login": "2025-01-07T14:30:00Z"
}
```

---

## 🔒 Endpoints 2FA

### POST /2fa/setup

Genera secret TOTP e QR code per enrollment.

**Request:**
```http
POST /api/v1/2fa/setup HTTP/1.1
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "secret": "JBSWY3DPEHPK3PXP",
  "qr_code": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUg...",
  "manual_entry_key": "JBSWY3DPEHPK3PXP",
  "issuer": "Orizon ZTC",
  "account_name": "admin@orizon.local"
}
```

**Note:**
- Il QR code può essere scansionato con Google Authenticator o Authy
- `manual_entry_key` può essere inserito manualmente se QR code non funziona

---

### POST /2fa/enable

Abilita 2FA dopo aver verificato il codice TOTP.

**Request:**
```http
POST /api/v1/2fa/enable HTTP/1.1
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "totp_code": "123456"
}
```

**Response:**
```json
{
  "message": "2FA enabled successfully",
  "backup_codes": [
    "ABCD-1234-EFGH-5678",
    "IJKL-9012-MNOP-3456",
    "QRST-7890-UVWX-1234",
    "YZAB-4567-CDEF-8901",
    "GHIJ-2345-KLMN-6789",
    "OPQR-0123-STUV-4567",
    "WXYZ-8901-ABCD-2345",
    "EFGH-6789-IJKL-0123",
    "MNOP-4567-QRST-8901",
    "UVWX-2345-YZAB-6789"
  ]
}
```

**Note:**
- Salvare i backup codes in un posto sicuro
- Ogni backup code è monouso

**Errori:**
- `400` - Codice TOTP non valido
- `409` - 2FA già abilitato

---

### POST /2fa/disable

Disabilita 2FA.

**Request:**
```http
POST /api/v1/2fa/disable HTTP/1.1
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "password": "user-password-for-confirmation"
}
```

**Response:**
```json
{
  "message": "2FA disabled successfully"
}
```

**Errori:**
- `400` - Password non valida
- `404` - 2FA non abilitato

---

### POST /2fa/verify

Verifica codice TOTP (per operazioni sensibili).

**Request:**
```http
POST /api/v1/2fa/verify HTTP/1.1
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "totp_code": "123456"
}
```

**Response:**
```json
{
  "valid": true,
  "message": "Code verified successfully"
}
```

---

### GET /2fa/backup-codes

Genera nuovi backup codes (invalida i precedenti).

**Request:**
```http
GET /api/v1/2fa/backup-codes HTTP/1.1
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "backup_codes": [
    "ABCD-1234-EFGH-5678",
    "IJKL-9012-MNOP-3456",
    // ... altri 8 codici
  ]
}
```

---

### POST /2fa/verify-backup-code

Verifica backup code (one-time use).

**Request:**
```http
POST /api/v1/2fa/verify-backup-code HTTP/1.1
Content-Type: application/json

{
  "temp_token": "temp-token-from-login",
  "backup_code": "ABCD-1234-EFGH-5678"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "message": "Backup code verified. This code has been consumed."
}
```

**Errori:**
- `400` - Backup code non valido o già usato

---

## 👥 Endpoints Users

### GET /users

Lista utenti (con filtri).

**Request:**
```http
GET /api/v1/users?role=Admin&status=active&search=john&limit=20&offset=0 HTTP/1.1
Authorization: Bearer <access_token>
```

**Query Parameters:**
- `role` (optional) - Filtra per ruolo: `SuperUser`, `SuperAdmin`, `Admin`, `User`
- `status` (optional) - Filtra per status: `active`, `inactive`
- `search` (optional) - Cerca per email o nome
- `limit` (optional) - Numero risultati (default: 50, max: 100)
- `offset` (optional) - Offset per paginazione (default: 0)

**Response:**
```json
{
  "total": 42,
  "limit": 20,
  "offset": 0,
  "users": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "email": "john.doe@example.com",
      "role": "Admin",
      "is_active": true,
      "is_2fa_enabled": true,
      "created_at": "2025-01-01T10:00:00Z",
      "last_login": "2025-01-07T14:30:00Z",
      "created_by_id": "uuid-of-creator"
    }
    // ... altri utenti
  ]
}
```

**Permessi:**
- `SuperUser` - Vede tutti gli utenti
- `SuperAdmin` - Vede utenti creati da sé e sotto-utenti
- `Admin` - Vede solo utenti creati da sé
- `User` - 403 Forbidden

---

### POST /users

Crea nuovo utente (RBAC enforced).

**Request:**
```http
POST /api/v1/users HTTP/1.1
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "email": "newuser@example.com",
  "password": "StrongPassword123!",
  "role": "User",
  "is_active": true
}
```

**Response:**
```json
{
  "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "email": "newuser@example.com",
  "role": "User",
  "is_active": true,
  "is_2fa_enabled": false,
  "created_at": "2025-01-07T15:00:00Z",
  "created_by_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Validazioni:**
- Email valida e non già esistente
- Password min 12 caratteri, complessità enforced
- Role valido e creabile dal ruolo corrente
- RBAC hierarchy: puoi creare solo ruoli inferiori al tuo

**Errori:**
- `400` - Dati non validi (email, password debole, etc.)
- `403` - Non autorizzato a creare questo ruolo
- `409` - Email già esistente

---

### GET /users/{user_id}

Ottieni dettagli utente.

**Request:**
```http
GET /api/v1/users/550e8400-e29b-41d4-a716-446655440000 HTTP/1.1
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "john.doe@example.com",
  "role": "Admin",
  "is_active": true,
  "is_2fa_enabled": true,
  "created_at": "2025-01-01T10:00:00Z",
  "last_login": "2025-01-07T14:30:00Z",
  "created_by_id": "parent-user-id",
  "statistics": {
    "nodes_count": 5,
    "tunnels_count": 12,
    "acl_rules_count": 8,
    "last_active": "2025-01-07T14:30:00Z"
  }
}
```

**Errori:**
- `403` - Non autorizzato a vedere questo utente
- `404` - Utente non trovato

---

### PUT /users/{user_id}

Aggiorna utente.

**Request:**
```http
PUT /api/v1/users/550e8400-e29b-41d4-a716-446655440000 HTTP/1.1
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "email": "newemail@example.com",
  "is_active": false
}
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "newemail@example.com",
  "role": "Admin",
  "is_active": false,
  "updated_at": "2025-01-07T15:30:00Z"
}
```

**Campi aggiornabili:**
- `email` - Nuova email (deve essere unica)
- `is_active` - Attiva/disattiva utente
- Non puoi cambiare: `role` (usa PATCH /users/{id}/role), `password` (usa PATCH /users/{id}/password)

**Errori:**
- `403` - Non autorizzato a modificare questo utente
- `404` - Utente non trovato
- `409` - Email già in uso

---

### DELETE /users/{user_id}

Elimina utente (solo SuperUser).

**Request:**
```http
DELETE /api/v1/users/550e8400-e29b-41d4-a716-446655440000 HTTP/1.1
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "message": "User deleted successfully",
  "deleted_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Note:**
- Solo SuperUser può eliminare utenti
- Elimina anche: nodi, tunnel, regole ACL associate
- Azione irreversibile, logged in audit

**Errori:**
- `403` - Solo SuperUser può eliminare utenti
- `404` - Utente non trovato

---

### PATCH /users/{user_id}/role

Cambia ruolo utente (RBAC enforced).

**Request:**
```http
PATCH /api/v1/users/550e8400-e29b-41d4-a716-446655440000/role HTTP/1.1
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "new_role": "SuperAdmin"
}
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "role": "SuperAdmin",
  "updated_at": "2025-01-07T16:00:00Z"
}
```

**Regole RBAC:**
- SuperUser → può cambiare qualsiasi ruolo
- SuperAdmin → può cambiare Admin/User
- Admin → può cambiare solo User
- User → 403 Forbidden

**Errori:**
- `403` - Non autorizzato a cambiare a questo ruolo
- `404` - Utente non trovato

---

### PATCH /users/{user_id}/password

Cambia password utente.

**Request:**
```http
PATCH /api/v1/users/550e8400-e29b-41d4-a716-446655440000/password HTTP/1.1
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "current_password": "OldPassword123!",
  "new_password": "NewStrongPassword456!"
}
```

**Response:**
```json
{
  "message": "Password changed successfully"
}
```

**Validazioni:**
- Password corrente deve essere corretta (se cambi la tua)
- Nuova password min 12 caratteri, complessità enforced
- Non può essere uguale alla vecchia
- Non può essere password comune (blacklist)

**Errori:**
- `400` - Password corrente errata o nuova password debole
- `403` - Non autorizzato a cambiare questa password

---

## 🖥️ Endpoints Nodes

### GET /nodes

Lista nodi registrati.

**Request:**
```http
GET /api/v1/nodes?status=online&type=Linux&location=EU&limit=50&offset=0 HTTP/1.1
Authorization: Bearer <access_token>
```

**Query Parameters:**
- `status` - Filtra per status: `online`, `offline`, `degraded`, `maintenance`
- `type` - Filtra per tipo: `Linux`, `macOS`, `Windows`, `Docker`, `Kubernetes`
- `location` - Filtra per location geografica
- `search` - Cerca per nome o IP
- `limit` - Numero risultati (default: 50)
- `offset` - Offset paginazione

**Response:**
```json
{
  "total": 125,
  "limit": 50,
  "offset": 0,
  "nodes": [
    {
      "id": "node-uuid-1",
      "name": "production-server-01",
      "type": "Linux",
      "ip_address": "192.168.1.100",
      "status": "online",
      "owner_id": "user-uuid",
      "location": {
        "country": "Italy",
        "city": "Milan",
        "latitude": 45.4642,
        "longitude": 9.1900
      },
      "metrics": {
        "cpu_usage": 45.2,
        "memory_usage": 62.8,
        "disk_usage": 78.5,
        "network_rx_bytes": 1024000,
        "network_tx_bytes": 512000
      },
      "tunnels_count": 3,
      "last_seen": "2025-01-07T16:00:00Z",
      "created_at": "2025-01-01T10:00:00Z"
    }
    // ... altri nodi
  ]
}
```

---

### POST /nodes

Registra nuovo nodo.

**Request:**
```http
POST /api/v1/nodes HTTP/1.1
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "name": "my-new-server",
  "type": "Linux",
  "ip_address": "192.168.1.150",
  "location": {
    "country": "Italy",
    "city": "Rome"
  },
  "metadata": {
    "environment": "production",
    "department": "Engineering"
  }
}
```

**Response:**
```json
{
  "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "name": "my-new-server",
  "type": "Linux",
  "ip_address": "192.168.1.150",
  "status": "offline",
  "owner_id": "current-user-id",
  "created_at": "2025-01-07T16:30:00Z",
  "agent_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Note:**
- `agent_token` è restituito solo alla creazione, salvarlo!
- Lo status iniziale è `offline` fino a connessione agent

**Errori:**
- `400` - Dati non validi (nome, IP, tipo)
- `409` - Nome nodo già esistente per questo utente

---

### GET /nodes/{node_id}

Ottieni dettagli nodo.

**Request:**
```http
GET /api/v1/nodes/7c9e6679-7425-40de-944b-e07fc1f90ae7 HTTP/1.1
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "name": "production-server-01",
  "type": "Linux",
  "ip_address": "192.168.1.100",
  "status": "online",
  "owner_id": "user-uuid",
  "location": {
    "country": "Italy",
    "city": "Milan",
    "latitude": 45.4642,
    "longitude": 9.1900
  },
  "metrics": {
    "cpu_usage": 45.2,
    "memory_usage": 62.8,
    "disk_usage": 78.5,
    "uptime_seconds": 86400,
    "load_average": [1.2, 1.5, 1.3]
  },
  "tunnels": [
    {
      "id": "tunnel-uuid-1",
      "type": "SSH",
      "status": "active",
      "local_port": 22,
      "remote_port": 10022
    },
    {
      "id": "tunnel-uuid-2",
      "type": "HTTPS",
      "status": "active",
      "local_port": 443,
      "remote_port": 60443
    }
  ],
  "last_seen": "2025-01-07T16:00:00Z",
  "created_at": "2025-01-01T10:00:00Z"
}
```

---

### PUT /nodes/{node_id}

Aggiorna configurazione nodo.

**Request:**
```http
PUT /api/v1/nodes/7c9e6679-7425-40de-944b-e07fc1f90ae7 HTTP/1.1
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "name": "updated-server-name",
  "location": {
    "country": "Italy",
    "city": "Florence"
  }
}
```

**Response:**
```json
{
  "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "name": "updated-server-name",
  "location": {
    "country": "Italy",
    "city": "Florence"
  },
  "updated_at": "2025-01-07T17:00:00Z"
}
```

---

### DELETE /nodes/{node_id}

Rimuovi nodo (chiude anche tutti i tunnel).

**Request:**
```http
DELETE /api/v1/nodes/7c9e6679-7425-40de-944b-e07fc1f90ae7 HTTP/1.1
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "message": "Node and all associated tunnels deleted successfully",
  "deleted_node_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "deleted_tunnels_count": 3
}
```

---

### GET /nodes/{node_id}/metrics

Ottieni metriche real-time del nodo.

**Request:**
```http
GET /api/v1/nodes/7c9e6679-7425-40de-944b-e07fc1f90ae7/metrics HTTP/1.1
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "node_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "timestamp": "2025-01-07T17:15:00Z",
  "cpu": {
    "usage_percent": 45.2,
    "cores": 8,
    "load_average": [1.2, 1.5, 1.3]
  },
  "memory": {
    "total_bytes": 17179869184,
    "used_bytes": 10795769856,
    "usage_percent": 62.8,
    "available_bytes": 6384099328
  },
  "disk": {
    "total_bytes": 1073741824000,
    "used_bytes": 843597383680,
    "usage_percent": 78.5,
    "free_bytes": 230144440320
  },
  "network": {
    "rx_bytes": 1024000,
    "tx_bytes": 512000,
    "rx_packets": 5000,
    "tx_packets": 3000,
    "rx_errors": 0,
    "tx_errors": 0
  },
  "uptime_seconds": 86400
}
```

---

### GET /nodes/{node_id}/health

Health check del nodo.

**Request:**
```http
GET /api/v1/nodes/7c9e6679-7425-40de-944b-e07fc1f90ae7/health HTTP/1.1
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "node_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "status": "healthy",
  "checks": {
    "agent_connected": true,
    "last_heartbeat": "2025-01-07T17:14:50Z",
    "heartbeat_interval_ok": true,
    "cpu_usage_ok": true,
    "memory_usage_ok": true,
    "disk_usage_ok": true,
    "tunnels_active": 3
  },
  "timestamp": "2025-01-07T17:15:00Z"
}
```

**Status possibili:**
- `healthy` - Tutto OK
- `degraded` - Warning su alcune metriche
- `unhealthy` - Problemi critici
- `offline` - Nodo non raggiungibile

---

## 🔀 Endpoints Tunnels

### GET /tunnels

Lista tunnel attivi.

**Request:**
```http
GET /api/v1/tunnels?node_id=xxx&type=SSH&status=active&limit=50 HTTP/1.1
Authorization: Bearer <access_token>
```

**Query Parameters:**
- `node_id` - Filtra per nodo specifico
- `type` - Filtra per tipo: `SSH`, `HTTPS`
- `status` - Filtra per status: `active`, `inactive`, `connecting`, `error`
- `limit` / `offset` - Paginazione

**Response:**
```json
{
  "total": 28,
  "tunnels": [
    {
      "id": "tunnel-uuid-1",
      "type": "SSH",
      "node_id": "node-uuid-1",
      "node_name": "production-server-01",
      "local_port": 22,
      "remote_port": 10022,
      "status": "active",
      "created_at": "2025-01-05T10:00:00Z",
      "last_active": "2025-01-07T17:15:00Z",
      "stats": {
        "bytes_sent": 10240000,
        "bytes_received": 5120000,
        "latency_ms": 25.5,
        "connections_count": 152
      }
    }
    // ... altri tunnel
  ]
}
```

---

### POST /tunnels

Crea nuovo tunnel (SSH o HTTPS).

**Request:**
```http
POST /api/v1/tunnels HTTP/1.1
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "node_id": "node-uuid-1",
  "type": "SSH",
  "local_port": 22,
  "auto_reconnect": true
}
```

**Response:**
```json
{
  "id": "new-tunnel-uuid",
  "type": "SSH",
  "node_id": "node-uuid-1",
  "local_port": 22,
  "remote_port": 10025,
  "status": "connecting",
  "connection_string": "ssh -p 10025 user@hub.orizon.syneto.net",
  "created_at": "2025-01-07T17:30:00Z"
}
```

**Note:**
- `remote_port` è allocato automaticamente:
  - SSH: range 10000-60000
  - HTTPS: range 60001-65000
- Status iniziale: `connecting`, diventa `active` quando agent si connette

**Errori:**
- `400` - Dati non validi (node_id, local_port)
- `403` - ACL rules negano la creazione
- `404` - Nodo non trovato
- `409` - Porta già in uso
- `507` - Nessuna porta disponibile nel range

---

### GET /tunnels/{tunnel_id}

Ottieni dettagli tunnel.

**Request:**
```http
GET /api/v1/tunnels/tunnel-uuid-1 HTTP/1.1
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "id": "tunnel-uuid-1",
  "type": "SSH",
  "node_id": "node-uuid-1",
  "node": {
    "id": "node-uuid-1",
    "name": "production-server-01",
    "ip_address": "192.168.1.100"
  },
  "local_port": 22,
  "remote_port": 10022,
  "status": "active",
  "auto_reconnect": true,
  "connection_string": "ssh -p 10022 user@hub.orizon.syneto.net",
  "stats": {
    "bytes_sent": 10240000,
    "bytes_received": 5120000,
    "latency_ms": 25.5,
    "uptime_seconds": 172800,
    "reconnects_count": 2,
    "last_reconnect": "2025-01-06T08:00:00Z"
  },
  "created_at": "2025-01-05T10:00:00Z",
  "last_active": "2025-01-07T17:35:00Z"
}
```

---

### DELETE /tunnels/{tunnel_id}

Chiudi tunnel.

**Request:**
```http
DELETE /api/v1/tunnels/tunnel-uuid-1 HTTP/1.1
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "message": "Tunnel closed successfully",
  "tunnel_id": "tunnel-uuid-1",
  "freed_port": 10022
}
```

---

### GET /tunnels/{tunnel_id}/stats

Statistiche dettagliate tunnel.

**Request:**
```http
GET /api/v1/tunnels/tunnel-uuid-1/stats HTTP/1.1
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "tunnel_id": "tunnel-uuid-1",
  "period": "last_24h",
  "stats": {
    "total_bytes_sent": 10240000,
    "total_bytes_received": 5120000,
    "average_latency_ms": 25.5,
    "max_latency_ms": 150.0,
    "min_latency_ms": 10.2,
    "p95_latency_ms": 45.8,
    "p99_latency_ms": 85.2,
    "uptime_percent": 99.8,
    "downtime_seconds": 172,
    "reconnects_count": 2,
    "active_connections": 5,
    "total_connections": 152
  },
  "timestamp": "2025-01-07T17:40:00Z"
}
```

---

### POST /tunnels/{tunnel_id}/reconnect

Forza reconnect del tunnel.

**Request:**
```http
POST /api/v1/tunnels/tunnel-uuid-1/reconnect HTTP/1.1
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "message": "Tunnel reconnection initiated",
  "tunnel_id": "tunnel-uuid-1",
  "status": "connecting"
}
```

---

## 🛡️ Endpoints ACL

### GET /acl/rules

Lista regole ACL (Access Control List).

**Request:**
```http
GET /api/v1/acl/rules?action=ALLOW&enabled=true&priority_min=1&priority_max=50 HTTP/1.1
Authorization: Bearer <access_token>
```

**Query Parameters:**
- `action` - Filtra per azione: `ALLOW`, `DENY`
- `enabled` - Filtra per stato: `true`, `false`
- `priority_min` / `priority_max` - Range priorità (1-100)
- `source_ip` - Filtra per IP sorgente
- `protocol` - Filtra per protocollo: `TCP`, `UDP`, `ICMP`, `ALL`

**Response:**
```json
{
  "total": 15,
  "rules": [
    {
      "id": "rule-uuid-1",
      "name": "Allow SSH from office",
      "priority": 10,
      "action": "ALLOW",
      "source_ip": "203.0.113.0/24",
      "destination_ip": "192.168.1.0/24",
      "protocol": "TCP",
      "destination_port": 22,
      "valid_from": "2025-01-01T00:00:00Z",
      "valid_until": null,
      "time_restrictions": {
        "days_of_week": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
        "time_range": {
          "start": "08:00",
          "end": "18:00"
        }
      },
      "enabled": true,
      "match_count": 1523,
      "created_by_id": "user-uuid",
      "created_at": "2025-01-01T10:00:00Z"
    }
    // ... altre regole
  ]
}
```

---

### POST /acl/rules

Crea nuova regola ACL.

**Request:**
```http
POST /api/v1/acl/rules HTTP/1.1
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "name": "Block external SSH",
  "priority": 5,
  "action": "DENY",
  "source_ip": "0.0.0.0/0",
  "destination_ip": "192.168.1.0/24",
  "protocol": "TCP",
  "destination_port": 22,
  "enabled": true
}
```

**Response:**
```json
{
  "id": "new-rule-uuid",
  "name": "Block external SSH",
  "priority": 5,
  "action": "DENY",
  "source_ip": "0.0.0.0/0",
  "destination_ip": "192.168.1.0/24",
  "protocol": "TCP",
  "destination_port": 22,
  "enabled": true,
  "created_by_id": "current-user-id",
  "created_at": "2025-01-07T18:00:00Z"
}
```

**Validazioni:**
- Priority: 1-100 (lower = higher priority)
- IP addresses in CIDR notation
- Protocol: TCP, UDP, ICMP, ALL
- Port: 1-65535 o 0 per "any"

**Errori:**
- `400` - Dati non validi (IP, priorità, porta)
- `409` - Regola con stessa priorità già esistente

---

### GET /acl/rules/{rule_id}

Ottieni dettagli regola ACL.

**Request:**
```http
GET /api/v1/acl/rules/rule-uuid-1 HTTP/1.1
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "id": "rule-uuid-1",
  "name": "Allow SSH from office",
  "description": "Permit SSH access from office network during business hours",
  "priority": 10,
  "action": "ALLOW",
  "source_ip": "203.0.113.0/24",
  "destination_ip": "192.168.1.0/24",
  "protocol": "TCP",
  "destination_port": 22,
  "valid_from": "2025-01-01T00:00:00Z",
  "valid_until": null,
  "time_restrictions": {
    "days_of_week": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
    "time_range": {
      "start": "08:00",
      "end": "18:00"
    }
  },
  "enabled": true,
  "statistics": {
    "match_count": 1523,
    "last_match": "2025-01-07T17:45:00Z",
    "matches_today": 85
  },
  "created_by_id": "user-uuid",
  "created_at": "2025-01-01T10:00:00Z",
  "updated_at": "2025-01-05T14:20:00Z"
}
```

---

### PUT /acl/rules/{rule_id}

Aggiorna regola ACL.

**Request:**
```http
PUT /api/v1/acl/rules/rule-uuid-1 HTTP/1.1
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "name": "Updated rule name",
  "priority": 15,
  "destination_port": 2222
}
```

**Response:**
```json
{
  "id": "rule-uuid-1",
  "name": "Updated rule name",
  "priority": 15,
  "destination_port": 2222,
  "updated_at": "2025-01-07T18:15:00Z"
}
```

---

### DELETE /acl/rules/{rule_id}

Elimina regola ACL.

**Request:**
```http
DELETE /api/v1/acl/rules/rule-uuid-1 HTTP/1.1
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "message": "ACL rule deleted successfully",
  "rule_id": "rule-uuid-1"
}
```

---

### PATCH /acl/rules/{rule_id}/enable

Abilita regola ACL.

**Request:**
```http
PATCH /api/v1/acl/rules/rule-uuid-1/enable HTTP/1.1
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "id": "rule-uuid-1",
  "enabled": true,
  "updated_at": "2025-01-07T18:20:00Z"
}
```

---

### PATCH /acl/rules/{rule_id}/disable

Disabilita regola ACL.

**Request:**
```http
PATCH /api/v1/acl/rules/rule-uuid-1/disable HTTP/1.1
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "id": "rule-uuid-1",
  "enabled": false,
  "updated_at": "2025-01-07T18:25:00Z"
}
```

---

### POST /acl/evaluate

Testa valutazione regola (dry-run).

**Request:**
```http
POST /api/v1/acl/evaluate HTTP/1.1
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "source_ip": "203.0.113.45",
  "destination_ip": "192.168.1.100",
  "protocol": "TCP",
  "destination_port": 22
}
```

**Response:**
```json
{
  "decision": "ALLOW",
  "matched_rule": {
    "id": "rule-uuid-1",
    "name": "Allow SSH from office",
    "priority": 10,
    "action": "ALLOW"
  },
  "evaluation_time_ms": 2.5,
  "rules_evaluated": 15
}
```

**Possibili decision:**
- `ALLOW` - Connessione permessa
- `DENY` - Connessione negata
- `DEFAULT_DENY` - Nessuna regola matched, default deny (Zero Trust)

---

## 📜 Endpoints Audit

### GET /audit/logs

Query audit logs con filtri avanzati.

**Request:**
```http
GET /api/v1/audit/logs?action=LOGIN&user_id=xxx&date_from=2025-01-01&date_to=2025-01-07&severity=INFO&limit=100 HTTP/1.1
Authorization: Bearer <access_token>
```

**Query Parameters:**
- `action` - Filtra per azione: `LOGIN`, `LOGOUT`, `CREATE_USER`, `DELETE_USER`, `CREATE_TUNNEL`, etc.
- `user_id` - Filtra per utente specifico
- `resource_type` - Filtra per tipo risorsa: `user`, `node`, `tunnel`, `acl_rule`
- `date_from` / `date_to` - Range temporale (ISO 8601)
- `severity` - Filtra per severità: `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- `ip_address` - Filtra per IP sorgente
- `search` - Full-text search
- `limit` / `offset` - Paginazione

**Response:**
```json
{
  "total": 5234,
  "limit": 100,
  "offset": 0,
  "logs": [
    {
      "id": "log-uuid-1",
      "timestamp": "2025-01-07T18:30:15.123Z",
      "action": "CREATE_TUNNEL",
      "user_id": "user-uuid",
      "user_email": "admin@orizon.local",
      "resource_type": "tunnel",
      "resource_id": "tunnel-uuid-1",
      "severity": "INFO",
      "ip_address": "203.0.113.45",
      "user_agent": "Mozilla/5.0...",
      "geolocation": {
        "country": "Italy",
        "city": "Milan",
        "latitude": 45.4642,
        "longitude": 9.1900
      },
      "details": {
        "tunnel_type": "SSH",
        "node_id": "node-uuid-1",
        "local_port": 22,
        "remote_port": 10025
      },
      "result": "success"
    }
    // ... altri log
  ]
}
```

---

### GET /audit/logs/{log_id}

Ottieni dettagli log specifico.

**Request:**
```http
GET /api/v1/audit/logs/log-uuid-1 HTTP/1.1
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "id": "log-uuid-1",
  "timestamp": "2025-01-07T18:30:15.123Z",
  "action": "CREATE_TUNNEL",
  "user_id": "user-uuid",
  "user_email": "admin@orizon.local",
  "user_role": "SuperUser",
  "resource_type": "tunnel",
  "resource_id": "tunnel-uuid-1",
  "severity": "INFO",
  "ip_address": "203.0.113.45",
  "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)...",
  "geolocation": {
    "country": "Italy",
    "city": "Milan",
    "region": "Lombardy",
    "latitude": 45.4642,
    "longitude": 9.1900,
    "timezone": "Europe/Rome"
  },
  "request": {
    "method": "POST",
    "path": "/api/v1/tunnels",
    "query_params": {},
    "body": {
      "node_id": "node-uuid-1",
      "type": "SSH",
      "local_port": 22
    }
  },
  "response": {
    "status_code": 201,
    "body": {
      "id": "tunnel-uuid-1",
      "remote_port": 10025
    }
  },
  "details": {
    "tunnel_type": "SSH",
    "node_name": "production-server-01",
    "acl_rules_evaluated": 5,
    "acl_decision": "ALLOW"
  },
  "result": "success",
  "duration_ms": 125.5
}
```

---

### GET /audit/export

Esporta audit logs in vari formati.

**Request:**
```http
GET /api/v1/audit/export?format=csv&date_from=2025-01-01&date_to=2025-01-07 HTTP/1.1
Authorization: Bearer <access_token>
```

**Query Parameters:**
- `format` - Formato export: `json`, `csv`, `siem` (CEF format)
- Tutti i filtri di `/audit/logs`

**Response (JSON):**
```json
{
  "format": "json",
  "total_records": 5234,
  "date_from": "2025-01-01T00:00:00Z",
  "date_to": "2025-01-07T23:59:59Z",
  "generated_at": "2025-01-07T18:45:00Z",
  "data": [
    {
      "timestamp": "2025-01-07T18:30:15Z",
      "action": "CREATE_TUNNEL",
      "user": "admin@orizon.local",
      "result": "success"
      // ... campi audit
    }
  ]
}
```

**Response (CSV):**
```csv
timestamp,action,user_email,resource_type,severity,ip_address,result
2025-01-07T18:30:15Z,CREATE_TUNNEL,admin@orizon.local,tunnel,INFO,203.0.113.45,success
...
```

**Response (SIEM/CEF):**
```
CEF:0|Orizon|ZTC|1.0.0|CREATE_TUNNEL|Tunnel Created|5|src=203.0.113.45 suser=admin@orizon.local outcome=success ...
```

---

### GET /audit/statistics

Statistiche aggregate audit logs.

**Request:**
```http
GET /api/v1/audit/statistics?period=last_30_days HTTP/1.1
Authorization: Bearer <access_token>
```

**Query Parameters:**
- `period` - Periodo: `last_24h`, `last_7_days`, `last_30_days`, `last_90_days`, `custom`
- `date_from` / `date_to` - Per periodo custom

**Response:**
```json
{
  "period": "last_30_days",
  "date_from": "2024-12-08T00:00:00Z",
  "date_to": "2025-01-07T23:59:59Z",
  "total_events": 15234,
  "events_by_action": {
    "LOGIN": 3245,
    "LOGOUT": 3100,
    "CREATE_TUNNEL": 521,
    "DELETE_TUNNEL": 489,
    "CREATE_USER": 45,
    "UPDATE_USER": 123,
    "CREATE_ACL_RULE": 78,
    "other": 7633
  },
  "events_by_user": {
    "admin@orizon.local": 5234,
    "user1@example.com": 2341,
    "user2@example.com": 1823,
    "other": 5836
  },
  "events_by_severity": {
    "INFO": 14123,
    "WARNING": 982,
    "ERROR": 115,
    "CRITICAL": 14
  },
  "failed_logins": {
    "total": 234,
    "unique_ips": 45,
    "top_ips": [
      {"ip": "198.51.100.10", "count": 89},
      {"ip": "198.51.100.25", "count": 45}
    ]
  },
  "top_actions": [
    {"action": "LOGIN", "count": 3245},
    {"action": "LOGOUT", "count": 3100},
    {"action": "CREATE_TUNNEL", "count": 521}
  ],
  "timeline": [
    {"date": "2024-12-08", "count": 512},
    {"date": "2024-12-09", "count": 498},
    // ... 30 giorni
  ]
}
```

---

### DELETE /audit/cleanup

Cleanup manuale vecchi audit logs (oltre retention period).

**Request:**
```http
DELETE /api/v1/audit/cleanup?older_than_days=90 HTTP/1.1
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "message": "Audit logs cleanup completed",
  "deleted_count": 12345,
  "cutoff_date": "2024-10-09T00:00:00Z"
}
```

**Note:**
- Solo SuperUser può eseguire cleanup manuale
- Retention di default: 90 giorni
- Cleanup automatico eseguito daily

---

## 📊 Endpoints Metrics

### GET /metrics

Export metriche Prometheus.

**Request:**
```http
GET /api/v1/metrics HTTP/1.1
```

**Response (Prometheus format):**
```
# HELP orizon_tunnels_created_total Total number of tunnels created
# TYPE orizon_tunnels_created_total counter
orizon_tunnels_created_total 1523

# HELP orizon_active_tunnels Number of currently active tunnels
# TYPE orizon_active_tunnels gauge
orizon_active_tunnels 28

# HELP orizon_api_requests_total Total API requests
# TYPE orizon_api_requests_total counter
orizon_api_requests_total{method="GET",endpoint="/nodes",status="200"} 5234
orizon_api_requests_total{method="POST",endpoint="/tunnels",status="201"} 521

# HELP orizon_api_request_duration_seconds API request latency
# TYPE orizon_api_request_duration_seconds histogram
orizon_api_request_duration_seconds_bucket{endpoint="/nodes",le="0.01"} 4523
orizon_api_request_duration_seconds_bucket{endpoint="/nodes",le="0.05"} 5124
orizon_api_request_duration_seconds_bucket{endpoint="/nodes",le="0.1"} 5200
orizon_api_request_duration_seconds_sum{endpoint="/nodes"} 125.45
orizon_api_request_duration_seconds_count{endpoint="/nodes"} 5234

# ... 30+ altre metriche
```

**Note:**
- Endpoint pubblico, no auth required
- Formato Prometheus standard
- Scraping ogni 15s consigliato

---

### GET /metrics/dashboard

Dashboard stats aggregate (per UI).

**Request:**
```http
GET /api/v1/metrics/dashboard HTTP/1.1
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "overview": {
    "total_nodes": 125,
    "nodes_online": 118,
    "nodes_offline": 7,
    "total_tunnels": 342,
    "tunnels_active": 328,
    "total_users": 45,
    "users_online": 12
  },
  "tunnel_stats": {
    "created_today": 15,
    "closed_today": 8,
    "average_latency_ms": 25.5,
    "total_bandwidth_gb": 1250.5
  },
  "api_stats": {
    "requests_last_hour": 5234,
    "average_latency_ms": 45.2,
    "error_rate_percent": 0.5
  },
  "security": {
    "failed_logins_last_24h": 23,
    "acl_denies_last_24h": 156,
    "2fa_enabled_percent": 78.5
  },
  "top_nodes": [
    {
      "id": "node-uuid-1",
      "name": "production-server-01",
      "tunnels_count": 8,
      "bandwidth_gb": 125.5
    }
    // ... top 5 nodi
  ]
}
```

---

### GET /metrics/health

Health check completo del sistema.

**Request:**
```http
GET /api/v1/metrics/health HTTP/1.1
```

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2025-01-07T19:00:00Z",
  "components": {
    "api": {
      "status": "healthy",
      "latency_ms": 12.5
    },
    "database": {
      "status": "healthy",
      "type": "PostgreSQL",
      "connections": 15,
      "max_connections": 100
    },
    "redis": {
      "status": "healthy",
      "memory_used_mb": 245,
      "memory_max_mb": 2048
    },
    "mongodb": {
      "status": "healthy",
      "storage_used_gb": 15.5
    },
    "websocket": {
      "status": "healthy",
      "active_connections": 12
    }
  },
  "uptime_seconds": 864000
}
```

**Status possibili:**
- `healthy` - Tutto OK
- `degraded` - Alcuni componenti warning
- `unhealthy` - Problemi critici

---

## 🔌 WebSocket

### Connessione WebSocket

**URL:** `ws://localhost:8000/ws`

**Connessione:**
```javascript
const socket = new WebSocket('ws://localhost:8000/ws');

socket.onopen = () => {
  console.log('WebSocket connected');

  // Autentica con JWT token
  socket.send(JSON.stringify({
    type: 'auth',
    token: 'your-jwt-access-token'
  }));
};

socket.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Received:', data);

  switch(data.event) {
    case 'node.connected':
      handleNodeConnected(data);
      break;
    case 'tunnel.created':
      handleTunnelCreated(data);
      break;
    // ... altri eventi
  }
};

socket.onerror = (error) => {
  console.error('WebSocket error:', error);
};

socket.onclose = () => {
  console.log('WebSocket disconnected');
  // Auto-reconnect logic
};
```

### Eventi WebSocket

#### node.connected
```json
{
  "event": "node.connected",
  "timestamp": "2025-01-07T19:10:00Z",
  "data": {
    "node_id": "node-uuid-1",
    "node_name": "production-server-01",
    "ip_address": "192.168.1.100"
  }
}
```

#### node.disconnected
```json
{
  "event": "node.disconnected",
  "timestamp": "2025-01-07T19:15:00Z",
  "data": {
    "node_id": "node-uuid-1",
    "node_name": "production-server-01",
    "reason": "timeout"
  }
}
```

#### tunnel.created
```json
{
  "event": "tunnel.created",
  "timestamp": "2025-01-07T19:20:00Z",
  "data": {
    "tunnel_id": "tunnel-uuid-1",
    "type": "SSH",
    "node_id": "node-uuid-1",
    "remote_port": 10025
  }
}
```

#### tunnel.closed
```json
{
  "event": "tunnel.closed",
  "timestamp": "2025-01-07T19:25:00Z",
  "data": {
    "tunnel_id": "tunnel-uuid-1",
    "reason": "user_request"
  }
}
```

#### acl.rule_updated
```json
{
  "event": "acl.rule_updated",
  "timestamp": "2025-01-07T19:30:00Z",
  "data": {
    "rule_id": "rule-uuid-1",
    "action": "updated",
    "enabled": true
  }
}
```

#### audit.new_event
```json
{
  "event": "audit.new_event",
  "timestamp": "2025-01-07T19:35:00Z",
  "data": {
    "log_id": "log-uuid-1",
    "action": "CREATE_USER",
    "severity": "INFO",
    "user_email": "admin@orizon.local"
  }
}
```

---

## ❌ Error Handling

### Error Response Format

Tutti gli errori seguono questo formato:

```json
{
  "detail": "Error message here",
  "error_code": "ERROR_CODE",
  "timestamp": "2025-01-07T19:40:00Z",
  "request_id": "req-uuid-12345"
}
```

### HTTP Status Codes

| Code | Significato | Esempio |
|------|-------------|---------|
| 200 | OK | GET request successful |
| 201 | Created | Resource created |
| 204 | No Content | DELETE successful |
| 400 | Bad Request | Invalid input data |
| 401 | Unauthorized | Missing or invalid token |
| 403 | Forbidden | RBAC permission denied |
| 404 | Not Found | Resource not found |
| 409 | Conflict | Resource already exists |
| 422 | Unprocessable Entity | Validation error |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error |
| 503 | Service Unavailable | Service down |

### Error Codes

| Code | Descrizione |
|------|-------------|
| `AUTH_INVALID_CREDENTIALS` | Email o password errati |
| `AUTH_TOKEN_EXPIRED` | Token JWT scaduto |
| `AUTH_TOKEN_INVALID` | Token JWT non valido |
| `AUTH_2FA_REQUIRED` | 2FA verification required |
| `AUTH_2FA_INVALID` | Codice 2FA non valido |
| `RBAC_PERMISSION_DENIED` | Permesso negato per ruolo |
| `VALIDATION_ERROR` | Errore validazione dati |
| `RESOURCE_NOT_FOUND` | Risorsa non trovata |
| `RESOURCE_ALREADY_EXISTS` | Risorsa già esistente |
| `RATE_LIMIT_EXCEEDED` | Rate limit superato |
| `ACL_DENIED` | ACL rule ha negato l'azione |
| `PORT_UNAVAILABLE` | Nessuna porta disponibile |
| `NODE_OFFLINE` | Nodo offline |
| `TUNNEL_ERROR` | Errore tunnel |

### Esempio Error Responses

**400 Bad Request:**
```json
{
  "detail": "Password must be at least 12 characters long",
  "error_code": "VALIDATION_ERROR",
  "timestamp": "2025-01-07T19:45:00Z",
  "request_id": "req-12345",
  "validation_errors": [
    {
      "field": "password",
      "message": "Password too short",
      "constraint": "min_length_12"
    }
  ]
}
```

**401 Unauthorized:**
```json
{
  "detail": "Invalid or expired token",
  "error_code": "AUTH_TOKEN_EXPIRED",
  "timestamp": "2025-01-07T19:46:00Z",
  "request_id": "req-12346"
}
```

**403 Forbidden:**
```json
{
  "detail": "You don't have permission to perform this action",
  "error_code": "RBAC_PERMISSION_DENIED",
  "timestamp": "2025-01-07T19:47:00Z",
  "request_id": "req-12347",
  "required_role": "Admin",
  "current_role": "User"
}
```

**429 Rate Limit:**
```json
{
  "detail": "Rate limit exceeded. Try again in 60 seconds.",
  "error_code": "RATE_LIMIT_EXCEEDED",
  "timestamp": "2025-01-07T19:48:00Z",
  "request_id": "req-12348",
  "retry_after": 60,
  "limit": 100,
  "remaining": 0,
  "reset_at": "2025-01-07T19:49:00Z"
}
```

---

## ⏱️ Rate Limiting

### Limiti per Ruolo

| Ruolo | Requests/Minuto | Burst |
|-------|-----------------|-------|
| SuperUser | 1000 | 1200 |
| SuperAdmin | 500 | 600 |
| Admin | 200 | 250 |
| User | 100 | 120 |
| Anonymous | 10 | 15 |

### Limiti per Endpoint

| Endpoint | Limit | Window |
|----------|-------|--------|
| `/auth/login` | 10 | 10 min |
| `/auth/verify-2fa` | 5 | 5 min |
| `/auth/refresh` | 20 | 1 min |
| `/users` (POST) | 10 | 1 hour |
| `/tunnels` (POST) | 50 | 10 min |
| Altri endpoint | By role | 1 min |

### Rate Limit Headers

Ogni risposta include headers:

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1673107200
```

---

## 📝 Best Practices

### 1. Autenticazione

✅ **DO:**
- Salva token in secure storage (httpOnly cookie o secure localStorage)
- Implementa auto-refresh token prima della scadenza
- Gestisci 401 con logout automatico
- Usa HTTPS in production

❌ **DON'T:**
- Salvare token in plain text nel browser
- Ignorare token expiration
- Hardcodare credenziali nel codice

### 2. Error Handling

✅ **DO:**
```javascript
try {
  const response = await api.createTunnel(data);
  // Handle success
} catch (error) {
  if (error.response) {
    // Server responded with error
    switch(error.response.status) {
      case 401:
        // Redirect to login
        break;
      case 403:
        // Show permission error
        break;
      case 429:
        // Wait and retry
        const retryAfter = error.response.data.retry_after;
        setTimeout(() => retry(), retryAfter * 1000);
        break;
      default:
        // Show generic error
    }
  } else if (error.request) {
    // Request made but no response (network error)
    showNetworkError();
  } else {
    // Request setup error
    console.error(error.message);
  }
}
```

### 3. Paginazione

✅ **DO:**
```javascript
async function loadAllUsers() {
  let allUsers = [];
  let offset = 0;
  const limit = 100;

  while (true) {
    const response = await api.getUsers({ limit, offset });
    allUsers = [...allUsers, ...response.users];

    if (allUsers.length >= response.total) {
      break;
    }

    offset += limit;
  }

  return allUsers;
}
```

### 4. Rate Limiting

✅ **DO:**
```javascript
// Implementa exponential backoff su 429
async function makeRequestWithRetry(apiCall, maxRetries = 3) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      return await apiCall();
    } catch (error) {
      if (error.response?.status === 429) {
        const retryAfter = error.response.data.retry_after || (2 ** i);
        await sleep(retryAfter * 1000);
        continue;
      }
      throw error;
    }
  }
  throw new Error('Max retries exceeded');
}
```

---

**Documento maintained by:** Marco Lorenzi @ Syneto/Orizon
**Last Review:** Gennaio 2025
**Interactive API Docs:** http://localhost:8000/docs
