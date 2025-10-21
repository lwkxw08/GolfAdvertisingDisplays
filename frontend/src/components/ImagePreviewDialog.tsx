import React from 'react';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from './ui/dialog';
import { Button } from './ui/button';
import { CheckCircle, XCircle, Info } from 'lucide-react';

interface ImagePreviewDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  previewData: {
    preview_image: string;
    image_info: any;
    e6_optimized: boolean;
  } | null;
  onApprove: () => void;
  onReject: () => void;
  loading?: boolean;
}

export const ImagePreviewDialog: React.FC<ImagePreviewDialogProps> = ({
  open,
  onOpenChange,
  previewData,
  onApprove,
  onReject,
  loading = false
}) => {
  if (!previewData) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <CheckCircle className="w-5 h-5 text-green-600" />
            E-ink Display Preview
          </DialogTitle>
          <DialogDescription>
            Preview how your image will appear on the Waveshare 13.3" E6 display (1200x1600, 6-color)
          </DialogDescription>
        </DialogHeader>
        
        <div className="space-y-4">
          <div className="flex justify-center bg-gray-100 p-4 rounded-lg">
            <img
              src={previewData.preview_image}
              alt="E6 Display Preview"
              className="max-w-full max-h-96 border-2 border-gray-300 rounded shadow-lg"
              style={{ aspectRatio: '3/4' }}
            />
          </div>
          
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Info className="w-4 h-4 text-blue-600" />
                <span className="font-medium">Display Information</span>
              </div>
              <div className="pl-6 space-y-1">
                <div>Resolution: 1200 × 1600 pixels</div>
                <div>Colors: 6-color E-ink Spectra</div>
                <div>Refresh Time: ~19 seconds</div>
              </div>
            </div>
            
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Info className="w-4 h-4 text-green-600" />
                <span className="font-medium">Optimization Applied</span>
              </div>
              <div className="pl-6 space-y-1">
                <div>✓ E6 color palette conversion</div>
                <div>✓ Contrast enhancement</div>
                <div>✓ Aspect ratio optimization</div>
              </div>
            </div>
          </div>
        </div>
        
        <DialogFooter>
          <Button
            variant="outline"
            onClick={onReject}
            disabled={loading}
            className="flex items-center gap-2"
          >
            <XCircle className="w-4 h-4" />
            Reject & Edit
          </Button>
          <Button
            onClick={onApprove}
            disabled={loading}
            className="flex items-center gap-2"
          >
            <CheckCircle className="w-4 h-4" />
            {loading ? 'Creating Campaign...' : 'Approve & Deploy'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
