#!/bin/bash
###############################################################################
# Lazarus Recovery - Automated Installer
#
# Installs and configures Tor Hidden Service with Shamir Secret Sharing
# for emergency firewall recovery.
#
# Usage:
#   sudo ./install_lazarus.sh
#
# Requirements:
#   - Must run as root
#   - Internet connection (to install packages)
#
# This script:
#   1. Installs Tor and Python dependencies
#   2. Generates Shamir shards and Tor auth keys
#   3. Configures Tor Hidden Service
#   4. Displays onion address, client key, and shards (ONE TIME ONLY)
###############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Banner
echo "═══════════════════════════════════════════════════════════════════════"
echo "  Lazarus Recovery - Automated Installer"
echo "═══════════════════════════════════════════════════════════════════════"
echo ""

###############################################################################
# Check Root Privileges
###############################################################################
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}ERROR: This script must be run as root${NC}"
    echo "Run: sudo $0"
    exit 1
fi

echo -e "${GREEN}✓${NC} Running as root"

###############################################################################
# Detect OS and Package Manager
###############################################################################
echo ""
echo "[*] Detecting operating system..."

if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    echo "    Detected: $PRETTY_NAME"
else
    echo -e "${RED}ERROR: Cannot detect OS${NC}"
    exit 1
fi

# Determine package manager
if command -v apt-get &> /dev/null; then
    PKG_MANAGER="apt-get"
    TOR_USER="debian-tor"  # Ubuntu/Debian uses debian-tor
    echo "    Package manager: apt-get"
elif command -v dnf &> /dev/null; then
    PKG_MANAGER="dnf"
    TOR_USER="tor"  # Fedora/RHEL uses tor
    echo "    Package manager: dnf"
elif command -v yum &> /dev/null; then
    PKG_MANAGER="yum"
    TOR_USER="tor"
    echo "    Package manager: yum"
else
    echo -e "${RED}ERROR: Unsupported package manager${NC}"
    exit 1
fi

###############################################################################
# Install Tor
###############################################################################
echo ""
echo "[*] Installing Tor..."

if command -v tor &> /dev/null; then
    echo -e "${GREEN}✓${NC} Tor already installed"
else
    if [ "$PKG_MANAGER" = "apt-get" ]; then
        apt-get update -qq
        apt-get install -y tor
    else
        $PKG_MANAGER install -y tor
    fi
    echo -e "${GREEN}✓${NC} Tor installed"
fi

###############################################################################
# Install Python and Pip
###############################################################################
echo ""
echo "[*] Installing Python..."

if command -v python3 &> /dev/null; then
    echo -e "${GREEN}✓${NC} Python3 already installed ($(python3 --version))"
else
    if [ "$PKG_MANAGER" = "apt-get" ]; then
        apt-get install -y python3 python3-pip
    else
        $PKG_MANAGER install -y python3 python3-pip
    fi
    echo -e "${GREEN}✓${NC} Python3 installed"
fi

###############################################################################
# Install Python Dependencies
###############################################################################
echo ""
echo "[*] Installing Python dependencies..."

# Check if we're in the lazarus_recovery directory
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}ERROR: requirements.txt not found${NC}"
    echo "Make sure you're running this script from the lazarus_recovery directory"
    exit 1
fi

pip3 install -q -r requirements.txt
echo -e "${GREEN}✓${NC} Python dependencies installed"

###############################################################################
# Generate Keys and Shards (Headless Mode)
###############################################################################
echo ""
echo "[*] Generating Shamir shards and Tor keys..."

python3 lazarus_setup.py --save-keys

if [ ! -f "generated_admin.auth" ] || [ ! -f "generated_client_private.key" ] || [ ! -f "shards.txt" ]; then
    echo -e "${RED}ERROR: Key generation failed${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} Keys generated successfully"

###############################################################################
# Configure Tor Hidden Service
###############################################################################
echo ""
echo "[*] Configuring Tor Hidden Service..."

# Create Tor directories
TOR_DIR="/var/lib/tor/lazarus"
TOR_CLIENTS_DIR="$TOR_DIR/authorized_clients"

mkdir -p "$TOR_CLIENTS_DIR"

# Move admin auth file
mv generated_admin.auth "$TOR_CLIENTS_DIR/admin.auth"
echo -e "${GREEN}✓${NC} Installed client authorization"

# Set ownership and permissions
chown -R "$TOR_USER:$TOR_USER" "$TOR_DIR"
chmod 700 "$TOR_DIR"
chmod 700 "$TOR_CLIENTS_DIR"
chmod 600 "$TOR_CLIENTS_DIR/admin.auth"
echo -e "${GREEN}✓${NC} Set permissions (owner: $TOR_USER)"

# Configure torrc (idempotent - only add if not present)
TORRC="/etc/tor/torrc"

if grep -q "lazarus" "$TORRC"; then
    echo -e "${YELLOW}⚠${NC}  Tor config already present (skipping)"
else
    echo "" >> "$TORRC"
    echo "# Lazarus Recovery Hidden Service" >> "$TORRC"
    echo "HiddenServiceDir /var/lib/tor/lazarus/" >> "$TORRC"
    echo "HiddenServicePort 80 127.0.0.1:9999" >> "$TORRC"
    echo "HiddenServiceVersion 3" >> "$TORRC"
    echo -e "${GREEN}✓${NC} Updated torrc configuration"
fi

###############################################################################
# Start Tor Service
###############################################################################
echo ""
echo "[*] Starting Tor service..."

systemctl enable tor
systemctl restart tor

# Wait for Tor to initialize
echo "    Waiting for Tor to initialize (5 seconds)..."
sleep 5

# Check if Tor started successfully
if systemctl is-active --quiet tor; then
    echo -e "${GREEN}✓${NC} Tor service running"
else
    echo -e "${RED}ERROR: Tor service failed to start${NC}"
    echo ""
    echo "Tor status:"
    systemctl status tor --no-pager
    exit 1
fi

###############################################################################
# Display Final Secrets (ONE TIME ONLY)
###############################################################################
echo ""
echo "════════════════════════════════════════════════════════════════════════════"
echo "💀 LAZARUS RECOVERY INSTALLED SUCCESSFULLY 💀"
echo "════════════════════════════════════════════════════════════════════════════"
echo ""

# Get onion address
if [ -f "$TOR_DIR/hostname" ]; then
    ONION_ADDRESS=$(cat "$TOR_DIR/hostname")
else
    echo -e "${RED}ERROR: Could not read onion address${NC}"
    echo "Check: $TOR_DIR/hostname"
    exit 1
fi

# Display onion address
echo -e "${RED}[1] YOUR BACKDOOR URL (Save this):${NC}"
echo "    $ONION_ADDRESS"
echo ""

# Display client private key
echo -e "${RED}[2] YOUR CLIENT PRIVATE KEY (Save this to ~/.tor/authorized_clients/lazarus.auth_private):${NC}"
cat generated_client_private.key | sed 's/^/    /'
echo ""

# Display Shamir shards
echo -e "${RED}[3] YOUR 5 RECOVERY SHARDS (Write these down PHYSICALLY on PAPER!):${NC}"
cat shards.txt | sed 's/^/    /'
echo ""
echo "════════════════════════════════════════════════════════════════════════════"
echo -e "${YELLOW}⚠️  TEMPORARY FILES HAVE BEEN DELETED.${NC}"
echo -e "${YELLOW}⚠️  IF YOU CLOSE THIS TERMINAL, THESE SECRETS ARE GONE FOREVER.${NC}"
echo -e "${YELLOW}⚠️  WRITE THEM DOWN NOW - THIS IS YOUR ONLY CHANCE!${NC}"
echo "════════════════════════════════════════════════════════════════════════════"
echo ""
echo -e "${RED}DO NOT PROCEED UNTIL YOU HAVE SAVED ALL 3 ITEMS ABOVE!${NC}"
echo ""
read -p "Press Enter ONLY after you have saved all secrets..." 

###############################################################################
# Cleanup Temporary Files
###############################################################################
echo "[*] Cleaning up temporary files..."

# Securely delete generated files
shred -u generated_client_private.key 2>/dev/null || rm -f generated_client_private.key
shred -u shards.txt 2>/dev/null || rm -f shards.txt

echo -e "${GREEN}✓${NC} Temporary files deleted"

###############################################################################
# Final Instructions
###############################################################################
echo ""
echo "═══════════════════════════════════════════════════════════════════════"
echo "  ✓ INSTALLATION COMPLETE"
echo "═══════════════════════════════════════════════════════════════════════"
echo ""
echo "Next Steps:"
echo ""
echo "1. Copy the Client Private Key to your admin machine:"
echo "   mkdir -p ~/.tor/authorized_clients"
echo "   echo '<PRIVATE_KEY>' > ~/.tor/authorized_clients/lazarus.auth_private"
echo ""
echo "2. Start the recovery server:"
echo "   sudo python3 lazarus_server.py"
echo ""
echo "3. Access via Tor Browser:"
echo "   http://$ONION_ADDRESS"
echo ""
echo "⚠️  SECURITY REMINDERS:"
echo "  • Write down all 5 shards on PAPER (never digital!)"
echo "  • Store each shard in a SEPARATE secure location"
echo "  • ANY 3 shards can recover the system"
echo "  • Losing 3+ shards = permanent lockout"
echo ""
echo "═══════════════════════════════════════════════════════════════════════"
echo ""

exit 0
