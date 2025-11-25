# Orizon Zero Trust Enterprise SASE - Deployment Guide

**Version:** 2.0.1
**Last Updated:** 25 November 2025
**Target Environment:** Production Server (139.59.149.48)

---

## 📋 Table of Contents

1. [System Overview](#system-overview)
2. [Prerequisites](#prerequisites)
3. [Production Server Setup](#production-server-setup)
4. [Backend Deployment](#backend-deployment)
5. [Frontend Deployment](#frontend-deployment)
6. [Database Configuration](#database-configuration)
7. [Nginx Configuration](#nginx-configuration)
8. [SSL/TLS Setup](#ssltls-setup)
9. [Environment Variables](#environment-variables)
10. [Deployment Verification](#deployment-verification)
11. [Troubleshooting](#troubleshooting)
12. [Rollback Procedures](#rollback-procedures)

---

## System Overview

### Architecture Components

```
┌─────────────────────────────────────────────────────────┐
│                    Production Server                    │
│                  139.59.149.48 (Ubuntu)                 │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │    Nginx     │  │    Docker    │  │  Databases   │ │
│  │  (Port 80)   │  │   Backend    │  │ PostgreSQL   │ │
│  │              │  │  (Port 8000) │  │   MongoDB    │ │
│  │  Frontend    │  │              │  │    Redis     │ │
│  │  Static      │  │   FastAPI    │  │              │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Technology Stack

- **Backend:** FastAPI (Python 3.11+) with async support
- **Frontend:** Vanilla JavaScript (no framework dependencies)
- **Databases:** PostgreSQL, MongoDB, Redis
- **Web Server:** Nginx
- **Containerization:** Docker & Docker Compose
- **SSH Access:** mcpbot user with key authentication

---

## Prerequisites

### Local Development Machine

```bash
# Required tools
- Git
- SSH client
- SSH key: ~/.ssh/id_ed25519_orizon_mcp
- Text editor
```

### Production Server Requirements

```bash
# System
- Ubuntu 20.04+ LTS
- 4GB+ RAM
- 40GB+ Storage
- Public IP: 139.59.149.48

# Software
- Docker 24.0+
- Docker Compose 2.20+
- Nginx 1.18+
- PostgreSQL 14+
- MongoDB 6.0+
- Redis 7.0+
```

### Server Access

```bash
# SSH Connection
ssh -i ~/.ssh/id_ed25519_orizon_mcp mcpbot@139.59.149.48

# Sudo Password
IlProfano.1969
```

---

## Production Server Setup

### 1. Initial Server Configuration

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker mcpbot

# Install Docker Compose
sudo apt install docker-compose-plugin -y

# Install Nginx
sudo apt install nginx -y

# Install PostgreSQL Client
sudo apt install postgresql-client -y
```

### 2. Directory Structure

```bash
# Create application directories
sudo mkdir -p /opt/orizon-ztc
sudo mkdir -p /var/www/orizon
sudo chown -R mcpbot:mcpbot /opt/orizon-ztc
sudo chown -R www-data:www-data /var/www/orizon

# Directory layout
/opt/orizon-ztc/           # Backend application
├── backend/               # FastAPI application
│   ├── app/
│   ├── alembic/
│   └── docker-compose.yml
├── .env                   # Environment variables
└── logs/                  # Application logs

/var/www/orizon/           # Frontend static files
├── auth/                  # Login pages
├── dashboard/             # Main dashboard
└── assets/                # Static resources
```

---

## Backend Deployment

### 1. Clone Repository

```bash
cd /opt/orizon-ztc
git clone <repository-url> .
# Or update existing:
git pull origin main
```

### 2. Environment Configuration

Create `/opt/orizon-ztc/.env`:

```bash
# Database Configuration
DATABASE_URL=postgresql+asyncpg://orizon_user:secure_password@localhost:5432/orizon_ztc
MONGODB_URL=mongodb://localhost:27017/orizon_ztc
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-secure-secret-key-min-32-chars
JWT_SECRET_KEY=your-jwt-secret-key-min-32-chars
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Application
PROJECT_NAME=Orizon Zero Trust Connect
VERSION=2.0.1
API_V1_STR=/api/v1
DEBUG=false
ENVIRONMENT=production

# CORS Origins
CORS_ORIGINS=["http://139.59.149.48", "https://139.59.149.48"]

# Superuser (Initial Admin)
FIRST_SUPERUSER_EMAIL=marco@syneto.eu
FIRST_SUPERUSER_PASSWORD=profano.69
FIRST_SUPERUSER_NAME=Marco Lorenzi
```

### 3. Docker Deployment

```bash
cd /opt/orizon-ztc

# Build and start containers
docker compose up -d --build

# Check status
docker compose ps

# View logs
docker compose logs -f backend

# Expected output:
# orizon-backend | INFO: Application startup complete
# orizon-backend | INFO: Uvicorn running on http://0.0.0.0:8000
```

### 4. Database Migrations

```bash
# Run migrations
docker compose exec backend alembic upgrade head

# Create initial superuser (if needed)
docker compose exec backend python -m app.core.init_db
```

### 5. Verify Backend

```bash
# Health check
curl http://localhost:8000/health

# API documentation
curl http://localhost:8000/docs

# Test login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"marco@syneto.eu","password":"profano.69"}'
```

---

## Frontend Deployment

### 1. Deploy Static Files

```bash
# Copy frontend files
sudo cp -r /opt/orizon-ztc/frontend/* /var/www/orizon/

# Set permissions
sudo chown -R www-data:www-data /var/www/orizon/
sudo find /var/www/orizon/ -type f -exec chmod 644 {} \;
sudo find /var/www/orizon/ -type d -exec chmod 755 {} \;
```

### 2. Frontend Structure

```bash
/var/www/orizon/
├── auth/
│   ├── login.html         # Login page
│   └── register.html      # Registration page
├── dashboard/
│   └── index.html         # Main CRUD dashboard
├── assets/
│   ├── css/
│   ├── js/
│   └── images/
└── index.html             # Landing page
```

### 3. Verify Frontend Files

```bash
# Check files exist
ls -lh /var/www/orizon/dashboard/index.html
ls -lh /var/www/orizon/auth/login.html

# Verify permissions
stat /var/www/orizon/dashboard/index.html
```

---

## Database Configuration

### 1. PostgreSQL Setup

```bash
# Install PostgreSQL
sudo apt install postgresql postgresql-contrib -y

# Create database and user
sudo -u postgres psql << EOF
CREATE DATABASE orizon_ztc;
CREATE USER orizon_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE orizon_ztc TO orizon_user;
\q
EOF

# Verify connection
psql -h localhost -U orizon_user -d orizon_ztc -c "SELECT version();"
```

### 2. MongoDB Setup

```bash
# Import MongoDB GPG key
curl -fsSL https://www.mongodb.org/static/pgp/server-6.0.asc | \
   sudo gpg -o /usr/share/keyrings/mongodb-server-6.0.gpg --dearmor

# Add MongoDB repository
echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-6.0.gpg ] \
https://repo.mongodb.org/apt/ubuntu focal/mongodb-org/6.0 multiverse" | \
sudo tee /etc/apt/sources.list.d/mongodb-org-6.0.list

# Install MongoDB
sudo apt update
sudo apt install -y mongodb-org

# Start MongoDB
sudo systemctl start mongod
sudo systemctl enable mongod

# Verify
mongosh --eval 'db.version()'
```

### 3. Redis Setup

```bash
# Install Redis
sudo apt install redis-server -y

# Configure Redis
sudo sed -i 's/supervised no/supervised systemd/' /etc/redis/redis.conf

# Restart Redis
sudo systemctl restart redis-server
sudo systemctl enable redis-server

# Verify
redis-cli ping
# Expected: PONG
```

---

## Nginx Configuration

### 1. Create Site Configuration

Create `/etc/nginx/sites-available/orizon`:

```nginx
server {
    listen 80;
    server_name 139.59.149.48;

    # Frontend static files
    location / {
        root /var/www/orizon;
        index index.html;
        try_files $uri $uri/ =404;

        # Cache control
        add_header Cache-Control "no-cache, no-store, must-revalidate";
        add_header Pragma "no-cache";
        add_header Expires "0";
    }

    # API proxy to backend
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;

        # CORS headers
        add_header 'Access-Control-Allow-Origin' '*' always;
        add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, OPTIONS' always;
        add_header 'Access-Control-Allow-Headers' 'Authorization, Content-Type' always;

        # Handle preflight requests
        if ($request_method = OPTIONS) {
            return 204;
        }
    }

    # API docs
    location /docs {
        proxy_pass http://localhost:8000/docs;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Health check
    location /health {
        proxy_pass http://localhost:8000/health;
        access_log off;
    }
}
```

### 2. Enable Site

```bash
# Create symlink
sudo ln -s /etc/nginx/sites-available/orizon /etc/nginx/sites-enabled/

# Remove default site
sudo rm /etc/nginx/sites-enabled/default

# Test configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx

# Verify status
sudo systemctl status nginx
```

---

## SSL/TLS Setup

### 1. Install Certbot

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx -y

# Obtain certificate
sudo certbot --nginx -d yourdomain.com

# Auto-renewal test
sudo certbot renew --dry-run
```

### 2. HTTPS Configuration

Certbot automatically updates Nginx config. Verify:

```bash
cat /etc/nginx/sites-available/orizon | grep ssl
```

---

## Environment Variables

### Backend Environment (.env)

Complete list of environment variables:

```bash
# === DATABASE ===
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/orizon_ztc
MONGODB_URL=mongodb://localhost:27017/orizon_ztc
REDIS_URL=redis://localhost:6379/0

# === SECURITY ===
SECRET_KEY=min-32-char-random-string
JWT_SECRET_KEY=another-32-char-random-string
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# === APPLICATION ===
PROJECT_NAME=Orizon Zero Trust Connect
VERSION=2.0.1
API_V1_STR=/api/v1
DEBUG=false
ENVIRONMENT=production
LOG_LEVEL=info

# === CORS ===
CORS_ORIGINS=["http://139.59.149.48","https://139.59.149.48"]

# === SUPERUSER ===
FIRST_SUPERUSER_EMAIL=marco@syneto.eu
FIRST_SUPERUSER_PASSWORD=profano.69
FIRST_SUPERUSER_NAME=Marco Lorenzi

# === RATE LIMITING ===
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_BURST=10

# === SESSION ===
SESSION_TIMEOUT_MINUTES=30
MAX_SESSIONS_PER_USER=5

# === EMAIL (Optional) ===
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=noreply@example.com
SMTP_PASSWORD=email_password
SMTP_FROM=noreply@example.com
```

### Generating Secrets

```bash
# Generate SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate JWT_SECRET_KEY
openssl rand -hex 32
```

---

## Deployment Verification

### 1. Backend Health Checks

```bash
# Container status
docker compose ps
# Expected: orizon-backend (healthy)

# Health endpoint
curl http://localhost:8000/health
# Expected: {"status":"healthy"}

# API documentation
curl http://localhost:8000/docs
# Expected: HTML OpenAPI docs

# Database connection
docker compose exec backend python -c "from app.core.database import engine; print('DB OK')"
```

### 2. Frontend Verification

```bash
# Check files served
curl -I http://139.59.149.48/
curl -I http://139.59.149.48/dashboard/
curl -I http://139.59.149.48/auth/login.html

# All should return: HTTP/1.1 200 OK
```

### 3. API Integration Test

```bash
# Login test
TOKEN=$(curl -s -X POST http://139.59.149.48/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"marco@syneto.eu","password":"profano.69"}' | \
  python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

echo "Token: ${TOKEN:0:20}..."

# Get users
curl -s http://139.59.149.48/api/v1/users \
  -H "Authorization: Bearer $TOKEN" | \
  python3 -c "import sys,json; users=json.load(sys.stdin); print(f'Users: {len(users)}')"
```

### 4. Database Verification

```bash
# PostgreSQL
psql -h localhost -U orizon_user -d orizon_ztc -c "SELECT COUNT(*) FROM users;"

# MongoDB
mongosh orizon_ztc --eval "db.audit_logs.countDocuments()"

# Redis
redis-cli DBSIZE
```

### 5. Log Monitoring

```bash
# Backend logs
docker compose logs -f backend --tail=50

# Nginx access logs
sudo tail -f /var/log/nginx/access.log

# Nginx error logs
sudo tail -f /var/log/nginx/error.log

# System logs
journalctl -u docker -f
```

---

## Troubleshooting

### Backend Issues

#### Container Won't Start

```bash
# Check logs
docker compose logs backend

# Common fixes:
# 1. Invalid .env file
docker compose config

# 2. Port already in use
sudo lsof -i :8000

# 3. Database connection failed
docker compose exec backend python -c "from app.core.database import engine; print(engine)"
```

#### Database Connection Errors

```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Test connection
psql -h localhost -U orizon_user -d orizon_ztc

# Reset password
sudo -u postgres psql -c "ALTER USER orizon_user PASSWORD 'new_password';"
```

#### 502 Bad Gateway

```bash
# Backend not responding
curl http://localhost:8000/health

# Restart backend
docker compose restart backend

# Check Nginx config
sudo nginx -t
```

### Frontend Issues

#### 404 Not Found

```bash
# Check file exists
ls -lh /var/www/orizon/dashboard/index.html

# Check permissions
stat /var/www/orizon/dashboard/index.html

# Fix permissions
sudo chown -R www-data:www-data /var/www/orizon/
sudo chmod -R 755 /var/www/orizon/
```

#### Blank Page / No Data

```bash
# Check browser console (F12)
# Common issues:
# 1. CORS errors - check Nginx config
# 2. API endpoint wrong - verify /api/ proxy
# 3. Token expired - re-login

# Clear browser cache
# Force refresh: Ctrl+Shift+R
```

### Performance Issues

```bash
# Check system resources
htop
df -h
free -m

# Check Docker stats
docker stats

# Check database connections
docker compose exec backend python -c "from sqlalchemy import create_engine; print('OK')"
```

---

## Rollback Procedures

### 1. Quick Rollback

```bash
# Stop current deployment
docker compose down

# Restore previous version
git log --oneline -5
git checkout <previous-commit>

# Rebuild and restart
docker compose up -d --build
```

### 2. Database Rollback

```bash
# List migrations
docker compose exec backend alembic history

# Rollback to previous version
docker compose exec backend alembic downgrade -1

# Or rollback to specific version
docker compose exec backend alembic downgrade <revision>
```

### 3. Frontend Rollback

```bash
# Restore from backup
sudo cp /var/www/orizon/dashboard/index.html.backup-TIMESTAMP \
       /var/www/orizon/dashboard/index.html

# Verify
curl -I http://139.59.149.48/dashboard/
```

### 4. Complete System Restore

```bash
# 1. Stop all services
docker compose down
sudo systemctl stop nginx

# 2. Restore database
pg_restore -h localhost -U orizon_user -d orizon_ztc backup.dump

# 3. Restore frontend
sudo rsync -av /backup/orizon/ /var/www/orizon/

# 4. Restore backend code
git reset --hard <stable-commit>

# 5. Restart services
docker compose up -d
sudo systemctl start nginx
```

---

## Deployment Checklist

### Pre-Deployment

- [ ] Backup current database
- [ ] Backup current frontend files
- [ ] Note current git commit
- [ ] Check disk space (df -h)
- [ ] Check system resources (htop)
- [ ] Review CHANGELOG for breaking changes

### Deployment

- [ ] Pull latest code (git pull)
- [ ] Review .env changes
- [ ] Run database migrations
- [ ] Build Docker containers
- [ ] Deploy frontend files
- [ ] Restart services
- [ ] Check logs for errors

### Post-Deployment

- [ ] Verify backend health endpoint
- [ ] Test user login
- [ ] Test CRUD operations
- [ ] Check API endpoints
- [ ] Monitor logs for 10 minutes
- [ ] Test from external network
- [ ] Update documentation if needed

---

## Production URLs

- **Dashboard:** http://139.59.149.48/dashboard/
- **Login:** http://139.59.149.48/auth/login.html
- **API Docs:** http://139.59.149.48/docs
- **Health Check:** http://139.59.149.48/health

---

## Support & Maintenance

### Regular Maintenance Tasks

```bash
# Weekly
- Check disk space
- Review error logs
- Update system packages
- Verify backups

# Monthly
- Rotate logs
- Update Docker images
- Security patches
- Performance review
```

### Monitoring Commands

```bash
# System health
systemctl status nginx docker postgresql mongodb redis-server

# Application status
docker compose ps
curl http://localhost:8000/health

# Resource usage
docker stats
df -h
free -m
```

---

**Document Version:** 1.0
**Last Updated:** 25 November 2025
**Maintained By:** Marco Lorenzi (marco@syneto.eu)
