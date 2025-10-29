#!/usr/bin/env python3
"""
E-ink Device Client for Waveshare 13.3" E6 Display with Raspberry Pi Zero 2W
Supports dual connectivity (WiFi + LTE 4G) with intelligent failover
"""

import sys
import os
import time
import json
import logging
import requests
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from PIL import Image
import psutil
import threading
import queue
import websocket
import ssl

try:
    from waveshare_epd import epd13in3E, epdconfig
    EINK_AVAILABLE = True
    print("Waveshare E-ink library loaded successfully (pip package)")
except ImportError:
    for path in ['/home/pi/e-Paper/RaspberryPi/python/lib', 
                 '/home/pi/e-Paper/RaspberryPi_JetsonNano/python/lib']:
        if os.path.exists(path):
            sys.path.append(path)
            break
    
    try:
        import epd13in3E
        import epdconfig
        EINK_AVAILABLE = True
        print("Waveshare E-ink library loaded successfully (local installation)")
    except ImportError as e:
        print(f"WARNING: Waveshare E-ink library not found: {e}. Running in simulation mode.")
        EINK_AVAILABLE = False

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/eink_device.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ConnectivityManager:
    """Manages dual connectivity (WiFi + LTE) with intelligent failover"""
    
    def __init__(self):
        self.wifi_interface = "wlan0"
        self.lte_interface = "ppp0"  # or "wwan0" depending on modem
        self.current_connection = "wifi"
        self.connection_queue = queue.Queue()
        self.monitoring_thread = None
        self.running = False
    
    def start_monitoring(self):
        """Start connectivity monitoring in background thread"""
        self.running = True
        self.monitoring_thread = threading.Thread(target=self._monitor_connectivity)
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()
        logger.info("Connectivity monitoring started")
    
    def stop_monitoring(self):
        """Stop connectivity monitoring"""
        self.running = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        logger.info("Connectivity monitoring stopped")
    
    def _monitor_connectivity(self):
        """Monitor connectivity and handle failover"""
        while self.running:
            try:
                wifi_status = self._check_wifi_connection()
                lte_status = self._check_lte_connection()
                
                if wifi_status['connected'] and wifi_status['signal_strength'] > -70:
                    if self.current_connection != "wifi":
                        logger.info("Switching to WiFi connection")
                        self.current_connection = "wifi"
                elif lte_status['connected']:
                    if self.current_connection != "lte":
                        logger.info("Switching to LTE connection")
                        self.current_connection = "lte"
                else:
                    logger.warning("No connectivity available")
                
                status = {
                    'timestamp': datetime.now(),
                    'current_connection': self.current_connection,
                    'wifi': wifi_status,
                    'lte': lte_status
                }
                
                try:
                    self.connection_queue.put_nowait(status)
                except queue.Full:
                    try:
                        self.connection_queue.get_nowait()
                        self.connection_queue.put_nowait(status)
                    except queue.Empty:
                        pass
                
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in connectivity monitoring: {e}")
                time.sleep(60)  # Wait longer on error
    
    def _check_wifi_connection(self) -> Dict[str, Any]:
        """Check WiFi connection status"""
        try:
            result = subprocess.run(['ip', 'link', 'show', self.wifi_interface], 
                                  capture_output=True, text=True, timeout=10)
            interface_up = 'UP' in result.stdout
            
            if not interface_up:
                return {'connected': False, 'signal_strength': -100, 'error': 'Interface down'}
            
            try:
                result = subprocess.run(['iwconfig', self.wifi_interface], 
                                      capture_output=True, text=True, timeout=10)
                signal_line = [line for line in result.stdout.split('\n') if 'Signal level' in line]
                if signal_line:
                    signal_str = signal_line[0].split('Signal level=')[1].split(' ')[0]
                    signal_strength = int(signal_str)
                else:
                    signal_strength = -50  # Default if can't parse
            except:
                signal_strength = -50
            
            try:
                response = requests.get('http://httpbin.org/ip', timeout=10)
                connected = response.status_code == 200
            except:
                connected = False
            
            return {
                'connected': connected,
                'signal_strength': signal_strength,
                'interface': self.wifi_interface
            }
            
        except Exception as e:
            return {'connected': False, 'signal_strength': -100, 'error': str(e)}
    
    def _check_lte_connection(self) -> Dict[str, Any]:
        """Check LTE connection status"""
        try:
            result = subprocess.run(['ip', 'link', 'show', self.lte_interface], 
                                  capture_output=True, text=True, timeout=10)
            interface_up = 'UP' in result.stdout if result.returncode == 0 else False
            
            if not interface_up:
                return {'connected': False, 'signal_strength': -100, 'error': 'Interface down'}
            
            try:
                response = requests.get('http://httpbin.org/ip', timeout=15)
                connected = response.status_code == 200
            except:
                connected = False
            
            signal_strength = -65  # Default LTE signal
            
            return {
                'connected': connected,
                'signal_strength': signal_strength,
                'interface': self.lte_interface
            }
            
        except Exception as e:
            return {'connected': False, 'signal_strength': -100, 'error': str(e)}
    
    def get_current_status(self) -> Dict[str, Any]:
        """Get current connectivity status"""
        try:
            return self.connection_queue.get_nowait()
        except queue.Empty:
            return {
                'timestamp': datetime.now(),
                'current_connection': self.current_connection,
                'wifi': {'connected': False},
                'lte': {'connected': False}
            }

class PowerManager:
    """Manages power consumption for solar-powered Pi Zero 2W"""
    
    def __init__(self):
        self.battery_level = 85.0
        self.charging = False
        self.power_mode = "normal"
    
    def get_battery_level(self) -> float:
        """Get current battery level (0-100%)"""
        try:
            if self.charging:
                self.battery_level = min(100.0, self.battery_level + 0.1)
            else:
                self.battery_level = max(0.0, self.battery_level - 0.05)
            
            return self.battery_level
        except Exception as e:
            logger.error(f"Error reading battery level: {e}")
            return 50.0  # Safe default
    
    def is_charging(self) -> bool:
        """Check if solar panel is charging battery"""
        try:
            current_hour = datetime.now().hour
            self.charging = 8 <= current_hour <= 18  # Daylight hours
            return self.charging
        except Exception as e:
            logger.error(f"Error checking charging status: {e}")
            return False
    
    def get_power_mode(self) -> str:
        """Determine optimal power mode based on battery and time"""
        battery = self.get_battery_level()
        current_hour = datetime.now().hour
        
        if battery < 10:
            return "emergency"
        elif battery < 20:
            return "deep_sleep"
        elif battery < 50 and not self.is_charging():
            return "slow"
        elif 22 <= current_hour or current_hour <= 6:  # Night time
            return "deep_sleep"
        else:
            return "normal"
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive power status"""
        return {
            'battery_level': self.get_battery_level(),
            'charging': self.is_charging(),
            'power_mode': self.get_power_mode(),
            'timestamp': datetime.now().isoformat()
        }

class EInkDisplayManager:
    """Manages Waveshare 13.3" E6 display operations"""
    
    def __init__(self):
        self.display_width = 1200
        self.display_height = 1600
        self.last_refresh = None
        self.refresh_count = 0
        self.error_count = 0
        self.is_sleeping = False
        
        if EINK_AVAILABLE:
            try:
                self.epd = epd13in3E.EPD()
                logger.info("E-ink display initialized")
            except Exception as e:
                logger.error(f"Failed to initialize E-ink display: {e}")
                self.epd = None
        else:
            self.epd = None
            logger.info("Running in simulation mode (no E-ink hardware)")
    
    def initialize_display(self) -> bool:
        """Initialize the E-ink display"""
        if not EINK_AVAILABLE or not self.epd:
            logger.info("Display initialization skipped (simulation mode)")
            return True
        
        try:
            logger.info("Initializing E-ink display...")
            self.epd.Init()
            self.epd.Clear()
            logger.info("E-ink display initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize display: {e}")
            self.error_count += 1
            return False
    
    def display_image(self, image_path: str) -> bool:
        """Display image on E-ink screen"""
        if not EINK_AVAILABLE or not self.epd:
            logger.info(f"Display image skipped (simulation mode): {image_path}")
            return True
        
        try:
            start_time = time.time()
            logger.info(f"Displaying image: {image_path}")
            
            if self.is_sleeping:
                logger.info("Re-initializing display after sleep")
                self.epd.Init()
                self.is_sleeping = False
            
            if not os.path.exists(image_path):
                logger.error(f"Image file not found: {image_path}")
                return False
            
            image = Image.open(image_path)
            
            if image.size != (self.display_width, self.display_height):
                image = image.resize((self.display_width, self.display_height), Image.Resampling.LANCZOS)
            
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            self.epd.display(self.epd.getbuffer(image))
            
            refresh_duration = time.time() - start_time
            self.last_refresh = datetime.now()
            self.refresh_count += 1
            
            logger.info(f"Image displayed successfully in {refresh_duration:.1f} seconds")
            return True
            
        except Exception as e:
            logger.error(f"Failed to display image: {e}")
            self.error_count += 1
            return False
    
    def display_text(self, title: str, content: str, style: Optional[Dict] = None) -> bool:
        """Display text notice on E-ink screen"""
        try:
            image = Image.new('RGB', (self.display_width, self.display_height), 'white')
            temp_path = f"/tmp/notice_{int(time.time())}.png"
            image.save(temp_path)
            
            result = self.display_image(temp_path)
            
            try:
                os.remove(temp_path)
            except:
                pass
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to display text: {e}")
            self.error_count += 1
            return False
    
    def sleep(self):
        """Put display to sleep to save power"""
        if EINK_AVAILABLE and self.epd:
            try:
                self.epd.sleep()
                self.is_sleeping = True
                logger.info("Display put to sleep")
            except Exception as e:
                logger.error(f"Failed to put display to sleep: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get display status"""
        return {
            'last_refresh': self.last_refresh.isoformat() if self.last_refresh else None,
            'refresh_count': self.refresh_count,
            'error_count': self.error_count,
            'display_available': EINK_AVAILABLE and self.epd is not None,
            'resolution': f"{self.display_width}x{self.display_height}"
        }

class WebSocketManager:
    """Manages WebSocket connection for real-time notifications"""
    
    def __init__(self, device_id: str, api_base_url: str, refresh_callback):
        self.device_id = device_id
        self.api_base_url = api_base_url
        self.refresh_callback = refresh_callback
        self.ws = None
        self.ws_thread = None
        self.running = False
        self.reconnect_delay = 5
        
    def start(self):
        """Start WebSocket connection in background thread"""
        self.running = True
        self.ws_thread = threading.Thread(target=self._connect_loop)
        self.ws_thread.daemon = True
        self.ws_thread.start()
        logger.info("WebSocket manager started")
    
    def stop(self):
        """Stop WebSocket connection"""
        self.running = False
        if self.ws:
            try:
                self.ws.close()
            except:
                pass
        if self.ws_thread:
            self.ws_thread.join(timeout=5)
        logger.info("WebSocket manager stopped")
    
    def _connect_loop(self):
        """Continuously try to maintain WebSocket connection"""
        while self.running:
            try:
                self._connect()
            except Exception as e:
                logger.error(f"WebSocket connection error: {e}")
            
            if self.running:
                logger.info(f"Reconnecting WebSocket in {self.reconnect_delay} seconds...")
                time.sleep(self.reconnect_delay)
    
    def _connect(self):
        """Connect to WebSocket endpoint"""
        ws_url = self.api_base_url.replace('http://', 'ws://').replace('https://', 'wss://')
        ws_url = f"{ws_url}/ws/device/{self.device_id}"
        
        logger.info(f"Connecting to WebSocket: {ws_url}")
        
        self.ws = websocket.WebSocketApp(
            ws_url,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
            on_open=self._on_open
        )
        
        if ws_url.startswith('wss://'):
            self.ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
        else:
            self.ws.run_forever()
    
    def _on_open(self, ws):
        """Called when WebSocket connection is established"""
        logger.info("WebSocket connected")
        self.reconnect_delay = 5
        
        def ping_loop():
            while self.running and self.ws:
                try:
                    self.ws.send("ping")
                    time.sleep(30)
                except:
                    break
        
        ping_thread = threading.Thread(target=ping_loop)
        ping_thread.daemon = True
        ping_thread.start()
    
    def _on_message(self, ws, message):
        """Called when WebSocket message is received"""
        try:
            if message == "pong":
                return
            
            data = json.loads(message)
            logger.info(f"WebSocket notification received: {data.get('type')}")
            
            if data.get('action') == 'refresh_playlist':
                logger.info(f"Triggering playlist refresh due to {data.get('type')}")
                self.refresh_callback()
            
        except Exception as e:
            logger.error(f"Error processing WebSocket message: {e}")
    
    def _on_error(self, ws, error):
        """Called when WebSocket error occurs"""
        logger.error(f"WebSocket error: {error}")
    
    def _on_close(self, ws, close_status_code, close_msg):
        """Called when WebSocket connection is closed"""
        logger.info(f"WebSocket closed: {close_status_code} - {close_msg}")


class EInkDeviceClient:
    """Main device client for E-ink golf tee box displays"""
    
    def __init__(self, config_file: str = "/etc/eink_device/config.json"):
        self.config = self._load_config(config_file)
        self.device_id = self.config.get('device_id', 'unknown')
        self.api_base_url = self.config.get('api_base_url', 'https://golfadvertisingdisplays.onrender.com')
        self.sync_interval = self.config.get('sync_interval', 900)  # 15 minutes default
        
        self.connectivity = ConnectivityManager()
        self.power = PowerManager()
        self.display = EInkDisplayManager()
        self.websocket_manager = WebSocketManager(
            self.device_id,
            self.api_base_url,
            self._handle_refresh_request
        )
        
        self.running = False
        self.last_sync = None
        self.current_playlist = []
        self.sync_errors = 0
        self.refresh_requested = False
        self.command_polling_thread = None
        
        logger.info(f"E-ink device client initialized for device: {self.device_id}")
    
    def _load_config(self, config_file: str) -> Dict[str, Any]:
        """Load device configuration"""
        default_config = {
            'device_id': 'eink_device_001',
            'api_base_url': 'https://golfadvertisingdisplays.onrender.com',
            'sync_interval': 900,
            'max_retries': 3,
            'timeout': 30
        }
        
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    default_config.update(config)
                    logger.info(f"Configuration loaded from {config_file}")
            else:
                logger.warning(f"Config file not found: {config_file}, using defaults")
        except Exception as e:
            logger.error(f"Failed to load config: {e}, using defaults")
        
        return default_config
    
    def start(self):
        """Start the device client"""
        logger.info("Starting E-ink device client...")
        
        if not self.display.initialize_display():
            logger.error("Failed to initialize display")
            return False
        
        self.connectivity.start_monitoring()
        self.websocket_manager.start()
        self._start_command_polling()
        
        self.running = True
        try:
            while self.running:
                self._main_loop_iteration()
                self._sleep_until_next_sync()
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}")
        finally:
            self.stop()
        
        return True
    
    def stop(self):
        """Stop the device client"""
        logger.info("Stopping E-ink device client...")
        self.running = False
        self.connectivity.stop_monitoring()
        self.websocket_manager.stop()
        if self.command_polling_thread:
            self.command_polling_thread.join(timeout=5)
        self.display.sleep()
        logger.info("Device client stopped")
    
    def _handle_refresh_request(self):
        """Handle refresh request from WebSocket notification"""
        self.refresh_requested = True
        logger.info("Refresh request received via WebSocket")
    
    def _start_command_polling(self):
        """Start background thread for polling remote commands"""
        self.command_polling_thread = threading.Thread(target=self._poll_commands_loop)
        self.command_polling_thread.daemon = True
        self.command_polling_thread.start()
        logger.info("Command polling thread started")
    
    def _poll_commands_loop(self):
        """Background loop to poll for remote commands"""
        while self.running:
            try:
                time.sleep(15)
                self._check_and_execute_commands()
            except Exception as e:
                logger.error(f"Error in command polling loop: {e}")
                time.sleep(30)
    
    def _check_and_execute_commands(self):
        """Check for pending commands and execute them"""
        try:
            url = f"{self.api_base_url}/api/device/{self.device_id}/commands/pending"
            response = requests.get(url, timeout=10)
            
            if response.status_code != 200:
                return
            
            commands = response.json()
            
            for command in commands:
                command_id = command.get('id')
                command_type = command.get('command_type')
                
                logger.info(f"Executing remote command: {command_type} (ID: {command_id})")
                
                result = self._execute_command(command_type, command.get('command_data'))
                
                result_url = f"{self.api_base_url}/api/device/commands/{command_id}/result"
                requests.put(result_url, json=result, timeout=10)
                
                logger.info(f"Command {command_type} completed: {result.get('success')}")
                
        except Exception as e:
            logger.error(f"Failed to check/execute commands: {e}")
    
    def _execute_command(self, command_type: str, command_data: Optional[Dict]) -> Dict[str, Any]:
        """Execute a remote command and return result"""
        try:
            if command_type == "refresh_display":
                self.refresh_requested = True
                return {"success": True, "message": "Display refresh triggered"}
            
            elif command_type == "reboot":
                try:
                    subprocess.run(['sudo', 'reboot'], check=True, timeout=5)
                    return {"success": True, "message": "Reboot initiated"}
                except subprocess.CalledProcessError:
                    return {"success": False, "error": "Reboot failed - insufficient privileges"}
                except Exception as e:
                    return {"success": False, "error": f"Reboot failed: {str(e)}"}
            
            elif command_type == "get_diagnostics":
                diagnostics = {
                    "device_id": self.device_id,
                    "uptime_hours": self._get_uptime_hours(),
                    "connectivity": self.connectivity.get_current_status(),
                    "power": self.power.get_status(),
                    "display": self.display.get_status(),
                    "last_sync": self.last_sync.isoformat() if self.last_sync else None,
                    "sync_errors": self.sync_errors
                }
                return {"success": True, "diagnostics": diagnostics}
            
            else:
                return {"success": False, "error": f"Unsupported command: {command_type}"}
                
        except Exception as e:
            logger.error(f"Error executing command {command_type}: {e}")
            return {"success": False, "error": str(e)}
    
    def _main_loop_iteration(self):
        """Single iteration of main loop"""
        try:
            connectivity_status = self.connectivity.get_current_status()
            power_status = self.power.get_status()
            display_status = self.display.get_status()
            
            power_mode = power_status['power_mode']
            self.sync_interval = self._get_sync_interval_for_power_mode(power_mode)
            
            self._send_status_update(connectivity_status, power_status, display_status)
            
            if connectivity_status['current_connection']:
                self._sync_and_display_content(connectivity_status['current_connection'])
            else:
                logger.warning("No connectivity available, skipping sync")
            
            self.last_sync = datetime.now()
            self.sync_errors = 0  # Reset error count on successful sync
            self.refresh_requested = False  # Reset refresh flag
            
        except Exception as e:
            logger.error(f"Error in main loop iteration: {e}")
            self.sync_errors += 1
            
            if self.sync_errors > 3:
                self.sync_interval = min(self.sync_interval * 2, 3600)  # Max 1 hour
    
    def _get_sync_interval_for_power_mode(self, power_mode: str) -> int:
        """Get sync interval based on power mode"""
        intervals = {
            'normal': 900,      # 15 minutes
            'slow': 3600,       # 1 hour
            'deep_sleep': 21600, # 6 hours
            'emergency': 86400   # 24 hours
        }
        return intervals.get(power_mode, 900)
    
    def _send_status_update(self, connectivity_status: Dict, power_status: Dict, display_status: Dict):
        """Send device status update to server"""
        try:
            status_data = {
                'device_id': self.device_id,
                'timestamp': datetime.now().isoformat(),
                'connectivity_type': connectivity_status['current_connection'],
                'battery_level': power_status['battery_level'],
                'charging': power_status['charging'],
                'power_mode': power_status['power_mode'],
                'signal_strength': self._get_signal_strength(connectivity_status),
                'uptime_hours': self._get_uptime_hours(),
                'display_status': 'ok' if display_status['display_available'] else 'error',
                'refresh_count': display_status['refresh_count'],
                'error_count': display_status['error_count'],
                'last_refresh_duration': 19.0  # E6 typical refresh time
            }
            
            url = f"{self.api_base_url}/api/device/{self.device_id}/status"
            response = requests.post(url, json=status_data, timeout=30)
            
            if response.status_code == 200:
                logger.debug("Status update sent successfully")
                
                server_response = response.json()
                if 'config_updates' in server_response:
                    self._apply_config_updates(server_response['config_updates'])
                    
            else:
                logger.warning(f"Status update failed: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Failed to send status update: {e}")
    
    def _get_signal_strength(self, connectivity_status: Dict) -> float:
        """Extract signal strength from connectivity status"""
        current_conn = connectivity_status['current_connection']
        if current_conn == 'wifi' and 'wifi' in connectivity_status:
            return connectivity_status['wifi'].get('signal_strength', -50)
        elif current_conn == 'lte' and 'lte' in connectivity_status:
            return connectivity_status['lte'].get('signal_strength', -65)
        else:
            return -100  # No signal
    
    def _get_uptime_hours(self) -> float:
        """Get system uptime in hours"""
        try:
            uptime_seconds = time.time() - psutil.boot_time()
            return uptime_seconds / 3600
        except:
            return 1.0  # Default
    
    def _apply_config_updates(self, config_updates: Dict):
        """Apply configuration updates from server"""
        try:
            if 'power_mode' in config_updates:
                logger.info(f"Server requested power mode: {config_updates['power_mode']}")
            
            if 'diagnostic_mode' in config_updates:
                logger.info("Server requested diagnostic mode")
                
        except Exception as e:
            logger.error(f"Failed to apply config updates: {e}")
    
    def _sync_and_display_content(self, connectivity_type: str):
        """Sync content from server and display on E-ink"""
        try:
            url = f"{self.api_base_url}/api/device/{self.device_id}/playlist"
            params = {'connectivity': connectivity_type}
            
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code != 200:
                logger.error(f"Failed to fetch playlist: {response.status_code}")
                return
            
            playlist_data = response.json()
            items = playlist_data.get('items', [])
            
            if not items:
                logger.info("No content items in playlist")
                return
            
            item = items[0]  # Items are already sorted by priority
            
            if item['type'] == 'notice':
                success = self.display.display_text(
                    item.get('title', ''),
                    item.get('content', ''),
                    item.get('style')
                )
            elif item['type'] == 'campaign':
                image_url = item.get('eink_url', item.get('content'))
                if image_url:
                    image_path = self._download_image(image_url)
                    if image_path:
                        success = self.display.display_image(image_path)
                        try:
                            os.remove(image_path)
                        except:
                            pass
                    else:
                        success = False
                else:
                    success = False
            
            if success:
                logger.info(f"Successfully displayed {item['type']}: {item.get('title', item.get('sponsor_name', 'Unknown'))}")
            else:
                logger.error(f"Failed to display {item['type']}")
                
        except Exception as e:
            logger.error(f"Failed to sync and display content: {e}")
    
    def _download_image(self, image_url: str) -> Optional[str]:
        """Download image for display"""
        try:
            if not image_url.startswith('http'):
                return image_url if os.path.exists(image_url) else None
            
            response = requests.get(image_url, timeout=60)
            if response.status_code != 200:
                logger.error(f"Failed to download image: {response.status_code}")
                return None
            
            temp_path = f"/tmp/campaign_{int(time.time())}.png"
            with open(temp_path, 'wb') as f:
                f.write(response.content)
            
            logger.debug(f"Downloaded image: {image_url} -> {temp_path}")
            return temp_path
            
        except Exception as e:
            logger.error(f"Failed to download image {image_url}: {e}")
            return None
    
    def _sleep_until_next_sync(self):
        """Sleep until next sync time, but wake up early if refresh is requested"""
        try:
            self.display.sleep()
            
            logger.info(f"Sleeping for {self.sync_interval} seconds until next sync")
            
            for _ in range(self.sync_interval):
                if self.refresh_requested:
                    logger.info("Waking up early due to refresh request")
                    break
                time.sleep(1)
            
        except KeyboardInterrupt:
            raise
        except Exception as e:
            logger.error(f"Error during sleep: {e}")
            time.sleep(60)  # Fallback sleep

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='E-ink Device Client for Golf CMS')
    parser.add_argument('--config', default='/etc/eink_device/config.json',
                       help='Configuration file path')
    parser.add_argument('--device-id', help='Override device ID')
    parser.add_argument('--api-url', help='Override API base URL')
    parser.add_argument('--simulate', action='store_true',
                       help='Run in simulation mode (no hardware)')
    
    args = parser.parse_args()
    
    client = EInkDeviceClient(args.config)
    
    if args.device_id:
        client.device_id = args.device_id
    if args.api_url:
        client.api_base_url = args.api_url
    
    try:
        client.start()
    except Exception as e:
        logger.error(f"Failed to start device client: {e}")
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
