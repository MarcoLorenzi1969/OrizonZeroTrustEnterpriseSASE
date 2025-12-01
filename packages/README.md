# Orizon Zero Trust Connect - Installation Packages

Enterprise-grade installation packages for connecting edge servers to the Orizon Hub infrastructure.

## Quick Start

### Download and Install

| Platform | Command |
|----------|---------|
| **Debian/Ubuntu** | `sudo dpkg -i orizon-agent_2.1.0_all.deb && sudo orizon-setup` |
| **RedHat/Fedora** | `sudo rpm -i orizon-agent-2.1.0-1.noarch.rpm && sudo orizon-setup` |
| **macOS** | `sudo bash orizon-installer.sh` |
| **Windows** | Run `orizon-installer.ps1` as Administrator |

## Package Contents

### What Gets Installed

| Component | Purpose | Platform |
|-----------|---------|----------|
| **autossh** | Maintains persistent SSH connections, auto-reconnects | Linux, macOS |
| **OpenSSH** | SSH client/server for encrypted connections | All |
| **NSSM** | Windows service manager for tunnel services | Windows |
| **nginx** (optional) | Status page web server | Windows |

### What Gets Configured

1. **SSH Reverse Tunnels** (3 per Hub server):
   - **System Tunnel**: Hub collects metrics from edge server
   - **Terminal Tunnel**: Authorized users access terminal/shell
   - **HTTPS Tunnel**: Access to local web services

2. **Services**:
   - Linux: systemd services (`orizon-tunnel-hub1.service`)
   - macOS: LaunchDaemons (`one.orizon.tunnel-hub1.plist`)
   - Windows: Windows Services (`OrizonTunnelHub1`)

3. **Watchdog Service**: Monitors and restarts failed tunnels

## Directory Structure

```
packages/
├── build/
│   └── build-packages.sh      # Build script for all platforms
├── linux/
│   ├── common/
│   │   └── orizon-agent-install.sh   # Main Linux installer
│   ├── debian/
│   │   ├── DEBIAN/
│   │   │   ├── control        # Package metadata
│   │   │   ├── postinst       # Post-installation script
│   │   │   └── prerm          # Pre-removal script
│   │   └── opt/orizon/
│   │       └── orizon-setup   # Interactive setup wizard
│   └── redhat/
│       └── orizon-agent.spec  # RPM spec file
├── macos/
│   └── orizon-installer.sh    # macOS installer script
├── windows/
│   └── orizon-installer.ps1   # Windows PowerShell installer
└── README.md                  # This file
```

## Building Packages

```bash
# Build all packages
./build/build-packages.sh all

# Build specific platform
./build/build-packages.sh debian
./build/build-packages.sh redhat
./build/build-packages.sh macos
./build/build-packages.sh windows

# Output directory
ls -la dist/
```

## Installation Instructions

### Linux (Debian/Ubuntu)

```bash
# Download package
wget https://your-hub.orizon.one/downloads/orizon-agent_2.1.0_all.deb

# Install package
sudo dpkg -i orizon-agent_2.1.0_all.deb

# Run setup wizard
sudo orizon-setup
```

The wizard will prompt for:
1. **Node ID**: From Orizon Hub dashboard
2. **Hub Servers**: `hub1.orizon.one:2222,hub2.orizon.one:2222`
3. **Node Name**: Friendly name (default: hostname)

### Linux (RedHat/Fedora/CentOS)

```bash
# Download package
wget https://your-hub.orizon.one/downloads/orizon-agent-2.1.0-1.noarch.rpm

# Install package
sudo rpm -i orizon-agent-2.1.0-1.noarch.rpm

# Or with yum/dnf
sudo yum install orizon-agent-2.1.0-1.noarch.rpm

# Run setup wizard
sudo orizon-setup
```

### macOS

```bash
# Download installer
curl -O https://your-hub.orizon.one/downloads/orizon-installer.sh

# Run installer (requires sudo)
sudo bash orizon-installer.sh
```

**Requirements**:
- macOS 12+ (Monterey, Ventura, Sonoma)
- Homebrew (will be installed if missing)

### Windows

1. Download `orizon-installer.ps1`
2. Right-click PowerShell → "Run as Administrator"
3. Navigate to download location
4. Run: `.\orizon-installer.ps1`

**Requirements**:
- Windows 10/11 or Windows Server 2019/2022/2025
- PowerShell 5.1 or later
- Administrator privileges

## Post-Installation

### Verify Services

**Linux**:
```bash
systemctl status orizon-tunnel-hub*
journalctl -u orizon-tunnel-hub1 -f
```

**macOS**:
```bash
launchctl list | grep orizon
tail -f /var/log/orizon/tunnel-hub1.log
```

**Windows**:
```powershell
Get-Service Orizon*
Get-Content C:\ProgramData\Orizon\logs\tunnel-hub1.log -Tail 50
```

### Register SSH Key

After installation, copy the displayed public key to:
1. Orizon Hub Dashboard
2. Navigate to: Nodes → [Your Node] → Settings → SSH Keys
3. Click "Add Key" and paste the public key

### Verify Connection

1. Go to Orizon Hub Dashboard
2. Navigate to Nodes
3. Your node should show "Online" status

## Uninstallation

**Linux**:
```bash
# Debian/Ubuntu
sudo dpkg -r orizon-agent

# RedHat/Fedora
sudo rpm -e orizon-agent

# Remove data (optional)
sudo rm -rf /opt/orizon /etc/orizon /var/log/orizon
```

**macOS**:
```bash
sudo bash orizon-installer.sh --uninstall
```

**Windows**:
```powershell
.\orizon-installer.ps1 -Uninstall
```

## Security

- **Encryption**: All traffic encrypted via SSH (Ed25519 keys)
- **No Inbound Ports**: Only outbound connections to Hub
- **Key Security**: SSH keys stored with restricted permissions (600/700)
- **Service Isolation**: Services run with minimal required privileges

## Troubleshooting

### Connection Issues

1. **Check Hub connectivity**:
   ```bash
   nc -zv hub.orizon.one 2222
   ```

2. **Verify SSH key registered**:
   Check Hub dashboard → Nodes → [Your Node] → SSH Keys

3. **Check service logs**:
   ```bash
   # Linux
   journalctl -u orizon-tunnel-hub1 -f

   # macOS
   tail -f /var/log/orizon/tunnel-hub1.log

   # Windows
   Get-Content C:\ProgramData\Orizon\logs\tunnel-hub1.log -Tail 100
   ```

### Service Not Starting

1. **Check SSH key permissions**:
   ```bash
   ls -la /opt/orizon/.ssh/
   # Should be: drwx------ (700) for directory, -rw------- (600) for keys
   ```

2. **Test SSH manually**:
   ```bash
   ssh -v -i /opt/orizon/.ssh/id_ed25519 -p 2222 -N \
       -R 9999:localhost:22 NODE_ID@hub.orizon.one
   ```

### Regenerate SSH Keys

```bash
# Linux/macOS
sudo rm /opt/orizon/.ssh/id_ed25519*
sudo orizon-setup  # Will regenerate keys

# Windows
Remove-Item C:\ProgramData\Orizon\.ssh\id_ed25519*
.\orizon-installer.ps1  # Will regenerate keys
```

## Support

- **Documentation**: https://docs.orizon.one
- **Support Email**: support@orizon.one
- **Hub Dashboard**: https://your-hub.orizon.one

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.1.0 | Dec 2024 | Multi-hub support, HTTPS tunnel, improved documentation |
| 2.0.0 | Nov 2024 | Complete rewrite, Windows support, watchdog service |

---

*Orizon Zero Trust Connect - Enterprise Security Made Simple*
