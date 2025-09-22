import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { apiClient, Course, Device, SponsorCampaign } from '../lib/api';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Alert, AlertDescription } from './ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Badge } from './ui/badge';
import { Plus, Building, Monitor, Megaphone, BarChart3, LogOut } from 'lucide-react';

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
      
      const [summaryData, revenueData, tenantData, performanceData] = await Promise.all([
        fetch(`${import.meta.env.VITE_API_URL}/admin/analytics/summary`, { headers }).then(r => r.json()),
        fetch(`${import.meta.env.VITE_API_URL}/admin/analytics/revenue`, { headers }).then(r => r.json()),
        fetch(`${import.meta.env.VITE_API_URL}/admin/analytics/tenants`, { headers }).then(r => r.json()),
        fetch(`${import.meta.env.VITE_API_URL}/admin/analytics/performance`, { headers }).then(r => r.json()),
      ]);
      
      setAnalytics(summaryData);
      setRevenueAnalytics(revenueData);
      setTenantAnalytics(tenantData);
      setPerformanceMetrics(performanceData);
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
          <TabsList>
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

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {devices.map((device) => (
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

          <TabsContent value="analytics" className="space-y-6">
            <div className="space-y-6">
              <h2 className="text-2xl font-bold">Analytics & Reports</h2>
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
        </Tabs>
      </main>
    </div>
  );
};
