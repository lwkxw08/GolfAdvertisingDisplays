const API_BASE_URL = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';

export interface User {
  id: number;
  email: string;
  role: 'admin' | 'client_tenant';
  course_id?: number;
  is_active: boolean;
  created_at: string;
}

export interface Course {
  id: number;
  name: string;
  location: string;
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
}

export const apiClient = new ApiClient();
