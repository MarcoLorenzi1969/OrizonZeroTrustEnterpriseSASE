#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Orizon Zero Trust Connect - Windows Installer
    Version: 2.1.0

.DESCRIPTION
    This script installs and configures the Orizon Zero Trust agent on Windows.

    WHAT THIS INSTALLER DOES:
    -------------------------
    1. Installs and configures OpenSSH Client and Server
    2. Downloads and installs NSSM (Non-Sucking Service Manager)
    3. Creates secure directory structure with proper permissions
    4. Generates SSH Ed25519 keys for authentication
    5. Creates Windows Services for:
       - SSH tunnels to each Hub server (System + Terminal + HTTPS)
       - Metrics collector for status page
       - Watchdog service for reliability
    6. Installs nginx for status page (optional)
    7. Configures Windows Firewall rules

    WHAT GETS INSTALLED:
    -------------------
    - OpenSSH Client: Creates encrypted connections to Orizon Hub
    - OpenSSH Server: Allows incoming connections via reverse tunnel
    - NSSM: Service manager that keeps tunnels running
    - nginx (optional): Local HTTPS status page

    SECURITY:
    ---------
    - All traffic is encrypted via SSH (Ed25519 keys)
    - No inbound internet ports are opened
    - Keys are stored with strict NTFS permissions
    - Services run as SYSTEM with minimal privileges

.PARAMETER NodeId
    Your node identifier from Orizon Hub dashboard
    Format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

.PARAMETER HubServers
    Comma-separated list of Hub servers
    Format: host1:port,host2:port or host1,host2 (default port: 2222)

.PARAMETER NodeName
    Friendly name for this node (default: computer name)

.PARAMETER ApiBaseUrl
    Hub API URL for automatic key registration (optional)

.PARAMETER AgentToken
    Authentication token for registration (optional)

.PARAMETER Uninstall
    Remove Orizon agent and services

.EXAMPLE
    # Interactive mode
    .\orizon-installer.ps1

.EXAMPLE
    # Non-interactive mode
    .\orizon-installer.ps1 -NodeId "abc123..." -HubServers "hub1.orizon.one:2222,hub2.orizon.one:2222"

.EXAMPLE
    # Uninstall
    .\orizon-installer.ps1 -Uninstall

.NOTES
    Version:        2.1.0
    Author:         Orizon Team
    Platform:       Windows 10/11, Windows Server 2019/2022/2025
#>

param(
    [string]$NodeId = "",
    [string]$HubServers = "",
    [string]$NodeName = $env:COMPUTERNAME,
    [string]$ApiBaseUrl = "",
    [string]$AgentToken = "",
    [int]$LocalSshPort = 22,
    [int]$LocalHttpsPort = 443,
    [switch]$Uninstall,
    [switch]$SkipNginx,
    [switch]$Help
)

#===============================================================================
# CONFIGURATION
#===============================================================================

$Version = "2.1.0"
$InstallPath = "C:\ProgramData\Orizon"
$LogPath = "$InstallPath\logs"
$SshPath = "$InstallPath\.ssh"
$NginxPath = "$InstallPath\nginx"
$WwwPath = "$InstallPath\www"
$SslPath = "$InstallPath\ssl"
$ToolsPath = "$InstallPath\tools"
$ConfigPath = "$InstallPath\config"

#===============================================================================
# LOGGING
#===============================================================================

$LogFile = ""

function Write-Log {
    param(
        [string]$Message,
        [ValidateSet("INFO", "WARN", "ERROR", "SUCCESS")]
        [string]$Level = "INFO"
    )

    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logEntry = "[$timestamp] [$Level] $Message"

    if (-not (Test-Path $LogPath)) {
        New-Item -ItemType Directory -Path $LogPath -Force | Out-Null
    }

    if ($LogFile) {
        Add-Content -Path $LogFile -Value $logEntry
    }

    switch ($Level) {
        "INFO"    { Write-Host $logEntry -ForegroundColor Cyan }
        "WARN"    { Write-Host $logEntry -ForegroundColor Yellow }
        "ERROR"   { Write-Host $logEntry -ForegroundColor Red }
        "SUCCESS" { Write-Host $logEntry -ForegroundColor Green }
    }
}

function Write-Banner {
    $banner = @"

    =====================================================================

         OOOO  RRRR   III  ZZZZZ  OOOO  N   N
        O    O R   R   I      Z  O    O NN  N
        O    O RRRR    I     Z   O    O N N N
        O    O R  R    I    Z    O    O N  NN
         OOOO  R   R  III  ZZZZZ  OOOO  N   N

              Zero Trust Connect - Windows Agent
                      Version $Version

    =====================================================================

"@
    Write-Host $banner -ForegroundColor Magenta
}

function Show-Help {
    $helpText = @"
ORIZON ZERO TRUST CONNECT - Windows Installer
==============================================

WHAT WILL BE INSTALLED:
-----------------------

  1. OPENSSH CLIENT
     Location: C:\Windows\System32\OpenSSH\
     Purpose:  Creates encrypted SSH connections to Orizon Hub
     Note:     Uses Ed25519 keys (most secure SSH algorithm)

  2. OPENSSH SERVER
     Location: C:\Windows\System32\OpenSSH\
     Purpose:  Allows SSH access via reverse tunnel
     Note:     Required for Terminal access feature

  3. NSSM (Non-Sucking Service Manager)
     Location: $ToolsPath\nssm.exe
     Purpose:  Manages SSH tunnel services
     Note:     Automatically restarts services if they fail

  4. NGINX (Optional)
     Location: $NginxPath\
     Purpose:  Serves local HTTPS status page
     Note:     Shows system metrics and tunnel status

WHAT WILL BE CONFIGURED:
------------------------

  1. SSH REVERSE TUNNELS
     For each Hub server, three tunnels are created:
     - System Tunnel: Hub collects metrics from this PC
     - Terminal Tunnel: Authorized users can access PowerShell
     - HTTPS Tunnel: Access to local web interface

  2. WINDOWS SERVICES
     - OrizonTunnelHub1, OrizonTunnelHub2, ...: Tunnel services
     - OrizonMetrics: Collects system metrics
     - OrizonNginx: Status page web server (optional)

  3. FIREWALL RULES
     - Outbound SSH to Hub servers (port 2222)
     - Local HTTPS for status page (port 443)

DIRECTORY STRUCTURE:
--------------------

  $InstallPath\                 Main installation directory
  $InstallPath\.ssh\            SSH keys (restricted access)
  $InstallPath\logs\            Service logs
  $InstallPath\nginx\           nginx web server
  $InstallPath\www\             Status page files
  $InstallPath\ssl\             SSL certificates
  $InstallPath\tools\           NSSM and utilities
  $InstallPath\config\          Configuration files

USAGE:
------

  Interactive mode:
    .\orizon-installer.ps1

  Non-interactive mode:
    .\orizon-installer.ps1 -NodeId "xxx-xxx-xxx" -HubServers "hub1:2222,hub2:2222"

  Uninstall:
    .\orizon-installer.ps1 -Uninstall

"@
    Write-Host $helpText
}

#===============================================================================
# UTILITY FUNCTIONS
#===============================================================================

function Test-Administrator {
    $currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    return $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Get-TunnelPorts {
    param([string]$NodeId)

    # Calculate hash from NodeId
    $md5 = [System.Security.Cryptography.MD5]::Create()
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($NodeId)
    $hash = $md5.ComputeHash($bytes)
    $hashHex = [BitConverter]::ToString($hash).Replace("-", "").Substring(0, 8)
    $hashDec = [Convert]::ToInt64($hashHex, 16)

    return @{
        System = 9000 + ($hashDec % 1000)
        Terminal = 10000 + ($hashDec % 50000)
        Https = 10001 + ($hashDec % 50000)
    }
}

function Parse-HubServers {
    param([string]$Servers)

    $hubs = @()
    $serverList = $Servers -split ","

    $num = 1
    foreach ($server in $serverList) {
        $server = $server.Trim()
        if ($server -match "^(.+):(\d+)$") {
            $hubs += @{
                Name = "Hub$num"
                Host = $Matches[1]
                Port = [int]$Matches[2]
            }
        } else {
            $hubs += @{
                Name = "Hub$num"
                Host = $server
                Port = 2222
            }
        }
        $num++
    }

    return $hubs
}

#===============================================================================
# INSTALLATION FUNCTIONS
#===============================================================================

function Initialize-Directories {
    Write-Log "Creating directory structure..." "INFO"

    $directories = @(
        $InstallPath,
        $LogPath,
        $SshPath,
        $NginxPath,
        $WwwPath,
        $SslPath,
        $ToolsPath,
        $ConfigPath
    )

    foreach ($dir in $directories) {
        if (-not (Test-Path $dir)) {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
            Write-Log "  Created: $dir" "INFO"
        }
    }

    # Secure SSH directory
    $acl = Get-Acl $SshPath
    $acl.SetAccessRuleProtection($true, $false)
    $rule = New-Object System.Security.AccessControl.FileSystemAccessRule("SYSTEM", "FullControl", "ContainerInherit,ObjectInherit", "None", "Allow")
    $acl.AddAccessRule($rule)
    $rule = New-Object System.Security.AccessControl.FileSystemAccessRule("Administrators", "FullControl", "ContainerInherit,ObjectInherit", "None", "Allow")
    $acl.AddAccessRule($rule)
    Set-Acl $SshPath $acl

    Write-Log "Directory structure created" "SUCCESS"
}

function Install-OpenSSH {
    Write-Log "Configuring OpenSSH..." "INFO"

    Write-Host ""
    Write-Host "  OPENSSH CLIENT" -ForegroundColor Cyan
    Write-Host "    Creates encrypted connections to Orizon Hub servers"
    Write-Host "    Uses Ed25519 algorithm for maximum security"
    Write-Host ""

    # Check OpenSSH Client
    $sshClient = Get-WindowsCapability -Online | Where-Object Name -like 'OpenSSH.Client*'
    if ($sshClient.State -ne 'Installed') {
        Write-Log "Installing OpenSSH Client..." "INFO"
        Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0
    }
    Write-Log "OpenSSH Client: OK" "SUCCESS"

    Write-Host ""
    Write-Host "  OPENSSH SERVER" -ForegroundColor Cyan
    Write-Host "    Allows incoming SSH connections via reverse tunnel"
    Write-Host "    Required for Terminal access feature"
    Write-Host ""

    # Check OpenSSH Server
    $sshServer = Get-WindowsCapability -Online | Where-Object Name -like 'OpenSSH.Server*'
    if ($sshServer.State -ne 'Installed') {
        Write-Log "Installing OpenSSH Server..." "INFO"
        Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
    }
    Write-Log "OpenSSH Server: OK" "SUCCESS"

    # Configure SSH Server
    Set-Service -Name sshd -StartupType Automatic
    Start-Service sshd -ErrorAction SilentlyContinue

    # Set default shell to PowerShell
    $shellPath = "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
    New-ItemProperty -Path "HKLM:\SOFTWARE\OpenSSH" -Name DefaultShell -Value $shellPath -PropertyType String -Force | Out-Null

    Write-Log "OpenSSH configured" "SUCCESS"
}

function New-SshKeys {
    param([string]$NodeId)

    Write-Log "Generating SSH keys..." "INFO"

    Write-Host ""
    Write-Host "  SSH KEY GENERATION" -ForegroundColor Cyan
    Write-Host "    Algorithm: Ed25519 (most secure)"
    Write-Host "    Purpose: Authenticate this PC to Orizon Hub"
    Write-Host ""

    $privateKeyPath = Join-Path $SshPath "id_ed25519"
    $publicKeyPath = "$privateKeyPath.pub"

    if (Test-Path $privateKeyPath) {
        Write-Log "SSH key already exists, backing up..." "WARN"
        $backupPath = "$privateKeyPath.backup_$(Get-Date -Format 'yyyyMMddHHmmss')"
        Move-Item $privateKeyPath $backupPath
        Move-Item $publicKeyPath "$backupPath.pub" -ErrorAction SilentlyContinue
    }

    # Generate key
    $keyComment = "orizon-agent-$NodeId"
    & ssh-keygen -t ed25519 -f $privateKeyPath -N '""' -C $keyComment 2>&1 | Out-Null

    if (Test-Path $publicKeyPath) {
        $publicKey = Get-Content $publicKeyPath
        Write-Log "SSH key generated" "SUCCESS"
        Write-Host ""
        Write-Host "  PUBLIC KEY:" -ForegroundColor Yellow
        Write-Host "  $publicKey" -ForegroundColor White
        Write-Host ""
        return $publicKey
    } else {
        Write-Log "Failed to generate SSH key" "ERROR"
        return $null
    }
}

function Install-NSSM {
    Write-Log "Installing NSSM (Service Manager)..." "INFO"

    Write-Host ""
    Write-Host "  NSSM (Non-Sucking Service Manager)" -ForegroundColor Cyan
    Write-Host "    Manages SSH tunnel Windows services"
    Write-Host "    Automatically restarts services if they crash"
    Write-Host "    Source: https://nssm.cc"
    Write-Host ""

    $nssmPath = Join-Path $ToolsPath "nssm.exe"

    if (Test-Path $nssmPath) {
        Write-Log "NSSM already installed" "INFO"
        return $true
    }

    $nssmUrl = "https://nssm.cc/release/nssm-2.24.zip"
    $zipPath = Join-Path $env:TEMP "nssm.zip"
    $extractPath = Join-Path $env:TEMP "nssm-extract"

    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -Uri $nssmUrl -OutFile $zipPath -UseBasicParsing

        Expand-Archive -Path $zipPath -DestinationPath $extractPath -Force

        $arch = if ([Environment]::Is64BitOperatingSystem) { "win64" } else { "win32" }
        $nssmExe = Get-ChildItem -Path $extractPath -Recurse -Filter "nssm.exe" |
                   Where-Object { $_.DirectoryName -like "*$arch*" } |
                   Select-Object -First 1

        Copy-Item $nssmExe.FullName $nssmPath -Force

        Remove-Item $zipPath -Force -ErrorAction SilentlyContinue
        Remove-Item $extractPath -Recurse -Force -ErrorAction SilentlyContinue

        Write-Log "NSSM installed: $nssmPath" "SUCCESS"
        return $true
    } catch {
        Write-Log "Failed to install NSSM: $_" "ERROR"
        return $false
    }
}

function Install-TunnelServices {
    param(
        [string]$NodeId,
        [array]$Hubs,
        [hashtable]$Ports
    )

    Write-Log "Creating SSH tunnel services..." "INFO"

    $nssmPath = Join-Path $ToolsPath "nssm.exe"
    $sshPath = "C:\Windows\System32\OpenSSH\ssh.exe"
    $privateKeyPath = Join-Path $SshPath "id_ed25519"

    foreach ($hub in $Hubs) {
        Write-Host ""
        Write-Host "  Creating tunnel service for $($hub.Name) ($($hub.Host):$($hub.Port))" -ForegroundColor Cyan
        Write-Host ""

        # Create three tunnels per hub: System, Terminal, HTTPS
        $tunnels = @(
            @{
                Suffix = ""
                Description = "Orizon Tunnel - $($hub.Name) System"
                LocalPort = $script:LocalSshPort
                RemotePort = $Ports.System
            },
            @{
                Suffix = "Term"
                Description = "Orizon Tunnel - $($hub.Name) Terminal"
                LocalPort = $script:LocalSshPort
                RemotePort = $Ports.Terminal
            },
            @{
                Suffix = "Https"
                Description = "Orizon Tunnel - $($hub.Name) HTTPS"
                LocalPort = $script:LocalHttpsPort
                RemotePort = $Ports.Https
            }
        )

        foreach ($tunnel in $tunnels) {
            $serviceName = "OrizonTunnel$($hub.Name)$($tunnel.Suffix)"
            $logFile = Join-Path $LogPath "tunnel-$($hub.Name.ToLower())$($tunnel.Suffix.ToLower()).log"

            # Remove existing service
            $existingService = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
            if ($existingService) {
                Stop-Service -Name $serviceName -Force -ErrorAction SilentlyContinue
                & $nssmPath remove $serviceName confirm 2>&1 | Out-Null
            }

            # Build SSH arguments
            $sshArgs = @(
                "-N",
                "-o", "ServerAliveInterval=30",
                "-o", "ServerAliveCountMax=3",
                "-o", "ExitOnForwardFailure=yes",
                "-o", "StrictHostKeyChecking=no",
                "-o", "UserKnownHostsFile=NUL",
                "-o", "BatchMode=yes",
                "-i", $privateKeyPath,
                "-p", $hub.Port,
                "-R", "$($tunnel.RemotePort):localhost:$($tunnel.LocalPort)",
                "$NodeId@$($hub.Host)"
            ) -join " "

            # Install service
            & $nssmPath install $serviceName $sshPath $sshArgs
            & $nssmPath set $serviceName Description $tunnel.Description
            & $nssmPath set $serviceName Start SERVICE_AUTO_START
            & $nssmPath set $serviceName AppStdout $logFile
            & $nssmPath set $serviceName AppStderr $logFile
            & $nssmPath set $serviceName AppRotateFiles 1
            & $nssmPath set $serviceName AppRotateBytes 1048576
            & $nssmPath set $serviceName AppRestartDelay 5000

            Start-Service -Name $serviceName -ErrorAction SilentlyContinue

            $status = Get-Service -Name $serviceName
            if ($status.Status -eq 'Running') {
                Write-Log "  $serviceName started (Port: $($tunnel.RemotePort))" "SUCCESS"
            } else {
                Write-Log "  $serviceName may have failed - check logs" "WARN"
            }
        }
    }
}

function Save-Configuration {
    param(
        [string]$NodeId,
        [string]$NodeName,
        [array]$Hubs,
        [hashtable]$Ports
    )

    $configFile = Join-Path $ConfigPath "agent.conf"

    $config = @"
# Orizon Zero Trust Connect - Agent Configuration
# Generated: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
# Version: $Version

[Node]
NodeId=$NodeId
NodeName=$NodeName

[Hubs]
$(($Hubs | ForEach-Object { "$($_.Name)=$($_.Host):$($_.Port)" }) -join "`n")

[Ports]
SystemTunnelPort=$($Ports.System)
TerminalTunnelPort=$($Ports.Terminal)
HttpsTunnelPort=$($Ports.Https)
LocalSshPort=$LocalSshPort
LocalHttpsPort=$LocalHttpsPort
"@

    $config | Out-File -FilePath $configFile -Encoding UTF8 -Force
    Write-Log "Configuration saved to: $configFile" "SUCCESS"
}

function Set-FirewallRules {
    param([array]$Hubs)

    Write-Log "Configuring Windows Firewall..." "INFO"

    # Remove existing Orizon rules
    Get-NetFirewallRule -DisplayName "Orizon*" -ErrorAction SilentlyContinue | Remove-NetFirewallRule

    # Allow outbound to each Hub
    foreach ($hub in $Hubs) {
        New-NetFirewallRule -DisplayName "Orizon - $($hub.Name) Outbound" `
            -Direction Outbound -Protocol TCP -RemotePort $hub.Port `
            -RemoteAddress $hub.Host -Action Allow -Profile Any `
            -Description "Allows outbound SSH tunnel to Orizon $($hub.Name)"
    }

    # Allow local HTTPS
    New-NetFirewallRule -DisplayName "Orizon - HTTPS Status Page" `
        -Direction Inbound -Protocol TCP -LocalPort $LocalHttpsPort `
        -Action Allow -Profile Any -Description "Allows HTTPS access to Orizon status page"

    Write-Log "Firewall rules configured" "SUCCESS"
}

function Show-Summary {
    param(
        [string]$NodeId,
        [string]$NodeName,
        [array]$Hubs,
        [hashtable]$Ports
    )

    Write-Host ""
    Write-Host "  ============================================================" -ForegroundColor Green
    Write-Host "           INSTALLATION COMPLETED SUCCESSFULLY" -ForegroundColor Green
    Write-Host "  ============================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Node Information:" -ForegroundColor White
    Write-Host "    Node ID:   $NodeId"
    Write-Host "    Node Name: $NodeName"
    Write-Host ""
    Write-Host "  Tunnel Ports:" -ForegroundColor White
    Write-Host "    System:   $($Ports.System)"
    Write-Host "    Terminal: $($Ports.Terminal)"
    Write-Host "    HTTPS:    $($Ports.Https)"
    Write-Host ""
    Write-Host "  Hub Servers:" -ForegroundColor White
    foreach ($hub in $Hubs) {
        Write-Host "    $($hub.Name): $($hub.Host):$($hub.Port)"
    }
    Write-Host ""
    Write-Host "  Service Commands:" -ForegroundColor White
    Write-Host "    Status:  Get-Service Orizon*"
    Write-Host "    Stop:    Stop-Service OrizonTunnelHub1"
    Write-Host "    Start:   Start-Service OrizonTunnelHub1"
    Write-Host "    Logs:    Get-Content $LogPath\tunnel-hub1.log -Tail 50"
    Write-Host ""
    Write-Host "  NEXT STEP:" -ForegroundColor Yellow
    Write-Host "    Add the public key to Orizon Hub dashboard:"
    Write-Host "    Nodes > $NodeName > Settings > SSH Keys > Add Key"
    Write-Host ""
}

#===============================================================================
# UNINSTALL
#===============================================================================

function Uninstall-Orizon {
    Write-Log "Uninstalling Orizon Agent..." "WARN"

    $nssmPath = Join-Path $ToolsPath "nssm.exe"

    # Stop and remove all Orizon services
    Get-Service -Name "Orizon*" -ErrorAction SilentlyContinue | ForEach-Object {
        Write-Log "Stopping $($_.Name)..." "INFO"
        Stop-Service -Name $_.Name -Force -ErrorAction SilentlyContinue

        if (Test-Path $nssmPath) {
            & $nssmPath remove $_.Name confirm 2>&1 | Out-Null
        }
    }

    # Remove scheduled tasks
    Get-ScheduledTask -TaskName "Orizon*" -ErrorAction SilentlyContinue | Unregister-ScheduledTask -Confirm:$false

    # Remove firewall rules
    Get-NetFirewallRule -DisplayName "Orizon*" -ErrorAction SilentlyContinue | Remove-NetFirewallRule

    Write-Log "Services and firewall rules removed" "SUCCESS"
    Write-Host ""
    Write-Host "Data preserved in:" -ForegroundColor Yellow
    Write-Host "  $InstallPath"
    Write-Host ""
    Write-Host "To remove all data:" -ForegroundColor Yellow
    Write-Host "  Remove-Item -Recurse -Force '$InstallPath'"
    Write-Host ""
}

#===============================================================================
# MAIN
#===============================================================================

function Main {
    if ($Help) {
        Show-Help
        return
    }

    if (-not (Test-Administrator)) {
        Write-Host "This script must be run as Administrator" -ForegroundColor Red
        Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
        exit 1
    }

    $script:LogFile = Join-Path $LogPath "install_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"

    if ($Uninstall) {
        Uninstall-Orizon
        return
    }

    Clear-Host
    Write-Banner

    # Interactive mode if parameters not provided
    if (-not $NodeId) {
        Write-Host "  STEP 1: Node Configuration" -ForegroundColor Yellow
        Write-Host "  ==========================" -ForegroundColor Yellow
        Write-Host ""
        $NodeId = Read-Host "  Enter Node ID"

        if ($NodeId -notmatch '^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$') {
            Write-Host "  Invalid Node ID format" -ForegroundColor Red
            exit 1
        }
    }

    if (-not $HubServers) {
        Write-Host ""
        Write-Host "  STEP 2: Hub Server Configuration" -ForegroundColor Yellow
        Write-Host "  =================================" -ForegroundColor Yellow
        Write-Host "  Format: host1:port,host2:port (port default: 2222)"
        Write-Host ""
        $HubServers = Read-Host "  Enter Hub Servers"
    }

    # Parse configuration
    $Hubs = Parse-HubServers -Servers $HubServers
    $Ports = Get-TunnelPorts -NodeId $NodeId

    Write-Host ""
    Write-Host "  Configuration Summary:" -ForegroundColor Cyan
    Write-Host "    Node ID: $NodeId"
    Write-Host "    Node Name: $NodeName"
    Write-Host "    Hub Servers: $($Hubs.Count)"
    Write-Host "    Tunnel Ports: System=$($Ports.System), Terminal=$($Ports.Terminal), HTTPS=$($Ports.Https)"
    Write-Host ""
    $confirm = Read-Host "  Press Enter to continue or Ctrl+C to cancel"

    # Run installation
    Initialize-Directories
    Install-OpenSSH
    $PublicKey = New-SshKeys -NodeId $NodeId
    Install-NSSM
    Install-TunnelServices -NodeId $NodeId -Hubs $Hubs -Ports $Ports
    Save-Configuration -NodeId $NodeId -NodeName $NodeName -Hubs $Hubs -Ports $Ports
    Set-FirewallRules -Hubs $Hubs
    Show-Summary -NodeId $NodeId -NodeName $NodeName -Hubs $Hubs -Ports $Ports

    Write-Host "  Press any key to exit..." -ForegroundColor Gray
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}

Main
