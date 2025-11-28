# Orizon Zero Trust Connect - API Reference

## Base URL

```
Production: https://139.59.149.48/api/v1
```

## Authentication

All API endpoints (except `/auth/login` and `/auth/register`) require authentication via JWT Bearer token.

```http
Authorization: Bearer <access_token>
```

---

## Authentication Endpoints

### POST /auth/login

Authenticate user and obtain JWT tokens.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

**Error Responses:**
- `401 Unauthorized`: Invalid credentials
- `403 Forbidden`: Account disabled

---

### POST /auth/refresh

Refresh access token using refresh token.

**Request Body:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

---

### GET /auth/me

Get current authenticated user information.

**Response (200 OK):**
```json
{
  "id": "5e02bb79-bd43-4fc0-b2d2-d50dc1ccc43b",
  "email": "user@example.com",
  "full_name": "User Name",
  "role": "admin",
  "is_active": true
}
```

---

## User Management Endpoints

### GET /users

List users visible to the current user based on hierarchy.

**Visibility Rules:**
- `SUPERUSER`: Sees all users
- `SUPER_ADMIN`: Sees self + ADMIN/USER created by them
- `ADMIN`: Sees self + USER created by them
- `USER`: Not authorized

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| skip | int | 0 | Pagination offset |
| limit | int | 100 | Max results (1-1000) |

**Response (200 OK):**
```json
[
  {
    "id": "uuid",
    "email": "user@example.com",
    "full_name": "User Name",
    "role": "admin",
    "is_active": true,
    "created_at": "2025-11-28T10:00:00",
    "last_login": "2025-11-28T12:00:00"
  }
]
```

**Required Role:** SUPERUSER, SUPER_ADMIN, or ADMIN

---

### POST /users

Create a new user. Users can only create roles lower than their own.

**Role Creation Rules:**
| Creator Role | Can Create |
|--------------|------------|
| SUPERUSER | SUPER_ADMIN, ADMIN, USER |
| SUPER_ADMIN | ADMIN, USER |
| ADMIN | USER only |

**Request Body:**
```json
{
  "email": "newuser@example.com",
  "full_name": "New User",
  "password": "SecurePass123!",
  "role": "admin",
  "is_active": true
}
```

**Response (201 Created):**
```json
{
  "id": "uuid",
  "email": "newuser@example.com",
  "full_name": "New User",
  "role": "admin",
  "is_active": true,
  "created_at": "2025-11-28T10:00:00",
  "last_login": null
}
```

**Error Responses:**
- `400 Bad Request`: Email already exists
- `403 Forbidden`: Cannot create user with that role

---

### GET /users/{user_id}

Get user by ID (only if in hierarchy).

**Response (200 OK):**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "full_name": "User Name",
  "role": "admin",
  "is_active": true,
  "created_at": "2025-11-28T10:00:00",
  "last_login": "2025-11-28T12:00:00"
}
```

**Error Responses:**
- `403 Forbidden`: Not authorized to access this user
- `404 Not Found`: User not found

---

### PUT /users/{user_id}

Update user (only if in hierarchy).

**Request Body:**
```json
{
  "full_name": "Updated Name",
  "role": "user",
  "is_active": false
}
```

**Response (200 OK):** Updated user object

---

### DELETE /users/{user_id}

Delete user (only if in hierarchy and lower role).

**Response (200 OK):**
```json
{
  "message": "User deleted successfully"
}
```

---

## Node Endpoints

### GET /nodes

List nodes accessible to the current user via groups.

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| skip | int | Pagination offset |
| limit | int | Max results |
| status | string | Filter by status (online, offline) |

**Response (200 OK):**
```json
{
  "nodes": [
    {
      "id": "uuid",
      "name": "UbuntuBot",
      "hostname": "192.168.3.101",
      "node_type": "linux",
      "status": "online",
      "public_ip": null,
      "private_ip": "192.168.3.101",
      "os_version": "Ubuntu 24.04",
      "agent_version": "1.0.0",
      "agent_token": "agt_xxx...",
      "cpu_usage": 25.5,
      "memory_usage": 45.2,
      "disk_usage": 60.0,
      "last_heartbeat": "2025-11-28T16:14:17",
      "reverse_tunnel_type": "SSH",
      "exposed_applications": ["TERMINAL", "HTTPS"],
      "application_ports": {
        "TERMINAL": {"local": 22, "remote": 9001},
        "HTTPS": {"local": 443, "remote": 34689}
      },
      "service_tunnel_port": 9001
    }
  ],
  "total": 1
}
```

---

### POST /nodes

Create a new node.

**Request Body:**
```json
{
  "name": "MyServer",
  "hostname": "192.168.1.100",
  "node_type": "linux",
  "private_ip": "192.168.1.100",
  "reverse_tunnel_type": "SSH",
  "exposed_applications": ["TERMINAL", "HTTPS"],
  "application_ports": {
    "TERMINAL": {"local": 22, "remote": null},
    "HTTPS": {"local": 443, "remote": null}
  }
}
```

**Response (201 Created):** Node object with generated `agent_token`

---

### GET /nodes/{node_id}

Get node by ID (if accessible via groups).

---

### PATCH /nodes/{node_id}

Update node.

---

### DELETE /nodes/{node_id}

Delete node and all associated data.

---

### GET /nodes/{node_id}/install-script/{os_type}

Generate installation script for node agent.

**Parameters:**
- `os_type`: `linux`, `macos`, or `windows`

**Response:** Plain text script file

---

### POST /nodes/heartbeat

Receive heartbeat from node agent (no user auth, uses agent_token).

**Request Body:**
```json
{
  "agent_token": "agt_xxx...",
  "timestamp": "2025-11-28T16:14:17",
  "agent_version": "1.0.0",
  "os_version": "Ubuntu 24.04"
}
```

---

### POST /nodes/metrics

Receive metrics update from node agent.

**Request Body:**
```json
{
  "agent_token": "agt_xxx...",
  "cpu_usage": 25.5,
  "memory_usage": 45.2,
  "disk_usage": 60.0,
  "cpu_cores": 4,
  "memory_mb": 8192,
  "disk_gb": 100
}
```

---

## Group Endpoints

### GET /groups/

List groups accessible to current user.

**Response (200 OK):**
```json
{
  "groups": [
    {
      "id": "uuid",
      "name": "Server Interni",
      "description": "Internal servers group",
      "settings": {
        "allow_terminal": true,
        "allow_rdp": false,
        "allow_vnc": false,
        "max_concurrent_sessions": 5
      },
      "created_by": "uuid",
      "is_active": true,
      "member_count": 3,
      "node_count": 5
    }
  ],
  "total": 1
}
```

---

### POST /groups/

Create a new group.

**Request Body:**
```json
{
  "name": "Development Servers",
  "description": "Servers for development team",
  "settings": {
    "allow_terminal": true,
    "allow_rdp": true,
    "allow_vnc": false,
    "max_concurrent_sessions": 10
  }
}
```

---

### GET /groups/{group_id}

Get group details.

---

### PUT /groups/{group_id}

Update group.

---

### DELETE /groups/{group_id}

Delete group (soft delete).

---

### GET /groups/{group_id}/members

List group members.

**Response (200 OK):**
```json
{
  "members": [
    {
      "user_id": "uuid",
      "email": "user@example.com",
      "username": "user",
      "full_name": "User Name",
      "role_in_group": "owner",
      "permissions": {},
      "added_at": "2025-11-28T10:00:00"
    }
  ],
  "total": 1
}
```

---

### POST /groups/{group_id}/members

Add user to group.

**Request Body:**
```json
{
  "user_id": "uuid",
  "role_in_group": "member",
  "permissions": {}
}
```

---

### DELETE /groups/{group_id}/members/{user_id}

Remove user from group.

---

### GET /groups/{group_id}/nodes

List nodes in group.

**Response (200 OK):**
```json
{
  "nodes": [
    {
      "node_id": "uuid",
      "name": "UbuntuBot",
      "hostname": "192.168.3.101",
      "status": "online",
      "node_type": "linux",
      "permissions": {
        "ssh": true,
        "rdp": false,
        "vnc": false,
        "ssl_tunnel": true
      },
      "added_at": "2025-11-28T10:00:00"
    }
  ],
  "total": 1
}
```

---

### POST /groups/{group_id}/nodes

Add node to group.

**Request Body:**
```json
{
  "node_id": "uuid",
  "permissions": {
    "ssh": true,
    "rdp": false,
    "vnc": false,
    "ssl_tunnel": false
  }
}
```

---

### PUT /groups/{group_id}/nodes/{node_id}

Update node permissions in group.

**Request Body:**
```json
{
  "permissions": {
    "ssh": true,
    "rdp": true,
    "vnc": false,
    "ssl_tunnel": true
  }
}
```

---

### DELETE /groups/{group_id}/nodes/{node_id}

Remove node from group.

---

## Tunnel Endpoints

### GET /tunnels/active

Get active tunnel sessions for current user.

---

### POST /tunnels/close/{tunnel_id}

Close an active tunnel.

---

## Health & Status

### GET /health

Health check endpoint.

**Response (200 OK):**
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "timestamp": "2025-11-28T16:14:17"
}
```

---

## Error Response Format

All error responses follow this format:

```json
{
  "detail": "Error message description"
}
```

Or for validation errors:

```json
{
  "detail": [
    {
      "loc": ["body", "field_name"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

## HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 201 | Created |
| 204 | No Content (successful delete) |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 422 | Validation Error |
| 500 | Internal Server Error |

## Rate Limiting

Currently no rate limiting is implemented. Consider implementing for production use.

## API Documentation

Interactive API documentation available at:
- Swagger UI: `https://139.59.149.48/docs`
- ReDoc: `https://139.59.149.48/redoc`
