# 🔐 Security Guide - Orizon Zero Trust Connect

**Versione:** 1.0.0
**Last Updated:** Gennaio 2025
**Autore:** Marco Lorenzi @ Syneto/Orizon Security

---

## 📋 Indice

1. [Panoramica Sicurezza](#panoramica-sicurezza)
2. [Zero Trust Architecture](#zero-trust-architecture)
3. [Autenticazione e Autorizzazione](#autenticazione-e-autorizzazione)
4. [Gestione Password](#gestione-password)
5. [Two-Factor Authentication (2FA)](#two-factor-authentication-2fa)
6. [Access Control Lists (ACL)](#access-control-lists-acl)
7. [Network Security](#network-security)
8. [Data Protection](#data-protection)
9. [Audit e Compliance](#audit-e-compliance)
10. [Security Hardening](#security-hardening)
11. [Incident Response](#incident-response)
12. [Security Checklist](#security-checklist)

---

## 🎯 Panoramica Sicurezza

Orizon Zero Trust Connect implementa un approccio **Defense in Depth** con sicurezza integrata a tutti i livelli dello stack.

### Principi di Sicurezza

1. **Zero Trust** - "Never trust, always verify"
2. **Least Privilege** - Accesso minimo necessario
3. **Defense in Depth** - Sicurezza multi-livello
4. **Fail Secure** - Comportamento sicuro di default
5. **Audit Everything** - Logging completo di tutte le azioni
6. **Compliance First** - GDPR/NIS2/ISO 27001 by design

### Security Layers

```
┌─────────────────────────────────────────┐
│  Layer 7: Application Security         │
│  - Input Validation                     │
│  - XSS/CSRF Protection                  │
│  - SQL Injection Prevention             │
└─────────────────────────────────────────┘
┌─────────────────────────────────────────┐
│  Layer 6: Authentication & Session      │
│  - JWT Tokens                           │
│  - 2FA TOTP                             │
│  - Session Management                   │
└─────────────────────────────────────────┘
┌─────────────────────────────────────────┐
│  Layer 5: Authorization                 │
│  - RBAC (4 levels)                      │
│  - ACL Rules                            │
│  - Permission Checks                    │
└─────────────────────────────────────────┘
┌─────────────────────────────────────────┐
│  Layer 4: Network Security              │
│  - TLS/SSL                              │
│  - SSH Tunnels                          │
│  - Firewall Rules                       │
└─────────────────────────────────────────┘
┌─────────────────────────────────────────┐
│  Layer 3: Data Security                 │
│  - Argon2 Hashing                       │
│  - Encryption at Rest                   │
│  - Secure Key Storage                   │
└─────────────────────────────────────────┘
┌─────────────────────────────────────────┐
│  Layer 2: Infrastructure                │
│  - Container Isolation                  │
│  - Network Policies                     │
│  - Resource Limits                      │
└─────────────────────────────────────────┘
┌─────────────────────────────────────────┐
│  Layer 1: Physical Security             │
│  - Datacenter Security (DigitalOcean)  │
└─────────────────────────────────────────┘
```

---

## 🛡️ Zero Trust Architecture

### Principi Zero Trust Implementati

#### 1. Never Trust, Always Verify

**Ogni richiesta è autenticata e autorizzata:**
```python
# Ogni endpoint API richiede JWT token
@router.get("/nodes")
async def get_nodes(
    current_user: User = Depends(get_current_user),  # Verifica JWT
    db: AsyncSession = Depends(get_db)
):
    # Check RBAC permissions
    if not has_permission(current_user, "read:nodes"):
        raise HTTPException(403, "Permission denied")

    # Check ACL rules
    if not acl_service.evaluate(current_user, "read", "nodes"):
        raise HTTPException(403, "ACL denied")

    # Procedi solo se tutte le verifiche OK
    return await node_service.list_nodes(db, current_user)
```

#### 2. Least Privilege Access

**RBAC Hierarchy:**
```
SuperUser (Marco - Owner)
    └─ Può tutto
    └─ Può creare: SuperAdmin, Admin, User

SuperAdmin (Distributori)
    └─ Gestisce clienti enterprise
    └─ Può creare: Admin, User

Admin (Rivenditori)
    └─ Gestisce clienti finali
    └─ Può creare: User

User (Cliente finale)
    └─ Accesso solo alle proprie risorse
    └─ Nessun permesso amministrativo
```

**Permessi Granulari:**
```python
# Esempio permessi per ruolo
PERMISSIONS = {
    "SuperUser": [
        "create:user",
        "delete:user",
        "read:all_audit",
        "manage:system",
        "create:acl_rule"
    ],
    "Admin": [
        "create:user",  # solo User role
        "read:own_audit",
        "create:tunnel",
        "manage:own_nodes"
    ],
    "User": [
        "read:own_resources",
        "create:tunnel",  # solo sui propri nodi
        "update:own_profile"
    ]
}
```

#### 3. Micro-segmentation

**ACL Rules per Segmentazione:**
```json
// Esempio: Segmentazione rete produzione vs dev
[
  {
    "name": "Prod: Block all by default",
    "priority": 100,
    "action": "DENY",
    "source_ip": "0.0.0.0/0",
    "destination_ip": "10.0.1.0/24",
    "protocol": "ALL"
  },
  {
    "name": "Prod: Allow only from office",
    "priority": 10,
    "action": "ALLOW",
    "source_ip": "203.0.113.0/24",
    "destination_ip": "10.0.1.0/24",
    "protocol": "TCP",
    "port": 22,
    "time_restrictions": {
      "days": ["Mon", "Tue", "Wed", "Thu", "Fri"],
      "hours": "08:00-18:00"
    }
  }
]
```

#### 4. Default DENY

**Comportamento Sicuro:**
```python
# ACL Evaluation Logic
def evaluate_acl(connection):
    rules = get_rules_by_priority()  # Ordinate per priority ASC

    for rule in rules:
        if rule.matches(connection):
            return rule.action  # ALLOW o DENY

    # Se nessuna regola matcha → DEFAULT DENY
    return "DENY"
```

#### 5. Continuous Verification

**Health Monitoring:**
```python
# Health check ogni 30 secondi
async def monitor_nodes():
    while True:
        for node in active_nodes:
            last_heartbeat = node.last_seen
            if (now() - last_heartbeat) > 60:  # 60s timeout
                node.status = "offline"
                await close_all_tunnels(node)
                await send_alert("Node offline", node.id)

        await asyncio.sleep(30)
```

---

## 🔑 Autenticazione e Autorizzazione

### JWT Token Authentication

#### Token Structure

**Access Token (24h validity):**
```json
{
  "header": {
    "alg": "HS256",
    "typ": "JWT"
  },
  "payload": {
    "sub": "user-uuid",
    "email": "user@example.com",
    "role": "Admin",
    "exp": 1705161600,  // 24h expiration
    "iat": 1705075200,
    "jti": "token-unique-id"
  },
  "signature": "..."
}
```

**Refresh Token (7 giorni validity):**
```json
{
  "payload": {
    "sub": "user-uuid",
    "type": "refresh",
    "exp": 1705680000,  // 7 days
    "iat": 1705075200,
    "jti": "refresh-token-id"
  }
}
```

#### Token Security Best Practices

✅ **DO:**
```javascript
// 1. Store tokens securely
// Opzione A: httpOnly cookie (più sicuro)
document.cookie = `token=${accessToken}; HttpOnly; Secure; SameSite=Strict`;

// Opzione B: Secure localStorage
const secureStorage = {
  setToken: (token) => {
    // Encrypt before storing (opzionale)
    const encrypted = encryptToken(token);
    localStorage.setItem('access_token', encrypted);
  },
  getToken: () => {
    const encrypted = localStorage.getItem('access_token');
    return decryptToken(encrypted);
  }
};

// 2. Auto-refresh prima della scadenza
setInterval(async () => {
  const tokenExpiry = parseJwt(accessToken).exp;
  const now = Date.now() / 1000;

  if (tokenExpiry - now < 300) {  // 5 min before expiry
    await refreshToken();
  }
}, 60000);  // Check ogni minuto

// 3. Handle 401 globally
axios.interceptors.response.use(
  response => response,
  async error => {
    if (error.response?.status === 401) {
      try {
        await refreshToken();
        // Retry original request
        return axios.request(error.config);
      } catch {
        // Logout se refresh fallisce
        logout();
        redirectToLogin();
      }
    }
    return Promise.reject(error);
  }
);
```

❌ **DON'T:**
```javascript
// ❌ NON salvare token in query string
window.location = `/dashboard?token=${accessToken}`;

// ❌ NON loggare token
console.log('Token:', accessToken);

// ❌ NON salvare in plain localStorage senza encryption
localStorage.setItem('token', accessToken);

// ❌ NON ignorare token expiration
// (usa sempre auto-refresh)
```

#### JWT Secret Rotation

**Rotazione Automatica ogni 30 giorni:**
```python
# backend/app/auth/jwt_rotation.py
class JWTRotationService:
    async def rotate_secret(self):
        # 1. Genera nuovo secret
        new_secret = secrets.token_urlsafe(64)

        # 2. Salva in database con valid_from
        await self.db.execute(
            insert(JWTSecret).values(
                secret=new_secret,
                valid_from=now(),
                valid_until=now() + timedelta(days=37)  # 30 + 7 grace
            )
        )

        # 3. Invalida vecchio secret (grace period 7 giorni)
        await self.db.execute(
            update(JWTSecret)
            .where(JWTSecret.valid_from < now() - timedelta(days=30))
            .values(valid_until=now() + timedelta(days=7))
        )

    async def verify_token(self, token: str):
        # Prova con tutti i secret validi (current + grace period)
        active_secrets = await self.get_active_secrets()

        for secret in active_secrets:
            try:
                payload = jwt.decode(token, secret, algorithms=["HS256"])
                return payload
            except jwt.InvalidTokenError:
                continue

        raise HTTPException(401, "Invalid token")
```

### Role-Based Access Control (RBAC)

#### Permission Check Decorator

```python
# backend/app/auth/rbac.py
from functools import wraps

def require_permission(permission: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, current_user: User, **kwargs):
            if not has_permission(current_user.role, permission):
                raise HTTPException(
                    403,
                    f"Permission '{permission}' required. Your role: {current_user.role}"
                )
            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator

# Usage
@router.delete("/users/{user_id}")
@require_permission("delete:user")
async def delete_user(
    user_id: str,
    current_user: User = Depends(get_current_user)
):
    # Solo se has_permission("delete:user") = True
    await user_service.delete(user_id)
```

#### Resource Ownership Check

```python
def check_resource_ownership(resource, user: User):
    """
    Verifica che user sia owner della risorsa o abbia ruolo superiore
    """
    # SuperUser vede tutto
    if user.role == "SuperUser":
        return True

    # Check ownership
    if resource.owner_id == user.id:
        return True

    # Check hierarchy (se risorsa creata da sotto-utente)
    if is_sub_user(resource.owner_id, user.id):
        return True

    return False

# Usage
@router.get("/nodes/{node_id}")
async def get_node(
    node_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    node = await node_service.get(db, node_id)
    if not node:
        raise HTTPException(404, "Node not found")

    if not check_resource_ownership(node, current_user):
        raise HTTPException(403, "Access denied to this resource")

    return node
```

---

## 🔒 Gestione Password

### Password Policy

**Requirements enforced:**
```python
# backend/app/auth/password_policy.py
class PasswordPolicy:
    MIN_LENGTH = 12
    REQUIRE_UPPERCASE = True
    REQUIRE_LOWERCASE = True
    REQUIRE_DIGIT = True
    REQUIRE_SYMBOL = True
    MIN_ENTROPY = 40  # bits
    MAX_SIMILARITY_USERNAME = 0.7  # Levenshtein distance
    COMMON_PASSWORDS_BLACKLIST = load_blacklist()  # Top 10K

    def validate(self, password: str, user_email: str = None) -> bool:
        # 1. Length check
        if len(password) < self.MIN_LENGTH:
            raise ValueError(f"Password must be at least {self.MIN_LENGTH} chars")

        # 2. Complexity checks
        if not re.search(r'[A-Z]', password):
            raise ValueError("Password must contain uppercase letter")

        if not re.search(r'[a-z]', password):
            raise ValueError("Password must contain lowercase letter")

        if not re.search(r'\d', password):
            raise ValueError("Password must contain digit")

        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise ValueError("Password must contain special character")

        # 3. Entropy check
        entropy = calculate_entropy(password)
        if entropy < self.MIN_ENTROPY:
            raise ValueError(f"Password too predictable (entropy: {entropy})")

        # 4. Common password check
        if password.lower() in self.COMMON_PASSWORDS_BLACKLIST:
            raise ValueError("Password is too common")

        # 5. Similarity check
        if user_email:
            username = user_email.split('@')[0]
            similarity = levenshtein_similarity(password.lower(), username.lower())
            if similarity > self.MAX_SIMILARITY_USERNAME:
                raise ValueError("Password too similar to username")

        return True
```

### Password Hashing (Argon2)

**Why Argon2 > bcrypt:**
- Winner of Password Hashing Competition 2015
- Resistente a GPU/ASIC attacks
- Memory-hard algorithm
- Side-channel attack resistant

**Implementation:**
```python
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

ph = PasswordHasher(
    time_cost=3,          # Iterations
    memory_cost=65536,    # 64MB memory
    parallelism=4,        # 4 threads
    hash_len=32,          # 32 bytes output
    salt_len=16           # 16 bytes salt
)

def hash_password(password: str) -> str:
    """
    Hash password con Argon2id
    Returns: $argon2id$v=19$m=65536,t=3,p=4$...
    """
    return ph.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    """
    Verifica password contro hash
    """
    try:
        ph.verify(hashed, password)

        # Check if rehash needed (parameters changed)
        if ph.check_needs_rehash(hashed):
            # Rehash con parametri più forti
            return hash_password(password)

        return True
    except VerifyMismatchError:
        return False
```

### Password Reset Flow (Sicuro)

```python
# 1. Request password reset
@router.post("/auth/password-reset/request")
async def request_password_reset(email: str):
    user = await user_service.get_by_email(email)

    # ⚠️ Non rivelare se email esiste o no (timing attack prevention)
    if user:
        # Genera token sicuro (1 ora validity)
        reset_token = secrets.token_urlsafe(32)
        await redis.setex(
            f"reset_token:{reset_token}",
            3600,  # 1 hour
            user.id
        )

        # Invia email con link
        reset_link = f"https://orizon.syneto.net/reset-password?token={reset_token}"
        await send_email(
            to=user.email,
            subject="Password Reset",
            body=f"Click here to reset: {reset_link}"
        )

        # Log audit
        await audit_log("PASSWORD_RESET_REQUESTED", user.id)

    # Risposta identica sempre (previene user enumeration)
    return {"message": "If email exists, reset link sent"}

# 2. Verify token e reset password
@router.post("/auth/password-reset/confirm")
async def confirm_password_reset(token: str, new_password: str):
    # Get user_id da token
    user_id = await redis.get(f"reset_token:{token}")
    if not user_id:
        raise HTTPException(400, "Invalid or expired token")

    user = await user_service.get(user_id)

    # Valida nuova password
    password_policy.validate(new_password, user.email)

    # Update password
    user.hashed_password = hash_password(new_password)
    await db.commit()

    # Invalida token (one-time use)
    await redis.delete(f"reset_token:{token}")

    # Invalida tutti i token JWT esistenti
    await invalidate_user_sessions(user.id)

    # Log audit
    await audit_log("PASSWORD_RESET_COMPLETED", user.id)

    return {"message": "Password reset successful"}
```

---

## 🔐 Two-Factor Authentication (2FA)

### TOTP Implementation

**Time-based One-Time Password (RFC 6238):**
```python
import pyotp
import qrcode
from io import BytesIO
import base64

class TOTPService:
    def __init__(self):
        self.issuer = "Orizon ZTC"

    def generate_secret(self, user_email: str) -> dict:
        """
        Genera secret TOTP e QR code
        """
        # Genera secret random (base32, 160 bits)
        secret = pyotp.random_base32()

        # Crea provisioning URI per QR code
        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(
            name=user_email,
            issuer_name=self.issuer
        )

        # Genera QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        # Convert to base64 data URL
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        qr_code_base64 = base64.b64encode(buffered.getvalue()).decode()
        qr_code_data_url = f"data:image/png;base64,{qr_code_base64}"

        return {
            "secret": secret,
            "qr_code": qr_code_data_url,
            "manual_entry_key": secret,
            "provisioning_uri": provisioning_uri
        }

    def verify_totp(self, secret: str, code: str) -> bool:
        """
        Verifica codice TOTP (6 digit)
        Accetta codici ±30 secondi (1 window prima/dopo)
        """
        totp = pyotp.TOTP(secret)
        return totp.verify(code, valid_window=1)

    def generate_backup_codes(self, count: int = 10) -> list:
        """
        Genera backup codes per recovery
        Format: ABCD-1234-EFGH-5678
        """
        codes = []
        for _ in range(count):
            code = secrets.token_hex(8).upper()
            # Format: XXXX-XXXX-XXXX-XXXX
            formatted = '-'.join([code[i:i+4] for i in range(0, 16, 4)])
            codes.append(formatted)
        return codes
```

### 2FA Enrollment Flow

```python
# 1. Setup 2FA
@router.post("/2fa/setup")
async def setup_2fa(current_user: User = Depends(get_current_user)):
    # Genera secret
    data = totp_service.generate_secret(current_user.email)

    # Salva secret in DB (encrypted)
    current_user.totp_secret_temp = encrypt(data["secret"])
    await db.commit()

    # Return QR code
    return {
        "secret": data["secret"],
        "qr_code": data["qr_code"],
        "manual_entry_key": data["manual_entry_key"]
    }

# 2. Enable 2FA (verifica codice prima di abilitare)
@router.post("/2fa/enable")
async def enable_2fa(
    totp_code: str,
    current_user: User = Depends(get_current_user)
):
    # Decrypt temp secret
    secret = decrypt(current_user.totp_secret_temp)

    # Verifica codice TOTP
    if not totp_service.verify_totp(secret, totp_code):
        raise HTTPException(400, "Invalid TOTP code")

    # Abilita 2FA
    current_user.is_2fa_enabled = True
    current_user.totp_secret = encrypt(secret)
    current_user.totp_secret_temp = None

    # Genera backup codes
    backup_codes = totp_service.generate_backup_codes()
    current_user.backup_codes = [
        hash_password(code) for code in backup_codes
    ]

    await db.commit()

    # Log audit
    await audit_log("2FA_ENABLED", current_user.id)

    return {
        "message": "2FA enabled successfully",
        "backup_codes": backup_codes  # Mostra UNA SOLA VOLTA
    }
```

### 2FA Login Flow

```python
# 1. Login con 2FA
@router.post("/auth/login")
async def login(email: str, password: str):
    user = await authenticate_user(email, password)
    if not user:
        raise HTTPException(401, "Invalid credentials")

    # Check se 2FA abilitato
    if user.is_2fa_enabled:
        # Genera temp token (5 min)
        temp_token = secrets.token_urlsafe(32)
        await redis.setex(
            f"2fa_pending:{temp_token}",
            300,  # 5 minutes
            user.id
        )

        return {
            "requires_2fa": True,
            "temp_token": temp_token
        }

    # No 2FA, return JWT tokens
    return generate_tokens(user)

# 2. Verify 2FA code
@router.post("/auth/verify-2fa")
@rate_limit(max_requests=5, window=300)  # 5 attempts / 5 min
async def verify_2fa(temp_token: str, totp_code: str):
    # Get user_id da temp token
    user_id = await redis.get(f"2fa_pending:{temp_token}")
    if not user_id:
        raise HTTPException(401, "Invalid or expired token")

    user = await user_service.get(user_id)
    secret = decrypt(user.totp_secret)

    # Verifica TOTP
    if not totp_service.verify_totp(secret, totp_code):
        # Log failed attempt
        await audit_log("2FA_VERIFICATION_FAILED", user.id)
        raise HTTPException(400, "Invalid TOTP code")

    # Delete temp token
    await redis.delete(f"2fa_pending:{temp_token}")

    # Generate JWT tokens
    tokens = generate_tokens(user)

    # Log successful 2FA
    await audit_log("2FA_VERIFICATION_SUCCESS", user.id)

    return tokens
```

### Backup Codes

**Usage:**
```python
@router.post("/auth/verify-backup-code")
async def verify_backup_code(temp_token: str, backup_code: str):
    user_id = await redis.get(f"2fa_pending:{temp_token}")
    if not user_id:
        raise HTTPException(401, "Invalid token")

    user = await user_service.get(user_id)

    # Verifica backup code (hashed in DB)
    for idx, hashed_code in enumerate(user.backup_codes):
        if verify_password(backup_code, hashed_code):
            # ✅ Codice valido

            # ❌ Rimuovi codice usato (one-time use)
            user.backup_codes.pop(idx)
            await db.commit()

            # Delete temp token
            await redis.delete(f"2fa_pending:{temp_token}")

            # Log audit
            await audit_log("BACKUP_CODE_USED", user.id, {
                "remaining_codes": len(user.backup_codes)
            })

            # Warning se pochi codici rimasti
            if len(user.backup_codes) < 3:
                await send_email(
                    user.email,
                    "Low backup codes",
                    f"You have only {len(user.backup_codes)} backup codes left"
                )

            return generate_tokens(user)

    raise HTTPException(400, "Invalid backup code")
```

---

## 🛡️ Access Control Lists (ACL)

### ACL Rule Evaluation Engine

```python
class ACLEngine:
    async def evaluate_connection(
        self,
        source_ip: str,
        dest_ip: str,
        protocol: str,
        dest_port: int
    ) -> dict:
        """
        Evalua connessione contro tutte le regole ACL
        Returns: {decision: "ALLOW"|"DENY", matched_rule: Rule|None}
        """
        # Get all enabled rules (ordered by priority ASC)
        rules = await self.get_active_rules()

        for rule in rules:
            # Check time restrictions
            if not self._check_time_window(rule):
                continue

            # Check IP match (CIDR notation)
            if not self._match_ip(source_ip, rule.source_ip):
                continue

            if not self._match_ip(dest_ip, rule.destination_ip):
                continue

            # Check protocol
            if rule.protocol != "ALL" and rule.protocol != protocol:
                continue

            # Check port
            if rule.destination_port != 0 and rule.destination_port != dest_port:
                continue

            # ✅ All conditions matched
            # Increment match counter
            rule.match_count += 1
            await self.db.commit()

            # Log decision
            await audit_log("ACL_RULE_MATCHED", None, {
                "rule_id": rule.id,
                "action": rule.action,
                "source_ip": source_ip,
                "dest_ip": dest_ip
            })

            return {
                "decision": rule.action,
                "matched_rule": rule
            }

        # No rule matched → DEFAULT DENY (Zero Trust)
        await audit_log("ACL_DEFAULT_DENY", None, {
            "source_ip": source_ip,
            "dest_ip": dest_ip,
            "reason": "No matching rule"
        })

        return {
            "decision": "DENY",
            "matched_rule": None
        }

    def _match_ip(self, ip: str, cidr: str) -> bool:
        """Check if IP matches CIDR range"""
        import ipaddress
        return ipaddress.ip_address(ip) in ipaddress.ip_network(cidr)

    def _check_time_window(self, rule: AccessRule) -> bool:
        """Check if current time is within rule's time restrictions"""
        now = datetime.utcnow()

        # Check valid_from / valid_until
        if rule.valid_from and now < rule.valid_from:
            return False
        if rule.valid_until and now > rule.valid_until:
            return False

        # Check day of week
        if rule.days_of_week:
            current_day = now.strftime("%A")
            if current_day not in rule.days_of_week:
                return False

        # Check time range
        if rule.time_range:
            current_time = now.strftime("%H:%M")
            if not (rule.time_range["start"] <= current_time <= rule.time_range["end"]):
                return False

        return True
```

### ACL Best Practices

✅ **DO:**
```json
// 1. Usa priorità per ordine esplicito
[
  {
    "name": "Critical: Block malicious IPs",
    "priority": 1,
    "action": "DENY",
    "source_ip": "198.51.100.0/24"
  },
  {
    "name": "Allow office SSH",
    "priority": 10,
    "action": "ALLOW",
    "source_ip": "203.0.113.0/24",
    "protocol": "TCP",
    "port": 22
  },
  {
    "name": "Default deny all",
    "priority": 100,
    "action": "DENY",
    "source_ip": "0.0.0.0/0"
  }
]

// 2. Usa time restrictions per security
{
  "name": "Business hours only",
  "days_of_week": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
  "time_range": {"start": "08:00", "end": "18:00"}
}

// 3. Testa regole prima di applicare
POST /acl/evaluate
{
  "source_ip": "203.0.113.50",
  "dest_ip": "192.168.1.100",
  "protocol": "TCP",
  "port": 22
}
```

❌ **DON'T:**
```json
// ❌ Non creare regole troppo permissive
{
  "action": "ALLOW",
  "source_ip": "0.0.0.0/0",  // ❌ ANY
  "protocol": "ALL"           // ❌ ANY protocol
}

// ❌ Non dimenticare default DENY
// (il sistema lo fa automaticamente, ma sii esplicito)

// ❌ Non usare stessa priority
{
  "priority": 10,  // ❌ Conflitto con altra regola
  "action": "ALLOW"
}
```

---

## 🌐 Network Security

### TLS/SSL Configuration

**Nginx SSL Best Practices:**
```nginx
server {
    listen 443 ssl http2;
    server_name orizon.syneto.net;

    # Certificati SSL (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/orizon.syneto.net/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/orizon.syneto.net/privkey.pem;

    # SSL Protocols (solo TLS 1.2+)
    ssl_protocols TLSv1.2 TLSv1.3;

    # Cipher suites (strong ciphers only)
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers on;

    # HSTS (Strict Transport Security)
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;

    # OCSP Stapling
    ssl_stapling on;
    ssl_stapling_verify on;
    ssl_trusted_certificate /etc/letsencrypt/live/orizon.syneto.net/chain.pem;
    resolver 8.8.8.8 8.8.4.4 valid=300s;

    # SSL Session
    ssl_session_cache shared:SSL:50m;
    ssl_session_timeout 1d;
    ssl_session_tickets off;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # CSP (Content Security Policy)
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';" always;

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### SSH Tunnel Security

```python
# backend/app/tunnel/ssh_server.py
import asyncssh

class SecureSSHServer(asyncssh.SSHServer):
    def connection_made(self, conn):
        self.conn = conn

    def connection_lost(self, exc):
        if exc:
            logger.error(f"SSH connection error: {exc}")

    def password_auth_supported(self):
        return False  # ❌ Disable password auth

    def public_key_auth_supported(self):
        return True  # ✅ Only key-based auth

    async def validate_public_key(self, username, key):
        # Validate SSH key against database
        node = await get_node_by_username(username)
        if not node:
            return False

        authorized_key = node.ssh_public_key
        return key == authorized_key

async def start_ssh_server():
    await asyncssh.create_server(
        SecureSSHServer,
        '',
        2222,
        server_host_keys=['/etc/ssh/ssh_host_rsa_key'],
        authorized_client_keys='/etc/ssh/authorized_keys',

        # Security options
        kex_algs=[
            'curve25519-sha256',
            'diffie-hellman-group-exchange-sha256'
        ],
        encryption_algs=[
            'aes256-gcm@openssh.com',
            'chacha20-poly1305@openssh.com'
        ],
        mac_algs=[
            'hmac-sha2-256-etm@openssh.com',
            'hmac-sha2-512-etm@openssh.com'
        ],
        compression_algs=['none'],

        # Rate limiting
        login_timeout=30,
        max_auth_tries=3
    )
```

### Firewall Configuration (UFW)

```bash
#!/bin/bash
# Production firewall setup

# Reset firewall
sudo ufw --force reset

# Default policies
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH (change default port)
sudo ufw allow 2200/tcp comment 'SSH (custom port)'

# Allow HTTP/HTTPS
sudo ufw allow 80/tcp comment 'HTTP'
sudo ufw allow 443/tcp comment 'HTTPS'

# Allow tunnel ports
sudo ufw allow 2222/tcp comment 'SSH Tunnels'
sudo ufw allow 8443/tcp comment 'HTTPS Tunnels'

# Rate limiting SSH (prevent brute force)
sudo ufw limit 2200/tcp

# Allow from specific IPs only (office)
sudo ufw allow from 203.0.113.0/24 to any port 22 comment 'Office SSH'

# Deny from known malicious ranges
sudo ufw deny from 198.51.100.0/24 comment 'Blocked range'

# Enable logging
sudo ufw logging on

# Enable firewall
sudo ufw --force enable

# Show status
sudo ufw status verbose
```

---

## 💾 Data Protection

### Encryption at Rest

**PostgreSQL Data Encryption (opzionale):**
```bash
# 1. Setup LUKS encrypted volume
sudo cryptsetup luksFormat /dev/sdb1
sudo cryptsetup luksOpen /dev/sdb1 postgres_encrypted

# 2. Create filesystem
sudo mkfs.ext4 /dev/mapper/postgres_encrypted

# 3. Mount
sudo mount /dev/mapper/postgres_encrypted /var/lib/postgresql/data

# 4. Configure auto-mount in /etc/crypttab e /etc/fstab
```

**Application-Level Encryption (per campi sensibili):**
```python
from cryptography.fernet import Fernet
import os

# Generate encryption key (store in secure vault!)
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
cipher = Fernet(ENCRYPTION_KEY)

def encrypt_field(plaintext: str) -> str:
    """Encrypt sensitive field"""
    return cipher.encrypt(plaintext.encode()).decode()

def decrypt_field(ciphertext: str) -> str:
    """Decrypt sensitive field"""
    return cipher.decrypt(ciphertext.encode()).decode()

# Usage in models
class User(Base):
    __tablename__ = "users"

    id = Column(UUID, primary_key=True)
    email = Column(String)  # Plain
    totp_secret = Column(String)  # ✅ Encrypted

    @property
    def decrypted_totp_secret(self):
        if self.totp_secret:
            return decrypt_field(self.totp_secret)
        return None

    @decrypted_totp_secret.setter
    def decrypted_totp_secret(self, value):
        if value:
            self.totp_secret = encrypt_field(value)
```

### Secure Key Management

**DO NOT hardcode secrets:**
```python
# ❌ WRONG
JWT_SECRET = "my-secret-key"
DATABASE_PASSWORD = "password123"

# ✅ CORRECT
import os
from pathlib import Path

JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    raise ValueError("JWT_SECRET environment variable required")

# Oppure usa secrets manager (AWS Secrets Manager, HashiCorp Vault)
from vault import VaultClient

vault = VaultClient(url="https://vault.internal")
JWT_SECRET = vault.get_secret("orizon/jwt_secret")
```

### Backup Encryption

```bash
#!/bin/bash
# Encrypted backup script

BACKUP_DIR="/backup/orizon"
DATE=$(date +%Y%m%d_%H%M%S)
GPG_KEY="admin@orizon.syneto.net"

# Backup PostgreSQL
docker exec postgres pg_dump -U orizon orizon_production | \
  gzip | \
  gpg --encrypt --recipient $GPG_KEY \
  > $BACKUP_DIR/postgres_$DATE.sql.gz.gpg

# Backup MongoDB
docker exec mongodb mongodump --archive | \
  gzip | \
  gpg --encrypt --recipient $GPG_KEY \
  > $BACKUP_DIR/mongodb_$DATE.archive.gz.gpg

echo "Encrypted backups created"
```

---

## 📜 Audit e Compliance

### GDPR Compliance

**Right to be Forgotten:**
```python
@router.delete("/users/{user_id}/gdpr-delete")
@require_permission("gdpr:delete")
async def gdpr_delete_user(user_id: str):
    """
    GDPR Article 17: Right to erasure
    """
    # 1. Delete user data
    user = await user_service.get(user_id)
    await user_service.delete(user_id)

    # 2. Anonymize audit logs (keep for compliance)
    await db.execute(
        update(AuditLog)
        .where(AuditLog.user_id == user_id)
        .values(
            user_email="deleted@anonymous.local",
            ip_address="0.0.0.0",
            user_agent="deleted"
        )
    )

    # 3. Delete nodes e tunnels
    await node_service.delete_all_by_user(user_id)
    await tunnel_service.close_all_by_user(user_id)

    # 4. Log deletion
    await audit_log("GDPR_USER_DELETED", user_id, {
        "email": user.email,
        "deletion_reason": "user_request"
    })

    return {"message": "User data deleted (GDPR compliant)"}
```

**Data Export (GDPR Article 20):**
```python
@router.get("/users/{user_id}/gdpr-export")
async def gdpr_export_user_data(user_id: str):
    """
    GDPR Article 20: Right to data portability
    """
    user = await user_service.get(user_id)
    nodes = await node_service.list_by_user(user_id)
    tunnels = await tunnel_service.list_by_user(user_id)
    audit_logs = await audit_service.list_by_user(user_id)

    data = {
        "export_date": datetime.utcnow().isoformat(),
        "user": {
            "email": user.email,
            "role": user.role,
            "created_at": user.created_at.isoformat()
        },
        "nodes": [
            {
                "name": node.name,
                "type": node.type,
                "created_at": node.created_at.isoformat()
            }
            for node in nodes
        ],
        "tunnels": [
            {
                "type": tunnel.type,
                "created_at": tunnel.created_at.isoformat()
            }
            for tunnel in tunnels
        ],
        "audit_logs": [
            {
                "action": log.action,
                "timestamp": log.timestamp.isoformat()
            }
            for log in audit_logs
        ]
    }

    # Return as downloadable JSON
    return Response(
        content=json.dumps(data, indent=2),
        media_type="application/json",
        headers={
            "Content-Disposition": f"attachment; filename=orizon_data_{user_id}.json"
        }
    )
```

### NIS2 Directive Compliance

**Incident Reporting (24h/72h):**
```python
class IncidentReporter:
    async def report_security_incident(
        self,
        severity: str,
        description: str,
        affected_systems: list
    ):
        """
        NIS2: Report security incidents
        - Significant: 24 hours
        - Major: 72 hours
        """
        incident = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow(),
            "severity": severity,
            "description": description,
            "affected_systems": affected_systems,
            "reporter": "Orizon ZTC Security Team"
        }

        # Log in audit system
        await audit_log("SECURITY_INCIDENT", None, incident)

        # Notify authorities if required
        if severity in ["major", "critical"]:
            await self.notify_csirt(incident)

        # Notify affected users
        await self.notify_users(affected_systems)

        return incident
```

---

## 🔒 Security Hardening

### Production Checklist

```bash
# ✅ Security Hardening Checklist

# 1. OS Updates
sudo apt update && sudo apt upgrade -y
sudo apt autoremove -y

# 2. Disable root SSH
sudo nano /etc/ssh/sshd_config
# PermitRootLogin no
sudo systemctl restart sshd

# 3. Setup fail2ban
sudo apt install fail2ban
sudo systemctl enable fail2ban

# 4. Automatic security updates
sudo apt install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades

# 5. Secure shared memory
sudo nano /etc/fstab
# tmpfs /run/shm tmpfs defaults,noexec,nosuid 0 0

# 6. Disable IPv6 (se non usato)
sudo nano /etc/sysctl.conf
# net.ipv6.conf.all.disable_ipv6 = 1

# 7. Kernel hardening
sudo nano /etc/sysctl.d/99-security.conf
```

**99-security.conf:**
```conf
# IP Forwarding
net.ipv4.ip_forward = 1

# SYN flood protection
net.ipv4.tcp_syncookies = 1
net.ipv4.tcp_max_syn_backlog = 2048

# Ignore ICMP redirects
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0

# Ignore source packet routing
net.ipv4.conf.all.accept_source_route = 0

# Log Martians
net.ipv4.conf.all.log_martians = 1

# Protect against tcp time-wait assassination
net.ipv4.tcp_rfc1337 = 1
```

---

## 🚨 Incident Response

### Security Incident Playbook

**1. Detection:**
```python
# Monitora metriche anomale
if failed_logins_last_hour > 100:
    alert("Possible brute force attack")

if acl_denies_last_hour > 1000:
    alert("Possible DDoS attack")

if unauthorized_access_attempts > 10:
    alert("Possible intrusion attempt")
```

**2. Containment:**
```bash
# Block malicious IP
sudo ufw deny from 198.51.100.50

# Disable compromised user
psql -U orizon -d orizon_db -c "UPDATE users SET is_active=false WHERE email='compromised@example.com';"

# Close all tunnels for compromised node
curl -X DELETE http://localhost:8000/api/v1/nodes/{node_id}/tunnels-all
```

**3. Investigation:**
```bash
# Query audit logs
mongo orizon_db --eval "db.audit_logs.find({ip_address: '198.51.100.50'}).pretty()"

# Check access patterns
psql -U orizon -d orizon_db -c "SELECT * FROM audit_logs WHERE action='LOGIN_FAILED' AND timestamp > NOW() - INTERVAL '24 hours';"
```

**4. Recovery:**
```bash
# Restore from backup
gunzip < /backup/orizon/postgres_20250107.sql.gz | psql -U orizon orizon_db

# Reset compromised passwords
# Force password reset per utenti affetti
```

**5. Post-Incident:**
- Document incident in audit log
- Update security policies
- Patch vulnerabilities
- Notify affected users (GDPR)
- Report to authorities (NIS2 se richiesto)

---

## ✅ Security Checklist

### Pre-Production Security Audit

- [ ] **Authentication**
  - [ ] JWT secrets > 64 chars random
  - [ ] Token rotation enabled (30 days)
  - [ ] 2FA enforced per admin+ ruoli
  - [ ] Password policy enforced (12+ chars)
  - [ ] Account lockout enabled (5 attempts)

- [ ] **Authorization**
  - [ ] RBAC hierarchy verified
  - [ ] Permission checks su tutti gli endpoint
  - [ ] Resource ownership checks
  - [ ] ACL default DENY verified

- [ ] **Network Security**
  - [ ] TLS 1.2+ only
  - [ ] Strong cipher suites
  - [ ] HSTS enabled
  - [ ] Firewall configured e testato
  - [ ] SSH key-based auth only
  - [ ] Non-standard ports per servizi

- [ ] **Data Protection**
  - [ ] Argon2 password hashing
  - [ ] Sensitive fields encrypted
  - [ ] Backup encrypted
  - [ ] Encryption keys in vault

- [ ] **Audit & Compliance**
  - [ ] Audit logging abilitato
  - [ ] GDPR data export funzionante
  - [ ] GDPR deletion testata
  - [ ] 90-day retention configurata
  - [ ] SIEM export testato

- [ ] **Infrastructure**
  - [ ] OS fully patched
  - [ ] Automatic security updates
  - [ ] Fail2ban configured
  - [ ] Kernel hardening applied
  - [ ] Container security scanning

- [ ] **Monitoring**
  - [ ] Security alerts configurati
  - [ ] Failed login monitoring
  - [ ] Rate limit violations alerts
  - [ ] Intrusion detection (opzionale)

- [ ] **Incident Response**
  - [ ] Incident playbook documented
  - [ ] Team contacts updated
  - [ ] Backup/restore tested
  - [ ] Disaster recovery plan

---

**Documento maintained by:** Marco Lorenzi @ Syneto/Orizon Security
**Last Security Audit:** Gennaio 2025
**Next Review:** Aprile 2025
**Contact:** security@orizon.syneto.net
