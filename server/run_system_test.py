#!/usr/bin/env python3
"""
Complete system test for MCP-MQTT Bridge with proper path handling
"""

import os
import sys
import time
import signal
import subprocess
import threading
import socket
from pathlib import Path

# Ensure we're in the server directory
SCRIPT_DIR = Path(__file__).parent.absolute()
SERVER_DIR = SCRIPT_DIR
PROJECT_ROOT = SERVER_DIR.parent
os.chdir(SERVER_DIR)

# Add server directory to Python path
sys.path.insert(0, str(SERVER_DIR))

print(f"🔧 Working directory: {os.getcwd()}")
print(f"🔧 Server directory: {SERVER_DIR}")
print(f"🔧 Project root: {PROJECT_ROOT}")

def check_port_in_use(port):
    """Check if a port is already in use"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('localhost', port))
            return False
        except OSError:
            return True

def find_and_kill_mosquitto():
    """Find and kill any existing mosquitto processes on port 1883"""
    try:
        # Find processes using port 1883
        result = subprocess.run(['lsof', '-ti:1883'], capture_output=True, text=True)
        if result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                print(f"🔄 Killing process {pid} on port 1883")
                subprocess.run(['kill', '-9', pid], capture_output=True)
            time.sleep(2)
    except Exception as e:
        print(f"⚠️  Warning: Could not kill existing mosquitto processes: {e}")

def start_mosquitto():
    """Start mosquitto MQTT broker"""
    print("🚀 Starting Mosquitto MQTT broker...")
    
    # Kill any existing mosquitto on port 1883
    find_and_kill_mosquitto()
    
    # Start mosquitto in background
    try:
        proc = subprocess.Popen(
            ['mosquitto', '-v'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait a moment for startup
        time.sleep(3)
        
        # Check if it's running
        if proc.poll() is None:
            print("✅ Mosquitto started successfully")
            return proc
        else:
            stdout, stderr = proc.communicate()
            print(f"❌ Mosquitto failed to start:")
            print(f"STDOUT: {stdout}")
            print(f"STDERR: {stderr}")
            return None
            
    except FileNotFoundError:
        print("❌ Mosquitto not found. Please install it: sudo apt install mosquitto")
        return None
    except Exception as e:
        print(f"❌ Error starting mosquitto: {e}")
        return None

def start_mock_devices():
    """Start mock ESP32 devices"""
    print("🤖 Starting mock ESP32 devices...")
    
    # Ensure we have the virtual environment
    venv_python = SERVER_DIR / "venv" / "bin" / "python"
    if not venv_python.exists():
        print("❌ Virtual environment not found. Please run setup first.")
        return None
    
    try:
        # Start mock devices
        proc = subprocess.Popen(
            [str(venv_python), "examples/mock_esp32_device.py", "--devices", "2"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=SERVER_DIR
        )
        
        # Wait for startup
        time.sleep(5)
        
        if proc.poll() is None:
            print("✅ Mock devices started successfully")
            return proc
        else:
            stdout, stderr = proc.communicate()
            print(f"❌ Mock devices failed to start:")
            print(f"STDOUT: {stdout}")
            print(f"STDERR: {stderr}")
            return None
            
    except Exception as e:
        print(f"❌ Error starting mock devices: {e}")
        return None

def start_bridge():
    """Start the MCP-MQTT Bridge"""
    print("🌉 Starting MCP-MQTT Bridge...")
    
    venv_python = SERVER_DIR / "venv" / "bin" / "python"
    if not venv_python.exists():
        print("❌ Virtual environment not found.")
        return None
    
    try:
        proc = subprocess.Popen(
            [str(venv_python), "-m", "mcp_mqtt_bridge", 
             "--mqtt-broker", "localhost", 
             "--mqtt-port", "1883",
             "--db-path", "./data/bridge.db",
             "--log-level", "DEBUG"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=SERVER_DIR
        )
        
        # Wait for startup
        time.sleep(5)
        
        if proc.poll() is None:
            print("✅ MCP Bridge started successfully")
            return proc
        else:
            stdout, stderr = proc.communicate()
            print(f"❌ Bridge failed to start:")
            print(f"STDOUT: {stdout}")
            print(f"STDERR: {stderr}")
            return None
            
    except Exception as e:
        print(f"❌ Error starting bridge: {e}")
        return None

def run_integration_test():
    """Run the integration test"""
    print("🧪 Running integration test...")
    
    venv_python = SERVER_DIR / "venv" / "bin" / "python"
    
    try:
        result = subprocess.run(
            [str(venv_python), "test_running_system.py"],
            capture_output=True,
            text=True,
            cwd=SERVER_DIR,
            timeout=60
        )
        
        print("📊 Integration Test Results:")
        print("=" * 50)
        print(result.stdout)
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        print("=" * 50)
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("⏰ Integration test timed out")
        return False
    except Exception as e:
        print(f"❌ Error running integration test: {e}")
        return False

def cleanup_processes(processes):
    """Clean up all started processes"""
    print("🧹 Cleaning up processes...")
    
    for name, proc in processes.items():
        if proc and proc.poll() is None:
            print(f"🔄 Stopping {name}...")
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print(f"🔨 Force killing {name}...")
                proc.kill()
    
    # Additional cleanup for mosquitto
    find_and_kill_mosquitto()

def main():
    """Main test execution"""
    print("🚀 Starting MCP-MQTT Bridge System Test")
    print("=" * 60)
    
    processes = {}
    
    try:
        # Check if we're in virtual environment
        venv_python = SERVER_DIR / "venv" / "bin" / "python"
        if not venv_python.exists():
            print("❌ Virtual environment not found!")
            print("Please run: python -m venv venv && source venv/bin/activate && pip install -e .")
            return False
        
        # Step 1: Start Mosquitto
        mosquitto_proc = start_mosquitto()
        if not mosquitto_proc:
            return False
        processes['mosquitto'] = mosquitto_proc
        
        # Step 2: Start Mock Devices
        devices_proc = start_mock_devices()
        if not devices_proc:
            return False
        processes['mock_devices'] = devices_proc
        
        # Step 3: Start Bridge
        bridge_proc = start_bridge()
        if not bridge_proc:
            return False
        processes['bridge'] = bridge_proc
        
        # Step 4: Wait for everything to settle
        print("⏱️  Waiting for all services to stabilize...")
        time.sleep(10)
        
        # Step 5: Run Integration Test
        test_success = run_integration_test()
        
        if test_success:
            print("🎉 System test PASSED!")
            return True
        else:
            print("❌ System test FAILED!")
            return False
            
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
        return False
    except Exception as e:
        print(f"💥 Unexpected error: {e}")
        return False
    finally:
        cleanup_processes(processes)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 