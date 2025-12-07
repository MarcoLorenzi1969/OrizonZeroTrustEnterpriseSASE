# Quick Start Guide / Guida Rapida

**Orizon Zero Trust Enterprise SASE v3.0.1**

---

## English

### Prerequisites
- Docker 24.x + Docker Compose v2
- Node.js 18+ (for frontend development)
- Python 3.11+ (for backend development)
- Public IP for hub deployment

### 1. Clone & Configure
```bash
git clone https://github.com/MarcoLorenzi1969/OrizonZeroTrustEnterpriseSASE.git
cd OrizonZeroTrustEnterpriseSASE
cp .env.example .env
# Edit .env with your settings
```

### 2. Start Services
```bash
docker compose up -d
```

### 3. Install Nginx (Production)
```bash
cd nginx
chmod +x install.sh
sudo ./install.sh YOUR_SERVER_IP
```

### 4. Build & Deploy Frontend
```bash
cd frontend
npm install
npm run build
sudo rsync -av dist/ /var/www/html/
```

### 5. Access
- **Dashboard**: https://YOUR_SERVER_IP
- **API Docs**: https://YOUR_SERVER_IP/docs
- **Default Login**: marco@syneto.eu / Syneto2601AA

### 6. Register Edge Node
1. Go to "Edge Provisioning" page
2. Fill node details (name, OS, applications)
3. Download and run the generated script on the edge

---

## Italiano

### Prerequisiti
- Docker 24.x + Docker Compose v2
- Node.js 18+ (per sviluppo frontend)
- Python 3.11+ (per sviluppo backend)
- IP pubblico per deployment hub

### 1. Clone e Configurazione
```bash
git clone https://github.com/MarcoLorenzi1969/OrizonZeroTrustEnterpriseSASE.git
cd OrizonZeroTrustEnterpriseSASE
cp .env.example .env
# Modifica .env con le tue impostazioni
```

### 2. Avvia Servizi
```bash
docker compose up -d
```

### 3. Installa Nginx (Produzione)
```bash
cd nginx
chmod +x install.sh
sudo ./install.sh TUO_IP_SERVER
```

### 4. Build e Deploy Frontend
```bash
cd frontend
npm install
npm run build
sudo rsync -av dist/ /var/www/html/
```

### 5. Accesso
- **Dashboard**: https://TUO_IP_SERVER
- **Documentazione API**: https://TUO_IP_SERVER/docs
- **Login Predefinito**: marco@syneto.eu / Syneto2601AA

### 6. Registra Nodo Edge
1. Vai alla pagina "Edge Provisioning"
2. Compila i dettagli del nodo (nome, OS, applicazioni)
3. Scarica ed esegui lo script generato sull'edge

---

## Services / Servizi

| Service | Port | Description |
|---------|------|-------------|
| Backend API | 8000 | FastAPI application |
| PostgreSQL | 5432 | Primary database |
| Redis | 6379 | Cache & sessions |
| MongoDB | 27017 | Audit logs |
| SSH Tunnel | 2222 | Reverse tunnels |
| Script Generator | 3000 | Provisioning scripts |
| Nginx | 80/443 | Reverse proxy |

---

## Troubleshooting

### Backend not starting
```bash
docker compose logs backend
# Check database connection and JWT_SECRET_KEY
```

### Frontend 502 error
```bash
sudo nginx -t
sudo systemctl status nginx
docker compose ps backend
```

### Edge not connecting
```bash
# On edge node
systemctl status orizon-tunnel
journalctl -u orizon-tunnel -n 50
```

---

© 2025 Syneto / Orizon
