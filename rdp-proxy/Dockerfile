# Orizon RDP Proxy Server
# WebSocket-to-RDP bridge for web-based Remote Desktop access

FROM node:20-slim

LABEL maintainer="Marco @ Syneto/Orizon"
LABEL description="Orizon RDP Proxy - WebSocket to RDP bridge"
LABEL version="1.0.0"

# Install build dependencies for node-rdpjs-2 (requires native modules)
RUN apt-get update && apt-get install -y \
    python3 \
    make \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy package files
COPY package.json ./

# Install dependencies
RUN npm install --production

# Copy source code
COPY src/ ./src/

# Expose WebSocket port
EXPOSE 8766

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8766/health || exit 1

# Run as non-root user
RUN useradd -r -u 1001 rdpproxy
USER rdpproxy

# Start server
CMD ["node", "src/index.js"]
