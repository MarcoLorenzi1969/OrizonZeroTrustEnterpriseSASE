# 🚀 Deployment Guide - Orizon Zero Trust Connect

**Versione:** 1.0.0
**Last Updated:** Gennaio 2025
**Autore:** Marco Lorenzi @ Syneto/Orizon

---

## 📋 Indice

1. [Prerequisiti](#prerequisiti)
2. [Deployment Locale (Development)](#deployment-locale-development)
3. [Deployment Docker Compose](#deployment-docker-compose)
4. [Deployment Kubernetes](#deployment-kubernetes)
5. [Deployment DigitalOcean](#deployment-digitalocean)
6. [Configurazione Avanzata](#configurazione-avanzata)
7. [Monitoraggio e Logging](#monitoraggio-e-logging)
8. [Backup e Disaster Recovery](#backup-e-disaster-recovery)
9. [Troubleshooting](#troubleshooting)

---

## 🔧 Prerequisiti

### Hardware Minimo

**Development:**
- CPU: 2 cores
- RAM: 4GB
- Disk: 20GB
- Network: 10 Mbps

**Staging:**
- CPU: 4 cores
- RAM: 8GB
- Disk: 50GB
- Network: 100 Mbps

**Production:**
- CPU: 8+ cores
- RAM: 16GB+
- Disk: 200GB+ (SSD raccomandato)
- Network: 1 Gbps

### Software Requirements

**Per tutti gli ambienti:**
```bash
# Docker & Docker Compose
Docker Engine 24.0+
Docker Compose 2.0+

# Git
Git 2.30+

# Accesso SSH al server (per deployment remoti)
SSH client configurato
```

**Per deployment Kubernetes:**
```bash
# Kubernetes cluster
Kubernetes 1.28+
kubectl configurato

# Helm (opzionale)
Helm 3.0+
```

**Per development locale:**
```bash
# Backend
Python 3.10+
pip/virtualenv

# Frontend
Node.js 18+
npm o yarn

# Database (se non usi Docker)
PostgreSQL 15+
Redis 7+
MongoDB 7+
```

---

## 💻 Deployment Locale (Development)

### Opzione 1: Docker Compose (Consigliata)

#### 1. Clone del Repository

```bash
# Clone del progetto
git clone <repository-url>
cd OrizonZeroTrustConnect

# Oppure se già clonato
cd /Users/marcolorenzi/Windsurf/MCP-Server-LocalModelCyber/OrizonZeroTrustConnect
```

#### 2. Configurazione Environment Variables

```bash
# Copia il template .env
cp .env.example .env

# Modifica .env con i tuoi parametri
nano .env
```

**File .env minimo:**
```bash
# Database
POSTGRES_USER=orizon
POSTGRES_PASSWORD=change-me-strong-password
POSTGRES_DB=orizon_db

# Redis
REDIS_PASSWORD=change-me-redis-password

# MongoDB
MONGODB_USER=orizon
MONGODB_PASSWORD=change-me-mongo-password
MONGODB_DB=orizon_logs

# Backend
JWT_SECRET=change-me-jwt-secret-min-64-chars-random-string-here
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# API
API_V1_PREFIX=/api/v1
BACKEND_CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]

# Hub Configuration
HUB_HOST=46.101.189.126
SSH_TUNNEL_PORT=2222
HTTPS_TUNNEL_PORT=8443

# Environment
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO
```

#### 3. Avvio Stack Completo

```bash
# Build e avvio di tutti i servizi
docker-compose up -d

# Verifica che tutti i container siano running
docker-compose ps

# Output atteso:
# NAME                    STATUS          PORTS
# backend                 Up              0.0.0.0:8000->8000/tcp
# frontend                Up              0.0.0.0:3000->3000/tcp
# postgres                Up              0.0.0.0:5432->5432/tcp
# redis                   Up              0.0.0.0:6379->6379/tcp
# mongodb                 Up              0.0.0.0:27017->27017/tcp
# prometheus              Up              0.0.0.0:9090->9090/tcp
# grafana                 Up              0.0.0.0:3001->3001/tcp
```

#### 4. Inizializzazione Database

```bash
# Esegui migration del database
docker-compose exec backend alembic upgrade head

# Crea utente admin iniziale
docker-compose exec backend python -c "
from app.core.database import get_db
from app.models.user import User
from app.auth.security import get_password_hash
import asyncio

async def create_admin():
    async for db in get_db():
        admin = User(
            email='admin@orizon.local',
            hashed_password=get_password_hash('changeme123'),
            role='SuperUser',
            is_active=True
        )
        db.add(admin)
        await db.commit()
        print('Admin user created!')

asyncio.run(create_admin())
"
```

#### 5. Verifica e Accesso

```bash
# Test backend API
curl http://localhost:8000/health

# Output atteso:
{
  "status": "healthy",
  "version": "1.0.0",
  "database": "connected",
  "redis": "connected",
  "mongodb": "connected"
}

# Accedi alla UI
open http://localhost:3000

# Credenziali default:
# Email: admin@orizon.local
# Password: changeme123
```

#### 6. Accesso ai Servizi

| Servizio | URL | Credenziali |
|----------|-----|-------------|
| Frontend | http://localhost:3000 | admin@orizon.local / changeme123 |
| Backend API | http://localhost:8000 | JWT token |
| API Docs (Swagger) | http://localhost:8000/docs | - |
| Prometheus | http://localhost:9090 | - |
| Grafana | http://localhost:3001 | admin / admin |
| PostgreSQL | localhost:5432 | orizon / (da .env) |
| Redis | localhost:6379 | (da .env) |
| MongoDB | localhost:27017 | orizon / (da .env) |

### Opzione 2: Development Manuale (senza Docker)

#### Backend Setup

```bash
# 1. Crea virtual environment
cd backend
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# oppure: venv\Scripts\activate  # Windows

# 2. Installa dependencies
pip install -r requirements.txt

# 3. Configura .env
cp .env.example .env
nano .env

# 4. Avvia database (PostgreSQL, Redis, MongoDB)
# Assicurati che siano running localmente

# 5. Esegui migration
alembic upgrade head

# 6. Avvia backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Backend running su http://localhost:8000
```

#### Frontend Setup

```bash
# 1. Installa dependencies
cd frontend
npm install
# oppure: yarn install

# 2. Configura .env
cp .env.example .env
nano .env

# Contenuto .env:
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_WS_URL=ws://localhost:8000/ws

# 3. Avvia dev server
npm run dev
# oppure: yarn dev

# Frontend running su http://localhost:3000
```

---

## 🐳 Deployment Docker Compose (Staging)

### Setup Staging Environment

#### 1. Preparazione Server

```bash
# Connetti al server staging
ssh user@staging-server.com

# Installa Docker e Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Installa Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Logout e re-login per applicare gruppo docker
```

#### 2. Clone e Setup Progetto

```bash
# Clone repository
git clone <repository-url> /opt/orizon-ztc
cd /opt/orizon-ztc

# Configura .env per staging
cp .env.example .env
nano .env
```

**File .env staging:**
```bash
# Database - USA PASSWORD FORTI!
POSTGRES_USER=orizon_prod
POSTGRES_PASSWORD=$(openssl rand -base64 32)
POSTGRES_DB=orizon_production

# Redis
REDIS_PASSWORD=$(openssl rand -base64 32)

# MongoDB
MONGODB_USER=orizon_prod
MONGODB_PASSWORD=$(openssl rand -base64 32)
MONGODB_DB=orizon_audit

# Backend - GENERA SEGRETO RANDOM
JWT_SECRET=$(openssl rand -base64 64)
JWT_ALGORITHM=HS256

# API
API_V1_PREFIX=/api/v1
BACKEND_CORS_ORIGINS=["https://staging.orizon.syneto.net"]

# Hub Configuration
HUB_HOST=staging-hub.orizon.syneto.net
SSH_TUNNEL_PORT=2222
HTTPS_TUNNEL_PORT=8443

# Environment
ENVIRONMENT=staging
DEBUG=false
LOG_LEVEL=INFO

# Email (per notifiche)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=noreply@orizon.syneto.net
SMTP_PASSWORD=your-smtp-password
```

#### 3. Build e Deploy

```bash
# Build immagini Docker
docker-compose build

# Avvia stack in background
docker-compose up -d

# Verifica status
docker-compose ps

# Check logs
docker-compose logs -f
```

#### 4. Setup Nginx Reverse Proxy

```bash
# Installa Nginx
sudo apt update
sudo apt install nginx certbot python3-certbot-nginx

# Configura virtual host
sudo nano /etc/nginx/sites-available/orizon-staging
```

**Configurazione Nginx:**
```nginx
# Frontend
server {
    listen 80;
    server_name staging.orizon.syneto.net;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}

# Backend API
server {
    listen 80;
    server_name api.staging.orizon.syneto.net;

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket support
    location /ws {
        proxy_pass http://localhost:8000/ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }
}
```

```bash
# Abilita virtual host
sudo ln -s /etc/nginx/sites-available/orizon-staging /etc/nginx/sites-enabled/

# Test configurazione
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx

# Setup SSL con Let's Encrypt
sudo certbot --nginx -d staging.orizon.syneto.net -d api.staging.orizon.syneto.net
```

#### 5. Setup Systemd Service (Auto-restart)

```bash
# Crea service file
sudo nano /etc/systemd/system/orizon-ztc.service
```

**Service file:**
```ini
[Unit]
Description=Orizon Zero Trust Connect
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/orizon-ztc
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
```

```bash
# Abilita e avvia service
sudo systemctl daemon-reload
sudo systemctl enable orizon-ztc
sudo systemctl start orizon-ztc

# Verifica status
sudo systemctl status orizon-ztc
```

---

## ☸️ Deployment Kubernetes (Production)

### Setup Kubernetes Cluster

#### 1. Prerequisiti Cluster

```bash
# Installa kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# Verifica installazione
kubectl version --client

# Configura kubeconfig
export KUBECONFIG=/path/to/kubeconfig.yaml
```

#### 2. Crea Namespace

```bash
# Crea namespace dedicato
kubectl create namespace orizon-ztc

# Imposta namespace di default
kubectl config set-context --current --namespace=orizon-ztc
```

#### 3. Crea Secrets

```bash
# Secret per database credentials
kubectl create secret generic db-credentials \
  --from-literal=POSTGRES_USER=orizon_prod \
  --from-literal=POSTGRES_PASSWORD=$(openssl rand -base64 32) \
  --from-literal=POSTGRES_DB=orizon_production \
  --from-literal=REDIS_PASSWORD=$(openssl rand -base64 32) \
  --from-literal=MONGODB_USER=orizon_prod \
  --from-literal=MONGODB_PASSWORD=$(openssl rand -base64 32) \
  -n orizon-ztc

# Secret per JWT
kubectl create secret generic jwt-secret \
  --from-literal=JWT_SECRET=$(openssl rand -base64 64) \
  -n orizon-ztc

# Secret per email SMTP (opzionale)
kubectl create secret generic smtp-credentials \
  --from-literal=SMTP_USER=noreply@orizon.syneto.net \
  --from-literal=SMTP_PASSWORD=your-smtp-password \
  -n orizon-ztc
```

#### 4. Crea ConfigMap

```bash
# ConfigMap per configurazione non sensibile
kubectl create configmap orizon-config \
  --from-literal=ENVIRONMENT=production \
  --from-literal=LOG_LEVEL=INFO \
  --from-literal=API_V1_PREFIX=/api/v1 \
  --from-literal=HUB_HOST=hub.orizon.syneto.net \
  --from-literal=SSH_TUNNEL_PORT=2222 \
  --from-literal=HTTPS_TUNNEL_PORT=8443 \
  -n orizon-ztc
```

#### 5. Deploy con Manifests

```bash
# Clone repository
git clone <repository-url>
cd OrizonZeroTrustConnect

# Verifica manifests
cat kubernetes/manifests.yaml

# Apply manifests
kubectl apply -f kubernetes/manifests.yaml

# Verifica deployment
kubectl get all -n orizon-ztc
```

**Output atteso:**
```
NAME                             READY   STATUS    RESTARTS   AGE
pod/backend-api-xxxxxxxxx-xxxxx  1/1     Running   0          2m
pod/frontend-xxxxxxxxx-xxxxx     1/1     Running   0          2m
pod/postgresql-0                 1/1     Running   0          2m
pod/redis-xxxxxxxxx-xxxxx        1/1     Running   0          2m
pod/mongodb-xxxxxxxxx-xxxxx      1/1     Running   0          2m

NAME                      TYPE           CLUSTER-IP      EXTERNAL-IP      PORT(S)
service/backend-service   ClusterIP      10.245.x.x      <none>           8000/TCP
service/frontend-service  LoadBalancer   10.245.x.x      xxx.xxx.xxx.xxx  80:30080/TCP
service/postgresql        ClusterIP      10.245.x.x      <none>           5432/TCP
service/redis             ClusterIP      10.245.x.x      <none>           6379/TCP
service/mongodb           ClusterIP      10.245.x.x      <none>           27017/TCP

NAME                          READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/backend-api   3/3     3            3           2m
deployment.apps/frontend      2/2     2            2           2m
```

#### 6. Setup Ingress (HTTPS)

```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: orizon-ingress
  namespace: orizon-ztc
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/websocket-services: "backend-service"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - orizon.syneto.net
    - api.orizon.syneto.net
    secretName: orizon-tls
  rules:
  # Frontend
  - host: orizon.syneto.net
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend-service
            port:
              number: 80
  # Backend API
  - host: api.orizon.syneto.net
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: backend-service
            port:
              number: 8000
```

```bash
# Apply ingress
kubectl apply -f ingress.yaml

# Verifica ingress
kubectl get ingress -n orizon-ztc

# Ottieni IP esterno
kubectl get ingress orizon-ingress -n orizon-ztc -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
```

#### 7. Setup Horizontal Pod Autoscaler (HPA)

```yaml
# hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: backend-hpa
  namespace: orizon-ztc
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: backend-api
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: frontend-hpa
  namespace: orizon-ztc
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: frontend
  minReplicas: 2
  maxReplicas: 5
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

```bash
# Apply HPA
kubectl apply -f hpa.yaml

# Verifica HPA
kubectl get hpa -n orizon-ztc
```

#### 8. Setup Persistent Storage

```yaml
# persistent-volumes.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgresql-pvc
  namespace: orizon-ztc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 100Gi
  storageClassName: do-block-storage  # DigitalOcean example
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: mongodb-pvc
  namespace: orizon-ztc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 500Gi
  storageClassName: do-block-storage
```

```bash
# Apply PVCs
kubectl apply -f persistent-volumes.yaml

# Verifica PVCs
kubectl get pvc -n orizon-ztc
```

---

## 🌊 Deployment DigitalOcean (Script Automatico)

### Deployment con Script Completo

#### 1. Preparazione Server DigitalOcean

```bash
# Crea droplet DigitalOcean (via CLI o web interface)
# Specs consigliate:
# - CPU: 4 vCPUs
# - RAM: 8GB
# - Disk: 160GB SSD
# - OS: Ubuntu 22.04 LTS

# Connetti al droplet
ssh root@46.101.189.126
```

#### 2. Setup Iniziale

```bash
# Update sistema
apt update && apt upgrade -y

# Installa tools essenziali
apt install -y git curl wget htop nano

# Crea user non-root
adduser orizonai
usermod -aG sudo orizonai

# Setup SSH key per nuovo user
mkdir -p /home/orizonai/.ssh
cp ~/.ssh/authorized_keys /home/orizonai/.ssh/
chown -R orizonai:orizonai /home/orizonai/.ssh
chmod 700 /home/orizonai/.ssh
chmod 600 /home/orizonai/.ssh/authorized_keys

# Switch a nuovo user
su - orizonai
```

#### 3. Deploy Automatico

```bash
# Clone repository
git clone <repository-url> /home/orizonai/OrizonZeroTrustConnect
cd /home/orizonai/OrizonZeroTrustConnect

# Rendi eseguibile lo script di deploy
chmod +x deploy/full_auto_deploy.sh

# Esegui deploy automatico
sudo ./deploy/full_auto_deploy.sh
```

**Lo script full_auto_deploy.sh esegue:**
1. ✅ Installazione Docker & Docker Compose
2. ✅ Setup firewall (ufw)
3. ✅ Creazione .env da template
4. ✅ Build immagini Docker
5. ✅ Avvio stack Docker Compose
6. ✅ Setup Nginx reverse proxy
7. ✅ Configurazione SSL con Let's Encrypt
8. ✅ Setup systemd service per auto-start
9. ✅ Configurazione monitoring (Prometheus + Grafana)
10. ✅ Setup backup automatici

#### 4. Verifica Deployment

```bash
# Check status servizi
sudo systemctl status orizon-backend
sudo systemctl status nginx

# Verifica Docker containers
docker ps

# Test API health
curl http://localhost:8000/health

# Check logs
docker-compose logs -f backend
```

#### 5. Configurazione DNS

```bash
# Aggiungi DNS records al tuo provider DNS:

# A record per frontend
orizon.syneto.net         A    46.101.189.126

# A record per API
api.orizon.syneto.net     A    46.101.189.126

# Verifica DNS propagation
nslookup orizon.syneto.net
nslookup api.orizon.syneto.net
```

---

## ⚙️ Configurazione Avanzata

### SSL/TLS Setup (Production)

#### Let's Encrypt con Certbot

```bash
# Installa Certbot
sudo apt install certbot python3-certbot-nginx

# Ottieni certificato SSL
sudo certbot --nginx \
  -d orizon.syneto.net \
  -d api.orizon.syneto.net \
  --email admin@syneto.net \
  --agree-tos \
  --non-interactive

# Auto-renewal (già configurato da certbot)
sudo certbot renew --dry-run

# Verifica cron job per renewal
sudo crontab -l | grep certbot
```

#### Custom SSL Certificate

```bash
# Se hai un certificato custom
sudo mkdir -p /etc/ssl/orizon
sudo cp your-cert.crt /etc/ssl/orizon/
sudo cp your-key.key /etc/ssl/orizon/
sudo chmod 600 /etc/ssl/orizon/*

# Update Nginx config
sudo nano /etc/nginx/sites-available/orizon

# Aggiungi:
ssl_certificate /etc/ssl/orizon/your-cert.crt;
ssl_certificate_key /etc/ssl/orizon/your-key.key;
```

### Database Optimization

#### PostgreSQL Tuning

```sql
-- Connetti al database
psql -U orizon -d orizon_production

-- Ottimizzazioni performance
ALTER SYSTEM SET shared_buffers = '2GB';
ALTER SYSTEM SET effective_cache_size = '6GB';
ALTER SYSTEM SET maintenance_work_mem = '512MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;
ALTER SYSTEM SET random_page_cost = 1.1;
ALTER SYSTEM SET effective_io_concurrency = 200;
ALTER SYSTEM SET work_mem = '10MB';
ALTER SYSTEM SET min_wal_size = '1GB';
ALTER SYSTEM SET max_wal_size = '4GB';

-- Reload config
SELECT pg_reload_conf();

-- Verifica parametri
SHOW shared_buffers;
SHOW effective_cache_size;
```

#### Redis Configuration

```bash
# Edit redis.conf
sudo nano /etc/redis/redis.conf

# Modifiche consigliate:
maxmemory 2gb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
appendonly yes
appendfsync everysec
```

### Firewall Setup

```bash
# Setup UFW (Ubuntu)
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH
sudo ufw allow 22/tcp

# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow custom ports per tunnel
sudo ufw allow 2222/tcp  # SSH tunnels
sudo ufw allow 8443/tcp  # HTTPS tunnels

# Enable firewall
sudo ufw enable

# Verifica status
sudo ufw status verbose
```

---

## 📊 Monitoraggio e Logging

### Setup Prometheus + Grafana

```bash
# Prometheus è già incluso in docker-compose
# Accedi a: http://your-server:9090

# Import dashboard in Grafana
# 1. Accedi a Grafana: http://your-server:3001
# 2. Login con admin/admin
# 3. Add data source → Prometheus (http://prometheus:9090)
# 4. Import dashboard da file:
#    backend/grafana/dashboards/orizon-dashboard.json
```

### Setup Log Aggregation (Loki)

```yaml
# docker-compose.yml - aggiungi Loki
loki:
  image: grafana/loki:latest
  ports:
    - "3100:3100"
  volumes:
    - ./loki-config.yaml:/etc/loki/local-config.yaml
  command: -config.file=/etc/loki/local-config.yaml

promtail:
  image: grafana/promtail:latest
  volumes:
    - /var/log:/var/log
    - ./promtail-config.yaml:/etc/promtail/config.yml
  command: -config.file=/etc/promtail/config.yml
```

---

## 💾 Backup e Disaster Recovery

### Automated Backups

```bash
# Script backup automatico
sudo nano /opt/orizon-backup.sh
```

**Backup script:**
```bash
#!/bin/bash
BACKUP_DIR="/backup/orizon"
DATE=$(date +%Y%m%d_%H%M%S)

# Backup PostgreSQL
docker exec postgres pg_dump -U orizon orizon_production | gzip > $BACKUP_DIR/postgres_$DATE.sql.gz

# Backup MongoDB
docker exec mongodb mongodump --archive | gzip > $BACKUP_DIR/mongodb_$DATE.archive.gz

# Backup Redis
docker exec redis redis-cli SAVE
docker cp redis:/data/dump.rdb $BACKUP_DIR/redis_$DATE.rdb

# Cleanup old backups (keep 30 days)
find $BACKUP_DIR -name "*.gz" -mtime +30 -delete
find $BACKUP_DIR -name "*.rdb" -mtime +30 -delete

echo "Backup completed: $DATE"
```

```bash
# Rendi eseguibile
sudo chmod +x /opt/orizon-backup.sh

# Aggiungi a crontab (daily backup at 2 AM)
sudo crontab -e
0 2 * * * /opt/orizon-backup.sh >> /var/log/orizon-backup.log 2>&1
```

### Restore da Backup

```bash
# Restore PostgreSQL
gunzip < /backup/orizon/postgres_YYYYMMDD_HHMMSS.sql.gz | \
  docker exec -i postgres psql -U orizon orizon_production

# Restore MongoDB
gunzip < /backup/orizon/mongodb_YYYYMMDD_HHMMSS.archive.gz | \
  docker exec -i mongodb mongorestore --archive

# Restore Redis
docker cp /backup/orizon/redis_YYYYMMDD_HHMMSS.rdb redis:/data/dump.rdb
docker restart redis
```

---

## 🔧 Troubleshooting

### Backend non si avvia

```bash
# Check logs
docker-compose logs backend

# Errori comuni:
# 1. Database connection error
#    → Verifica che PostgreSQL sia running
#    → Check credentials in .env

# 2. Redis connection error
#    → Verifica che Redis sia running
#    → Check REDIS_PASSWORD

# 3. Port already in use
#    → Cambia porta in docker-compose.yml
```

### Frontend build error

```bash
# Check logs
docker-compose logs frontend

# Rebuild immagine
docker-compose build --no-cache frontend
docker-compose up -d frontend
```

### Database migration error

```bash
# Reset migration (ATTENZIONE: perde dati!)
docker-compose exec backend alembic downgrade base
docker-compose exec backend alembic upgrade head
```

### Performance issues

```bash
# Check resource usage
docker stats

# Scale backend replicas (Kubernetes)
kubectl scale deployment backend-api --replicas=5 -n orizon-ztc

# Check database queries slow log
docker exec postgres psql -U orizon -d orizon_production -c "SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;"
```

---

## ✅ Checklist Pre-Production

- [ ] Password forti generate per tutti i servizi
- [ ] JWT_SECRET random di almeno 64 caratteri
- [ ] SSL/TLS configurato correttamente
- [ ] Firewall abilitato e configurato
- [ ] Backup automatici configurati e testati
- [ ] Monitoring (Prometheus + Grafana) funzionante
- [ ] Log aggregation configurata
- [ ] DNS records configurati
- [ ] Health checks funzionanti
- [ ] Auto-scaling configurato (Kubernetes)
- [ ] Disaster recovery plan testato
- [ ] Rate limiting abilitato
- [ ] CORS origins configurati correttamente
- [ ] Database optimized e indexed
- [ ] Retention policy audit logs configurata
- [ ] Security scan eseguito
- [ ] Load testing eseguito
- [ ] Documentation aggiornata

---

**Documento maintained by:** Marco Lorenzi @ Syneto/Orizon
**Last Review:** Gennaio 2025
**Support:** support@orizon.syneto.net
