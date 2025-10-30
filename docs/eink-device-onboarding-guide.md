# E-ink Device Onboarding Guide
## Waveshare 13.3" E6 Display with Raspberry Pi Zero 2W

### Overview
This guide provides step-by-step instructions for onboarding new E-ink devices to the Golf CMS system. The target hardware is the Waveshare 13.3" E-ink Spectra 6 (E6) display with Raspberry Pi Zero 2W, supporting both WiFi and LTE 4G connectivity.

### Hardware Specifications
- **Display**: Waveshare 13.3" E-ink Spectra 6 (E6)
- **Resolution**: 1600x1200 pixels
- **Colors**: 6-color (Black, White, Red, Yellow, Blue, Green)
- **Refresh Time**: 19 seconds
- **Controller**: Raspberry Pi Zero 2W
- **Power**: Solar panel with battery backup
- **Connectivity**: WiFi and LTE 4G with intelligent failover

---

## Phase 1: Hardware Setup

### 1.1 Physical Assembly
1. **Connect E-ink Display to Pi Zero 2W**
   - Attach Waveshare 13.3" E6 display to Pi Zero 2W via HAT+ connector
   - Ensure secure connection of all ribbon cables
   - Mount display in weatherproof enclosure for outdoor installation

2. **Power System Setup**
   - Install solar panel (minimum 10W recommended)
   - Connect battery pack (minimum 5000mAh for overnight operation)
   - Wire power management circuit to Pi Zero 2W
   - Test charging system during daylight hours

3. **Connectivity Hardware**
   - **WiFi**: Built-in WiFi on Pi Zero 2W
   - **LTE 4G**: Install compatible USB LTE modem (e.g., Huawei E3372)
   - Mount external antennas for optimal signal reception
   - Configure antenna positioning for best coverage

### 1.2 Initial Pi Zero 2W Setup
1. **Install Raspberry Pi OS**
   ```bash
   # Flash Raspberry Pi OS Lite to microSD card
   # Enable SSH and WiFi in boot partition
   ```

2. **Basic System Configuration**
   ```bash
   sudo raspi-config
   # Enable SPI interface for E-ink display
   # Set timezone and locale
   # Expand filesystem
   ```

3. **Configure GPIO for HAT+ (E) Display**
   
   **CRITICAL FOR HAT+ MODELS**: The 13.3inch e-Paper HAT+ (E) requires specific GPIO configuration for the dual-IC chip select pins. Without this configuration, the display controller will respond but the panel will not physically refresh.
   
   ```bash
   # Edit the boot config file
   sudo nano /boot/firmware/config.txt
   # Or for older Pi OS versions:
   # sudo nano /boot/config.txt
   
   # Add these lines at the end of the file:
   gpio=7=op,dl
   gpio=8=op,dl
   
   # Save (Ctrl+O, Enter, Ctrl+X) and reboot
   sudo reboot
   ```
   
   **What these settings do:**
   - `gpio=7=op,dl` - Sets GPIO 7 (CS_S - Slave chip select) to output mode with pull-down
   - `gpio=8=op,dl` - Sets GPIO 8 (CS_M - Master chip select) to output mode with pull-down
   
   **Note**: The HAT+ (E) uses a dual-IC controller where each IC controls half of the display. These GPIO settings are required for proper chip select operation. Regular HAT (non-plus) models do not require this configuration.

4. **Install Required Dependencies**
   ```bash
   sudo apt update && sudo apt upgrade -y
   sudo apt install python3-pip python3-venv git -y
   sudo apt install python3-pil python3-numpy -y
   sudo apt install network-manager modemmanager -y
   ```

---

## Phase 2: Software Installation

### 2.1 Waveshare E-ink Library Setup

**IMPORTANT**: The 13.3" E6 display driver (epd13in3E) is located in a separate program folder, not in the main waveshare_epd package. The installation script handles this automatically, but for manual setup:

1. **Download Waveshare Libraries**
   ```bash
   cd /home/pi
   git clone https://github.com/waveshare/e-Paper.git
   ```

2. **Enable SPI Interface**
   ```bash
   sudo raspi-config
   # Navigate to: Interface Options -> SPI -> Enable
   # Or use: sudo raspi-config nonint do_spi 0
   sudo reboot
   ```

3. **Verify SPI is Enabled**
   ```bash
   ls /dev/spidev*
   # Should show: /dev/spidev0.0  /dev/spidev0.1
   ```

### 2.2 Device Client Installation

**IMPORTANT**: The device client uses a virtual environment, and all Waveshare drivers must be installed in that venv, not system-wide.

1. **Download Device Client**
   ```bash
   cd /home/pi
   mkdir eink-device
   cd eink-device
   wget https://raw.githubusercontent.com/lwkxw08/GolfAdvertisingDisplays/devin/1727000056-supabase-migration/device-client/eink_device_client.py
   ```

2. **Create Virtual Environment and Install Dependencies**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install requests pillow psutil websocket-client spidev RPi.GPIO gpiozero numpy
   ```

3. **Install Waveshare Drivers in Virtual Environment**
   ```bash
   # Copy waveshare_epd package from main repo
   mkdir -p venv/lib/python*/site-packages/waveshare_epd
   cp -r /home/pi/e-Paper/RaspberryPi_JetsonNano/python/lib/waveshare_epd/* venv/lib/python*/site-packages/waveshare_epd/
   
   # Copy epd13in3E driver from separate program folder
   cp /home/pi/e-Paper/E-paper_Separate_Program/13.3inch_e-Paper_E/RaspberryPi/python/lib/epd13in3E.py venv/lib/python*/site-packages/waveshare_epd/
   
   # Copy epdconfig from separate program folder (compatible with epd13in3E)
   cp /home/pi/e-Paper/E-paper_Separate_Program/13.3inch_e-Paper_E/RaspberryPi/python/lib/epdconfig.py venv/lib/python*/site-packages/waveshare_epd/
   
   # Copy .so library files for hardware communication
   cp /home/pi/e-Paper/E-paper_Separate_Program/13.3inch_e-Paper_E/RaspberryPi/python/lib/*.so venv/lib/python*/site-packages/waveshare_epd/
   
   # Fix import in epd13in3E.py to use relative import
   sed -i 's/^import epdconfig$/from . import epdconfig/' venv/lib/python*/site-packages/waveshare_epd/epd13in3E.py
   
   deactivate
   ```

4. **Verify Installation**
   ```bash
   /home/pi/eink-device/venv/bin/python -c "from waveshare_epd import epd13in3E; print('epd13in3E driver loaded successfully')"
   ```

5. **Create System Service**
   ```bash
   sudo nano /etc/systemd/system/eink-device.service
   ```
   
   Service file content:
   ```ini
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
   ```

6. **Create Log File**
   ```bash
   sudo touch /var/log/eink_device.log
   sudo chown pi:pi /var/log/eink_device.log
   sudo chmod 644 /var/log/eink_device.log
   ```

---

## Phase 3: CMS Registration

### 3.1 Admin Dashboard Device Creation
1. **Access Golf CMS Admin Dashboard**
   - URL: https://golfadvertisingdisplays.onrender.com
   - Login with admin credentials

2. **Create New Device Entry**
   - Navigate to "Devices" section
   - Click "Add New Device"
   - Fill in device details:
     ```
     Device ID: eink_device_[unique_id]
     Device Name: [Tee Box Location] E-ink Display
     Course: [Select target golf course]
     Location: [Specific tee box number/name]
     Device Type: E-ink Display
     ```

3. **Configure Device Settings**
   - **Display Type**: Waveshare 13.3" E6
   - **Resolution**: 1600x1200
   - **Refresh Interval**: 15 minutes (normal mode)
   - **Power Management**: Solar + Battery
   - **Connectivity**: WiFi + LTE Failover

### 3.2 Device Registration in Database
The device will be automatically registered in the database with:
- Unique device ID
- Course association
- Initial analytics tracking setup
- Default power management settings

---

## Phase 4: Device Configuration

### 4.1 Create Device Configuration File
```bash
sudo mkdir -p /etc/eink_device
sudo nano /etc/eink_device/config.json
```

Configuration content:
```json
{
  "device_id": "eink_device_[unique_id]",
  "api_base_url": "https://golfadvertisingdisplays.onrender.com",
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
```

### 4.2 Network Configuration

#### WiFi Setup
```bash
sudo nmcli dev wifi connect "[SSID]" password "[PASSWORD]"
```

#### LTE Setup (if available)
```bash
sudo nmcli connection add type gsm ifname "*" con-name "LTE" apn "[APN]"
sudo nmcli connection up "LTE"
```

### 4.3 Test API Connectivity
```bash
# Test health endpoint
curl https://golfadvertisingdisplays.onrender.com/healthz

# Test connectivity options
curl https://golfadvertisingdisplays.onrender.com/api/eink/connectivity-options

# Test device playlist (will return 404 until device is registered)
curl "https://golfadvertisingdisplays.onrender.com/api/device/[device_id]/playlist?connectivity=wifi"
```

---

## Phase 5: Service Activation

### 5.1 Start Device Client Service
```bash
sudo systemctl enable eink-device.service
sudo systemctl start eink-device.service
sudo systemctl status eink-device.service
```

### 5.2 Monitor Service Logs
```bash
# View real-time logs
sudo journalctl -u eink-device.service -f

# View device-specific logs
tail -f /var/log/eink_device.log
```

### 5.3 Verify Device Communication
1. **Check Device Status in CMS**
   - Admin dashboard should show device as "Online"
   - Last sync timestamp should be recent
   - Connectivity type should be displayed (WiFi/LTE)

2. **Monitor Analytics**
   - Battery level reporting
   - Signal strength metrics
   - Refresh performance data
   - Error count tracking

---

## Phase 6: Content Management

### 6.1 Sponsor Campaign Assignment
1. **Create Sponsor Campaign**
   - Upload creative images (1600x1200 recommended)
   - Set campaign duration and rotation schedule
   - Assign to specific device(s)

2. **Image Optimization**
   - System automatically converts images to E6 format
   - 6-color palette optimization
   - Compression for LTE bandwidth conservation

### 6.2 Notice Management
1. **Course Staff Access**
   - Tenant portal login for course staff
   - Create temporary notices (max 1 hour duration)
   - Override sponsor content when needed

2. **Notice Styling**
   - E-ink optimized fonts and colors
   - Automatic color conversion to E6 palette
   - Readability optimization for outdoor viewing

---

## Phase 7: Monitoring and Maintenance

### 7.1 Device Health Monitoring
The system automatically tracks:
- **Power Metrics**: Battery level, charging status, power consumption
- **Connectivity**: Signal strength, connection type, failover events
- **Display Performance**: Refresh times, error counts, image quality
- **System Health**: Uptime, memory usage, temperature

### 7.2 Diagnostic Endpoints
```bash
# Get device diagnostics
curl "https://golfadvertisingdisplays.onrender.com/api/device/[device_id]/diagnostics"

# Check connectivity options
curl "https://golfadvertisingdisplays.onrender.com/api/eink/connectivity-options"
```

### 7.3 Power Management
- **Normal Mode**: 15-minute refresh intervals
- **Power Saving**: 1-hour intervals when battery < 50%
- **Deep Sleep**: 6-hour intervals during night (22:00-06:00)
- **Emergency Mode**: 24-hour intervals when battery < 10%

### 7.4 Maintenance Schedule
- **Daily**: Check device status in admin dashboard
- **Weekly**: Review analytics and performance metrics
- **Monthly**: Clean solar panel and check physical connections
- **Quarterly**: Update device client software and system packages

---

## Phase 8: Troubleshooting

### 8.1 Common Issues

#### Device Offline
1. Check power system and battery level
2. Verify network connectivity (WiFi/LTE)
3. Restart device client service
4. Check system logs for errors

#### Display Not Refreshing
1. Verify E-ink library installation
2. Check SPI interface configuration
3. Test display with example scripts
4. Review device client logs

#### Poor Image Quality
1. Verify image resolution (1600x1200)
2. Check color palette compatibility
3. Review image processing logs
4. Test with known good images

### 8.2 Log Analysis
```bash
# Device client logs (real-time)
tail -f /var/log/eink_device.log

# Device client logs (last 100 lines)
tail -100 /var/log/eink_device.log

# System logs
sudo journalctl -u eink-device.service --since "1 hour ago"

# Network connectivity
sudo journalctl -u NetworkManager --since "1 hour ago"
```

### 8.4 Key Success Indicators in Logs

When the device is working correctly, you should see these log messages:

```
E-ink display initialized successfully
Websocket connected
Displaying image: /tmp/campaign_*.png
Image displayed successfully in X seconds
Display put to sleep
```

**Common Error Messages and Solutions:**

1. **"Running in simulation mode (no E-ink hardware)"**
   - Cause: Waveshare library not installed in venv
   - Solution: Follow section 2.2 step 3 to install drivers in venv

2. **"Failed to initialize display: 'EPD' object has no attribute 'init'"**
   - Cause: Wrong API method name (should be uppercase Init)
   - Solution: Update device client code (fixed in v2.0.0+)

3. **"Failed to initialize display: 'NoneType' object has no attribute 'DEV_ModuleInit'"**
   - Cause: Missing .so library files or wrong epdconfig version
   - Solution: Copy .so files from E driver folder to venv (see section 2.2 step 3)

4. **"No content items in playlist"**
   - Cause: No active campaigns assigned to device, or campaigns filtered by time window
   - Solution: Check campaign assignment and time windows in admin dashboard

5. **"ls: cannot access '/dev/spidev*': No such file or directory"**
   - Cause: SPI interface not enabled
   - Solution: Enable SPI via raspi-config and reboot (see section 2.1 step 2)

### 8.3 Remote Diagnostics
The CMS provides remote diagnostic capabilities:
- Real-time device status monitoring
- Performance metrics and health scores
- Automated recommendations for optimization
- Remote configuration updates

---

## API Endpoints Reference

### Device Management
- `GET /api/device/{device_id}/playlist?connectivity={type}` - Get optimized content playlist
- `POST /api/device/{device_id}/status` - Update device status and metrics
- `GET /api/device/{device_id}/diagnostics` - Get comprehensive device diagnostics

### E-ink Specific
- `GET /api/eink/connectivity-options` - Get connectivity types and power modes
- `POST /api/images/process-for-eink` - Process images for E-ink display
- `POST /api/notices/generate-eink-image` - Generate notice images for E-ink

### System Health
- `GET /healthz` - Backend health check
- `GET /docs` - API documentation

---

## Security Considerations

1. **Device Authentication**: Each device uses unique ID for API access
2. **Network Security**: Use WPA3 for WiFi, VPN for LTE if required
3. **Physical Security**: Secure mounting and tamper-evident enclosures
4. **Software Updates**: Regular security patches and client updates
5. **Data Privacy**: Minimal data collection, encrypted transmission

---

## Performance Optimization

### Connectivity-Based Optimization
- **WiFi**: Higher refresh rates, larger image sizes, real-time updates
- **LTE**: Compressed images, batch updates, scheduled sync windows
- **Failover**: Automatic switching based on signal quality and power levels

### Power Optimization
- **Solar Charging**: Optimized charging schedules based on daylight hours
- **Battery Management**: Intelligent power modes based on charge level
- **Display Efficiency**: Minimal refreshes during low-light conditions

---

## Support and Documentation

- **Technical Support**: Contact system administrator
- **API Documentation**: https://golfadvertisingdisplays.onrender.com/docs
- **Hardware Documentation**: Waveshare E-ink display manuals
- **Software Repository**: https://github.com/lwkxw08/GolfAdvertisingDisplays

---

*This guide covers the complete onboarding process for E-ink devices in the Golf CMS system. For additional support or custom configurations, please contact the system administrator.*
