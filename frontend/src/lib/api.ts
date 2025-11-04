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
  location: string;
  is_online: boolean;
  last_sync?: string;
  created_at: string;
  firmware_version?: string;
  hardware_version?: string;
  remote_update_enabled?: boolean;
  diagnostic_enabled?: boolean;
  orientation?: 'portrait' | 'landscape';
}

export interface SponsorCampaign {
  id: number;
  sponsor_name: string;
  device_id: number;
  creative_path: string;
  start_date: string;
  end_date: string;
  start_time?: string;
  end_time?: string;
  days_of_week?: string[];
  rotation_interval: number;
  rotation_unit: 'hours' | 'days' | 'weeks' | 'months';
  priority: number;
  is_active: boolean;
  created_at: string;
  schedule_id?: number;
  ab_test_group?: string;
  performance_metrics?: any;
  status?: 'active_now' | 'scheduled' | 'expired' | 'paused';
  currently_active?: boolean;
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

  private async request(endpoint: string, options: RequestInit = {}, retries = 2, timeout = 30000) {
    const url = `${API_BASE_URL}${endpoint}`;
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
    };

    if (this.token) {
      headers.Authorization = `Bearer ${this.token}`;
    }

    for (let attempt = 0; attempt <= retries; attempt++) {
      try {
        const response = await fetch(url, {
          ...options,
          headers,
          signal: AbortSignal.timeout(timeout),
        });

        if (response.status === 401) {
          if (this.token) {
            this.clearToken();
            localStorage.removeItem('user');
            if (!(window as any).__redirectingToLogin) {
              (window as any).__redirectingToLogin = true;
              const next = encodeURIComponent(window.location.href);
              window.location.replace(`/?next=${next}`);
            }
          }
          throw new Error('Unauthorized');
        }

        if (!response.ok) {
          const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
          throw new Error(error.detail || `HTTP ${response.status}`);
        }

        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
          return response.json();
        } else if (response.status === 204 || response.headers.get('content-length') === '0') {
          return {};
        } else {
          return response.json().catch(() => ({}));
        }
      } catch (error: any) {
        if (attempt === retries || (error.name !== 'AbortError' && !error.message.includes('fetch'))) {
          if (error.name === 'AbortError' || error.name === 'TimeoutError') {
            throw new Error('Request timed out. The server may be sleeping, please try again.');
          }
          throw error;
        }
        await new Promise(resolve => setTimeout(resolve, Math.pow(2, attempt) * 1000));
      }
    }
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
    location: string;
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

  async updateCampaign(campaignId: number, campaignData: FormData): Promise<SponsorCampaign> {
    const url = `${API_BASE_URL}/admin/campaigns/${campaignId}`;
    const headers: Record<string, string> = {};

    if (this.token) {
      headers.Authorization = `Bearer ${this.token}`;
    }

    const response = await fetch(url, {
      method: 'PUT',
      headers,
      body: campaignData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }

  async deleteCampaign(campaignId: number): Promise<void> {
    const result = await this.request(`/admin/campaigns/${campaignId}`, {
      method: 'DELETE',
    });
    return result;
  }

  async bulkCreateCampaigns(campaignsData: string, creatives: File[]): Promise<SponsorCampaign[]> {
    const url = `${API_BASE_URL}/admin/campaigns/bulk`;
    const headers: Record<string, string> = {};

    if (this.token) {
      headers.Authorization = `Bearer ${this.token}`;
    }

    const formData = new FormData();
    formData.append('campaigns_data', campaignsData);
    creatives.forEach((file) => {
      formData.append('creatives', file);
    });

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

  async previewImageForEink(file: File): Promise<{
    status: string;
    preview_image: string;
    image_info: any;
    e6_optimized: boolean;
  }> {
    const formData = new FormData();
    formData.append('file', file);
    
    const url = `${API_BASE_URL}/api/images/preview-for-eink`;
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

  async updateNoticeTemplate(courseId: number, templateId: number, templateData: any): Promise<any> {
    return this.request(`/courses/${courseId}/notice-templates/${templateId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(templateData),
    });
  }

  async deleteNoticeTemplate(courseId: number, templateId: number): Promise<{message: string}> {
    try {
      const result = await this.request(`/courses/${courseId}/notice-templates/${templateId}`, {
        method: 'DELETE',
      }, 2, 60000);
      return result;
    } catch (error) {
      console.error('Error deleting template:', error);
      throw error;
    }
  }

  async createEnhancedNotice(courseId: number, noticeData: any): Promise<any> {
    return this.request(`/courses/${courseId}/notices/enhanced`, {
      method: 'POST',
      body: JSON.stringify(noticeData),
    });
  }

  async deleteCourse(courseId: number): Promise<{message: string}> {
    console.log('Deleting course:', courseId);
    try {
      const result = await this.request(`/admin/courses/${courseId}`, {
        method: 'DELETE',
      }, 2, 60000);
      console.log('Course deleted successfully:', result);
      return result;
    } catch (error) {
      console.error('Error deleting course:', error);
      throw error;
    }
  }

  async deleteDevice(deviceId: number): Promise<{message: string}> {
    console.log('Deleting device:', deviceId);
    try {
      const result = await this.request(`/admin/devices/${deviceId}`, {
        method: 'DELETE',
      }, 2, 60000);
      console.log('Device deleted successfully:', result);
      return result;
    } catch (error) {
      console.error('Error deleting device:', error);
      throw error;
    }
  }

  async getAllNotices(courseId?: number, deviceId?: number): Promise<Notice[]> {
    let url = '/admin/notices';
    const params = new URLSearchParams();
    if (courseId) params.append('course_id', courseId.toString());
    if (deviceId) params.append('device_id', deviceId.toString());
    if (params.toString()) url += `?${params.toString()}`;
    return this.request(url);
  }

  async updateNotice(noticeId: number, noticeData: Partial<Notice>): Promise<Notice> {
    return this.request(`/api/notices/${noticeId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(noticeData),
    });
  }

  async deleteNotice(noticeId: number): Promise<{message: string}> {
    try {
      const result = await this.request(`/api/notices/${noticeId}`, {
        method: 'DELETE',
      }, 2, 60000);
      return result;
    } catch (error) {
      console.error('Error deleting notice:', error);
      throw error;
    }
  }

  async previewNoticeEink(noticeData: {title: string, content: string, device_id: number}): Promise<{preview_url: string}> {
    const response = await fetch(`${API_BASE_URL}/api/notices/preview-eink`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(this.token ? { Authorization: `Bearer ${this.token}` } : {}),
      },
      body: JSON.stringify(noticeData),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }

  async getMonitoringDashboard(): Promise<any> {
    return this.request('/api/devices/monitoring/dashboard');
  }

  async listAlerts(params?: { device_id?: number; is_resolved?: boolean; severity?: string; limit?: number }): Promise<any[]> {
    const queryParams = new URLSearchParams();
    if (params?.device_id) queryParams.append('device_id', params.device_id.toString());
    if (params?.is_resolved !== undefined) queryParams.append('is_resolved', params.is_resolved.toString());
    if (params?.severity) queryParams.append('severity', params.severity);
    if (params?.limit) queryParams.append('limit', params.limit.toString());
    
    const query = queryParams.toString();
    return this.request(`/api/alerts${query ? `?${query}` : ''}`);
  }

  async resolveAlert(alertId: number, data: { resolution_note?: string }): Promise<any> {
    return this.request(`/api/alerts/${alertId}/resolve`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async issueRemoteCommand(deviceId: number, command: { command_type: string; command_data?: any }): Promise<any> {
    return this.request(`/api/devices/${deviceId}/commands`, {
      method: 'POST',
      body: JSON.stringify(command),
    });
  }

  async getDeviceHealthHistory(deviceId: number, hours: number = 24): Promise<any[]> {
    return this.request(`/api/devices/${deviceId}/health/history?hours=${hours}`);
  }

  async getDeviceCommands(deviceId: number, status?: string): Promise<any[]> {
    const query = status ? `?status=${status}` : '';
    return this.request(`/api/devices/${deviceId}/commands${query}`);
  }

  async getAlertStatistics(days: number = 7): Promise<any> {
    return this.request(`/api/alerts/statistics?days=${days}`);
  }

  async getCampaignPerformance(params?: {
    campaign_id?: number;
    device_id?: number;
    course_id?: number;
    start_date?: string;
    end_date?: string;
  }): Promise<any[]> {
    const queryParams = new URLSearchParams();
    if (params?.campaign_id) queryParams.append('campaign_id', params.campaign_id.toString());
    if (params?.device_id) queryParams.append('device_id', params.device_id.toString());
    if (params?.course_id) queryParams.append('course_id', params.course_id.toString());
    if (params?.start_date) queryParams.append('start_date', params.start_date);
    if (params?.end_date) queryParams.append('end_date', params.end_date);
    
    const query = queryParams.toString();
    return this.request(`/api/analytics/campaign-performance${query ? `?${query}` : ''}`);
  }

  async getDeviceUptimeReport(params?: {
    device_id?: number;
    course_id?: number;
    start_date?: string;
    end_date?: string;
  }): Promise<any[]> {
    const queryParams = new URLSearchParams();
    if (params?.device_id) queryParams.append('device_id', params.device_id.toString());
    if (params?.course_id) queryParams.append('course_id', params.course_id.toString());
    if (params?.start_date) queryParams.append('start_date', params.start_date);
    if (params?.end_date) queryParams.append('end_date', params.end_date);
    
    const query = queryParams.toString();
    return this.request(`/api/analytics/device-uptime${query ? `?${query}` : ''}`);
  }

  async getRevenueAnalytics(params?: {
    course_id?: number;
    region_id?: number;
    start_date?: string;
    end_date?: string;
  }): Promise<any[]> {
    const queryParams = new URLSearchParams();
    if (params?.course_id) queryParams.append('course_id', params.course_id.toString());
    if (params?.region_id) queryParams.append('region_id', params.region_id.toString());
    if (params?.start_date) queryParams.append('start_date', params.start_date);
    if (params?.end_date) queryParams.append('end_date', params.end_date);
    
    const query = queryParams.toString();
    return this.request(`/api/analytics/revenue${query ? `?${query}` : ''}`);
  }

  async getRevenueConfigurations(courseId: number): Promise<any[]> {
    return this.request(`/api/analytics/revenue-config/${courseId}`);
  }

  async createRevenueConfiguration(config: any): Promise<any> {
    return this.request('/api/analytics/revenue-config', {
      method: 'POST',
      body: JSON.stringify(config),
    });
  }

  async updateRevenueConfiguration(configId: number, config: any): Promise<any> {
    return this.request(`/api/analytics/revenue-config/${configId}`, {
      method: 'PUT',
      body: JSON.stringify(config),
    });
  }

  async deleteRevenueConfiguration(configId: number): Promise<{message: string}> {
    return this.request(`/api/analytics/revenue-config/${configId}`, {
      method: 'DELETE',
    });
  }

  async calculateRevenue(courseId: number, periodStart: string, periodEnd: string): Promise<any> {
    return this.request(`/api/analytics/revenue/calculate/${courseId}?period_start=${periodStart}&period_end=${periodEnd}`, {
      method: 'POST',
    });
  }

  async exportReportCSV(exportRequest: {
    report_type: string;
    export_format: string;
    date_range_start?: string;
    date_range_end?: string;
    course_ids?: number[];
    region_ids?: number[];
  }): Promise<Blob> {
    const url = `${API_BASE_URL}/api/analytics/export/csv`;
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    if (this.token) {
      headers.Authorization = `Bearer ${this.token}`;
    }

    const response = await fetch(url, {
      method: 'POST',
      headers,
      body: JSON.stringify(exportRequest),
    });

    if (response.status === 401) {
      if (this.token) {
        this.clearToken();
        localStorage.removeItem('user');
        if (!(window as any).__redirectingToLogin) {
          (window as any).__redirectingToLogin = true;
          const next = encodeURIComponent(window.location.href);
          window.location.replace(`/?next=${next}`);
        }
      }
      throw new Error('Unauthorized');
    }

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.blob();
  }

  async getAnalyticsDashboard(): Promise<any> {
    return this.request('/api/analytics/dashboard');
  }

  async createQRCode(qrCodeData: {
    campaign_id?: number;
    course_id: number;
    destination_url: string;
    title?: string;
    description?: string;
  }): Promise<any> {
    return this.request('/api/qr-codes', {
      method: 'POST',
      body: JSON.stringify(qrCodeData),
    });
  }

  async getQRCode(qrCodeId: number): Promise<any> {
    return this.request(`/api/qr-codes/${qrCodeId}`);
  }

  async getQRCodesByCampaign(campaignId: number): Promise<any[]> {
    return this.request(`/api/qr-codes/campaign/${campaignId}`);
  }

  async getQRCodesByCourse(courseId: number): Promise<any[]> {
    return this.request(`/api/qr-codes/course/${courseId}`);
  }

  async updateQRCode(qrCodeId: number, qrCodeData: {
    destination_url?: string;
    title?: string;
    description?: string;
    is_active?: boolean;
  }): Promise<any> {
    return this.request(`/api/qr-codes/${qrCodeId}`, {
      method: 'PUT',
      body: JSON.stringify(qrCodeData),
    });
  }

  async deleteQRCode(qrCodeId: number): Promise<{message: string}> {
    return this.request(`/api/qr-codes/${qrCodeId}`, {
      method: 'DELETE',
    });
  }

  async getQRCodePerformance(params?: {
    qr_code_id?: number;
    campaign_id?: number;
    course_id?: number;
    start_date?: string;
    end_date?: string;
  }): Promise<any[]> {
    const queryParams = new URLSearchParams();
    if (params?.qr_code_id) queryParams.append('qr_code_id', params.qr_code_id.toString());
    if (params?.campaign_id) queryParams.append('campaign_id', params.campaign_id.toString());
    if (params?.course_id) queryParams.append('course_id', params.course_id.toString());
    if (params?.start_date) queryParams.append('start_date', params.start_date);
    if (params?.end_date) queryParams.append('end_date', params.end_date);
    
    const query = queryParams.toString();
    return this.request(`/api/qr-codes/performance/report${query ? `?${query}` : ''}`);
  }

  async getDeviceTrends(deviceId: number, days: number = 7): Promise<any> {
    return this.request(`/api/devices/${deviceId}/trends?days=${days}`);
  }

  async getFleetTrends(days: number = 7, courseId?: number): Promise<any> {
    const query = courseId ? `?days=${days}&course_id=${courseId}` : `?days=${days}`;
    return this.request(`/api/devices/fleet/trends${query}`);
  }

  async issueBulkCommand(deviceIds: number[], commandType: string, commandData?: any): Promise<any> {
    return this.request('/api/devices/bulk/command', {
      method: 'POST',
      body: JSON.stringify({
        device_ids: deviceIds,
        command_type: commandType,
        command_data: commandData
      })
    });
  }

  async exportDevicesCSV(statusFilter?: string, courseId?: number): Promise<Blob> {
    const queryParams = new URLSearchParams();
    if (statusFilter) queryParams.append('status_filter', statusFilter);
    if (courseId) queryParams.append('course_id', courseId.toString());
    
    const query = queryParams.toString();
    const response = await fetch(`${API_BASE_URL}/api/devices/export/csv${query ? `?${query}` : ''}`, {
      headers: {
        'Authorization': `Bearer ${this.token}`
      }
    });
    
    if (response.status === 401) {
      if (this.token) {
        this.clearToken();
        localStorage.removeItem('user');
        if (!(window as any).__redirectingToLogin) {
          (window as any).__redirectingToLogin = true;
          const next = encodeURIComponent(window.location.href);
          window.location.replace(`/?next=${next}`);
        }
      }
      throw new Error('Unauthorized');
    }
    
    if (!response.ok) {
      throw new Error('Failed to export CSV');
    }
    
    return response.blob();
  }
}

export const apiClient = new ApiClient();
