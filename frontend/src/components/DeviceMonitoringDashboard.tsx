import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import {
  Activity,
  AlertTriangle,
  Battery,
  Wifi,
  Thermometer,
  HardDrive,
  RefreshCw,
  Terminal,
  CheckCircle,
  XCircle,
  Clock,
  TrendingUp,
  TrendingDown
} from 'lucide-react';
import { apiClient } from '../lib/api';

interface DeviceHealthSummary {
  device_id: number;
  device_name: string;
  is_online: boolean;
  last_seen: string | null;
  battery_level: number | null;
  signal_strength: number | null;
  temperature: number | null;
  storage_usage: number | null;
  health_score: number;
  active_alerts: number;
  critical_alerts: number;
}

interface MonitoringDashboard {
  total_devices: number;
  online_devices: number;
  offline_devices: number;
  devices_with_alerts: number;
  critical_alerts: number;
  avg_battery_level: number | null;
  avg_signal_strength: number | null;
  devices_low_battery: number;
  devices_high_temp: number;
  device_health_summary: DeviceHealthSummary[];
}

interface DeviceAlert {
  id: number;
  device_id: number;
  alert_type: string;
  severity: string;
  title: string;
  message: string;
  is_resolved: boolean;
  created_at: string;
  resolved_at: string | null;
}

const DeviceMonitoringDashboard: React.FC = () => {
  const [dashboard, setDashboard] = useState<MonitoringDashboard | null>(null);
  const [alerts, setAlerts] = useState<DeviceAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedDevice, setSelectedDevice] = useState<number | null>(null);

  useEffect(() => {
    loadDashboardData();
    const interval = setInterval(loadDashboardData, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, []);

  const loadDashboardData = async () => {
    try {
      const [dashboardData, alertsData] = await Promise.all([
        apiClient.getMonitoringDashboard(),
        apiClient.listAlerts({ is_resolved: false, limit: 50 })
      ]);
      setDashboard(dashboardData);
      setAlerts(alertsData);
      setError('');
    } catch (err: any) {
      setError(err.message || 'Failed to load monitoring data');
    } finally {
      setLoading(false);
    }
  };

  const handleResolveAlert = async (alertId: number) => {
    try {
      await apiClient.resolveAlert(alertId, { resolution_note: 'Resolved from dashboard' });
      await loadDashboardData();
    } catch (err: any) {
      setError(err.message || 'Failed to resolve alert');
    }
  };

  const handleIssueCommand = async (deviceId: number, commandType: string) => {
    try {
      await apiClient.issueRemoteCommand(deviceId, { command_type: commandType });
      setError('');
      alert(`Command "${commandType}" issued successfully!`);
    } catch (err: any) {
      setError(err.message || 'Failed to issue command');
    }
  };

  const getHealthScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-600';
    if (score >= 60) return 'text-yellow-600';
    if (score >= 40) return 'text-orange-600';
    return 'text-red-600';
  };

  const getSeverityBadge = (severity: string) => {
    const variants: Record<string, any> = {
      critical: 'destructive',
      error: 'destructive',
      warning: 'default',
      info: 'secondary'
    };
    return variants[severity] || 'default';
  };

  const formatLastSeen = (lastSeen: string | null) => {
    if (!lastSeen) return 'Never';
    const date = new Date(lastSeen);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}d ago`;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-gray-400" />
      </div>
    );
  }

  if (!dashboard) {
    return (
      <div className="text-center py-8">
        <p className="text-red-600">{error || 'Failed to load monitoring data'}</p>
        <Button onClick={loadDashboardData} className="mt-4">
          <RefreshCw className="w-4 h-4 mr-2" />
          Retry
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Device Monitoring</h2>
        <Button onClick={loadDashboardData} variant="outline" size="sm">
          <RefreshCw className="w-4 h-4 mr-2" />
          Refresh
        </Button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">Total Devices</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{dashboard.total_devices}</div>
            <div className="text-sm text-gray-500 mt-1">
              <span className="text-green-600">{dashboard.online_devices} online</span>
              {' • '}
              <span className="text-gray-600">{dashboard.offline_devices} offline</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">Active Alerts</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{dashboard.devices_with_alerts}</div>
            <div className="text-sm text-gray-500 mt-1">
              <span className="text-red-600">{dashboard.critical_alerts} critical</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">Avg Battery</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">
              {dashboard.avg_battery_level ? `${Math.round(dashboard.avg_battery_level)}%` : 'N/A'}
            </div>
            <div className="text-sm text-gray-500 mt-1">
              {dashboard.devices_low_battery > 0 && (
                <span className="text-orange-600">{dashboard.devices_low_battery} low battery</span>
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">Avg Signal</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">
              {dashboard.avg_signal_strength ? `${Math.round(dashboard.avg_signal_strength)}%` : 'N/A'}
            </div>
            <div className="text-sm text-gray-500 mt-1">
              {dashboard.devices_high_temp > 0 && (
                <span className="text-red-600">{dashboard.devices_high_temp} high temp</span>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="devices" className="w-full">
        <TabsList>
          <TabsTrigger value="devices">Device Health</TabsTrigger>
          <TabsTrigger value="alerts">
            Alerts
            {alerts.length > 0 && (
              <Badge variant="destructive" className="ml-2">{alerts.length}</Badge>
            )}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="devices" className="space-y-4">
          <div className="grid grid-cols-1 gap-4">
            {dashboard.device_health_summary.map((device) => (
              <Card key={device.device_id} className={device.critical_alerts > 0 ? 'border-red-300' : ''}>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <CardTitle className="text-lg">{device.device_name}</CardTitle>
                      <Badge variant={device.is_online ? 'default' : 'secondary'}>
                        {device.is_online ? 'Online' : 'Offline'}
                      </Badge>
                      {device.active_alerts > 0 && (
                        <Badge variant="destructive">
                          {device.active_alerts} alert{device.active_alerts > 1 ? 's' : ''}
                        </Badge>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`text-2xl font-bold ${getHealthScoreColor(device.health_score)}`}>
                        {device.health_score}
                      </span>
                      <span className="text-sm text-gray-500">health</span>
                    </div>
                  </div>
                  <CardDescription>
                    Last seen: {formatLastSeen(device.last_seen)}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                    <div className="flex items-center gap-2">
                      <Battery className="w-4 h-4 text-gray-500" />
                      <div>
                        <div className="text-sm font-medium">
                          {device.battery_level !== null ? `${Math.round(device.battery_level)}%` : 'N/A'}
                        </div>
                        <div className="text-xs text-gray-500">Battery</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Wifi className="w-4 h-4 text-gray-500" />
                      <div>
                        <div className="text-sm font-medium">
                          {device.signal_strength !== null ? `${Math.round(device.signal_strength)}%` : 'N/A'}
                        </div>
                        <div className="text-xs text-gray-500">Signal</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Thermometer className="w-4 h-4 text-gray-500" />
                      <div>
                        <div className="text-sm font-medium">
                          {device.temperature !== null ? `${Math.round(device.temperature)}°C` : 'N/A'}
                        </div>
                        <div className="text-xs text-gray-500">Temp</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <HardDrive className="w-4 h-4 text-gray-500" />
                      <div>
                        <div className="text-sm font-medium">
                          {device.storage_usage !== null ? `${Math.round(device.storage_usage)}%` : 'N/A'}
                        </div>
                        <div className="text-xs text-gray-500">Storage</div>
                      </div>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleIssueCommand(device.device_id, 'refresh_display')}
                    >
                      <RefreshCw className="w-4 h-4 mr-1" />
                      Refresh Display
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleIssueCommand(device.device_id, 'reboot')}
                    >
                      <Activity className="w-4 h-4 mr-1" />
                      Reboot
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleIssueCommand(device.device_id, 'get_diagnostics')}
                    >
                      <Terminal className="w-4 h-4 mr-1" />
                      Diagnostics
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="alerts" className="space-y-4">
          {alerts.length === 0 ? (
            <Card>
              <CardContent className="text-center py-8">
                <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-2" />
                <p className="text-gray-600">No active alerts</p>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-3">
              {alerts.map((alert) => (
                <Card key={alert.id} className={alert.severity === 'critical' ? 'border-red-300' : ''}>
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <AlertTriangle className={`w-5 h-5 ${
                            alert.severity === 'critical' ? 'text-red-600' :
                            alert.severity === 'error' ? 'text-red-500' :
                            alert.severity === 'warning' ? 'text-yellow-600' :
                            'text-blue-500'
                          }`} />
                          <h3 className="font-semibold">{alert.title}</h3>
                          <Badge variant={getSeverityBadge(alert.severity)}>
                            {alert.severity}
                          </Badge>
                        </div>
                        <p className="text-sm text-gray-600 mb-2">{alert.message}</p>
                        <div className="flex items-center gap-2 text-xs text-gray-500">
                          <Clock className="w-3 h-3" />
                          {new Date(alert.created_at).toLocaleString()}
                        </div>
                      </div>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleResolveAlert(alert.id)}
                      >
                        Resolve
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default DeviceMonitoringDashboard;
