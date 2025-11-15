"""
Node Provisioning Service
Gestisce QR code generation e script auto-configurazione per nuovi nodi
"""

import qrcode
from io import BytesIO
import base64
import secrets
from typing import Dict, List
from datetime import datetime, timedelta


class NodeProvisioningService:
    """
    Servizio per provisioning semplificato nodi con QR code
    """

    def __init__(self, config):
        self.config = config
        self.hub_host = config.HUB_HOST
        self.api_base_url = f"https://{self.hub_host}/api/v1"
        self.provision_base_url = f"https://{self.hub_host}/provision"

    def generate_provision_token(self, node_id: str, services: List[Dict]) -> str:
        """
        Genera token di provisioning sicuro con expiration

        Args:
            node_id: ID del nodo
            services: Lista servizi da esporre [{port: 22, name: "SSH", protocol: "TCP"}]

        Returns:
            Token JWT-like per provisioning
        """
        import jwt
        from datetime import datetime, timedelta

        payload = {
            "node_id": node_id,
            "services": services,
            "exp": datetime.utcnow() + timedelta(hours=24),  # Token valido 24h
            "iat": datetime.utcnow(),
            "type": "provision"
        }

        token = jwt.encode(
            payload,
            self.config.JWT_SECRET,
            algorithm="HS256"
        )

        return token

    def generate_qr_code(self, node_id: str, provision_token: str) -> str:
        """
        Genera QR code con link provisioning

        Returns:
            Base64 data URL del QR code
        """
        # URL provisioning
        provision_url = f"{self.provision_base_url}/{node_id}?token={provision_token}"

        # Genera QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(provision_url)
        qr.make(fit=True)

        # Crea immagine
        img = qr.make_image(fill_color="black", back_color="white")

        # Convert to base64
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        qr_code_base64 = base64.b64encode(buffered.getvalue()).decode()

        return f"data:image/png;base64,{qr_code_base64}"

    def generate_provision_data(
        self,
        node_id: str,
        node_name: str,
        node_type: str,
        services: List[Dict]
    ) -> Dict:
        """
        Genera tutti i dati necessari per provisioning

        Returns:
            {
                "provision_token": "...",
                "qr_code": "data:image/png;base64,...",
                "provision_url": "https://...",
                "expires_at": "2025-01-08T10:00:00Z"
            }
        """
        # Genera token
        provision_token = self.generate_provision_token(node_id, services)

        # Genera QR code
        qr_code = self.generate_qr_code(node_id, provision_token)

        # URL provisioning
        provision_url = f"{self.provision_base_url}/{node_id}?token={provision_token}"

        # Expires
        expires_at = datetime.utcnow() + timedelta(hours=24)

        return {
            "provision_token": provision_token,
            "qr_code": qr_code,
            "provision_url": provision_url,
            "download_urls": {
                "linux": f"{self.provision_base_url}/{node_id}/script/linux?token={provision_token}",
                "macos": f"{self.provision_base_url}/{node_id}/script/macos?token={provision_token}",
                "windows": f"{self.provision_base_url}/{node_id}/script/windows?token={provision_token}"
            },
            "expires_at": expires_at.isoformat()
        }

    def generate_linux_script(
        self,
        node_id: str,
        node_name: str,
        provision_token: str,
        services: List[Dict]
    ) -> str:
        """
        Genera script bash per Linux
        """
        services_json = str(services).replace("'", '"')

        script = f'''#!/bin/bash
#
# Orizon Zero Trust Connect - Node Setup Script
# Generated: {datetime.utcnow().isoformat()}
# Node: {node_name} ({node_id})
# OS: Linux
#

set -e  # Exit on error

# Colors
RED='\\033[0;31m'
GREEN='\\033[0;32m'
YELLOW='\\033[1;33m'
NC='\\033[0m' # No Color

echo -e "${{GREEN}}=========================================${{NC}}"
echo -e "${{GREEN}}  Orizon ZTC - Node Setup (Linux)${{NC}}"
echo -e "${{GREEN}}=========================================${{NC}}"
echo ""
echo "Node Name: {node_name}"
echo "Node ID: {node_id}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${{RED}}Please run as root (sudo)${{NC}}"
    exit 1
fi

# Detect Linux distribution
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    VERSION=$VERSION_ID
else
    echo -e "${{RED}}Cannot detect Linux distribution${{NC}}"
    exit 1
fi

echo -e "${{YELLOW}}Detected OS: $OS $VERSION${{NC}}"
echo ""

# Install dependencies
echo -e "${{YELLOW}}[1/5] Installing dependencies...${{NC}}"
if [ "$OS" = "ubuntu" ] || [ "$OS" = "debian" ]; then
    apt-get update -qq
    apt-get install -y -qq python3 python3-pip curl wget > /dev/null 2>&1
elif [ "$OS" = "centos" ] || [ "$OS" = "rhel" ] || [ "$OS" = "fedora" ]; then
    yum install -y -q python3 python3-pip curl wget > /dev/null 2>&1
else
    echo -e "${{RED}}Unsupported distribution: $OS${{NC}}"
    exit 1
fi
echo -e "${{GREEN}}✓ Dependencies installed${{NC}}"

# Install Python packages
echo -e "${{YELLOW}}[2/5] Installing Python packages...${{NC}}"
pip3 install -q requests websocket-client psutil > /dev/null 2>&1
echo -e "${{GREEN}}✓ Python packages installed${{NC}}"

# Download Orizon Agent
echo -e "${{YELLOW}}[3/5] Downloading Orizon Agent...${{NC}}"
AGENT_DIR="/opt/orizon"
mkdir -p $AGENT_DIR
curl -sSL {self.api_base_url}/downloads/orizon_agent.py -o $AGENT_DIR/orizon_agent.py
chmod +x $AGENT_DIR/orizon_agent.py
echo -e "${{GREEN}}✓ Agent downloaded${{NC}}"

# Create configuration
echo -e "${{YELLOW}}[4/5] Creating configuration...${{NC}}"
cat > $AGENT_DIR/config.json <<EOF
{{
  "node_id": "{node_id}",
  "node_name": "{node_name}",
  "provision_token": "{provision_token}",
  "hub_url": "https://{self.hub_host}",
  "api_url": "{self.api_base_url}",
  "services": {services_json},
  "auto_start": true,
  "health_check_interval": 30
}}
EOF
echo -e "${{GREEN}}✓ Configuration created${{NC}}"

# Create systemd service
echo -e "${{YELLOW}}[5/5] Setting up systemd service...${{NC}}"
cat > /etc/systemd/system/orizon-agent.service <<EOF
[Unit]
Description=Orizon Zero Trust Connect Agent
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$AGENT_DIR
ExecStart=/usr/bin/python3 $AGENT_DIR/orizon_agent.py -c $AGENT_DIR/config.json
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable orizon-agent.service > /dev/null 2>&1
systemctl start orizon-agent.service

echo -e "${{GREEN}}✓ Systemd service created and started${{NC}}"
echo ""

# Check status
sleep 2
if systemctl is-active --quiet orizon-agent.service; then
    echo -e "${{GREEN}}=========================================${{NC}}"
    echo -e "${{GREEN}}  ✓ Installation Complete!${{NC}}"
    echo -e "${{GREEN}}=========================================${{NC}}"
    echo ""
    echo "Agent Status: Running"
    echo "Config: $AGENT_DIR/config.json"
    echo ""
    echo "Useful commands:"
    echo "  Status:  sudo systemctl status orizon-agent"
    echo "  Logs:    sudo journalctl -u orizon-agent -f"
    echo "  Restart: sudo systemctl restart orizon-agent"
    echo "  Stop:    sudo systemctl stop orizon-agent"
else
    echo -e "${{RED}}✗ Agent failed to start${{NC}}"
    echo "Check logs: sudo journalctl -u orizon-agent -n 50"
    exit 1
fi
'''
        return script

    def generate_macos_script(
        self,
        node_id: str,
        node_name: str,
        provision_token: str,
        services: List[Dict]
    ) -> str:
        """
        Genera script bash per macOS
        """
        services_json = str(services).replace("'", '"')

        script = f'''#!/bin/bash
#
# Orizon Zero Trust Connect - Node Setup Script
# Generated: {datetime.utcnow().isoformat()}
# Node: {node_name} ({node_id})
# OS: macOS
#

set -e  # Exit on error

# Colors
RED='\\033[0;31m'
GREEN='\\033[0;32m'
YELLOW='\\033[1;33m'
NC='\\033[0m' # No Color

echo -e "${{GREEN}}=========================================${{NC}}"
echo -e "${{GREEN}}  Orizon ZTC - Node Setup (macOS)${{NC}}"
echo -e "${{GREEN}}=========================================${{NC}}"
echo ""
echo "Node Name: {node_name}"
echo "Node ID: {node_id}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${{RED}}Please run with sudo${{NC}}"
    exit 1
fi

# Check for Homebrew
echo -e "${{YELLOW}}[1/5] Checking dependencies...${{NC}}"
if ! command -v brew &> /dev/null; then
    echo -e "${{YELLOW}}Homebrew not found. Installing...${{NC}}"
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

# Install Python if needed
if ! command -v python3 &> /dev/null; then
    echo -e "${{YELLOW}}Installing Python3...${{NC}}"
    brew install python3
fi
echo -e "${{GREEN}}✓ Dependencies OK${{NC}}"

# Install Python packages
echo -e "${{YELLOW}}[2/5] Installing Python packages...${{NC}}"
pip3 install -q requests websocket-client psutil > /dev/null 2>&1
echo -e "${{GREEN}}✓ Python packages installed${{NC}}"

# Download Orizon Agent
echo -e "${{YELLOW}}[3/5] Downloading Orizon Agent...${{NC}}"
AGENT_DIR="/usr/local/opt/orizon"
mkdir -p $AGENT_DIR
curl -sSL {self.api_base_url}/downloads/orizon_agent.py -o $AGENT_DIR/orizon_agent.py
chmod +x $AGENT_DIR/orizon_agent.py
echo -e "${{GREEN}}✓ Agent downloaded${{NC}}"

# Create configuration
echo -e "${{YELLOW}}[4/5] Creating configuration...${{NC}}"
cat > $AGENT_DIR/config.json <<EOF
{{
  "node_id": "{node_id}",
  "node_name": "{node_name}",
  "provision_token": "{provision_token}",
  "hub_url": "https://{self.hub_host}",
  "api_url": "{self.api_base_url}",
  "services": {services_json},
  "auto_start": true,
  "health_check_interval": 30
}}
EOF
echo -e "${{GREEN}}✓ Configuration created${{NC}}"

# Create LaunchDaemon
echo -e "${{YELLOW}}[5/5] Setting up LaunchDaemon...${{NC}}"
cat > /Library/LaunchDaemons/com.orizon.agent.plist <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.orizon.agent</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>$AGENT_DIR/orizon_agent.py</string>
        <string>-c</string>
        <string>$AGENT_DIR/config.json</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/var/log/orizon-agent.log</string>
    <key>StandardErrorPath</key>
    <string>/var/log/orizon-agent-error.log</string>
</dict>
</plist>
EOF

launchctl load /Library/LaunchDaemons/com.orizon.agent.plist

echo -e "${{GREEN}}✓ LaunchDaemon created and loaded${{NC}}"
echo ""

# Check status
sleep 2
if launchctl list | grep -q com.orizon.agent; then
    echo -e "${{GREEN}}=========================================${{NC}}"
    echo -e "${{GREEN}}  ✓ Installation Complete!${{NC}}"
    echo -e "${{GREEN}}=========================================${{NC}}"
    echo ""
    echo "Agent Status: Running"
    echo "Config: $AGENT_DIR/config.json"
    echo ""
    echo "Useful commands:"
    echo "  Status:  sudo launchctl list | grep orizon"
    echo "  Logs:    tail -f /var/log/orizon-agent.log"
    echo "  Restart: sudo launchctl kickstart -k system/com.orizon.agent"
    echo "  Stop:    sudo launchctl unload /Library/LaunchDaemons/com.orizon.agent.plist"
else
    echo -e "${{RED}}✗ Agent failed to start${{NC}}"
    echo "Check logs: tail -f /var/log/orizon-agent-error.log"
    exit 1
fi
'''
        return script

    def generate_windows_script(
        self,
        node_id: str,
        node_name: str,
        provision_token: str,
        services: List[Dict]
    ) -> str:
        """
        Genera script PowerShell per Windows
        """
        services_json = str(services).replace("'", '"')

        script = f'''# Orizon Zero Trust Connect - Node Setup Script
# Generated: {datetime.utcnow().isoformat()}
# Node: {node_name} ({node_id})
# OS: Windows
#
# Run as Administrator!

$ErrorActionPreference = "Stop"

Write-Host "=========================================" -ForegroundColor Green
Write-Host "  Orizon ZTC - Node Setup (Windows)" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Node Name: {node_name}"
Write-Host "Node ID: {node_id}"
Write-Host ""

# Check if running as Administrator
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
$isAdmin = $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {{
    Write-Host "ERROR: Please run as Administrator!" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}}

# Check Python installation
Write-Host "[1/5] Checking Python..." -ForegroundColor Yellow
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {{
    Write-Host "Python not found. Installing Python 3..." -ForegroundColor Yellow

    # Download Python installer
    $pythonUrl = "https://www.python.org/ftp/python/3.11.0/python-3.11.0-amd64.exe"
    $pythonInstaller = "$env:TEMP\\python-installer.exe"

    Invoke-WebRequest -Uri $pythonUrl -OutFile $pythonInstaller

    # Install Python
    Start-Process -FilePath $pythonInstaller -Args "/quiet InstallAllUsers=1 PrependPath=1" -Wait

    # Refresh PATH
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

    Remove-Item $pythonInstaller
}}
Write-Host "✓ Python OK" -ForegroundColor Green

# Install Python packages
Write-Host "[2/5] Installing Python packages..." -ForegroundColor Yellow
python -m pip install --quiet --upgrade pip
python -m pip install --quiet requests websocket-client psutil
Write-Host "✓ Python packages installed" -ForegroundColor Green

# Download Orizon Agent
Write-Host "[3/5] Downloading Orizon Agent..." -ForegroundColor Yellow
$agentDir = "C:\\Program Files\\Orizon"
New-Item -ItemType Directory -Force -Path $agentDir | Out-Null

$agentUrl = "{self.api_base_url}/downloads/orizon_agent.py"
$agentPath = "$agentDir\\orizon_agent.py"
Invoke-WebRequest -Uri $agentUrl -OutFile $agentPath
Write-Host "✓ Agent downloaded" -ForegroundColor Green

# Create configuration
Write-Host "[4/5] Creating configuration..." -ForegroundColor Yellow
$config = @"
{{
  "node_id": "{node_id}",
  "node_name": "{node_name}",
  "provision_token": "{provision_token}",
  "hub_url": "https://{self.hub_host}",
  "api_url": "{self.api_base_url}",
  "services": {services_json},
  "auto_start": true,
  "health_check_interval": 30
}}
"@
$config | Out-File -FilePath "$agentDir\\config.json" -Encoding UTF8
Write-Host "✓ Configuration created" -ForegroundColor Green

# Create Windows Service
Write-Host "[5/5] Creating Windows Service..." -ForegroundColor Yellow

# Create service wrapper script
$serviceScript = @"
import sys
import os
import servicemanager
import win32serviceutil
import win32service
import win32event

# Add agent directory to path
sys.path.insert(0, r'$agentDir')

class OrizonAgentService(win32serviceutil.ServiceFramework):
    _svc_name_ = 'OrizonAgent'
    _svc_display_name_ = 'Orizon Zero Trust Connect Agent'
    _svc_description_ = 'Connects this node to Orizon ZTC hub'

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)

    def SvcDoRun(self):
        os.chdir(r'$agentDir')
        exec(open('orizon_agent.py').read())

if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(OrizonAgentService)
"@
$serviceScript | Out-File -FilePath "$agentDir\\service_wrapper.py" -Encoding UTF8

# Install service dependencies
python -m pip install --quiet pywin32

# Install service
python "$agentDir\\service_wrapper.py" install

# Start service
Start-Service OrizonAgent

Write-Host "✓ Windows Service created and started" -ForegroundColor Green
Write-Host ""

# Check status
Start-Sleep -Seconds 2
$service = Get-Service -Name OrizonAgent -ErrorAction SilentlyContinue
if ($service -and $service.Status -eq 'Running') {{
    Write-Host "=========================================" -ForegroundColor Green
    Write-Host "  ✓ Installation Complete!" -ForegroundColor Green
    Write-Host "=========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Agent Status: Running"
    Write-Host "Config: $agentDir\\config.json"
    Write-Host ""
    Write-Host "Useful commands:"
    Write-Host "  Status:  Get-Service OrizonAgent"
    Write-Host "  Logs:    Get-EventLog -LogName Application -Source OrizonAgent -Newest 50"
    Write-Host "  Restart: Restart-Service OrizonAgent"
    Write-Host "  Stop:    Stop-Service OrizonAgent"
}} else {{
    Write-Host "✗ Agent failed to start" -ForegroundColor Red
    Write-Host "Check Event Viewer > Application logs"
    Read-Host "Press Enter to exit"
    exit 1
}}

Read-Host "Press Enter to exit"
'''
        return script

    def get_script_content_type(self, os_type: str) -> tuple:
        """
        Restituisce content type e filename per script
        """
        if os_type in ["linux", "macos"]:
            return "text/x-shellscript", "install-orizon-agent.sh"
        elif os_type == "windows":
            return "application/x-powershell", "install-orizon-agent.ps1"
        else:
            raise ValueError(f"Unknown OS type: {{os_type}}")
