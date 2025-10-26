import React, { useState, useEffect } from 'react';
import { apiClient } from '../lib/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Label } from './ui/label';
import { Input } from './ui/input';
import { 
  BarChart3, 
  TrendingUp, 
  Users, 
  Smartphone, 
  Monitor, 
  Tablet,
  MapPin,
  Calendar
} from 'lucide-react';

interface QRCodePerformance {
  qr_code_id: number;
  qr_code_key: string;
  title?: string;
  date: string;
  total_scans: number;
  unique_visitors: number;
  mobile_scans: number;
  desktop_scans: number;
  tablet_scans: number;
  top_countries: Array<{ country: string; count: number }>;
  top_cities: Array<{ city: string; count: number }>;
}

interface QRCodeAnalyticsProps {
  qrCodeId?: number;
  campaignId?: number;
  courseId?: number;
}

export const QRCodeAnalytics: React.FC<QRCodeAnalyticsProps> = ({
  qrCodeId,
  campaignId,
  courseId,
}) => {
  const [performance, setPerformance] = useState<QRCodePerformance[]>([]);
  const [loading, setLoading] = useState(false);
  const [dateRange, setDateRange] = useState({
    start_date: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    end_date: new Date().toISOString().split('T')[0],
  });

  useEffect(() => {
    loadPerformance();
  }, [qrCodeId, campaignId, courseId, dateRange]);

  const loadPerformance = async () => {
    setLoading(true);
    try {
      const data = await apiClient.getQRCodePerformance({
        qr_code_id: qrCodeId,
        campaign_id: campaignId,
        course_id: courseId,
        start_date: dateRange.start_date,
        end_date: dateRange.end_date,
      });
      setPerformance(data);
    } catch (error) {
      console.error('Error loading QR code performance:', error);
    } finally {
      setLoading(false);
    }
  };

  const calculateTotals = () => {
    return performance.reduce(
      (acc, day) => ({
        total_scans: acc.total_scans + day.total_scans,
        unique_visitors: acc.unique_visitors + day.unique_visitors,
        mobile_scans: acc.mobile_scans + day.mobile_scans,
        desktop_scans: acc.desktop_scans + day.desktop_scans,
        tablet_scans: acc.tablet_scans + day.tablet_scans,
      }),
      { total_scans: 0, unique_visitors: 0, mobile_scans: 0, desktop_scans: 0, tablet_scans: 0 }
    );
  };

  const getTopLocations = () => {
    const countryCounts: Record<string, number> = {};
    const cityCounts: Record<string, number> = {};

    performance.forEach((day) => {
      day.top_countries?.forEach((country) => {
        countryCounts[country.country] = (countryCounts[country.country] || 0) + country.count;
      });
      day.top_cities?.forEach((city) => {
        cityCounts[city.city] = (cityCounts[city.city] || 0) + city.count;
      });
    });

    const topCountries = Object.entries(countryCounts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5)
      .map(([country, count]) => ({ country, count }));

    const topCities = Object.entries(cityCounts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5)
      .map(([city, count]) => ({ city, count }));

    return { topCountries, topCities };
  };

  const totals = calculateTotals();
  const { topCountries, topCities } = getTopLocations();

  if (loading && performance.length === 0) {
    return <div className="text-center py-8">Loading analytics...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold flex items-center gap-2">
            <BarChart3 className="h-6 w-6" />
            QR Code Analytics
          </h2>
          <p className="text-gray-600 mt-1">
            Track scans, visitor behavior, and geographic distribution
          </p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Date Range</CardTitle>
          <CardDescription>Select the time period for analytics</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4 items-end">
            <div className="flex-1">
              <Label htmlFor="start_date">Start Date</Label>
              <Input
                id="start_date"
                type="date"
                value={dateRange.start_date}
                onChange={(e) => setDateRange({ ...dateRange, start_date: e.target.value })}
              />
            </div>
            <div className="flex-1">
              <Label htmlFor="end_date">End Date</Label>
              <Input
                id="end_date"
                type="date"
                value={dateRange.end_date}
                onChange={(e) => setDateRange({ ...dateRange, end_date: e.target.value })}
              />
            </div>
            <Button onClick={loadPerformance} disabled={loading}>
              {loading ? 'Loading...' : 'Update'}
            </Button>
          </div>
        </CardContent>
      </Card>

      {performance.length === 0 ? (
        <Card>
          <CardContent className="text-center py-12">
            <BarChart3 className="h-16 w-16 mx-auto text-gray-400 mb-4" />
            <h3 className="text-lg font-semibold mb-2">No Data Available</h3>
            <p className="text-gray-600">
              No QR code scans recorded for the selected period
            </p>
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Total Scans</CardTitle>
                <TrendingUp className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{totals.total_scans.toLocaleString()}</div>
                <p className="text-xs text-muted-foreground">
                  All QR code scans in period
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Unique Visitors</CardTitle>
                <Users className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{totals.unique_visitors.toLocaleString()}</div>
                <p className="text-xs text-muted-foreground">
                  {totals.total_scans > 0
                    ? `${((totals.unique_visitors / totals.total_scans) * 100).toFixed(1)}% of total scans`
                    : 'No scans yet'}
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Mobile Scans</CardTitle>
                <Smartphone className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{totals.mobile_scans.toLocaleString()}</div>
                <p className="text-xs text-muted-foreground">
                  {totals.total_scans > 0
                    ? `${((totals.mobile_scans / totals.total_scans) * 100).toFixed(1)}% of total`
                    : 'No scans yet'}
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Desktop Scans</CardTitle>
                <Monitor className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{totals.desktop_scans.toLocaleString()}</div>
                <p className="text-xs text-muted-foreground">
                  {totals.total_scans > 0
                    ? `${((totals.desktop_scans / totals.total_scans) * 100).toFixed(1)}% of total`
                    : 'No scans yet'}
                </p>
              </CardContent>
            </Card>
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Tablet Scans</CardTitle>
                <Tablet className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{totals.tablet_scans.toLocaleString()}</div>
                <p className="text-xs text-muted-foreground">
                  {totals.total_scans > 0
                    ? `${((totals.tablet_scans / totals.total_scans) * 100).toFixed(1)}% of total`
                    : 'No scans yet'}
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <MapPin className="h-4 w-4" />
                  Top Countries
                </CardTitle>
              </CardHeader>
              <CardContent>
                {topCountries.length > 0 ? (
                  <div className="space-y-2">
                    {topCountries.map((country, index) => (
                      <div key={index} className="flex justify-between items-center">
                        <span className="text-sm">{country.country || 'Unknown'}</span>
                        <span className="text-sm font-semibold">{country.count}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-gray-500">No location data</p>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <MapPin className="h-4 w-4" />
                  Top Cities
                </CardTitle>
              </CardHeader>
              <CardContent>
                {topCities.length > 0 ? (
                  <div className="space-y-2">
                    {topCities.map((city, index) => (
                      <div key={index} className="flex justify-between items-center">
                        <span className="text-sm">{city.city || 'Unknown'}</span>
                        <span className="text-sm font-semibold">{city.count}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-gray-500">No location data</p>
                )}
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Calendar className="h-5 w-5" />
                Daily Scan Trends
              </CardTitle>
              <CardDescription>Scans per day over the selected period</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {performance.slice(-14).map((day, index) => {
                  const maxScans = Math.max(...performance.map(d => d.total_scans));
                  const barWidth = maxScans > 0 ? (day.total_scans / maxScans) * 100 : 0;
                  
                  return (
                    <div key={index} className="flex items-center gap-4">
                      <div className="w-24 text-sm text-gray-600">
                        {new Date(day.date).toLocaleDateString('en-US', { 
                          month: 'short', 
                          day: 'numeric' 
                        })}
                      </div>
                      <div className="flex-1 bg-gray-100 rounded-full h-6 relative">
                        <div
                          className="bg-blue-500 h-6 rounded-full flex items-center justify-end pr-2"
                          style={{ width: `${barWidth}%` }}
                        >
                          {day.total_scans > 0 && (
                            <span className="text-xs text-white font-semibold">
                              {day.total_scans}
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="w-20 text-sm text-gray-600 text-right">
                        {day.unique_visitors} unique
                      </div>
                    </div>
                  );
                })}
              </div>
              {performance.length > 14 && (
                <p className="text-sm text-gray-500 mt-4 text-center">
                  Showing last 14 days. Total period: {performance.length} days
                </p>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
};
