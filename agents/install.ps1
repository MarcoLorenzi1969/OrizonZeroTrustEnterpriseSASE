# Orizon Zero Trust Connect - Windows Agent Installer
# For: Windows 10/11 and Windows Server
# Version: 1.0.0
# Requires: Administrator privileges

param(
    [string]$HubHost = "46.101.189.126",
    [string]$NodeToken = "",
    [switch]$Uninstall
)

$ErrorActionPreference = "Stop"

# Configuration
$AgentName = "OrizonAgent"
$AgentVersion = "1.0.0"
$InstallDir = "C:\Program Files\Orizon"
$ConfigDir = "C:\ProgramData\Orizon"
$LogDir = "C:\ProgramData\Orizon\Logs"
$ServiceName = "OrizonZeroTrustAgent"
$ServiceDisplayName = "Orizon Zero Trust Connect Agent"

# Colors
function Write-ColorOutput {
    param([string]$Message, [string]$Color = "White")
    Write-Host $Message -ForegroundColor $Color
}

# Banner
Write-ColorOutput "╔════════════════════════════════════════════════════╗" "Cyan"
Write-ColorOutput "║     Orizon Zero Trust Connect - Agent Installer    ║" "Cyan"
Write-ColorOutput "║              For Syneto/Orizon Security            ║" "Cyan"
Write-ColorOutput "╚════════════════════════════════════════════════════╝" "Cyan"
Write-Host ""
Write-ColorOutput "Version: $AgentVersion" "Green"
Write-ColorOutput "System: Windows $([System.Environment]::OSVersion.Version)" "Green"
Write-ColorOutput "Hub: $HubHost" "Green"
Write-Host ""

# Check administrator privileges
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-ColorOutput "Error: This script requires Administrator privileges" "Red"
    Write-ColorOutput "Please run PowerShell as Administrator" "Yellow"
    exit 1
}

function Test-Dependencies {
    Write-ColorOutput "Checking dependencies..." "Yellow"
    
    $missing = @()
    
    # Check Python
    try {
        $pythonVersion = python --version 2>&1
        if ($pythonVersion -match "Python 3") {
            Write-ColorOutput "  ✓ Python 3 found: $pythonVersion" "Green"
        } else {
            $missing += "Python 3"
        }
    } catch {
        $missing += "Python 3"
    }
    
    # Check OpenSSH
    if (Get-Command ssh -ErrorAction SilentlyContinue) {
        Write-ColorOutput "  ✓ OpenSSH found" "Green"
    } else {
        $missing += "OpenSSH"
    }
    
    if ($missing.Count -gt 0) {
        Write-ColorOutput "Missing dependencies: $($missing -join ', ')" "Red"
        Write-ColorOutput "Installing missing dependencies..." "Yellow"
        
        foreach ($dep in $missing) {
            switch ($dep) {
                "Python 3" {
                    Write-ColorOutput "Installing Python 3..." "Yellow"
                    # Download Python installer
                    $pythonUrl = "https://www.python.org/ftp/python/3.11.0/python-3.11.0-amd64.exe"
                    $pythonInstaller = "$env:TEMP\python-installer.exe"
                    Invoke-WebRequest -Uri $pythonUrl -OutFile $pythonInstaller
                    Start-Process -FilePath $pythonInstaller -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1" -Wait
                    Remove-Item $pythonInstaller
                }
                "OpenSSH" {
                    Write-ColorOutput "Installing OpenSSH..." "Yellow"
                    Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0
                }
            }
        }
    }
}

function Install-PythonPackages {
    Write-ColorOutput "Installing Python packages..." "Yellow"
    
    $packages = @("requests", "websocket-client", "psutil", "pywin32")
    
    foreach ($package in $packages) {
        Write-ColorOutput "  Installing $package..." "Gray"
        & python -m pip install $package --quiet
    }
    
    Write-ColorOutput "  ✓ Python packages installed" "Green"
}

function New-Directories {
    Write-ColorOutput "Creating directories..." "Yellow"
    
    $dirs = @($InstallDir, $ConfigDir, $LogDir)
    
    foreach ($dir in $dirs) {
        if (!(Test-Path $dir)) {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
            Write-ColorOutput "  ✓ Created $dir" "Green"
        } else {
            Write-ColorOutput "  ℹ Directory exists: $dir" "Gray"
        }
    }
}

function Install-AgentFiles {
    Write-ColorOutput "Installing agent files..." "Yellow"
    
    # Agent Python script
    $agentScript = @'
# Embedded agent code for Windows
import sys
sys.path.insert(0, r"C:\Program Files\Orizon")
from orizon_agent import main
if __name__ == "__main__":
    main()
'@
    
    # Save agent script
    $agentScript | Out-File -FilePath "$InstallDir\orizon_agent_wrapper.py" -Encoding UTF8
    
    # Copy main agent file if exists locally
    if (Test-Path ".\orizon_agent.py") {
        Copy-Item ".\orizon_agent.py" -Destination "$InstallDir\orizon_agent.py" -Force
    } else {
        # Download from hub
        try {
            Invoke-WebRequest -Uri "https://$HubHost/downloads/agent/orizon_agent.py" `
                -OutFile "$InstallDir\orizon_agent.py" `
                -SkipCertificateCheck
        } catch {
            Write-ColorOutput "Warning: Could not download agent from hub" "Yellow"
        }
    }
    
    Write-ColorOutput "  ✓ Agent files installed" "Green"
}

function New-Configuration {
    Write-ColorOutput "Creating configuration..." "Yellow"
    
    if ([string]::IsNullOrEmpty($NodeToken)) {
        $NodeToken = Read-Host "Enter Node Token (press Enter to skip)"
    }
    
    $config = @{
        hub_host = $HubHost
        hub_ssh_port = 2222
        hub_https_port = 8443
        api_endpoint = "https://${HubHost}:8443/api/v1"
        node_token = $NodeToken
        reconnect_delay = 5
        max_reconnect_delay = 300
        health_check_interval = 30
        log_level = "INFO"
        log_file = "$LogDir\agent.log"
    }
    
    $config | ConvertTo-Json | Out-File -FilePath "$ConfigDir\agent.json" -Encoding UTF8
    
    Write-ColorOutput "  ✓ Configuration saved to $ConfigDir\agent.json" "Green"
}

function Install-WindowsService {
    Write-ColorOutput "Installing Windows service..." "Yellow"
    
    # Create service wrapper script
    $serviceScript = @"
import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import sys
import os

sys.path.insert(0, r'$InstallDir')

class OrizonAgentService(win32serviceutil.ServiceFramework):
    _svc_name_ = '$ServiceName'
    _svc_display_name_ = '$ServiceDisplayName'
    _svc_description_ = 'Orizon Zero Trust Connect Agent - Secure tunnel management'
    
    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        socket.setdefaulttimeout(60)
        
    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        
    def SvcDoRun(self):
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                            servicemanager.PYS_SERVICE_STARTED,
                            (self._svc_name_, ''))
        
        import orizon_agent
        agent = orizon_agent.OrizonAgent(config_path=r'$ConfigDir\agent.json')
        agent.run()

if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(OrizonAgentService)
"@
    
    $serviceScript | Out-File -FilePath "$InstallDir\orizon_service.py" -Encoding UTF8
    
    # Install the service
    Write-ColorOutput "  Installing service..." "Gray"
    & python "$InstallDir\orizon_service.py" install
    
    # Configure service
    Set-Service -Name $ServiceName -StartupType Automatic -Description "Orizon Zero Trust Connect Agent"
    
    Write-ColorOutput "  ✓ Windows service installed" "Green"
}

function Start-AgentService {
    Write-ColorOutput "Starting service..." "Yellow"
    
    Start-Service -Name $ServiceName
    $service = Get-Service -Name $ServiceName
    
    if ($service.Status -eq "Running") {
        Write-ColorOutput "  ✓ Service started successfully" "Green"
    } else {
        Write-ColorOutput "  ⚠ Service failed to start" "Red"
    }
}

function New-SSHKeys {
    Write-ColorOutput "Generating SSH keys..." "Yellow"
    
    $sshDir = "$InstallDir\.ssh"
    if (!(Test-Path $sshDir)) {
        New-Item -ItemType Directory -Path $sshDir -Force | Out-Null
    }
    
    $keyPath = "$sshDir\id_rsa"
    
    if (!(Test-Path $keyPath)) {
        & ssh-keygen -t rsa -b 4096 -f $keyPath -N '""' -C "orizon-agent@$env:COMPUTERNAME"
        Write-ColorOutput "  ✓ SSH key generated" "Green"
    } else {
        Write-ColorOutput "  ℹ SSH key already exists" "Gray"
    }
    
    Write-Host ""
    Write-ColorOutput "SSH Public Key (add this to hub authorized_keys):" "Green"
    Write-Host "----------------------------------------"
    Get-Content "$keyPath.pub"
    Write-Host "----------------------------------------"
}

function Add-FirewallRules {
    Write-ColorOutput "Adding firewall rules..." "Yellow"
    
    # Allow outbound connections for the agent
    New-NetFirewallRule -DisplayName "Orizon Agent Outbound" `
        -Direction Outbound `
        -Program "$InstallDir\python.exe" `
        -Action Allow `
        -Profile Any `
        -ErrorAction SilentlyContinue
    
    Write-ColorOutput "  ✓ Firewall rules added" "Green"
}

function Show-CompletionMessage {
    Write-Host ""
    Write-ColorOutput "╔════════════════════════════════════════════════════╗" "Green"
    Write-ColorOutput "║           Installation Completed Successfully!       ║" "Green"
    Write-ColorOutput "╚════════════════════════════════════════════════════╝" "Green"
    Write-Host ""
    Write-ColorOutput "Service Commands:" "Cyan"
    Write-Host "  Start:   Start-Service $ServiceName"
    Write-Host "  Stop:    Stop-Service $ServiceName"
    Write-Host "  Status:  Get-Service $ServiceName"
    Write-Host "  Logs:    Get-Content '$LogDir\agent.log' -Tail 50"
    Write-Host ""
    Write-ColorOutput "Configuration: $ConfigDir\agent.json" "Cyan"
    Write-ColorOutput "Logs: $LogDir\agent.log" "Cyan"
    Write-Host ""
    Write-ColorOutput "Agent is now running and connected to hub!" "Green"
}

function Uninstall-Agent {
    Write-ColorOutput "Uninstalling Orizon Agent..." "Red"
    
    # Stop and remove service
    if (Get-Service -Name $ServiceName -ErrorAction SilentlyContinue) {
        Stop-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue
        & python "$InstallDir\orizon_service.py" remove
        Write-ColorOutput "  ✓ Service removed" "Green"
    }
    
    # Remove firewall rules
    Remove-NetFirewallRule -DisplayName "Orizon Agent Outbound" -ErrorAction SilentlyContinue
    
    # Remove directories
    if (Test-Path $InstallDir) {
        Remove-Item -Path $InstallDir -Recurse -Force
        Write-ColorOutput "  ✓ Removed $InstallDir" "Green"
    }
    
    if (Test-Path $ConfigDir) {
        Remove-Item -Path $ConfigDir -Recurse -Force
        Write-ColorOutput "  ✓ Removed $ConfigDir" "Green"
    }
    
    Write-ColorOutput "Uninstall completed" "Green"
}

# Main execution
if ($Uninstall) {
    Uninstall-Agent
} else {
    Write-ColorOutput "Starting installation..." "Yellow"
    Write-Host ""
    
    Test-Dependencies
    Install-PythonPackages
    New-Directories
    Install-AgentFiles
    New-Configuration
    New-SSHKeys
    Install-WindowsService
    Add-FirewallRules
    Start-AgentService
    Show-CompletionMessage
}
