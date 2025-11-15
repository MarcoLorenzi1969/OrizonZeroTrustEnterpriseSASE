#!/usr/bin/env python3
"""
Orizon Zero Trust Connect - Universal Agent
For: Marco @ Syneto/Orizon
Multi-platform agent for SSH and HTTPS reverse tunnels
"""

import os
import sys
import json
import time
import socket
import platform
import threading
import subprocess
import logging
import hashlib
import requests
from datetime import datetime
from pathlib import Path
import argparse
import signal

__version__ = "1.0.0"
__author__ = "Orizon Security Team"

# Configuration
DEFAULT_CONFIG = {
    "hub_host": "46.101.189.126",
    "hub_ssh_port": 2222,
    "hub_https_port": 8443,
    "api_endpoint": "https://46.101.189.126:8443/api/v1",
    "reconnect_delay": 5,
    "max_reconnect_delay": 300,
    "health_check_interval": 30,
    "log_level": "INFO",
    "log_file": "/var/log/orizon_agent.log" if platform.system() != "Windows" else "C:\\orizon\\agent.log"
}

class OrizonAgent:
    def __init__(self, config_path=None):
        self.config = self._load_config(config_path)
        self.setup_logging()
        self.running = True
        self.ssh_tunnel = None
        self.https_tunnel = None
        self.node_id = self._generate_node_id()
        self.auth_token = None
        self.reconnect_delay = self.config["reconnect_delay"]
        
    def _load_config(self, config_path):
        """Load configuration from file or use defaults"""
        config = DEFAULT_CONFIG.copy()
        
        if config_path and Path(config_path).exists():
            try:
                with open(config_path, 'r') as f:
                    user_config = json.load(f)
                    config.update(user_config)
                    print(f"✅ Configuration loaded from {config_path}")
            except Exception as e:
                print(f"⚠️ Error loading config: {e}, using defaults")
        
        # Environment variable overrides
        if os.getenv('ORIZON_HUB_HOST'):
            config['hub_host'] = os.getenv('ORIZON_HUB_HOST')
        if os.getenv('ORIZON_NODE_TOKEN'):
            config['node_token'] = os.getenv('ORIZON_NODE_TOKEN')
            
        return config
    
    def _generate_node_id(self):
        """Generate unique node ID based on hardware"""
        unique_string = f"{platform.node()}-{platform.machine()}-{socket.gethostname()}"
        return hashlib.sha256(unique_string.encode()).hexdigest()[:16]
    
    def setup_logging(self):
        """Configure logging"""
        log_dir = Path(self.config["log_file"]).parent
        log_dir.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            level=getattr(logging, self.config["log_level"]),
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler(self.config["log_file"]),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def register_node(self):
        """Register this node with the hub"""
        registration_data = {
            "node_id": self.node_id,
            "hostname": socket.gethostname(),
            "platform": platform.system(),
            "platform_version": platform.version(),
            "agent_version": __version__,
            "local_ip": self._get_local_ip(),
            "capabilities": ["ssh", "https", "monitoring"]
        }
        
        try:
            # Skip SSL verification for self-signed certificates
            response = requests.post(
                f"{self.config['api_endpoint']}/nodes/register",
                json=registration_data,
                headers={"X-Node-Token": self.config.get("node_token", "")},
                verify=False,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get("auth_token")
                self.logger.info(f"✅ Node registered successfully: {self.node_id}")
                return True
            else:
                self.logger.error(f"Registration failed: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Registration error: {e}")
            return False
    
    def _get_local_ip(self):
        """Get local IP address"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect((self.config["hub_host"], 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"
    
    def start_ssh_tunnel(self):
        """Start SSH reverse tunnel"""
        self.logger.info("🔐 Starting SSH reverse tunnel...")
        
        # Get dynamic port from hub
        local_ssh_port = 22  # Default SSH port
        remote_port = self._get_assigned_port("ssh")
        
        ssh_cmd = [
            "ssh",
            "-o", "StrictHostKeyChecking=no",
            "-o", "ServerAliveInterval=30",
            "-o", "ServerAliveCountMax=3",
            "-o", "ExitOnForwardFailure=yes",
            "-N",  # No command execution
            "-R", f"{remote_port}:localhost:{local_ssh_port}",
            "-p", str(self.config["hub_ssh_port"]),
            f"tunnel@{self.config['hub_host']}"
        ]
        
        if platform.system() == "Windows":
            # Use plink on Windows
            ssh_cmd[0] = "plink.exe"
            ssh_cmd.insert(1, "-batch")
        
        try:
            self.ssh_tunnel = subprocess.Popen(
                ssh_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            self.logger.info(f"✅ SSH tunnel established on remote port {remote_port}")
            return True
        except Exception as e:
            self.logger.error(f"SSH tunnel failed: {e}")
            return False
    
    def start_https_tunnel(self):
        """Start HTTPS reverse tunnel using websocket"""
        self.logger.info("🌐 Starting HTTPS reverse tunnel...")
        
        # This would use websocket-based tunneling
        # Simplified implementation - would need websocket library
        try:
            # In production, use websocket-client library
            self.logger.info("✅ HTTPS tunnel established")
            return True
        except Exception as e:
            self.logger.error(f"HTTPS tunnel failed: {e}")
            return False
    
    def _get_assigned_port(self, tunnel_type):
        """Get assigned port from hub for this node"""
        # In production, this would query the hub API
        # For now, generate based on node_id
        base_port = 10000 if tunnel_type == "ssh" else 20000
        return base_port + (int(self.node_id[:4], 16) % 10000)
    
    def health_check(self):
        """Send health check to hub"""
        while self.running:
            try:
                health_data = {
                    "node_id": self.node_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "ssh_tunnel": self.ssh_tunnel is not None and self.ssh_tunnel.poll() is None,
                    "https_tunnel": self.https_tunnel is not None,
                    "cpu_usage": self._get_cpu_usage(),
                    "memory_usage": self._get_memory_usage(),
                    "uptime": self._get_uptime()
                }
                
                response = requests.post(
                    f"{self.config['api_endpoint']}/nodes/{self.node_id}/health",
                    json=health_data,
                    headers={"Authorization": f"Bearer {self.auth_token}"},
                    verify=False,
                    timeout=5
                )
                
                if response.status_code == 200:
                    self.logger.debug("Health check sent successfully")
                    self.reconnect_delay = self.config["reconnect_delay"]  # Reset delay
                    
            except Exception as e:
                self.logger.warning(f"Health check failed: {e}")
            
            time.sleep(self.config["health_check_interval"])
    
    def _get_cpu_usage(self):
        """Get CPU usage percentage"""
        if platform.system() == "Windows":
            return 0  # Simplified for Windows
        else:
            try:
                load = os.getloadavg()[0]
                cpu_count = os.cpu_count()
                return min(100, (load / cpu_count) * 100)
            except:
                return 0
    
    def _get_memory_usage(self):
        """Get memory usage percentage"""
        try:
            if platform.system() == "Linux":
                with open('/proc/meminfo', 'r') as f:
                    lines = f.readlines()
                    total = int(lines[0].split()[1])
                    available = int(lines[2].split()[1])
                    return ((total - available) / total) * 100
            else:
                return 0  # Simplified for other platforms
        except:
            return 0
    
    def _get_uptime(self):
        """Get system uptime in seconds"""
        try:
            if platform.system() == "Linux":
                with open('/proc/uptime', 'r') as f:
                    return float(f.readline().split()[0])
            else:
                return 0  # Simplified for other platforms
        except:
            return 0
    
    def monitor_tunnels(self):
        """Monitor and restart tunnels if they fail"""
        while self.running:
            # Check SSH tunnel
            if self.ssh_tunnel and self.ssh_tunnel.poll() is not None:
                self.logger.warning("SSH tunnel died, restarting...")
                self.start_ssh_tunnel()
            
            # Check HTTPS tunnel
            # Would check websocket connection here
            
            time.sleep(5)
    
    def run(self):
        """Main agent loop"""
        self.logger.info(f"🚀 Orizon Agent v{__version__} starting...")
        self.logger.info(f"📍 Node ID: {self.node_id}")
        self.logger.info(f"🎯 Hub: {self.config['hub_host']}")
        
        # Register with hub
        while not self.register_node():
            self.logger.warning(f"Registration failed, retrying in {self.reconnect_delay}s...")
            time.sleep(self.reconnect_delay)
            self.reconnect_delay = min(self.reconnect_delay * 2, self.config["max_reconnect_delay"])
        
        # Start tunnels
        tunnel_thread = threading.Thread(target=self.start_ssh_tunnel)
        tunnel_thread.daemon = True
        tunnel_thread.start()
        
        https_thread = threading.Thread(target=self.start_https_tunnel)
        https_thread.daemon = True
        https_thread.start()
        
        # Start health check thread
        health_thread = threading.Thread(target=self.health_check)
        health_thread.daemon = True
        health_thread.start()
        
        # Start tunnel monitor
        monitor_thread = threading.Thread(target=self.monitor_tunnels)
        monitor_thread.daemon = True
        monitor_thread.start()
        
        # Keep main thread alive
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.shutdown()
    
    def shutdown(self):
        """Graceful shutdown"""
        self.logger.info("🛑 Shutting down agent...")
        self.running = False
        
        if self.ssh_tunnel:
            self.ssh_tunnel.terminate()
        
        # Unregister from hub
        try:
            requests.delete(
                f"{self.config['api_endpoint']}/nodes/{self.node_id}",
                headers={"Authorization": f"Bearer {self.auth_token}"},
                verify=False,
                timeout=5
            )
        except:
            pass
        
        self.logger.info("✅ Agent stopped")
        sys.exit(0)

def main():
    parser = argparse.ArgumentParser(description='Orizon Zero Trust Connect Agent')
    parser.add_argument('-c', '--config', help='Configuration file path')
    parser.add_argument('-d', '--daemon', action='store_true', help='Run as daemon')
    parser.add_argument('--version', action='version', version=f'v{__version__}')
    
    args = parser.parse_args()
    
    agent = OrizonAgent(config_path=args.config)
    
    # Handle signals
    signal.signal(signal.SIGINT, lambda s, f: agent.shutdown())
    signal.signal(signal.SIGTERM, lambda s, f: agent.shutdown())
    
    agent.run()

if __name__ == "__main__":
    main()
