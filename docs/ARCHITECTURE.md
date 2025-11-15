# 🏗️ Architettura - Orizon Zero Trust Connect

**Versione:** 1.0.0
**Last Updated:** Gennaio 2025
**Autore:** Marco Lorenzi @ Syneto/Orizon

---

## 📋 Indice

1. [Panoramica Architetturale](#panoramica-architetturale)
2. [Pattern Architetturali](#pattern-architetturali)
3. [Componenti Sistema](#componenti-sistema)
4. [Data Flow](#data-flow)
5. [Security Architecture](#security-architecture)
6. [Scalabilità & Performance](#scalabilita--performance)
7. [Deployment Architecture](#deployment-architecture)

---

## 🎯 Panoramica Architetturale

Orizon Zero Trust Connect implementa un'architettura **a 4 livelli** (Presentation, Application, Data, Network) con pattern moderni e best practices enterprise.

### Principi Architetturali

1. **Zero Trust Security** - "Never trust, always verify"
2. **Separation of Concerns** - Responsabilità separate per layer
3. **Microservices-oriented** - Servizi modulari e indipendenti
4. **Event-Driven** - Comunicazione asincrona via eventi
5. **API-First** - REST API come contratto principale
6. **Cloud-Native** - Design per cloud e containerizzazione

### Stack Tecnologico Completo

#### Backend (Application Layer)
```yaml
Framework: FastAPI 0.104+
Language: Python 3.10+
ASGI Server: Uvicorn
ORM: SQLAlchemy 2.0 (async)
Validation: Pydantic 2.0+
Migrations: Alembic
Task Queue: Celery (futuro)
```

#### Frontend (Presentation Layer)
```yaml
Framework: React 18.3
Build Tool: Vite 5.4
State Management: Redux Toolkit 2.0
3D Rendering: Three.js + React Three Fiber
Styling: Tailwind CSS 3.4
HTTP Client: Axios 1.7
Real-time: Socket.IO Client
```

#### Data Layer
```yaml
Primary DB: PostgreSQL 15 (relational)
Cache: Redis 7 (cache + pub/sub + rate limiting)
NoSQL: MongoDB 7 (audit logs, analytics)
Object Storage: MinIO/S3 (futuro, per file upload)
```

#### Infrastructure
```yaml
Container Runtime: Docker 24+
Orchestration: Kubernetes 1.28+
Reverse Proxy: Nginx 1.24
Monitoring: Prometheus + Grafana
Logging: Loki + Promtail
Service Mesh: Istio (opzionale, futuro)
```

---

## 🧩 Pattern Architetturali

### 1. Layered Architecture (4 Livelli)

```
┌───────────────────────────────────────────────┐
│         PRESENTATION LAYER                    │
│  React Frontend + 3D Visualization            │
│  • Components (UI)                            │
│  • Pages (Routes)                             │
│  • Store (State Management)                   │
│  • Services (API Clients)                     │
└─────────────────┬─────────────────────────────┘
                  │ HTTP/HTTPS + WebSocket
┌─────────────────▼─────────────────────────────┐
│          APPLICATION LAYER                    │
│  FastAPI Backend + Business Logic             │
│  • API Endpoints (REST)                       │
│  • Services (Business Logic)                  │
│  • Middleware (Cross-cutting)                 │
│  • WebSocket Manager                          │
└─────────────────┬─────────────────────────────┘
                  │ SQLAlchemy ORM
┌─────────────────▼─────────────────────────────┐
│            DATA LAYER                         │
│  Database & Caching                           │
│  • PostgreSQL (Transactional)                 │
│  • Redis (Cache + Pub/Sub)                    │
│  • MongoDB (Audit Logs)                       │
└─────────────────┬─────────────────────────────┘
                  │ Network Tunnels
┌─────────────────▼─────────────────────────────┐
│           NETWORK LAYER                       │
│  Tunnel Hub + Edge Agents                     │
│  • SSH Tunnels (Port 2222)                    │
│  • HTTPS Tunnels (Port 8443)                  │
│  • Health Monitoring                          │
└───────────────────────────────────────────────┘
```

**Vantaggi:**
- ✅ Separazione delle responsabilità
- ✅ Testabilità per layer
- ✅ Manutenibilità migliorata
- ✅ Scalabilità indipendente

### 2. Repository Pattern

Astrazione dell'accesso ai dati attraverso repository dedicati.

```python
# Esempio: TunnelService
class TunnelService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_tunnel(self, data: TunnelCreate) -> Tunnel:
        # Business logic separata da data access
        tunnel = Tunnel(**data.dict())
        self.db.add(tunnel)
        await self.db.commit()
        return tunnel

    async def get_tunnel(self, tunnel_id: str) -> Optional[Tunnel]:
        result = await self.db.execute(
            select(Tunnel).where(Tunnel.id == tunnel_id)
        )
        return result.scalar_one_or_none()
```

**Vantaggi:**
- ✅ Testabilità (mock del repository)
- ✅ Cambio database più semplice
- ✅ Business logic isolata

### 3. Dependency Injection (FastAPI)

Injection di dipendenze tramite `Depends()`.

```python
# Dependencies
async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    # Decode JWT and get user
    return user

# Endpoint con DI
@router.get("/tunnels")
async def list_tunnels(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # current_user e db sono iniettati automaticamente
    return await tunnel_service.list_tunnels(db, current_user)
```

**Vantaggi:**
- ✅ Testabilità (facile mock)
- ✅ Riutilizzo codice
- ✅ Type safety

### 4. Event-Driven Architecture (Pub/Sub)

Comunicazione asincrona tramite Redis Pub/Sub + WebSocket.

```python
# Publisher (Backend Service)
await redis_client.publish("tunnel_events", json.dumps({
    "event": "tunnel.created",
    "tunnel_id": tunnel.id,
    "node_id": tunnel.node_id
}))

# Subscriber (WebSocket Manager)
async def handle_tunnel_event(message):
    data = json.loads(message)
    # Broadcast to all connected WebSocket clients
    await ws_manager.broadcast(data)
```

**Vantaggi:**
- ✅ Decoupling dei servizi
- ✅ Scalabilità orizzontale
- ✅ Real-time updates

### 5. Middleware Chain Pattern

Catena di middleware per cross-cutting concerns.

```
Request Flow:
Client Request
    ↓
CORS Middleware (origin check)
    ↓
Trusted Host Middleware (host validation)
    ↓
Rate Limiting Middleware (check limits)
    ↓
Authentication Middleware (verify JWT)
    ↓
Route Handler (business logic)
    ↓
Response
```

**Middleware implementati:**
- `CORSMiddleware` - Cross-Origin Resource Sharing
- `TrustedHostMiddleware` - Host header validation
- `RateLimitMiddleware` - Rate limiting con Redis
- Custom error handlers

### 6. Strategy Pattern (ACL Evaluation)

Strategie diverse per evaluazione regole ACL.

```python
class ACLRuleEvaluator:
    def evaluate(self, rule: AccessRule, connection: Connection) -> bool:
        # Strategy: Priority-based evaluation
        if not rule.enabled:
            return False

        # Match IP
        if not self._match_ip(rule.source_ip, connection.source):
            return False

        # Match Port
        if not self._match_port(rule.destination_port, connection.port):
            return False

        # Match Protocol
        if not self._match_protocol(rule.protocol, connection.protocol):
            return False

        # Time-based check
        if not self._check_time_window(rule):
            return False

        return True  # All conditions matched
```

---

## 🔧 Componenti Sistema

### Backend Components

#### 1. API Layer (`app/api/v1/endpoints/`)

Gestione degli endpoint REST.

**Endpoints principali:**
- `auth.py` - Authentication (login, 2FA, refresh, logout)
- `users.py` - User management (CRUD, RBAC)
- `nodes.py` - Node management (register, health, metrics)
- `tunnels.py` - Tunnel management (create, close, stats)
- `acl.py` - ACL rules (CRUD, enable/disable)
- `audit.py` - Audit logs (query, export, statistics)
- `twofa.py` - 2FA setup (TOTP enrollment, backup codes)
- `metrics.py` - Prometheus metrics export

**Responsabilità:**
- Request validation (Pydantic schemas)
- Authentication/Authorization check
- Business logic delegation to services
- Response formatting
- Error handling

#### 2. Services Layer (`app/services/`)

Business logic separata dal data access.

**Services implementati:**

**TunnelService** (`tunnel_service.py`)
- Create SSH/HTTPS tunnels
- Port allocation (dynamic)
- Health monitoring
- Auto-reconnect logic
- Metrics tracking

**ACLService** (`acl_service.py`)
- CRUD ACL rules
- Priority-based evaluation
- Zero Trust policy enforcement
- Time-based access control
- Rule matching statistics

**AuditService** (`audit_service.py`)
- Event logging (MongoDB + PostgreSQL)
- Geolocation tracking
- Export to JSON/CSV/SIEM (CEF format)
- 90-day retention + cleanup
- Advanced filtering

**TOTPService** (`totp_service.py`)
- TOTP secret generation
- QR code generation
- Token verification (±30s window)
- Backup codes management
- Rate limiting (5 attempts / 5 min)

#### 3. Models Layer (`app/models/`)

SQLAlchemy ORM models.

**Modelli principali:**

```python
# User Model
class User(Base):
    __tablename__ = "users"

    id: UUID (PK)
    email: String (unique)
    hashed_password: String
    role: Enum (SuperUser, SuperAdmin, Admin, User)
    is_active: Boolean
    is_2fa_enabled: Boolean
    totp_secret: String (encrypted)
    created_at: DateTime
    last_login: DateTime

    # Relationships
    nodes: List[Node]
    created_rules: List[AccessRule]

# Node Model
class Node(Base):
    __tablename__ = "nodes"

    id: UUID (PK)
    name: String
    type: Enum (Linux, macOS, Windows, Docker, Kubernetes)
    ip_address: String
    status: Enum (Online, Offline, Degraded)
    owner_id: UUID (FK → users)

    # Metrics
    cpu_usage: Float
    memory_usage: Float
    disk_usage: Float

    # Relationships
    tunnels: List[Tunnel]
    owner: User

# Tunnel Model
class Tunnel(Base):
    __tablename__ = "tunnels"

    id: UUID (PK)
    type: Enum (SSH, HTTPS)
    node_id: UUID (FK → nodes)
    local_port: Integer
    remote_port: Integer
    status: Enum (Active, Inactive, Connecting, Error)

    # Metrics
    bytes_sent: BigInteger
    bytes_received: BigInteger
    latency_ms: Float

    # Relationships
    node: Node

# AccessRule Model (ACL)
class AccessRule(Base):
    __tablename__ = "access_rules"

    id: UUID (PK)
    name: String
    priority: Integer (1-100, lower = higher priority)
    action: Enum (ALLOW, DENY)

    # Matching criteria
    source_ip: String (CIDR)
    destination_ip: String (CIDR)
    protocol: Enum (TCP, UDP, ICMP, ALL)
    destination_port: Integer

    # Time-based
    valid_from: DateTime (nullable)
    valid_until: DateTime (nullable)

    enabled: Boolean
    created_by_id: UUID (FK → users)
```

#### 4. Middleware Layer (`app/middleware/`)

Cross-cutting concerns.

**RateLimitMiddleware** (`rate_limit.py`)
```python
class RateLimitMiddleware:
    def __init__(self, redis: Redis):
        self.redis = redis

    async def __call__(self, request: Request, call_next):
        # Get user/IP identifier
        identifier = self._get_identifier(request)

        # Check rate limit in Redis
        current = await self.redis.incr(f"rate_limit:{identifier}")

        if current == 1:
            await self.redis.expire(f"rate_limit:{identifier}", 60)

        # Get limit based on user role
        limit = self._get_limit(request.user.role)

        if current > limit:
            raise HTTPException(429, "Rate limit exceeded")

        # Add headers
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, limit - current))

        return response
```

#### 5. WebSocket Manager (`app/websocket/manager.py`)

Gestione connessioni WebSocket real-time.

```python
class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.redis = Redis()

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket

    async def disconnect(self, client_id: str):
        self.active_connections.pop(client_id, None)

    async def broadcast(self, message: dict):
        """Send message to all connected clients"""
        for connection in self.active_connections.values():
            await connection.send_json(message)

    async def send_to_user(self, user_id: str, message: dict):
        """Send message to specific user"""
        # Find all connections for this user
        for client_id, ws in self.active_connections.items():
            if client_id.startswith(f"user_{user_id}"):
                await ws.send_json(message)

    async def subscribe_redis_events(self):
        """Subscribe to Redis pub/sub for multi-instance support"""
        pubsub = self.redis.pubsub()
        await pubsub.subscribe("tunnel_events", "node_events", "acl_events")

        async for message in pubsub.listen():
            if message["type"] == "message":
                await self.broadcast(json.loads(message["data"]))
```

**Eventi supportati:**
- `node.connected` - Nodo connesso
- `node.disconnected` - Nodo disconnesso
- `tunnel.created` - Tunnel creato
- `tunnel.closed` - Tunnel chiuso
- `acl.rule_updated` - Regola ACL aggiornata
- `audit.new_event` - Nuovo evento audit

### Frontend Components

#### 1. Pages (`src/pages/`)

Pagine principali dell'applicazione.

**DashboardPage.jsx**
- Dashboard overview con stats
- 3D network visualization
- Real-time updates via WebSocket
- Quick actions panel

**TunnelsPage.jsx**
- Lista tunnel attivi
- Create tunnel modal
- Tunnel stats & metrics
- Close tunnel action

**NodesPage.jsx**
- Lista nodi registrati
- Node health indicators
- Create node modal
- Node metrics visualization

**ACLPage.jsx**
- Lista regole ACL
- Create/Edit ACL modal
- Priority ordering
- Enable/Disable toggle

**AuditPage.jsx**
- Audit log viewer
- Advanced filters (user, action, date, severity)
- Export functionality (JSON/CSV/SIEM)
- Statistics dashboard

**SettingsPage.jsx**
- User profile management
- Password change
- 2FA setup wizard
- Preferences

#### 2. Components (`src/components/`)

Componenti riutilizzabili.

**NetworkMap3D.jsx** (Three.js)
```jsx
import { Canvas } from '@react-three/fiber'
import { OrbitControls } from '@react-three/drei'

function NetworkMap3D({ nodes, tunnels }) {
  return (
    <Canvas camera={{ position: [0, 0, 50], fov: 75 }}>
      {/* Lights */}
      <ambientLight intensity={0.5} />
      <pointLight position={[10, 10, 10]} />

      {/* Controls */}
      <OrbitControls />

      {/* Hub centrale */}
      <mesh position={[0, 0, 0]}>
        <sphereGeometry args={[2, 32, 32]} />
        <meshStandardMaterial color="blue" />
      </mesh>

      {/* Nodi edge */}
      {nodes.map((node, index) => {
        const angle = (index / nodes.length) * Math.PI * 2
        const radius = 20
        const x = Math.cos(angle) * radius
        const z = Math.sin(angle) * radius

        return (
          <Node3D
            key={node.id}
            position={[x, 0, z]}
            node={node}
            onClick={() => handleNodeClick(node)}
          />
        )
      })}

      {/* Tunnel connections */}
      {tunnels.map(tunnel => (
        <Connection3D
          key={tunnel.id}
          start={hubPosition}
          end={getNodePosition(tunnel.node_id)}
          status={tunnel.status}
        />
      ))}
    </Canvas>
  )
}
```

**Features 3D:**
- Circular layout per nodi
- Colori status (verde=online, giallo=warning, rosso=offline)
- Connessioni animate
- OrbitControls per navigazione
- Raycasting per click detection
- Labels con CSS2DRenderer
- 60 FPS rendering

#### 3. State Management (Redux Toolkit)

Store centralizzato con Redux Toolkit.

**authSlice.js**
```javascript
const authSlice = createSlice({
  name: 'auth',
  initialState: {
    user: null,
    token: null,
    refreshToken: null,
    isAuthenticated: false,
    loading: false,
    error: null
  },
  reducers: {
    loginStart: (state) => {
      state.loading = true
      state.error = null
    },
    loginSuccess: (state, action) => {
      state.user = action.payload.user
      state.token = action.payload.token
      state.refreshToken = action.payload.refreshToken
      state.isAuthenticated = true
      state.loading = false
    },
    loginFailure: (state, action) => {
      state.error = action.payload
      state.loading = false
    },
    logout: (state) => {
      state.user = null
      state.token = null
      state.isAuthenticated = false
    }
  }
})
```

**Altri slices:**
- `tunnelsSlice.js` - Gestione stato tunnel
- `nodesSlice.js` - Gestione stato nodi
- `aclSlice.js` - Gestione stato ACL rules
- `auditSlice.js` - Gestione audit logs

---

## 🔄 Data Flow

### 1. Authentication Flow

```
User Input (email + password)
    ↓
Frontend: authSlice.loginStart()
    ↓
API Call: POST /api/v1/auth/login
    ↓
Backend: AuthEndpoint.login()
    ↓
Validate credentials (Argon2 hash)
    ↓
If 2FA enabled:
    ├─ Return 2FA required response
    └─ Frontend: Prompt for TOTP code
        ↓
    API Call: POST /api/v1/auth/verify-2fa
        ↓
    Verify TOTP code (pyotp)
        ↓
If valid:
    ├─ Generate JWT tokens (access + refresh)
    ├─ Store in Redis (session tracking)
    └─ Return tokens to frontend
        ↓
Frontend: authSlice.loginSuccess()
    ↓
Store tokens in localStorage
    ↓
Redirect to Dashboard
```

### 2. Tunnel Creation Flow

```
User clicks "Create Tunnel"
    ↓
Frontend: CreateTunnelModal
    ↓
User selects node + tunnel type (SSH/HTTPS)
    ↓
API Call: POST /api/v1/tunnels
    {
      "node_id": "uuid",
      "type": "SSH",
      "local_port": 22
    }
    ↓
Backend: TunnelService.create_tunnel()
    ↓
Check ACL rules (Zero Trust)
    ├─ If DENIED: Return 403 Forbidden
    └─ If ALLOWED: Continue
        ↓
    Allocate remote port (dynamic, 10000-60000)
        ↓
    Create tunnel in database
        ↓
    Start SSH server (asyncssh)
        ↓
    Wait for agent connection
        ↓
    Publish event to Redis:
        {"event": "tunnel.created", "tunnel_id": "..."}
        ↓
    WebSocket Manager receives event
        ↓
    Broadcast to all connected clients
        ↓
Frontend: WebSocket receives message
    ↓
Redux: tunnelsSlice.addTunnel()
    ↓
UI updates in real-time
    ↓
3D Visualization adds connection line
```

### 3. ACL Rule Evaluation Flow

```
Connection request from Node A to Node B
    ↓
Backend: ACLService.evaluate_connection()
    ↓
Get all ACL rules (order by priority ASC)
    ↓
For each rule:
    ├─ Check if enabled
    ├─ Check time window (valid_from, valid_until)
    ├─ Match source IP (CIDR notation)
    ├─ Match destination IP
    ├─ Match protocol (TCP/UDP/ICMP/ALL)
    └─ Match port
        ↓
If all conditions match:
    ├─ If action = ALLOW: Allow connection
    └─ If action = DENY: Deny connection
        ↓
If no rule matched:
    └─ Default DENY (Zero Trust principle)
        ↓
Log decision to audit log (MongoDB)
    ↓
Increment Prometheus metric:
    - orizon_acl_rules_matched_total (if matched)
    - orizon_acl_rules_denied_total (if denied)
```

### 4. Real-time Update Flow (WebSocket)

```
Backend Event (es. node.connected)
    ↓
Service publishes to Redis Pub/Sub:
    redis.publish("node_events", {
      "event": "node.connected",
      "node_id": "uuid",
      "timestamp": "..."
    })
    ↓
WebSocket Manager subscribes to Redis
    ↓
WebSocket Manager receives message
    ↓
Broadcast to all connected WebSocket clients
    ↓
Frontend WebSocket client receives message
    ↓
Dispatch Redux action:
    dispatch(nodesSlice.nodeConnected(data))
    ↓
Redux reducer updates state
    ↓
React components re-render
    ↓
3D Visualization updates node color (green)
    ↓
Toast notification appears
```

---

## 🔐 Security Architecture

### Defense in Depth

Sicurezza implementata a **tutti i livelli**:

```
Layer 7 (Application)
    ├─ Input validation (Pydantic)
    ├─ CSRF protection
    ├─ XSS sanitization
    └─ SQL injection prevention (ORM)

Layer 6 (Session/Auth)
    ├─ JWT authentication
    ├─ 2FA TOTP
    ├─ Token rotation (30 giorni)
    └─ Session tracking

Layer 5 (Authorization)
    ├─ RBAC (4 livelli)
    ├─ ACL rules (Zero Trust)
    └─ Permission checks per endpoint

Layer 4 (Network)
    ├─ TLS/SSL (HTTPS)
    ├─ SSH tunnels cifrati
    ├─ Firewall rules
    └─ Port security

Layer 3 (Data)
    ├─ Password hashing (Argon2)
    ├─ Encryption at rest (futuro)
    ├─ Secure key storage
    └─ Audit logging

Layer 2 (Infrastructure)
    ├─ Container isolation
    ├─ Network policies (K8s)
    ├─ Resource limits
    └─ Health checks

Layer 1 (Physical)
    └─ DigitalOcean datacenter security
```

### Zero Trust Implementation

**Principi applicati:**

1. **Never Trust, Always Verify**
   - Ogni richiesta autenticata e autorizzata
   - JWT token verificato ad ogni chiamata
   - ACL rules valutate in real-time

2. **Least Privilege Access**
   - RBAC con 4 livelli gerarchici
   - Permessi granulari per endpoint
   - Users can only see/modify their own resources

3. **Micro-segmentation**
   - ACL rules per nodo
   - IP whitelisting
   - Protocol filtering

4. **Default DENY**
   - Se nessuna regola ACL matcha → DENY
   - Nessun accesso implicito

5. **Continuous Verification**
   - Health checks ogni 30s
   - Heartbeat monitoring
   - Auto-disconnect su timeout

---

## 🚀 Scalabilità & Performance

### Horizontal Scaling

**Backend (Stateless):**
```yaml
# Kubernetes HPA
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: backend-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: backend-api
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

**Frontend (Static):**
```yaml
# Nginx replicas per load distribution
replicas: 3
```

**Database (Vertical + Replication):**
```yaml
# PostgreSQL
- Primary (write)
- Replica 1 (read)
- Replica 2 (read)

# Redis
- Master (write)
- Sentinel nodes (failover)
- Slave nodes (read)
```

### Performance Optimizations

**Backend:**
- ✅ Async/await per I/O operations
- ✅ Connection pooling (PostgreSQL, Redis)
- ✅ Query optimization (indexes, N+1 prevention)
- ✅ Caching (Redis) per dati frequenti
- ✅ Rate limiting per protezione

**Frontend:**
- ✅ Code splitting (React.lazy)
- ✅ Memoization (React.memo, useMemo)
- ✅ Virtual scrolling per liste lunghe
- ✅ WebSocket per real-time (no polling)
- ✅ Build optimization (Vite)

**Database:**
- ✅ Indexes su colonne filtrate
- ✅ Partitioning per audit logs (time-based)
- ✅ Connection pooling
- ✅ Query caching

### Benchmarks Attesi

| Metric | Target | Current |
|--------|--------|---------|
| API Latency (P95) | < 100ms | ~50ms |
| WebSocket Concurrent Connections | 10,000+ | 10,000+ |
| Tunnel Creation Time | < 2s | ~1s |
| 3D Rendering FPS | 60 | 60 (fino a 100 nodi) |
| Audit Log Query (10K records) | < 200ms | ~100ms |

---

## 🌐 Deployment Architecture

### Development Environment

```
Docker Compose Stack:
├─ backend (FastAPI)       :8000
├─ frontend (Vite dev)     :3000
├─ postgresql              :5432
├─ redis                   :6379
├─ mongodb                 :27017
├─ prometheus              :9090
└─ grafana                 :3001
```

### Staging Environment

```
Kubernetes Cluster (DigitalOcean):
├─ Namespace: orizon-staging
├─ Pods:
│   ├─ backend-api (2 replicas)
│   ├─ frontend (2 replicas)
│   ├─ postgresql (StatefulSet, 1 replica)
│   ├─ redis (3 replicas, Sentinel)
│   └─ mongodb (3 replicas, ReplicaSet)
├─ Services:
│   ├─ backend-service (ClusterIP)
│   ├─ frontend-service (LoadBalancer)
│   └─ db-service (ClusterIP)
└─ Ingress (Nginx):
    ├─ staging.orizon.syneto.net → frontend
    └─ api.staging.orizon.syneto.net → backend
```

### Production Environment

```
Kubernetes Cluster (Multi-region):
├─ Namespace: orizon-production
├─ Pods:
│   ├─ backend-api (HPA: 3-10 replicas)
│   ├─ frontend (HPA: 2-5 replicas)
│   ├─ postgresql (StatefulSet, HA)
│   │   ├─ Primary (1)
│   │   └─ Replicas (2)
│   ├─ redis (Sentinel, 3 masters + 3 slaves)
│   └─ mongodb (ReplicaSet, 3 nodes)
├─ Monitoring:
│   ├─ Prometheus (scraping metrics)
│   ├─ Grafana (dashboards)
│   ├─ Loki (log aggregation)
│   └─ AlertManager (alerting)
├─ Ingress (TLS):
│   ├─ www.orizon.syneto.net → frontend
│   └─ api.orizon.syneto.net → backend
└─ Persistent Volumes:
    ├─ PostgreSQL data (100Gi)
    ├─ MongoDB data (500Gi)
    └─ Redis RDB snapshots (10Gi)
```

**High Availability:**
- Multi-zone deployment
- LoadBalancer con health checks
- Auto-scaling (CPU/RAM based)
- Database replication (sync/async)
- Redis Sentinel (automatic failover)
- Backup automatici (daily)

---

## 📊 Diagrammi UML

### Component Diagram

```
┌─────────────────────────────────────────────────────┐
│               Frontend Components                    │
├─────────────────────────────────────────────────────┤
│ Pages:                                              │
│  - DashboardPage                                    │
│  - TunnelsPage                                      │
│  - NodesPage                                        │
│  - ACLPage                                          │
│  - AuditPage                                        │
│                                                     │
│ Core Components:                                    │
│  - NetworkMap3D (Three.js)                         │
│  - CreateTunnelModal                               │
│  - ACLRuleCard                                     │
│  - AuditLogViewer                                  │
│                                                     │
│ Services:                                           │
│  - apiService (Axios)                              │
│  - websocketService (Socket.IO)                    │
│                                                     │
│ Store:                                              │
│  - authSlice                                        │
│  - tunnelsSlice                                     │
│  - nodesSlice                                       │
│  - aclSlice                                         │
└─────────────────────────────────────────────────────┘
                        │
                        │ HTTP/WS
                        ▼
┌─────────────────────────────────────────────────────┐
│              Backend Components                      │
├─────────────────────────────────────────────────────┤
│ API Layer:                                          │
│  - auth.py (JWT, 2FA)                              │
│  - users.py (RBAC)                                 │
│  - tunnels.py (SSH/HTTPS)                          │
│  - acl.py (Zero Trust)                             │
│  - audit.py (Logs)                                 │
│                                                     │
│ Services:                                           │
│  - TunnelService                                    │
│  - ACLService                                       │
│  - AuditService                                     │
│  - TOTPService                                      │
│                                                     │
│ Models (SQLAlchemy):                                │
│  - User                                             │
│  - Node                                             │
│  - Tunnel                                           │
│  - AccessRule                                       │
│                                                     │
│ Middleware:                                         │
│  - RateLimitMiddleware                             │
│  - CORSMiddleware                                  │
│                                                     │
│ WebSocket Manager:                                  │
│  - Connection pooling                               │
│  - Broadcasting                                     │
│  - Redis pub/sub                                    │
└─────────────────────────────────────────────────────┘
                        │
                        │ SQLAlchemy
                        ▼
┌─────────────────────────────────────────────────────┐
│                Data Layer                            │
├─────────────────────────────────────────────────────┤
│ PostgreSQL:                                         │
│  Tables: users, nodes, tunnels, access_rules        │
│                                                     │
│ Redis:                                              │
│  - Cache (user sessions)                           │
│  - Pub/Sub (events)                                │
│  - Rate limiting (counters)                        │
│                                                     │
│ MongoDB:                                            │
│  Collections: audit_logs, analytics                 │
└─────────────────────────────────────────────────────┘
```

---

## 🎯 Conclusioni

L'architettura di Orizon Zero Trust Connect è progettata per essere:

- **Scalabile** - Supporta crescita da 1 a 1000+ nodi
- **Sicura** - Zero Trust, Defense in Depth, Compliance
- **Performante** - Async I/O, caching, optimization
- **Mantenibile** - Layered, modular, testable
- **Cloud-Native** - Containerized, Kubernetes-ready

**Next Steps:**
- Implementare Service Mesh (Istio) per observability avanzata
- Multi-tenancy support
- Geographic load balancing
- Advanced ML-based anomaly detection

---

**Documento maintained by:** Marco Lorenzi @ Syneto/Orizon
**Last Review:** Gennaio 2025
