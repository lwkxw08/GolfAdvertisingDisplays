from typing import Dict, List, Optional, Tuple, Any
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import io
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class ImageProcessingService:
    """Service for processing images for E-ink displays"""
    
    E6_WIDTH = 1200
    E6_HEIGHT = 1600
    E6_COLORS = {
        'BLACK': (0, 0, 0),
        'WHITE': (255, 255, 255),
        'YELLOW': (255, 255, 0),
        'RED': (255, 0, 0),
        'BLUE': (0, 0, 255),
        'GREEN': (0, 255, 0)
    }
    
    def __init__(self):
        self.supported_formats = ['JPEG', 'PNG', 'BMP', 'TIFF']
        self.max_file_size = 5 * 1024 * 1024  # 5MB
    
    def process_image_for_e6(self, image_path: str, output_path: Optional[str] = None, orientation: str = 'portrait') -> str:
        """Process image for Waveshare E6 display"""
        try:
            with Image.open(image_path) as img:
                if img.format not in self.supported_formats:
                    raise ValueError(f"Unsupported format: {img.format}")
                
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                processed_img = self._resize_for_e6(img, orientation)
                
                e6_img = self._convert_to_e6_colors(processed_img)
                
                optimized_img = self._optimize_for_eink(e6_img)
                
                if not output_path:
                    base_name = os.path.splitext(image_path)[0]
                    output_path = f"{base_name}_e6.png"
                
                optimized_img.save(output_path, 'PNG', optimize=True)
                
                logger.info(f"Processed image for E6 ({orientation}): {image_path} -> {output_path}")
                return output_path
                
        except Exception as e:
            logger.error(f"Failed to process image {image_path}: {e}")
            raise
    
    def _resize_for_e6(self, img: Image.Image, orientation: str = 'portrait') -> Image.Image:
        """Resize image to E6 display dimensions with proper aspect ratio"""
        original_width, original_height = img.size
        
        if orientation == 'landscape':
            target_width, target_height = self.E6_HEIGHT, self.E6_WIDTH
        else:
            target_width, target_height = self.E6_WIDTH, self.E6_HEIGHT
        
        scale_w = target_width / original_width
        scale_h = target_height / original_height
        scale = min(scale_w, scale_h)
        
        new_width = int(original_width * scale)
        new_height = int(original_height * scale)
        
        resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        canvas = Image.new('RGB', (target_width, target_height), 'white')
        
        x_offset = (target_width - new_width) // 2
        y_offset = (target_height - new_height) // 2
        canvas.paste(resized_img, (x_offset, y_offset))
        
        return canvas
    
    def _convert_to_e6_colors(self, img: Image.Image) -> Image.Image:
        """Convert image to E6 Spectra 6-color palette"""
        palette_img = Image.new("P", (1, 1))
        
        palette_data = []
        for color_name, rgb in self.E6_COLORS.items():
            palette_data.extend(rgb)
        
        while len(palette_data) < 768:  # 256 colors * 3 values
            palette_data.extend([0, 0, 0])
        
        palette_img.putpalette(palette_data)
        
        quantized_img = img.quantize(palette=palette_img, dither=Image.Dither.FLOYDSTEINBERG)
        
        return quantized_img.convert('RGB')
    
    def _optimize_for_eink(self, img: Image.Image) -> Image.Image:
        """Optimize image for E-ink display characteristics"""
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.3)
        
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(1.2)
        
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(0.95)
        
        return img
    
    def create_notice_image(self, notice_data: Dict[str, Any], orientation: str = 'portrait') -> str:
        """Create optimized notice image for E-ink display"""
        try:
            if orientation == 'landscape':
                width, height = self.E6_HEIGHT, self.E6_WIDTH
            else:
                width, height = self.E6_WIDTH, self.E6_HEIGHT
            
            img = Image.new('RGB', (width, height), 'white')
            draw = ImageDraw.Draw(img)
            
            style = notice_data.get('style', {})
            font_size = style.get('font_size', 48)
            text_color = style.get('text_color', 'BLACK')
            bg_color = style.get('background_color', 'WHITE')
            text_align = style.get('text_align', 'center')
            
            text_rgb = self.E6_COLORS.get(text_color, self.E6_COLORS['BLACK'])
            bg_rgb = self.E6_COLORS.get(bg_color, self.E6_COLORS['WHITE'])
            
            if bg_color != 'WHITE':
                draw.rectangle([(0, 0), (width, height)], fill=bg_rgb)
            
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
            except:
                font = ImageFont.load_default()
            
            title = notice_data.get('title', '')
            content = notice_data.get('content', '')
            
            y_position = 100
            
            if title:
                title_lines = self._wrap_text(title, font, width - 100)
                for line in title_lines:
                    bbox = draw.textbbox((0, 0), line, font=font)
                    text_width = bbox[2] - bbox[0]
                    
                    if text_align == 'center':
                        x_position = (width - text_width) // 2
                    elif text_align == 'right':
                        x_position = width - text_width - 50
                    else:
                        x_position = 50
                    
                    draw.text((x_position, y_position), line, font=font, fill=text_rgb)
                    y_position += font_size + 10
                
                y_position += 30
            
            if content:
                content_font_size = max(font_size - 12, 24)
                try:
                    content_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", content_font_size)
                except:
                    content_font = font
                
                content_lines = self._wrap_text(content, content_font, width - 100)
                for line in content_lines:
                    bbox = draw.textbbox((0, 0), line, font=content_font)
                    text_width = bbox[2] - bbox[0]
                    
                    if text_align == 'center':
                        x_position = (width - text_width) // 2
                    elif text_align == 'right':
                        x_position = width - text_width - 50
                    else:
                        x_position = 50
                    
                    draw.text((x_position, y_position), line, font=content_font, fill=text_rgb)
                    y_position += content_font_size + 8
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            try:
                timestamp_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
            except:
                timestamp_font = font
            
            draw.text((50, height - 50), f"Updated: {timestamp}", 
                     font=timestamp_font, fill=text_rgb)
            
            optimized_img = self._optimize_for_eink(img)
            
            os.makedirs("uploads/previews", exist_ok=True)
            filename = f"notice_{notice_data.get('id', 'temp')}_{int(datetime.now().timestamp())}_e6.png"
            output_path = f"uploads/previews/{filename}"
            optimized_img.save(output_path, 'PNG', optimize=True)
            
            logger.info(f"Created notice image: {output_path}")
            return f"/uploads/previews/{filename}"
            
        except Exception as e:
            logger.error(f"Failed to create notice image: {e}")
            raise
    
    def _wrap_text(self, text: str, font: ImageFont.ImageFont, max_width: int) -> List[str]:
        """Wrap text to fit within specified width"""
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            bbox = font.getbbox(test_line)
            text_width = bbox[2] - bbox[0]
            
            if text_width <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    lines.append(word)
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines
    
    def get_image_info(self, image_path: str) -> Dict[str, Any]:
        """Get information about an image file"""
        try:
            with Image.open(image_path) as img:
                return {
                    'format': img.format,
                    'mode': img.mode,
                    'size': img.size,
                    'width': img.width,
                    'height': img.height,
                    'file_size': os.path.getsize(image_path),
                    'e6_compatible': img.format in self.supported_formats,
                    'needs_processing': img.size != (self.E6_WIDTH, self.E6_HEIGHT) or img.mode != 'RGB'
                }
        except Exception as e:
            logger.error(f"Failed to get image info for {image_path}: {e}")
            return {'error': str(e)}
    
    def batch_process_images(self, image_paths: List[str], output_dir: str) -> Dict[str, Any]:
        """Process multiple images for E6 display"""
        results = {
            'processed': [],
            'failed': [],
            'total': len(image_paths)
        }
        
        os.makedirs(output_dir, exist_ok=True)
        
        for image_path in image_paths:
            try:
                filename = os.path.basename(image_path)
                name, ext = os.path.splitext(filename)
                output_path = os.path.join(output_dir, f"{name}_e6.png")
                
                processed_path = self.process_image_for_e6(image_path, output_path)
                results['processed'].append({
                    'original': image_path,
                    'processed': processed_path,
                    'status': 'success'
                })
                
            except Exception as e:
                results['failed'].append({
                    'original': image_path,
                    'error': str(e),
                    'status': 'failed'
                })
        
        logger.info(f"Batch processing complete: {len(results['processed'])} success, {len(results['failed'])} failed")
        return results

    def preview_notice_eink(self, notice_data: Dict[str, Any], orientation: str = 'portrait') -> Dict[str, str]:
        """Generate preview of notice for E-ink display"""
        try:
            image_path = self.create_notice_image(notice_data, orientation=orientation)
            
            return {
                'preview_url': image_path,
                'orientation': orientation
            }
            
        except Exception as e:
            logger.error(f"Failed to generate notice preview: {e}")
            raise

image_processing_service = ImageProcessingService()
