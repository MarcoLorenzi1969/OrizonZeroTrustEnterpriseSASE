# Orizon Zero Trust Connect - Nginx Configuration

This directory contains the Nginx reverse proxy configuration for Orizon ZTNA hubs.

## Directory Structure

```
nginx/
├── orizon.conf         # Main Nginx site configuration
├── conf.d/             # Additional configuration snippets
│   └── (custom configs)
├── ssl/
│   └── generate-ssl.sh # SSL certificate generator script
└── README.md           # This file
```

## Quick Installation

### 1. Install Nginx

```bash
sudo apt update
sudo apt install nginx -y
sudo systemctl enable nginx
```

### 2. Generate SSL Certificate

```bash
# Make script executable
chmod +x ssl/generate-ssl.sh

# Generate self-signed certificate (replace with your IP/domain)
sudo ./ssl/generate-ssl.sh 139.59.149.48
```

### 3. Install Configuration

```bash
# Copy configuration (replace ${HUB_IP} first!)
sed 's/${HUB_IP}/139.59.149.48/g' orizon.conf | sudo tee /etc/nginx/sites-available/orizon

# Enable site
sudo ln -sf /etc/nginx/sites-available/orizon /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test and reload
sudo nginx -t
sudo systemctl reload nginx
```

### 4. Deploy Frontend

```bash
# Copy built frontend to web root
sudo rsync -av /opt/orizon-ztc/frontend/dist/ /var/www/html/
sudo chown -R www-data:www-data /var/www/html
```

## Configuration Details

### Ports

| Port | Protocol | Purpose |
|------|----------|---------|
| 80 | HTTP | Redirect to HTTPS |
| 443 | HTTPS | Main application |

### Proxy Locations

| Location | Backend | Description |
|----------|---------|-------------|
| `/` | Static files | React SPA |
| `/api/` | `:8000/api/` | FastAPI backend |
| `/ws/` | `:8000/ws/` | WebSocket terminal |
| `/health` | `:8000/health` | Health check |
| `/docs` | `:8000/docs` | Swagger UI |
| `/redoc` | `:8000/redoc` | ReDoc |

### SSL Configuration

- **Protocols**: TLSv1.2, TLSv1.3
- **Ciphers**: Modern ECDHE suites
- **Session Cache**: 10MB shared
- **Session Timeout**: 1 day

## Production Recommendations

### Use Let's Encrypt

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

### Enable Caching

Edit `orizon.conf` and change the assets section:

```nginx
location /assets/ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

### Enable Gzip Compression

Add to `/etc/nginx/nginx.conf` in http block:

```nginx
gzip on;
gzip_vary on;
gzip_min_length 1024;
gzip_types text/plain text/css application/json application/javascript text/xml application/xml;
```

### Rate Limiting

Add to `orizon.conf`:

```nginx
# In http block (nginx.conf)
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

# In location /api/
limit_req zone=api burst=20 nodelay;
```

## Troubleshooting

### Check Nginx Status

```bash
sudo systemctl status nginx
sudo nginx -t
```

### View Logs

```bash
# Access log
sudo tail -f /var/log/nginx/orizon_access.log

# Error log
sudo tail -f /var/log/nginx/orizon_error.log
```

### Common Issues

1. **502 Bad Gateway**: Backend not running
   ```bash
   docker compose ps backend
   docker compose logs backend
   ```

2. **SSL Certificate Error**: Regenerate certificate
   ```bash
   sudo ./ssl/generate-ssl.sh YOUR_IP
   sudo systemctl reload nginx
   ```

3. **Permission Denied**: Fix file permissions
   ```bash
   sudo chown -R www-data:www-data /var/www/html
   sudo chmod -R 755 /var/www/html
   ```

## Hub-Specific Configurations

### HUB 1 (139.59.149.48)

```bash
sed 's/${HUB_IP}/139.59.149.48/g' orizon.conf | sudo tee /etc/nginx/sites-available/orizon
```

### HUB 2 (68.183.219.222)

```bash
sed 's/${HUB_IP}/68.183.219.222/g' orizon.conf | sudo tee /etc/nginx/sites-available/orizon
```

## Version

- **Nginx**: 1.24+
- **Configuration Version**: 3.0.1
- **Last Updated**: 2025-12-07
