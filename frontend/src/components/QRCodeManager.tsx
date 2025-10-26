import React, { useState, useEffect } from 'react';
import { apiClient } from '../lib/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Textarea } from './ui/textarea';
import { Switch } from './ui/switch';
import { QrCode, Download, ExternalLink, Trash2, Edit, Plus } from 'lucide-react';

interface QRCode {
  id: number;
  qr_code_key: string;
  campaign_id?: number;
  course_id: number;
  destination_url: string;
  title?: string;
  description?: string;
  qr_code_image: string;
  is_active: boolean;
  created_at: string;
  total_scans?: number;
  unique_visitors?: number;
}

interface QRCodeManagerProps {
  courseId?: number;
  campaignId?: number;
  onQRCodeCreated?: (qrCode: QRCode) => void;
}

export const QRCodeManager: React.FC<QRCodeManagerProps> = ({ 
  courseId, 
  campaignId,
  onQRCodeCreated 
}) => {
  const [qrCodes, setQRCodes] = useState<QRCode[]>([]);
  const [loading, setLoading] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingQRCode, setEditingQRCode] = useState<QRCode | null>(null);
  const [formData, setFormData] = useState({
    destination_url: '',
    title: '',
    description: '',
  });

  useEffect(() => {
    loadQRCodes();
  }, [courseId, campaignId]);

  const loadQRCodes = async () => {
    if (!courseId && !campaignId) return;
    
    setLoading(true);
    try {
      let codes: QRCode[];
      if (campaignId) {
        codes = await apiClient.getQRCodesByCampaign(campaignId);
      } else if (courseId) {
        codes = await apiClient.getQRCodesByCourse(courseId);
      } else {
        codes = [];
      }
      setQRCodes(codes);
    } catch (error) {
      console.error('Error loading QR codes:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateQRCode = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!courseId) return;

    setLoading(true);
    try {
      const qrCode = await apiClient.createQRCode({
        campaign_id: campaignId,
        course_id: courseId,
        destination_url: formData.destination_url,
        title: formData.title || undefined,
        description: formData.description || undefined,
      });

      setQRCodes([...qrCodes, qrCode]);
      setFormData({ destination_url: '', title: '', description: '' });
      setShowCreateForm(false);
      
      if (onQRCodeCreated) {
        onQRCodeCreated(qrCode);
      }
    } catch (error) {
      console.error('Error creating QR code:', error);
      alert('Failed to create QR code');
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateQRCode = async (qrCodeId: number, updates: Partial<QRCode>) => {
    setLoading(true);
    try {
      const updated = await apiClient.updateQRCode(qrCodeId, {
        destination_url: updates.destination_url,
        title: updates.title,
        description: updates.description,
        is_active: updates.is_active,
      });

      setQRCodes(qrCodes.map(qr => qr.id === qrCodeId ? updated : qr));
      setEditingQRCode(null);
    } catch (error) {
      console.error('Error updating QR code:', error);
      alert('Failed to update QR code');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteQRCode = async (qrCodeId: number) => {
    if (!confirm('Are you sure you want to delete this QR code? This action cannot be undone.')) {
      return;
    }

    setLoading(true);
    try {
      await apiClient.deleteQRCode(qrCodeId);
      setQRCodes(qrCodes.filter(qr => qr.id !== qrCodeId));
    } catch (error) {
      console.error('Error deleting QR code:', error);
      alert('Failed to delete QR code');
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadQRCode = (qrCode: QRCode) => {
    const link = document.createElement('a');
    link.href = qrCode.qr_code_image;
    link.download = `qr-code-${qrCode.qr_code_key}.png`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    alert('Copied to clipboard!');
  };

  if (loading && qrCodes.length === 0) {
    return <div className="text-center py-8">Loading QR codes...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold flex items-center gap-2">
            <QrCode className="h-6 w-6" />
            QR Code Manager
          </h2>
          <p className="text-gray-600 mt-1">
            Generate and manage QR codes with built-in analytics tracking
          </p>
        </div>
        <Button
          onClick={() => setShowCreateForm(!showCreateForm)}
          disabled={!courseId}
        >
          <Plus className="h-4 w-4 mr-2" />
          Create QR Code
        </Button>
      </div>

      {showCreateForm && (
        <Card>
          <CardHeader>
            <CardTitle>Create New QR Code</CardTitle>
            <CardDescription>
              Generate a trackable QR code that redirects to your destination URL
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleCreateQRCode} className="space-y-4">
              <div>
                <Label htmlFor="destination_url">Destination URL *</Label>
                <Input
                  id="destination_url"
                  type="url"
                  placeholder="https://example.com/landing-page"
                  value={formData.destination_url}
                  onChange={(e) => setFormData({ ...formData, destination_url: e.target.value })}
                  required
                />
                <p className="text-sm text-gray-500 mt-1">
                  Where users will be redirected after scanning the QR code
                </p>
              </div>

              <div>
                <Label htmlFor="title">Title (Optional)</Label>
                <Input
                  id="title"
                  placeholder="Summer Campaign QR Code"
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                />
              </div>

              <div>
                <Label htmlFor="description">Description (Optional)</Label>
                <Textarea
                  id="description"
                  placeholder="QR code for summer promotion campaign..."
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  rows={3}
                />
              </div>

              <div className="flex gap-2">
                <Button type="submit" disabled={loading}>
                  {loading ? 'Creating...' : 'Create QR Code'}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => {
                    setShowCreateForm(false);
                    setFormData({ destination_url: '', title: '', description: '' });
                  }}
                >
                  Cancel
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {qrCodes.length === 0 && !showCreateForm ? (
        <Card>
          <CardContent className="text-center py-12">
            <QrCode className="h-16 w-16 mx-auto text-gray-400 mb-4" />
            <h3 className="text-lg font-semibold mb-2">No QR Codes Yet</h3>
            <p className="text-gray-600 mb-4">
              Create your first QR code to start tracking scans and analytics
            </p>
            <Button onClick={() => setShowCreateForm(true)} disabled={!courseId}>
              <Plus className="h-4 w-4 mr-2" />
              Create QR Code
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {qrCodes.map((qrCode) => (
            <Card key={qrCode.id} className={!qrCode.is_active ? 'opacity-60' : ''}>
              <CardHeader>
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <CardTitle className="text-lg">
                      {qrCode.title || `QR Code ${qrCode.qr_code_key.substring(0, 8)}`}
                    </CardTitle>
                    <CardDescription className="mt-1">
                      {qrCode.description || 'No description'}
                    </CardDescription>
                  </div>
                  <div className="flex gap-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setEditingQRCode(qrCode)}
                    >
                      <Edit className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDeleteQRCode(qrCode.id)}
                    >
                      <Trash2 className="h-4 w-4 text-red-500" />
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex justify-center bg-white p-4 rounded border">
                  <img
                    src={qrCode.qr_code_image}
                    alt={`QR Code for ${qrCode.title || qrCode.destination_url}`}
                    className="w-48 h-48"
                  />
                </div>

                <div className="space-y-2 text-sm">
                  <div>
                    <span className="font-semibold">Destination:</span>
                    <div className="flex items-center gap-2 mt-1">
                      <a
                        href={qrCode.destination_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:underline truncate flex-1"
                      >
                        {qrCode.destination_url}
                      </a>
                      <ExternalLink className="h-4 w-4 text-gray-400 flex-shrink-0" />
                    </div>
                  </div>

                  <div>
                    <span className="font-semibold">Short URL:</span>
                    <div className="flex items-center gap-2 mt-1">
                      <code className="text-xs bg-gray-100 px-2 py-1 rounded flex-1 truncate">
                        {window.location.origin}/qr/{qrCode.qr_code_key}
                      </code>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => copyToClipboard(`${window.location.origin}/qr/${qrCode.qr_code_key}`)}
                      >
                        Copy
                      </Button>
                    </div>
                  </div>

                  {(qrCode.total_scans !== undefined || qrCode.unique_visitors !== undefined) && (
                    <div className="flex gap-4 pt-2 border-t">
                      <div>
                        <div className="text-2xl font-bold">{qrCode.total_scans || 0}</div>
                        <div className="text-gray-600">Total Scans</div>
                      </div>
                      <div>
                        <div className="text-2xl font-bold">{qrCode.unique_visitors || 0}</div>
                        <div className="text-gray-600">Unique Visitors</div>
                      </div>
                    </div>
                  )}
                </div>

                <div className="flex items-center justify-between pt-2 border-t">
                  <div className="flex items-center gap-2">
                    <Switch
                      checked={qrCode.is_active}
                      onCheckedChange={(checked) => 
                        handleUpdateQRCode(qrCode.id, { is_active: checked })
                      }
                    />
                    <span className="text-sm">
                      {qrCode.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleDownloadQRCode(qrCode)}
                  >
                    <Download className="h-4 w-4 mr-1" />
                    Download
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {editingQRCode && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <Card className="w-full max-w-md">
            <CardHeader>
              <CardTitle>Edit QR Code</CardTitle>
            </CardHeader>
            <CardContent>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  handleUpdateQRCode(editingQRCode.id, editingQRCode);
                }}
                className="space-y-4"
              >
                <div>
                  <Label htmlFor="edit_destination_url">Destination URL</Label>
                  <Input
                    id="edit_destination_url"
                    type="url"
                    value={editingQRCode.destination_url}
                    onChange={(e) =>
                      setEditingQRCode({ ...editingQRCode, destination_url: e.target.value })
                    }
                    required
                  />
                </div>

                <div>
                  <Label htmlFor="edit_title">Title</Label>
                  <Input
                    id="edit_title"
                    value={editingQRCode.title || ''}
                    onChange={(e) =>
                      setEditingQRCode({ ...editingQRCode, title: e.target.value })
                    }
                  />
                </div>

                <div>
                  <Label htmlFor="edit_description">Description</Label>
                  <Textarea
                    id="edit_description"
                    value={editingQRCode.description || ''}
                    onChange={(e) =>
                      setEditingQRCode({ ...editingQRCode, description: e.target.value })
                    }
                    rows={3}
                  />
                </div>

                <div className="flex gap-2">
                  <Button type="submit" disabled={loading}>
                    {loading ? 'Saving...' : 'Save Changes'}
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => setEditingQRCode(null)}
                  >
                    Cancel
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
};
