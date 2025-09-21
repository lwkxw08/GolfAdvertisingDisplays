import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { apiClient, Device, Notice } from '../lib/api';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Textarea } from './ui/textarea';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Alert, AlertDescription } from './ui/alert';
import { Badge } from './ui/badge';
import { Plus, Monitor, Bell, LogOut, Clock } from 'lucide-react';

export const TenantDashboard: React.FC = () => {
  const { user, logout } = useAuth();
  const [devices, setDevices] = useState<Device[]>([]);
  const [notices, setNotices] = useState<Notice[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [newNotice, setNewNotice] = useState({
    title: '',
    content: '',
    device_id: 0,
    start_time: '',
  });

  useEffect(() => {
    if (user?.course_id) {
      loadData();
    }
  }, [user]);

  const loadData = async () => {
    if (!user?.course_id) return;

    try {
      setLoading(true);
      const [devicesData, noticesData] = await Promise.all([
        apiClient.getCourseDevices(user.course_id),
        apiClient.getNotices(user.course_id),
      ]);
      setDevices(devicesData);
      setNotices(noticesData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateNotice = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user?.course_id) return;

    try {
      await apiClient.createNotice(user.course_id, newNotice);
      setNewNotice({
        title: '',
        content: '',
        device_id: 0,
        start_time: '',
      });
      loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create notice');
    }
  };

  const isNoticeActive = (notice: Notice) => {
    const now = new Date();
    const startTime = new Date(notice.start_time);
    const endTime = new Date(notice.end_time);
    return now >= startTime && now <= endTime && notice.is_active;
  };

  const getTimeRemaining = (notice: Notice) => {
    const now = new Date();
    const endTime = new Date(notice.end_time);
    const diff = endTime.getTime() - now.getTime();
    
    if (diff <= 0) return 'Expired';
    
    const minutes = Math.floor(diff / (1000 * 60));
    const hours = Math.floor(minutes / 60);
    
    if (hours > 0) {
      return `${hours}h ${minutes % 60}m remaining`;
    }
    return `${minutes}m remaining`;
  };

  if (loading) {
    return <div className="flex items-center justify-center min-h-screen">Loading...</div>;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <h1 className="text-2xl font-bold text-gray-900">Course Management</h1>
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

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Create Notice</CardTitle>
                <CardDescription>
                  Create a temporary notice for your tee box displays (max 1 hour)
                </CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleCreateNotice} className="space-y-4">
                  <Input
                    placeholder="Notice Title"
                    value={newNotice.title}
                    onChange={(e) => setNewNotice({ ...newNotice, title: e.target.value })}
                    required
                  />
                  
                  <Textarea
                    placeholder="Notice Content"
                    value={newNotice.content}
                    onChange={(e) => setNewNotice({ ...newNotice, content: e.target.value })}
                    required
                    rows={3}
                  />
                  
                  <select
                    className="w-full px-3 py-2 border border-gray-300 rounded-md"
                    value={newNotice.device_id}
                    onChange={(e) => setNewNotice({ ...newNotice, device_id: parseInt(e.target.value) })}
                    required
                  >
                    <option value={0}>Select Device</option>
                    {devices.map((device) => (
                      <option key={device.id} value={device.id}>
                        {device.name}
                      </option>
                    ))}
                  </select>
                  
                  <Input
                    type="datetime-local"
                    value={newNotice.start_time}
                    onChange={(e) => setNewNotice({ ...newNotice, start_time: e.target.value })}
                    required
                  />
                  
                  <Button type="submit" className="w-full">
                    <Plus className="w-4 h-4 mr-2" />
                    Create Notice
                  </Button>
                </form>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>
                  <Monitor className="w-5 h-5 mr-2 inline" />
                  Your Devices
                </CardTitle>
                <CardDescription>Tee box displays in your course</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {devices.map((device) => (
                    <div key={device.id} className="flex items-center justify-between p-3 border rounded-lg">
                      <div>
                        <h4 className="font-medium">{device.name}</h4>
                        <p className="text-sm text-gray-600">{device.device_id}</p>
                      </div>
                      <div className="flex items-center space-x-2">
                        <Badge variant={device.is_online ? "default" : "secondary"}>
                          {device.is_online ? "Online" : "Offline"}
                        </Badge>
                        {device.last_sync && (
                          <span className="text-xs text-gray-500">
                            Last sync: {new Date(device.last_sync).toLocaleTimeString()}
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>

          <div>
            <Card>
              <CardHeader>
                <CardTitle>
                  <Bell className="w-5 h-5 mr-2 inline" />
                  Active Notices
                </CardTitle>
                <CardDescription>Current and recent notices for your devices</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {notices.length === 0 ? (
                    <p className="text-gray-500 text-center py-8">No notices created yet</p>
                  ) : (
                    notices
                      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
                      .map((notice) => (
                        <div key={notice.id} className="border rounded-lg p-4">
                          <div className="flex items-start justify-between mb-2">
                            <h4 className="font-medium">{notice.title}</h4>
                            <Badge variant={isNoticeActive(notice) ? "default" : "secondary"}>
                              {isNoticeActive(notice) ? "Active" : "Expired"}
                            </Badge>
                          </div>
                          
                          <p className="text-sm text-gray-600 mb-3">{notice.content}</p>
                          
                          <div className="flex items-center justify-between text-xs text-gray-500">
                            <span>
                              Device: {devices.find(d => d.id === notice.device_id)?.name}
                            </span>
                            {isNoticeActive(notice) && (
                              <div className="flex items-center">
                                <Clock className="w-3 h-3 mr-1" />
                                {getTimeRemaining(notice)}
                              </div>
                            )}
                          </div>
                          
                          <div className="mt-2 text-xs text-gray-400">
                            Created: {new Date(notice.created_at).toLocaleString()}
                          </div>
                        </div>
                      ))
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </main>
    </div>
  );
};
