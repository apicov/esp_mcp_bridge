#!/usr/bin/env python3
"""
Test script for already-running MCP-MQTT Bridge system
"""

import time
import sys
from pathlib import Path

# Add server directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from mcp_mqtt_bridge.database import DatabaseManager

def test_running_system():
    """Test the running system"""
    print("🧪 Testing Running MCP-MQTT Bridge System")
    print("=" * 50)
    
    try:
        # Test database
        print("1️⃣ Testing database...")
        db = DatabaseManager("./data/bridge.db")
        devices = db.get_all_devices()
        print(f"   📱 Found {len(devices)} devices")
        
        # Check for sensor data
        total_readings = 0
        for device in devices:
            readings = db.get_sensor_data(device['device_id'], "temperature", 30)
            total_readings += len(readings)
            if readings:
                print(f"   📊 {device['device_id']}: {len(readings)} temperature readings")
        
        print(f"   📈 Total readings: {total_readings}")
        db.close()
        
        if len(devices) > 0 and total_readings >= 0:
            print("🎉 System test PASSED!")
            return True
        else:
            print("❌ System test FAILED!")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_running_system()
    sys.exit(0 if success else 1) 