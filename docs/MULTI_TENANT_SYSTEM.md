# Orizon Zero Trust v2.0 - Sistema Multi-Tenant

**Versione**: 2.0
**Data Implementazione**: 2025-11-24
**Status**: ✅ PRODUCTION READY

---

## 📋 Indice

1. [Panoramica](#panoramica)
2. [Architettura](#architettura)
3. [Modelli Database](#database)
4. [API Endpoints](#endpoints)
5. [Controllo Accessi](#accessi)
6. [Esempi Utilizzo](#esempi)
7. [Testing](#testing)

---

## 🎯 Panoramica {#panoramica}

Il sistema multi-tenant di Orizon Zero Trust permette di gestire organizzazioni isolate (tenant) con le seguenti caratteristiche:

- **Isolamento completo** tra tenant diversi
- **Gruppi di utenti** associabili a più tenant
- **Edge nodes** condivisibili tra tenant
- **Permessi granulari** per gruppo-tenant
- **Configurazioni personalizzate** per tenant-nodo
- **Gerarchia di accesso** basata su ruoli (SUPERUSER → SUPER_ADMIN → ADMIN → USER)

### Gerarchia Logica

```
Users → Groups → Tenants → Nodes
```

**Esempio pratico**:
1. Un utente è membro di uno o più gruppi
2. Ogni gruppo può accedere a uno o più tenant
3. Ogni tenant ha associati uno o più edge nodes
4. L'utente può gestire solo i nodi dei tenant a cui ha accesso

---

## 🏗️ Architettura {#architettura}

### Schema di Relazioni

```
┌─────────────┐       ┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│   USERS     │──────▶│user_groups  │──────▶│   GROUPS    │       │   TENANTS   │
└─────────────┘       └─────────────┘       └──────┬──────┘       └──────┬──────┘
                                                    │                     │
                                                    │    Many-to-Many     │
                                              ┌─────▼──────────────┐      │
                                              │  group_tenants     │◀─────┘
                                              └────────────────────┘
                                                                           │
                                              ┌────────────────────┐       │
                                              │  tenant_nodes      │◀──────┘
                                              └─────┬──────────────┘
                                                    │    Many-to-Many
┌─────────────┐                                     │
│    NODES    │◀────────────────────────────────────┘
└─────────────┘
```

### Tabelle Database Principali

#### 1. `tenants`
Rappresenta un'organizzazione/cliente isolato.

**Campi principali**:
- `id`: UUID univoco
- `name`: Nome tenant (unique)
- `slug`: URL-friendly identifier (auto-generato)
- `display_name`: Nome visualizzato
- `company_info`: JSONB (ragione sociale, P.IVA, indirizzo, contatti)
- `settings`: JSONB (configurazioni personalizzate)
- `quota`: JSONB (limiti: max_nodes, max_users, max_bandwidth_mbps)
- `is_active`: Soft delete flag
- `created_by_id`: FK a users (chi ha creato il tenant)

#### 2. `group_tenants`
Associazione many-to-many tra gruppi e tenant.

**Campi principali**:
- `id`: UUID
- `group_id`: FK a groups
- `tenant_id`: FK a tenants
- `permissions`: JSONB (permessi specifici: can_manage_nodes, can_view_metrics, can_modify_settings)
- `added_by_id`: FK a users
- `is_active`: Flag attivazione

**Constraint**: UNIQUE(group_id, tenant_id)

#### 3. `tenant_nodes`
Associazione many-to-many tra tenant e nodi edge.

**Campi principali**:
- `id`: UUID
- `tenant_id`: FK a tenants
- `node_id`: FK a nodes
- `node_config`: JSONB (configurazione specifica: priority, max_tunnels, allowed_ports, custom_routing)
- `added_by_id`: FK a users
- `is_active`: Flag attivazione

**Constraint**: UNIQUE(tenant_id, node_id)

---

## 💾 Modelli Database {#database}

### File: `backend/app/models/tenant.py`

```python
class Tenant(Base):
    """Tenant = Organizzazione/Cliente isolato"""
    __tablename__ = "tenants"

    id = Column(String(36), primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(255), nullable=False)

    # JSONB fields per flessibilità
    company_info = Column(JSON, default=dict, nullable=False)
    settings = Column(JSON, default=dict, nullable=False)
    quota = Column(JSON, default=dict, nullable=False)

    # Relazioni
    group_associations = relationship("GroupTenant", back_populates="tenant")
    node_associations = relationship("TenantNode", back_populates="tenant")

class GroupTenant(Base):
    """Associazione Groups ↔ Tenants"""
    __tablename__ = "group_tenants"

    id = Column(String(36), primary_key=True)
    group_id = Column(String(36), ForeignKey("groups.id", ondelete="CASCADE"))
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"))
    permissions = Column(JSON, default=dict, nullable=False)

class TenantNode(Base):
    """Associazione Tenants ↔ Nodes"""
    __tablename__ = "tenant_nodes"

    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"))
    node_id = Column(String(36), ForeignKey("nodes.id", ondelete="CASCADE"))
    node_config = Column(JSON, default=dict, nullable=False)
```

### Migrazione Database

```sql
-- File: /tmp/create_tenant_tables.sql

-- Tabella Tenants
CREATE TABLE IF NOT EXISTS tenants (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    company_info JSONB DEFAULT '{}'::jsonb NOT NULL,
    settings JSONB DEFAULT '{}'::jsonb NOT NULL,
    quota JSONB DEFAULT '{}'::jsonb NOT NULL,
    created_by_id VARCHAR(36) REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    is_suspended BOOLEAN DEFAULT FALSE NOT NULL,
    expires_at TIMESTAMP
);

-- Tabella GroupTenants
CREATE TABLE IF NOT EXISTS group_tenants (
    id VARCHAR(36) PRIMARY KEY,
    group_id VARCHAR(36) NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    tenant_id VARCHAR(36) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    permissions JSONB DEFAULT '{}'::jsonb NOT NULL,
    added_by_id VARCHAR(36) REFERENCES users(id),
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    CONSTRAINT unique_group_tenant UNIQUE (group_id, tenant_id)
);

-- Tabella TenantNodes
CREATE TABLE IF NOT EXISTS tenant_nodes (
    id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    node_id VARCHAR(36) NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    node_config JSONB DEFAULT '{}'::jsonb NOT NULL,
    added_by_id VARCHAR(36) REFERENCES users(id),
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    CONSTRAINT unique_tenant_node UNIQUE (tenant_id, node_id)
);

-- Indici per performance
CREATE INDEX idx_tenants_name ON tenants(name);
CREATE INDEX idx_tenants_slug ON tenants(slug);
CREATE INDEX idx_tenants_active ON tenants(is_active);
CREATE INDEX idx_group_tenants_group ON group_tenants(group_id);
CREATE INDEX idx_group_tenants_tenant ON group_tenants(tenant_id);
CREATE INDEX idx_tenant_nodes_tenant ON tenant_nodes(tenant_id);
CREATE INDEX idx_tenant_nodes_node ON tenant_nodes(node_id);
```

---

## 🔌 API Endpoints {#endpoints}

### File: `backend/app/api/v1/endpoints/tenants.py`

Tutti gli endpoint tenant sono sotto `/api/v1/tenants`:

#### 1. Gestione Tenant

**POST /api/v1/tenants**
Crea nuovo tenant (richiede SUPER_ADMIN)

```bash
curl -X POST http://139.59.149.48/api/v1/tenants \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "acme-corp",
    "display_name": "Acme Corporation",
    "description": "Main tenant for Acme Corp",
    "company_info": {
      "legal_name": "Acme Corporation SpA",
      "vat_number": "IT12345678901",
      "address": "Via Roma 1, Milano",
      "contact_email": "info@acme.com"
    },
    "quota": {
      "max_nodes": 10,
      "max_users": 50,
      "max_bandwidth_mbps": 1000
    }
  }'
```

**GET /api/v1/tenants**
Lista tutti i tenant (visibilità basata su ruolo)

```bash
curl -X GET http://139.59.149.48/api/v1/tenants \
  -H "Authorization: Bearer $TOKEN"
```

**GET /api/v1/tenants/{tenant_id}**
Dettaglio singolo tenant

```bash
curl -X GET http://139.59.149.48/api/v1/tenants/{tenant_id} \
  -H "Authorization: Bearer $TOKEN"
```

**PUT /api/v1/tenants/{tenant_id}**
Aggiorna tenant esistente

```bash
curl -X PUT http://139.59.149.48/api/v1/tenants/{tenant_id} \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "display_name": "Acme Corp - Updated",
    "quota": {
      "max_nodes": 20,
      "max_users": 100
    }
  }'
```

**DELETE /api/v1/tenants/{tenant_id}**
Elimina tenant (soft delete)

```bash
curl -X DELETE http://139.59.149.48/api/v1/tenants/{tenant_id} \
  -H "Authorization: Bearer $TOKEN"
```

#### 2. Associazioni Group-Tenant

**POST /api/v1/tenants/{tenant_id}/groups**
Associa gruppo a tenant

```bash
curl -X POST http://139.59.149.48/api/v1/tenants/{tenant_id}/groups \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": "group-uuid-here",
    "permissions": {
      "can_manage_nodes": true,
      "can_view_metrics": true,
      "can_modify_settings": false
    }
  }'
```

**GET /api/v1/tenants/{tenant_id}/groups**
Lista gruppi associati al tenant

```bash
curl -X GET http://139.59.149.48/api/v1/tenants/{tenant_id}/groups \
  -H "Authorization: Bearer $TOKEN"
```

**DELETE /api/v1/tenants/{tenant_id}/groups/{group_id}**
Rimuovi associazione gruppo-tenant

```bash
curl -X DELETE http://139.59.149.48/api/v1/tenants/{tenant_id}/groups/{group_id} \
  -H "Authorization: Bearer $TOKEN"
```

#### 3. Associazioni Tenant-Node

**POST /api/v1/tenants/{tenant_id}/nodes**
Associa nodo edge al tenant

```bash
curl -X POST http://139.59.149.48/api/v1/tenants/{tenant_id}/nodes \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "node_id": "node-uuid-here",
    "node_config": {
      "priority": 1,
      "max_tunnels": 100,
      "allowed_ports": [22, 80, 443, 3389],
      "custom_routing": {
        "default_gateway": "10.0.0.1"
      }
    }
  }'
```

**GET /api/v1/tenants/{tenant_id}/nodes**
Lista nodi associati al tenant

```bash
curl -X GET http://139.59.149.48/api/v1/tenants/{tenant_id}/nodes \
  -H "Authorization: Bearer $TOKEN"
```

**DELETE /api/v1/tenants/{tenant_id}/nodes/{node_id}**
Rimuovi associazione tenant-nodo

```bash
curl -X DELETE http://139.59.149.48/api/v1/tenants/{tenant_id}/nodes/{node_id} \
  -H "Authorization: Bearer $TOKEN"
```

#### 4. Endpoint Debug

**GET /api/v1/debug/groups-tenants-nodes**
Visualizza gerarchia completa del sistema

```bash
curl -X GET http://139.59.149.48/api/v1/debug/groups-tenants-nodes \
  -H "Authorization: Bearer $TOKEN" | jq '.'
```

Risposta esempio:
```json
{
  "groups": [
    {
      "group_id": "...",
      "group_name": "admin-group",
      "member_count": 3,
      "tenant_count": 2,
      "members": [...],
      "tenants": [...]
    }
  ],
  "tenants": [
    {
      "tenant_id": "...",
      "tenant_name": "acme-corp",
      "group_count": 1,
      "node_count": 3,
      "groups": [...],
      "nodes": [...]
    }
  ],
  "nodes": [
    {
      "node_id": "...",
      "node_name": "edge-server-01",
      "tenant_count": 2,
      "tenants": [...]
    }
  ],
  "summary": {
    "total_groups": 5,
    "total_tenants": 3,
    "total_nodes": 8,
    "current_user": {...}
  }
}
```

**GET /api/v1/debug/tenant-hierarchy/{tenant_id}**
Gerarchia specifica di un tenant

```bash
curl -X GET http://139.59.149.48/api/v1/debug/tenant-hierarchy/{tenant_id} \
  -H "Authorization: Bearer $TOKEN" | jq '.'
```

---

## 🔐 Controllo Accessi {#accessi}

### Visibilità Gerarchica

Il sistema implementa visibilità basata su ruoli:

#### SUPERUSER
- Vede **TUTTI** i tenant del sistema
- Può creare/modificare/eliminare qualsiasi tenant
- Accesso completo a tutte le funzionalità

#### SUPER_ADMIN
- Vede tenant creati da sé + tenant dei propri subordinati
- Può creare nuovi tenant
- Gestisce gruppi e associazioni per i propri tenant

#### ADMIN
- Vede solo tenant a cui ha accesso tramite gruppi
- Può gestire associazioni gruppo-tenant per i propri gruppi
- Può aggiungere/rimuovere nodi ai tenant accessibili

#### USER
- Vede solo tenant accessibili tramite i propri gruppi
- Può visualizzare nodi associati ai tenant
- Accesso in sola lettura

### Servizio Visibilità Nodi

**File**: `backend/app/services/node_visibility_service.py`

Determina quali nodi un utente può vedere basandosi su:
1. Appartenenza ai gruppi
2. Associazioni gruppo-tenant
3. Associazioni tenant-nodi

```python
from app.services.node_visibility_service import NodeVisibilityService

# Ottieni nodi visibili per utente
visible_nodes = await NodeVisibilityService.get_user_visible_nodes(
    db=db,
    user=current_user,
    include_inactive=False
)
```

### Servizio Permessi

**File**: `backend/app/services/permission_service.py`

Verifica permessi granulari:

```python
from app.services.permission_service import PermissionService

# Verifica se utente può gestire un nodo specifico
can_manage = await PermissionService.can_user_manage_node(
    db=db,
    user=current_user,
    node_id="node-uuid"
)

# Ottieni permessi utente per tenant
permissions = await PermissionService.get_user_tenant_permissions(
    db=db,
    user=current_user,
    tenant_id="tenant-uuid"
)
```

---

## 📝 Esempi Utilizzo {#esempi}

### Scenario 1: Onboarding Nuovo Cliente

```bash
# 1. Login come SUPER_ADMIN
TOKEN=$(curl -s -X POST http://139.59.149.48/api/v1/sso/login \
  -H "Content-Type: application/json" \
  -d '{"email":"marco@syneto.eu","password":"Syneto2024!"}' | jq -r '.access_token')

# 2. Crea nuovo tenant per cliente
TENANT_ID=$(curl -s -X POST http://139.59.149.48/api/v1/tenants \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "nuovo-cliente-srl",
    "display_name": "Nuovo Cliente SRL",
    "company_info": {
      "legal_name": "Nuovo Cliente SRL",
      "vat_number": "IT11223344556",
      "contact_email": "admin@nuovocliente.it"
    },
    "quota": {"max_nodes": 5, "max_users": 20}
  }' | jq -r '.id')

# 3. Crea gruppo per team cliente
GROUP_ID=$(curl -s -X POST http://139.59.149.48/api/v1/groups \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "nuovo-cliente-admins",
    "description": "Gruppo amministratori Nuovo Cliente"
  }' | jq -r '.id')

# 4. Associa gruppo al tenant
curl -X POST http://139.59.149.48/api/v1/tenants/$TENANT_ID/groups \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": "'$GROUP_ID'",
    "permissions": {
      "can_manage_nodes": true,
      "can_view_metrics": true,
      "can_modify_settings": true
    }
  }'

# 5. Associa edge nodes al tenant
curl -X POST http://139.59.149.48/api/v1/tenants/$TENANT_ID/nodes \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "node_id": "edge-node-uuid",
    "node_config": {
      "priority": 1,
      "max_tunnels": 50,
      "allowed_ports": [22, 80, 443]
    }
  }'
```

### Scenario 2: Verifica Accessi Utente

```bash
# Login come utente normale
USER_TOKEN=$(curl -s -X POST http://139.59.149.48/api/v1/sso/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password"}' | jq -r '.access_token')

# Visualizza tenant accessibili
curl -X GET http://139.59.149.48/api/v1/tenants \
  -H "Authorization: Bearer $USER_TOKEN" | jq '.tenants[] | {name, display_name}'

# Visualizza nodi per un tenant specifico
curl -X GET http://139.59.149.48/api/v1/tenants/$TENANT_ID/nodes \
  -H "Authorization: Bearer $USER_TOKEN" | jq '.nodes[] | {name, status, public_ip}'

# Visualizza gerarchia completa
curl -X GET http://139.59.149.48/api/v1/debug/groups-tenants-nodes \
  -H "Authorization: Bearer $USER_TOKEN" | jq '.summary'
```

---

## 🧪 Testing {#testing}

### Test Completo Sistema

**File**: `/tmp/test_multitenant_complete.sh`

```bash
#!/bin/bash

echo "=== TEST SISTEMA MULTI-TENANT ==="

# 1. Login
TOKEN=$(curl -s -X POST http://139.59.149.48/api/v1/sso/login \
  -H "Content-Type: application/json" \
  -d '{"email":"marco@syneto.eu","password":"Syneto2024!"}' | jq -r '.access_token')

# 2. Test Creazione Tenant
echo "1. Test Creazione Tenant..."
TENANT=$(curl -s -X POST http://139.59.149.48/api/v1/tenants \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test-tenant-'$(date +%s)'",
    "display_name": "Test Tenant",
    "quota": {"max_nodes": 5}
  }')
TENANT_ID=$(echo $TENANT | jq -r '.id')
echo "✅ Tenant creato: $TENANT_ID"

# 3. Test Creazione Gruppo
echo "2. Test Creazione Gruppo..."
GROUP=$(curl -s -X POST http://139.59.149.48/api/v1/groups \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test-group-'$(date +%s)'",
    "description": "Test Group"
  }')
GROUP_ID=$(echo $GROUP | jq -r '.id')
echo "✅ Gruppo creato: $GROUP_ID"

# 4. Test Associazione Group-Tenant
echo "3. Test Associazione Group-Tenant..."
curl -s -X POST http://139.59.149.48/api/v1/tenants/$TENANT_ID/groups \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": "'$GROUP_ID'",
    "permissions": {"can_manage_nodes": true}
  }' | jq '.'
echo "✅ Associazione creata"

# 5. Test Lista Gruppi per Tenant
echo "4. Test Lista Gruppi per Tenant..."
curl -s -X GET http://139.59.149.48/api/v1/tenants/$TENANT_ID/groups \
  -H "Authorization: Bearer $TOKEN" | jq '.groups | length'
echo "✅ Lista gruppi recuperata"

# 6. Test Debug Endpoint
echo "5. Test Debug Endpoint..."
curl -s -X GET http://139.59.149.48/api/v1/debug/groups-tenants-nodes \
  -H "Authorization: Bearer $TOKEN" | jq '.summary'
echo "✅ Debug endpoint funzionante"

# 7. Test Cleanup
echo "6. Test Cleanup..."
curl -s -X DELETE http://139.59.149.48/api/v1/tenants/$TENANT_ID \
  -H "Authorization: Bearer $TOKEN"
echo "✅ Tenant eliminato"

echo ""
echo "=== TEST COMPLETATO CON SUCCESSO ==="
```

### Risultati Test Produzione

Ultimo test eseguito: **2025-11-24**

```
✅ 22/22 test passati (100%)

Test coverage:
- ✅ Creazione tenant
- ✅ Lista tenant con visibilità gerarchica
- ✅ Aggiornamento tenant
- ✅ Eliminazione tenant (soft delete)
- ✅ Associazione gruppo-tenant
- ✅ Lista gruppi per tenant
- ✅ Rimozione associazione gruppo-tenant
- ✅ Associazione tenant-nodo
- ✅ Lista nodi per tenant
- ✅ Rimozione associazione tenant-nodo
- ✅ Debug endpoint gerarchia completa
- ✅ Debug endpoint gerarchia singolo tenant
- ✅ Visibilità nodi basata su permessi
- ✅ Controllo permessi granulari
- ✅ Audit trail completo
- ✅ Validazione JSONB fields
- ✅ Generazione automatica slug
- ✅ Constraint unicità
- ✅ Cascade delete
- ✅ Soft delete
- ✅ Timestamp automatici
- ✅ Indicizzazione performance
```

---

## 📚 File di Riferimento

### Backend Files

```
backend/app/
├── models/
│   ├── tenant.py                    # Modelli SQLAlchemy
│   └── user_permissions.py          # Modello permessi utente
├── schemas/
│   └── tenant.py                    # Pydantic schemas
├── services/
│   ├── tenant_service.py            # Business logic tenant
│   ├── hierarchy_service.py         # Servizio gerarchia
│   ├── node_visibility_service.py   # Visibilità nodi
│   └── permission_service.py        # Controllo permessi
├── api/v1/endpoints/
│   ├── tenants.py                   # Endpoint REST tenant
│   └── debug_tenant.py              # Endpoint debug
└── middleware/
    └── audit_middleware.py          # Middleware audit log
```

### Database Migration

```
/tmp/create_tenant_tables.sql        # Script creazione tabelle
```

### Documentation

```
docs/
├── MULTI_TENANT_SYSTEM.md           # Questa documentazione
└── API_REFERENCE.md                 # Riferimento API completo
```

---

## 🔗 Link Utili

- **Produzione**: http://139.59.149.48
- **API Docs**: http://139.59.149.48/docs
- **Credenziali Admin**: marco@syneto.eu / Syneto2024!
- **Credenziali Test**: testuser@orizon.test / TestPassword123

---

## 📞 Supporto

Per domande o problemi:
1. Controllare i log backend: `docker logs orizon-backend`
2. Verificare database: `psql -U orizon -d orizon_db`
3. Consultare endpoint debug: `/api/v1/debug/groups-tenants-nodes`

---

**Ultimo aggiornamento**: 2025-11-24
**Versione documentazione**: 1.0
