#!/bin/bash
#
# Sentinyl Guard Agent Installer
# One-line installation: curl -fsSL https://sentinyl.example.com/install.sh | sudo bash
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
API_URL="http://localhost:8000"
AGENT_ID=$(uuidgen)
INSTALL_DIR="/opt/sentinyl-guard"
SERVICE_NAME="sentinyl-guard"

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}Sentinyl Guard Agent Installer${NC}"
echo -e "${GREEN}================================${NC}"
echo

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --api-url)
            API_URL="$2"
            shift 2
            ;;
        --agent-id)
            AGENT_ID="$2"
            shift 2
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Error: This script must be run as root${NC}"
    echo "Please run: sudo bash install.sh"
    exit 1
fi

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    OS_VERSION=$VERSION_ID
else
    echo -e "${RED}Error: Cannot detect operating system${NC}"
    exit 1
fi

echo -e "${YELLOW}Detected OS: $OS $OS_VERSION${NC}"
echo

# Install Python dependencies
echo -e "${GREEN}[1/6] Installing Python dependencies...${NC}"
if [ "$OS" = "ubuntu" ] || [ "$OS" = "debian" ]; then
    apt-get update -qq
    apt-get install -y python3 python3-pip uuid-runtime >/dev/null 2>&1
elif [ "$OS" = "centos" ] || [ "$OS" = "rhel" ]; then
    yum install -y python3 python3-pip uuid >/dev/null 2>&1
else
    echo -e "${YELLOW}Warning: Unsupported OS. Manual dependency installation required.${NC}"
fi

# Install Python packages
pip3 install --quiet psutil requests 2>/dev/null || pip install --quiet psutil requests

echo -e "${GREEN}[2/6] Creating installation directory...${NC}"
mkdir -p $INSTALL_DIR
mkdir -p /var/log

# Download agent script
echo -e "${GREEN}[3/6] Downloading Sentinyl Guard agent...${NC}"
if command -v wget >/dev/null 2>&1; then
    wget -q -O "${INSTALL_DIR}/sentinyl_guard_agent.py" "${API_URL}/agent/sentinyl_guard_agent.py" 2>/dev/null || {
        echo -e "${YELLOW}Cannot download from API, using embedded script...${NC}"
        # In production, this would fetch from GitHub or API
        cat > "${INSTALL_DIR}/sentinyl_guard_agent.py" << 'AGENT_SCRIPT_EOF'
# Agent script would be embedded here or fetched from repository
AGENT_SCRIPT_EOF
    }
elif command -v curl >/dev/null 2>&1; then
    curl -fsSL -o "${INSTALL_DIR}/sentinyl_guard_agent.py" "${API_URL}/agent/sentinyl_guard_agent.py" || {
        echo -e "${YELLOW}Cannot download from API${NC}"
    }
fi

# Make executable
chmod +x "${INSTALL_DIR}/sentinyl_guard_agent.py"

# Create systemd service
echo -e "${GREEN}[4/6] Creating systemd service...${NC}"
cat > "/etc/systemd/system/${SERVICE_NAME}.service" << EOF
[Unit]
Description=Sentinyl Guard Active Defense Agent
After=network.target

[Service]
Type=simple
User=root
ExecStart=/usr/bin/python3 ${INSTALL_DIR}/sentinyl_guard_agent.py --api-url ${API_URL} --agent-id ${AGENT_ID}
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security hardening
NoNewPrivileges=false
PrivateTmp=true

# Network capability for iptables
AmbientCapabilities=CAP_NET_ADMIN
CapabilityBoundingSet=CAP_NET_ADMIN

[Install]
WantedBy=multi-user.target
EOF

# Create configuration file
echo -e "${GREEN}[5/6] Creating configuration...${NC}"
cat > "${INSTALL_DIR}/config.env" << EOF
API_URL=${API_URL}
AGENT_ID=${AGENT_ID}
HOSTNAME=$(hostname)
INSTALLED_AT=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
EOF

# Reload systemd, enable and start service
echo -e "${GREEN}[6/6] Starting Sentinyl Guard agent...${NC}"
systemctl daemon-reload
systemctl enable ${SERVICE_NAME}
systemctl start ${SERVICE_NAME}

# Wait a moment and check status
sleep 2
if systemctl is-active --quiet ${SERVICE_NAME}; then
    echo
    echo -e "${GREEN}✓ Installation complete!${NC}"
    echo
    echo -e "${YELLOW}Agent Details:${NC}"
    echo "  - Agent ID: ${AGENT_ID}"
    echo "  - API URL: ${API_URL}"
    echo "  - Hostname: $(hostname)"
    echo
    echo -e "${YELLOW}Service Management:${NC}"
    echo "  - Check status: systemctl status ${SERVICE_NAME}"
    echo "  - View logs: journalctl -u ${SERVICE_NAME} -f"
    echo "  - Stop agent: systemctl stop ${SERVICE_NAME}"
    echo "  - Restart agent: systemctl restart ${SERVICE_NAME}"
    echo
    echo -e "${GREEN}The agent is now monitoring for behavioral anomalies.${NC}"
else
    echo -e "${RED}Error: Service failed to start${NC}"
    echo "Check logs with: journalctl -u ${SERVICE_NAME} -n 50"
    exit 1
fi
