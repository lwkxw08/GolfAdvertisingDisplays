const API_BASE_URL = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';

export interface User {
  id: number;
  email: string;
  role: 'admin' | 'super_admin' | 'regional_admin' | 'course_manager' | 'client_tenant';
  course_id?: number;
  region_id?: number;
  permissions?: any;
  last_login?: string;
  sso_provider?: string;
  sso_user_id?: string;
  is_active: boolean;
  created_at: string;
}

export interface Course {
  id: number;
  name: string;
  location: string;
  region_id?: number;
  created_at: string;
}

export interface Device {
  id: number;
  name: string;
  device_id: string;
  course_id: number;
  is_online: boolean;
  last_sync?: string;
  created_at: string;
  firmware_version?: string;
  hardware_version?: string;
  remote_update_enabled?: boolean;
  diagnostic_enabled?: boolean;
}

export interface SponsorCampaign {
  id: number;
  sponsor_name: string;
  device_id: number;
  creative_path: string;
  start_date: string;
  end_date: string;
  rotation_interval: number;
  rotation_unit: 'hours' | 'days' | 'weeks' | 'months';
  priority: number;
  is_active: boolean;
  created_at: string;
  schedule_id?: number;
  ab_test_group?: string;
  performance_metrics?: any;
}

export interface Notice {
  id: number;
  title: string;
  content: string;
  device_id: number;
  course_id: number;
  created_by: number;
  start_time: string;
  end_time: string;
  is_active: boolean;
  created_at: string;
  duration_minutes?: number;
  style_id?: number;
  schedule_id?: number;
}

class ApiClient {
  private token: string | null = null;

  constructor() {
    this.token = localStorage.getItem('token');
  }

  setToken(token: string) {
    this.token = token;
    localStorage.setItem('token', token);
  }

  clearToken() {
    this.token = null;
    localStorage.removeItem('token');
  }

  private async request(endpoint: string, options: RequestInit = {}) {
    const url = `${API_BASE_URL}${endpoint}`;
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
    };

    if (this.token) {
      headers.Authorization = `Bearer ${this.token}`;
    }

    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }

  async login(email: string, password: string) {
    const response = await this.request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    this.setToken(response.access_token);
    return response;
  }

  async register(userData: {
    email: string;
    password: string;
    role: 'admin' | 'client_tenant';
    course_id?: number;
  }) {
    return this.request('/auth/register', {
      method: 'POST',
      body: JSON.stringify(userData),
    });
  }

  async getCourses(): Promise<Course[]> {
    return this.request('/admin/courses');
  }

  async createCourse(courseData: { name: string; location: string }): Promise<Course> {
    return this.request('/admin/courses', {
      method: 'POST',
      body: JSON.stringify(courseData),
    });
  }

  async getDevices(): Promise<Device[]> {
    return this.request('/admin/devices');
  }

  async getCourseDevices(courseId: number): Promise<Device[]> {
    return this.request(`/courses/${courseId}/devices`);
  }

  async createDevice(deviceData: {
    name: string;
    device_id: string;
    course_id: number;
  }): Promise<Device> {
    return this.request('/admin/devices', {
      method: 'POST',
      body: JSON.stringify(deviceData),
    });
  }

  async getCampaigns(deviceId?: number): Promise<SponsorCampaign[]> {
    const params = deviceId ? `?device_id=${deviceId}` : '';
    return this.request(`/admin/campaigns${params}`);
  }

  async createCampaign(campaignData: FormData): Promise<SponsorCampaign> {
    const url = `${API_BASE_URL}/admin/campaigns`;
    const headers: Record<string, string> = {};

    if (this.token) {
      headers.Authorization = `Bearer ${this.token}`;
    }

    const response = await fetch(url, {
      method: 'POST',
      headers,
      body: campaignData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }

  async getNotices(courseId: number): Promise<Notice[]> {
    return this.request(`/courses/${courseId}/notices`);
  }

  async createNotice(courseId: number, noticeData: {
    title: string;
    content: string;
    device_id: number;
    start_time: string;
  }): Promise<Notice> {
    return this.request(`/courses/${courseId}/notices`, {
      method: 'POST',
      body: JSON.stringify(noticeData),
    });
  }

  async registerCourse(courseData: {
    course_name: string;
    location: string;
    owner_email: string;
    owner_password: string;
    phone?: string;
    website?: string;
    plan_type: 'basic' | 'premium' | 'enterprise';
  }) {
    return this.request('/auth/register-course', {
      method: 'POST',
      body: JSON.stringify(courseData),
    });
  }

  async getSubscriptions() {
    return this.request('/admin/subscriptions');
  }

  async getAnalyticsSummary() {
    return this.request('/admin/analytics/summary');
  }

  async getCourseAnalytics() {
    return this.request('/admin/analytics/courses');
  }

  async getDevicePlaylistOptimized(deviceId: string, connectivity: 'wifi' | 'lte' = 'wifi') {
    return this.request(`/api/device/${deviceId}/playlist?connectivity=${connectivity}`);
  }

  async updateDeviceStatus(deviceId: string, statusData: any) {
    return this.request(`/api/device/${deviceId}/status`, {
      method: 'POST',
      body: JSON.stringify(statusData),
    });
  }

  async getDeviceDiagnostics(deviceId: string) {
    return this.request(`/api/device/${deviceId}/diagnostics`);
  }

  async processImageForEink(file: File) {
    const formData = new FormData();
    formData.append('file', file);
    
    const url = `${API_BASE_URL}/api/images/process-for-eink`;
    const headers: Record<string, string> = {};

    if (this.token) {
      headers.Authorization = `Bearer ${this.token}`;
    }

    const response = await fetch(url, {
      method: 'POST',
      headers,
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }

  async generateNoticeEinkImage(noticeId: number) {
    return this.request(`/api/notices/${noticeId}/generate-eink-image`, {
      method: 'POST',
    });
  }

  async getConnectivityOptions() {
    return this.request('/api/eink/connectivity-options');
  }

  async getEmailTemplates() {
    return this.request('/admin/email-templates');
  }

  async setupDefaultTemplates() {
    return this.request('/admin/setup-templates', {
      method: 'POST',
    });
  }

  async testAlert(alertType: string): Promise<any> {
    const response = await this.request(`/admin/alerts/test?alert_type=${alertType}`, {
      method: 'POST'
    });
    return response;
  }

  async getAdvancedAnalytics(days: number = 30): Promise<any> {
    const response = await this.request(`/admin/analytics/advanced?days=${days}`);
    return response;
  }

  async getDeviceHealth(courseId?: number): Promise<any> {
    const url = courseId ? `/admin/devices/health?course_id=${courseId}` : '/admin/devices/health';
    const response = await this.request(url);
    return response;
  }

  async createAdvancedNotice(noticeData: any): Promise<any> {
    const response = await this.request('/notices/advanced', {
      method: 'POST',
      body: JSON.stringify(noticeData)
    });
    return response;
  }

  async getNoticeStyles(): Promise<any> {
    const response = await this.request('/admin/notice-styles');
    return response;
  }

  async createSeasonalCampaign(campaignData: any): Promise<any> {
    const response = await this.request('/admin/campaigns/seasonal', {
      method: 'POST',
      body: JSON.stringify(campaignData)
    });
    return response;
  }

  async createABTestCampaign(testData: any): Promise<any> {
    const response = await this.request('/admin/campaigns/ab-test', {
      method: 'POST',
      body: JSON.stringify(testData)
    });
    return response;
  }

  async getAuditLogs(params?: any): Promise<any> {
    const queryParams = new URLSearchParams(params || {}).toString();
    const url = queryParams ? `/admin/audit-logs?${queryParams}` : '/admin/audit-logs';
    const response = await this.request(url);
    return response;
  }

  async getAuditSummary(days: number = 30): Promise<any> {
    const response = await this.request(`/admin/audit-logs/summary?days=${days}`);
    return response;
  }

  async exportAuditLogs(exportRequest: any): Promise<any> {
    const response = await this.request('/admin/audit-logs/export', {
      method: 'POST',
      body: JSON.stringify(exportRequest)
    });
    return response;
  }

  async getRegions(): Promise<any> {
    const response = await this.request('/admin/regions');
    return response;
  }

  async createRegion(regionData: any): Promise<any> {
    const response = await this.request('/admin/regions', {
      method: 'POST',
      body: JSON.stringify(regionData)
    });
    return response;
  }

  async getSSOProviders(): Promise<any> {
    const response = await this.request('/admin/sso-providers');
    return response;
  }

  async createSSOProvider(providerData: any): Promise<any> {
    const response = await this.request('/admin/sso-providers', {
      method: 'POST',
      body: JSON.stringify(providerData)
    });
    return response;
  }

  async getNoticeTemplates(courseId: number): Promise<any[]> {
    return this.request(`/courses/${courseId}/notice-templates`);
  }

  async createNoticeTemplate(courseId: number, templateData: any): Promise<any> {
    return this.request(`/courses/${courseId}/notice-templates`, {
      method: 'POST',
      body: JSON.stringify(templateData),
    });
  }

  async createEnhancedNotice(courseId: number, noticeData: any): Promise<any> {
    return this.request(`/courses/${courseId}/notices/enhanced`, {
      method: 'POST',
      body: JSON.stringify(noticeData),
    });
  }
}

export const apiClient = new ApiClient();
