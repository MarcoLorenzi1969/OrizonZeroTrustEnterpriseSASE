# Orizon SSH Tunnel Server
# For: Marco @ Syneto/Orizon
# Dedicated SSH server for edge node reverse tunnels

FROM alpine:3.19

# Install OpenSSH server and netcat for healthcheck
RUN apk add --no-cache \
    openssh-server \
    openssh-client \
    bash \
    curl \
    netcat-openbsd \
    && rm -rf /var/cache/apk/*

# Create SSH directory
RUN mkdir -p /etc/ssh /root/.ssh /var/run/sshd

# Generate host keys
RUN ssh-keygen -A

# Configure SSH server for tunneling
RUN cat > /etc/ssh/sshd_config << 'EOF'
# Orizon SSH Tunnel Server Configuration

# Network
Port 2222
ListenAddress 0.0.0.0
Protocol 2

# Authentication
PermitRootLogin no
PubkeyAuthentication yes
PasswordAuthentication no
PermitEmptyPasswords no
ChallengeResponseAuthentication no

# Authorized keys location (supports dynamic users)
AuthorizedKeysFile /etc/ssh/authorized_keys/%u

# Security
X11Forwarding no
PrintMotd no
UseDNS no

# Tunneling - CRITICAL for reverse tunnels
AllowTcpForwarding yes
GatewayPorts yes
PermitTunnel yes
ClientAliveInterval 30
ClientAliveCountMax 3

# Restrict to tunnel-only (no shell, but keep connection alive)
Match User *
    ForceCommand sleep infinity
    AllowTcpForwarding yes
    PermitTTY no
    X11Forwarding no
    PermitOpen any

# Accept any user (dynamic tunnel users)
Match User *
    AuthorizedKeysFile /etc/ssh/authorized_keys/%u
EOF

# Create directories for authorized keys
RUN mkdir -p /etc/ssh/authorized_keys && chmod 755 /etc/ssh/authorized_keys

# Create entrypoint script
RUN cat > /entrypoint.sh << 'ENTRY'
#!/bin/bash
set -e

echo "=== Orizon SSH Tunnel Server ==="

# Ensure proper permissions
chmod 755 /etc/ssh/authorized_keys
chmod 600 /etc/ssh/authorized_keys/* 2>/dev/null || true

# Create system users for each authorized key file
for keyfile in /etc/ssh/authorized_keys/*; do
    if [[ -f "$keyfile" ]]; then
        username=$(basename "$keyfile")
        if ! id "$username" &>/dev/null; then
            # Create user with nologin shell
            adduser -D -s /sbin/nologin -H "$username" 2>/dev/null || true
            # Unlock account (required for SSH login)
            passwd -u "$username" 2>/dev/null || true
            echo "Created tunnel user: $username"
        fi
    fi
done

echo "Starting SSH server on port 2222..."

# Start SSH server in foreground
exec /usr/sbin/sshd -D -e
ENTRY

RUN chmod +x /entrypoint.sh

# Expose SSH tunnel port
EXPOSE 2222

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD nc -z localhost 2222 || exit 1

ENTRYPOINT ["/entrypoint.sh"]
