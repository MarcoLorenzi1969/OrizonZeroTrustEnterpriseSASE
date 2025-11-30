# Orizon Zero Trust Enterprise SASE - Development Guide

**Version:** 2.0.1
**Last Updated:** 25 November 2025

---

## 📋 Table of Contents

1. [Development Environment Setup](#development-environment-setup)
2. [Project Structure](#project-structure)
3. [Backend Development](#backend-development)
4. [Frontend Development](#frontend-development)
5. [Database Development](#database-development)
6. [Testing](#testing)
7. [Code Style & Standards](#code-style--standards)
8. [Git Workflow](#git-workflow)
9. [Debugging](#debugging)
10. [Common Development Tasks](#common-development-tasks)

---

## Development Environment Setup

### Prerequisites

```bash
# System requirements
- Python 3.11+
- Node.js 18+ (optional, for tools)
- Docker & Docker Compose
- Git
- PostgreSQL 14+
- MongoDB 6.0+
- Redis 7.0+
```

### Local Setup

```bash
# 1. Clone repository
git clone <repository-url>
cd OrizonZeroTrustEnterpriseSASE

# 2. Create Python virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
cd backend
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development dependencies

# 4. Set up environment variables
cp .env.example .env
# Edit .env with your local settings

# 5. Start databases (via Docker)
docker compose up -d postgres mongodb redis

# 6. Run migrations
alembic upgrade head

# 7. Create initial data
python -m app.core.init_db

# 8. Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## Project Structure

```
OrizonZeroTrustEnterpriseSASE/
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── api/               # API endpoints
│   │   │   └── v1/
│   │   │       ├── endpoints/ # Endpoint modules
│   │   │       └── router.py  # Main router
│   │   ├── auth/              # Authentication
│   │   │   ├── dependencies.py
│   │   │   └── security.py
│   │   ├── core/              # Core configuration
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   └── init_db.py
│   │   ├── models/            # SQLAlchemy models
│   │   ├── schemas/           # Pydantic schemas
│   │   ├── services/          # Business logic
│   │   └── main.py            # FastAPI app
│   ├── alembic/               # Database migrations
│   ├── tests/                 # Backend tests
│   ├── requirements.txt
│   └── docker-compose.yml
│
├── frontend/                   # Frontend application
│   ├── auth/                  # Login/register pages
│   │   ├── login.html
│   │   └── register.html
│   ├── dashboard/             # Main dashboard
│   │   └── index.html
│   ├── assets/                # Static assets
│   │   ├── css/
│   │   ├── js/
│   │   └── images/
│   └── index.html             # Landing page
│
├── docs/                       # Documentation
│   ├── DEPLOYMENT_GUIDE.md
│   ├── DEVELOPMENT_GUIDE.md
│   ├── API_REFERENCE.md
│   ├── USER_GUIDE.md
│   ├── ARCHITECTURE.md
│   ├── SECURITY_GUIDE.md
│   └── MULTI_TENANT_SYSTEM.md
│
├── tests/                      # Integration tests
│   └── crud_operations_test.sh
│
├── scripts/                    # Utility scripts
│   └── README.md
│
├── backups_docs/              # Archived documentation
│
├── .gitignore
├── README.md
├── CHANGELOG.md
└── VERSION
```

---

## Backend Development

### FastAPI Application Structure

#### 1. Models (SQLAlchemy)

Location: `backend/app/models/`

```python
# Example: user.py
from sqlalchemy import Column, String, Enum
from app.core.database import Base
import enum

class UserRole(str, enum.Enum):
    SUPERUSER = "superuser"
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    USER = "user"

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.USER)
    # ... more fields
```

#### 2. Schemas (Pydantic)

Location: `backend/app/schemas/`

```python
# Example: user.py
from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    role: str = "user"

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str

    class Config:
        from_attributes = True  # Pydantic v2
```

#### 3. API Endpoints

Location: `backend/app/api/v1/endpoints/`

```python
# Example: user_management.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

@router.post("/users", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    # Implementation
    pass

@router.get("/users", response_model=List[UserResponse])
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Implementation
    pass
```

#### 4. Services (Business Logic)

Location: `backend/app/services/`

```python
# Example: user_service.py
class UserService:
    @staticmethod
    async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
        result = await db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create_user(db: AsyncSession, user_data: UserCreate) -> User:
        # Business logic here
        pass
```

### Database Migrations

#### Create New Migration

```bash
# Auto-generate migration from model changes
cd backend
alembic revision --autogenerate -m "Description of changes"

# Review generated file in alembic/versions/
# Edit if necessary

# Apply migration
alembic upgrade head
```

#### Migration Best Practices

```python
# alembic/versions/xxxx_add_user_role.py
def upgrade():
    # Add new column with default
    op.add_column('users',
        sa.Column('role', sa.String(20), nullable=False, server_default='user'))

    # Update existing data if needed
    op.execute("UPDATE users SET role = 'admin' WHERE is_admin = true")

    # Remove old column
    op.drop_column('users', 'is_admin')

def downgrade():
    # Reverse operations
    op.add_column('users', sa.Column('is_admin', sa.Boolean(), default=False))
    op.execute("UPDATE users SET is_admin = true WHERE role = 'admin'")
    op.drop_column('users', 'role')
```

### Authentication & Authorization

#### 1. JWT Token Generation

```python
# app/auth/security.py
from jose import jwt
from datetime import datetime, timedelta

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=30)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
```

#### 2. Role-Based Access Control

```python
# app/auth/dependencies.py
class RoleChecker:
    def __init__(self, required_role: UserRole):
        self.required_role = required_role

    async def __call__(self, current_user: User = Depends(get_current_user)):
        if not check_permission(current_user.role, self.required_role):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user

# Usage in endpoints
require_admin = RoleChecker(UserRole.ADMIN)
require_superuser = RoleChecker(UserRole.SUPERUSER)
```

### Running Backend Locally

```bash
# Development server with auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# With custom log level
uvicorn app.main:app --reload --log-level debug

# Access API docs
open http://localhost:8000/docs
```

---

## Frontend Development

### Architecture

The frontend is built with **vanilla JavaScript** (no frameworks) for simplicity and performance.

#### Key Files

```
frontend/dashboard/index.html
- Complete single-page dashboard
- CRUD operations for Groups, Nodes, Users
- Modal-based forms
- Role-based UI elements
```

### Dashboard Structure

```javascript
// API Configuration
const API_BASE_URL = '/api/v1';

// State management
const currentData = {
    groups: [],
    nodes: [],
    users: []
};

// API calls with authentication
async function apiCall(endpoint, options = {}) {
    const token = localStorage.getItem('token');
    const headers = {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
        ...options.headers
    };

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        ...options,
        headers
    });

    if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
    }

    return response.json();
}

// CRUD Operations
async function loadUsers() {
    const data = await apiCall('/users');
    const usersList = Array.isArray(data) ? data : (data.users || []);
    currentData.users = usersList;
    renderUsersTable(usersList);
}

async function createUser(userData) {
    const response = await apiCall('/users', {
        method: 'POST',
        body: JSON.stringify(userData)
    });
    return response;
}
```

### Styling System

```css
/* Dark theme with gradient accents */
:root {
    --bg-dark: #0f172a;
    --bg-card: #1e293b;
    --text-primary: #f1f5f9;
    --accent-blue: #3b82f6;
    --accent-purple: #8b5cf6;
}

/* Role badges with visual hierarchy */
.badge-superuser {
    background: linear-gradient(135deg, #667eea, #764ba2);
    color: white;
}

.badge-super_admin {
    background: linear-gradient(135deg, #f093fb, #f5576c);
    color: white;
}

.badge-admin {
    background: rgba(59, 130, 246, 0.2);
    color: #3b82f6;
}

.badge-user {
    background: rgba(156, 163, 175, 0.2);
    color: #9ca3af;
}
```

### Modal System

```javascript
// Show modal
function showCreateUserModal() {
    document.getElementById('userForm').reset();
    document.getElementById('userModal').classList.add('show');
}

// Hide modal
function hideModal(modalId) {
    document.getElementById(modalId).classList.remove('show');
}

// Form submission
async function saveUser() {
    const formData = {
        email: document.getElementById('userEmail').value,
        full_name: document.getElementById('userFullName').value,
        password: document.getElementById('userPassword').value,
        role: document.getElementById('userRole').value
    };

    await createUser(formData);
    hideModal('userModal');
    loadUsers();
    showSuccess('User created successfully');
}
```

### Local Development

```bash
# Option 1: Python HTTP server
cd frontend
python3 -m http.server 8080

# Option 2: Node.js http-server
npx http-server frontend -p 8080

# Access: http://localhost:8080/dashboard/
```

---

## Database Development

### PostgreSQL Schema

```sql
-- Users table with role hierarchy
CREATE TABLE users (
    id VARCHAR(36) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(20) DEFAULT 'user',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_created_at ON users(created_at);
```

### MongoDB Collections

```javascript
// audit_logs collection
{
    _id: ObjectId(),
    user_id: "uuid",
    action: "user.create",
    resource: "users",
    timestamp: ISODate(),
    ip_address: "192.168.1.1",
    success: true,
    details: {
        target_user_id: "uuid",
        changes: {...}
    }
}
```

### Redis Cache Patterns

```python
# Cache user sessions
redis_client.setex(f"session:{user_id}", 1800, token)

# Rate limiting
key = f"rate_limit:{user_id}:{endpoint}"
current = redis_client.incr(key)
if current == 1:
    redis_client.expire(key, 60)  # 1 minute window
```

---

## Testing

### Backend Unit Tests

```bash
# Run all tests
cd backend
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_users.py

# Run specific test
pytest tests/test_users.py::test_create_user
```

### Integration Tests

```bash
# CRUD operations test
cd tests
bash crud_operations_test.sh

# Expected output:
# ✅ Groups CRUD: 5/6 tests passed
# ✅ Nodes CRUD: 6/6 tests passed
# ✅ Users CRUD: 6/6 tests passed
```

### API Testing with curl

```bash
# Login
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password"}' | \
  jq -r '.access_token')

# Create user
curl -X POST http://localhost:8000/api/v1/users \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser@example.com",
    "full_name": "New User",
    "password": "SecurePass123!",
    "role": "user"
  }'

# List users
curl -X GET http://localhost:8000/api/v1/users \
  -H "Authorization: Bearer $TOKEN"
```

---

## Code Style & Standards

### Python (Backend)

```python
# Use type hints
def create_user(db: AsyncSession, user_data: UserCreate) -> User:
    pass

# Use async/await
async def get_users(db: AsyncSession) -> List[User]:
    result = await db.execute(select(User))
    return result.scalars().all()

# Error handling
try:
    user = await user_service.create_user(db, user_data)
except IntegrityError:
    raise HTTPException(status_code=400, detail="Email already registered")

# Logging
from loguru import logger
logger.info(f"User created: {user.email}")
logger.error(f"Failed to create user: {str(e)}")
```

### JavaScript (Frontend)

```javascript
// Use async/await
async function loadData() {
    try {
        const data = await apiCall('/users');
        renderTable(data);
    } catch (error) {
        showError('Failed to load data');
        console.error(error);
    }
}

// Use const/let (no var)
const API_BASE_URL = '/api/v1';
let currentPage = 1;

// Arrow functions for callbacks
users.forEach(user => {
    console.log(user.email);
});

// Template literals
const message = `User ${user.name} created successfully`;
```

---

## Git Workflow

### Branch Strategy

```bash
# Main branches
main        # Production-ready code
develop     # Development branch (if using)

# Feature branches
git checkout -b feature/add-user-roles
git checkout -b fix/login-bug
git checkout -b docs/update-readme
```

### Commit Messages

```bash
# Good commit messages
git commit -m "Add 4-level role hierarchy to dashboard"
git commit -m "Fix: Users list not displaying correctly"
git commit -m "Docs: Update deployment guide with SSL setup"
git commit -m "Refactor: Extract user service logic"

# Include context
git commit -m "$(cat <<EOF
Implement complete 4-level role hierarchy

Changes:
- Add SuperAdmin role to UserRole enum
- Update dashboard dropdown with all 4 roles
- Add CSS badges for visual hierarchy
- Test all role levels on production

Tests: ✅ All CRUD operations passing
EOF
)"
```

### Pull Requests

```bash
# Before creating PR
1. Update from main: git pull origin main
2. Run tests: pytest && bash tests/crud_operations_test.sh
3. Check linting: flake8 backend/app
4. Update CHANGELOG.md
5. Create PR with description of changes
```

---

## Debugging

### Backend Debugging

```python
# Add breakpoints with debugpy
import debugpy
debugpy.listen(5678)
debugpy.wait_for_client()
debugpy.breakpoint()

# Or use pdb
import pdb; pdb.set_trace()

# Logging
from loguru import logger
logger.debug(f"User data: {user_data}")
logger.info(f"Processing {len(users)} users")
```

### Frontend Debugging

```javascript
// Browser DevTools Console
console.log('Current data:', currentData);
console.table(users);
console.dir(response);

// Debug API calls
apiCall('/users')
    .then(data => console.log('Success:', data))
    .catch(error => console.error('Error:', error));

// Check localStorage
console.log('Token:', localStorage.getItem('token'));
```

### Database Debugging

```bash
# PostgreSQL query monitoring
psql -U orizon_user -d orizon_ztc -c "
SELECT pid, query, state
FROM pg_stat_activity
WHERE datname = 'orizon_ztc';
"

# MongoDB query profiling
mongosh orizon_ztc --eval "db.setProfilingLevel(2)"
mongosh orizon_ztc --eval "db.system.profile.find().pretty()"

# Redis monitoring
redis-cli MONITOR
```

---

## Common Development Tasks

### Add New API Endpoint

```bash
# 1. Create schema in schemas/
# 2. Add endpoint in api/v1/endpoints/
# 3. Register router in api/v1/router.py
# 4. Test with curl
# 5. Update API_REFERENCE.md
```

### Add New Database Table

```bash
# 1. Create model in models/
# 2. Import in models/__init__.py
# 3. Generate migration: alembic revision --autogenerate
# 4. Review and edit migration
# 5. Apply: alembic upgrade head
# 6. Update ARCHITECTURE.md
```

### Add New Frontend Page

```bash
# 1. Create HTML file in frontend/
# 2. Add CSS styles
# 3. Add JavaScript for API calls
# 4. Update navigation/links
# 5. Test authentication flow
# 6. Update USER_GUIDE.md
```

### Update Role Permissions

```bash
# 1. Update UserRole enum in models/user.py
# 2. Update check_permission in auth/security.py
# 3. Update role hierarchy in User.can_manage_user()
# 4. Update dashboard role dropdown
# 5. Add CSS badge styles
# 6. Create migration if needed
# 7. Test all permission scenarios
```

---

## Development Tools

### Recommended VSCode Extensions

```json
{
    "recommendations": [
        "ms-python.python",
        "ms-python.vscode-pylance",
        "ms-toolsai.jupyter",
        "ms-azuretools.vscode-docker",
        "esbenp.prettier-vscode",
        "dbaeumer.vscode-eslint"
    ]
}
```

### Pre-commit Hooks

```bash
# Install pre-commit
pip install pre-commit

# Create .pre-commit-config.yaml
cat > .pre-commit-config.yaml << EOF
repos:
  - repo: https://github.com/psf/black
    rev: 23.0.0
    hooks:
      - id: black
  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
EOF

# Install hooks
pre-commit install
```

---

**Document Version:** 1.0
**Last Updated:** 25 November 2025
**Maintained By:** Development Team
