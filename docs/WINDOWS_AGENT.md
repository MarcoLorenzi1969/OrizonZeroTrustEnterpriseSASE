# Windows Agent - Orizon Zero Trust Connect

## Panoramica / Overview

L'Agent Windows permette di connettere workstation e server Windows alla piattaforma Orizon Zero Trust. Supporta Windows 10/11 e Windows Server 2019/2022.

*The Windows Agent enables connecting Windows workstations and servers to the Orizon Zero Trust platform. Supports Windows 10/11 and Windows Server 2019/2022.*

---

## Requisiti / Requirements

### Sistema Operativo / Operating System

| OS | Versione Minima | Architettura |
|----|-----------------|--------------|
| Windows 10 | 1903+ | x64 |
| Windows 11 | 21H2+ | x64 |
| Windows Server | 2019+ | x64 |

### Prerequisiti / Prerequisites

- PowerShell 5.1 o superiore
- Accesso amministratore
- Connettività alla porta 2222 dell'Hub
- OpenSSH Client (incluso in Windows 10+)

---

## Installazione / Installation

### Metodo 1: Script Automatico (Consigliato)

Dalla dashboard Orizon, generare lo script di installazione:

*From the Orizon dashboard, generate the installation script:*

1. Vai a **Nodes** → **Create Node**
2. Seleziona **Windows** come tipo di nodo
3. Compila i dettagli del nodo
4. Clicca **Download Script**
5. Esegui come Amministratore:

```powershell
# PowerShell (Amministratore)
Set-ExecutionPolicy Bypass -Scope Process -Force
.\install_orizon_agent.ps1
```

### Metodo 2: Installer Unificato

```powershell
# Download e esecuzione
Invoke-WebRequest -Uri "https://HUB_IP/downloads/orizon_unified_installer.ps1" -OutFile "install.ps1"
.\install.ps1 -NodeId "YOUR_NODE_ID" -AgentToken "YOUR_TOKEN" -HubHost "HUB_IP"
```

---

## Struttura Directory / Directory Structure

```
C:\ProgramData\Orizon\
├── .ssh\
│   ├── id_ed25519           # Chiave privata / Private key
│   └── id_ed25519.pub       # Chiave pubblica / Public key
├── bin\
│   └── nssm.exe             # Service manager
├── config\
│   └── orizon.conf          # Configurazione agent
├── logs\
│   ├── tunnel-system.log    # Log tunnel sistema
│   ├── tunnel-terminal.log  # Log tunnel terminale
│   ├── tunnel-https.log     # Log tunnel HTTPS
│   └── watchdog.log         # Log watchdog
├── www\
│   └── index.html           # Status page locale
└── scripts\
    ├── metrics-collector.ps1
    └── watchdog.ps1
```

---

## Servizi Windows / Windows Services

L'installer crea i seguenti servizi:

*The installer creates the following services:*

| Servizio | Descrizione | Stato |
|----------|-------------|-------|
| OrizonTunnelSystem | Tunnel SSH principale | Auto Start |
| OrizonTunnelTerminal | Tunnel per terminale web | Auto Start |
| OrizonTunnelHTTPS | Tunnel per proxy HTTPS | Auto Start |
| OrizonMetricsCollector | Raccolta metriche sistema | Auto Start |
| OrizonWatchdog | Monitoraggio e riavvio | Auto Start |
| OrizonStatusServer | Server status page locale | Auto Start |

### Gestione Servizi / Service Management

```powershell
# Verifica stato / Check status
Get-Service -Name "Orizon*"

# Riavvia tutti / Restart all
Get-Service -Name "Orizon*" | Restart-Service

# Ferma tutto / Stop all
Get-Service -Name "Orizon*" | Stop-Service

# Avvia tutto / Start all
Get-Service -Name "Orizon*" | Start-Service
```

---

## Configurazione Tunnel / Tunnel Configuration

### File di Configurazione

`C:\ProgramData\Orizon\config\orizon.conf`:

```ini
[hub]
host = HUB_IP
port = 2222
node_id = xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
agent_token = agt_xxxxxxxxxxxxxxxxx

[tunnels]
system_port = 9128
system_local = 22
terminal_port = 9129
terminal_local = 22
https_port = 9130
https_local = 443

[keepalive]
server_alive_interval = 15
server_alive_count_max = 3

[watchdog]
enabled = true
check_interval = 60
max_restart_attempts = 5
```

### Parametri SSH Hardened

```powershell
# Comando SSH tunnel (eseguito dal servizio)
ssh.exe -N `
  -o ServerAliveInterval=15 `
  -o ServerAliveCountMax=3 `
  -o ExitOnForwardFailure=yes `
  -o StrictHostKeyChecking=no `
  -o UserKnownHostsFile=NUL `
  -o BatchMode=yes `
  -i "C:\ProgramData\Orizon\.ssh\id_ed25519" `
  -p 2222 `
  -R 9128:localhost:22 `
  NODE_ID@HUB_IP
```

---

## Status Page Locale / Local Status Page

L'agent include un server web locale per la pagina di stato:

*The agent includes a local web server for the status page:*

- **URL Locale**: `http://localhost:8443` o `https://localhost:443`
- **Metriche**: CPU, RAM, Disco, GPU (se disponibile)
- **Stato Tunnel**: Online/Offline per ogni tunnel
- **Auto-refresh**: Ogni 10 secondi

### Accesso via Hub Proxy

Dalla dashboard, clicca sull'icona della pagina di stato del nodo:

```
https://HUB_IP/api/v1/nodes/{node_id}/https-proxy?t=TOKEN
```

---

## Raccolta Metriche / Metrics Collection

### Script Metrics Collector

`C:\ProgramData\Orizon\scripts\metrics-collector.ps1`:

```powershell
# Metriche raccolte / Collected metrics
$metrics = @{
    hostname = $env:COMPUTERNAME
    os = (Get-WmiObject Win32_OperatingSystem).Caption
    uptime = (Get-Uptime).ToString()
    cpu_usage = (Get-Counter '\Processor(_Total)\% Processor Time').CounterSamples.CookedValue
    memory_usage = [math]::Round((1 - (Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory /
                   (Get-CimInstance Win32_OperatingSystem).TotalVisibleMemorySize) * 100, 2)
    disk_usage = [math]::Round((1 - (Get-PSDrive C).Free / (Get-PSDrive C).Used) * 100, 2)
    gpu_info = Get-WmiObject Win32_VideoController | Select-Object Name, AdapterRAM
}
```

### API Metrics Endpoint

```json
GET /api/metrics

{
  "hostname": "DESKTOP-WIN11",
  "os": "Microsoft Windows 11 Pro",
  "uptime": "2.04:32:15",
  "cpu_usage": 23.5,
  "memory_usage": 67.2,
  "memory_detail": "10.8 GB / 16 GB",
  "disk_usage": 45.3,
  "disk_detail": "213 GB / 476 GB",
  "gpu_model": "NVIDIA GeForce RTX 3080",
  "tunnel_system": true,
  "tunnel_terminal": true,
  "tunnel_https": true,
  "last_update": "2025-11-30T16:45:00Z"
}
```

---

## Watchdog

Il servizio Watchdog monitora e riavvia i tunnel se necessario:

*The Watchdog service monitors and restarts tunnels if necessary:*

### Funzionalità / Features

- Monitora stato tunnel ogni 60 secondi
- Riavvia tunnel se disconnesso
- Invia heartbeat all'Hub
- Log eventi in `watchdog.log`
- Max 5 tentativi di riavvio per ciclo

### Script Watchdog

```powershell
# C:\ProgramData\Orizon\scripts\watchdog.ps1
while ($true) {
    $services = @("OrizonTunnelSystem", "OrizonTunnelTerminal", "OrizonTunnelHTTPS")

    foreach ($svc in $services) {
        $service = Get-Service -Name $svc -ErrorAction SilentlyContinue
        if ($service.Status -ne "Running") {
            Write-Log "Service $svc not running, restarting..."
            Start-Service -Name $svc
            $restartCount++
        }
    }

    # Test connettività tunnel
    $tunnelTest = Test-NetConnection -ComputerName HUB_IP -Port 2222
    if (-not $tunnelTest.TcpTestSucceeded) {
        Write-Log "Hub connectivity lost, waiting for network..."
    }

    Start-Sleep -Seconds 60
}
```

---

## Disinstallazione / Uninstallation

### Script di Disinstallazione

```powershell
# PowerShell (Amministratore)
C:\ProgramData\Orizon\Uninstall-Orizon.ps1
```

### Disinstallazione Manuale

```powershell
# Ferma e rimuovi servizi
$services = @("OrizonTunnelSystem", "OrizonTunnelTerminal", "OrizonTunnelHTTPS",
              "OrizonMetricsCollector", "OrizonWatchdog", "OrizonStatusServer")

foreach ($svc in $services) {
    Stop-Service -Name $svc -ErrorAction SilentlyContinue
    nssm remove $svc confirm
}

# Rimuovi directory
Remove-Item -Path "C:\ProgramData\Orizon" -Recurse -Force

# Rimuovi dalla dashboard
# DELETE /api/v1/nodes/{node_id}
```

---

## Troubleshooting

### Tunnel Non Si Connette / Tunnel Won't Connect

1. **Verifica servizi**:
   ```powershell
   Get-Service -Name "Orizon*" | Format-Table Name, Status
   ```

2. **Controlla logs**:
   ```powershell
   Get-Content "C:\ProgramData\Orizon\logs\tunnel-system.log" -Tail 50
   ```

3. **Test connettività manuale**:
   ```powershell
   ssh -v -p 2222 -i "C:\ProgramData\Orizon\.ssh\id_ed25519" NODE_ID@HUB_IP
   ```

4. **Verifica firewall Windows**:
   ```powershell
   Get-NetFirewallRule -DisplayName "*Orizon*"
   ```

### Status Page Non Carica / Status Page Won't Load

1. **Verifica nginx locale**:
   ```powershell
   Get-Process -Name "nginx" -ErrorAction SilentlyContinue
   ```

2. **Test locale**:
   ```powershell
   Invoke-WebRequest -Uri "http://localhost:8443/api/metrics"
   ```

3. **Riavvia servizio status**:
   ```powershell
   Restart-Service -Name "OrizonStatusServer"
   ```

### Metriche Non Aggiornate / Metrics Not Updating

1. **Verifica metrics collector**:
   ```powershell
   Get-Service -Name "OrizonMetricsCollector"
   ```

2. **Esegui manualmente**:
   ```powershell
   & "C:\ProgramData\Orizon\scripts\metrics-collector.ps1"
   ```

---

## Logs

### Posizioni Log / Log Locations

| Log | Path | Contenuto |
|-----|------|-----------|
| Tunnel System | `C:\ProgramData\Orizon\logs\tunnel-system.log` | Connessione SSH principale |
| Tunnel Terminal | `C:\ProgramData\Orizon\logs\tunnel-terminal.log` | Tunnel terminale web |
| Tunnel HTTPS | `C:\ProgramData\Orizon\logs\tunnel-https.log` | Tunnel proxy HTTPS |
| Watchdog | `C:\ProgramData\Orizon\logs\watchdog.log` | Monitoraggio servizi |
| Metrics | `C:\ProgramData\Orizon\logs\metrics.log` | Raccolta metriche |

### Visualizzazione Real-Time

```powershell
# Segui log in tempo reale
Get-Content "C:\ProgramData\Orizon\logs\tunnel-system.log" -Wait -Tail 20
```

---

## Sicurezza / Security

### Best Practices

1. **Esegui come SYSTEM**: I servizi girano come LocalSystem
2. **Chiave ED25519**: Più sicura di RSA
3. **No password SSH**: Solo autenticazione chiave
4. **Firewall**: Blocca accessi non autorizzati alla porta 443 locale

### Hardening Consigliato

```powershell
# Imposta permessi restrittivi sulla directory
$acl = Get-Acl "C:\ProgramData\Orizon"
$acl.SetAccessRuleProtection($true, $false)
$rule = New-Object System.Security.AccessControl.FileSystemAccessRule("SYSTEM","FullControl","ContainerInherit,ObjectInherit","None","Allow")
$acl.AddAccessRule($rule)
$rule = New-Object System.Security.AccessControl.FileSystemAccessRule("Administrators","FullControl","ContainerInherit,ObjectInherit","None","Allow")
$acl.AddAccessRule($rule)
Set-Acl "C:\ProgramData\Orizon" $acl
```

---

## Riferimenti / References

- [System Tunnels](SYSTEM_TUNNELS.md) - Documentazione tunnel
- [Architecture](ARCHITECTURE.md) - Architettura generale
- [Deployment](DEPLOYMENT.md) - Guida deployment
- [API Reference](API_REFERENCE.md) - Documentazione API

---

*Ultimo aggiornamento / Last updated: 30 Novembre 2025*
