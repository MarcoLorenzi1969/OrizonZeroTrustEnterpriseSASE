# Orizon Zero Trust Connect - Security Guide

## Zero Trust Principles

Orizon implements Zero Trust security architecture following these core principles:

1. **Never Trust, Always Verify** - Every request is authenticated and authorized
2. **Least Privilege Access** - Users get minimum required permissions
3. **Assume Breach** - Design assumes attackers are already inside
4. **Verify Explicitly** - Always validate identity, location, and device

## Authentication

### JWT Token Authentication

The system uses JSON Web Tokens (JWT) for stateless authentication.

#### Token Structure

```json
{
  "sub": "user-uuid",
  "email": "user@example.com",
  "role": "admin",
  "exp": 1764369312,
  "iat": 1764365712,
  "type": "access"
}
```

#### Token Types

| Token | Lifetime | Purpose |
|-------|----------|---------|
| Access Token | 60 minutes | API authentication |
| Refresh Token | 7 days | Obtain new access tokens |

#### Security Configuration

```python
# backend/app/core/config.py
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")  # 256-bit key
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 7
```

### Password Security

- **Hashing**: bcrypt with cost factor 12
- **Minimum Length**: 8 characters (recommended: 12+)
- **Complexity**: Recommended mix of upper, lower, numbers, symbols

```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)
```

## Authorization

### Role-Based Access Control (RBAC)

Four hierarchical roles control system access:

| Role | Level | Permissions |
|------|-------|-------------|
| SUPERUSER | 4 | Full system access |
| SUPER_ADMIN | 3 | Manage subordinate users/resources |
| ADMIN | 2 | Manage assigned users/resources |
| USER | 1 | Access assigned resources only |

### API Endpoint Protection

```python
from app.auth.dependencies import require_role

# Only SUPERUSER can access
@router.delete("/users/{id}", dependencies=[Depends(require_role([UserRole.SUPERUSER]))])

# Multiple roles allowed
@router.get("/users", dependencies=[Depends(require_role([UserRole.SUPERUSER, UserRole.SUPER_ADMIN, UserRole.ADMIN]))])
```

### Group-Based Node Access

Node access is controlled through group membership:

```
User ─┬─ Member of Group A ─┬─ Node 1 (ssh: true)
      │                     └─ Node 2 (rdp: true)
      └─ Member of Group B ─── Node 3 (vnc: true)
```

Permission types per node:
- `ssh` - SSH terminal access
- `rdp` - Remote Desktop Protocol
- `vnc` - Virtual Network Computing
- `ssl_tunnel` - HTTPS proxy access

## Transport Security

### HTTPS Configuration

All traffic is encrypted using TLS 1.2/1.3.

```nginx
# Nginx SSL Configuration
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
ssl_prefer_server_ciphers off;
ssl_session_cache shared:SSL:10m;
ssl_session_timeout 1d;
```

### Certificate Management

#### Self-Signed Certificate (Current)

```bash
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/nginx/ssl/orizon.key \
  -out /etc/nginx/ssl/orizon.crt \
  -subj "/C=IT/ST=Italy/L=Milan/O=Orizon/CN=139.59.149.48"
```

#### Let's Encrypt (Recommended for Domain)

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal
sudo certbot renew --dry-run
```

## SSH Tunnel Security

### Agent Authentication

Each node has a unique agent token:

```python
agent_token = f"agt_{secrets.token_urlsafe(32)}"
# Example: agt_HRe023-kmbkSXyGnZLIFeD44YAZAzZYH35vqgrOofVM
```

### Tunnel Authentication Flow

```
1. Node Agent → SSH Server (port 2222)
2. Agent presents agent_token
3. Server validates against database
4. If valid, reverse tunnel established
5. Heartbeat every 30 seconds maintains connection
```

### Proxy Token Security

HTTPS proxy uses one-time tokens:

```python
# Generate token (valid 60 seconds, single-use)
proxy_token = secrets.token_urlsafe(32)
await redis.setex(f"proxy_token:{proxy_token}", 60, f"{user_id}:{node_id}")

# Token is deleted after first use
token_data = await redis.get(f"proxy_token:{proxy_token}")
await redis.delete(f"proxy_token:{proxy_token}")
```

## API Security

### Request Validation

All requests are validated using Pydantic schemas:

```python
class UserCreateRequest(BaseModel):
    email: EmailStr  # Validates email format
    full_name: str
    password: str
    role: UserRole = UserRole.USER
    is_active: bool = True
```

### SQL Injection Prevention

SQLAlchemy ORM with parameterized queries:

```python
# Safe query
result = await db.execute(
    select(User).where(User.email == email)
)

# Never do this
# query = f"SELECT * FROM users WHERE email = '{email}'"
```

### CORS Configuration

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://139.59.149.48"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Data Protection

### Sensitive Data Handling

| Data Type | Protection |
|-----------|------------|
| Passwords | bcrypt hashed, never stored plain |
| JWT Secret | Environment variable, not in code |
| Agent Tokens | Unique per node, revocable |
| API Keys | Not exposed in logs |

### Database Security

```yaml
# PostgreSQL isolation
postgres:
  environment:
    - POSTGRES_USER=orizon
    - POSTGRES_PASSWORD=${SECURE_PASSWORD}
  networks:
    - internal  # Not exposed to internet
```

### Log Sanitization

Sensitive data is excluded from logs:

```python
# Don't log passwords or tokens
logger.info(f"User login: {email}")  # OK
logger.info(f"Password: {password}")  # NEVER
```

## Network Security

### Firewall Rules (UFW)

```bash
# Allow SSH (management)
sudo ufw allow 22/tcp

# Allow HTTPS
sudo ufw allow 443/tcp

# Allow HTTP (redirect to HTTPS)
sudo ufw allow 80/tcp

# Allow SSH Tunnel Server
sudo ufw allow 2222/tcp

# Enable firewall
sudo ufw enable
```

### Docker Network Isolation

```yaml
networks:
  orizon-network:
    driver: bridge
    internal: false  # Allows internet access

  internal:
    driver: bridge
    internal: true   # No internet access
```

### Port Exposure

| Port | Service | Access |
|------|---------|--------|
| 80 | HTTP | Public (redirects to 443) |
| 443 | HTTPS | Public |
| 2222 | SSH Tunnel | Public (agent connections) |
| 8000 | Backend API | Internal only |
| 5432 | PostgreSQL | Internal only |
| 6379 | Redis | Internal only |
| 27017 | MongoDB | Internal only |

## Audit Logging

### Access Logs

All API access is logged:

```python
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    logger.info(
        f"{request.method} {request.url.path} "
        f"status={response.status_code} "
        f"duration={duration:.3f}s "
        f"ip={request.client.host}"
    )
    return response
```

### Security Events

Logged security events:
- Login attempts (success/failure)
- Password changes
- Permission changes
- Node access attempts
- Tunnel establishment/termination

### Log Storage

```python
# MongoDB for audit logs
class AccessLog:
    user_id: str
    node_id: str
    action: str  # "ssh_connect", "rdp_connect", etc.
    source_ip: str
    success: bool
    timestamp: datetime
    details: dict
```

## Security Best Practices

### For Administrators

1. **Use Strong Passwords**
   - Minimum 12 characters
   - Mix of character types
   - Unique per system

2. **Rotate Secrets Regularly**
   ```bash
   # Generate new JWT secret
   openssl rand -hex 32
   ```

3. **Monitor Access Logs**
   ```bash
   # Check for failed logins
   docker compose logs backend | grep "401"
   ```

4. **Keep Systems Updated**
   ```bash
   sudo apt update && sudo apt upgrade -y
   docker compose pull
   docker compose up -d
   ```

5. **Backup Encryption Keys**
   - Store JWT_SECRET_KEY securely
   - Keep backup of SSL certificates

### For Users

1. **Secure Your Credentials**
   - Don't share passwords
   - Use password manager
   - Enable 2FA when available

2. **Report Suspicious Activity**
   - Unexpected login notifications
   - Unknown nodes appearing
   - Access denied errors

3. **Logout When Done**
   - Close browser sessions
   - Don't save passwords in browser on shared computers

## Incident Response

### Security Incident Procedure

1. **Identify** - Detect and confirm the incident
2. **Contain** - Limit the damage
3. **Eradicate** - Remove the threat
4. **Recover** - Restore systems
5. **Document** - Record lessons learned

### Emergency Actions

```bash
# Revoke all sessions (change JWT secret)
export JWT_SECRET_KEY=$(openssl rand -hex 32)
docker compose restart backend

# Disable compromised user
docker compose exec postgres psql -U orizon -d orizon_ztc \
  -c "UPDATE users SET is_active = false WHERE email = 'compromised@example.com'"

# Block IP address
sudo ufw deny from <attacker_ip>
```

## Compliance Considerations

### Data Privacy
- User data stored in EU (DigitalOcean Amsterdam)
- Passwords hashed, not recoverable
- Access logs retained for audit

### Security Standards
- OWASP Top 10 addressed
- TLS 1.2+ required
- Regular security updates

## Security Contacts

For security issues, contact:
- Email: security@orizon.one
- GitHub: Open private security advisory
