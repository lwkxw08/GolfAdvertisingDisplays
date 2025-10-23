import React, { useState } from 'react';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from './ui/dialog';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Copy, CheckCircle, Settings, Wifi, Key, Terminal } from 'lucide-react';
import { Device } from '../lib/api';

interface PiImagerConfigDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  device: Device | null;
}

export const PiImagerConfigDialog: React.FC<PiImagerConfigDialogProps> = ({
  open,
  onOpenChange,
  device
}) => {
  const [copiedSection, setCopiedSection] = useState<string | null>(null);

  if (!device) {
    console.log('PiImagerConfigDialog: device is null, not rendering');
    return null;
  }
  
  console.log('PiImagerConfigDialog: rendering with device:', device);

  const copyToClipboard = async (text: string, section: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedSection(section);
      setTimeout(() => setCopiedSection(null), 2000);
    } catch (err) {
      console.error('Failed to copy to clipboard:', err);
    }
  };

  const piImagerConfig = {
    username: 'pi',
    password: 'golfcms123',
    hostname: `eink-${device.device_id}`,
    ssh: {
      enabled: true,
      passwordAuth: true,
      publicKey: 'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQC... (your SSH public key)'
    },
    wifi: {
      ssid: '[YOUR_WIFI_SSID]',
      password: '[YOUR_WIFI_PASSWORD]',
      country: 'GB'
    },
    locale: {
      timezone: 'Europe/London',
      keyboard: 'gb'
    }
  };

  const deviceConfig = {
    device_id: device.device_id,
    api_base_url: 'https://golfadvertisingdisplays.onrender.com',
    sync_interval: 900,
    max_retries: 3,
    timeout: 30,
    connectivity: {
      wifi_interface: 'wlan0',
      lte_interface: 'ppp0',
      failover_enabled: true
    },
    power_management: {
      solar_optimization: true,
      battery_monitoring: true,
      low_power_threshold: 20
    }
  };

  const automatedSetupCommand = `curl -sSL https://raw.githubusercontent.com/lwkxw08/GolfAdvertisingDisplays/devin/1727000056-supabase-migration/setup-scripts/install-device.sh | bash -s -- ${device.device_id}`;

  const manualSetupCommands = `# Manual Device Client Setup Commands (if automated script fails)
cd /home/pi
mkdir eink-device && cd eink-device
wget https://raw.githubusercontent.com/lwkxw08/GolfAdvertisingDisplays/devin/1727000056-supabase-migration/device-client/eink_device_client.py
python3 -m venv venv
source venv/bin/activate
pip install requests pillow psutil

# Create configuration file
sudo mkdir -p /etc/eink_device
sudo tee /etc/eink_device/config.json << EOF
${JSON.stringify(deviceConfig, null, 2)}
EOF

# Create systemd service
sudo tee /etc/systemd/system/eink-device.service << EOF
[Unit]
Description=E-ink Device Client
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/eink-device
ExecStart=/home/pi/eink-device/venv/bin/python eink_device_client.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl enable eink-device.service
sudo systemctl start eink-device.service`;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Settings className="w-5 h-5 text-blue-600" />
            Raspberry Pi Imager Configuration
          </DialogTitle>
          <DialogDescription>
            Copy these settings into Raspberry Pi Imager's OS Customization for device: <strong>{device.name}</strong>
          </DialogDescription>
        </DialogHeader>
        
        <div className="space-y-6">
          {/* Pi Imager OS Customization Settings */}
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <Settings className="w-4 h-4 text-blue-600" />
              <span className="font-medium">OS Customization Settings</span>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Username</label>
                <div className="flex gap-2">
                  <Input value={piImagerConfig.username} readOnly />
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => copyToClipboard(piImagerConfig.username, 'username')}
                  >
                    {copiedSection === 'username' ? <CheckCircle className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                  </Button>
                </div>
              </div>
              
              <div className="space-y-2">
                <label className="text-sm font-medium">Password</label>
                <div className="flex gap-2">
                  <Input value={piImagerConfig.password} readOnly />
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => copyToClipboard(piImagerConfig.password, 'password')}
                  >
                    {copiedSection === 'password' ? <CheckCircle className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                  </Button>
                </div>
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Hostname</label>
              <div className="flex gap-2">
                <Input value={piImagerConfig.hostname} readOnly />
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => copyToClipboard(piImagerConfig.hostname, 'hostname')}
                >
                  {copiedSection === 'hostname' ? <CheckCircle className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                </Button>
              </div>
            </div>
          </div>

          {/* SSH Configuration */}
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <Key className="w-4 h-4 text-green-600" />
              <span className="font-medium">SSH Configuration</span>
            </div>
            <div className="bg-gray-50 p-4 rounded-lg">
              <div className="space-y-2">
                <div>✓ Enable SSH</div>
                <div>✓ Use password authentication</div>
                <div className="text-sm text-gray-600">SSH will be enabled with the username/password above</div>
              </div>
            </div>
          </div>

          {/* WiFi Configuration */}
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <Wifi className="w-4 h-4 text-purple-600" />
              <span className="font-medium">WiFi Configuration</span>
            </div>
            <div className="bg-yellow-50 p-4 rounded-lg">
              <div className="space-y-2">
                <div><strong>SSID:</strong> {piImagerConfig.wifi.ssid}</div>
                <div><strong>Password:</strong> {piImagerConfig.wifi.password}</div>
                <div><strong>Country:</strong> {piImagerConfig.wifi.country}</div>
                <div className="text-sm text-orange-600 mt-2">
                  ⚠️ Replace with your actual WiFi credentials before flashing
                </div>
              </div>
            </div>
          </div>

          {/* Automated Setup Command */}
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <Terminal className="w-4 h-4 text-green-600" />
              <span className="font-medium">Automated Setup (Recommended)</span>
            </div>
            <div className="bg-green-50 border-2 border-green-200 p-4 rounded-lg">
              <div className="space-y-3">
                <p className="text-sm text-green-800 font-medium">
                  ✨ One-command installation! SSH into your Pi and run:
                </p>
                <div className="bg-gray-900 text-green-400 p-3 rounded font-mono text-sm">
                  <pre className="whitespace-pre-wrap">{automatedSetupCommand}</pre>
                </div>
                <Button
                  variant="default"
                  onClick={() => copyToClipboard(automatedSetupCommand, 'automated')}
                  className="w-full bg-green-600 hover:bg-green-700"
                >
                  {copiedSection === 'automated' ? (
                    <>
                      <CheckCircle className="w-4 h-4 mr-2" />
                      Command Copied!
                    </>
                  ) : (
                    <>
                      <Copy className="w-4 h-4 mr-2" />
                      Copy Automated Setup Command
                    </>
                  )}
                </Button>
                <p className="text-xs text-green-700">
                  This script will automatically install all dependencies, configure the device, and start the service.
                </p>
              </div>
            </div>
          </div>

          {/* Manual Setup Commands (Collapsible) */}
          <details className="space-y-4">
            <summary className="cursor-pointer flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900">
              <Terminal className="w-4 h-4" />
              <span className="font-medium">Manual Setup (Advanced)</span>
            </summary>
            <div className="mt-4 space-y-3">
              <p className="text-sm text-gray-600">
                If the automated script fails, you can run these commands manually:
              </p>
              <div className="bg-gray-900 text-green-400 p-4 rounded-lg font-mono text-sm max-h-96 overflow-y-auto">
                <pre className="whitespace-pre-wrap">{manualSetupCommands}</pre>
              </div>
              <Button
                variant="outline"
                onClick={() => copyToClipboard(manualSetupCommands, 'manual')}
                className="w-full"
              >
                {copiedSection === 'manual' ? (
                  <>
                    <CheckCircle className="w-4 h-4 mr-2" />
                    Manual Commands Copied!
                  </>
                ) : (
                  <>
                    <Copy className="w-4 h-4 mr-2" />
                    Copy Manual Setup Commands
                  </>
                )}
              </Button>
            </div>
          </details>
        </div>
        
        <DialogFooter>
          <Button onClick={() => onOpenChange(false)}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
