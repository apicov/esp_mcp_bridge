#!/usr/bin/env python3
"""
Example MCP client for testing the IoT Bridge

This demonstrates how to interact with the MCP-MQTT bridge server
from an LLM or other MCP client.
"""

import asyncio
import json
from typing import Any, Dict
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def test_iot_bridge():
    """Test various IoT bridge operations"""
    
    # Connect to the MCP server
    server_params = StdioServerParameters(
        command="python",
        args=["mcp_mqtt_bridge.py"],
        env={"MQTT_BROKER": "localhost"}
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize connection
            await session.initialize()
            
            print("Connected to IoT Bridge MCP Server")
            print("=" * 50)
            
            # List available tools
            tools = await session.list_tools()
            print("\nAvailable tools:")
            for tool in tools:
                print(f"  - {tool.name}: {tool.description}")
            
            print("\n" + "=" * 50)
            
            # Example 1: List all devices
            print("\n1. Listing all IoT devices:")
            result = await session.call_tool("list_devices", {"online_only": False})
            devices = json.loads(result[0].text)
            print(f"Found {len(devices)} devices:")
            for device in devices:
                print(f"  - {device['device_id']}: {'Online' if device['online'] else 'Offline'}")
                print(f"    Sensors: {', '.join(device['sensors'])}")
                print(f"    Actuators: {', '.join(device['actuators'])}")
            
            # Example 2: Read sensor data
            if devices and devices[0]['sensors']:
                device_id = devices[0]['device_id']
                sensor = devices[0]['sensors'][0]
                
                print(f"\n2. Reading {sensor} from {device_id}:")
                result = await session.call_tool("read_sensor", {
                    "device_id": device_id,
                    "sensor_type": sensor,
                    "history_minutes": 30
                })
                sensor_data = json.loads(result[0].text)
                
                if sensor_data.get('current'):
                    current = sensor_data['current']
                    print(f"  Current value: {current['value']} {current.get('unit', '')}")
                    print(f"  Timestamp: {current['timestamp']}")
                
                if sensor_data.get('history'):
                    print(f"  Historical readings: {len(sensor_data['history'])}")
            
            # Example 3: Control an actuator
            led_device = None
            for device in devices:
                if 'led' in device['actuators']:
                    led_device = device['device_id']
                    break
            
            if led_device:
                print(f"\n3. Controlling LED on {led_device}:")
                
                # Toggle LED
                result = await session.call_tool("control_actuator", {
                    "device_id": led_device,
                    "actuator_type": "led",
                    "action": "toggle"
                })
                control_result = json.loads(result[0].text)
                print(f"  Toggle result: {control_result['status']}")
                
                # Set LED to specific state
                await asyncio.sleep(2)
                result = await session.call_tool("control_actuator", {
                    "device_id": led_device,
                    "actuator_type": "led",
                    "action": "write",
                    "value": "on"
                })
                control_result = json.loads(result[0].text)
                print(f"  Set to 'on' result: {control_result['status']}")
            
            # Example 4: Query devices by capability
            print("\n4. Finding all temperature sensors:")
            result = await session.call_tool("query_devices", {
                "sensor_type": "temperature",
                "online_only": True
            })
            query_result = json.loads(result[0].text)
            print(f"  Found {query_result['count']} devices with temperature sensors")
            for device in query_result['devices']:
                if 'temperature_value' in device:
                    print(f"  - {device['device_id']}: {device['temperature_value']}°C")
            
            # Example 5: Get alerts
            print("\n5. Checking for device alerts:")
            result = await session.call_tool("get_alerts", {
                "severity_min": 1  # Warning and above
            })
            alerts = json.loads(result[0].text)
            print(f"  Found {alerts['count']} alerts")
            for alert in alerts['alerts'][:5]:  # Show first 5
                print(f"  - [{alert['severity']}] {alert['device_id']}: {alert['message']}")

async def interactive_client():
    """Interactive client for testing"""
    
    server_params = StdioServerParameters(
        command="python",
        args=["mcp_mqtt_bridge.py"],
        env={"MQTT_BROKER": "localhost"}
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            print("IoT Bridge Interactive Client")
            print("Type 'help' for commands, 'quit' to exit")
            print("-" * 40)
            
            while True:
                try:
                    command = input("\n> ").strip().lower()
                    
                    if command == "quit":
                        break
                    elif command == "help":
                        print("Commands:")
                        print("  devices     - List all devices")
                        print("  read        - Read a sensor")
                        print("  control     - Control an actuator")
                        print("  query       - Query devices")
                        print("  alerts      - Show alerts")
                        print("  help        - Show this help")
                        print("  quit        - Exit")
                    elif command == "devices":
                        result = await session.call_tool("list_devices", {"online_only": False})
                        devices = json.loads(result[0].text)
                        print(json.dumps(devices, indent=2))
                    elif command == "read":
                        device_id = input("Device ID: ")
                        sensor = input("Sensor type: ")
                        result = await session.call_tool("read_sensor", {
                            "device_id": device_id,
                            "sensor_type": sensor
                        })
                        print(json.dumps(json.loads(result[0].text), indent=2))
                    elif command == "control":
                        device_id = input("Device ID: ")
                        actuator = input("Actuator type: ")
                        action = input("Action (read/write/toggle): ")
                        value = None
                        if action == "write":
                            value = input("Value: ")
                        result = await session.call_tool("control_actuator", {
                            "device_id": device_id,
                            "actuator_type": actuator,
                            "action": action,
                            "value": value
                        })
                        print(json.dumps(json.loads(result[0].text), indent=2))
                    elif command == "query":
                        sensor_type = input("Sensor type (or press Enter to skip): ")
                        actuator_type = input("Actuator type (or press Enter to skip): ")
                        args = {"online_only": True}
                        if sensor_type:
                            args["sensor_type"] = sensor_type
                        if actuator_type:
                            args["actuator_type"] = actuator_type
                        result = await session.call_tool("query_devices", args)
                        print(json.dumps(json.loads(result[0].text), indent=2))
                    elif command == "alerts":
                        result = await session.call_tool("get_alerts", {"severity_min": 0})
                        print(json.dumps(json.loads(result[0].text), indent=2))
                    else:
                        print("Unknown command. Type 'help' for available commands.")
                        
                except KeyboardInterrupt:
                    print("\nUse 'quit' to exit")
                except Exception as e:
                    print(f"Error: {e}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "interactive":
        asyncio.run(interactive_client())
    else:
        asyncio.run(test_iot_bridge())
