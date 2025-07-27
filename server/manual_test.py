#!/usr/bin/env python3
"""
Manual step-by-step test
"""

import subprocess
import time
import sys
import os
from pathlib import Path

# Ensure we're in server directory
os.chdir(Path(__file__).parent)
sys.path.insert(0, str(Path(__file__).parent))

def run_cmd(cmd, timeout=10):
    """Run a command and return success/output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Timeout"

def test_database():
    """Test database connectivity"""
    print("1. Testing Database...")
    try:
        from mcp_mqtt_bridge.database import DatabaseManager
        db = DatabaseManager("./data/bridge.db")
        devices = db.get_all_devices()
        print(f"   ✅ Database OK - {len(devices)} devices")
        db.close()
        return True
    except Exception as e:
        print(f"   ❌ Database failed: {e}")
        return False

def test_mqtt_connection():
    """Test MQTT client connection"""
    print("2. Testing MQTT Connection...")
    try:
        import paho.mqtt.client as mqtt
        
        connected = False
        def on_connect(client, userdata, flags, rc, properties=None):
            nonlocal connected
            connected = (rc == 0)
        
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="test_client")
        client.on_connect = on_connect
        client.connect("localhost", 1883, 60)
        client.loop_start()
        
        # Wait for connection
        for i in range(10):
            if connected:
                break
            time.sleep(0.5)
        
        client.disconnect()
        client.loop_stop()
        
        if connected:
            print("   ✅ MQTT connection OK")
            return True
        else:
            print("   ❌ MQTT connection failed")
            return False
            
    except Exception as e:
        print(f"   ❌ MQTT test failed: {e}")
        return False

def test_mock_device_direct():
    """Test mock device directly"""
    print("3. Testing Mock Device...")
    
    # Start mock device for short time
    success, stdout, stderr = run_cmd("timeout 5 python examples/mock_esp32_device.py --devices 1", timeout=6)
    
    if "Starting mock ESP32 device" in stdout or "Starting mock ESP32 device" in stderr:
        print("   ✅ Mock device started")
        return True
    else:
        print(f"   ❌ Mock device failed")
        print(f"   STDOUT: {stdout[:200]}")
        print(f"   STDERR: {stderr[:200]}")
        return False

def main():
    print("🔧 Manual Component Testing")
    print("=" * 40)
    
    # Ensure data directory exists
    os.makedirs("data", exist_ok=True)
    
    tests = [
        test_database,
        test_mqtt_connection,
        test_mock_device_direct,
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    print("\n📊 Test Results:")
    print(f"   🟢 Passed: {sum(results)}")
    print(f"   🔴 Failed: {len(results) - sum(results)}")
    
    if all(results):
        print("🎉 All components working!")
        return True
    else:
        print("❌ Some components failed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 