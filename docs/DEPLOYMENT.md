# Orizon Zero Trust Connect - Deployment Guide

## Production Server Information

| Property | Value |
|----------|-------|
| IP Address | 139.59.149.48 |
| OS | Ubuntu 24.04 LTS |
| Provider | DigitalOcean |
| SSH User | mcpbot |
| Application Path | /opt/orizon-ztc |
| Web Root | /var/www/html |

## Prerequisites

### Server Requirements
- Ubuntu 22.04 or 24.04 LTS
- Minimum 2 CPU cores
- Minimum 4GB RAM
- 40GB+ disk space
- Docker 24.x+
- Docker Compose v2+
- Nginx 1.24+

### Network Requirements
- Public IP address
- Open ports: 80, 443, 2222
- Domain (optional, for Let's Encrypt SSL)

## Directory Structure

```
/opt/orizon-ztc/
├── backend/
│   ├── app/
│   ├── alembic/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   ├── dist/           # Build output
│   ├── package.json
│   └── Dockerfile
├── script-generator/
│   └── Dockerfile
├── docker-compose.yml
├── .env
└── data/
    ├── postgres/
    ├── redis/
    └── mongodb/

/var/www/html/          # Frontend served by Nginx
├── index.html
└── assets/

/etc/nginx/
├── sites-available/orizon
├── sites-enabled/orizon -> ../sites-available/orizon
└── ssl/
    ├── orizon.crt
    └── orizon.key
```

## Installation Steps

### 1. Install Docker

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh

# Add user to docker group
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt install docker-compose-plugin -y

# Verify
docker --version
docker compose version
```

### 2. Install Nginx

```bash
sudo apt install nginx -y
sudo systemctl enable nginx
sudo systemctl start nginx
```

### 3. Clone Repository

```bash
cd /opt
sudo git clone https://github.com/MarcoLorenzi1969/OrizonZeroTrustEnterpriseSASE.git orizon-ztc
cd orizon-ztc
sudo chown -R $USER:$USER .
```

### 4. Configure Environment

Create `/opt/orizon-ztc/.env`:

```env
# Database
POSTGRES_USER=orizon
POSTGRES_PASSWORD=<secure_password>
POSTGRES_DB=orizon_ztc
DATABASE_URL=postgresql+asyncpg://orizon:<password>@postgres:5432/orizon_ztc

# Redis
REDIS_URL=redis://redis:6379/0

# MongoDB
MONGODB_URL=mongodb://mongodb:27017/orizon_logs

# JWT
JWT_SECRET_KEY=<generate_with_openssl_rand_hex_32>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7

# API
API_BASE_URL=https://139.59.149.48
SCRIPT_GENERATOR_URL=http://script-generator:3000

# SSH Tunnel
HUB_HOST=139.59.149.48
HUB_SSH_PORT=2222
SSH_TUNNEL_HOST=ssh-tunnel

# Environment
ENVIRONMENT=production
DEBUG=false
```

### 5. Generate SSL Certificate

```bash
# Create SSL directory
sudo mkdir -p /etc/nginx/ssl

# Generate self-signed certificate
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/nginx/ssl/orizon.key \
  -out /etc/nginx/ssl/orizon.crt \
  -subj "/C=IT/ST=Italy/L=Milan/O=Orizon/CN=139.59.149.48"
```

### 6. Configure Nginx

Create `/etc/nginx/sites-available/orizon`:

```nginx
upstream backend {
    server 127.0.0.1:8000;
}

# Redirect HTTP to HTTPS
server {
    listen 80 default_server;
    server_name 139.59.149.48 _;
    return 301 https://$host$request_uri;
}

# HTTPS Server
server {
    listen 443 ssl default_server;
    server_name 139.59.149.48 _;

    # SSL Configuration
    ssl_certificate /etc/nginx/ssl/orizon.crt;
    ssl_certificate_key /etc/nginx/ssl/orizon.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;

    client_max_body_size 100M;
    proxy_read_timeout 86400;
    proxy_send_timeout 86400;

    root /var/www/html;
    index index.html;

    # Health check
    location /health {
        proxy_pass http://backend/health;
        proxy_set_header Host $host;
        access_log off;
    }

    # API endpoints
    location /api/ {
        proxy_pass http://backend/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # WebSocket support
    location /ws/ {
        proxy_pass http://backend/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }

    # API Documentation
    location /docs {
        proxy_pass http://backend/docs;
        proxy_set_header Host $host;
    }

    location /redoc {
        proxy_pass http://backend/redoc;
        proxy_set_header Host $host;
    }

    # Static assets
    location /assets/ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # SPA fallback
    location / {
        try_files $uri $uri/ /index.html;
    }

    access_log /var/log/nginx/orizon_access.log;
    error_log /var/log/nginx/orizon_error.log warn;
}
```

Enable site:
```bash
sudo ln -sf /etc/nginx/sites-available/orizon /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

### 7. Build and Start Services

```bash
cd /opt/orizon-ztc

# Build containers
docker compose build

# Start services
docker compose up -d

# Check status
docker compose ps
```

### 8. Build and Deploy Frontend

```bash
# On local machine
cd frontend
npm install
npm run build

# Copy to server
rsync -avz dist/ user@139.59.149.48:/tmp/frontend_dist/

# On server
sudo rsync -av /tmp/frontend_dist/ /var/www/html/
sudo chown -R www-data:www-data /var/www/html
```

### 9. Initialize Database

```bash
# Run migrations
docker compose exec backend alembic upgrade head

# Create initial superuser (if not exists)
docker compose exec -it orizon-postgres psql -U orizon -d orizon_ztc
```

### 10. Initialize Default Superuser

Run the init_superuser.py script to create or update the default superuser:

```bash
# From the project directory
docker compose exec backend python /app/deploy/init_superuser.py

# Or run directly if Python is available
cd /opt/orizon-ztc
python3 deploy/init_superuser.py
```

## Default Credentials

### Web Administration Interface

| Field | Value |
|-------|-------|
| **Email** | marco@syneto.eu |
| **Password** | Syneto2601AA |
| **Role** | SUPERUSER |

**Security Note:** Change the default password immediately after initial deployment in production environments.

## Docker Compose Configuration

```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    container_name: orizon-backend
    restart: always
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
    depends_on:
      - postgres
      - redis
      - mongodb
    networks:
      - orizon-network

  postgres:
    image: postgres:15
    container_name: orizon-postgres
    restart: always
    environment:
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=${POSTGRES_DB}
    volumes:
      - ./data/postgres:/var/lib/postgresql/data
    networks:
      - orizon-network

  redis:
    image: redis:7-alpine
    container_name: orizon-redis
    restart: always
    volumes:
      - ./data/redis:/data
    networks:
      - orizon-network

  mongodb:
    image: mongo:6
    container_name: orizon-mongodb
    restart: always
    volumes:
      - ./data/mongodb:/data/db
    networks:
      - orizon-network

  ssh-tunnel:
    build: ./ssh-tunnel
    container_name: orizon-ssh-tunnel
    restart: always
    ports:
      - "2222:2222"
    networks:
      - orizon-network

  script-generator:
    build: ./script-generator
    container_name: orizon-script-generator
    restart: always
    ports:
      - "3000:3000"
    networks:
      - orizon-network

networks:
  orizon-network:
    driver: bridge
```

## Management Commands

### Service Management

```bash
# Start all services
docker compose up -d

# Stop all services
docker compose down

# Restart specific service
docker compose restart backend

# View logs
docker compose logs -f backend
docker compose logs -f --tail=100

# Check status
docker compose ps
```

### Database Operations

```bash
# Connect to PostgreSQL
docker compose exec postgres psql -U orizon -d orizon_ztc

# Backup database
docker compose exec postgres pg_dump -U orizon orizon_ztc > backup.sql

# Restore database
cat backup.sql | docker compose exec -T postgres psql -U orizon -d orizon_ztc
```

### Frontend Updates

```bash
# On local machine
cd frontend
npm run build

# Deploy to server
rsync -avz --delete dist/ user@server:/tmp/frontend_dist/

# On server
sudo rsync -av /tmp/frontend_dist/ /var/www/html/
```

### Backend Updates

```bash
# On server
cd /opt/orizon-ztc

# Pull latest code
git pull origin main

# Rebuild and restart
docker compose build backend
docker compose up -d backend
```

## Monitoring

### Check Service Health

```bash
# Health endpoint
curl -k https://139.59.149.48/health

# API status
curl -k https://139.59.149.48/api/v1/health
```

### View Logs

```bash
# Application logs
docker compose logs backend --tail=100 -f

# Nginx access logs
sudo tail -f /var/log/nginx/orizon_access.log

# Nginx error logs
sudo tail -f /var/log/nginx/orizon_error.log
```

### Resource Usage

```bash
# Docker stats
docker stats

# Disk usage
df -h
du -sh /opt/orizon-ztc/data/*
```

## Troubleshooting

### Common Issues

#### 1. Backend not starting
```bash
# Check logs
docker compose logs backend

# Check database connection
docker compose exec backend python -c "from app.core.database import engine; print('OK')"
```

#### 2. Frontend not loading
```bash
# Check Nginx config
sudo nginx -t

# Check file permissions
ls -la /var/www/html/
```

#### 3. SSL certificate issues
```bash
# Verify certificate
openssl x509 -in /etc/nginx/ssl/orizon.crt -text -noout

# Regenerate if needed
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/nginx/ssl/orizon.key \
  -out /etc/nginx/ssl/orizon.crt \
  -subj "/C=IT/ST=Italy/L=Milan/O=Orizon/CN=139.59.149.48"
```

#### 4. Database connection refused
```bash
# Check if PostgreSQL is running
docker compose ps postgres

# Check PostgreSQL logs
docker compose logs postgres
```

## Backup Strategy

### Daily Backup Script

```bash
#!/bin/bash
# /opt/orizon-ztc/backup.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=/opt/orizon-ztc/backups

mkdir -p $BACKUP_DIR

# Backup PostgreSQL
docker compose exec -T postgres pg_dump -U orizon orizon_ztc | gzip > $BACKUP_DIR/postgres_$DATE.sql.gz

# Backup MongoDB
docker compose exec -T mongodb mongodump --archive | gzip > $BACKUP_DIR/mongodb_$DATE.gz

# Keep only last 7 days
find $BACKUP_DIR -mtime +7 -delete

echo "Backup completed: $DATE"
```

### Cron Job

```bash
# Add to crontab
0 2 * * * /opt/orizon-ztc/backup.sh >> /var/log/orizon-backup.log 2>&1
```

## Security Checklist

- [ ] Change default passwords in .env
- [ ] Use strong JWT secret key
- [ ] Configure firewall (ufw)
- [ ] Enable automatic security updates
- [ ] Set up SSL certificate renewal (if using Let's Encrypt)
- [ ] Regular backups configured
- [ ] Log rotation configured
- [ ] Monitor disk space
