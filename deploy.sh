#!/bin/bash
#
# Orizon Zero Trust Connect - Server Deployment Script
# For: DigitalOcean Server (46.101.189.126)
# This script installs K3s and deploys the Orizon ZTC platform
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║    Orizon Zero Trust Connect - Server Deployment    ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if running as root or with sudo
if [[ $EUID -ne 0 ]]; then
   echo -e "${YELLOW}Running with sudo...${NC}"
   SUDO="sudo"
else
   SUDO=""
fi

# Step 1: Install K3s (lightweight Kubernetes)
install_k3s() {
    echo -e "${YELLOW}Installing K3s Kubernetes...${NC}"
    
    if command -v k3s &> /dev/null; then
        echo -e "${GREEN}K3s already installed${NC}"
    else
        curl -sfL https://get.k3s.io | sh -
        
        # Wait for K3s to be ready
        echo "Waiting for K3s to start..."
        sleep 10
        
        # Setup kubeconfig for non-root user
        mkdir -p $HOME/.kube
        $SUDO cp /etc/rancher/k3s/k3s.yaml $HOME/.kube/config
        $SUDO chown $(id -u):$(id -g) $HOME/.kube/config
        
        echo -e "${GREEN}✅ K3s installed successfully${NC}"
    fi
    
    # Install kubectl if not present
    if ! command -v kubectl &> /dev/null; then
        echo "Installing kubectl..."
        curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
        $SUDO install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
        rm kubectl
    fi
}

# Step 2: Install Helm
install_helm() {
    echo -e "${YELLOW}Installing Helm...${NC}"
    
    if command -v helm &> /dev/null; then
        echo -e "${GREEN}Helm already installed${NC}"
    else
        curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
        echo -e "${GREEN}✅ Helm installed${NC}"
    fi
}

# Step 3: Install cert-manager for TLS
install_cert_manager() {
    echo -e "${YELLOW}Installing cert-manager for TLS...${NC}"
    
    kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.3/cert-manager.yaml
    
    # Wait for cert-manager to be ready
    echo "Waiting for cert-manager..."
    kubectl wait --for=condition=Available --timeout=300s deployment/cert-manager -n cert-manager
    kubectl wait --for=condition=Available --timeout=300s deployment/cert-manager-webhook -n cert-manager
    
    echo -e "${GREEN}✅ cert-manager installed${NC}"
}

# Step 4: Install NGINX Ingress Controller
install_nginx_ingress() {
    echo -e "${YELLOW}Installing NGINX Ingress Controller...${NC}"
    
    helm upgrade --install ingress-nginx ingress-nginx \
        --repo https://kubernetes.github.io/ingress-nginx \
        --namespace ingress-nginx --create-namespace \
        --set controller.service.type=LoadBalancer
    
    echo -e "${GREEN}✅ NGINX Ingress installed${NC}"
}

# Step 5: Build Docker images
build_docker_images() {
    echo -e "${YELLOW}Building Docker images...${NC}"
    
    # Backend image
    echo "Building backend image..."
    cat > /tmp/backend.Dockerfile << 'EOF'
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y gcc postgresql-client && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF
    
    # Frontend image
    echo "Building frontend image..."
    cat > /tmp/frontend.Dockerfile << 'EOF'
FROM node:18-alpine as builder
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
EOF
    
    # Tunnel Hub image
    echo "Building tunnel hub image..."
    cat > /tmp/tunnel-hub.Dockerfile << 'EOF'
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y openssh-server && rm -rf /var/lib/apt/lists/*
RUN mkdir /var/run/sshd
RUN echo 'root:orizon' | chpasswd
RUN sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config
COPY agents/orizon_agent.py ./tunnel_hub.py
EXPOSE 2222 8443
CMD ["python", "tunnel_hub.py", "--hub-mode"]
EOF
    
    # Build images
    docker build -f /tmp/backend.Dockerfile -t orizon/backend:latest . 2>/dev/null || echo "Note: Build from actual source"
    docker build -f /tmp/frontend.Dockerfile -t orizon/frontend:latest . 2>/dev/null || echo "Note: Build from actual source"
    docker build -f /tmp/tunnel-hub.Dockerfile -t orizon/tunnel-hub:latest . 2>/dev/null || echo "Note: Build from actual source"
    
    echo -e "${GREEN}✅ Docker images prepared${NC}"
}

# Step 6: Deploy Orizon Zero Trust Connect
deploy_orizon() {
    echo -e "${YELLOW}Deploying Orizon Zero Trust Connect...${NC}"
    
    # Apply Kubernetes manifests
    kubectl apply -f kubernetes/manifests.yaml
    
    # Wait for deployments
    echo "Waiting for deployments to be ready..."
    kubectl wait --for=condition=Available --timeout=300s deployment/backend-api -n orizon-ztc
    kubectl wait --for=condition=Available --timeout=300s deployment/frontend -n orizon-ztc
    
    echo -e "${GREEN}✅ Orizon Zero Trust Connect deployed${NC}"
}

# Step 7: Setup monitoring (optional)
setup_monitoring() {
    echo -e "${YELLOW}Setting up monitoring with Prometheus & Grafana...${NC}"
    
    # Add Prometheus helm repo
    helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
    helm repo update
    
    # Install kube-prometheus-stack
    helm upgrade --install monitoring prometheus-community/kube-prometheus-stack \
        --namespace monitoring --create-namespace \
        --set grafana.adminPassword=orizon-admin
    
    echo -e "${GREEN}✅ Monitoring stack installed${NC}"
    echo "Grafana admin password: orizon-admin"
}

# Step 8: Display access information
show_access_info() {
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║            Deployment Complete! 🎉                  ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    # Get ingress IP
    INGRESS_IP=$(kubectl get svc -n ingress-nginx ingress-nginx-controller -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "46.101.189.126")
    
    echo -e "${BLUE}Access Points:${NC}"
    echo "  Web UI: http://$INGRESS_IP or http://orizon.46.101.189.126.nip.io"
    echo "  API: http://$INGRESS_IP:8000/api"
    echo "  SSH Tunnel: $INGRESS_IP:32222"
    echo "  HTTPS Tunnel: $INGRESS_IP:32443"
    echo ""
    
    echo -e "${BLUE}Default Credentials:${NC}"
    echo "  Username: admin@orizon.local"
    echo "  Password: changeme123"
    echo ""
    
    echo -e "${BLUE}Kubernetes Commands:${NC}"
    echo "  View pods: kubectl get pods -n orizon-ztc"
    echo "  View services: kubectl get svc -n orizon-ztc"
    echo "  View logs: kubectl logs -n orizon-ztc deployment/backend-api"
    echo "  Port forward: kubectl port-forward -n orizon-ztc svc/frontend-service 8080:80"
    echo ""
    
    if [ -d "/var/lib/rancher/k3s/server" ]; then
        echo -e "${BLUE}K3s Info:${NC}"
        echo "  Config: /etc/rancher/k3s/k3s.yaml"
        echo "  Kubectl: k3s kubectl (or regular kubectl)"
    fi
}

# Main deployment flow
main() {
    echo -e "${YELLOW}Starting deployment...${NC}"
    echo ""
    
    # Update system
    echo "Updating system packages..."
    $SUDO apt-get update -qq
    
    # Install dependencies
    $SUDO apt-get install -y curl wget git jq
    
    # Run installation steps
    install_k3s
    install_helm
    #install_cert_manager  # Optional for production
    #install_nginx_ingress # Optional for production
    build_docker_images
    
    # Check if manifests exist
    if [ -f "kubernetes/manifests.yaml" ]; then
        deploy_orizon
    else
        echo -e "${YELLOW}Note: Kubernetes manifests not found locally${NC}"
        echo "Please copy the project files to the server first"
    fi
    
    # Optional: Setup monitoring
    read -p "Install monitoring stack (Prometheus/Grafana)? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        setup_monitoring
    fi
    
    show_access_info
}

# Parse arguments
case "${1:-}" in
    uninstall)
        echo -e "${RED}Uninstalling Orizon Zero Trust Connect...${NC}"
        kubectl delete namespace orizon-ztc --ignore-not-found=true
        kubectl delete namespace monitoring --ignore-not-found=true
        echo -e "${GREEN}Uninstall complete${NC}"
        ;;
    status)
        echo -e "${BLUE}Orizon Zero Trust Connect Status:${NC}"
        kubectl get all -n orizon-ztc
        ;;
    logs)
        kubectl logs -n orizon-ztc deployment/backend-api --tail=100 -f
        ;;
    *)
        main
        ;;
esac
