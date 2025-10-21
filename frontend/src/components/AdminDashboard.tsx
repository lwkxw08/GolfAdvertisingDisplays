import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Badge } from './ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Plus, Building, Monitor, Megaphone, BarChart3, LogOut, Bell, Settings, Shield, Trash2 } from 'lucide-react';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from './ui/dialog';
import { ImagePreviewDialog } from './ImagePreviewDialog';
import { PiImagerConfigDialog } from './PiImagerConfigDialog';
import { apiClient, Course, Device, SponsorCampaign } from '../lib/api';

const AdminDashboard = () => {
  const [courses, setCourses] = useState<Course[]>([]);
  const [devices, setDevices] = useState<Device[]>([]);
  const [campaigns, setCampaigns] = useState<SponsorCampaign[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  const [newCourse, setNewCourse] = useState({ name: '', location: '' });
  const [newDevice, setNewDevice] = useState({ 
    name: '', 
    device_id: '', 
    course_id: 0, 
    location: '' 
  });
  const [newCampaign, setNewCampaign] = useState({
    sponsor_name: '',
    device_id: '',
    start_date: '',
    end_date: '',
    creative_file: null as File | null
  });
  const [previewDialogOpen, setPreviewDialogOpen] = useState(false);
  const [previewData, setPreviewData] = useState<any>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [campaignLoading, setCampaignLoading] = useState(false);
  const [pendingCampaignData, setPendingCampaignData] = useState<any>(null);

  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<{type: 'course' | 'device', id: number, name: string} | null>(null);
  const [deleteLoading, setDeleteLoading] = useState(false);

  const [piConfigDialogOpen, setPiConfigDialogOpen] = useState(false);
  const [createdDevice, setCreatedDevice] = useState<Device | null>(null);

  const auditLogs = [
    { action: 'Course Created', user: 'admin@golfcms.com', timestamp: '2024-01-15 10:30:00' },
    { action: 'Device Added', user: 'admin@golfcms.com', timestamp: '2024-01-15 09:15:00' },
    { action: 'Campaign Updated', user: 'staff@pinevalley.com', timestamp: '2024-01-14 16:45:00' }
  ];

  const loadData = async () => {
    try {
      setLoading(true);
      const [coursesData, devicesData, campaignsData] = await Promise.all([
        apiClient.getCourses(),
        apiClient.getDevices(),
        apiClient.getCampaigns()
      ]);
      setCourses(coursesData);
      setDevices(devicesData);
      setCampaigns(campaignsData);
      setError('');
    } catch (err) {
      setError('Failed to load data');
    } finally {
      setLoading(false);
    }
  };


  const handleCreateCourse = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await apiClient.createCourse(newCourse);
      setNewCourse({ name: '', location: '' });
      loadData();
    } catch (err) {
      setError('Failed to create course');
    }
  };

  const handleCreateDevice = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      console.log('Creating device with data:', newDevice);
      const createdDeviceData = await apiClient.createDevice(newDevice);
      console.log('Device created successfully:', createdDeviceData);
      setCreatedDevice(createdDeviceData);
      console.log('Set createdDevice state - useEffect will open dialog');
      setNewDevice({ name: '', device_id: '', course_id: 0, location: '' });
      loadData();
    } catch (err) {
      console.error('Error creating device:', err);
      setError('Failed to create device');
    }
  };

  const handleCreateCampaign = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!newCampaign.creative_file) {
      setError('Please select an image file');
      return;
    }
    
    try {
      setPreviewLoading(true);
      const previewResult = await apiClient.previewImageForEink(newCampaign.creative_file);
      
      setPreviewData(previewResult);
      setPendingCampaignData({
        sponsor_name: newCampaign.sponsor_name,
        device_id: newCampaign.device_id,
        start_date: newCampaign.start_date,
        end_date: newCampaign.end_date,
        creative_file: newCampaign.creative_file
      });
      setPreviewDialogOpen(true);
      setError('');
      
    } catch (err) {
      setError('Failed to generate preview. Please check your image format.');
    } finally {
      setPreviewLoading(false);
    }
  };

  const handlePreviewApprove = async () => {
    if (!pendingCampaignData) return;
    
    try {
      setCampaignLoading(true);
      const formData = new FormData();
      formData.append('sponsor_name', pendingCampaignData.sponsor_name);
      formData.append('device_id', pendingCampaignData.device_id);
      formData.append('start_date', pendingCampaignData.start_date);
      formData.append('end_date', pendingCampaignData.end_date);
      formData.append('creative_file', pendingCampaignData.creative_file);
      
      await apiClient.createCampaign(formData);
      
      setNewCampaign({
        sponsor_name: '',
        device_id: '',
        start_date: '',
        end_date: '',
        creative_file: null
      });
      setPreviewDialogOpen(false);
      setPendingCampaignData(null);
      setPreviewData(null);
      loadData();
      
    } catch (err) {
      setError('Failed to create campaign');
    } finally {
      setCampaignLoading(false);
    }
  };

  const handlePreviewReject = () => {
    setPreviewDialogOpen(false);
    setPendingCampaignData(null);
    setPreviewData(null);
  };

  const handleDeleteClick = (type: 'course' | 'device', id: number, name: string) => {
    setDeleteTarget({ type, id, name });
    setDeleteDialogOpen(true);
  };

  const handleDeleteConfirm = async () => {
    if (!deleteTarget) return;
    
    setDeleteLoading(true);
    try {
      if (deleteTarget.type === 'course') {
        await apiClient.deleteCourse(deleteTarget.id);
      } else {
        await apiClient.deleteDevice(deleteTarget.id);
      }
      
      setDeleteDialogOpen(false);
      setDeleteTarget(null);
      loadData();
      setError('');
    } catch (err) {
      setError(err instanceof Error ? err.message : `Failed to delete ${deleteTarget.type}`);
    } finally {
      setDeleteLoading(false);
    }
  };

  const handleDeleteCancel = () => {
    setDeleteDialogOpen(false);
    setDeleteTarget(null);
  };

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    if (createdDevice) {
      console.log('createdDevice changed, opening dialog:', createdDevice);
      setPiConfigDialogOpen(true);
    }
  }, [createdDevice]);

  const handleLogout = () => {
    localStorage.removeItem('token');
    window.location.href = '/';
  };

  if (loading) {
    return <div className="flex items-center justify-center min-h-screen">Loading...</div>;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <Shield className="h-8 w-8 text-blue-600 mr-3" />
              <h1 className="text-xl font-semibold text-gray-900">Golf CMS Admin</h1>
            </div>
            <div className="flex items-center space-x-4">
              <Button variant="outline" size="sm">
                <Bell className="h-4 w-4 mr-2" />
                Notifications
              </Button>
              <Button variant="outline" size="sm">
                <Settings className="h-4 w-4 mr-2" />
                Settings
              </Button>
              <Button variant="outline" size="sm" onClick={handleLogout}>
                <LogOut className="h-4 w-4 mr-2" />
                Logout
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-md">
            <p className="text-red-600">{error}</p>
          </div>
        )}

        <Tabs defaultValue="overview" className="space-y-6">
          <TabsList className="grid w-full grid-cols-8">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="courses">Courses</TabsTrigger>
            <TabsTrigger value="devices">Devices</TabsTrigger>
            <TabsTrigger value="campaigns">Campaigns</TabsTrigger>
            <TabsTrigger value="notices">Notices</TabsTrigger>
            <TabsTrigger value="analytics">Analytics</TabsTrigger>
            <TabsTrigger value="audit-logs">Audit Logs</TabsTrigger>
            <TabsTrigger value="settings">Settings</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Total Courses</CardTitle>
                  <Building className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{courses.length}</div>
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Total Devices</CardTitle>
                  <Monitor className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{devices.length}</div>
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Active Campaigns</CardTitle>
                  <Megaphone className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{campaigns.length}</div>
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">System Health</CardTitle>
                  <BarChart3 className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold text-green-600">Good</div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

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
                    <div className="space-y-3">
                      <div className="flex justify-between items-center">
                        <Badge variant="secondary">
                          {devices.filter(d => d.course_id === course.id).length} devices
                        </Badge>
                        <span className="text-sm text-gray-500">
                          ID: {course.id}
                        </span>
                      </div>
                      <div className="flex justify-end">
                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={() => handleDeleteClick('course', course.id, course.name)}
                        >
                          <Trash2 className="w-4 h-4 mr-2" />
                          Delete
                        </Button>
                      </div>
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
                    <Input
                      placeholder="Location (e.g., Tee Box 1)"
                      value={newDevice.location}
                      onChange={(e) => setNewDevice({ ...newDevice, location: e.target.value })}
                      required
                    />
                    <select
                      className="px-3 py-2 border border-gray-300 rounded-md"
                      value={newDevice.course_id}
                      onChange={(e) => setNewDevice({ ...newDevice, course_id: parseInt(e.target.value) })}
                      required
                    >
                      <option value="0">Select Course</option>
                      {courses.map((course) => (
                        <option key={course.id} value={course.id}>
                          {course.name}
                        </option>
                      ))}
                    </select>
                  </div>
                  <Input
                    placeholder="Location (e.g., Tee Box 1)"
                    value={newDevice.location}
                    onChange={(e) => setNewDevice({ ...newDevice, location: e.target.value })}
                    required
                  />
                  <Button type="submit">
                    <Plus className="w-4 h-4 mr-2" />
                    Create Device
                  </Button>
                </form>
              </CardContent>
            </Card>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {devices
                .filter((device) => courses.some(c => c.id === device.course_id))
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
                      <div className="flex justify-end pt-2">
                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={() => handleDeleteClick('device', device.id, device.name)}
                        >
                          <Trash2 className="w-4 h-4 mr-2" />
                          Delete
                        </Button>
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
                <CardDescription>Add a new sponsor campaign</CardDescription>
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
                      onChange={(e) => setNewCampaign({ ...newCampaign, device_id: e.target.value })}
                      required
                    >
                      <option value="">Select Device</option>
                      {devices.map((device) => (
                        <option key={device.id} value={device.id}>
                          {device.name}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <Input
                      type="date"
                      placeholder="Start Date"
                      value={newCampaign.start_date}
                      onChange={(e) => setNewCampaign({ ...newCampaign, start_date: e.target.value })}
                      required
                    />
                    <Input
                      type="date"
                      placeholder="End Date"
                      value={newCampaign.end_date}
                      onChange={(e) => setNewCampaign({ ...newCampaign, end_date: e.target.value })}
                      required
                    />
                  </div>
                  <Input
                    type="file"
                    accept="image/*"
                    onChange={(e) => setNewCampaign({ ...newCampaign, creative_file: e.target.files?.[0] || null })}
                    required
                  />
                  <Button type="submit" disabled={previewLoading}>
                    <Plus className="w-4 h-4 mr-2" />
                    {previewLoading ? 'Generating Preview...' : 'Preview Campaign'}
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
                        <span className="text-sm text-gray-600">Start:</span>
                        <span className="text-sm">{new Date(campaign.start_date).toLocaleDateString()}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-600">End:</span>
                        <span className="text-sm">{new Date(campaign.end_date).toLocaleDateString()}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-600">Status:</span>
                        <Badge variant="default">Active</Badge>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </TabsContent>

          <TabsContent value="notices" className="space-y-6">
            <div className="text-center py-8">
              <h3 className="text-lg font-medium text-gray-900">Notice Management</h3>
              <p className="text-gray-500">Temporary notices are managed by course staff in their tenant dashboard.</p>
            </div>
          </TabsContent>

          <TabsContent value="analytics" className="space-y-6">
            <div className="space-y-6">
              <h2 className="text-2xl font-bold">Analytics & Reports</h2>
              
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
            </div>
          </TabsContent>

          <TabsContent value="audit-logs">
            <div className="space-y-6">
              <h2 className="text-2xl font-bold">Audit Logs</h2>
              
              <div className="bg-white p-6 rounded-lg shadow">
                <h3 className="text-xl font-semibold mb-4">Recent Activity</h3>
                <div className="space-y-2">
                  {auditLogs.map((log: any, index: number) => (
                    <div key={index} className="flex justify-between items-center p-3 bg-gray-50 rounded">
                      <div>
                        <span className="font-medium">{log.action}</span>
                        <span className="text-gray-600 ml-2">by {log.user}</span>
                      </div>
                      <span className="text-sm text-gray-500">{log.timestamp}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="settings">
            <div className="space-y-6">
              <h2 className="text-2xl font-bold">System Settings</h2>
              
              <div className="bg-white p-6 rounded-lg shadow">
                <h3 className="text-xl font-semibold mb-4">Configuration</h3>
                <p className="text-gray-600">System configuration options will be available here.</p>
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </main>

      <ImagePreviewDialog
        open={previewDialogOpen}
        onOpenChange={setPreviewDialogOpen}
        previewData={previewData}
        onApprove={handlePreviewApprove}
        onReject={handlePreviewReject}
        loading={campaignLoading}
      />

      <PiImagerConfigDialog
        open={piConfigDialogOpen}
        onOpenChange={(open) => {
          setPiConfigDialogOpen(open);
          if (!open) {
            setCreatedDevice(null);
          }
        }}
        device={createdDevice}
      />

      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Confirm Deletion</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete {deleteTarget?.type} "{deleteTarget?.name}"?
              {deleteTarget?.type === 'device' && (
                <span className="block mt-2 text-red-600">
                  This will also delete all associated campaigns, notices, and analytics data.
                </span>
              )}
              This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={handleDeleteCancel}
              disabled={deleteLoading}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDeleteConfirm}
              disabled={deleteLoading}
            >
              {deleteLoading ? 'Deleting...' : 'Delete'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default AdminDashboard;
