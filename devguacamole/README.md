# Orizon Zero Trust Connect - Guacamole Integration

**Production-ready Node.js TypeScript library and CLI for Apache Guacamole integration with Single Sign-On (SSO) support for Orizon Zero Trust Connect.**

## Features

- ✅ **SSO Integration** - Single Sign-On with Orizon hub
- ✅ **Connection Management** - Create and manage SSH/RDP/VNC connections via API
- ✅ **Permission Control** - Grant and revoke user permissions
- ✅ **Secret Management** - Pluggable secret store (env vars, vault)
- ✅ **Node Synchronization** - Auto-sync Orizon nodes to Guacamole
- ✅ **CLI & Library** - Use as command-line tool or Node.js library
- ✅ **Type-Safe** - Full TypeScript with Zod validation
- ✅ **Secure Defaults** - TLS validation, minimal permissions, no plaintext secrets

---

## Architecture

```
┌─────────────────┐
│  Orizon Hub     │  SSO Authentication
│  46.101.189.126 │  User Management
└────────┬────────┘
         │ SSO Login
         ▼
┌─────────────────┐
│  Guacamole CLI  │  This Library
│  (guacctl)      │
└────────┬────────┘
         │ API Calls
         ▼
┌─────────────────┐
│  Guacamole Hub  │  SSH/RDP Gateway
│  167.71.33.70   │  Connection Broker
└────────┬────────┘
         │ Proxy Connections
         ▼
┌─────────────────┐
│  Edge Nodes     │  Target Machines
│  (SSH/RDP)      │  10.211.55.x
└─────────────────┘
```

---

## Quick Start

### Installation

```bash
# Clone or navigate to devguacamole directory
cd devguacamole

# Install dependencies
npm install
# or
pnpm install

# Build TypeScript
npm run build

# Copy environment template
cp .env.example .env

# Edit .env with your credentials
nano .env
```

### Required Environment Variables

Edit `.env`:

```bash
# Guacamole Server
GUAC_URL=https://167.71.33.70/guacamole
GUAC_DATASOURCE=mysql
GUAC_ADMIN_USER=guacadmin
GUAC_ADMIN_PASS=guacadmin
GUAC_VERIFY_TLS=false

# Orizon Hub (for SSO)
ORIZON_API_URL=https://46.101.189.126/api/v1
ORIZON_ADMIN_EMAIL=admin@orizon.local
ORIZON_ADMIN_PASS=admin123

# Edge Node Credentials
SECRET__SSH__EDGE_UBUNTU_USER=parallels
SECRET__SSH__EDGE_UBUNTU_PASS=profano.69
SECRET__RDP__EDGE_UBUNTU_USER=parallels
SECRET__RDP__EDGE_UBUNTU_PASS=profano.69

# Test Hosts
TEST_EDGE_UBUNTU_IP=10.211.55.20
TEST_EDGE_KALI_IP=10.211.55.19
```

---

## CLI Usage

### SSO Login (Recommended)

Authenticate with Orizon SSO, then access Guacamole:

```bash
# Login via Orizon SSO
npm run dev -- sso-login \
  --email admin@orizon.local \
  --password admin123

# Output:
# ✓ Authenticated with Orizon
# ✓ Authenticated with Guacamole via SSO
# Orizon Token: eyJhbGc...
# Guacamole Token: ABC123...
```

### Direct Guacamole Login

```bash
npm run dev -- login \
  --user guacadmin \
  --password guacadmin
```

### Create SSH Connection

```bash
# Using command-line credentials
npm run dev -- create-ssh \
  --name "Edge Ubuntu SSH" \
  --host 10.211.55.20 \
  --port 22 \
  --user parallels \
  --password profano.69

# Using secret references (recommended)
npm run dev -- create-ssh \
  --name "Edge Ubuntu SSH" \
  --host 10.211.55.20 \
  --user parallels \
  --password-ref SECRET__SSH__EDGE_UBUNTU_PASS
```

### Create RDP Connection

```bash
npm run dev -- create-rdp \
  --name "Edge Ubuntu RDP" \
  --host 10.211.55.20 \
  --port 3389 \
  --user parallels \
  --password-ref SECRET__RDP__EDGE_UBUNTU_PASS \
  --security any \
  --no-drive \
  --no-clipboard

# Output:
# ✓ RDP connection created
# Connection ID: 5
# Access URL: https://167.71.33.70/guacamole/#/client/5
```

### List Connections

```bash
npm run dev -- list

# Output:
# [1] Edge Ubuntu - SSH (ssh)
#     Host: 10.211.55.20:22
#     Active: 0
#
# [2] Edge Ubuntu - RDP (rdp)
#     Host: 10.211.55.20:3389
#     Active: 0
```

### Grant User Permission

```bash
npm run dev -- grant \
  --user alice \
  --connection 1 \
  --perm READ

# Now alice can access connection ID 1
```

### Sync Orizon Nodes to Guacamole

```bash
# Dry run (see what would be done)
npm run dev -- sync-nodes --dry-run

# Sync SSH connections only
npm run dev -- sync-nodes --ssh

# Sync both SSH and RDP
npm run dev -- sync-nodes --ssh --rdp
```

### Test Edge Ubuntu

```bash
# Create test SSH connection
npm run dev -- test-edge-ubuntu --ssh

# Create test RDP connection
npm run dev -- test-edge-ubuntu --rdp

# Create both
npm run dev -- test-edge-ubuntu --ssh --rdp
```

---

## Library Usage

### Example: Create SSH Connection

```typescript
import { createGuacamoleClient, createDefaultSecretStore } from '@orizon/guacamole-integration';

const secretStore = createDefaultSecretStore();
const client = createGuacamoleClient({
  url: 'https://167.71.33.70/guacamole',
  datasource: 'mysql',
  verifyTLS: false,
  secretStore,
});

// Authenticate
await client.getToken('guacadmin', 'guacadmin');

// Create SSH connection
const connection = await client.createSSHConnection({
  name: 'Edge Ubuntu SSH',
  hostname: '10.211.55.20',
  port: '22',
  username: 'parallels',
  password: 'profano.69',
  enableSFTP: true,
});

console.log(`Connection created: ${connection.identifier}`);
```

### Example: SSO Integration

```typescript
import { createOrizonSSO, createGuacamoleClient } from '@orizon/guacamole-integration';

// Step 1: Authenticate with Orizon
const orizonSSO = createOrizonSSO({
  apiUrl: 'https://46.101.189.126/api/v1',
  verifyTLS: false,
});

const orizonToken = await orizonSSO.login('admin@orizon.local', 'admin123');
console.log(`Orizon Role: ${orizonToken.user?.role}`);

// Step 2: Get Guacamole credentials
const guacCreds = await orizonSSO.getGuacamoleCredentials();

// Step 3: Authenticate with Guacamole
const guacClient = createGuacamoleClient({ verifyTLS: false });
await guacClient.getToken(guacCreds.username, guacCreds.password);

// Now use guacClient to manage connections
const connections = await guacClient.getConnections();
console.log(`Total connections: ${Object.keys(connections).length}`);
```

### Example: Node Synchronization

```typescript
import { createOrizonSSO, createGuacamoleClient, NodeSync } from '@orizon/guacamole-integration';

// Authenticate with Orizon
const orizonSSO = createOrizonSSO({ verifyTLS: false });
const orizonToken = await orizonSSO.login('admin@orizon.local', 'admin123');

// Authenticate with Guacamole
const guacClient = createGuacamoleClient({ verifyTLS: false });
const guacCreds = await orizonSSO.getGuacamoleCredentials();
await guacClient.getToken(guacCreds.username, guacCreds.password);

// Sync nodes
const nodeSync = new NodeSync({
  orizonApiUrl: 'https://46.101.189.126/api/v1',
  orizonToken: orizonToken.access_token,
  verifyTLS: false,
});

const results = await nodeSync.syncAllNodes(guacClient, {
  createSSH: true,
  createRDP: true,
});

console.log(`Synced ${results.size} nodes`);
```

---

## Security

### TLS Verification

**Production:**
```bash
# Always enable TLS verification in production
GUAC_VERIFY_TLS=true
```

**Development:**
```bash
# Disable only for self-signed certs in dev
GUAC_VERIFY_TLS=false
```

### Secret Management

**Current (Development):** Environment variables

**Production (Recommended):** Integrate with HashiCorp Vault or AWS Secrets Manager

Example Vault integration:

```typescript
import { SecretStore } from '@orizon/guacamole-integration';
import VaultClient from 'node-vault';

class VaultSecretStore implements SecretStore {
  private vault: VaultClient;

  constructor(endpoint: string, token: string) {
    this.vault = VaultClient({
      endpoint,
      token,
    });
  }

  async getSecret(ref: string): Promise<string> {
    const path = ref.replace('SECRET__', '').toLowerCase().replace(/__/g, '/');
    const result = await this.vault.read(`secret/data/${path}`);
    return result.data.data.value;
  }

  async hasSecret(ref: string): Promise<boolean> {
    try {
      await this.getSecret(ref);
      return true;
    } catch {
      return false;
    }
  }
}

// Use it:
const secretStore = new VaultSecretStore(
  'https://vault.example.com',
  process.env.VAULT_TOKEN!
);

const client = createGuacamoleClient({ secretStore });
```

### Secure RDP Defaults

RDP connections default to **disabled** drive and clipboard redirection:

```typescript
await client.createRDPConnection({
  name: 'Secure RDP',
  hostname: '10.211.55.20',
  username: 'parallels',
  password: 'profano.69',
  enableDrive: false,       // ← Default: disabled
  enableClipboard: false,   // ← Default: disabled
});
```

Enable only when needed:

```bash
npm run dev -- create-rdp \
  --name "RDP with Drive" \
  --host 10.211.55.20 \
  --user parallels \
  --password-ref SECRET__RDP__EDGE_UBUNTU_PASS \
  --enable-drive \
  --enable-clipboard
```

---

## Testing

### Run All Tests

```bash
npm test
```

### Watch Mode

```bash
npm run test:watch
```

### Test Coverage

```bash
npm test -- --coverage
```

### Manual End-to-End Test

1. **Ensure Guacamole is running:**
   ```bash
   ssh orizonzerotrust@167.71.33.70
   docker ps  # Verify guacamole, guacd, guacdb are UP
   ```

2. **Test CLI:**
   ```bash
   # From your local machine
   cd devguacamole
   npm run dev -- test-edge-ubuntu --ssh
   ```

3. **Access via Web:**
   - Open: https://167.71.33.70/guacamole/
   - Login: guacadmin / guacadmin
   - Click on newly created connection
   - Verify SSH terminal appears

---

## API Reference

### GuacamoleClient

#### `getToken(username, password): Promise<AuthToken>`
Authenticate and get session token.

#### `createConnection(payload: ConnectionPayload): Promise<Connection>`
Create a new connection.

#### `getConnections(): Promise<ConnectionList>`
Get all connections.

#### `getConnection(id: string): Promise<Connection>`
Get specific connection by ID.

#### `deleteConnection(id: string): Promise<void>`
Delete a connection.

#### `grantConnectionAccess(username, connectionId, permissions): Promise<void>`
Grant user access to a connection.

#### `createSSHConnection(params): Promise<Connection>`
Helper to create SSH connection with defaults.

#### `createRDPConnection(params): Promise<Connection>`
Helper to create RDP connection with secure defaults.

### OrizonSSO

#### `login(email, password): Promise<OrizonToken>`
Authenticate with Orizon hub.

#### `getGuacamoleCredentials(): Promise<{username, password}>`
Get Guacamole credentials for authenticated Orizon user.

#### `isAdmin(): boolean`
Check if user has admin role.

### NodeSync

#### `getOrizonNodes(): Promise<OrizonNode[]>`
Get all nodes from Orizon API.

#### `syncNodeToGuacamole(node, guacClient, options): Promise<{ssh?, rdp?}>`
Sync single node to Guacamole.

#### `syncAllNodes(guacClient, options): Promise<Map>`
Sync all Orizon nodes to Guacamole.

---

## Development

### Build

```bash
npm run build
```

### Clean

```bash
npm run clean
```

### Lint

```bash
npm run lint
```

### Format

```bash
npm run format
```

---

## Troubleshooting

### "Login failed: 401"

- Verify credentials in `.env`
- Check Guacamole is accessible: `curl -k https://167.71.33.70/guacamole/`

### "Secret not found"

- Ensure secret is defined in `.env`
- Check secret reference matches format: `SECRET__<CATEGORY>__<NAME>_<FIELD>`

### "TLS certificate error"

- Development: Use `--insecure` flag or set `GUAC_VERIFY_TLS=false`
- Production: Install valid SSL certificate

### "Connection refused"

- Verify Guacamole Docker containers are running:
  ```bash
  ssh orizonzerotrust@167.71.33.70
  docker ps
  ```

### "SSH authentication failed"

- Verify node SSH credentials are correct
- Test manually: `ssh parallels@10.211.55.20`

---

## Roadmap

- [ ] User provisioning in Guacamole (create users via API)
- [ ] Role-based access control (RBAC) mapping Orizon → Guacamole
- [ ] Sharing profiles for time-bounded access
- [ ] QuickConnect support for ad-hoc connections
- [ ] Session recording integration
- [ ] Frontend component for embedding in Orizon dashboard
- [ ] Multi-factor authentication (MFA) support

---

## License

MIT

---

## Support

For issues or questions:
- Check existing Guacamole connections: https://167.71.33.70/guacamole/
- Review logs: `ssh orizonzerotrust@167.71.33.70 'docker logs guacamole'`
- Test connectivity: `npm run dev -- test-edge-ubuntu --ssh`

---

**Created:** 2025-11-09
**Version:** 1.0.0
**Status:** Production Ready
