#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Orizon Zero Trust Connect - Windows Uninstaller

.DESCRIPTION
    Completely removes the Orizon agent from Windows including:
    - All services (tunnels, nginx, metrics)
    - Scheduled tasks (watchdog)
    - Firewall rules
    - Installation directory (optional)

.PARAMETER KeepData
    If specified, keeps the C:\ProgramData\Orizon directory

.EXAMPLE
    # Full removal
    .\Uninstall-Orizon.ps1

    # Keep configuration and logs
    .\Uninstall-Orizon.ps1 -KeepData
#>

param(
    [switch]$KeepData
)

$InstallPath = "C:\ProgramData\Orizon"
$ToolsPath = "$InstallPath\tools"

Write-Host ""
Write-Host "╔═══════════════════════════════════════════════════╗" -ForegroundColor Yellow
Write-Host "║     ORIZON ZERO TRUST CONNECT - UNINSTALLER       ║" -ForegroundColor Yellow
Write-Host "╚═══════════════════════════════════════════════════╝" -ForegroundColor Yellow
Write-Host ""

$confirm = Read-Host "Are you sure you want to uninstall Orizon? (yes/no)"
if ($confirm -ne "yes") {
    Write-Host "Uninstall cancelled." -ForegroundColor Gray
    exit 0
}

Write-Host ""
Write-Host "[1/5] Stopping and removing services..." -ForegroundColor Cyan

$services = @(
    "OrizonTunnelSystem",
    "OrizonTunnelTerminal",
    "OrizonNginx",
    "OrizonMetrics"
)

$nssmPath = Join-Path $ToolsPath "nssm.exe"

foreach ($service in $services) {
    $svc = Get-Service -Name $service -ErrorAction SilentlyContinue
    if ($svc) {
        Write-Host "  Removing $service..." -ForegroundColor Gray
        Stop-Service -Name $service -Force -ErrorAction SilentlyContinue
        if (Test-Path $nssmPath) {
            & $nssmPath remove $service confirm 2>&1 | Out-Null
        } else {
            sc.exe delete $service 2>&1 | Out-Null
        }
        Write-Host "  [$service] Removed" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "[2/5] Removing scheduled tasks..." -ForegroundColor Cyan

$tasks = @("OrizonWatchdog")

foreach ($task in $tasks) {
    $t = Get-ScheduledTask -TaskName $task -ErrorAction SilentlyContinue
    if ($t) {
        Write-Host "  Removing $task..." -ForegroundColor Gray
        Unregister-ScheduledTask -TaskName $task -Confirm:$false
        Write-Host "  [$task] Removed" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "[3/5] Removing firewall rules..." -ForegroundColor Cyan

$rules = Get-NetFirewallRule -DisplayName "Orizon*" -ErrorAction SilentlyContinue
if ($rules) {
    $rules | Remove-NetFirewallRule
    Write-Host "  Orizon firewall rules removed" -ForegroundColor Green
} else {
    Write-Host "  No firewall rules found" -ForegroundColor Gray
}

Write-Host ""
Write-Host "[4/5] Cleaning up SSL certificates..." -ForegroundColor Cyan

# Remove self-signed certificates from store
Get-ChildItem -Path Cert:\LocalMachine\My | Where-Object { $_.Subject -like "*Orizon*" } | ForEach-Object {
    Write-Host "  Removing certificate: $($_.Subject)" -ForegroundColor Gray
    Remove-Item -Path $_.PSPath -Force
}

Write-Host ""
Write-Host "[5/5] Removing installation directory..." -ForegroundColor Cyan

if (-not $KeepData) {
    if (Test-Path $InstallPath) {
        # Stop any remaining processes
        Get-Process -Name "nginx" -ErrorAction SilentlyContinue | Stop-Process -Force
        Get-Process -Name "ssh" -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "*Orizon*" } | Stop-Process -Force

        Start-Sleep -Seconds 2

        Remove-Item -Path $InstallPath -Recurse -Force -ErrorAction SilentlyContinue
        if (Test-Path $InstallPath) {
            Write-Host "  Warning: Could not completely remove $InstallPath" -ForegroundColor Yellow
            Write-Host "  Some files may be in use. Retry after reboot." -ForegroundColor Yellow
        } else {
            Write-Host "  $InstallPath removed" -ForegroundColor Green
        }
    }
} else {
    Write-Host "  Keeping $InstallPath (KeepData flag set)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "╔═══════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║          UNINSTALLATION COMPLETE                  ║" -ForegroundColor Green
Write-Host "╚═══════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "Orizon Zero Trust Connect has been removed from this system." -ForegroundColor Gray
Write-Host ""

if (-not $KeepData) {
    Write-Host "Note: The node may still appear in the Hub dashboard." -ForegroundColor Yellow
    Write-Host "Please remove it manually from the Orizon web interface." -ForegroundColor Yellow
}

Write-Host ""
