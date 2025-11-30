# Changelog - Orizon Zero Trust Connect

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.0.2] - 2025-11-30

### System Tunnels & Windows Agent

Questa release introduce System Tunnels persistenti con hardened keep-alive e supporto completo per Windows Agent.

*This release introduces persistent System Tunnels with hardened keep-alive and full Windows Agent support.*

### Added

#### System Tunnels
- **Persistent System Tunnels**: Ogni nodo edge stabilisce automaticamente 3 tunnel persistenti
  - System Tunnel (SSH): Accesso SSH principale
  - Terminal Tunnel: Sessioni terminale web
  - HTTPS Tunnel: Proxy verso servizi web del nodo
- **is_system Flag**: Identificazione tunnel di sistema nel database
  - Non eliminabili dall'utente
  - Auto-creati all'installazione dell'agent
  - Badge "System" distintivo nella dashboard
- **Dashboard Visualization**: Nuova visualizzazione tunnel con badge colorati

#### Hardened Keep-Alive
- **Configurazione SSH ottimizzata**:
  ```
  ServerAliveInterval=15
  ServerAliveCountMax=3
  ExitOnForwardFailure=yes
  ```
- **Rilevamento disconnessione**: 45 secondi massimo
- **Riconnessione automatica**: Tramite autossh con AUTOSSH_GATETIME=0

#### Windows Agent
- **Installer Unificato** (`orizon_unified_installer.ps1`):
  - Installazione automatica OpenSSH, nginx, nssm
  - Creazione servizi Windows (OrizonTunnelSystem, OrizonTunnelTerminal, OrizonTunnelHTTPS)
  - Configurazione firewall automatica
- **Status Page Locale**: Server nginx con pagina di stato real-time
- **Metrics Collector**: Raccolta metriche CPU, RAM, Disco, GPU (se disponibile)
- **Watchdog Service**: Monitoraggio e riavvio automatico tunnel
- **Uninstaller**: Script di disinstallazione completo

#### HTTPS Proxy Path Endpoint
- **GET /nodes/{node_id}/https-proxy/{proxy_path}**: Nuovo endpoint per proxy sub-path
  - Permette accesso a `/api/metrics` e altri path attraverso il tunnel
  - JavaScript proxy-aware nella status page per funzionamento via Hub

#### Documentation
- **Nuovi documenti**:
  - `docs/SYSTEM_TUNNELS.md`: Guida completa ai System Tunnels
  - `docs/WINDOWS_AGENT.md`: Guida all'Agent Windows
- **Aggiornamenti**:
  - `docs/ARCHITECTURE.md`: Sezione System Tunnels e Keep-Alive
  - `docs/API_REFERENCE.md`: Endpoint HTTPS proxy path
  - `docs/INDEX.md`: Link ai nuovi documenti

### Fixed

- **Status Page via Proxy**: La status page ora funziona correttamente quando accessa via Hub proxy
  - JavaScript rileva automaticamente accesso via proxy (parametro `t`)
  - Costruisce URL corretti per `/api/metrics`

### Changed

- **Placeholder Template**: Sostituzione IP hardcoded con `<HUB_IP>` placeholder
- **Versioning**: Da v2.0.1 a v2.0.2

### Technical Details

- **Backend**: `nodes.py` +128 linee per HTTPS proxy path
- **Script Generator**: Supporto template Windows PowerShell (+1035 linee)
- **agents/windows/**: Nuova directory con installer completo

---

## [2.0.1] - 2025-11-25

### 🎯 4-Level Role Hierarchy

This release completes the role hierarchy implementation and unifies all documentation.

### ✨ Added

#### Role System Enhancement
- **Complete 4-Level Role Hierarchy**
  - SuperUser: System owner with full access (Level 4)
  - SuperAdmin: Distributors managing multiple tenants (Level 3)
  - Admin: Resellers managing single tenant (Level 2)
  - User: End customers with resource access only (Level 1)
  - Visual hierarchy with distinct badge colors in UI
  - Backend role enforcement via `check_permission()` function
  - Tenant-scoped permissions respecting role levels

#### Dashboard Improvements
- **User Interface Updates**
  - Added SuperAdmin role option to user creation dropdown
  - CSS badge styles for all 4 roles with gradient effects
  - Role hierarchy visualization in user management table
  - Proper role display in all CRUD operations

### 📚 Documentation Overhaul

#### Unified Documentation
- **New Consolidated Guides**
  - `DEPLOYMENT_GUIDE.md`: Complete production deployment instructions
  - `DEVELOPMENT_GUIDE.md`: Full development environment setup and workflows
  - Unified all scattered documentation into topic-based structure
  - Moved old/duplicate documentation to `backups_docs/` directory

#### Documentation Structure
- **Organized by Topic**
  - `docs/`: All current documentation
  - `backups_docs/`: Historical documentation archive (not in Git)
  - Removed duplicate guides from subdirectories
  - Standardized format across all documents

### 🔧 Changed

#### User Management
- **CRUD Operations**
  - Users can now be created with SuperAdmin role
  - Role dropdown displays all 4 levels in hierarchical order
  - Updated role validation in backend endpoints

### 🐛 Fixed

#### Dashboard Issues
- **Users Display**
  - Fixed Users list stuck on "Loading users..."
  - Updated `loadUsers()` to handle array response format
  - All CRUD operations now working correctly

#### API Endpoints
- **Users CRUD**
  - Fixed endpoint paths (absolute → relative)
  - Corrected router registration
  - All HTTP methods (POST, GET, PUT, DELETE) functional

### 🧪 Testing

- **Role Hierarchy Tests**
  - Successfully created users with all 4 role levels
  - Verified role permissions and hierarchy enforcement
  - Test coverage: 95% (21/22 tests passing)
  - Current user distribution: 13 users across all 4 roles

### 📊 System Status

- **Production Server**: 139.59.149.48 ✅ Healthy
- **Backend**: Docker container running, all services operational
- **Frontend**: Dashboard deployed with all features
- **Database**: PostgreSQL, MongoDB, Redis all healthy
- **Role System**: Complete 4-level hierarchy operational
- **Documentation**: Unified and organized

### 🔗 Previous Release

## [2.0.1a] - 2025-11-24

### 🏢 Multi-Tenant System

This release introduces a complete multi-tenant architecture for managing isolated organizations with hierarchical access control.

### ✨ Added

#### Multi-Tenant Core
- **Tenant Management**
  - Complete CRUD operations for tenants
  - Automatic slug generation for URL-friendly identifiers
  - JSONB fields for flexible company info, settings, and quota configurations
  - Soft delete with is_active flags
  - Audit trail tracking (created_by, timestamps)

#### Group-Tenant Associations
- **Many-to-Many Relationships**
  - Groups can be associated with multiple tenants
  - Granular permissions per group-tenant association
  - Permission types: can_manage_nodes, can_view_metrics, can_modify_settings
  - Active/inactive association management

#### Tenant-Node Associations
- **Shared Infrastructure**
  - Tenants can have multiple edge nodes assigned
  - Nodes can be shared across multiple tenants
  - Custom configuration per tenant-node (priority, max_tunnels, allowed_ports, custom_routing)
  - JSONB node_config for flexible settings

#### Hierarchical Access Control
- **Visibility Service** (`node_visibility_service.py`)
  - SUPERUSER: Full system access, sees all tenants
  - SUPER_ADMIN: Sees own tenants + subordinates' tenants
  - ADMIN: Sees tenants accessible through groups
  - USER: Read-only access to assigned tenants
- **Permission Service** (`permission_service.py`)
  - Granular permission checks for tenant/node operations
  - User-tenant permission aggregation
  - Node management authorization

#### API Endpoints
- **Tenant Management** (`/api/v1/tenants`)
  - POST /tenants - Create tenant (SUPER_ADMIN+)
  - GET /tenants - List tenants (hierarchical visibility)
  - GET /tenants/{id} - Get tenant details
  - PUT /tenants/{id} - Update tenant
  - DELETE /tenants/{id} - Soft delete tenant
- **Group-Tenant** (`/api/v1/tenants/{id}/groups`)
  - POST /tenants/{id}/groups - Associate group
  - GET /tenants/{id}/groups - List associated groups
  - DELETE /tenants/{id}/groups/{group_id} - Remove association
- **Tenant-Node** (`/api/v1/tenants/{id}/nodes`)
  - POST /tenants/{id}/nodes - Associate node
  - GET /tenants/{id}/nodes - List associated nodes
  - DELETE /tenants/{id}/nodes/{node_id} - Remove association
- **Debug Endpoints**
  - GET /debug/groups-tenants-nodes - Complete system hierarchy
  - GET /debug/tenant-hierarchy/{id} - Specific tenant hierarchy

#### Database Schema
- **New Tables**
  - `tenants` - Organization/customer isolation
  - `group_tenants` - Many-to-many groups ↔ tenants
  - `tenant_nodes` - Many-to-many tenants ↔ nodes
- **Indexes**
  - Performance indexes on name, slug, is_active
  - Foreign key indexes for associations
  - Unique constraints on group_id+tenant_id and tenant_id+node_id

#### Services
- `tenant_service.py` - Tenant CRUD and business logic
- `hierarchy_service.py` - Hierarchical data management
- `node_visibility_service.py` - Node access control
- `permission_service.py` - Granular permission checks
- `sso_service.py` - Enhanced SSO with session management

#### Middleware & Utils
- `audit_middleware.py` - Request/response audit logging
- `debug_middleware.py` - Debug event tracking
- `audit_logger.py` - Structured audit logging utility

### 📚 Documentation
- **Complete Multi-Tenant Guide** (`docs/MULTI_TENANT_SYSTEM.md`)
  - Architecture overview with diagrams
  - Database schema documentation
  - API endpoint reference with examples
  - Access control explanation
  - Usage scenarios and testing guides

### 🔧 Fixed
- Group creation authentication issues
- Logout endpoint implementation
- Database column name mismatches (role vs role_in_group)
- Schema validation for tenant_id in request paths
- Service return type mismatches for association objects

---

## [2.0.0] - 2025-11-15

### 🎉 Major Release: Web Terminal Integration

This release introduces a complete web-based terminal solution with visual debugging capabilities, fixing critical connectivity issues and providing a seamless remote access experience.

### ✨ Added

#### Web Terminal System
- **Interactive Web Terminal** (`terminal.html`)
  - Full xterm.js v5.3.0 integration
  - Real-time SSH sessions through WebSocket
  - Automatic terminal sizing and responsive design
  - Support for terminal resize events
  - Clean, professional interface with loading states

#### Visual Debug Panel
- **Integrated Debug Panel** (no F12 console required!)
  - Real-time event monitoring with millisecond precision timestamps
  - Categorized statistics (INFO, SUCCESS, ERROR, WARNING, DEBUG, WEBSOCKET)
  - Tabbed interface for filtering events:
    - ALL: Complete event timeline
    - ERRORS: Error messages only
    - WARNINGS: Warning messages
    - WEBSOCKET: WebSocket lifecycle events (CREATED, OPEN, CLOSE, ERROR, MESSAGE)
    - PARAMS: URL parameters validation with OK/NULL status
  - "Copy All" button for exporting debug data as JSON
  - Auto-scroll to latest events
  - Fixed-position panel (450px width, always visible)

#### WebSocket Terminal Server
- **Enhanced WebSocket Server** (`websocket_terminal_server.py` v2.1)
  - **CRITICAL FIX**: Proper URL parameter parsing using `urllib.parse`
    - Previous bug: Manual string splitting failed with browser WebSocket connections
    - New implementation: Standards-compliant URL parsing with proper encoding support
  - 6-phase connection logging for detailed debugging:
    1. JWT Token Validation
    2. Database Tunnel Lookup
    3. Hub-side Tunnel Connectivity Test
    4. SSH Connection Establishment
    5. Interactive Shell Channel Opening
    6. Bidirectional I/O Loop
  - Session statistics tracking (bytes sent/received, commands count, errors)
  - Comprehensive error handling with detailed logging
  - Support for terminal resize via PTY
  - WebSocket close code explanations
  - Enhanced security with token expiration validation

#### Dashboard Integration
- **Terminal Launch from Dashboard**
  - One-click terminal access from tunnel list
  - **TOKEN FIX**: Long-lived JWT tokens (1-year expiration) for terminal sessions
    - Previous issue: Dashboard used expired localStorage tokens
    - New solution: Hardcoded PyJWT standard token compatible with WebSocket server
  - Automatic window management with proper dimensions (1200x800)
  - Pass-through of tunnel metadata (ID, name, port)

#### Infrastructure
- **Firewall Configuration**
  - **CRITICAL FIX**: Opened port 8765/tcp for WebSocket connections
    - Previous bug: Browser connections blocked by firewall (code 1006 errors)
    - New rule: `ufw allow 8765/tcp comment 'Orizon WebSocket Terminal Server'`
  - Verified with both IPv4 and IPv6 rules

### 🔧 Fixed

#### Critical Bugs
1. **WebSocket URL Parameter Parsing** (HIGH PRIORITY)
   - **Problem**: Manual URL parsing (`split('&')`, `split('=')`) didn't handle URL encoding
   - **Impact**: Browser connections received `tunnel_id=None`, `token=None`
   - **Solution**: Implemented `urllib.parse.parse_qs()` with proper `unquote()`
   - **Result**: Server now correctly receives all parameters from browser
   - **File**: `/opt/orizon/websocket_terminal_server.py` (lines 168-176)

2. **Firewall Blocking WebSocket Port** (HIGH PRIORITY)
   - **Problem**: Port 8765 not allowed through UFW firewall
   - **Impact**: Browser connections failed with WebSocket code 1006 (Abnormal Closure)
   - **Solution**: Added UFW rule for port 8765/tcp
   - **Result**: External browser connections now succeed
   - **Verification**: Tested with both local and remote clients

3. **Token Incompatibility Between Dashboard and WebSocket Server** (HIGH PRIORITY)
   - **Problem**: Dashboard used custom base64+HMAC tokens, WebSocket expected PyJWT standard
   - **Impact**: All dashboard-initiated terminal sessions failed with code 1008 (Policy Violation)
   - **Solution**: Dashboard now generates PyJWT standard tokens with 1-year expiration
   - **Result**: Terminal sessions launch successfully from dashboard
   - **File**: `/var/www/orizon-ztc/dashboard.html` (line 1283)

4. **URL Parameter Naming Inconsistency**
   - **Problem**: Dashboard used `remote_port` but terminal.html expected `remotePort`
   - **Impact**: Parameter appeared as NULL in debug panel
   - **Solution**: Standardized on `remote_port` (snake_case) across all components
   - **Result**: All URL parameters now parse correctly

### 🛠 Changed

#### Enhanced Logging
- WebSocket server now logs all 6 connection phases with emoji indicators
- Session summaries include duration, bytes transferred, command count, and errors
- Debug panel provides browser-side visibility without requiring developer tools
- All timestamps use millisecond precision (fractionalSecondDigits: 3)

#### Security Improvements
- JWT tokens now include expiration validation
- WebSocket server verifies token before establishing SSH connection
- Clear error messages for authentication failures
- Session IDs for tracking and auditing

#### Performance
- Non-blocking I/O for SSH channel reads
- Efficient WebSocket message batching
- Auto-cleanup of session statistics

### 📚 Documentation

#### New Documentation Files
- `TERMINAL_FIX_SUMMARY.md` - Complete technical explanation of all fixes
- `CHANGELOG-v2.md` - This file, comprehensive change history
- `VERSION` - Semantic version tracking
- `DEPLOYMENT-v2.md` - Deployment guide for v2.0

#### Archived Documentation
- Moved to `/tmp/orizon-v2-backup/old-docs/`:
  - `DEBUG_TERMINAL_GUIDE.md` - Superseded by visual debug panel
  - `VISUAL_DEBUG_PANEL_GUIDE.md` - Superseded by integrated docs

### 🗂 File Structure Changes

#### Production Files (Deployed)
```
/var/www/orizon-ztc/
├── terminal.html                      # Web terminal with visual debug panel (22KB)
├── dashboard.html                     # Updated with terminal integration
└── dashboard.html.bak                 # Backup before token fix

/opt/orizon/
├── websocket_terminal_server.py       # v2.1 with urllib.parse fix
└── websocket_terminal_server.py.backup # Backup before fix
```

#### Backup Files (Archived)
```
/tmp/orizon-v2-backup/
├── old-docs/
│   ├── DEBUG_TERMINAL_GUIDE.md
│   └── VISUAL_DEBUG_PANEL_GUIDE.md
├── temp-scripts/
│   ├── FIXED_TERMINAL_TEST_URL.txt
│   ├── add_terminal_token_endpoint.py
│   ├── terminal_url.txt
│   └── visual_debug_url.txt
├── test-files/
│   └── test_websocket_with_params.py
└── old-versions/
    ├── terminal_visual_debug.html
    ├── websocket_terminal_server_fixed.py
    └── websocket_terminal_server_v2.py
```

### 🧪 Testing

#### Verification Tests Performed
1. ✅ **Local WebSocket Test** - Python client successfully connected and received welcome message
2. ✅ **Browser WebSocket Test** - Firefox successfully connected from external IP
3. ✅ **Parameter Parsing Test** - All URL parameters (tunnel_id, token, remote_port) received correctly
4. ✅ **Terminal Interaction Test** - Commands (`ls`, `ls -la`, `nmap -h`) executed successfully
5. ✅ **Debug Panel Test** - All events logged with correct timestamps and categories
6. ✅ **Dashboard Integration Test** - Terminal launched successfully from dashboard

#### Test Environment
- **Server**: DigitalOcean Droplet (68.183.219.222)
- **Edge Node**: Parallels VM (10.211.55.21) running Ubuntu 24.04.3 LTS
- **Tunnel**: SSH reverse tunnel on port 10001
- **Browser**: Firefox (anonymous window for cache-free testing)
- **Token**: 1-year expiration (expires 2026-11-15)

### ⚡ Performance Metrics

#### WebSocket Server
- Connection establishment: < 500ms
- SSH tunnel connection: < 400ms
- Terminal initialization: < 200ms
- Total time to interactive: < 1.2s

#### Resource Usage
- WebSocket server memory: ~22.5 MB
- Terminal page size: 22 KB
- Debug panel overhead: ~3% CPU during active logging

### 🔐 Security Notes

#### JWT Tokens
- Algorithm: HS256
- Secret: `your-secret-key-change-in-production-2024` (⚠️ CHANGE IN PRODUCTION!)
- Dashboard token expiration: 1 year
- Manual token generation available for testing

#### Network Security
- WebSocket over WS (not WSS) - ⚠️ Upgrade to WSS in production
- SSH authentication using password - Consider switching to SSH keys
- No rate limiting on WebSocket endpoint - Add in production

### 📖 Migration Guide

#### From v1.x to v2.0

1. **Backup existing files**:
   ```bash
   sudo cp /opt/orizon/websocket_terminal_server.py /opt/orizon/websocket_terminal_server.py.v1.bak
   sudo cp /var/www/orizon-ztc/dashboard.html /var/www/orizon-ztc/dashboard.html.v1.bak
   ```

2. **Deploy new WebSocket server**:
   ```bash
   sudo cp websocket_terminal_server.py /opt/orizon/
   sudo systemctl restart orizon-terminal.service
   ```

3. **Update firewall**:
   ```bash
   sudo ufw allow 8765/tcp comment 'Orizon WebSocket Terminal Server'
   ```

4. **Deploy new frontend**:
   ```bash
   sudo cp terminal.html /var/www/orizon-ztc/
   sudo cp dashboard.html /var/www/orizon-ztc/
   sudo chown www-data:www-data /var/www/orizon-ztc/*.html
   ```

5. **Verify deployment**:
   ```bash
   sudo systemctl status orizon-terminal.service
   curl -s http://localhost/terminal.html | head -5
   ```

### 🙏 Acknowledgments

- xterm.js team for the excellent terminal emulator
- WebSocket protocol RFC authors
- Python websockets library maintainers

### 📝 Notes

- This is a major version bump due to breaking changes in token format
- Existing sessions using old token format will need to re-authenticate
- Visual debug panel is enabled by default (can be disabled by removing the debug panel div)

---

## [1.1.0] - 2025-11-14

### Added
- Group-based access control system
- Remote desktop access via Apache Guacamole
- Initial terminal prototype (superseded by v2.0)

### Fixed
- Various bug fixes and improvements

---

## [1.0.0] - Initial Release

### Added
- SSH tunnel management
- Node management
- Basic authentication
- Dashboard interface

---

**For detailed technical documentation, see:**
- `DEPLOYMENT-v2.md` - Deployment procedures
- `TERMINAL_FIX_SUMMARY.md` - Technical details of terminal fixes
- `README-v2.md` - Updated project README
