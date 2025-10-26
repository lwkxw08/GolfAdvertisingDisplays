import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Badge } from './ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Plus, Building, Monitor, Megaphone, BarChart3, LogOut, Bell, Settings, Shield, Trash2, Info } from 'lucide-react';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from './ui/dialog';
import { ImagePreviewDialog } from './ImagePreviewDialog';
import { PiImagerConfigDialog } from './PiImagerConfigDialog';
import DeviceMonitoringDashboard from './DeviceMonitoringDashboard';
import { AnalyticsDashboard } from './AnalyticsDashboard';
import { QRCodeManager } from './QRCodeManager';
import { QRCodeAnalytics } from './QRCodeAnalytics';
import { apiClient, Course, Device, SponsorCampaign, Notice } from '../lib/api';
import { Textarea } from './ui/textarea';
import { Edit, Clock } from 'lucide-react';

const AdminDashboard = () => {
  const [courses, setCourses] = useState<Course[]>([]);
  const [devices, setDevices] = useState<Device[]>([]);
  const [campaigns, setCampaigns] = useState<SponsorCampaign[]>([]);
  const [notices, setNotices] = useState<Notice[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  const [newCourse, setNewCourse] = useState({ name: '', location: '' });
  const [newDevice, setNewDevice] = useState({ 
    name: '', 
    device_id: '', 
    course_id: 0, 
    location: '',
    orientation: 'portrait' as 'portrait' | 'landscape'
  });
  const [newCampaign, setNewCampaign] = useState({
    sponsor_name: '',
    device_id: '',
    start_date: '',
    end_date: '',
    start_time: '',
    end_time: '',
    days_of_week: [] as string[],
    rotation_interval: '1',
    rotation_unit: 'hours',
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
  const [selectedDeviceForSetup, setSelectedDeviceForSetup] = useState<Device | null>(null);

  const [editingNotice, setEditingNotice] = useState<Notice | null>(null);
  const [noticeDialogOpen, setNoticeDialogOpen] = useState(false);

  const auditLogs = [
    { action: 'Course Created', user: 'admin@golfcms.com', timestamp: '2024-01-15 10:30:00' },
    { action: 'Device Added', user: 'admin@golfcms.com', timestamp: '2024-01-15 09:15:00' },
    { action: 'Campaign Updated', user: 'staff@pinevalley.com', timestamp: '2024-01-14 16:45:00' }
  ];

  const loadData = async () => {
    try {
      setLoading(true);
      const [coursesData, devicesData, campaignsData, noticesData] = await Promise.all([
        apiClient.getCourses(),
        apiClient.getDevices(),
        apiClient.getCampaigns(),
        apiClient.getAllNotices()
      ]);
      setCourses(coursesData);
      setDevices(devicesData);
      setCampaigns(campaignsData);
      setNotices(noticesData);
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
      setNewDevice({ name: '', device_id: '', course_id: 0, location: '', orientation: 'portrait' });
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
        start_time: newCampaign.start_time,
        end_time: newCampaign.end_time,
        days_of_week: newCampaign.days_of_week,
        rotation_interval: newCampaign.rotation_interval,
        rotation_unit: newCampaign.rotation_unit,
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
      formData.append('rotation_interval', pendingCampaignData.rotation_interval);
      formData.append('rotation_unit', pendingCampaignData.rotation_unit);
      if (pendingCampaignData.start_time) {
        formData.append('start_time', pendingCampaignData.start_time);
      }
      if (pendingCampaignData.end_time) {
        formData.append('end_time', pendingCampaignData.end_time);
      }
      if (pendingCampaignData.days_of_week && pendingCampaignData.days_of_week.length > 0) {
        formData.append('days_of_week', JSON.stringify(pendingCampaignData.days_of_week));
      }
      formData.append('creative', pendingCampaignData.creative_file);
      
      await apiClient.createCampaign(formData);
      
      setNewCampaign({
        sponsor_name: '',
        device_id: '',
        start_date: '',
        end_date: '',
        start_time: '',
        end_time: '',
        days_of_week: [],
        rotation_interval: '1',
        rotation_unit: 'hours',
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
    setError('');
    try {
      console.log(`Attempting to delete ${deleteTarget.type} with ID:`, deleteTarget.id);
      if (deleteTarget.type === 'course') {
        const result = await apiClient.deleteCourse(deleteTarget.id);
        console.log('Course delete result:', result);
      } else {
        const result = await apiClient.deleteDevice(deleteTarget.id);
        console.log('Device delete result:', result);
      }
      
      console.log('Delete successful, closing dialog and reloading data');
      setDeleteDialogOpen(false);
      setDeleteTarget(null);
      await loadData();
      setError('');
    } catch (err) {
      console.error('Delete failed with error:', err);
      const errorMessage = err instanceof Error ? err.message : `Failed to delete ${deleteTarget.type}`;
      console.error('Error message to display:', errorMessage);
      setError(errorMessage);
    } finally {
      setDeleteLoading(false);
    }
  };

  const handleDeleteCancel = () => {
    setDeleteDialogOpen(false);
    setDeleteTarget(null);
  };

  const handleEditNotice = (notice: Notice) => {
    setEditingNotice(notice);
    setNoticeDialogOpen(true);
  };

  const handleDeleteNotice = async (noticeId: number) => {
    if (!confirm('Are you sure you want to delete this notice?')) return;
    
    try {
      await apiClient.deleteNotice(noticeId);
      await loadData();
      setError('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete notice');
    }
  };

  const handleSaveNotice = async (noticeData: Partial<Notice>) => {
    try {
      if (editingNotice) {
        await apiClient.updateNotice(editingNotice.id, noticeData);
      }
      setNoticeDialogOpen(false);
      setEditingNotice(null);
      await loadData();
      setError('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save notice');
    }
  };

  const isNoticeActive = (notice: Notice) => {
    const now = new Date();
    const startTime = new Date(notice.start_time);
    const endTime = new Date(notice.end_time);
    return now >= startTime && now <= endTime && notice.is_active;
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
          <TabsList className="grid w-full grid-cols-10">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="courses">Courses</TabsTrigger>
            <TabsTrigger value="devices">Devices</TabsTrigger>
            <TabsTrigger value="campaigns">Campaigns</TabsTrigger>
            <TabsTrigger value="notices">Notices</TabsTrigger>
            <TabsTrigger value="qr-codes">QR Codes</TabsTrigger>
            <TabsTrigger value="monitoring">Monitoring</TabsTrigger>
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
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
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
                    <select
                      className="px-3 py-2 border border-gray-300 rounded-md"
                      value={newDevice.orientation}
                      onChange={(e) => setNewDevice({ ...newDevice, orientation: e.target.value as 'portrait' | 'landscape' })}
                      required
                    >
                      <option value="portrait">Portrait</option>
                      <option value="landscape">Landscape</option>
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
                        <span className="text-sm text-gray-600">Orientation:</span>
                        <span className="text-sm capitalize">{device.orientation || 'portrait'}</span>
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
                      <div className="flex justify-end gap-2 pt-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setSelectedDeviceForSetup(device)}
                        >
                          <Info className="w-4 h-4 mr-2" />
                          Setup Info
                        </Button>
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
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-sm text-gray-600 mb-1 block">Start Time (Optional)</label>
                      <Input
                        type="time"
                        placeholder="Start Time"
                        value={newCampaign.start_time}
                        onChange={(e) => setNewCampaign({ ...newCampaign, start_time: e.target.value })}
                      />
                    </div>
                    <div>
                      <label className="text-sm text-gray-600 mb-1 block">End Time (Optional)</label>
                      <Input
                        type="time"
                        placeholder="End Time"
                        value={newCampaign.end_time}
                        onChange={(e) => setNewCampaign({ ...newCampaign, end_time: e.target.value })}
                      />
                    </div>
                  </div>
                  <div>
                    <label className="text-sm text-gray-600 mb-2 block">Days of Week (Optional - leave empty for all days)</label>
                    <div className="grid grid-cols-4 gap-2">
                      {['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'].map((day) => (
                        <label key={day} className="flex items-center space-x-2 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={newCampaign.days_of_week.includes(day.toLowerCase())}
                            onChange={(e) => {
                              if (e.target.checked) {
                                setNewCampaign({ 
                                  ...newCampaign, 
                                  days_of_week: [...newCampaign.days_of_week, day.toLowerCase()] 
                                });
                              } else {
                                setNewCampaign({ 
                                  ...newCampaign, 
                                  days_of_week: newCampaign.days_of_week.filter(d => d !== day.toLowerCase()) 
                                });
                              }
                            }}
                            className="rounded"
                          />
                          <span className="text-sm">{day.slice(0, 3)}</span>
                        </label>
                      ))}
                    </div>
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
            <h2 className="text-2xl font-bold">Notice Management</h2>
            
            <div className="grid grid-cols-1 gap-4">
              {notices.length === 0 ? (
                <Card>
                  <CardContent className="text-center py-8">
                    <p className="text-gray-500">No notices created yet</p>
                  </CardContent>
                </Card>
              ) : (
                notices
                  .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
                  .map((notice) => (
                    <Card key={notice.id}>
                      <CardContent className="p-6">
                        <div className="flex items-start justify-between mb-4">
                          <div className="flex-1">
                            <div className="flex items-center gap-3 mb-2">
                              <h3 className="text-lg font-semibold">{notice.title}</h3>
                              <Badge variant={isNoticeActive(notice) ? "default" : "secondary"}>
                                {isNoticeActive(notice) ? "Active" : "Expired"}
                              </Badge>
                            </div>
                            <p className="text-gray-600 mb-3">{notice.content}</p>
                            <div className="grid grid-cols-2 gap-4 text-sm text-gray-500">
                              <div>
                                <span className="font-medium">Device:</span> {devices.find(d => d.id === notice.device_id)?.name || 'Unknown'}
                              </div>
                              <div>
                                <span className="font-medium">Course:</span> {courses.find(c => c.id === notice.course_id)?.name || 'Unknown'}
                              </div>
                              <div>
                                <span className="font-medium">Start:</span> {new Date(notice.start_time).toLocaleString()}
                              </div>
                              <div>
                                <span className="font-medium">End:</span> {new Date(notice.end_time).toLocaleString()}
                              </div>
                            </div>
                          </div>
                          <div className="flex gap-2 ml-4">
                            {!isNoticeActive(notice) && (
                              <Button
                                variant="secondary"
                                size="sm"
                                onClick={() => {
                                  const now = new Date();
                                  const duration = new Date(notice.end_time).getTime() - new Date(notice.start_time).getTime();
                                  const newEndTime = new Date(now.getTime() + duration);
                                  setEditingNotice({
                                    ...notice,
                                    start_time: now.toISOString(),
                                    end_time: newEndTime.toISOString()
                                  });
                                  setNoticeDialogOpen(true);
                                }}
                              >
                                <Clock className="w-4 h-4 mr-1" />
                                Re-use
                              </Button>
                            )}
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleEditNotice(notice)}
                            >
                              <Edit className="w-4 h-4 mr-1" />
                              Edit
                            </Button>
                            <Button
                              variant="destructive"
                              size="sm"
                              onClick={() => handleDeleteNotice(notice.id)}
                            >
                              <Trash2 className="w-4 h-4 mr-1" />
                              Delete
                            </Button>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))
              )}
            </div>
          </TabsContent>

          <TabsContent value="qr-codes" className="space-y-6">
            <Tabs defaultValue="manager" className="space-y-6">
              <TabsList>
                <TabsTrigger value="manager">QR Code Manager</TabsTrigger>
                <TabsTrigger value="analytics">QR Analytics</TabsTrigger>
              </TabsList>
              
              <TabsContent value="manager">
                <QRCodeManager 
                  courseId={courses.length > 0 ? courses[0].id : undefined}
                />
              </TabsContent>
              
              <TabsContent value="analytics">
                <QRCodeAnalytics 
                  courseId={courses.length > 0 ? courses[0].id : undefined}
                />
              </TabsContent>
            </Tabs>
          </TabsContent>

          <TabsContent value="monitoring" className="space-y-6">
            <DeviceMonitoringDashboard />
          </TabsContent>

          <TabsContent value="analytics" className="space-y-6">
            <AnalyticsDashboard />
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
        orientation={devices.find(d => d.id === parseInt(newCampaign.device_id))?.orientation || 'portrait'}
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

      <PiImagerConfigDialog
        open={selectedDeviceForSetup !== null}
        onOpenChange={(open) => {
          if (!open) {
            setSelectedDeviceForSetup(null);
          }
        }}
        device={selectedDeviceForSetup}
      />

      <Dialog open={noticeDialogOpen} onOpenChange={setNoticeDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Edit Notice</DialogTitle>
            <DialogDescription>Update notice details</DialogDescription>
          </DialogHeader>
          {editingNotice && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Title</label>
                <Input
                  value={editingNotice.title}
                  onChange={(e) => setEditingNotice({...editingNotice, title: e.target.value})}
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Content</label>
                <Textarea
                  value={editingNotice.content}
                  onChange={(e) => setEditingNotice({...editingNotice, content: e.target.value})}
                  rows={4}
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Start Time</label>
                  <Input
                    type="datetime-local"
                    value={new Date(editingNotice.start_time).toISOString().slice(0, 16)}
                    onChange={(e) => setEditingNotice({...editingNotice, start_time: new Date(e.target.value).toISOString()})}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">End Time</label>
                  <Input
                    type="datetime-local"
                    value={new Date(editingNotice.end_time).toISOString().slice(0, 16)}
                    onChange={(e) => setEditingNotice({...editingNotice, end_time: new Date(e.target.value).toISOString()})}
                  />
                </div>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setNoticeDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={() => handleSaveNotice(editingNotice!)}>
              Save Changes
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

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
              {deleteLoading && (
                <span className="block mt-2 text-blue-600">
                  Please wait... This may take up to a minute if the server is waking up.
                </span>
              )}
              {!deleteLoading && <span className="block mt-2">This action cannot be undone.</span>}
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
