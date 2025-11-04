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
  Clock,
  Download,
  Table as TableIcon,
  Grid,
  TrendingUp,
  Eye,
  EyeOff
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
  status_color: 'green' | 'yellow' | 'red';
  status_reason: string;
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

interface DeviceCommand {
  id: number;
  device_id: number;
  command_type: string;
  status: 'pending' | 'executing' | 'completed' | 'failed' | 'cancelled';
  issued_at: string;
  executed_at: string | null;
  result: any;
  error_message: string | null;
}

const DeviceMonitoringDashboard: React.FC = () => {
  const [dashboard, setDashboard] = useState<MonitoringDashboard | null>(null);
  const [alerts, setAlerts] = useState<DeviceAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [deviceCommands, setDeviceCommands] = useState<Record<number, DeviceCommand[]>>({});
  const [pendingCommands, setPendingCommands] = useState<Record<number, number>>({});
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [sortBy, setSortBy] = useState<string>('status_color');
  const [viewMode, setViewMode] = useState<'cards' | 'table'>('cards');
  const [selectedDevices, setSelectedDevices] = useState<Set<number>>(new Set());
  const [visibleColumns, setVisibleColumns] = useState<Set<string>>(new Set([
    'name', 'status', 'battery', 'signal', 'temperature', 'storage', 'health', 'alerts'
  ]));

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
      if (pendingCommands[deviceId]) {
        setError('A command is already in progress for this device');
        return;
      }

      const command = await apiClient.issueRemoteCommand(deviceId, { command_type: commandType });
      console.log(`Command issued: ${commandType} (ID: ${command.id}) for device ${deviceId}`);
      setError('');
      
      setPendingCommands(prev => ({ ...prev, [deviceId]: command.id }));
      
      pollCommandStatus(deviceId, command.id);
    } catch (err: any) {
      console.error('Failed to issue command:', err);
      setError(err.message || 'Failed to issue command');
    }
  };

  const pollCommandStatus = async (deviceId: number, commandId: number) => {
    const maxAttempts = 60;
    let attempts = 0;
    let retryDelay = 1000;

    const poll = async () => {
      attempts++;
      
      try {
        const commands = await apiClient.getDeviceCommands(deviceId);
        const command = commands.find((cmd: DeviceCommand) => cmd.id === commandId);

        if (command) {
          console.log(`Command ${commandId} status: ${command.status} (attempt ${attempts}/${maxAttempts})`);
          
          setDeviceCommands(prev => ({
            ...prev,
            [deviceId]: [command, ...(prev[deviceId] || []).filter(c => c.id !== commandId)].slice(0, 5)
          }));

          if (command.status === 'completed' || command.status === 'failed') {
            console.log(`Command ${commandId} finished with status: ${command.status}`);
            setPendingCommands(prev => {
              const updated = { ...prev };
              delete updated[deviceId];
              return updated;
            });
            return;
          }
        } else {
          console.warn(`Command ${commandId} not found in response (attempt ${attempts}/${maxAttempts})`);
        }

        if (attempts < maxAttempts) {
          setTimeout(poll, 1000);
        } else {
          setPendingCommands(prev => {
            const updated = { ...prev };
            delete updated[deviceId];
            return updated;
          });
        }
      } catch (err) {
        console.error(`Failed to poll command status (attempt ${attempts}/${maxAttempts}):`, err);
        
        if (attempts < maxAttempts) {
          retryDelay = Math.min(retryDelay * 1.5, 5000);
          setTimeout(poll, retryDelay);
        } else {
          setPendingCommands(prev => {
            const updated = { ...prev };
            delete updated[deviceId];
            return updated;
          });
        }
      }
    };

    poll();
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

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'green': return 'bg-green-500';
      case 'yellow': return 'bg-yellow-500';
      case 'red': return 'bg-red-500';
      default: return 'bg-gray-500';
    }
  };

  const getStatusBorderColor = (status: string) => {
    switch (status) {
      case 'green': return 'border-green-300';
      case 'yellow': return 'border-yellow-300';
      case 'red': return 'border-red-300';
      default: return 'border-gray-300';
    }
  };

  const handleBulkCommand = async (commandType: string) => {
    if (selectedDevices.size === 0) {
      setError('Please select at least one device');
      return;
    }

    try {
      const deviceIds = Array.from(selectedDevices);
      await apiClient.issueBulkCommand(deviceIds, commandType);
      setError('');
      setSelectedDevices(new Set());
      loadDashboardData();
    } catch (err: any) {
      setError(err.message || 'Failed to issue bulk command');
    }
  };

  const handleExportCSV = async () => {
    try {
      const blob = await apiClient.exportDevicesCSV(statusFilter !== 'all' ? statusFilter : undefined);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `device_health_export_${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err: any) {
      setError(err.message || 'Failed to export CSV');
    }
  };

  const toggleDeviceSelection = (deviceId: number) => {
    const newSelection = new Set(selectedDevices);
    if (newSelection.has(deviceId)) {
      newSelection.delete(deviceId);
    } else {
      newSelection.add(deviceId);
    }
    setSelectedDevices(newSelection);
  };

  const toggleAllDevices = () => {
    if (selectedDevices.size === filteredDevices.length) {
      setSelectedDevices(new Set());
    } else {
      setSelectedDevices(new Set(filteredDevices.map(d => d.device_id)));
    }
  };

  const toggleColumn = (column: string) => {
    const newColumns = new Set(visibleColumns);
    if (newColumns.has(column)) {
      newColumns.delete(column);
    } else {
      newColumns.add(column);
    }
    setVisibleColumns(newColumns);
  };

  const filteredDevices = dashboard?.device_health_summary.filter(device => {
    if (statusFilter !== 'all' && device.status_color !== statusFilter) return false;
    if (searchQuery && !device.device_name.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    return true;
  }).sort((a, b) => {
    if (sortBy === 'status_color') {
      const statusOrder = { red: 0, yellow: 1, green: 2 };
      return (statusOrder[a.status_color] || 3) - (statusOrder[b.status_color] || 3);
    } else if (sortBy === 'device_name') {
      return a.device_name.localeCompare(b.device_name);
    } else if (sortBy === 'last_seen') {
      const aTime = a.last_seen ? new Date(a.last_seen).getTime() : 0;
      const bTime = b.last_seen ? new Date(b.last_seen).getTime() : 0;
      return bTime - aTime;
    } else if (sortBy === 'battery') {
      return (b.battery_level || 0) - (a.battery_level || 0);
    } else if (sortBy === 'health') {
      return b.health_score - a.health_score;
    }
    return 0;
  }) || [];

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

      {/* Filters and Search */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col gap-4">
            <div className="flex flex-col md:flex-row gap-4">
              <div className="flex-1">
                <input
                  type="text"
                  placeholder="Search devices..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div className="flex gap-2">
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="all">All Status</option>
                  <option value="green">🟢 Healthy</option>
                  <option value="yellow">🟡 Warning</option>
                  <option value="red">🔴 Critical</option>
                </select>
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value)}
                  className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="status_color">Sort by Status</option>
                  <option value="device_name">Sort by Name</option>
                  <option value="last_seen">Sort by Last Seen</option>
                  <option value="battery">Sort by Battery</option>
                  <option value="health">Sort by Health Score</option>
                </select>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setViewMode(viewMode === 'cards' ? 'table' : 'cards')}
                >
                  {viewMode === 'cards' ? <TableIcon className="w-4 h-4" /> : <Grid className="w-4 h-4" />}
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleExportCSV}
                >
                  <Download className="w-4 h-4 mr-1" />
                  CSV
                </Button>
              </div>
            </div>
            
            {selectedDevices.size > 0 && (
              <div className="flex items-center gap-2 p-3 bg-blue-50 rounded-md">
                <span className="text-sm font-medium">{selectedDevices.size} device(s) selected</span>
                <div className="flex gap-2 ml-auto">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleBulkCommand('refresh_display')}
                  >
                    <RefreshCw className="w-3 h-3 mr-1" />
                    Refresh All
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleBulkCommand('reboot')}
                  >
                    <Activity className="w-3 h-3 mr-1" />
                    Reboot All
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setSelectedDevices(new Set())}
                  >
                    Clear
                  </Button>
                </div>
              </div>
            )}
            
            <div className="flex items-center justify-between">
              <div className="text-sm text-gray-600">
                Showing {filteredDevices.length} of {dashboard.device_health_summary.length} devices
              </div>
              {viewMode === 'table' && (
                <div className="flex gap-2">
                  <span className="text-sm text-gray-600">Columns:</span>
                  {['name', 'status', 'battery', 'signal', 'temperature', 'storage', 'health', 'alerts'].map(col => (
                    <button
                      key={col}
                      onClick={() => toggleColumn(col)}
                      className={`text-xs px-2 py-1 rounded ${
                        visibleColumns.has(col) ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-600'
                      }`}
                    >
                      {visibleColumns.has(col) ? <Eye className="w-3 h-3 inline mr-1" /> : <EyeOff className="w-3 h-3 inline mr-1" />}
                      {col}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      <Tabs defaultValue="devices" className="w-full">
        <TabsList>
          <TabsTrigger value="devices">Device Health</TabsTrigger>
          <TabsTrigger value="alerts">
            Alerts
            {alerts.length > 0 && (
              <Badge variant="destructive" className="ml-2">{alerts.length}</Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="trends">
            <TrendingUp className="w-4 h-4 mr-1" />
            Trends
          </TabsTrigger>
        </TabsList>

        <TabsContent value="devices" className="space-y-4">
          {viewMode === 'table' ? (
            <Card>
              <CardContent className="p-0">
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-gray-50 border-b">
                      <tr>
                        <th className="px-4 py-3 text-left">
                          <input
                            type="checkbox"
                            checked={selectedDevices.size === filteredDevices.length && filteredDevices.length > 0}
                            onChange={toggleAllDevices}
                            className="rounded"
                          />
                        </th>
                        {visibleColumns.has('name') && <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Device</th>}
                        {visibleColumns.has('status') && <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>}
                        {visibleColumns.has('battery') && <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Battery</th>}
                        {visibleColumns.has('signal') && <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Signal</th>}
                        {visibleColumns.has('temperature') && <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Temp</th>}
                        {visibleColumns.has('storage') && <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Storage</th>}
                        {visibleColumns.has('health') && <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Health</th>}
                        {visibleColumns.has('alerts') && <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Alerts</th>}
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                      {filteredDevices.map((device) => (
                        <tr key={device.device_id} className={`hover:bg-gray-50 ${getStatusBorderColor(device.status_color)} border-l-4`}>
                          <td className="px-4 py-3">
                            <input
                              type="checkbox"
                              checked={selectedDevices.has(device.device_id)}
                              onChange={() => toggleDeviceSelection(device.device_id)}
                              className="rounded"
                            />
                          </td>
                          {visibleColumns.has('name') && (
                            <td className="px-4 py-3">
                              <div className="flex items-center gap-2">
                                <div className={`w-2 h-2 rounded-full ${getStatusColor(device.status_color)}`}></div>
                                <span className="font-medium">{device.device_name}</span>
                              </div>
                            </td>
                          )}
                          {visibleColumns.has('status') && (
                            <td className="px-4 py-3">
                              <Badge variant={device.is_online ? 'default' : 'secondary'}>
                                {device.is_online ? 'Online' : 'Offline'}
                              </Badge>
                            </td>
                          )}
                          {visibleColumns.has('battery') && (
                            <td className="px-4 py-3">
                              <div className="flex items-center gap-1">
                                <Battery className="w-4 h-4 text-gray-400" />
                                {device.battery_level !== null ? `${Math.round(device.battery_level)}%` : 'N/A'}
                              </div>
                            </td>
                          )}
                          {visibleColumns.has('signal') && (
                            <td className="px-4 py-3">
                              <div className="flex items-center gap-1">
                                <Wifi className="w-4 h-4 text-gray-400" />
                                {device.signal_strength !== null ? `${Math.round(device.signal_strength)}%` : 'N/A'}
                              </div>
                            </td>
                          )}
                          {visibleColumns.has('temperature') && (
                            <td className="px-4 py-3">
                              <div className="flex items-center gap-1">
                                <Thermometer className="w-4 h-4 text-gray-400" />
                                {device.temperature !== null ? `${Math.round(device.temperature)}°C` : 'N/A'}
                              </div>
                            </td>
                          )}
                          {visibleColumns.has('storage') && (
                            <td className="px-4 py-3">
                              <div className="flex items-center gap-1">
                                <HardDrive className="w-4 h-4 text-gray-400" />
                                {device.storage_usage !== null ? `${Math.round(device.storage_usage)}%` : 'N/A'}
                              </div>
                            </td>
                          )}
                          {visibleColumns.has('health') && (
                            <td className="px-4 py-3">
                              <span className={`font-bold ${getHealthScoreColor(device.health_score)}`}>
                                {device.health_score}
                              </span>
                            </td>
                          )}
                          {visibleColumns.has('alerts') && (
                            <td className="px-4 py-3">
                              {device.active_alerts > 0 ? (
                                <Badge variant="destructive">{device.active_alerts}</Badge>
                              ) : (
                                <span className="text-gray-400">-</span>
                              )}
                            </td>
                          )}
                          <td className="px-4 py-3">
                            <div className="flex gap-1">
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => handleIssueCommand(device.device_id, 'refresh_display')}
                                disabled={!!pendingCommands[device.device_id]}
                                title="Refresh Display"
                              >
                                <RefreshCw className={`w-3 h-3 ${pendingCommands[device.device_id] ? 'animate-spin' : ''}`} />
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => handleIssueCommand(device.device_id, 'reboot')}
                                disabled={!!pendingCommands[device.device_id]}
                                title="Reboot"
                              >
                                <Activity className="w-3 h-3" />
                              </Button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          ) : (
            <div className="grid grid-cols-1 gap-4">
              {filteredDevices.map((device) => (
              <Card key={device.device_id} className={`${getStatusBorderColor(device.status_color)} border-2`}>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className={`w-3 h-3 rounded-full ${getStatusColor(device.status_color)}`} title={device.status_reason}></div>
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
                    <div className="flex items-center gap-2">
                      <span>Last seen: {formatLastSeen(device.last_seen)}</span>
                      <span className="text-gray-400">•</span>
                      <span className="text-sm">{device.status_reason}</span>
                    </div>
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
                  
                  {deviceCommands[device.device_id]?.[0] && (
                    <div className="mb-4 p-3 bg-gray-50 rounded-lg">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium text-gray-700">Latest Command</span>
                        <Badge variant={
                          deviceCommands[device.device_id][0].status === 'completed' ? 'default' :
                          deviceCommands[device.device_id][0].status === 'failed' ? 'destructive' :
                          deviceCommands[device.device_id][0].status === 'executing' ? 'secondary' :
                          'outline'
                        }>
                          {deviceCommands[device.device_id][0].status}
                        </Badge>
                      </div>
                      <div className="text-sm text-gray-600">
                        <div className="flex items-center gap-2">
                          <Terminal className="w-3 h-3" />
                          <span className="font-medium">{deviceCommands[device.device_id][0].command_type.replace('_', ' ')}</span>
                        </div>
                        <div className="flex items-center gap-2 mt-1 text-xs text-gray-500">
                          <Clock className="w-3 h-3" />
                          {new Date(deviceCommands[device.device_id][0].issued_at).toLocaleString()}
                        </div>
                        {deviceCommands[device.device_id][0].error_message && (
                          <div className="mt-2 text-xs text-red-600">
                            Error: {deviceCommands[device.device_id][0].error_message}
                          </div>
                        )}
                        
                        {deviceCommands[device.device_id][0].command_type === 'get_diagnostics' && 
                         deviceCommands[device.device_id][0].status === 'completed' &&
                         deviceCommands[device.device_id][0].result?.diagnostics && (
                          <div className="mt-3 pt-3 border-t border-gray-200">
                            <div className="text-xs font-semibold text-gray-700 mb-2">Device Diagnostics</div>
                            <div className="grid grid-cols-2 gap-2 text-xs">
                              <div className="flex items-center gap-1">
                                <Clock className="w-3 h-3 text-blue-500" />
                                <span className="text-gray-600">Uptime:</span>
                                <span className="font-medium">
                                  {Math.floor(deviceCommands[device.device_id][0].result.diagnostics.uptime_hours)}h
                                </span>
                              </div>
                              
                              <div className="flex items-center gap-1">
                                <Battery className={`w-3 h-3 ${
                                  deviceCommands[device.device_id][0].result.diagnostics.power?.battery_level > 50 ? 'text-green-500' :
                                  deviceCommands[device.device_id][0].result.diagnostics.power?.battery_level > 20 ? 'text-yellow-500' :
                                  'text-red-500'
                                }`} />
                                <span className="text-gray-600">Battery:</span>
                                <span className="font-medium">
                                  {Math.round(deviceCommands[device.device_id][0].result.diagnostics.power?.battery_level || 0)}%
                                </span>
                              </div>
                              
                              <div className="flex items-center gap-1">
                                <Wifi className={`w-3 h-3 ${
                                  deviceCommands[device.device_id][0].result.diagnostics.connectivity?.current_connection === 'wifi' ? 'text-green-500' :
                                  deviceCommands[device.device_id][0].result.diagnostics.connectivity?.current_connection === 'lte' ? 'text-blue-500' :
                                  'text-gray-400'
                                }`} />
                                <span className="text-gray-600">Connection:</span>
                                <span className="font-medium capitalize">
                                  {deviceCommands[device.device_id][0].result.diagnostics.connectivity?.current_connection || 'None'}
                                </span>
                              </div>
                              
                              <div className="flex items-center gap-1">
                                <Activity className={`w-3 h-3 ${
                                  deviceCommands[device.device_id][0].result.diagnostics.power?.charging ? 'text-green-500' : 'text-gray-400'
                                }`} />
                                <span className="text-gray-600">Charging:</span>
                                <span className="font-medium">
                                  {deviceCommands[device.device_id][0].result.diagnostics.power?.charging ? 'Yes' : 'No'}
                                </span>
                              </div>
                              
                              <div className="flex items-center gap-1">
                                <HardDrive className={`w-3 h-3 ${
                                  deviceCommands[device.device_id][0].result.diagnostics.display?.display_available ? 'text-green-500' : 'text-red-500'
                                }`} />
                                <span className="text-gray-600">Display:</span>
                                <span className="font-medium">
                                  {deviceCommands[device.device_id][0].result.diagnostics.display?.display_available ? 'OK' : 'Error'}
                                </span>
                              </div>
                              
                              <div className="flex items-center gap-1">
                                <RefreshCw className="w-3 h-3 text-blue-500" />
                                <span className="text-gray-600">Refreshes:</span>
                                <span className="font-medium">
                                  {deviceCommands[device.device_id][0].result.diagnostics.display?.refresh_count || 0}
                                </span>
                              </div>
                            </div>
                            
                            {deviceCommands[device.device_id][0].result.diagnostics.last_sync && (
                              <div className="mt-2 text-xs text-gray-500">
                                Last sync: {new Date(deviceCommands[device.device_id][0].result.diagnostics.last_sync).toLocaleString()}
                              </div>
                            )}
                            
                            {deviceCommands[device.device_id][0].result.diagnostics.sync_errors > 0 && (
                              <div className="mt-2 text-xs text-red-600">
                                ⚠️ {deviceCommands[device.device_id][0].result.diagnostics.sync_errors} sync error(s)
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleIssueCommand(device.device_id, 'refresh_display')}
                      disabled={!!pendingCommands[device.device_id]}
                    >
                      <RefreshCw className={`w-4 h-4 mr-1 ${pendingCommands[device.device_id] ? 'animate-spin' : ''}`} />
                      Refresh Display
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleIssueCommand(device.device_id, 'reboot')}
                      disabled={!!pendingCommands[device.device_id]}
                    >
                      <Activity className="w-4 h-4 mr-1" />
                      Reboot
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleIssueCommand(device.device_id, 'get_diagnostics')}
                      disabled={!!pendingCommands[device.device_id]}
                    >
                      <Terminal className="w-4 h-4 mr-1" />
                      Diagnostics
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
          )}
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

        <TabsContent value="trends" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Fleet Health Trends</CardTitle>
              <CardDescription>
                Predictive insights and historical trends for your device fleet
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-center py-8 text-gray-500">
                <TrendingUp className="w-12 h-12 mx-auto mb-2 text-gray-400" />
                <p>Trends visualization coming soon</p>
                <p className="text-sm mt-2">
                  View battery degradation, temperature patterns, and predictive maintenance alerts
                </p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default DeviceMonitoringDashboard;
