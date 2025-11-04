#!/bin/bash
set -e


RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_root() {
    if [ "$EUID" -eq 0 ]; then
        print_error "Please do not run this script as root. Run as the 'pi' user."
        exit 1
    fi
}

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Device Health Metrics Fix - Update Script"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

check_root

REPO_BRANCH="devin/1727000056-supabase-migration"
DEVICE_CLIENT_URL="https://raw.githubusercontent.com/lwkxw08/GolfAdvertisingDisplays/${REPO_BRANCH}/device-client/eink_device_client.py"
CONFIG_FILE="/etc/eink_device/config.json"
CLIENT_FILE="/home/pi/eink-device/eink_device_client.py"

print_info "Checking device configuration..."
if [ ! -f "$CONFIG_FILE" ]; then
    print_error "Configuration file not found at $CONFIG_FILE"
    exit 1
fi

DEVICE_ID=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['device_id'])" 2>/dev/null)
if [ -z "$DEVICE_ID" ]; then
    print_error "Could not read device_id from config file"
    exit 1
fi

print_success "Found device_id: $DEVICE_ID"

EXTERNAL_ID=$(python3 -c "import json; config=json.load(open('$CONFIG_FILE')); print(config.get('external_id', ''))" 2>/dev/null)

if [ -n "$EXTERNAL_ID" ]; then
    print_warning "external_id already exists in config: $EXTERNAL_ID"
    read -p "Do you want to continue anyway? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Update cancelled"
        exit 0
    fi
fi

print_info "Backing up current configuration..."
sudo cp "$CONFIG_FILE" "${CONFIG_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
print_success "Backup created"

print_info "Updating configuration to add external_id..."
TEMP_CONFIG=$(mktemp)
python3 << EOF
import json

with open('$CONFIG_FILE', 'r') as f:
    config = json.load(f)

if 'external_id' not in config:
    config['external_id'] = config['device_id']
    print(f"Added external_id: {config['external_id']}")
else:
    print(f"external_id already present: {config['external_id']}")

with open('$TEMP_CONFIG', 'w') as f:
    json.dump(config, f, indent=2)
EOF

sudo mv "$TEMP_CONFIG" "$CONFIG_FILE"
sudo chown root:root "$CONFIG_FILE"
sudo chmod 644 "$CONFIG_FILE"
print_success "Configuration updated"

print_info "Backing up current device client..."
if [ -f "$CLIENT_FILE" ]; then
    cp "$CLIENT_FILE" "${CLIENT_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
    print_success "Device client backed up"
fi

print_info "Downloading updated device client..."
cd /home/pi/eink-device
wget -q -O eink_device_client.py.new "$DEVICE_CLIENT_URL"

if [ $? -eq 0 ]; then
    mv eink_device_client.py.new eink_device_client.py
    chmod +x eink_device_client.py
    print_success "Device client updated"
else
    print_error "Failed to download device client"
    exit 1
fi

print_info "Restarting device client service..."
sudo systemctl restart eink-device.service

sleep 2

if sudo systemctl is-active --quiet eink-device.service; then
    print_success "Device client service restarted successfully"
else
    print_error "Service failed to start. Check logs with: sudo journalctl -u eink-device.service -n 50"
    exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
print_success "Update Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "What was updated:"
echo "  ✓ Device client updated to use external_id for health endpoint"
echo "  ✓ Configuration updated with external_id: $DEVICE_ID"
echo "  ✓ Service restarted"
echo ""
echo "Next steps:"
echo "  • Wait 10 minutes for the next health heartbeat"
echo "  • Check the monitoring dashboard - metrics should show actual values"
echo "  • Health score should change from 50 to reflect actual device health"
echo ""
echo "Useful commands:"
echo "  • View logs:         tail -f /var/log/eink_device.log"
echo "  • Check service:     sudo systemctl status eink-device.service"
echo "  • View config:       cat $CONFIG_FILE"
echo ""
echo "Backups created:"
echo "  • Config backup:     ${CONFIG_FILE}.backup.*"
echo "  • Client backup:     ${CLIENT_FILE}.backup.*"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
