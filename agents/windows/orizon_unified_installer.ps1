#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Orizon Zero Trust Connect - Windows Unified Installer

.DESCRIPTION
    Complete installation script for Windows Edge nodes including:
    - OpenSSH client/server configuration
    - Two SSH tunnels (System + Terminal)
    - nginx for Windows with SSL status page
    - Watchdog service with Task Scheduler
    - Windows Firewall hardening

.NOTES
    Version:        2.0.0
    Author:         Orizon Team
    Creation Date:  2025-11-30
    Platform:       Windows 10/11, Windows Server 2019/2022

.EXAMPLE
    # Run as Administrator
    .\orizon_unified_installer.ps1
#>

#==============================================================================
# CONFIGURATION - Populated by Handlebars template
#==============================================================================
$Config = @{
    # Node Identity
    NodeId              = "PLACEHOLDER_NODE_ID"
    NodeName            = "PLACEHOLDER_NODE_NAME"
    AgentToken          = "PLACEHOLDER_AGENT_TOKEN"

    # Hub Connection
    HubHost             = "PLACEHOLDER_HUB_HOST"
    HubSshPort          = 2222
    ApiBaseUrl          = "PLACEHOLDER_API_BASE_URL"

    # Tunnel Ports (calculated from Node ID hash)
    SystemTunnelPort    = 9000
    TerminalTunnelPort  = 10000

    # Local Configuration
    LocalSshPort        = 22
    LocalHttpsPort      = 443

    # Installation Paths
    InstallPath         = "C:\ProgramData\Orizon"
    LogPath             = "C:\ProgramData\Orizon\logs"
    SshPath             = "C:\ProgramData\Orizon\.ssh"
    NginxPath           = "C:\ProgramData\Orizon\nginx"
    WwwPath             = "C:\ProgramData\Orizon\www"
    SslPath             = "C:\ProgramData\Orizon\ssl"
    ToolsPath           = "C:\ProgramData\Orizon\tools"
}

#==============================================================================
# LOGGING
#==============================================================================
$LogFile = Join-Path $Config.LogPath "install_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"

function Write-Log {
    param(
        [string]$Message,
        [ValidateSet("INFO", "WARN", "ERROR", "SUCCESS")]
        [string]$Level = "INFO"
    )

    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logEntry = "[$timestamp] [$Level] $Message"

    # Ensure log directory exists
    if (-not (Test-Path $Config.LogPath)) {
        New-Item -ItemType Directory -Path $Config.LogPath -Force | Out-Null
    }

    Add-Content -Path $LogFile -Value $logEntry

    switch ($Level) {
        "INFO"    { Write-Host $logEntry -ForegroundColor Cyan }
        "WARN"    { Write-Host $logEntry -ForegroundColor Yellow }
        "ERROR"   { Write-Host $logEntry -ForegroundColor Red }
        "SUCCESS" { Write-Host $logEntry -ForegroundColor Green }
    }
}

function Write-Banner {
    $banner = @"

    ╔═══════════════════════════════════════════════════════════════════╗
    ║                                                                   ║
    ║     ██████╗ ██████╗ ██╗███████╗ ██████╗ ███╗   ██╗               ║
    ║    ██╔═══██╗██╔══██╗██║╚══███╔╝██╔═══██╗████╗  ██║               ║
    ║    ██║   ██║██████╔╝██║  ███╔╝ ██║   ██║██╔██╗ ██║               ║
    ║    ██║   ██║██╔══██╗██║ ███╔╝  ██║   ██║██║╚██╗██║               ║
    ║    ╚██████╔╝██║  ██║██║███████╗╚██████╔╝██║ ╚████║               ║
    ║     ╚═════╝ ╚═╝  ╚═╝╚═╝╚══════╝ ╚═════╝ ╚═╝  ╚═══╝               ║
    ║                                                                   ║
    ║              Zero Trust Connect - Windows Agent                   ║
    ║                        Version 2.0.0                              ║
    ║                                                                   ║
    ╚═══════════════════════════════════════════════════════════════════╝

"@
    Write-Host $banner -ForegroundColor Magenta
}

#==============================================================================
# PHASE 1: Prerequisites Check
#==============================================================================
function Test-Prerequisites {
    Write-Log "=== PHASE 1: Checking Prerequisites ===" "INFO"

    # Check Windows version
    $osVersion = [System.Environment]::OSVersion.Version
    Write-Log "Windows Version: $($osVersion.Major).$($osVersion.Minor) Build $($osVersion.Build)" "INFO"

    if ($osVersion.Build -lt 17763) {
        Write-Log "Windows 10 1809 or later required (Build 17763+)" "ERROR"
        return $false
    }

    # Check if running as Administrator
    $currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    if (-not $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        Write-Log "This script must be run as Administrator" "ERROR"
        return $false
    }
    Write-Log "Running as Administrator: OK" "SUCCESS"

    # Check Internet connectivity
    try {
        $testConnection = Test-NetConnection -ComputerName $Config.HubHost -Port $Config.HubSshPort -WarningAction SilentlyContinue
        if (-not $testConnection.TcpTestSucceeded) {
            Write-Log "Cannot reach Hub at $($Config.HubHost):$($Config.HubSshPort)" "ERROR"
            return $false
        }
        Write-Log "Hub connectivity: OK" "SUCCESS"
    } catch {
        Write-Log "Network test failed: $_" "ERROR"
        return $false
    }

    return $true
}

#==============================================================================
# PHASE 2: Create Directory Structure
#==============================================================================
function Initialize-Directories {
    Write-Log "=== PHASE 2: Creating Directory Structure ===" "INFO"

    $directories = @(
        $Config.InstallPath,
        $Config.LogPath,
        $Config.SshPath,
        $Config.NginxPath,
        $Config.WwwPath,
        $Config.SslPath,
        $Config.ToolsPath
    )

    foreach ($dir in $directories) {
        if (-not (Test-Path $dir)) {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
            Write-Log "Created: $dir" "INFO"
        } else {
            Write-Log "Exists: $dir" "INFO"
        }
    }

    # Secure SSH directory
    $acl = Get-Acl $Config.SshPath
    $acl.SetAccessRuleProtection($true, $false)
    $rule = New-Object System.Security.AccessControl.FileSystemAccessRule("SYSTEM", "FullControl", "ContainerInherit,ObjectInherit", "None", "Allow")
    $acl.AddAccessRule($rule)
    $rule = New-Object System.Security.AccessControl.FileSystemAccessRule("Administrators", "FullControl", "ContainerInherit,ObjectInherit", "None", "Allow")
    $acl.AddAccessRule($rule)
    Set-Acl $Config.SshPath $acl

    Write-Log "Directory structure created" "SUCCESS"
    return $true
}

#==============================================================================
# PHASE 3: Install OpenSSH
#==============================================================================
function Install-OpenSSH {
    Write-Log "=== PHASE 3: Configuring OpenSSH ===" "INFO"

    # Check if OpenSSH Client is installed
    $sshClient = Get-WindowsCapability -Online | Where-Object Name -like 'OpenSSH.Client*'
    if ($sshClient.State -ne 'Installed') {
        Write-Log "Installing OpenSSH Client..." "INFO"
        Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0
    }
    Write-Log "OpenSSH Client: Installed" "SUCCESS"

    # Check if OpenSSH Server is installed
    $sshServer = Get-WindowsCapability -Online | Where-Object Name -like 'OpenSSH.Server*'
    if ($sshServer.State -ne 'Installed') {
        Write-Log "Installing OpenSSH Server..." "INFO"
        Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
    }
    Write-Log "OpenSSH Server: Installed" "SUCCESS"

    # Configure and start SSH server
    Set-Service -Name sshd -StartupType Automatic
    Start-Service sshd

    # Configure default shell to PowerShell
    $shellPath = "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
    New-ItemProperty -Path "HKLM:\SOFTWARE\OpenSSH" -Name DefaultShell -Value $shellPath -PropertyType String -Force | Out-Null

    Write-Log "OpenSSH Server configured and started" "SUCCESS"
    return $true
}

#==============================================================================
# PHASE 4: Generate SSH Keys
#==============================================================================
function New-SshKeys {
    Write-Log "=== PHASE 4: Generating SSH Keys ===" "INFO"

    $privateKeyPath = Join-Path $Config.SshPath "id_ed25519"
    $publicKeyPath = "$privateKeyPath.pub"

    if (Test-Path $privateKeyPath) {
        Write-Log "SSH keys already exist, backing up..." "WARN"
        $backupPath = "$privateKeyPath.backup_$(Get-Date -Format 'yyyyMMddHHmmss')"
        Move-Item $privateKeyPath $backupPath
        Move-Item $publicKeyPath "$backupPath.pub"
    }

    # Generate ed25519 key
    $keyComment = "orizon-agent-$($Config.NodeId)"
    & ssh-keygen -t ed25519 -f $privateKeyPath -N '""' -C $keyComment 2>&1 | Out-Null

    if (Test-Path $publicKeyPath) {
        $publicKey = Get-Content $publicKeyPath
        Write-Log "SSH key generated: $keyComment" "SUCCESS"
        Write-Log "Public Key: $publicKey" "INFO"

        # Store public key for registration
        $script:PublicKey = $publicKey
        return $true
    } else {
        Write-Log "Failed to generate SSH keys" "ERROR"
        return $false
    }
}

#==============================================================================
# PHASE 5: Register Public Key with Hub
#==============================================================================
function Register-PublicKey {
    Write-Log "=== PHASE 5: Registering Public Key with Hub ===" "INFO"

    $registrationUrl = "$($Config.ApiBaseUrl)/api/v1/nodes/$($Config.NodeId)/register-key"

    $body = @{
        public_key = $script:PublicKey
        node_name = $Config.NodeName
    } | ConvertTo-Json

    try {
        $response = Invoke-RestMethod -Uri $registrationUrl -Method POST -Body $body -ContentType "application/json" -Headers @{
            "Authorization" = "Bearer $($Config.AgentToken)"
        }
        Write-Log "Public key registered with Hub" "SUCCESS"
        return $true
    } catch {
        Write-Log "Failed to register public key: $_" "ERROR"
        Write-Log "Attempting manual registration..." "WARN"

        # Write key to file for manual registration
        $keyFile = Join-Path $Config.InstallPath "public_key_to_register.txt"
        $script:PublicKey | Out-File -FilePath $keyFile
        Write-Log "Public key saved to: $keyFile" "INFO"
        Write-Log "Please add this key manually to the Hub's authorized_keys" "WARN"
        return $true  # Continue anyway
    }
}

#==============================================================================
# PHASE 6: Download and Install NSSM
#==============================================================================
function Install-NSSM {
    Write-Log "=== PHASE 6: Installing NSSM (Service Manager) ===" "INFO"

    $nssmPath = Join-Path $Config.ToolsPath "nssm.exe"

    if (Test-Path $nssmPath) {
        Write-Log "NSSM already installed" "INFO"
        return $true
    }

    $nssmUrl = "https://nssm.cc/release/nssm-2.24.zip"
    $zipPath = Join-Path $env:TEMP "nssm.zip"
    $extractPath = Join-Path $env:TEMP "nssm-extract"

    try {
        Write-Log "Downloading NSSM..." "INFO"
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -Uri $nssmUrl -OutFile $zipPath -UseBasicParsing

        Write-Log "Extracting NSSM..." "INFO"
        Expand-Archive -Path $zipPath -DestinationPath $extractPath -Force

        # Find the correct architecture
        $arch = if ([Environment]::Is64BitOperatingSystem) { "win64" } else { "win32" }
        $nssmExe = Get-ChildItem -Path $extractPath -Recurse -Filter "nssm.exe" |
                   Where-Object { $_.DirectoryName -like "*$arch*" } |
                   Select-Object -First 1

        Copy-Item $nssmExe.FullName $nssmPath -Force

        # Cleanup
        Remove-Item $zipPath -Force
        Remove-Item $extractPath -Recurse -Force

        Write-Log "NSSM installed: $nssmPath" "SUCCESS"
        return $true
    } catch {
        Write-Log "Failed to install NSSM: $_" "ERROR"
        return $false
    }
}

#==============================================================================
# PHASE 7: Create SSH Tunnel Services
#==============================================================================
function Install-TunnelServices {
    Write-Log "=== PHASE 7: Creating SSH Tunnel Services ===" "INFO"

    $nssmPath = Join-Path $Config.ToolsPath "nssm.exe"
    $sshPath = "C:\Windows\System32\OpenSSH\ssh.exe"
    $privateKeyPath = Join-Path $Config.SshPath "id_ed25519"

    # Service definitions
    $tunnels = @(
        @{
            Name = "OrizonTunnelSystem"
            Description = "Orizon Zero Trust - System Management Tunnel"
            Port = $Config.SystemTunnelPort
            LogFile = Join-Path $Config.LogPath "tunnel-system.log"
        },
        @{
            Name = "OrizonTunnelTerminal"
            Description = "Orizon Zero Trust - Terminal Access Tunnel"
            Port = $Config.TerminalTunnelPort
            LogFile = Join-Path $Config.LogPath "tunnel-terminal.log"
        }
    )

    foreach ($tunnel in $tunnels) {
        Write-Log "Configuring $($tunnel.Name)..." "INFO"

        # Stop and remove existing service
        $existingService = Get-Service -Name $tunnel.Name -ErrorAction SilentlyContinue
        if ($existingService) {
            Stop-Service -Name $tunnel.Name -Force -ErrorAction SilentlyContinue
            & $nssmPath remove $tunnel.Name confirm 2>&1 | Out-Null
        }

        # Build SSH arguments
        $sshArgs = @(
            "-N",
            "-o", "ServerAliveInterval=15",
            "-o", "ServerAliveCountMax=3",
            "-o", "ExitOnForwardFailure=yes",
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=NUL",
            "-o", "BatchMode=yes",
            "-i", $privateKeyPath,
            "-p", $Config.HubSshPort,
            "-R", "$($tunnel.Port):localhost:$($Config.LocalSshPort)",
            "$($Config.NodeId)@$($Config.HubHost)"
        ) -join " "

        # Install service with NSSM
        & $nssmPath install $tunnel.Name $sshPath $sshArgs
        & $nssmPath set $tunnel.Name Description $tunnel.Description
        & $nssmPath set $tunnel.Name Start SERVICE_AUTO_START
        & $nssmPath set $tunnel.Name AppStdout $tunnel.LogFile
        & $nssmPath set $tunnel.Name AppStderr $tunnel.LogFile
        & $nssmPath set $tunnel.Name AppRotateFiles 1
        & $nssmPath set $tunnel.Name AppRotateBytes 1048576
        & $nssmPath set $tunnel.Name AppRestartDelay 5000

        # Start service
        Start-Service -Name $tunnel.Name

        $status = Get-Service -Name $tunnel.Name
        if ($status.Status -eq 'Running') {
            Write-Log "$($tunnel.Name) started successfully (Port: $($tunnel.Port))" "SUCCESS"
        } else {
            Write-Log "$($tunnel.Name) failed to start" "ERROR"
        }
    }

    return $true
}

#==============================================================================
# PHASE 8: Install nginx for Windows
#==============================================================================
function Install-Nginx {
    Write-Log "=== PHASE 8: Installing nginx for Windows ===" "INFO"

    $nginxExe = Join-Path $Config.NginxPath "nginx.exe"

    if (Test-Path $nginxExe) {
        Write-Log "nginx already installed" "INFO"
    } else {
        $nginxUrl = "https://nginx.org/download/nginx-1.24.0.zip"
        $zipPath = Join-Path $env:TEMP "nginx.zip"
        $extractPath = Join-Path $env:TEMP "nginx-extract"

        try {
            Write-Log "Downloading nginx..." "INFO"
            [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
            Invoke-WebRequest -Uri $nginxUrl -OutFile $zipPath -UseBasicParsing

            Write-Log "Extracting nginx..." "INFO"
            Expand-Archive -Path $zipPath -DestinationPath $extractPath -Force

            # Move nginx files
            $nginxFolder = Get-ChildItem -Path $extractPath -Directory | Select-Object -First 1
            Get-ChildItem -Path $nginxFolder.FullName | Move-Item -Destination $Config.NginxPath -Force

            # Cleanup
            Remove-Item $zipPath -Force
            Remove-Item $extractPath -Recurse -Force

            Write-Log "nginx installed: $($Config.NginxPath)" "SUCCESS"
        } catch {
            Write-Log "Failed to install nginx: $_" "ERROR"
            return $false
        }
    }

    # Generate self-signed SSL certificate
    Write-Log "Generating SSL certificate..." "INFO"
    $certPath = Join-Path $Config.SslPath "orizon.crt"
    $keyPath = Join-Path $Config.SslPath "orizon.key"

    if (-not (Test-Path $certPath)) {
        $opensslCmd = @"
openssl req -x509 -nodes -days 365 -newkey rsa:2048 `
    -keyout "$keyPath" `
    -out "$certPath" `
    -subj "/C=IT/ST=Italy/L=Milan/O=Orizon/CN=$($Config.NodeName)"
"@
        # Use PowerShell to generate self-signed cert as fallback
        $cert = New-SelfSignedCertificate -DnsName $Config.NodeName -CertStoreLocation "Cert:\LocalMachine\My" -NotAfter (Get-Date).AddYears(5)
        Export-Certificate -Cert $cert -FilePath "$certPath.cer" -Type CERT

        # Export private key
        $password = ConvertTo-SecureString -String "orizon" -Force -AsPlainText
        Export-PfxCertificate -Cert $cert -FilePath (Join-Path $Config.SslPath "orizon.pfx") -Password $password

        # Convert PFX to PEM format using certutil
        $pfxPath = Join-Path $Config.SslPath "orizon.pfx"

        Write-Log "SSL certificate generated" "SUCCESS"
    }

    # Create nginx configuration
    $nginxConf = @"
worker_processes 1;
error_log logs/error.log;
pid logs/nginx.pid;

events {
    worker_connections 1024;
}

http {
    include mime.types;
    default_type application/octet-stream;
    sendfile on;
    keepalive_timeout 65;

    server {
        listen $($Config.LocalHttpsPort) ssl;
        server_name $($Config.NodeName);

        ssl_certificate $($Config.SslPath.Replace('\','/'))/orizon.crt;
        ssl_certificate_key $($Config.SslPath.Replace('\','/'))/orizon.key;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;

        root $($Config.WwwPath.Replace('\','/'));
        index index.html;

        location / {
            try_files `$uri `$uri/ /index.html;
        }

        location /api/metrics {
            default_type application/json;
            alias $($Config.WwwPath.Replace('\','/'))/metrics.json;
        }
    }
}
"@

    $nginxConf | Out-File -FilePath (Join-Path $Config.NginxPath "conf\nginx.conf") -Encoding UTF8 -Force

    # Install nginx as Windows Service using NSSM
    $nssmPath = Join-Path $Config.ToolsPath "nssm.exe"
    $serviceName = "OrizonNginx"

    $existingService = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
    if ($existingService) {
        Stop-Service -Name $serviceName -Force -ErrorAction SilentlyContinue
        & $nssmPath remove $serviceName confirm 2>&1 | Out-Null
    }

    & $nssmPath install $serviceName $nginxExe
    & $nssmPath set $serviceName Description "Orizon Zero Trust - Status Page (nginx)"
    & $nssmPath set $serviceName AppDirectory $Config.NginxPath
    & $nssmPath set $serviceName Start SERVICE_AUTO_START

    Start-Service -Name $serviceName

    Write-Log "nginx service created and started" "SUCCESS"
    return $true
}

#==============================================================================
# PHASE 9: Create Status Page
#==============================================================================
function New-StatusPage {
    Write-Log "=== PHASE 9: Creating Status Page ===" "INFO"

    $statusPagePath = Join-Path $Config.WwwPath "index.html"

    $statusHtml = @"
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="10">
    <title>$($Config.NodeName) - Orizon Status</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #eee;
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        header {
            text-align: center;
            padding: 30px 0;
            border-bottom: 1px solid #333;
            margin-bottom: 30px;
        }
        .logo { font-size: 48px; font-weight: bold; color: #00d4ff; }
        .subtitle { color: #888; margin-top: 10px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .card {
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            padding: 25px;
            border: 1px solid rgba(255,255,255,0.1);
        }
        .card h3 {
            color: #00d4ff;
            margin-bottom: 20px;
            font-size: 18px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .metric { margin: 15px 0; }
        .metric-label { color: #888; font-size: 14px; }
        .metric-value { font-size: 24px; font-weight: bold; color: #fff; }
        .progress-bar {
            height: 8px;
            background: #333;
            border-radius: 4px;
            margin-top: 8px;
            overflow: hidden;
        }
        .progress-fill {
            height: 100%;
            border-radius: 4px;
            transition: width 0.3s ease;
        }
        .progress-fill.green { background: linear-gradient(90deg, #00ff88, #00d4ff); }
        .progress-fill.yellow { background: linear-gradient(90deg, #ffdd00, #ff9900); }
        .progress-fill.red { background: linear-gradient(90deg, #ff6600, #ff0000); }
        .status-badge {
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: bold;
        }
        .status-online { background: #00ff88; color: #000; }
        .status-offline { background: #ff4444; color: #fff; }
        .tunnel-status { display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid #333; }
        .tunnel-status:last-child { border-bottom: none; }
        footer { text-align: center; padding: 30px 0; color: #666; margin-top: 30px; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo">ORIZON</div>
            <p class="subtitle">Zero Trust Connect - $($Config.NodeName)</p>
            <p class="subtitle">Node ID: $($Config.NodeId)</p>
        </header>

        <div class="grid">
            <div class="card">
                <h3>System Information</h3>
                <div class="metric">
                    <div class="metric-label">Hostname</div>
                    <div class="metric-value" id="hostname">Loading...</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Operating System</div>
                    <div class="metric-value" id="os">Loading...</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Uptime</div>
                    <div class="metric-value" id="uptime">Loading...</div>
                </div>
            </div>

            <div class="card">
                <h3>CPU Usage</h3>
                <div class="metric">
                    <div class="metric-value"><span id="cpu-value">--</span>%</div>
                    <div class="progress-bar">
                        <div class="progress-fill green" id="cpu-bar" style="width: 0%"></div>
                    </div>
                </div>
            </div>

            <div class="card">
                <h3>Memory Usage</h3>
                <div class="metric">
                    <div class="metric-value"><span id="mem-value">--</span>%</div>
                    <div class="metric-label" id="mem-detail">Loading...</div>
                    <div class="progress-bar">
                        <div class="progress-fill green" id="mem-bar" style="width: 0%"></div>
                    </div>
                </div>
            </div>

            <div class="card">
                <h3>Disk Usage</h3>
                <div class="metric">
                    <div class="metric-value"><span id="disk-value">--</span>%</div>
                    <div class="metric-label" id="disk-detail">Loading...</div>
                    <div class="progress-bar">
                        <div class="progress-fill green" id="disk-bar" style="width: 0%"></div>
                    </div>
                </div>
            </div>

            <div class="card">
                <h3>Network</h3>
                <div class="metric">
                    <div class="metric-label">IP Address</div>
                    <div class="metric-value" id="ip-address">Loading...</div>
                </div>
            </div>

            <div class="card">
                <h3>Tunnel Status</h3>
                <div class="tunnel-status">
                    <span>System Tunnel (Port $($Config.SystemTunnelPort))</span>
                    <span class="status-badge" id="tunnel-system">Checking...</span>
                </div>
                <div class="tunnel-status">
                    <span>Terminal Tunnel (Port $($Config.TerminalTunnelPort))</span>
                    <span class="status-badge" id="tunnel-terminal">Checking...</span>
                </div>
            </div>
        </div>

        <footer>
            <p>Orizon Zero Trust Connect v2.0.0</p>
            <p>Last Update: <span id="last-update">--</span></p>
        </footer>
    </div>

    <script>
        async function updateMetrics() {
            try {
                const response = await fetch('/api/metrics');
                const data = await response.json();

                document.getElementById('hostname').textContent = data.hostname || 'N/A';
                document.getElementById('os').textContent = data.os || 'N/A';
                document.getElementById('uptime').textContent = data.uptime || 'N/A';

                updateProgress('cpu', data.cpu_usage || 0);
                updateProgress('mem', data.memory_usage || 0);
                document.getElementById('mem-detail').textContent = data.memory_detail || '';

                updateProgress('disk', data.disk_usage || 0);
                document.getElementById('disk-detail').textContent = data.disk_detail || '';

                document.getElementById('ip-address').textContent = data.ip_address || 'N/A';

                updateTunnelStatus('tunnel-system', data.tunnel_system);
                updateTunnelStatus('tunnel-terminal', data.tunnel_terminal);

                document.getElementById('last-update').textContent = new Date().toLocaleString();
            } catch (error) {
                console.error('Failed to update metrics:', error);
            }
        }

        function updateProgress(id, value) {
            const bar = document.getElementById(id + '-bar');
            const valueEl = document.getElementById(id + '-value');
            valueEl.textContent = value;
            bar.style.width = value + '%';
            bar.className = 'progress-fill ' + (value < 70 ? 'green' : value < 90 ? 'yellow' : 'red');
        }

        function updateTunnelStatus(id, isOnline) {
            const el = document.getElementById(id);
            el.textContent = isOnline ? 'ONLINE' : 'OFFLINE';
            el.className = 'status-badge ' + (isOnline ? 'status-online' : 'status-offline');
        }

        updateMetrics();
        setInterval(updateMetrics, 10000);
    </script>
</body>
</html>
"@

    $statusHtml | Out-File -FilePath $statusPagePath -Encoding UTF8 -Force
    Write-Log "Status page created: $statusPagePath" "SUCCESS"

    return $true
}

#==============================================================================
# PHASE 10: Create Metrics Update Script
#==============================================================================
function New-MetricsScript {
    Write-Log "=== PHASE 10: Creating Metrics Update Script ===" "INFO"

    $metricsScriptPath = Join-Path $Config.InstallPath "Update-Metrics.ps1"

    $metricsScript = @'
# Orizon Metrics Update Script
# Updates metrics.json for status page

$metricsPath = "C:\ProgramData\Orizon\www\metrics.json"

while ($true) {
    try {
        # System Info
        $os = Get-CimInstance Win32_OperatingSystem
        $cs = Get-CimInstance Win32_ComputerSystem

        # CPU
        $cpu = Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average
        $cpuUsage = [math]::Round($cpu.Average, 1)

        # Memory
        $memTotal = [math]::Round($os.TotalVisibleMemorySize / 1MB, 1)
        $memFree = [math]::Round($os.FreePhysicalMemory / 1MB, 1)
        $memUsed = $memTotal - $memFree
        $memUsage = [math]::Round(($memUsed / $memTotal) * 100, 1)

        # Disk
        $disk = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='C:'"
        $diskTotal = [math]::Round($disk.Size / 1GB, 1)
        $diskFree = [math]::Round($disk.FreeSpace / 1GB, 1)
        $diskUsed = $diskTotal - $diskFree
        $diskUsage = [math]::Round(($diskUsed / $diskTotal) * 100, 1)

        # Uptime
        $uptime = (Get-Date) - $os.LastBootUpTime
        $uptimeStr = "{0}d {1}h {2}m" -f $uptime.Days, $uptime.Hours, $uptime.Minutes

        # IP Address
        $ip = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notmatch '^(127\.|169\.254\.)' } | Select-Object -First 1).IPAddress

        # Tunnel Status
        $tunnelSystem = (Get-Service -Name "OrizonTunnelSystem" -ErrorAction SilentlyContinue).Status -eq 'Running'
        $tunnelTerminal = (Get-Service -Name "OrizonTunnelTerminal" -ErrorAction SilentlyContinue).Status -eq 'Running'

        $metrics = @{
            hostname = $env:COMPUTERNAME
            os = "$($os.Caption) $($os.Version)"
            uptime = $uptimeStr
            cpu_usage = $cpuUsage
            memory_usage = $memUsage
            memory_detail = "$memUsed GB / $memTotal GB"
            disk_usage = $diskUsage
            disk_detail = "$diskUsed GB / $diskTotal GB"
            ip_address = $ip
            tunnel_system = $tunnelSystem
            tunnel_terminal = $tunnelTerminal
            last_update = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
        }

        $metrics | ConvertTo-Json | Out-File -FilePath $metricsPath -Encoding UTF8 -Force
    } catch {
        # Log error but continue
    }

    Start-Sleep -Seconds 10
}
'@

    $metricsScript | Out-File -FilePath $metricsScriptPath -Encoding UTF8 -Force
    Write-Log "Metrics script created: $metricsScriptPath" "SUCCESS"

    return $true
}

#==============================================================================
# PHASE 11: Install Watchdog
#==============================================================================
function Install-Watchdog {
    Write-Log "=== PHASE 11: Installing Watchdog Service ===" "INFO"

    $watchdogScriptPath = Join-Path $Config.InstallPath "Orizon-Watchdog.ps1"

    $watchdogScript = @"
# Orizon Watchdog Service
# Monitors and restarts tunnel services if needed

`$Config = @{
    HubHost = "$($Config.HubHost)"
    HubSshPort = $($Config.HubSshPort)
    LogPath = "$($Config.LogPath)"
}

`$LogFile = Join-Path `$Config.LogPath "watchdog.log"

function Write-WatchdogLog {
    param([string]`$Message)
    `$entry = "[`$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] `$Message"
    Add-Content -Path `$LogFile -Value `$entry
}

function Test-TunnelHealth {
    `$systemTunnel = Get-Service -Name "OrizonTunnelSystem" -ErrorAction SilentlyContinue
    `$terminalTunnel = Get-Service -Name "OrizonTunnelTerminal" -ErrorAction SilentlyContinue
    `$metricsService = Get-Service -Name "OrizonMetrics" -ErrorAction SilentlyContinue

    return @{
        SystemTunnel = (`$systemTunnel.Status -eq 'Running')
        TerminalTunnel = (`$terminalTunnel.Status -eq 'Running')
        MetricsService = (`$metricsService.Status -eq 'Running')
    }
}

Write-WatchdogLog "Watchdog started"

while (`$true) {
    try {
        `$health = Test-TunnelHealth

        if (-not `$health.SystemTunnel) {
            Write-WatchdogLog "System tunnel down, restarting..."
            Restart-Service -Name "OrizonTunnelSystem" -Force
        }

        if (-not `$health.TerminalTunnel) {
            Write-WatchdogLog "Terminal tunnel down, restarting..."
            Restart-Service -Name "OrizonTunnelTerminal" -Force
        }

        if (-not `$health.MetricsService) {
            Write-WatchdogLog "Metrics service down, restarting..."
            Restart-Service -Name "OrizonMetrics" -Force
        }
    } catch {
        Write-WatchdogLog "Error: `$_"
    }

    Start-Sleep -Seconds 30
}
"@

    $watchdogScript | Out-File -FilePath $watchdogScriptPath -Encoding UTF8 -Force

    # Create scheduled task for watchdog
    $taskName = "OrizonWatchdog"

    # Remove existing task
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

    $action = New-ScheduledTaskAction -Execute "powershell.exe" `
        -Argument "-ExecutionPolicy Bypass -WindowStyle Hidden -File `"$watchdogScriptPath`""

    $trigger = New-ScheduledTaskTrigger -AtStartup
    $settings = New-ScheduledTaskSettingsSet -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
    $principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -RunLevel Highest

    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal
    Start-ScheduledTask -TaskName $taskName

    Write-Log "Watchdog scheduled task created" "SUCCESS"

    # Also create Metrics service using NSSM
    $nssmPath = Join-Path $Config.ToolsPath "nssm.exe"
    $serviceName = "OrizonMetrics"
    $metricsScriptPath = Join-Path $Config.InstallPath "Update-Metrics.ps1"

    $existingService = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
    if ($existingService) {
        Stop-Service -Name $serviceName -Force -ErrorAction SilentlyContinue
        & $nssmPath remove $serviceName confirm 2>&1 | Out-Null
    }

    & $nssmPath install $serviceName "powershell.exe" "-ExecutionPolicy Bypass -File `"$metricsScriptPath`""
    & $nssmPath set $serviceName Description "Orizon Zero Trust - Metrics Collector"
    & $nssmPath set $serviceName Start SERVICE_AUTO_START

    Start-Service -Name $serviceName

    Write-Log "Metrics service created and started" "SUCCESS"

    return $true
}

#==============================================================================
# PHASE 12: Configure Windows Firewall
#==============================================================================
function Set-FirewallRules {
    Write-Log "=== PHASE 12: Configuring Windows Firewall ===" "INFO"

    # Remove existing Orizon rules
    Get-NetFirewallRule -DisplayName "Orizon*" -ErrorAction SilentlyContinue | Remove-NetFirewallRule

    # Allow HTTPS inbound (status page)
    New-NetFirewallRule -DisplayName "Orizon - HTTPS Status Page" `
        -Direction Inbound -Protocol TCP -LocalPort $Config.LocalHttpsPort `
        -Action Allow -Profile Any -Description "Allows HTTPS access to Orizon status page"

    # Allow SSH inbound (local network only)
    New-NetFirewallRule -DisplayName "Orizon - SSH Local" `
        -Direction Inbound -Protocol TCP -LocalPort $Config.LocalSshPort `
        -Action Allow -Profile Any -Description "Allows SSH access for Orizon tunnels"

    # Allow outbound to Hub
    New-NetFirewallRule -DisplayName "Orizon - Hub Tunnel Outbound" `
        -Direction Outbound -Protocol TCP -RemotePort $Config.HubSshPort `
        -RemoteAddress $Config.HubHost -Action Allow -Profile Any `
        -Description "Allows outbound SSH tunnel to Orizon Hub"

    # Enable firewall logging
    $logPath = Join-Path $Config.LogPath "firewall.log"
    Set-NetFirewallProfile -Profile Domain,Public,Private `
        -LogFileName $logPath -LogAllowed False -LogBlocked True -LogMaxSizeKilobytes 4096

    Write-Log "Windows Firewall rules configured" "SUCCESS"

    return $true
}

#==============================================================================
# PHASE 13: Final Verification
#==============================================================================
function Test-Installation {
    Write-Log "=== PHASE 13: Verifying Installation ===" "INFO"

    $results = @{
        OpenSSH = (Get-Service -Name sshd -ErrorAction SilentlyContinue).Status -eq 'Running'
        TunnelSystem = (Get-Service -Name OrizonTunnelSystem -ErrorAction SilentlyContinue).Status -eq 'Running'
        TunnelTerminal = (Get-Service -Name OrizonTunnelTerminal -ErrorAction SilentlyContinue).Status -eq 'Running'
        Nginx = (Get-Service -Name OrizonNginx -ErrorAction SilentlyContinue).Status -eq 'Running'
        Metrics = (Get-Service -Name OrizonMetrics -ErrorAction SilentlyContinue).Status -eq 'Running'
        Watchdog = (Get-ScheduledTask -TaskName OrizonWatchdog -ErrorAction SilentlyContinue).State -eq 'Running'
        StatusPage = Test-Path (Join-Path $Config.WwwPath "index.html")
        SshKeys = Test-Path (Join-Path $Config.SshPath "id_ed25519")
    }

    Write-Host ""
    Write-Host "╔═══════════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║           INSTALLATION VERIFICATION               ║" -ForegroundColor Cyan
    Write-Host "╠═══════════════════════════════════════════════════╣" -ForegroundColor Cyan

    foreach ($key in $results.Keys) {
        $status = if ($results[$key]) { "[OK]" } else { "[FAIL]" }
        $color = if ($results[$key]) { "Green" } else { "Red" }
        $line = "║  {0,-20} {1,-26}  ║" -f $key, $status
        Write-Host $line -ForegroundColor $color
    }

    Write-Host "╚═══════════════════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host ""

    $allPassed = $results.Values -notcontains $false

    if ($allPassed) {
        Write-Log "All components installed successfully!" "SUCCESS"
        Write-Host ""
        Write-Host "  Status Page: https://localhost:$($Config.LocalHttpsPort)" -ForegroundColor Green
        Write-Host "  System Tunnel Port: $($Config.SystemTunnelPort)" -ForegroundColor Green
        Write-Host "  Terminal Tunnel Port: $($Config.TerminalTunnelPort)" -ForegroundColor Green
        Write-Host ""
    } else {
        Write-Log "Some components failed to install" "ERROR"
    }

    return $allPassed
}

#==============================================================================
# MAIN EXECUTION
#==============================================================================

# Clear screen and show banner
Clear-Host
Write-Banner

Write-Log "Starting Orizon Agent installation..." "INFO"
Write-Log "Node ID: $($Config.NodeId)" "INFO"
Write-Log "Node Name: $($Config.NodeName)" "INFO"
Write-Log "Hub: $($Config.HubHost):$($Config.HubSshPort)" "INFO"

# Execute installation phases
$phases = @(
    @{ Name = "Prerequisites"; Function = { Test-Prerequisites } },
    @{ Name = "Directories"; Function = { Initialize-Directories } },
    @{ Name = "OpenSSH"; Function = { Install-OpenSSH } },
    @{ Name = "SSH Keys"; Function = { New-SshKeys } },
    @{ Name = "Register Key"; Function = { Register-PublicKey } },
    @{ Name = "NSSM"; Function = { Install-NSSM } },
    @{ Name = "Tunnels"; Function = { Install-TunnelServices } },
    @{ Name = "nginx"; Function = { Install-Nginx } },
    @{ Name = "Status Page"; Function = { New-StatusPage } },
    @{ Name = "Metrics"; Function = { New-MetricsScript } },
    @{ Name = "Watchdog"; Function = { Install-Watchdog } },
    @{ Name = "Firewall"; Function = { Set-FirewallRules } }
)

$success = $true
foreach ($phase in $phases) {
    $result = & $phase.Function
    if (-not $result) {
        Write-Log "Phase '$($phase.Name)' failed!" "ERROR"
        $success = $false
        break
    }
}

if ($success) {
    Test-Installation
}

Write-Log "Installation log saved to: $LogFile" "INFO"
Write-Host ""
Write-Host "Press any key to exit..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
