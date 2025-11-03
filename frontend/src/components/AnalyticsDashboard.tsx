import React, { useState, useEffect } from 'react';
import { apiClient } from '../lib/api';

interface AnalyticsDashboardProps {
  courseId?: number;
}

export function AnalyticsDashboard({ courseId }: AnalyticsDashboardProps) {
  const [activeTab, setActiveTab] = useState<'overview' | 'campaigns' | 'devices' | 'revenue' | 'proofofplay'>('overview');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const [dashboardData, setDashboardData] = useState<any>(null);
  const [campaignData, setCampaignData] = useState<any[]>([]);
  const [deviceUptimeData, setDeviceUptimeData] = useState<any[]>([]);
  const [revenueData, setRevenueData] = useState<any[]>([]);
  const [revenueConfigs, setRevenueConfigs] = useState<any[]>([]);
  
  const [popCampaignFilter, setPopCampaignFilter] = useState<number | null>(null);
  const [popDeviceFilter, setPopDeviceFilter] = useState<number | null>(null);
  const [popIncludeQR, setPopIncludeQR] = useState(false);
  const [popFormat, setPopFormat] = useState<'csv' | 'json'>('csv');
  const [campaigns, setCampaigns] = useState<any[]>([]);
  const [devices, setDevices] = useState<any[]>([]);
  
  const [dateRange, setDateRange] = useState({
    start: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    end: new Date().toISOString().split('T')[0]
  });
  
  const [showRevenueConfigDialog, setShowRevenueConfigDialog] = useState(false);
  const [editingConfig, setEditingConfig] = useState<any>(null);

  useEffect(() => {
    loadDashboardData();
    loadCampaignsAndDevices();
  }, [courseId]);
  
  const loadCampaignsAndDevices = async () => {
    try {
      const [campaignsData, devicesData] = await Promise.all([
        apiClient.getCampaigns(),
        apiClient.getDevices()
      ]);
      setCampaigns(campaignsData);
      setDevices(devicesData);
    } catch (err: any) {
      console.error('Failed to load campaigns/devices:', err);
    }
  };

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiClient.getAnalyticsDashboard();
      setDashboardData(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const loadCampaignPerformance = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiClient.getCampaignPerformance({
        course_id: courseId,
        start_date: dateRange.start,
        end_date: dateRange.end
      });
      setCampaignData(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const loadDeviceUptime = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiClient.getDeviceUptimeReport({
        course_id: courseId,
        start_date: dateRange.start,
        end_date: dateRange.end
      });
      setDeviceUptimeData(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const loadRevenueAnalytics = async () => {
    try {
      setLoading(true);
      setError(null);
      const [revenue, configs] = await Promise.all([
        apiClient.getRevenueAnalytics({
          course_id: courseId,
          start_date: dateRange.start,
          end_date: dateRange.end
        }),
        courseId ? apiClient.getRevenueConfigurations(courseId) : Promise.resolve([])
      ]);
      setRevenueData(revenue);
      setRevenueConfigs(configs);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'campaigns') {
      loadCampaignPerformance();
    } else if (activeTab === 'devices') {
      loadDeviceUptime();
    } else if (activeTab === 'revenue') {
      loadRevenueAnalytics();
    }
  }, [activeTab, dateRange, courseId]);

  const exportReport = async (reportType: string, format: 'csv' | 'pdf') => {
    try {
      setLoading(true);
      if (format === 'csv') {
        const blob = await apiClient.exportReportCSV({
          report_type: reportType,
          export_format: 'csv',
          date_range_start: dateRange.start,
          date_range_end: dateRange.end,
          course_ids: courseId ? [courseId] : undefined
        });
        
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${reportType}_${dateRange.start}_${dateRange.end}.csv`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      } else {
        alert('PDF export is not yet implemented. Please use CSV export.');
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const saveRevenueConfig = async (config: any) => {
    try {
      setLoading(true);
      if (editingConfig) {
        await apiClient.updateRevenueConfiguration(editingConfig.id, config);
      } else {
        await apiClient.createRevenueConfiguration({
          ...config,
          course_id: courseId
        });
      }
      setShowRevenueConfigDialog(false);
      setEditingConfig(null);
      loadRevenueAnalytics();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };
  
  const exportProofOfPlay = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const params = new URLSearchParams({
        format: popFormat,
        include_qr_analytics: popIncludeQR.toString(),
        start_date: dateRange.start,
        end_date: dateRange.end
      });
      
      if (popCampaignFilter) {
        params.append('campaign_id', popCampaignFilter.toString());
      }
      if (popDeviceFilter) {
        params.append('device_id', popDeviceFilter.toString());
      }
      
      const response = await fetch(`${import.meta.env.VITE_API_URL}/api/analytics/proof-of-play/export?${params}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      
      if (!response.ok) {
        throw new Error('Failed to export proof-of-play data');
      }
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `proof_of_play_${dateRange.start}_${dateRange.end}.${popFormat}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading && !dashboardData) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-600">Loading analytics...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold">Analytics & Reporting</h2>
        <div className="flex gap-2">
          <input
            type="date"
            value={dateRange.start}
            onChange={(e) => setDateRange({ ...dateRange, start: e.target.value })}
            className="px-3 py-2 border rounded"
          />
          <span className="flex items-center">to</span>
          <input
            type="date"
            value={dateRange.end}
            onChange={(e) => setDateRange({ ...dateRange, end: e.target.value })}
            className="px-3 py-2 border rounded"
          />
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      <div className="border-b border-gray-200">
        <nav className="flex space-x-8">
          <button
            onClick={() => setActiveTab('overview')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'overview'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Overview
          </button>
          <button
            onClick={() => setActiveTab('campaigns')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'campaigns'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Campaign Performance
          </button>
          <button
            onClick={() => setActiveTab('devices')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'devices'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Device Uptime
          </button>
          <button
            onClick={() => setActiveTab('revenue')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'revenue'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Revenue Analytics
          </button>
          <button
            onClick={() => setActiveTab('proofofplay')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'proofofplay'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Proof-of-Play Export
          </button>
        </nav>
      </div>

      {activeTab === 'overview' && dashboardData && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-white p-6 rounded-lg shadow">
              <div className="text-sm font-medium text-gray-500">Total Campaigns</div>
              <div className="mt-2 text-3xl font-semibold">{dashboardData.total_campaigns}</div>
              <div className="mt-1 text-sm text-gray-600">
                {dashboardData.active_campaigns} active
              </div>
            </div>
            
            <div className="bg-white p-6 rounded-lg shadow">
              <div className="text-sm font-medium text-gray-500">Total Impressions</div>
              <div className="mt-2 text-3xl font-semibold">{dashboardData.total_impressions.toLocaleString()}</div>
              <div className="mt-1 text-sm text-gray-600">Last 30 days</div>
            </div>
            
            <div className="bg-white p-6 rounded-lg shadow">
              <div className="text-sm font-medium text-gray-500">Device Uptime</div>
              <div className="mt-2 text-3xl font-semibold">{dashboardData.total_uptime_percentage.toFixed(1)}%</div>
              <div className="mt-1 text-sm text-gray-600">
                {dashboardData.online_devices} / {dashboardData.total_devices} online
              </div>
            </div>
            
            <div className="bg-white p-6 rounded-lg shadow">
              <div className="text-sm font-medium text-gray-500">Total Revenue</div>
              <div className="mt-2 text-3xl font-semibold">£{dashboardData.total_revenue.toFixed(2)}</div>
              <div className="mt-1 text-sm text-gray-600">
                Platform: £{dashboardData.platform_revenue.toFixed(2)}
              </div>
            </div>
          </div>

          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-lg font-semibold mb-4">Top Performing Campaigns</h3>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead>
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Campaign</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Device</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Impressions</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Rotations</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Avg/Day</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {dashboardData.top_performing_campaigns.map((campaign: any, index: number) => (
                    <tr key={index}>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">{campaign.campaign_name}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">{campaign.device_name}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">{campaign.total_impressions.toLocaleString()}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">{campaign.total_rotations}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">{campaign.avg_impressions_per_day.toFixed(1)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'campaigns' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-semibold">Campaign Performance Report</h3>
            <div className="flex gap-2">
              <button
                onClick={() => exportReport('campaign_performance', 'csv')}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                disabled={loading}
              >
                Export CSV
              </button>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow overflow-hidden">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Campaign</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Device</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Impressions</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Rotations</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Display Time (hrs)</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Avg/Day</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {campaignData.map((campaign, index) => (
                    <tr key={index}>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">{campaign.campaign_name}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">{campaign.device_name}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">{campaign.total_impressions.toLocaleString()}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">{campaign.total_rotations}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">{campaign.total_display_time_hours.toFixed(2)}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">{campaign.avg_impressions_per_day.toFixed(1)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'devices' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-semibold">Device Uptime Report</h3>
            <div className="flex gap-2">
              <button
                onClick={() => exportReport('device_uptime', 'csv')}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                disabled={loading}
              >
                Export CSV
              </button>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow overflow-hidden">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Device</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Course</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Uptime %</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Uptime (min)</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Downtime (min)</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Syncs</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Errors</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {deviceUptimeData.map((device, index) => (
                    <tr key={index}>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">{device.device_name}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">{device.course_name}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        <span className={`px-2 py-1 rounded ${
                          device.uptime_percentage >= 95 ? 'bg-green-100 text-green-800' :
                          device.uptime_percentage >= 80 ? 'bg-yellow-100 text-yellow-800' :
                          'bg-red-100 text-red-800'
                        }`}>
                          {device.uptime_percentage.toFixed(1)}%
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">{device.total_uptime_minutes.toLocaleString()}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">{device.total_downtime_minutes.toLocaleString()}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">{device.total_syncs}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        {device.total_errors > 0 ? (
                          <span className="text-red-600">{device.total_errors}</span>
                        ) : (
                          <span className="text-green-600">0</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'revenue' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-semibold">Revenue Analytics</h3>
            <div className="flex gap-2">
              {courseId && (
                <button
                  onClick={() => {
                    setEditingConfig(null);
                    setShowRevenueConfigDialog(true);
                  }}
                  className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
                >
                  Configure Revenue
                </button>
              )}
              <button
                onClick={() => exportReport('revenue_analytics', 'csv')}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                disabled={loading}
              >
                Export CSV
              </button>
            </div>
          </div>

          {revenueConfigs.length > 0 && (
            <div className="bg-blue-50 border border-blue-200 p-4 rounded">
              <h4 className="font-semibold mb-2">Current Revenue Configuration</h4>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <div className="text-gray-600">Device Cost/Month</div>
                  <div className="font-semibold">£{revenueConfigs[0].device_cost_per_month.toFixed(2)}</div>
                </div>
                <div>
                  <div className="text-gray-600">Sponsorship Revenue/Month</div>
                  <div className="font-semibold">£{revenueConfigs[0].sponsorship_revenue_per_month.toFixed(2)}</div>
                </div>
                <div>
                  <div className="text-gray-600">Course Split</div>
                  <div className="font-semibold">{revenueConfigs[0].course_revenue_split_percentage.toFixed(0)}%</div>
                </div>
                <div>
                  <div className="text-gray-600">Platform Split</div>
                  <div className="font-semibold">{revenueConfigs[0].platform_revenue_split_percentage.toFixed(0)}%</div>
                </div>
              </div>
            </div>
          )}

          <div className="bg-white rounded-lg shadow overflow-hidden">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Course</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Period</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Device Costs</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Sponsorship Revenue</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Course Share</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Platform Share</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Net Revenue</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {revenueData.map((revenue, index) => (
                    <tr key={index}>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">{revenue.course_name}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        {revenue.period_start} to {revenue.period_end}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">£{revenue.total_device_costs.toFixed(2)}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">£{revenue.total_sponsorship_revenue.toFixed(2)}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">£{revenue.course_revenue_share.toFixed(2)}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">£{revenue.platform_revenue_share.toFixed(2)}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        <span className={revenue.net_revenue >= 0 ? 'text-green-600' : 'text-red-600'}>
                          £{revenue.net_revenue.toFixed(2)}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'proofofplay' && (
        <div className="space-y-6">
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-lg font-semibold mb-4">Export Proof-of-Play Logs</h3>
            <p className="text-sm text-gray-600 mb-6">
              Export detailed proof-of-play logs for sponsor reporting and compliance. 
              Each record includes display timestamp, duration, image hash, and device metadata.
            </p>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Campaign Filter (Optional)
                </label>
                <select
                  value={popCampaignFilter || ''}
                  onChange={(e) => setPopCampaignFilter(e.target.value ? parseInt(e.target.value) : null)}
                  className="w-full px-3 py-2 border rounded"
                >
                  <option value="">All Campaigns</option>
                  {campaigns.map((campaign) => (
                    <option key={campaign.id} value={campaign.id}>
                      {campaign.sponsor_name}
                    </option>
                  ))}
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Device Filter (Optional)
                </label>
                <select
                  value={popDeviceFilter || ''}
                  onChange={(e) => setPopDeviceFilter(e.target.value ? parseInt(e.target.value) : null)}
                  className="w-full px-3 py-2 border rounded"
                >
                  <option value="">All Devices</option>
                  {devices.map((device) => (
                    <option key={device.id} value={device.id}>
                      {device.device_id}
                    </option>
                  ))}
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Export Format
                </label>
                <select
                  value={popFormat}
                  onChange={(e) => setPopFormat(e.target.value as 'csv' | 'json')}
                  className="w-full px-3 py-2 border rounded"
                >
                  <option value="csv">CSV</option>
                  <option value="json">JSON</option>
                </select>
              </div>
              
              <div className="flex items-end">
                <label className="flex items-center space-x-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={popIncludeQR}
                    onChange={(e) => setPopIncludeQR(e.target.checked)}
                    className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                  />
                  <span className="text-sm font-medium text-gray-700">
                    Include QR Analytics
                  </span>
                </label>
              </div>
            </div>
            
            <div className="flex justify-between items-center pt-4 border-t">
              <div className="text-sm text-gray-600">
                Date Range: {dateRange.start} to {dateRange.end}
                {popCampaignFilter && <span className="ml-2">• Campaign filtered</span>}
                {popDeviceFilter && <span className="ml-2">• Device filtered</span>}
                {popIncludeQR && <span className="ml-2">• QR analytics included</span>}
              </div>
              <button
                onClick={exportProofOfPlay}
                disabled={loading}
                className="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
              >
                {loading ? 'Exporting...' : `Export ${popFormat.toUpperCase()}`}
              </button>
            </div>
          </div>
          
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h4 className="font-semibold text-blue-900 mb-2">About Proof-of-Play Logs</h4>
            <ul className="text-sm text-blue-800 space-y-1">
              <li>• <strong>Event ID:</strong> Unique identifier for each display event</li>
              <li>• <strong>Image Hash:</strong> SHA-256 cryptographic verification of displayed content</li>
              <li>• <strong>Duration:</strong> Actual measured display time (not estimated)</li>
              <li>• <strong>Metadata:</strong> Connectivity type, power mode, firmware version</li>
              <li>• <strong>QR Analytics:</strong> When enabled, includes QR code scan counts per campaign</li>
              <li>• <strong>Limit:</strong> Maximum 10,000 records per export</li>
            </ul>
          </div>
        </div>
      )}

      {showRevenueConfigDialog && (
        <RevenueConfigDialog
          config={editingConfig}
          onSave={saveRevenueConfig}
          onCancel={() => {
            setShowRevenueConfigDialog(false);
            setEditingConfig(null);
          }}
        />
      )}
    </div>
  );
}

interface RevenueConfigDialogProps {
  config: any;
  onSave: (config: any) => void;
  onCancel: () => void;
}

function RevenueConfigDialog({ config, onSave, onCancel }: RevenueConfigDialogProps) {
  const [formData, setFormData] = useState({
    device_cost_per_month: config?.device_cost_per_month || 0,
    sponsorship_revenue_per_month: config?.sponsorship_revenue_per_month || 0,
    course_revenue_split_percentage: config?.course_revenue_split_percentage || 50,
    platform_revenue_split_percentage: config?.platform_revenue_split_percentage || 50,
    notes: config?.notes || '',
    effective_from: config?.effective_from || new Date().toISOString().split('T')[0],
    effective_to: config?.effective_to || ''
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(formData);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <h3 className="text-lg font-semibold mb-4">
          {config ? 'Edit Revenue Configuration' : 'Create Revenue Configuration'}
        </h3>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Device Cost per Month (£)
              </label>
              <input
                type="number"
                step="0.01"
                value={formData.device_cost_per_month}
                onChange={(e) => setFormData({ ...formData, device_cost_per_month: parseFloat(e.target.value) })}
                className="w-full px-3 py-2 border rounded"
                required
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Sponsorship Revenue per Month (£)
              </label>
              <input
                type="number"
                step="0.01"
                value={formData.sponsorship_revenue_per_month}
                onChange={(e) => setFormData({ ...formData, sponsorship_revenue_per_month: parseFloat(e.target.value) })}
                className="w-full px-3 py-2 border rounded"
                required
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Course Revenue Split (%)
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                max="100"
                value={formData.course_revenue_split_percentage}
                onChange={(e) => {
                  const value = parseFloat(e.target.value);
                  setFormData({
                    ...formData,
                    course_revenue_split_percentage: value,
                    platform_revenue_split_percentage: 100 - value
                  });
                }}
                className="w-full px-3 py-2 border rounded"
                required
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Platform Revenue Split (%)
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                max="100"
                value={formData.platform_revenue_split_percentage}
                onChange={(e) => {
                  const value = parseFloat(e.target.value);
                  setFormData({
                    ...formData,
                    platform_revenue_split_percentage: value,
                    course_revenue_split_percentage: 100 - value
                  });
                }}
                className="w-full px-3 py-2 border rounded"
                required
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Effective From
              </label>
              <input
                type="date"
                value={formData.effective_from}
                onChange={(e) => setFormData({ ...formData, effective_from: e.target.value })}
                className="w-full px-3 py-2 border rounded"
                required
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Effective To (optional)
              </label>
              <input
                type="date"
                value={formData.effective_to}
                onChange={(e) => setFormData({ ...formData, effective_to: e.target.value })}
                className="w-full px-3 py-2 border rounded"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Notes
            </label>
            <textarea
              value={formData.notes}
              onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              className="w-full px-3 py-2 border rounded"
              rows={3}
            />
          </div>

          <div className="flex justify-end gap-2 pt-4">
            <button
              type="button"
              onClick={onCancel}
              className="px-4 py-2 border rounded hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              Save Configuration
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
