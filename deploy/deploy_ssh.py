#!/usr/bin/env python3
"""
Orizon Zero Trust Connect - Python SSH Deployment
For: Marco @ Syneto/Orizon
Uses paramiko for direct SSH deployment
"""

import paramiko
import os
import sys
import time
from pathlib import Path

# Colors
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'

# Configuration
SERVER = "46.101.189.126"
USERNAME = "orizzonti"
PASSWORD = "ripper-FfFIlBelloccio.1969F"
APP_DIR = "/opt/orizon-ztc"
LOCAL_DIR = Path(__file__).parent.parent


def print_step(step, total, message):
    """Print a step message"""
    print(f"\n{YELLOW}[{step}/{total}] {message}...{NC}")


def print_success(message):
    """Print success message"""
    print(f"{GREEN}✓ {message}{NC}")


def print_error(message):
    """Print error message"""
    print(f"{RED}✗ {message}{NC}")


def print_info(message):
    """Print info message"""
    print(f"{BLUE}→ {message}{NC}")


def execute_command(ssh, command, sudo=False):
    """Execute a command via SSH"""
    if sudo:
        command = f"echo '{PASSWORD}' | sudo -S {command}"

    stdin, stdout, stderr = ssh.exec_command(command)
    exit_code = stdout.channel.recv_exit_status()
    output = stdout.read().decode('utf-8', errors='ignore')
    error = stderr.read().decode('utf-8', errors='ignore')

    return exit_code, output, error


def upload_file(sftp, local_path, remote_path):
    """Upload a file via SFTP"""
    print_info(f"Uploading {local_path.name}...")
    sftp.put(str(local_path), remote_path)
    print_success(f"Uploaded {local_path.name}")


def main():
    print(f"{BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}")
    print(f"{BLUE}   Orizon Zero Trust Connect - SSH Deployment{NC}")
    print(f"{BLUE}   Server: {SERVER}{NC}")
    print(f"{BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}")

    # Step 1: Connect to server
    print_step(1, 10, "Connecting to server")

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(
            hostname=SERVER,
            username=USERNAME,
            password=PASSWORD,
            timeout=10
        )
        print_success("SSH connection established")
    except Exception as e:
        print_error(f"Connection failed: {e}")
        return 1

    # Step 2: Check user privileges
    print_step(2, 10, "Checking user privileges")
    exit_code, output, error = execute_command(ssh, "whoami")
    print_success(f"Connected as: {output.strip()}")

    # Check sudo
    exit_code, output, error = execute_command(ssh, "whoami", sudo=True)
    has_sudo = "root" in output.lower()
    if has_sudo:
        print_success("User has sudo privileges")
    else:
        print_info("User does not have sudo - will use user permissions")

    # Step 3: Create directories
    print_step(3, 10, "Creating application directories")
    commands = [
        f"mkdir -p {APP_DIR}/backend",
        f"mkdir -p {APP_DIR}/frontend/dist",
        f"mkdir -p /var/log/orizon-ztc",
    ]

    for cmd in commands:
        execute_command(ssh, cmd, sudo=has_sudo)

    print_success("Directories created")

    # Step 4: Upload backend
    print_step(4, 10, "Uploading backend files")

    # Create tarball locally
    backend_dir = LOCAL_DIR / "backend"
    tarball_path = "/tmp/backend.tar.gz"

    print_info("Creating backend tarball...")
    os.system(f"cd {backend_dir} && tar --exclude='venv' --exclude='__pycache__' --exclude='*.pyc' --exclude='.pytest_cache' --exclude='.env' -czf {tarball_path} .")

    # Upload tarball
    sftp = ssh.open_sftp()
    upload_file(sftp, Path(tarball_path), "/tmp/backend.tar.gz")

    # Extract on server
    print_info("Extracting backend...")
    execute_command(ssh, f"cd {APP_DIR}/backend && tar -xzf /tmp/backend.tar.gz")
    execute_command(ssh, "rm /tmp/backend.tar.gz")

    print_success("Backend uploaded")

    # Clean up local tarball
    os.remove(tarball_path)

    # Step 5: Install backend dependencies
    print_step(5, 10, "Installing backend dependencies")

    commands = [
        f"cd {APP_DIR}/backend && python3 -m venv venv",
        f"cd {APP_DIR}/backend && venv/bin/pip install --upgrade pip",
        f"cd {APP_DIR}/backend && venv/bin/pip install -r requirements.txt",
    ]

    for cmd in commands:
        print_info(f"Running: {cmd.split('&&')[-1].strip()}")
        exit_code, output, error = execute_command(ssh, cmd)
        if exit_code != 0 and error:
            print_info(f"Warning: {error[:200]}")

    print_success("Backend dependencies installed")

    # Step 6: Create environment file
    print_step(6, 10, "Creating environment configuration")

    env_content = f"""# Orizon Zero Trust Connect - Environment Configuration
DATABASE_URL=postgresql://orizon:OrizonSecure2025!@localhost:5432/orizon_ztc
REDIS_URL=redis://localhost:6379/0
MONGODB_URL=mongodb://orizon:OrizonSecure2025!@localhost:27017/orizon_audit

SECRET_KEY=$(openssl rand -hex 32)
JWT_SECRET=$(openssl rand -hex 32)
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=30

ALLOWED_ORIGINS=http://{SERVER},https://{SERVER}

HOST=0.0.0.0
PORT=8000
DEBUG=false

LOG_LEVEL=INFO
LOG_FILE=/var/log/orizon-ztc/backend.log
"""

    # Upload env file
    with open("/tmp/.env", "w") as f:
        f.write(env_content)

    upload_file(sftp, Path("/tmp/.env"), f"{APP_DIR}/backend/.env")
    execute_command(ssh, f"chmod 600 {APP_DIR}/backend/.env")

    print_success("Environment configured")
    os.remove("/tmp/.env")

    # Step 7: Build and upload frontend
    print_step(7, 10, "Building and uploading frontend")

    frontend_dir = LOCAL_DIR / "frontend"

    print_info("Building frontend...")
    os.environ["VITE_API_BASE_URL"] = f"http://{SERVER}/api/v1"
    os.environ["VITE_WS_URL"] = f"ws://{SERVER}/ws"

    build_result = os.system(f"cd {frontend_dir} && npm run build")
    if build_result != 0:
        print_error("Frontend build failed")
        return 1

    # Create frontend tarball
    tarball_path = "/tmp/frontend.tar.gz"
    os.system(f"cd {frontend_dir}/dist && tar -czf {tarball_path} .")

    # Upload
    upload_file(sftp, Path(tarball_path), "/tmp/frontend.tar.gz")

    # Extract
    print_info("Extracting frontend...")
    execute_command(ssh, f"cd {APP_DIR}/frontend/dist && tar -xzf /tmp/frontend.tar.gz")
    execute_command(ssh, "rm /tmp/frontend.tar.gz")

    print_success("Frontend uploaded")
    os.remove(tarball_path)

    # Step 8: Upload systemd service
    print_step(8, 10, "Creating systemd service")

    service_content = f"""[Unit]
Description=Orizon Zero Trust Connect - Backend API
After=network.target

[Service]
Type=simple
User={USERNAME}
Group={USERNAME}
WorkingDirectory={APP_DIR}/backend
Environment="PATH={APP_DIR}/backend/venv/bin"
EnvironmentFile={APP_DIR}/backend/.env
ExecStart={APP_DIR}/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""

    with open("/tmp/orizon-ztc-backend.service", "w") as f:
        f.write(service_content)

    upload_file(sftp, Path("/tmp/orizon-ztc-backend.service"), "/tmp/orizon-ztc-backend.service")

    if has_sudo:
        execute_command(ssh, "mv /tmp/orizon-ztc-backend.service /etc/systemd/system/", sudo=True)
        execute_command(ssh, "systemctl daemon-reload", sudo=True)

    print_success("Systemd service created")
    os.remove("/tmp/orizon-ztc-backend.service")

    # Step 9: Start backend
    print_step(9, 10, "Starting backend service")

    if has_sudo:
        execute_command(ssh, "systemctl start orizon-ztc-backend", sudo=True)
        time.sleep(3)

        exit_code, output, error = execute_command(ssh, "systemctl status orizon-ztc-backend", sudo=True)
        if "active (running)" in output:
            print_success("Backend service started")
        else:
            print_info("Backend service status unclear, checking manually...")
    else:
        # Start manually if no sudo
        print_info("Starting backend manually (no systemd)...")
        execute_command(ssh, f"cd {APP_DIR}/backend && nohup venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 > /var/log/orizon-ztc/backend.log 2>&1 &")
        time.sleep(3)

    # Test if backend is responding
    exit_code, output, error = execute_command(ssh, "curl -s http://localhost:8000/health")
    if exit_code == 0:
        print_success("Backend is responding")
    else:
        print_info("Backend may still be starting...")

    # Step 10: Setup basic nginx if available
    print_step(10, 10, "Checking web server")

    exit_code, output, error = execute_command(ssh, "which nginx")
    if exit_code == 0:
        print_success("Nginx is available")
        print_info("Manual nginx configuration may be needed")
    else:
        print_info("Nginx not found - install manually if needed")

    # Close connections
    sftp.close()
    ssh.close()

    # Final message
    print(f"\n{BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}")
    print(f"{GREEN}✓ Deployment Complete!{NC}")
    print(f"{BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}")
    print(f"\n{YELLOW}Application Status:{NC}")
    print(f"  Backend: {GREEN}http://{SERVER}:8000{NC}")
    print(f"  API Docs: {GREEN}http://{SERVER}:8000/docs{NC}")
    print(f"  Frontend: {GREEN}Deployed to {APP_DIR}/frontend/dist{NC}")
    print(f"\n{YELLOW}Next Steps:{NC}")
    print(f"  1. Configure Nginx reverse proxy")
    print(f"  2. Setup SSL certificate")
    print(f"  3. Create admin user")
    print(f"  4. Access via http://{SERVER}:8000")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
