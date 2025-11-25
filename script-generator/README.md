# Orizon Script Generator Service

Node.js/TypeScript microservice for generating agent installation scripts.

## Features

- Generates installation scripts for Linux, macOS, and Windows
- Uses Handlebars templates for customization
- RESTful API for script generation
- Automatic port assignment
- SSH tunnel configuration

## API Endpoints

### Health Check
```
GET /health
```

### Generate Script for Single OS
```
POST /api/scripts/generate/:osType
Content-Type: application/json

{
  "nodeId": "node-uuid",
  "nodeName": "my-server",
  "agentToken": "agt_xxx",
  "hubHost": "139.59.149.48",
  "hubSshPort": 2222,
  "tunnelType": "SSH",
  "apiBaseUrl": "http://139.59.149.48/api/v1",
  "applicationPorts": {
    "TERMINAL": { "local": 22, "remote": 10000 },
    "WEB_SERVER": { "local": 80, "remote": 10001 }
  }
}
```

### Generate Scripts for All Platforms
```
POST /api/scripts/generate-all
Content-Type: application/json

{
  "nodeId": "node-uuid",
  "nodeName": "my-server",
  "agentToken": "agt_xxx",
  "hubHost": "139.59.149.48",
  "hubSshPort": 2222,
  "tunnelType": "SSH",
  "apiBaseUrl": "http://139.59.149.48/api/v1",
  "applicationPorts": {
    "TERMINAL": { "local": 22, "remote": 10000 }
  }
}
```

## Development

```bash
# Install dependencies
npm install

# Run in development mode
npm run dev

# Build TypeScript
npm run build

# Run production build
npm start
```

## Docker

```bash
# Build image
docker build -t orizon/script-generator:2.0.1 .

# Run container
docker run -p 3001:3001 \
  -e PORT=3001 \
  -e LOG_LEVEL=info \
  orizon/script-generator:2.0.1
```

## Environment Variables

- `PORT` - Service port (default: 3001)
- `LOG_LEVEL` - Logging level (default: info)
- `BACKEND_API_URL` - Backend API URL (optional)

## Templates

Templates are located in `src/templates/`:
- `install_linux.sh.hbs` - Linux installation script
- `install_macos.sh.hbs` - macOS installation script
- `install_windows.ps1.hbs` - Windows PowerShell script

## Integration

This service is called by the FastAPI backend when a node is created.
The backend endpoint `/api/v1/nodes/{node_id}/provision` calls this service to generate scripts.
