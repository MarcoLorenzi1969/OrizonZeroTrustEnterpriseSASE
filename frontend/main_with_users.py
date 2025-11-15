from fastapi import FastAPI, HTTPException, status, Request, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text
from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext
import json
import logging
import sys
import uuid
from typing import Optional, List

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("orizon_backend")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=30)
    to_encode.update({"exp": expire})
    token = jwt.encode(to_encode, "secret-key-change-in-production", algorithm="HS256")
    return token

def decode_token(token: str):
    try:
        payload = jwt.decode(token, "secret-key-change-in-production", algorithms=["HS256"])
        return payload
    except JWTError:
        return None

DATABASE_URL = "postgresql+asyncpg://orizon:orizon_secure_2024@localhost:5432/orizon_ztc"
engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

app = FastAPI(title="Orizon Zero Trust Connect - User Management")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic Models
class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    role: str = "user"

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None

class PasswordChange(BaseModel):
    new_password: str

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: Optional[str] = None

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

# Authentication dependency
async def get_current_user(authorization: str = Header(None), db: AsyncSession = Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = authorization.replace("Bearer ", "")
    payload = decode_token(token)

    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    email = payload.get("sub")
    if not email:
        raise HTTPException(status_code=401, detail="Invalid token")

    result = await db.execute(
        text("SELECT id, email, full_name, role, is_active FROM users WHERE email = :email"),
        {"email": email}
    )
    user = result.first()

    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    return user

# Admin only dependency
async def require_admin(current_user = Depends(get_current_user)):
    if current_user.role not in ["admin", "superuser"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

# ============= AUTH ENDPOINTS =============

@app.post("/api/v1/auth/login")
async def login(request: Request, db: AsyncSession = Depends(get_db)):
    logger.info("=== LOGIN REQUEST RECEIVED ===")

    email = None
    password = None
    content_type = request.headers.get("content-type", "")

    if "application/json" in content_type:
        body = await request.body()
        json_data = json.loads(body)
        email = json_data.get("email")
        password = json_data.get("password")
    elif "application/x-www-form-urlencoded" in content_type:
        form = await request.form()
        email = form.get("username")
        password = form.get("password")

    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password required")

    result = await db.execute(
        text("SELECT id, email, full_name, hashed_password, is_active, role FROM users WHERE email = :email"),
        {"email": email}
    )
    user = result.first()

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")

    if not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")

    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    access_token = create_access_token(data={"sub": user.email, "role": user.role})

    logger.info(f"=== LOGIN SUCCESS for {email} ===")

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "refresh_token": "dummy-refresh-token",
        "user": {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "is_active": user.is_active
        }
    }

@app.get("/api/v1/auth/me")
async def get_me(current_user = Depends(get_current_user)):
    """Get current user info"""
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "is_active": current_user.is_active
    }

# ============= USER MANAGEMENT ENDPOINTS =============

@app.get("/api/v1/users")
async def list_users(
    current_user = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """List all users (admin only)"""
    logger.info(f"[list_users] Admin {current_user.email} listing users")

    result = await db.execute(
        text("""
            SELECT id, email, full_name, role, is_active, created_at
            FROM users
            ORDER BY created_at DESC
        """)
    )
    users = result.fetchall()

    return {
        "users": [
            {
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat() if user.created_at else None
            }
            for user in users
        ],
        "total": len(users)
    }

@app.post("/api/v1/users")
async def create_user(
    user_data: UserCreate,
    current_user = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Create new user (admin only)"""
    logger.info(f"[create_user] Admin {current_user.email} creating user {user_data.email}")

    # Check if user already exists
    result = await db.execute(
        text("SELECT id FROM users WHERE email = :email"),
        {"email": user_data.email}
    )
    if result.first():
        raise HTTPException(status_code=400, detail="User with this email already exists")

    # Validate role
    if user_data.role not in ["user", "admin", "superuser"]:
        raise HTTPException(status_code=400, detail="Invalid role")

    # Hash password
    hashed_password = hash_password(user_data.password)
    user_id = str(uuid.uuid4())

    # Create user
    await db.execute(
        text("""
            INSERT INTO users (id, email, full_name, hashed_password, role, is_active, created_at)
            VALUES (:id, :email, :full_name, :hashed_password, :role, true, :created_at)
        """),
        {
            "id": user_id,
            "email": user_data.email,
            "full_name": user_data.full_name,
            "hashed_password": hashed_password,
            "role": user_data.role,
            "created_at": datetime.utcnow()
        }
    )
    await db.commit()

    logger.info(f"[create_user] User {user_data.email} created successfully")

    return {
        "id": user_id,
        "email": user_data.email,
        "full_name": user_data.full_name,
        "role": user_data.role,
        "is_active": True,
        "message": "User created successfully"
    }

@app.get("/api/v1/users/{user_id}")
async def get_user(
    user_id: str,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user details"""
    # Users can see their own profile, admins can see all
    if str(current_user.id) != user_id and current_user.role not in ["admin", "superuser"]:
        raise HTTPException(status_code=403, detail="Access denied")

    result = await db.execute(
        text("SELECT id, email, full_name, role, is_active, created_at FROM users WHERE id = :id"),
        {"id": user_id}
    )
    user = result.first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat() if user.created_at else None
    }

@app.put("/api/v1/users/{user_id}")
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    current_user = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Update user (admin only)"""
    logger.info(f"[update_user] Admin {current_user.email} updating user {user_id}")

    # Check if user exists
    result = await db.execute(
        text("SELECT id FROM users WHERE id = :id"),
        {"id": user_id}
    )
    if not result.first():
        raise HTTPException(status_code=404, detail="User not found")

    # Build update query
    updates = []
    params = {"id": user_id}

    if user_data.email:
        updates.append("email = :email")
        params["email"] = user_data.email
    if user_data.full_name:
        updates.append("full_name = :full_name")
        params["full_name"] = user_data.full_name
    if user_data.role:
        if user_data.role not in ["user", "admin", "superuser"]:
            raise HTTPException(status_code=400, detail="Invalid role")
        updates.append("role = :role")
        params["role"] = user_data.role
    if user_data.is_active is not None:
        updates.append("is_active = :is_active")
        params["is_active"] = user_data.is_active

    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")

    query = f"UPDATE users SET {', '.join(updates)} WHERE id = :id"
    await db.execute(text(query), params)
    await db.commit()

    logger.info(f"[update_user] User {user_id} updated successfully")

    return {"message": "User updated successfully"}

@app.delete("/api/v1/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Delete user (admin only)"""
    logger.info(f"[delete_user] Admin {current_user.email} deleting user {user_id}")

    # Prevent self-deletion
    if str(current_user.id) == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")

    # Check if user exists
    result = await db.execute(
        text("SELECT id FROM users WHERE id = :id"),
        {"id": user_id}
    )
    if not result.first():
        raise HTTPException(status_code=404, detail="User not found")

    # Delete user
    await db.execute(
        text("DELETE FROM users WHERE id = :id"),
        {"id": user_id}
    )
    await db.commit()

    logger.info(f"[delete_user] User {user_id} deleted successfully")

    return {"message": "User deleted successfully"}

@app.put("/api/v1/users/{user_id}/password")
async def change_password(
    user_id: str,
    password_data: PasswordChange,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Change user password"""
    # Users can change their own password, admins can change any
    if str(current_user.id) != user_id and current_user.role not in ["admin", "superuser"]:
        raise HTTPException(status_code=403, detail="Access denied")

    logger.info(f"[change_password] Changing password for user {user_id}")

    # Validate password length
    if len(password_data.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    # Hash new password
    hashed_password = hash_password(password_data.new_password)

    # Update password
    await db.execute(
        text("UPDATE users SET hashed_password = :hashed_password WHERE id = :id"),
        {"id": user_id, "hashed_password": hashed_password}
    )
    await db.commit()

    logger.info(f"[change_password] Password changed for user {user_id}")

    return {"message": "Password changed successfully"}

# ============= DASHBOARD ENDPOINTS =============

@app.get("/api/v1/nodes")
async def list_nodes(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all nodes with their status"""
    logger.info(f"[list_nodes] User {current_user.email} listing nodes")

    # Stub nodes (for demo purposes)
    stub_nodes = [
        {
            "id": "node-001",
            "name": "web-server-01",
            "status": "online",
            "ip_address": "10.0.1.10",
            "last_seen": datetime.utcnow().isoformat(),
            "location": "datacenter-eu-west",
        },
        {
            "id": "node-002",
            "name": "db-server-01",
            "status": "online",
            "ip_address": "10.0.1.20",
            "last_seen": datetime.utcnow().isoformat(),
            "location": "datacenter-eu-west",
        },
        {
            "id": "node-003",
            "name": "app-server-01",
            "status": "offline",
            "ip_address": "10.0.1.30",
            "last_seen": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
            "location": "datacenter-us-east",
        },
    ]

    # Add dynamically registered nodes from QR code
    dynamic_nodes = list(registered_nodes_store.values())

    # Combine all nodes
    all_nodes = stub_nodes + dynamic_nodes

    return {
        "items": all_nodes,
        "total": len(all_nodes),
        "online": sum(1 for n in all_nodes if n["status"] == "online"),
        "offline": sum(1 for n in all_nodes if n["status"] == "offline"),
    }

@app.get("/api/v1/dashboard/stats")
async def get_dashboard_stats(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get dashboard statistics"""
    logger.info(f"[get_dashboard_stats] User {current_user.email} fetching dashboard stats")

    try:
        # Get real user count from database
        result = await db.execute(text("SELECT COUNT(*) as count FROM users WHERE is_active = true"))
        active_users = result.first().count
    except Exception as e:
        logger.error(f"[get_dashboard_stats] Error counting users: {e}")
        active_users = 0

    # TODO: Replace with real tunnel/connection data from database
    # For now, return stub data for testing
    return {
        "active_tunnels": 5,
        "total_bandwidth_mbps": 245.7,
        "active_connections": 12,
        "active_users": active_users,
        "uptime_hours": 168,
        "timestamp": datetime.utcnow().isoformat(),
    }

# ============= NODE MANAGEMENT ENDPOINTS =============

# In-memory storage for pending node registrations
# TODO: Move to database for production
pending_node_tokens = {}
registered_nodes_store = {}

@app.post("/api/v1/nodes/generate-token")
async def generate_node_token(
    request: Request,
    current_user = Depends(get_current_user)
):
    """Generate registration token for new node with QR code"""
    logger.info(f"[generate_node_token] User {current_user.email} generating node token")

    body = await request.json()
    node_name = body.get("name")
    protocols = body.get("protocols", [])

    if not node_name:
        raise HTTPException(status_code=400, detail="Node name is required")

    if not protocols:
        raise HTTPException(status_code=400, detail="At least one protocol must be selected")

    # Generate unique token
    token = str(uuid.uuid4())

    # Store token data temporarily (valid for 24 hours)
    pending_node_tokens[token] = {
        "name": node_name,
        "protocols": protocols,
        "created_by": current_user.email,
        "created_at": datetime.utcnow().isoformat(),
        "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat()
    }

    # Build registration URL
    registration_url = f"http://46.101.189.126/api/v1/nodes/register?token={token}"

    logger.info(f"[generate_node_token] Token generated for node '{node_name}' with protocols: {protocols}")

    return {
        "token": token,
        "registration_url": registration_url,
        "node_name": node_name,
        "protocols": protocols,
        "expires_in_hours": 24
    }

@app.post("/api/v1/nodes/register")
async def register_node_from_qr(
    token: str,
    request: Request
):
    """Register node using QR code token (called by agent app)"""
    logger.info(f"[register_node_from_qr] Registration attempt with token: {token[:20]}...")

    # Verify token exists
    if token not in pending_node_tokens:
        logger.error(f"[register_node_from_qr] Invalid or expired token")
        raise HTTPException(status_code=400, detail="Invalid or expired registration token")

    token_data = pending_node_tokens[token]

    # Check if token expired
    expires_at = datetime.fromisoformat(token_data["expires_at"])
    if datetime.utcnow() > expires_at:
        del pending_node_tokens[token]
        raise HTTPException(status_code=400, detail="Registration token has expired")

    # Get agent info from request
    body = await request.json()
    agent_ip = body.get("ip_address") or request.client.host
    agent_hostname = body.get("hostname", "unknown")

    # Create node ID
    node_id = str(uuid.uuid4())

    # Register node
    registered_node = {
        "id": node_id,
        "name": token_data["name"],
        "ip_address": agent_ip,
        "hostname": agent_hostname,
        "status": "online",
        "protocols": token_data["protocols"],
        "location": body.get("location", "unknown"),
        "registered_at": datetime.utcnow().isoformat(),
        "last_seen": datetime.utcnow().isoformat(),
        "created_by": token_data["created_by"]
    }

    # Store registered node
    registered_nodes_store[node_id] = registered_node

    # Remove used token
    del pending_node_tokens[token]

    logger.info(f"[register_node_from_qr] Node '{token_data['name']}' registered successfully: {node_id}")

    return {
        "status": "success",
        "message": "Node registered successfully",
        "node": registered_node,
        "tunnels_to_create": [
            {
                "protocol": protocol,
                "local_port": get_protocol_port(protocol),
                "remote_endpoint": f"http://46.101.189.126/tunnel/{node_id}/{protocol}"
            }
            for protocol in token_data["protocols"]
        ]
    }

@app.delete("/api/v1/nodes/{node_id}")
async def delete_node(
    node_id: str,
    current_user = Depends(require_admin)
):
    """Delete node (admin only)"""
    logger.info(f"[delete_node] Admin {current_user.email} deleting node {node_id}")

    # Check if node exists in registered_nodes_store
    if node_id in registered_nodes_store:
        del registered_nodes_store[node_id]
        logger.info(f"[delete_node] Node {node_id} deleted successfully")
        return {"message": "Node deleted successfully"}

    # If not found in store, it might be a stub node - just return success
    logger.warn(f"[delete_node] Node {node_id} not found in registered nodes, might be stub data")
    return {"message": "Node deleted successfully"}

def get_protocol_port(protocol: str) -> int:
    """Get default port for protocol"""
    ports = {
        "ssh": 22,
        "https": 443,
        "http": 80,
        "vpn": 1194,
        "rdp": 3389
    }
    return ports.get(protocol.lower(), 0)

# ============= TUNNELS MANAGEMENT =============

# In-memory storage for tunnels
# TODO: Move to database for production
tunnels_store = {}

@app.get("/api/v1/tunnels")
async def list_tunnels(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all active tunnels"""
    logger.info(f"[list_tunnels] User {current_user.email} listing tunnels")

    # Generate stub tunnels based on registered nodes
    stub_tunnels = []

    # Add tunnels for stub nodes
    stub_nodes = ["node-001", "node-002"]
    for idx, node_id in enumerate(stub_nodes):
        tunnel_id = f"tunnel-{idx+1:03d}"
        stub_tunnels.append({
            "id": tunnel_id,
            "node_id": node_id,
            "node_name": f"web-server-{idx+1:02d}" if idx == 0 else f"db-server-{idx+1:02d}",
            "protocol": "ssh" if idx == 0 else "https",
            "local_port": 22 if idx == 0 else 443,
            "remote_port": 50000 + idx,
            "status": "active",
            "bandwidth_mbps": 12.5 + (idx * 5.3),
            "created_at": (datetime.utcnow() - timedelta(hours=24-idx)).isoformat(),
            "last_activity": datetime.utcnow().isoformat(),
        })

    # Add tunnels from dynamically registered nodes
    dynamic_tunnels = list(tunnels_store.values())

    all_tunnels = stub_tunnels + dynamic_tunnels

    return {
        "tunnels": all_tunnels,
        "total": len(all_tunnels),
        "active": sum(1 for t in all_tunnels if t["status"] == "active"),
        "inactive": sum(1 for t in all_tunnels if t["status"] != "active"),
    }

@app.post("/api/v1/tunnels")
async def create_tunnel(
    request: Request,
    current_user = Depends(get_current_user)
):
    """Create a new tunnel"""
    logger.info(f"[create_tunnel] User {current_user.email} creating tunnel")

    body = await request.json()
    node_id = body.get("node_id")
    protocol = body.get("protocol")
    local_port = body.get("local_port")

    if not all([node_id, protocol, local_port]):
        raise HTTPException(status_code=400, detail="node_id, protocol, and local_port are required")

    # Generate tunnel ID
    tunnel_id = str(uuid.uuid4())

    # Create tunnel
    tunnel = {
        "id": tunnel_id,
        "node_id": node_id,
        "protocol": protocol,
        "local_port": local_port,
        "remote_port": 50000 + len(tunnels_store),
        "status": "active",
        "bandwidth_mbps": 0.0,
        "created_at": datetime.utcnow().isoformat(),
        "last_activity": datetime.utcnow().isoformat(),
        "created_by": current_user.email
    }

    tunnels_store[tunnel_id] = tunnel

    logger.info(f"[create_tunnel] Tunnel created: {tunnel_id} for node {node_id}")

    return tunnel

@app.delete("/api/v1/tunnels/{tunnel_id}")
async def close_tunnel(
    tunnel_id: str,
    current_user = Depends(get_current_user)
):
    """Close/delete a tunnel"""
    logger.info(f"[close_tunnel] User {current_user.email} closing tunnel {tunnel_id}")

    if tunnel_id in tunnels_store:
        del tunnels_store[tunnel_id]
        logger.info(f"[close_tunnel] Tunnel {tunnel_id} closed successfully")
        return {"message": "Tunnel closed successfully"}

    # Stub tunnels can't be deleted
    if tunnel_id.startswith("tunnel-"):
        raise HTTPException(status_code=400, detail="Cannot delete demo tunnels")

    raise HTTPException(status_code=404, detail="Tunnel not found")

@app.get("/api/v1/tunnels/health/all")
async def get_tunnels_health(current_user = Depends(get_current_user)):
    """Get health status of all tunnels"""
    logger.info(f"[get_tunnels_health] User {current_user.email} checking tunnels health")

    all_tunnels = list(tunnels_store.values())

    return {
        "total_tunnels": len(all_tunnels),
        "healthy": sum(1 for t in all_tunnels if t["status"] == "active"),
        "unhealthy": sum(1 for t in all_tunnels if t["status"] != "active"),
        "average_bandwidth": sum(t["bandwidth_mbps"] for t in all_tunnels) / len(all_tunnels) if all_tunnels else 0,
        "timestamp": datetime.utcnow().isoformat()
    }

# ============= ACL MANAGEMENT =============

# In-memory storage for ACL rules
# TODO: Move to database for production
acl_rules_store = {}

@app.get("/api/v1/acl")
async def list_acl_rules(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all ACL rules"""
    logger.info(f"[list_acl_rules] User {current_user.email} listing ACL rules")

    # Stub ACL rules for demo
    stub_rules = [
        {
            "id": "acl-001",
            "name": "Allow Admin SSH",
            "source": "10.0.0.0/24",
            "destination": "10.0.1.10",
            "protocol": "tcp",
            "port": 22,
            "action": "allow",
            "priority": 100,
            "enabled": True,
            "created_at": (datetime.utcnow() - timedelta(days=7)).isoformat(),
        },
        {
            "id": "acl-002",
            "name": "Block External HTTP",
            "source": "0.0.0.0/0",
            "destination": "10.0.1.0/24",
            "protocol": "tcp",
            "port": 80,
            "action": "deny",
            "priority": 200,
            "enabled": True,
            "created_at": (datetime.utcnow() - timedelta(days=5)).isoformat(),
        },
        {
            "id": "acl-003",
            "name": "Allow HTTPS Traffic",
            "source": "0.0.0.0/0",
            "destination": "10.0.1.10",
            "protocol": "tcp",
            "port": 443,
            "action": "allow",
            "priority": 150,
            "enabled": True,
            "created_at": (datetime.utcnow() - timedelta(days=3)).isoformat(),
        },
    ]

    # Add dynamic rules
    dynamic_rules = list(acl_rules_store.values())
    all_rules = stub_rules + dynamic_rules

    return {
        "rules": all_rules,
        "total": len(all_rules),
        "enabled": sum(1 for r in all_rules if r["enabled"]),
        "disabled": sum(1 for r in all_rules if not r["enabled"]),
    }

@app.get("/api/v1/acl/node/{node_id}")
async def get_node_acl_rules(
    node_id: str,
    current_user = Depends(get_current_user)
):
    """Get ACL rules for a specific node"""
    logger.info(f"[get_node_acl_rules] User {current_user.email} getting ACL rules for node {node_id}")

    # Return filtered stub rules for the node
    stub_rules = [
        {
            "id": "acl-001",
            "name": "Allow Admin SSH",
            "source": "10.0.0.0/24",
            "destination": "10.0.1.10",
            "protocol": "tcp",
            "port": 22,
            "action": "allow",
            "priority": 100,
            "enabled": True,
        }
    ]

    return {"rules": stub_rules, "node_id": node_id}

@app.post("/api/v1/acl")
async def create_acl_rule(
    request: Request,
    current_user = Depends(require_admin)
):
    """Create a new ACL rule (admin only)"""
    logger.info(f"[create_acl_rule] Admin {current_user.email} creating ACL rule")

    body = await request.json()
    rule_name = body.get("name")
    source = body.get("source")
    destination = body.get("destination")
    protocol = body.get("protocol")
    port = body.get("port")
    action = body.get("action")

    if not all([rule_name, source, destination, protocol, action]):
        raise HTTPException(status_code=400, detail="Missing required fields")

    # Generate rule ID
    rule_id = str(uuid.uuid4())

    # Create ACL rule
    rule = {
        "id": rule_id,
        "name": rule_name,
        "source": source,
        "destination": destination,
        "protocol": protocol,
        "port": port or 0,
        "action": action,
        "priority": body.get("priority", 500),
        "enabled": True,
        "created_at": datetime.utcnow().isoformat(),
        "created_by": current_user.email
    }

    acl_rules_store[rule_id] = rule

    logger.info(f"[create_acl_rule] ACL rule created: {rule_id}")

    return rule

@app.delete("/api/v1/acl/{rule_id}")
async def delete_acl_rule(
    rule_id: str,
    current_user = Depends(require_admin)
):
    """Delete an ACL rule (admin only)"""
    logger.info(f"[delete_acl_rule] Admin {current_user.email} deleting ACL rule {rule_id}")

    if rule_id in acl_rules_store:
        del acl_rules_store[rule_id]
        logger.info(f"[delete_acl_rule] ACL rule {rule_id} deleted successfully")
        return {"message": "ACL rule deleted successfully"}

    # Stub rules can't be deleted
    if rule_id.startswith("acl-"):
        raise HTTPException(status_code=400, detail="Cannot delete demo ACL rules")

    raise HTTPException(status_code=404, detail="ACL rule not found")

@app.post("/api/v1/acl/{rule_id}/enable")
async def enable_acl_rule(
    rule_id: str,
    current_user = Depends(require_admin)
):
    """Enable an ACL rule (admin only)"""
    logger.info(f"[enable_acl_rule] Admin {current_user.email} enabling ACL rule {rule_id}")

    if rule_id in acl_rules_store:
        acl_rules_store[rule_id]["enabled"] = True
        return {"message": "ACL rule enabled", "rule": acl_rules_store[rule_id]}

    raise HTTPException(status_code=404, detail="ACL rule not found")

@app.post("/api/v1/acl/{rule_id}/disable")
async def disable_acl_rule(
    rule_id: str,
    current_user = Depends(require_admin)
):
    """Disable an ACL rule (admin only)"""
    logger.info(f"[disable_acl_rule] Admin {current_user.email} disabling ACL rule {rule_id}")

    if rule_id in acl_rules_store:
        acl_rules_store[rule_id]["enabled"] = False
        return {"message": "ACL rule disabled", "rule": acl_rules_store[rule_id]}

    raise HTTPException(status_code=404, detail="ACL rule not found")

# ============= AUDIT LOGS =============

# In-memory storage for audit logs
# TODO: Move to database for production
audit_logs_store = []

def log_audit_event(action: str, user_email: str, resource_type: str, resource_id: str, details: dict = None):
    """Log an audit event"""
    event = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.utcnow().isoformat(),
        "action": action,
        "user": user_email,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "details": details or {},
        "ip_address": "unknown",
        "user_agent": "unknown"
    }
    audit_logs_store.append(event)
    # Keep only last 1000 logs in memory
    if len(audit_logs_store) > 1000:
        audit_logs_store.pop(0)
    return event

@app.get("/api/v1/audit")
async def get_audit_logs(
    current_user = Depends(require_admin),
    skip: int = 0,
    limit: int = 50
):
    """Get audit logs (admin only)"""
    logger.info(f"[get_audit_logs] Admin {current_user.email} fetching audit logs")

    # Generate stub audit logs
    stub_logs = [
        {
            "id": "audit-001",
            "timestamp": (datetime.utcnow() - timedelta(minutes=5)).isoformat(),
            "action": "user.login",
            "user": "admin@nexus.local",
            "resource_type": "auth",
            "resource_id": "session-001",
            "details": {"ip_address": "192.168.1.100"},
            "ip_address": "192.168.1.100",
            "user_agent": "Mozilla/5.0"
        },
        {
            "id": "audit-002",
            "timestamp": (datetime.utcnow() - timedelta(minutes=15)).isoformat(),
            "action": "node.create",
            "user": "admin@nexus.local",
            "resource_type": "node",
            "resource_id": "node-001",
            "details": {"node_name": "web-server-01"},
            "ip_address": "192.168.1.100",
            "user_agent": "Mozilla/5.0"
        },
        {
            "id": "audit-003",
            "timestamp": (datetime.utcnow() - timedelta(minutes=30)).isoformat(),
            "action": "tunnel.create",
            "user": "admin@orizon.local",
            "resource_type": "tunnel",
            "resource_id": "tunnel-001",
            "details": {"protocol": "ssh", "port": 22},
            "ip_address": "192.168.1.101",
            "user_agent": "Mozilla/5.0"
        },
        {
            "id": "audit-004",
            "timestamp": (datetime.utcnow() - timedelta(hours=1)).isoformat(),
            "action": "acl.create",
            "user": "admin@nexus.local",
            "resource_type": "acl",
            "resource_id": "acl-001",
            "details": {"rule_name": "Allow Admin SSH"},
            "ip_address": "192.168.1.100",
            "user_agent": "Mozilla/5.0"
        },
        {
            "id": "audit-005",
            "timestamp": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
            "action": "user.password_change",
            "user": "admin@nexus.local",
            "resource_type": "user",
            "resource_id": "9fb865a4-48cc-4c8b-8eea-8d12c8544f5a",
            "details": {},
            "ip_address": "192.168.1.100",
            "user_agent": "Mozilla/5.0"
        }
    ]

    # Add dynamic logs
    all_logs = stub_logs + audit_logs_store

    # Apply pagination
    paginated_logs = all_logs[skip:skip + limit]

    return {
        "logs": paginated_logs,
        "total": len(all_logs),
        "skip": skip,
        "limit": limit
    }

@app.get("/api/v1/audit/statistics")
async def get_audit_statistics(current_user = Depends(require_admin)):
    """Get audit statistics (admin only)"""
    logger.info(f"[get_audit_statistics] Admin {current_user.email} fetching audit statistics")

    # Calculate statistics from stub data
    return {
        "total_events": 156,
        "events_today": 23,
        "events_this_week": 87,
        "events_this_month": 156,
        "top_actions": [
            {"action": "user.login", "count": 45},
            {"action": "node.update", "count": 23},
            {"action": "tunnel.create", "count": 18},
            {"action": "acl.modify", "count": 12}
        ],
        "top_users": [
            {"user": "admin@nexus.local", "count": 78},
            {"user": "admin@orizon.local", "count": 56}
        ],
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/api/v1/audit/export")
async def export_audit_logs(
    current_user = Depends(require_admin),
    format: str = "json"
):
    """Export audit logs (admin only)"""
    logger.info(f"[export_audit_logs] Admin {current_user.email} exporting audit logs as {format}")

    # For now, just return the logs in JSON format
    # TODO: Implement CSV/Excel export
    stub_logs = [
        {
            "id": "audit-001",
            "timestamp": datetime.utcnow().isoformat(),
            "action": "user.login",
            "user": "admin@nexus.local",
            "resource_type": "auth",
            "resource_id": "session-001"
        }
    ]

    return {"logs": stub_logs + audit_logs_store, "format": format}

# ============= HEALTH ENDPOINTS =============

@app.get("/health")
def health():
    return {"status": "ok", "service": "orizon-ztc"}

@app.get("/api/v1/health")
def api_health():
    return {"status": "ok", "version": "1.0.0"}

@app.get("/api/v1/debug/test")
def debug_test():
    return {
        "status": "ok",
        "message": "Backend is working",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/api/v1/debug/info")
async def debug_info(db: AsyncSession = Depends(get_db)):
    """Get comprehensive debug information"""
    import platform
    import psutil

    # Database connection test
    try:
        await db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    # Count users
    try:
        result = await db.execute(text("SELECT COUNT(*) as count FROM users"))
        users_count = result.first().count
    except Exception as e:
        users_count = f"error: {str(e)}"

    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "system": {
            "platform": platform.system(),
            "python_version": platform.python_version(),
            "cpu_count": psutil.cpu_count(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent,
        },
        "database": {
            "status": db_status,
            "users_count": users_count,
        },
        "environment": {
            "database_url": "postgresql://orizon:***@localhost:5432/orizon_ztc",
        }
    }

@app.get("/api/v1/debug/headers")
async def debug_headers(request: Request):
    """Debug endpoint to see all request headers"""
    return {
        "headers": dict(request.headers),
        "client": request.client.host if request.client else None,
        "method": request.method,
        "url": str(request.url),
    }

@app.post("/api/v1/debug/token")
async def debug_token(authorization: str = Header(None)):
    """Debug JWT token"""
    if not authorization or not authorization.startswith("Bearer "):
        return {"error": "No token provided"}

    token = authorization.replace("Bearer ", "")
    payload = decode_token(token)

    return {
        "token_length": len(token),
        "payload": payload,
        "valid": payload is not None
    }

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f">>> {request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"<<< {response.status_code}")
    return response
