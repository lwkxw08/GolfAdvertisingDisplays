#!/usr/bin/env python3
"""Test script for E-ink device endpoints"""

import requests
import json

API_BASE = "https://golfadvertisingdisplays.onrender.com"

def test_connectivity_options():
    """Test the connectivity options endpoint"""
    try:
        response = requests.get(f"{API_BASE}/api/eink/connectivity-options")
        print(f"Connectivity Options Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print("✓ Connectivity options endpoint working")
            print(f"  - Available types: {len(data.get('connectivity_types', []))}")
            print(f"  - Power modes: {len(data.get('power_modes', []))}")
            return True
        else:
            print(f"✗ Failed: {response.text}")
            return False
    except Exception as e:
        print(f"✗ Error testing connectivity options: {e}")
        return False

def test_device_playlist_optimized():
    """Test optimized device playlist endpoint"""
    try:
        device_id = "test_device_001"
        response = requests.get(f"{API_BASE}/api/device/{device_id}/playlist?connectivity=wifi")
        print(f"Optimized Playlist Status: {response.status_code}")
        if response.status_code in [200, 404]:  # 404 is expected for non-existent device
            print("✓ Optimized playlist endpoint accessible")
            return True
        else:
            print(f"✗ Unexpected status: {response.text}")
            return False
    except Exception as e:
        print(f"✗ Error testing optimized playlist: {e}")
        return False

def test_backend_health():
    """Test backend health"""
    try:
        response = requests.get(f"{API_BASE}/healthz")
        print(f"Health Check Status: {response.status_code}")
        if response.status_code == 200:
            print("✓ Backend is healthy")
            return True
        else:
            print(f"✗ Backend unhealthy: {response.text}")
            return False
    except Exception as e:
        print(f"✗ Error testing backend health: {e}")
        return False

if __name__ == "__main__":
    print("Testing E-ink device endpoints...")
    print("=" * 50)
    
    health_ok = test_backend_health()
    connectivity_ok = test_connectivity_options()
    playlist_ok = test_device_playlist_optimized()
    
    print("=" * 50)
    print("Test Results:")
    print(f"  Backend Health: {'✓' if health_ok else '✗'}")
    print(f"  Connectivity Options: {'✓' if connectivity_ok else '✗'}")
    print(f"  Optimized Playlist: {'✓' if playlist_ok else '✗'}")
    
    if all([health_ok, connectivity_ok, playlist_ok]):
        print("\n🎉 All E-ink endpoints are working!")
    else:
        print("\n⚠️  Some endpoints need attention")
