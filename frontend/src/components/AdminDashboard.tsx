import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { apiClient, Course, Device, SponsorCampaign } from '../lib/api';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Alert, AlertDescription } from './ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Badge } from './ui/badge';
import { Plus, Building, Monitor, Megaphone, BarChart3, LogOut, Bell, Settings, Shield, Database } from 'lucide-react';

export const AdminDashboard: React.FC = () => {
  const { user, logout } = useAuth();
  const [courses, setCourses] = useState<Course[]>([]);
  const [devices, setDevices] = useState<Device[]>([]);
  const [campaigns, setCampaigns] = useState<SponsorCampaign[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  const [analytics, setAnalytics] = useState<any>({});
  const [revenueAnalytics, setRevenueAnalytics] = useState<any>({});
  const [tenantAnalytics, setTenantAnalytics] = useState<any[]>([]);
  const [performanceMetrics, setPerformanceMetrics] = useState<any>({});
  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  const [customDashboards, setCustomDashboards] = useState<any[]>([]);
  const [deviceHealth, setDeviceHealth] = useState<any>({});
  const [noticeStyles, setNoticeStyles] = useState<any[]>([]);
  const [regions, setRegions] = useState<any[]>([]);
  const [ssoProviders, setSsoProviders] = useState<any[]>([]);

  const [newCourse, setNewCourse] = useState({ name: '', location: '' });
  const [newDevice, setNewDevice] = useState({ name: '', device_id: '', course_id: 0 });
  const [newCampaign, setNewCampaign] = useState({
    sponsor_name: '',
    device_id: 0,
    start_date: '',
    end_date: '',
    rotation_interval: 1,
    rotation_unit: 'days' as const,
    priority: 1,
  });
  const [campaignFile, setCampaignFile] = useState<File | null>(null);
  const [deviceFilter, setDeviceFilter] = useState<number>(0); // 0 = all courses

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [coursesData, devicesData, campaignsData] = await Promise.all([
        apiClient.getCourses(),
        apiClient.getDevices(),
        apiClient.getCampaigns(),
      ]);
      setCourses(coursesData);
      setDevices(devicesData);
      setCampaigns(campaignsData);
      
      await loadAnalytics();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const loadAnalytics = async () => {
    try {
      const token = localStorage.getItem('token');
      if (!token) return;

      const headers = { Authorization: `Bearer ${token}` };
      
      const [summaryData, revenueData, tenantData, performanceData, healthData, stylesData, logsData] = await Promise.all([
        fetch(`${import.meta.env.VITE_API_URL}/admin/analytics/summary`, { headers }).then(r => r.json()),
        fetch(`${import.meta.env.VITE_API_URL}/admin/analytics/revenue`, { headers }).then(r => r.json()),
        fetch(`${import.meta.env.VITE_API_URL}/admin/analytics/tenants`, { headers }).then(r => r.json()),
        fetch(`${import.meta.env.VITE_API_URL}/admin/analytics/performance`, { headers }).then(r => r.json()),
        apiClient.getDeviceHealth().catch(() => ({})),
        apiClient.getNoticeStyles().catch(() => []),
        apiClient.getAuditLogs().catch(() => [])
      ]);
      
      setAnalytics(summaryData);
      setRevenueAnalytics(revenueData);
      setTenantAnalytics(tenantData);
      setPerformanceMetrics(performanceData);
      setDeviceHealth(healthData);
      setNoticeStyles(stylesData);
      setAuditLogs(logsData);
      setCustomDashboards([]);
      setRegions([]);
      setSsoProviders([]);
    } catch (err) {
      console.error('Failed to load analytics:', err);
    }
  };

  const handleCreateCourse = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await apiClient.createCourse(newCourse);
      setNewCourse({ name: '', location: '' });
      loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create course');
    }
  };

  const handleCreateDevice = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await apiClient.createDevice(newDevice);
      setNewDevice({ name: '', device_id: '', course_id: 0 });
      loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create device');
    }
  };

  const handleCreateCampaign = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!campaignFile) {
      setError('Please select a creative file');
      return;
    }

    try {
      const formData = new FormData();
      Object.entries(newCampaign).forEach(([key, value]) => {
        formData.append(key, value.toString());
      });
      formData.append('creative', campaignFile);

      await apiClient.createCampaign(formData);
      setNewCampaign({
        sponsor_name: '',
        device_id: 0,
        start_date: '',
        end_date: '',
        rotation_interval: 1,
        rotation_unit: 'days',
        priority: 1,
      });
      setCampaignFile(null);
      loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create campaign');
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center min-h-screen">Loading...</div>;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <h1 className="text-2xl font-bold text-gray-900">Golf CMS Admin</h1>
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-600">Welcome, {user?.email}</span>
              <Button variant="outline" onClick={logout}>
                <LogOut className="w-4 h-4 mr-2" />
                Logout
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {error && (
          <Alert variant="destructive" className="mb-6">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <Tabs defaultValue="courses" className="space-y-6">
          <TabsList className="grid w-full grid-cols-4 lg:grid-cols-8">
            <TabsTrigger value="courses">
              <Building className="w-4 h-4 mr-2" />
              Courses
            </TabsTrigger>
            <TabsTrigger value="devices">
              <Monitor className="w-4 h-4 mr-2" />
              Devices
            </TabsTrigger>
            <TabsTrigger value="campaigns">
              <Megaphone className="w-4 h-4 mr-2" />
              Campaigns
            </TabsTrigger>
            <TabsTrigger value="analytics">
              <BarChart3 className="w-4 h-4 mr-2" />
              Analytics
            </TabsTrigger>
            <TabsTrigger value="notices">
              <Bell className="w-4 h-4 mr-2" />
              Notices
            </TabsTrigger>
            <TabsTrigger value="device-mgmt">
              <Settings className="w-4 h-4 mr-2" />
              Device Mgmt
            </TabsTrigger>
            <TabsTrigger value="audit-logs">
              <Shield className="w-4 h-4 mr-2" />
              Audit Logs
            </TabsTrigger>
            <TabsTrigger value="dashboards">
              <Database className="w-4 h-4 mr-2" />
              Dashboards
            </TabsTrigger>
          </TabsList>

          <TabsContent value="courses" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Create New Course</CardTitle>
                <CardDescription>Add a new golf course to the system</CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleCreateCourse} className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <Input
                      placeholder="Course Name"
                      value={newCourse.name}
                      onChange={(e) => setNewCourse({ ...newCourse, name: e.target.value })}
                      required
                    />
                    <Input
                      placeholder="Location"
                      value={newCourse.location}
                      onChange={(e) => setNewCourse({ ...newCourse, location: e.target.value })}
                      required
                    />
                  </div>
                  <Button type="submit">
                    <Plus className="w-4 h-4 mr-2" />
                    Create Course
                  </Button>
                </form>
              </CardContent>
            </Card>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {courses.map((course) => (
                <Card key={course.id}>
                  <CardHeader>
                    <CardTitle>{course.name}</CardTitle>
                    <CardDescription>{course.location}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="flex justify-between items-center">
                      <Badge variant="secondary">
                        {devices.filter(d => d.course_id === course.id).length} devices
                      </Badge>
                      <span className="text-sm text-gray-500">
                        ID: {course.id}
                      </span>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </TabsContent>

          <TabsContent value="devices" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Create New Device</CardTitle>
                <CardDescription>Add a new tee box display device</CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleCreateDevice} className="space-y-4">
                  <div className="grid grid-cols-3 gap-4">
                    <Input
                      placeholder="Device Name"
                      value={newDevice.name}
                      onChange={(e) => setNewDevice({ ...newDevice, name: e.target.value })}
                      required
                    />
                    <Input
                      placeholder="Device ID"
                      value={newDevice.device_id}
                      onChange={(e) => setNewDevice({ ...newDevice, device_id: e.target.value })}
                      required
                    />
                    <select
                      className="px-3 py-2 border border-gray-300 rounded-md"
                      value={newDevice.course_id}
                      onChange={(e) => setNewDevice({ ...newDevice, course_id: parseInt(e.target.value) })}
                      required
                    >
                      <option value={0}>Select Course</option>
                      {courses.map((course) => (
                        <option key={course.id} value={course.id}>
                          {course.name}
                        </option>
                      ))}
                    </select>
                  </div>
                  <Button type="submit">
                    <Plus className="w-4 h-4 mr-2" />
                    Create Device
                  </Button>
                </form>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Filter Devices</CardTitle>
                <CardDescription>Filter devices by golf course</CardDescription>
              </CardHeader>
              <CardContent>
                <select
                  className="px-3 py-2 border border-gray-300 rounded-md w-full max-w-xs"
                  value={deviceFilter}
                  onChange={(e) => setDeviceFilter(parseInt(e.target.value))}
                >
                  <option value={0}>All Courses</option>
                  {courses.map((course) => (
                    <option key={course.id} value={course.id}>
                      {course.name}
                    </option>
                  ))}
                </select>
              </CardContent>
            </Card>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {devices
                .filter(device => deviceFilter === 0 || device.course_id === deviceFilter)
                .map((device) => (
                <Card key={device.id}>
                  <CardHeader>
                    <CardTitle>{device.name}</CardTitle>
                    <CardDescription>
                      {courses.find(c => c.id === device.course_id)?.name}
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-600">Device ID:</span>
                        <span className="text-sm font-mono">{device.device_id}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-600">Status:</span>
                        <Badge variant={device.is_online ? "default" : "secondary"}>
                          {device.is_online ? "Online" : "Offline"}
                        </Badge>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-600">Campaigns:</span>
                        <span className="text-sm">
                          {campaigns.filter(c => c.device_id === device.id).length}/5
                        </span>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </TabsContent>

          <TabsContent value="campaigns" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Create New Campaign</CardTitle>
                <CardDescription>Add a sponsor campaign to a device (max 5 per device)</CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleCreateCampaign} className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <Input
                      placeholder="Sponsor Name"
                      value={newCampaign.sponsor_name}
                      onChange={(e) => setNewCampaign({ ...newCampaign, sponsor_name: e.target.value })}
                      required
                    />
                    <select
                      className="px-3 py-2 border border-gray-300 rounded-md"
                      value={newCampaign.device_id}
                      onChange={(e) => setNewCampaign({ ...newCampaign, device_id: parseInt(e.target.value) })}
                      required
                    >
                      <option value={0}>Select Device</option>
                      {devices.map((device) => (
                        <option key={device.id} value={device.id}>
                          {device.name} ({courses.find(c => c.id === device.course_id)?.name})
                        </option>
                      ))}
                    </select>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4">
                    <Input
                      type="datetime-local"
                      value={newCampaign.start_date}
                      onChange={(e) => setNewCampaign({ ...newCampaign, start_date: e.target.value })}
                      required
                    />
                    <Input
                      type="datetime-local"
                      value={newCampaign.end_date}
                      onChange={(e) => setNewCampaign({ ...newCampaign, end_date: e.target.value })}
                      required
                    />
                  </div>
                  
                  <div className="grid grid-cols-3 gap-4">
                    <Input
                      type="number"
                      placeholder="Rotation Interval"
                      min="1"
                      value={newCampaign.rotation_interval}
                      onChange={(e) => setNewCampaign({ ...newCampaign, rotation_interval: parseInt(e.target.value) })}
                      required
                    />
                    <select
                      className="px-3 py-2 border border-gray-300 rounded-md"
                      value={newCampaign.rotation_unit}
                      onChange={(e) => setNewCampaign({ ...newCampaign, rotation_unit: e.target.value as any })}
                    >
                      <option value="hours">Hours</option>
                      <option value="days">Days</option>
                      <option value="weeks">Weeks</option>
                      <option value="months">Months</option>
                    </select>
                    <Input
                      type="number"
                      placeholder="Priority"
                      min="1"
                      value={newCampaign.priority}
                      onChange={(e) => setNewCampaign({ ...newCampaign, priority: parseInt(e.target.value) })}
                      required
                    />
                  </div>
                  
                  <Input
                    type="file"
                    accept="image/*"
                    onChange={(e) => setCampaignFile(e.target.files?.[0] || null)}
                    required
                  />
                  
                  <Button type="submit">
                    <Plus className="w-4 h-4 mr-2" />
                    Create Campaign
                  </Button>
                </form>
              </CardContent>
            </Card>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {campaigns.map((campaign) => (
                <Card key={campaign.id}>
                  <CardHeader>
                    <CardTitle>{campaign.sponsor_name}</CardTitle>
                    <CardDescription>
                      {devices.find(d => d.id === campaign.device_id)?.name}
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-600">Rotation:</span>
                        <span className="text-sm">
                          {campaign.rotation_interval} {campaign.rotation_unit}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-600">Priority:</span>
                        <Badge variant="outline">{campaign.priority}</Badge>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-600">Status:</span>
                        <Badge variant={campaign.is_active ? "default" : "secondary"}>
                          {campaign.is_active ? "Active" : "Inactive"}
                        </Badge>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </TabsContent>

          <TabsContent value="notices" className="space-y-6">
            <div className="space-y-6">
              <h2 className="text-2xl font-bold">Advanced Notice Management</h2>
              
              <div className="bg-white p-6 rounded-lg shadow">
                <h3 className="text-xl font-semibold mb-4">Create Advanced Notice</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-2">Title</label>
                    <Input placeholder="Notice title" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2">Device</label>
                    <select className="w-full p-2 border rounded">
                      <option value="">Select device</option>
                      {devices.map(device => (
                        <option key={device.id} value={device.id}>{device.name}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2">Duration (minutes)</label>
                    <Input type="number" placeholder="60" min="1" max="1440" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2">Font Family</label>
                    <select className="w-full p-2 border rounded">
                      {noticeStyles.length > 0 ? (
                        noticeStyles.map((style) => (
                          <option key={style.id} value={style.font_family}>
                            {style.name}
                          </option>
                        ))
                      ) : (
                        <>
                          <option value="arial">Arial</option>
                          <option value="helvetica">Helvetica</option>
                          <option value="times">Times</option>
                          <option value="courier">Courier</option>
                          <option value="impact">Impact</option>
                          <option value="comic_sans">Comic Sans</option>
                        </>
                      )}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2">Font Size</label>
                    <Input type="number" placeholder="24" min="12" max="72" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2">Text Color</label>
                    <Input type="color" defaultValue="#000000" />
                  </div>
                </div>
                <div className="mt-4">
                  <label className="block text-sm font-medium mb-2">Content</label>
                  <textarea 
                    className="w-full p-2 border rounded h-24" 
                    placeholder="Notice content..."
                  />
                </div>
                <Button className="mt-4">Create Advanced Notice</Button>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="device-mgmt" className="space-y-6">
            <div className="space-y-6">
              <h2 className="text-2xl font-bold">Device Management</h2>
              
              <div className="bg-white p-6 rounded-lg shadow">
                <h3 className="text-xl font-semibold mb-4">Device Health Overview</h3>
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  <div className="text-center p-4 bg-green-50 rounded">
                    <p className="text-sm text-gray-600">Healthy Devices</p>
                    <p className="text-2xl font-bold text-green-600">
                      {devices.filter(d => d.is_online).length}
                    </p>
                  </div>
                  <div className="text-center p-4 bg-yellow-50 rounded">
                    <p className="text-sm text-gray-600">Warning Status</p>
                    <p className="text-2xl font-bold text-yellow-600">0</p>
                  </div>
                  <div className="text-center p-4 bg-red-50 rounded">
                    <p className="text-sm text-gray-600">Critical Issues</p>
                    <p className="text-2xl font-bold text-red-600">
                      {devices.filter(d => !d.is_online).length}
                    </p>
                  </div>
                  <div className="text-center p-4 bg-blue-50 rounded">
                    <p className="text-sm text-gray-600">Total Devices</p>
                    <p className="text-2xl font-bold text-blue-600">{devices.length}</p>
                  </div>
                </div>
              </div>

              <div className="bg-white p-6 rounded-lg shadow">
                <h3 className="text-xl font-semibold mb-4">Device Diagnostics</h3>
                <div className="overflow-x-auto">
                  <table className="min-w-full table-auto">
                    <thead>
                      <tr className="bg-gray-50">
                        <th className="px-4 py-2 text-left">Device</th>
                        <th className="px-4 py-2 text-left">Status</th>
                        <th className="px-4 py-2 text-left">Last Sync</th>
                        <th className="px-4 py-2 text-left">Firmware</th>
                        <th className="px-4 py-2 text-left">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {devices.map(device => (
                        <tr key={device.id} className="border-t">
                          <td className="px-4 py-2">{device.name}</td>
                          <td className="px-4 py-2">
                            <Badge variant={device.is_online ? "default" : "destructive"}>
                              {device.is_online ? "Online" : "Offline"}
                            </Badge>
                          </td>
                          <td className="px-4 py-2">
                            {device.last_sync ? new Date(device.last_sync).toLocaleString() : 'Never'}
                          </td>
                          <td className="px-4 py-2">v1.0.0</td>
                          <td className="px-4 py-2">
                            <div className="flex gap-2">
                              <Button size="sm" variant="outline">Diagnostics</Button>
                              <Button size="sm" variant="outline">Update</Button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="analytics" className="space-y-6">
            <div className="space-y-6">
              <h2 className="text-2xl font-bold">Analytics & Reports</h2>
              
              {/* Test Alerts Section (important-comment) */}
              <div className="bg-white p-6 rounded-lg shadow">
                <h3 className="text-xl font-semibold mb-4">System Alerts</h3>
                <div className="flex gap-4">
                  <Button 
                    onClick={async () => {
                      try {
                        await apiClient.testAlert('device_offline');
                        setError('');
                        alert('Test alert sent successfully!');
                      } catch (err) {
                        setError('Failed to send test alert');
                      }
                    }}
                    variant="outline"
                  >
                    Test Device Alert
                  </Button>
                  <Button 
                    onClick={async () => {
                      try {
                        await apiClient.testAlert('system_health');
                        setError('');
                        alert('System health alert sent!');
                      } catch (err) {
                        setError('Failed to send system alert');
                      }
                    }}
                    variant="outline"
                  >
                    Test System Alert
                  </Button>
                </div>
              </div>

              <div className="bg-white p-6 rounded-lg shadow">
                <h3 className="text-xl font-semibold mb-4">Revenue Analytics</h3>
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  <div className="text-center">
                    <p className="text-sm text-gray-600">Monthly Recurring Revenue</p>
                    <p className="text-2xl font-bold text-green-600">${revenueAnalytics.total_mrr || 0}</p>
                  </div>
                  <div className="text-center">
                    <p className="text-sm text-gray-600">Annual Recurring Revenue</p>
                    <p className="text-2xl font-bold text-green-600">${revenueAnalytics.total_arr || 0}</p>
                  </div>
                  <div className="text-center">
                    <p className="text-sm text-gray-600">Total Subscribers</p>
                    <p className="text-2xl font-bold text-blue-600">{revenueAnalytics.total_subscribers || 0}</p>
                  </div>
                  <div className="text-center">
                    <p className="text-sm text-gray-600">Active Courses</p>
                    <p className="text-2xl font-bold text-purple-600">{revenueAnalytics.active_courses || 0}</p>
                  </div>
                </div>
              </div>

              <div className="bg-white p-6 rounded-lg shadow">
                <h3 className="text-xl font-semibold mb-4">System Performance</h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="text-center">
                    <p className="text-sm text-gray-600">Device Uptime</p>
                    <p className="text-2xl font-bold text-green-600">{performanceMetrics.device_uptime_percentage?.toFixed(1) || 0}%</p>
                  </div>
                  <div className="text-center">
                    <p className="text-sm text-gray-600">Active Campaigns</p>
                    <p className="text-2xl font-bold text-blue-600">{performanceMetrics.active_campaigns || 0}</p>
                  </div>
                  <div className="text-center">
                    <p className="text-sm text-gray-600">System Health Score</p>
                    <p className="text-2xl font-bold text-purple-600">{performanceMetrics.system_health_score || 0}</p>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="bg-white p-6 rounded-lg shadow">
                  <h3 className="text-lg font-semibold mb-2">Total Devices</h3>
                  <p className="text-3xl font-bold text-blue-600">{analytics.total_devices || 0}</p>
                </div>
                <div className="bg-white p-6 rounded-lg shadow">
                  <h3 className="text-lg font-semibold mb-2">Online Devices</h3>
                  <p className="text-3xl font-bold text-green-600">{analytics.online_devices || 0}</p>
                </div>
                <div className="bg-white p-6 rounded-lg shadow">
                  <h3 className="text-lg font-semibold mb-2">Total Impressions</h3>
                  <p className="text-3xl font-bold text-purple-600">{analytics.total_impressions || 0}</p>
                </div>
              </div>

              <div className="bg-white p-6 rounded-lg shadow">
                <h3 className="text-xl font-semibold mb-4">Tenant Usage Analytics</h3>
                <div className="overflow-x-auto">
                  <table className="min-w-full table-auto">
                    <thead>
                      <tr className="bg-gray-50">
                        <th className="px-4 py-2 text-left">Course Name</th>
                        <th className="px-4 py-2 text-left">Plan</th>
                        <th className="px-4 py-2 text-left">Devices</th>
                        <th className="px-4 py-2 text-left">Online</th>
                        <th className="px-4 py-2 text-left">Uptime %</th>
                        <th className="px-4 py-2 text-left">Last Activity</th>
                      </tr>
                    </thead>
                    <tbody>
                      {tenantAnalytics.map((tenant) => (
                        <tr key={tenant.course_id} className="border-t">
                          <td className="px-4 py-2">{tenant.course_name}</td>
                          <td className="px-4 py-2">
                            <span className={`px-2 py-1 rounded text-xs ${
                              tenant.plan_type === 'basic' ? 'bg-blue-100 text-blue-800' :
                              tenant.plan_type === 'premium' ? 'bg-purple-100 text-purple-800' :
                              tenant.plan_type === 'enterprise' ? 'bg-green-100 text-green-800' :
                              'bg-gray-100 text-gray-800'
                            }`}>
                              {tenant.plan_type}
                            </span>
                          </td>
                          <td className="px-4 py-2">{tenant.device_count}</td>
                          <td className="px-4 py-2">{tenant.online_devices}</td>
                          <td className="px-4 py-2">{tenant.avg_uptime_percentage?.toFixed(1) || 0}%</td>
                          <td className="px-4 py-2">
                            {tenant.last_activity ? new Date(tenant.last_activity).toLocaleDateString() : 'Never'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="audit-logs">
            <div className="space-y-6">
              <div className="bg-white p-6 rounded-lg shadow">
                <h3 className="text-xl font-semibold mb-4">Audit Logs</h3>
                <div className="overflow-x-auto">
                  <table className="min-w-full table-auto">
                    <thead>
                      <tr className="bg-gray-50">
                        <th className="px-4 py-2 text-left">Timestamp</th>
                        <th className="px-4 py-2 text-left">User</th>
                        <th className="px-4 py-2 text-left">Action</th>
                        <th className="px-4 py-2 text-left">Resource</th>
                        <th className="px-4 py-2 text-left">IP Address</th>
                      </tr>
                    </thead>
                    <tbody>
                      {auditLogs.map((log: any) => (
                        <tr key={log.id} className="border-t">
                          <td className="px-4 py-2">{new Date(log.timestamp).toLocaleString()}</td>
                          <td className="px-4 py-2">{log.user_email}</td>
                          <td className="px-4 py-2">
                            <span className={`px-2 py-1 rounded text-xs ${
                              log.action === 'create' ? 'bg-green-100 text-green-800' :
                              log.action === 'update' ? 'bg-blue-100 text-blue-800' :
                              log.action === 'delete' ? 'bg-red-100 text-red-800' :
                              'bg-gray-100 text-gray-800'
                            }`}>
                              {log.action}
                            </span>
                          </td>
                          <td className="px-4 py-2">{log.resource_type}</td>
                          <td className="px-4 py-2">{log.ip_address}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="notices">
            <div className="space-y-6">
              <div className="bg-white p-6 rounded-lg shadow">
                <h3 className="text-xl font-semibold mb-4">Advanced Notice Management</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <h4 className="text-lg font-medium mb-3">Create Advanced Notice</h4>
                    <form className="space-y-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Title</label>
                        <input
                          type="text"
                          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                          placeholder="Notice title"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Content</label>
                        <textarea
                          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                          rows={3}
                          placeholder="Notice content"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Font Family</label>
                        <select className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500">
                          <option value="Arial">Arial</option>
                          <option value="Helvetica">Helvetica</option>
                          <option value="Times">Times New Roman</option>
                          <option value="Courier">Courier New</option>
                          <option value="Impact">Impact</option>
                          <option value="Comic Sans MS">Comic Sans</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Duration (minutes)</label>
                        <input
                          type="number"
                          min="1"
                          max="1440"
                          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                          placeholder="60"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Device</label>
                        <select className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500">
                          <option value="">Select device</option>
                          {devices.map((device) => (
                            <option key={device.id} value={device.id}>
                              {device.name} - {device.device_id}
                            </option>
                          ))}
                        </select>
                      </div>
                      <Button type="submit" className="w-full">
                        Create Advanced Notice
                      </Button>
                    </form>
                  </div>
                  <div>
                    <h4 className="text-lg font-medium mb-3">Seasonal Campaigns</h4>
                    <form className="space-y-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Campaign Name</label>
                        <input
                          type="text"
                          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                          placeholder="Summer Special"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Season Start</label>
                        <input
                          type="date"
                          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Season End</label>
                        <input
                          type="date"
                          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Repeat Yearly</label>
                        <input
                          type="checkbox"
                          className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                        />
                      </div>
                      <Button type="submit" className="w-full">
                        Create Seasonal Campaign
                      </Button>
                    </form>
                  </div>
                </div>
              </div>

              <div className="bg-white p-6 rounded-lg shadow">
                <h3 className="text-xl font-semibold mb-4">A/B Testing Campaigns</h3>
                <form className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Test Name</label>
                      <input
                        type="text"
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="Header Color Test"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Duration (days)</label>
                      <input
                        type="number"
                        min="1"
                        max="365"
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="14"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Traffic Split (%)</label>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-xs text-gray-500">Variant A</label>
                        <input
                          type="number"
                          min="0"
                          max="100"
                          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                          placeholder="50"
                        />
                      </div>
                      <div>
                        <label className="block text-xs text-gray-500">Variant B</label>
                        <input
                          type="number"
                          min="0"
                          max="100"
                          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                          placeholder="50"
                        />
                      </div>
                    </div>
                  </div>
                  <Button type="submit" className="w-full">
                    Create A/B Test Campaign
                  </Button>
                </form>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="device-mgmt">
            <div className="space-y-6">
              <div className="bg-white p-6 rounded-lg shadow">
                <h3 className="text-xl font-semibold mb-4">Device Management & Diagnostics</h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <div className="text-center">
                    <p className="text-sm text-gray-600">Total Devices</p>
                    <p className="text-2xl font-bold text-blue-600">{analytics.total_devices || 0}</p>
                  </div>
                  <div className="text-center">
                    <p className="text-sm text-gray-600">Online Devices</p>
                    <p className="text-2xl font-bold text-green-600">{analytics.online_devices || 0}</p>
                  </div>
                  <div className="text-center">
                    <p className="text-sm text-gray-600">Health Score</p>
                    <p className="text-2xl font-bold text-purple-600">{performanceMetrics.system_health_score || 0}</p>
                  </div>
                </div>
              </div>

              <div className="bg-white p-6 rounded-lg shadow">
                <h3 className="text-xl font-semibold mb-4">Device Health Monitoring</h3>
                <div className="overflow-x-auto">
                  <table className="min-w-full table-auto">
                    <thead>
                      <tr className="bg-gray-50">
                        <th className="px-4 py-2 text-left">Device</th>
                        <th className="px-4 py-2 text-left">Status</th>
                        <th className="px-4 py-2 text-left">Battery</th>
                        <th className="px-4 py-2 text-left">Signal</th>
                        <th className="px-4 py-2 text-left">Temperature</th>
                        <th className="px-4 py-2 text-left">Last Sync</th>
                        <th className="px-4 py-2 text-left">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {devices.map((device) => (
                        <tr key={device.id} className="border-t">
                          <td className="px-4 py-2">{device.name}</td>
                          <td className="px-4 py-2">
                            <span className={`px-2 py-1 rounded text-xs ${
                              device.is_online ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                            }`}>
                              {device.is_online ? 'Online' : 'Offline'}
                            </span>
                          </td>
                          <td className="px-4 py-2">{deviceHealth[device.id]?.battery || '85%'}</td>
                          <td className="px-4 py-2">{deviceHealth[device.id]?.signal || '-65 dBm'}</td>
                          <td className="px-4 py-2">{deviceHealth[device.id]?.temperature || '22°C'}</td>
                          <td className="px-4 py-2">{deviceHealth[device.id]?.last_sync || '2 min ago'}</td>
                          <td className="px-4 py-2">
                            <Button size="sm" variant="outline">
                              Update Firmware
                            </Button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="bg-white p-6 rounded-lg shadow">
                <h3 className="text-xl font-semibold mb-4">Remote Device Updates</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <h4 className="text-lg font-medium mb-3">Firmware Update</h4>
                    <form className="space-y-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Select Devices</label>
                        <select multiple className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500">
                          {devices.map((device) => (
                            <option key={device.id} value={device.id}>
                              {device.name} - {device.device_id}
                            </option>
                          ))}
                        </select>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Firmware Version</label>
                        <select className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500">
                          <option value="v2.1.0">v2.1.0 (Latest)</option>
                          <option value="v2.0.5">v2.0.5</option>
                          <option value="v2.0.0">v2.0.0</option>
                        </select>
                      </div>
                      <Button type="submit" className="w-full">
                        Start Firmware Update
                      </Button>
                    </form>
                  </div>
                  <div>
                    <h4 className="text-lg font-medium mb-3">Update Status</h4>
                    <div className="space-y-3">
                      <div className="p-3 bg-blue-50 rounded-md">
                        <div className="flex justify-between items-center">
                          <span className="text-sm font-medium">Device TEE-001</span>
                          <span className="text-sm text-blue-600">In Progress</span>
                        </div>
                        <div className="mt-2 bg-blue-200 rounded-full h-2">
                          <div className="bg-blue-600 h-2 rounded-full" style={{width: '75%'}}></div>
                        </div>
                      </div>
                      <div className="p-3 bg-green-50 rounded-md">
                        <div className="flex justify-between items-center">
                          <span className="text-sm font-medium">Device TEE-002</span>
                          <span className="text-sm text-green-600">Completed</span>
                        </div>
                        <div className="mt-2 bg-green-200 rounded-full h-2">
                          <div className="bg-green-600 h-2 rounded-full" style={{width: '100%'}}></div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="audit-logs">
            <div className="space-y-6">
              <div className="bg-white p-6 rounded-lg shadow">
                <h3 className="text-xl font-semibold mb-4">Audit Logs</h3>
                <div className="overflow-x-auto">
                  <table className="min-w-full table-auto">
                    <thead>
                      <tr className="bg-gray-50">
                        <th className="px-4 py-2 text-left">Timestamp</th>
                        <th className="px-4 py-2 text-left">User</th>
                        <th className="px-4 py-2 text-left">Action</th>
                        <th className="px-4 py-2 text-left">Resource</th>
                        <th className="px-4 py-2 text-left">Details</th>
                        <th className="px-4 py-2 text-left">IP Address</th>
                      </tr>
                    </thead>
                    <tbody>
                      {auditLogs.map((log, index) => (
                        <tr key={index} className="border-t">
                          <td className="px-4 py-2">{new Date(log.timestamp).toLocaleString()}</td>
                          <td className="px-4 py-2">{log.user_email || 'System'}</td>
                          <td className="px-4 py-2">
                            <span className={`px-2 py-1 rounded text-xs ${
                              log.action === 'CREATE' ? 'bg-green-100 text-green-800' :
                              log.action === 'UPDATE' ? 'bg-blue-100 text-blue-800' :
                              log.action === 'DELETE' ? 'bg-red-100 text-red-800' :
                              'bg-gray-100 text-gray-800'
                            }`}>
                              {log.action}
                            </span>
                          </td>
                          <td className="px-4 py-2">{log.resource_type}</td>
                          <td className="px-4 py-2">{log.details ? JSON.stringify(log.details).substring(0, 50) + '...' : '-'}</td>
                          <td className="px-4 py-2">{log.ip_address || '-'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="dashboards">
            <div className="space-y-6">
              <div className="bg-white p-6 rounded-lg shadow">
                <h3 className="text-xl font-semibold mb-4">Custom Dashboards</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
                    <Database className="w-12 h-12 mx-auto text-gray-400 mb-4" />
                    <h4 className="text-lg font-medium text-gray-900 mb-2">Create New Dashboard</h4>
                    <p className="text-gray-600 mb-4">Build custom analytics views with widgets</p>
                    <Button>
                      <Plus className="w-4 h-4 mr-2" />
                      Create Dashboard
                    </Button>
                  </div>
                  {customDashboards.map((dashboard) => (
                    <div key={dashboard.id} className="bg-white border rounded-lg p-6">
                      <h4 className="text-lg font-medium mb-2">{dashboard.name}</h4>
                      <p className="text-gray-600 mb-4">
                        {dashboard.is_shared ? 'Shared Dashboard' : 'Private Dashboard'}
                      </p>
                      <div className="flex space-x-2">
                        <Button size="sm" variant="outline">Edit</Button>
                        <Button size="sm" variant="outline">View</Button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="bg-white p-6 rounded-lg shadow">
                <h3 className="text-xl font-semibold mb-4">Dashboard Templates</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  <div className="border rounded-lg p-4">
                    <h4 className="font-medium mb-2">Revenue Overview</h4>
                    <p className="text-sm text-gray-600 mb-4">Track subscription revenue and growth metrics</p>
                    <Button size="sm" variant="outline">Use Template</Button>
                  </div>
                  <div className="border rounded-lg p-4">
                    <h4 className="font-medium mb-2">Device Performance</h4>
                    <p className="text-sm text-gray-600 mb-4">Monitor device health and uptime statistics</p>
                    <Button size="sm" variant="outline">Use Template</Button>
                  </div>
                  <div className="border rounded-lg p-4">
                    <h4 className="font-medium mb-2">Campaign Analytics</h4>
                    <p className="text-sm text-gray-600 mb-4">Analyze campaign performance and engagement</p>
                    <Button size="sm" variant="outline">Use Template</Button>
                  </div>
                </div>
              </div>

              <div className="bg-white p-6 rounded-lg shadow">
                <h3 className="text-xl font-semibold mb-4">Enterprise Configuration</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <h4 className="text-lg font-medium mb-3">Regions ({regions.length})</h4>
                    <div className="space-y-2">
                      {regions.map((region) => (
                        <div key={region.id} className="flex justify-between items-center p-2 border rounded">
                          <span>{region.name}</span>
                          <span className="text-sm text-gray-500">{region.code}</span>
                        </div>
                      ))}
                      {regions.length === 0 && (
                        <p className="text-gray-500 text-sm">No regions configured</p>
                      )}
                    </div>
                  </div>
                  <div>
                    <h4 className="text-lg font-medium mb-3">SSO Providers ({ssoProviders.length})</h4>
                    <div className="space-y-2">
                      {ssoProviders.map((provider) => (
                        <div key={provider.id} className="flex justify-between items-center p-2 border rounded">
                          <span>{provider.name}</span>
                          <span className={`text-xs px-2 py-1 rounded ${
                            provider.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                          }`}>
                            {provider.is_active ? 'Active' : 'Inactive'}
                          </span>
                        </div>
                      ))}
                      {ssoProviders.length === 0 && (
                        <p className="text-gray-500 text-sm">No SSO providers configured</p>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
};

export default AdminDashboard;
