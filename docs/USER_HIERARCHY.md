# Orizon Zero Trust Connect - User Hierarchy System

## Overview

Orizon implements a 4-level hierarchical role-based access control (RBAC) system. This system ensures that users can only see and manage resources within their hierarchical scope.

## Role Hierarchy

```
Level 4: SUPERUSER (Platform Owner)
    │
    └── Level 3: SUPER_ADMIN (Distributors)
            │
            └── Level 2: ADMIN (Resellers)
                    │
                    └── Level 1: USER (End Clients)
```

## Role Definitions

### SUPERUSER (Level 4)
- **Purpose**: Platform owner with full system access
- **Typical User**: Marco @ Syneto/Orizon
- **Permissions**:
  - View ALL users in the system
  - Create users of ANY role (SUPER_ADMIN, ADMIN, USER)
  - Delete ANY user
  - Access ALL nodes
  - Manage ALL groups
  - Full system configuration

### SUPER_ADMIN (Level 3)
- **Purpose**: Distributors managing multiple resellers
- **Typical User**: Regional distributors, partners
- **Permissions**:
  - View: Self + all users they created (and their subordinates)
  - Create: ADMIN and USER only
  - Delete: Only users they created (lower level)
  - Nodes: Only those in their groups
  - Groups: Create and manage their own groups

### ADMIN (Level 2)
- **Purpose**: Resellers managing end clients
- **Typical User**: IT service providers, MSPs
- **Permissions**:
  - View: Self + all USERs they created
  - Create: USER only
  - Delete: Only USERs they created
  - Nodes: Only those in their groups
  - Groups: Manage groups they're part of

### USER (Level 1)
- **Purpose**: End clients accessing their assigned resources
- **Typical User**: Company employees, contractors
- **Permissions**:
  - View: Only themselves
  - Create: Cannot create users
  - Delete: Cannot delete users
  - Nodes: Only those in their groups (read-only)
  - Groups: View only

## Hierarchy Tracking

The system tracks "who created whom" using the `created_by_id` field in the User model:

```sql
users
├── id (UUID)
├── email
├── role (SUPERUSER, SUPER_ADMIN, ADMIN, USER)
├── created_by_id (UUID, FK → users.id)  -- Parent in hierarchy
└── ...
```

### Example Hierarchy Tree

```
Marco (SUPERUSER) - created_by_id: NULL
├── Luca (SUPER_ADMIN) - created_by_id: Marco's ID
│   ├── Reseller1 (ADMIN) - created_by_id: Luca's ID
│   │   ├── Client1 (USER) - created_by_id: Reseller1's ID
│   │   └── Client2 (USER) - created_by_id: Reseller1's ID
│   └── Reseller2 (ADMIN) - created_by_id: Luca's ID
│       └── Client3 (USER) - created_by_id: Reseller2's ID
└── AnotherDistributor (SUPER_ADMIN) - created_by_id: Marco's ID
    └── ...
```

## Visibility Rules

### User Visibility

| Viewer Role | Can See |
|-------------|---------|
| SUPERUSER | All users |
| SUPER_ADMIN | Self + all created ADMIN/USER (recursively) |
| ADMIN | Self + all created USER |
| USER | Self only |

### User Creation Rules

| Creator Role | Can Create |
|--------------|------------|
| SUPERUSER | SUPER_ADMIN, ADMIN, USER |
| SUPER_ADMIN | ADMIN, USER |
| ADMIN | USER only |
| USER | Cannot create |

### User Modification Rules

| Modifier Role | Can Modify |
|---------------|------------|
| SUPERUSER | Any user |
| SUPER_ADMIN | Users in their hierarchy (lower level) |
| ADMIN | Users in their hierarchy (lower level) |
| USER | Self only (limited fields) |

### User Deletion Rules

| Deleter Role | Can Delete |
|--------------|------------|
| SUPERUSER | Any user (except self) |
| SUPER_ADMIN | Users in their hierarchy (lower level) |
| ADMIN | Users in their hierarchy (lower level) |
| USER | Cannot delete |

## Node Access via Groups

Node access is controlled through the Group system, not directly through hierarchy.

### Access Flow
```
User → Member of Group → Group contains Nodes → User can access Nodes
```

### Group Membership

Users access nodes through groups they belong to:

```
Group: "Server Interni"
├── Members:
│   ├── Marco (owner)
│   └── Luca (member)
├── Nodes:
│   ├── UbuntuBot (ssh: true, rdp: false, vnc: false, ssl_tunnel: true)
│   └── WindowsServer (ssh: false, rdp: true, vnc: false, ssl_tunnel: false)
```

### Permission Types per Node

| Permission | Description |
|------------|-------------|
| ssh | SSH terminal access |
| rdp | Remote Desktop Protocol |
| vnc | Virtual Network Computing |
| ssl_tunnel | SSL tunnel for HTTPS services |

## Implementation Details

### HierarchyService

Located at: `backend/app/services/hierarchy_service.py`

```python
class HierarchyService:
    @staticmethod
    def get_role_level(role: UserRole) -> int:
        """Returns numeric level (1-4)"""

    @staticmethod
    def can_manage_role(manager_role, target_role) -> bool:
        """Check if manager can create/modify target role"""

    @staticmethod
    async def get_subordinate_users(db, user, include_self=False) -> List[User]:
        """Get all users in hierarchy below this user"""

    @staticmethod
    async def can_access_user(db, accessor, target_user_id) -> bool:
        """Check if accessor can view/modify target user"""
```

### API Endpoints Using Hierarchy

| Endpoint | Hierarchy Check |
|----------|----------------|
| GET /users | Returns only visible users |
| POST /users | Validates role creation permission |
| GET /users/{id} | Checks access permission |
| PUT /users/{id} | Checks access + role change permission |
| DELETE /users/{id} | Checks access + deletion permission |

## Database Queries

### Get All Subordinates (Recursive)

```sql
WITH RECURSIVE subordinates AS (
    -- Base case: direct children
    SELECT id, email, role, created_by_id
    FROM users
    WHERE created_by_id = :user_id

    UNION ALL

    -- Recursive case: children of children
    SELECT u.id, u.email, u.role, u.created_by_id
    FROM users u
    INNER JOIN subordinates s ON u.created_by_id = s.id
)
SELECT * FROM subordinates;
```

### Check Hierarchy Access

```sql
-- Can user A access user B?
WITH RECURSIVE hierarchy AS (
    SELECT id, created_by_id FROM users WHERE id = :user_b_id
    UNION ALL
    SELECT u.id, u.created_by_id
    FROM users u
    INNER JOIN hierarchy h ON u.id = h.created_by_id
)
SELECT EXISTS (SELECT 1 FROM hierarchy WHERE id = :user_a_id);
```

## Testing the Hierarchy

### Test Case 1: SUPERUSER sees all

```bash
# Login as SUPERUSER
curl -X POST /api/v1/auth/login -d '{"email":"marco@syneto.eu","password":"xxx"}'

# Get users - should see ALL
curl /api/v1/users -H "Authorization: Bearer $TOKEN"
# Result: 14 users
```

### Test Case 2: SUPER_ADMIN sees limited

```bash
# Login as SUPER_ADMIN
curl -X POST /api/v1/auth/login -d '{"email":"luca.lorenzi@orizon.one","password":"xxx"}'

# Get users - should see only self + created users
curl /api/v1/users -H "Authorization: Bearer $TOKEN"
# Result: 2 users (self + admin created by luca)
```

### Test Case 3: Role creation restriction

```bash
# Login as SUPER_ADMIN
# Try to create another SUPER_ADMIN - should FAIL
curl -X POST /api/v1/users -H "Authorization: Bearer $TOKEN" \
  -d '{"email":"test@test.com","password":"xxx","role":"super_admin"}'
# Result: 403 Forbidden - Cannot create user with role super_admin
```

## Best Practices

1. **Always set created_by_id** when creating users programmatically
2. **Use HierarchyService** methods instead of direct queries
3. **Check hierarchy** before any user operation
4. **SUPERUSER accounts** should be limited (ideally 1-2)
5. **Audit trail**: Log all hierarchy-related operations

## Security Considerations

1. Users cannot escalate their own privileges
2. Users cannot access data outside their hierarchy
3. Deletion cascades should be handled carefully
4. created_by_id cannot be modified after creation
5. SUPERUSER role cannot be assigned via API (only DB admin)
