#!/bin/bash
set -e


SCRIPT_VERSION="2.0.0"
API_BASE_URL="https://golfadvertisingdisplays.onrender.com"
REPO_BRANCH="devin/1727000056-supabase-migration"
DEVICE_CLIENT_URL="https://raw.githubusercontent.com/lwkxw08/GolfAdvertisingDisplays/${REPO_BRANCH}/device-client/eink_device_client.py"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

check_device_id() {
    if [ -z "$1" ]; then
        print_error "Device ID is required!"
        echo ""
        echo "Usage: $0 DEVICE_ID"
        echo ""
        echo "Example: $0 eink_device_001"
        echo ""
        echo "You can find your device ID in the Golf CMS admin dashboard after creating a new device."
        exit 1
    fi
}

check_internet() {
    print_info "Checking internet connectivity..."
    if ! ping -c 1 8.8.8.8 &> /dev/null; then
        print_error "No internet connection detected. Please check your network settings."
        exit 1
    fi
    print_success "Internet connection verified"
}

install_dependencies() {
    print_info "Installing system dependencies..."
    
    sudo apt update -qq
    
    PACKAGES="python3-pip python3-venv git python3-pil python3-numpy network-manager modemmanager"
    MISSING_PACKAGES=""
    
    for pkg in $PACKAGES; do
        if ! dpkg -l | grep -q "^ii  $pkg "; then
            MISSING_PACKAGES="$MISSING_PACKAGES $pkg"
        fi
    done
    
    if [ -n "$MISSING_PACKAGES" ]; then
        print_info "Installing missing packages:$MISSING_PACKAGES"
        sudo apt install -y $MISSING_PACKAGES
        print_success "System dependencies installed"
    else
        print_success "All system dependencies already installed"
    fi
}

enable_spi() {
    print_info "Enabling SPI interface..."
    
    if [ -f /dev/spidev0.0 ]; then
        print_success "SPI already enabled"
        return
    fi
    
    print_info "Enabling SPI via raspi-config..."
    sudo raspi-config nonint do_spi 0
    
    if sudo raspi-config nonint get_spi | grep -q "0"; then
        print_success "SPI enabled (reboot required)"
    else
        print_warning "SPI enable may have failed. Please check manually."
    fi
}

install_eink_library() {
    print_info "Installing Waveshare E-ink library..."
    
    if [ -d "/home/pi/e-Paper" ]; then
        print_warning "Waveshare library already exists, skipping clone..."
    else
        cd /home/pi
        
        print_info "Cloning Waveshare e-Paper repository..."
        if ! git clone https://github.com/waveshare/e-Paper.git; then
            print_error "Failed to clone Waveshare repository"
            exit 1
        fi
    fi
    
    if [ ! -d "/home/pi/e-Paper/RaspberryPi_JetsonNano/python" ]; then
        print_error "Waveshare repository structure not as expected"
        print_info "Checking available directories..."
        ls -la /home/pi/e-Paper/
        exit 1
    fi
    
    if [ ! -d "/home/pi/e-Paper/E-paper_Separate_Program/13.3inch_e-Paper_E" ]; then
        print_error "13.3inch E-Paper E driver not found in repository"
        exit 1
    fi
    
    print_success "Waveshare E-ink library repository ready"
}

setup_device_client() {
    local device_id=$1
    
    print_info "Setting up device client for device: $device_id"
    
    mkdir -p /home/pi/eink-device
    cd /home/pi/eink-device
    
    print_info "Downloading device client..."
    wget -q -O eink_device_client.py "$DEVICE_CLIENT_URL"
    
    if [ ! -f "eink_device_client.py" ]; then
        print_error "Failed to download device client"
        exit 1
    fi
    
    print_success "Device client downloaded"
    
    print_info "Creating Python virtual environment..."
    python3 -m venv venv
    
    print_info "Installing Python dependencies..."
    source venv/bin/activate
    pip install -q --upgrade pip
    pip install -q requests pillow psutil websocket-client spidev RPi.GPIO gpiozero numpy
    
    print_info "Installing Waveshare epd drivers in venv..."
    mkdir -p venv/lib/python*/site-packages/waveshare_epd
    cp -r /home/pi/e-Paper/RaspberryPi_JetsonNano/python/lib/waveshare_epd/* venv/lib/python*/site-packages/waveshare_epd/
    
    cp /home/pi/e-Paper/E-paper_Separate_Program/13.3inch_e-Paper_E/RaspberryPi/python/lib/epd13in3E.py venv/lib/python*/site-packages/waveshare_epd/
    
    cp /home/pi/e-Paper/E-paper_Separate_Program/13.3inch_e-Paper_E/RaspberryPi/python/lib/epdconfig.py venv/lib/python*/site-packages/waveshare_epd/
    
    cp /home/pi/e-Paper/E-paper_Separate_Program/13.3inch_e-Paper_E/RaspberryPi/python/lib/*.so venv/lib/python*/site-packages/waveshare_epd/
    
    sed -i 's/^import epdconfig$/from . import epdconfig/' venv/lib/python*/site-packages/waveshare_epd/epd13in3E.py
    
    deactivate
    
    print_success "Python environment configured with Waveshare drivers"
}

create_device_config() {
    local device_id=$1
    
    print_info "Creating device configuration..."
    
    sudo mkdir -p /etc/eink_device
    
    sudo tee /etc/eink_device/config.json > /dev/null <<EOF
{
  "device_id": "$device_id",
  "api_base_url": "$API_BASE_URL",
  "sync_interval": 900,
  "max_retries": 3,
  "timeout": 30,
  "connectivity": {
    "wifi_interface": "wlan0",
    "lte_interface": "ppp0",
    "failover_enabled": true
  },
  "power_management": {
    "solar_optimization": true,
    "battery_monitoring": true,
    "low_power_threshold": 20
  }
}
EOF
    
    print_success "Device configuration created at /etc/eink_device/config.json"
}

create_systemd_service() {
    print_info "Creating systemd service..."
    
    print_info "Creating log file..."
    sudo touch /var/log/eink_device.log
    sudo chown pi:pi /var/log/eink_device.log
    sudo chmod 644 /var/log/eink_device.log
    
    sudo tee /etc/systemd/system/eink-device.service > /dev/null <<EOF
[Unit]
Description=E-ink Device Client for Golf CMS
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/eink-device
ExecStart=/home/pi/eink-device/venv/bin/python eink_device_client.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
    
    print_success "Systemd service created"
}

start_service() {
    print_info "Enabling and starting device client service..."
    
    sudo systemctl daemon-reload
    sudo systemctl enable eink-device.service
    sudo systemctl start eink-device.service
    
    sleep 2
    
    if sudo systemctl is-active --quiet eink-device.service; then
        print_success "Device client service is running"
    else
        print_warning "Service started but may have issues. Check status with: sudo systemctl status eink-device.service"
    fi
}

test_api_connectivity() {
    local device_id=$1
    
    print_info "Testing API connectivity..."
    
    if curl -s -f "$API_BASE_URL/healthz" > /dev/null; then
        print_success "API health check passed"
    else
        print_warning "API health check failed. The backend may be sleeping or unreachable."
    fi
}

verify_installation() {
    print_info "Verifying installation..."
    
    local errors=0
    
    if [ ! -d "/home/pi/e-Paper" ]; then
        print_error "Waveshare repository not found"
        errors=$((errors + 1))
    fi
    
    if [ ! -d "/home/pi/eink-device/venv" ]; then
        print_error "Virtual environment not found"
        errors=$((errors + 1))
    fi
    
    if [ ! -f "/home/pi/eink-device/eink_device_client.py" ]; then
        print_error "Device client not found"
        errors=$((errors + 1))
    fi
    
    if [ ! -f "/etc/eink_device/config.json" ]; then
        print_error "Configuration file not found"
        errors=$((errors + 1))
    fi
    
    if [ ! -f "/etc/systemd/system/eink-device.service" ]; then
        print_error "Systemd service not found"
        errors=$((errors + 1))
    fi
    
    if ! /home/pi/eink-device/venv/bin/python -c "from waveshare_epd import epd13in3E" 2>/dev/null; then
        print_error "Waveshare epd13in3E driver not properly installed in venv"
        errors=$((errors + 1))
    fi
    
    if [ $errors -eq 0 ]; then
        print_success "Installation verification passed"
        return 0
    else
        print_error "Installation verification failed with $errors error(s)"
        return 1
    fi
}

display_completion() {
    local device_id=$1
    
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    print_success "Installation Complete!"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "Device ID: $device_id"
    echo "API URL: $API_BASE_URL"
    echo ""
    echo "IMPORTANT: After reboot, start the service with:"
    echo "  sudo systemctl start eink-device.service"
    echo ""
    echo "Useful Commands:"
    echo "  • Check service status:  sudo systemctl status eink-device.service"
    echo "  • View logs:            tail -f /var/log/eink_device.log"
    echo "  • Restart service:      sudo systemctl restart eink-device.service"
    echo "  • Stop service:         sudo systemctl stop eink-device.service"
    echo ""
    echo "Configuration file: /etc/eink_device/config.json"
    echo "Device client: /home/pi/eink-device/eink_device_client.py"
    echo ""
    echo "The device should appear as 'Online' in the Golf CMS admin dashboard"
    echo "within 1-2 minutes after starting the service."
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
}

main() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  Golf CMS E-ink Device Setup Script v${SCRIPT_VERSION}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    check_root
    check_device_id "$1"
    
    DEVICE_ID=$1
    
    print_info "Starting installation for device: $DEVICE_ID"
    echo ""
    
    check_internet
    install_dependencies
    enable_spi
    install_eink_library
    setup_device_client "$DEVICE_ID"
    create_device_config "$DEVICE_ID"
    create_systemd_service
    verify_installation
    
    display_completion "$DEVICE_ID"
    
    print_warning "SPI interface has been enabled. A reboot is required before starting the service."
    echo ""
    read -p "Reboot now? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Rebooting in 5 seconds..."
        print_info "After reboot, run: sudo systemctl start eink-device.service"
        sleep 5
        sudo reboot
    else
        print_warning "Please reboot manually before starting the service:"
        print_info "  sudo reboot"
        print_info "After reboot, start the service with:"
        print_info "  sudo systemctl start eink-device.service"
    fi
}

main "$@"
