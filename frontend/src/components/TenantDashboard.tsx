import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { apiClient, Device, Notice } from '../lib/api';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Textarea } from './ui/textarea';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Alert, AlertDescription } from './ui/alert';
import { Badge } from './ui/badge';
import { Plus, Monitor, Bell, LogOut, Clock, Eye } from 'lucide-react';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from './ui/dialog';

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
    start_time: (() => {
      const now = new Date();
      const year = now.getFullYear();
      const month = String(now.getMonth() + 1).padStart(2, '0');
      const day = String(now.getDate()).padStart(2, '0');
      const hours = String(now.getHours()).padStart(2, '0');
      const minutes = String(now.getMinutes()).padStart(2, '0');
      return `${year}-${month}-${day}T${hours}:${minutes}`;
    })(),
    duration_minutes: 60,
    style_id: null as number | null,
    template_id: null as number | null,
  });
  const [noticeTemplates, setNoticeTemplates] = useState<any[]>([]);
  const [noticeStyles, setNoticeStyles] = useState<any[]>([]);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [showTemplate, setShowTemplate] = useState(false);
  const [showPreview, setShowPreview] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [newTemplate, setNewTemplate] = useState({
    name: '',
    title: '',
    content: '',
    style_id: null as number | null,
    default_duration_minutes: 60,
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
      const [devicesData, noticesData, templatesData, stylesData] = await Promise.all([
        apiClient.getCourseDevices(user.course_id),
        apiClient.getNotices(user.course_id),
        apiClient.getNoticeTemplates(user.course_id),
        apiClient.getNoticeStyles(),
      ]);
      setDevices(devicesData);
      setNotices(noticesData);
      setNoticeTemplates(templatesData);
      setNoticeStyles(stylesData);
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
      if (showAdvanced) {
        await apiClient.createEnhancedNotice(user.course_id, newNotice);
      } else {
        await apiClient.createNotice(user.course_id, newNotice);
      }
      setNewNotice({
        title: '',
        content: '',
        device_id: 0,
        start_time: (() => {
          const now = new Date();
          const year = now.getFullYear();
          const month = String(now.getMonth() + 1).padStart(2, '0');
          const day = String(now.getDate()).padStart(2, '0');
          const hours = String(now.getHours()).padStart(2, '0');
          const minutes = String(now.getMinutes()).padStart(2, '0');
          return `${year}-${month}-${day}T${hours}:${minutes}`;
        })(),
        duration_minutes: 60,
        style_id: null,
        template_id: null,
      });
      loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create notice');
    }
  };

  const handleCreateTemplate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user?.course_id) return;

    try {
      await apiClient.createNoticeTemplate(user.course_id, newTemplate);
      setNewTemplate({
        name: '',
        title: '',
        content: '',
        style_id: null,
        default_duration_minutes: 60,
      });
      setShowTemplate(false);
      loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create template');
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

  const handlePreviewNotice = async () => {
    if (!newNotice.title || !newNotice.content || !newNotice.device_id) {
      setError('Please fill in title, content, and select a device before previewing');
      return;
    }

    try {
      setPreviewLoading(true);
      setError('');
      const result = await apiClient.previewNoticeEink({
        title: newNotice.title,
        content: newNotice.content,
        device_id: newNotice.device_id,
      });
      setPreviewUrl(result.preview_url);
      setShowPreview(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate preview');
    } finally {
      setPreviewLoading(false);
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
                  Create a notice for your tee box displays with advanced scheduling options
                </CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleCreateNotice} className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-lg font-medium">Create Notice</h3>
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => setShowAdvanced(!showAdvanced)}
                    >
                      {showAdvanced ? 'Basic' : 'Advanced'}
                    </Button>
                  </div>
                  
                  {noticeTemplates.length > 0 && (
                    <select
                      className="w-full px-3 py-2 border border-gray-300 rounded-md"
                      value={newNotice.template_id || ''}
                      onChange={(e) => {
                        const templateId = e.target.value ? parseInt(e.target.value) : null;
                        if (templateId) {
                          const template = noticeTemplates.find(t => t.id === templateId);
                          if (template) {
                            setNewNotice({
                              ...newNotice,
                              template_id: templateId,
                              title: template.title,
                              content: template.content,
                              style_id: template.style_id,
                              duration_minutes: template.default_duration_minutes
                            });
                          }
                        } else {
                          setNewNotice({
                            ...newNotice,
                            template_id: null,
                            title: '',
                            content: '',
                            style_id: null,
                            duration_minutes: 60
                          });
                        }
                      }}
                    >
                      <option value="">Create from scratch</option>
                      {noticeTemplates.map((template) => (
                        <option key={template.id} value={template.id}>
                          {template.name}
                        </option>
                      ))}
                    </select>
                  )}
                  
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
                  
                  {showAdvanced && (
                    <>
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="block text-sm font-medium mb-1">Duration (minutes)</label>
                          <Input
                            type="number"
                            min="1"
                            max={user?.role === 'course_manager' ? "1440" : "60"}
                            value={newNotice.duration_minutes}
                            onChange={(e) => setNewNotice({ ...newNotice, duration_minutes: parseInt(e.target.value) })}
                            required
                          />
                        </div>
                        
                        <div>
                          <label className="block text-sm font-medium mb-1">Font Style</label>
                          <select
                            className="w-full px-3 py-2 border border-gray-300 rounded-md"
                            value={newNotice.style_id || ''}
                            onChange={(e) => setNewNotice({ ...newNotice, style_id: e.target.value ? parseInt(e.target.value) : null })}
                          >
                            <option value="">Default Style</option>
                            {noticeStyles.map((style) => (
                              <option key={style.id} value={style.id}>
                                {style.name} ({style.font_family})
                              </option>
                            ))}
                          </select>
                        </div>
                      </div>
                    </>
                  )}
                  
                  <div className="flex space-x-2">
                    <Button
                      type="button"
                      variant="outline"
                      onClick={handlePreviewNotice}
                      disabled={previewLoading || !newNotice.title || !newNotice.content || !newNotice.device_id}
                    >
                      <Eye className="w-4 h-4 mr-2" />
                      {previewLoading ? 'Loading...' : 'Preview'}
                    </Button>
                    <Button type="submit" className="flex-1">
                      <Plus className="w-4 h-4 mr-2" />
                      Create Notice
                    </Button>
                    {showAdvanced && (
                      <Button
                        type="button"
                        variant="outline"
                        onClick={() => setShowTemplate(true)}
                      >
                        Save as Template
                      </Button>
                    )}
                  </div>
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

        {showTemplate && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 w-full max-w-md">
              <h3 className="text-lg font-medium mb-4">Save as Template</h3>
              <form onSubmit={handleCreateTemplate} className="space-y-4">
                <Input
                  placeholder="Template Name"
                  value={newTemplate.name}
                  onChange={(e) => setNewTemplate({ ...newTemplate, name: e.target.value })}
                  required
                />
                
                <Input
                  placeholder="Template Title"
                  value={newTemplate.title}
                  onChange={(e) => setNewTemplate({ ...newTemplate, title: e.target.value })}
                  required
                />
                
                <Textarea
                  placeholder="Template Content"
                  value={newTemplate.content}
                  onChange={(e) => setNewTemplate({ ...newTemplate, content: e.target.value })}
                  required
                  rows={3}
                />
                
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">Default Duration (minutes)</label>
                    <Input
                      type="number"
                      min="1"
                      max="1440"
                      value={newTemplate.default_duration_minutes}
                      onChange={(e) => setNewTemplate({ ...newTemplate, default_duration_minutes: parseInt(e.target.value) })}
                      required
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium mb-1">Font Style</label>
                    <select
                      className="w-full px-3 py-2 border border-gray-300 rounded-md"
                      value={newTemplate.style_id || ''}
                      onChange={(e) => setNewTemplate({ ...newTemplate, style_id: e.target.value ? parseInt(e.target.value) : null })}
                    >
                      <option value="">Default Style</option>
                      {noticeStyles.map((style) => (
                        <option key={style.id} value={style.id}>
                          {style.name} ({style.font_family})
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
                
                <div className="flex space-x-2">
                  <Button type="submit" className="flex-1">
                    Save Template
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => setShowTemplate(false)}
                  >
                    Cancel
                  </Button>
                </div>
              </form>
            </div>
          </div>
        )}

        <Dialog open={showPreview} onOpenChange={setShowPreview}>
          <DialogContent className="max-w-4xl">
            <DialogHeader>
              <DialogTitle>Notice Preview - E-ink Display</DialogTitle>
              <DialogDescription>
                Preview how your notice will appear on the device's E-ink display
              </DialogDescription>
            </DialogHeader>
            {previewUrl && (
              <div className="flex justify-center bg-gray-100 p-4 rounded-lg">
                <img
                  src={previewUrl}
                  alt="Notice Preview"
                  className="max-w-full max-h-96 border-2 border-gray-300 rounded shadow-lg"
                />
              </div>
            )}
          </DialogContent>
        </Dialog>
      </main>
    </div>
  );
};
