#!/usr/bin/env python3
"""
Test script demonstrating the MCP-MQTT Bridge with Mock ESP32 devices.

This script starts mock devices and demonstrates various testing scenarios.
"""

import asyncio
import json
import time
import logging
from pathlib import Path

from mock_esp32_device import MockDeviceManager
from basic_client import main as run_basic_client


async def test_scenario_1_basic_interaction():
    """Test basic device interaction"""
    print("\n🧪 Test Scenario 1: Basic Device Interaction")
    print("=" * 50)
    
    # This would typically involve:
    # 1. Start mock devices
    # 2. Wait for them to come online
    # 3. Test basic sensor reading
    # 4. Test actuator control
    # 5. Verify responses
    
    print("✅ Mock devices should be publishing sensor data")
    print("✅ Try controlling actuators via MQTT or MCP bridge")
    print("✅ Check device status and capabilities")


async def test_scenario_2_error_handling():
    """Test error handling and recovery"""
    print("\n🧪 Test Scenario 2: Error Handling")
    print("=" * 50)
    
    print("✅ Mock devices will occasionally simulate errors")
    print("✅ Test bridge error handling and logging")
    print("✅ Verify device reconnection after simulated failures")


async def test_scenario_3_performance():
    """Test system performance with multiple devices"""
    print("\n🧪 Test Scenario 3: Performance Testing")
    print("=" * 50)
    
    print("✅ Multiple devices publishing simultaneously")
    print("✅ Monitor message throughput and latency")
    print("✅ Test system stability under load")


async def run_demo_sequence():
    """Run a demonstration sequence"""
    print("\n🎬 Running Demo Sequence")
    print("=" * 30)
    
    # Wait for devices to initialize
    print("⏳ Waiting for devices to initialize...")
    await asyncio.sleep(5)
    
    # Demonstrate some interactions
    demo_steps = [
        "📊 Devices publishing sensor data",
        "🔧 Simulating actuator commands",
        "⚠️  Occasional error simulation",
        "📈 Performance monitoring",
        "🔄 Connection resilience testing"
    ]
    
    for i, step in enumerate(demo_steps, 1):
        print(f"Step {i}: {step}")
        await asyncio.sleep(3)  # Pause between demonstrations
    
    print("\n✅ Demo sequence complete!")


async def main():
    """Main test function"""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🚀 MCP-MQTT Bridge Mock Device Test")
    print("=" * 50)
    
    # Create mock device manager
    manager = MockDeviceManager()
    
    # Load configuration
    config_file = Path(__file__).parent / "mock_device_config.yaml"
    if config_file.exists():
        print(f"📋 Loading device config from {config_file}")
        manager.load_config(str(config_file))
    else:
        print("📋 Using default device configuration")
        manager.create_default_devices(3)
    
    print(f"📱 Created {len(manager.devices)} mock devices:")
    for device in manager.devices:
        sensors = [s.name for s in device.config.sensors]
        actuators = [a.name for a in device.config.actuators]
        print(f"  • {device.config.device_id} ({device.config.location})")
        print(f"    Sensors: {', '.join(sensors)}")
        print(f"    Actuators: {', '.join(actuators)}")
    
    print("\n🔗 MQTT Topics that will be used:")
    print("  📤 Published by devices:")
    print("    • devices/{device_id}/status")
    print("    • devices/{device_id}/capabilities")
    print("    • devices/{device_id}/sensors/{sensor_name}")
    print("    • devices/{device_id}/actuators/{actuator_name}/status")
    print("    • devices/{device_id}/error")
    print("  📥 Subscribed by devices:")
    print("    • devices/{device_id}/actuators/{actuator_name}/cmd")
    print("    • devices/{device_id}/cmd")
    
    print("\n🎯 Test Instructions:")
    print("1. Start an MQTT broker (e.g., mosquitto)")
    print("2. Start the MCP-MQTT bridge server")
    print("3. Connect an MCP client (like Claude Desktop)")
    print("4. Try these MCP commands:")
    print("   • list_devices")
    print("   • get_device_info with device_id='esp32_kitchen'")
    print("   • read_sensor with device_id='esp32_kitchen', sensor_type='temperature'")
    print("   • control_actuator with device_id='esp32_kitchen', actuator_type='led', action='toggle'")
    
    print("\n▶️  Starting mock devices...")
    
    # Start test scenarios in background
    asyncio.create_task(test_scenario_1_basic_interaction())
    asyncio.create_task(run_demo_sequence())
    
    # Start all devices (this will run until interrupted)
    try:
        await manager.start_all()
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        logging.exception("Test error")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!") 