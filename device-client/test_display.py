#!/usr/bin/env python3
"""
Hardware test script for Waveshare 13.3" E6 Display
Displays a timestamp and test pattern to verify the display is working
"""

import sys
import os
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

try:
    from waveshare_epd import epd13in3E
    EINK_AVAILABLE = True
except ImportError:
    print("WARNING: Waveshare library not found. Running in simulation mode.")
    EINK_AVAILABLE = False

def create_test_image():
    """Create a test image with timestamp and pattern"""
    width = 1200
    height = 1600
    
    image = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(image)
    
    try:
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 120)
        font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 60)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 40)
    except:
        print("Using default font")
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    draw.text((100, 200), "DISPLAY TEST", fill='black', font=font_large)
    draw.text((100, 400), timestamp, fill='black', font=font_medium)
    
    square_size = 100
    for row in range(8):
        for col in range(6):
            x = 100 + col * square_size
            y = 700 + row * square_size
            if (row + col) % 2 == 0:
                draw.rectangle([x, y, x + square_size, y + square_size], fill='black')
    
    draw.rectangle([50, 50, width-50, height-50], outline='black', width=10)
    
    draw.text((100, 600), "If you can see this, the display is working!", 
              fill='black', font=font_small)
    
    return image

def main():
    """Run the display test"""
    print("=" * 60)
    print("E-ink Display Hardware Test")
    print("=" * 60)
    
    if not EINK_AVAILABLE:
        print("\nERROR: Waveshare library not available")
        print("This test must be run on the Raspberry Pi with the display connected")
        return 1
    
    try:
        print("\n1. Initializing display...")
        epd = epd13in3E.EPD()
        epd.Init()
        print("   ✓ Display initialized")
        
        print("\n2. Clearing display...")
        epd.Clear()
        print("   ✓ Display cleared")
        
        print("\n3. Creating test image...")
        image = create_test_image()
        print("   ✓ Test image created")
        
        print("\n4. Displaying test image...")
        print("   (This will take about 6-10 seconds)")
        epd.display(epd.getbuffer(image))
        print("   ✓ Test image displayed")
        
        print("\n5. Putting display to sleep...")
        epd.sleep()
        print("   ✓ Display sleeping")
        
        print("\n" + "=" * 60)
        print("TEST COMPLETE!")
        print("=" * 60)
        print("\nYou should see:")
        print("  - 'DISPLAY TEST' in large text")
        print("  - Current timestamp")
        print("  - A checkerboard pattern")
        print("  - A black border around the edge")
        print("\nIf you don't see these, there may be a hardware issue.")
        print("=" * 60)
        
        return 0
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        print("\nTest failed. Check:")
        print("  1. Display is properly connected")
        print("  2. Waveshare library is correctly installed")
        print("  3. SPI is enabled (raspi-config)")
        return 1

if __name__ == '__main__':
    sys.exit(main())
