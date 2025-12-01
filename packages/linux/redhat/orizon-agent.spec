#===============================================================================
#  ORIZON ZERO TRUST CONNECT - RPM Spec File
#  For: RedHat, Fedora, CentOS, Rocky Linux, AlmaLinux
#===============================================================================

Name:           orizon-agent
Version:        2.1.0
Release:        1%{?dist}
Summary:        Orizon Zero Trust Connect Agent

License:        Proprietary
URL:            https://orizon.one
Source0:        %{name}-%{version}.tar.gz

BuildArch:      noarch
Requires:       openssh-clients
Requires:       autossh
Requires:       curl
Requires:       jq

%description
Enterprise-grade Zero Trust agent that creates secure reverse SSH tunnels
to connect edge servers to the Orizon Hub infrastructure.

Features:
- Secure SSH reverse tunnels (Ed25519 encryption)
- Multi-hub support for redundancy
- Automatic reconnection with autossh
- System management, terminal access, and HTTPS proxy tunnels
- Watchdog service for reliability
- No inbound ports required (outbound only)

After installation, run: orizon-setup

%prep
%setup -q

%install
mkdir -p %{buildroot}/opt/orizon
mkdir -p %{buildroot}/etc/orizon
mkdir -p %{buildroot}/usr/local/bin
mkdir -p %{buildroot}/var/log/orizon

# Copy main installer/setup script
install -m 755 orizon-agent-install.sh %{buildroot}/opt/orizon/orizon-setup

# Create symlink
ln -sf /opt/orizon/orizon-setup %{buildroot}/usr/local/bin/orizon-setup

%files
%defattr(-,root,root,-)
/opt/orizon/
/etc/orizon/
/var/log/orizon/
/usr/local/bin/orizon-setup

%post
echo ""
echo "╔═══════════════════════════════════════════════════════════════════╗"
echo "║     ORIZON ZERO TRUST CONNECT - Package Installed                 ║"
echo "╚═══════════════════════════════════════════════════════════════════╝"
echo ""
echo "The following components have been installed:"
echo ""
echo "  AUTOSSH"
echo "    Purpose: Maintains persistent SSH tunnel connections"
echo "    Automatically restarts tunnels if they disconnect"
echo ""
echo "  OPENSSH CLIENT"
echo "    Purpose: Creates encrypted connections to Orizon Hub"
echo "    Uses Ed25519 keys for maximum security"
echo ""
echo "NEXT STEPS:"
echo ""
echo "  1. Run the setup wizard to configure your node:"
echo ""
echo "     sudo orizon-setup"
echo ""
echo "  2. The wizard will guide you through:"
echo "     - Entering your Node ID and Hub server addresses"
echo "     - Generating SSH keys"
echo "     - Creating and starting the tunnel services"
echo ""
echo "  For help: orizon-setup --help"
echo "  Documentation: https://docs.orizon.one"
echo ""

%preun
echo ""
echo "Stopping Orizon services..."

# Stop all Orizon tunnel services
for service in $(systemctl list-units --type=service --all 2>/dev/null | grep 'orizon' | awk '{print $1}'); do
    echo "  Stopping $service..."
    systemctl stop "$service" 2>/dev/null || true
    systemctl disable "$service" 2>/dev/null || true
done

# Remove service files
rm -f /etc/systemd/system/orizon-tunnel-*.service 2>/dev/null || true
rm -f /etc/systemd/system/orizon-watchdog.service 2>/dev/null || true

# Reload systemd
systemctl daemon-reload 2>/dev/null || true

echo ""
echo "Orizon services stopped and disabled."
echo ""
echo "Note: Configuration files in /etc/orizon and SSH keys in"
echo "      /opt/orizon/.ssh have been preserved."
echo ""
echo "To completely remove all data, run:"
echo "  sudo rm -rf /opt/orizon /etc/orizon /var/log/orizon"
echo ""

%changelog
* Sun Dec 01 2024 Orizon Team <support@orizon.one> - 2.1.0-1
- Multi-hub support for redundancy
- Improved watchdog service
- Enhanced installation documentation
- Support for system, terminal, and HTTPS tunnels
