#!/usr/bin/env python3
"""
Basic MCP client example for MCP-MQTT Bridge.
Demonstrates how to connect to the bridge and use its tools.
"""
import asyncio
import sys
from pathlib import Path

# Add the parent directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    """Main function demonstrating basic MCP client usage."""
    print("🔌 MCP-MQTT Bridge Basic Client Example")
    print("=" * 50)
    
    # Server parameters for the MCP bridge
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "mcp_mqtt_bridge", "--config", "config/development.yaml"],
        env={}
    )
    
    try:
        # Connect to the MCP server
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize the session
                init_result = await session.initialize()
                print(f"✅ Connected to server: {init_result.server_info.name}")
                print(f"   Version: {init_result.server_info.version}")
                
                # List available tools
                tools = await session.list_tools()
                print(f"\n📋 Available tools ({len(tools.tools)}):")
                for tool in tools.tools:
                    print(f"  • {tool.name}: {tool.description}")
                
                # Example 1: List all devices
                print("\n🔍 Example 1: Listing all devices")
                try:
                    result = await session.call_tool("list_devices", {"online_only": False})
                    devices = result.content[0].text if result.content else "No devices found"
                    print(f"Result: {devices}")
                except Exception as e:
                    print(f"Error: {e}")
                
                # Example 2: Get device information
                print("\n🔍 Example 2: Getting device information")
                try:
                    # First get a device to query
                    devices_result = await session.call_tool("list_devices", {"online_only": True})
                    if devices_result.content and "esp32" in devices_result.content[0].text.lower():
                        # Extract first device ID (simplified parsing)
                        device_info = await session.call_tool("get_device_info", {
                            "device_id": "esp32_001"  # Example device ID
                        })
                        info = device_info.content[0].text if device_info.content else "No info found"
                        print(f"Device info: {info}")
                    else:
                        print("No ESP32 devices found online")
                except Exception as e:
                    print(f"Error: {e}")
                
                # Example 3: Read sensor data
                print("\n🔍 Example 3: Reading sensor data")
                try:
                    sensor_result = await session.call_tool("read_sensor", {
                        "device_id": "esp32_001",
                        "sensor_type": "temperature",
                        "history_minutes": 60
                    })
                    sensor_data = sensor_result.content[0].text if sensor_result.content else "No sensor data"
                    print(f"Sensor data: {sensor_data}")
                except Exception as e:
                    print(f"Error: {e}")
                
                # Example 4: Control an actuator
                print("\n🔍 Example 4: Controlling an actuator")
                try:
                    control_result = await session.call_tool("control_actuator", {
                        "device_id": "esp32_001",
                        "actuator_type": "led",
                        "action": "toggle"
                    })
                    control_response = control_result.content[0].text if control_result.content else "No response"
                    print(f"Control result: {control_response}")
                except Exception as e:
                    print(f"Error: {e}")
                
                # Example 5: Query devices by capability
                print("\n🔍 Example 5: Querying devices by capability")
                try:
                    query_result = await session.call_tool("query_devices", {
                        "sensor_type": "temperature",
                        "online_only": True
                    })
                    query_response = query_result.content[0].text if query_result.content else "No devices found"
                    print(f"Query result: {query_response}")
                except Exception as e:
                    print(f"Error: {e}")
                
                # Example 6: Get recent alerts
                print("\n🔍 Example 6: Getting recent alerts")
                try:
                    alerts_result = await session.call_tool("get_alerts", {
                        "severity_min": 1
                    })
                    alerts = alerts_result.content[0].text if alerts_result.content else "No alerts"
                    print(f"Recent alerts: {alerts}")
                except Exception as e:
                    print(f"Error: {e}")
                
                print("\n✅ Basic client example completed!")
                
    except Exception as e:
        print(f"❌ Connection error: {e}")
        print("Make sure the MCP-MQTT Bridge server is running")
        sys.exit(1)


def interactive_mode():
    """Interactive mode for manual testing."""
    print("\n🎮 Interactive Mode")
    print("Available commands:")
    print("  list - List all devices")
    print("  info <device_id> - Get device information")
    print("  read <device_id> <sensor_type> - Read sensor")
    print("  control <device_id> <actuator_type> <action> - Control actuator")
    print("  query <sensor_type> - Query devices by sensor type")
    print("  alerts - Get recent alerts")
    print("  quit - Exit interactive mode")
    
    while True:
        try:
            command = input("\n> ").strip().split()
            if not command:
                continue
            
            if command[0] == "quit":
                break
            elif command[0] == "list":
                print("Would call: list_devices")
            elif command[0] == "info" and len(command) > 1:
                print(f"Would call: get_device_info with device_id={command[1]}")
            elif command[0] == "read" and len(command) > 2:
                print(f"Would call: read_sensor with device_id={command[1]}, sensor_type={command[2]}")
            elif command[0] == "control" and len(command) > 3:
                print(f"Would call: control_actuator with device_id={command[1]}, actuator_type={command[2]}, action={command[3]}")
            elif command[0] == "query" and len(command) > 1:
                print(f"Would call: query_devices with sensor_type={command[1]}")
            elif command[0] == "alerts":
                print("Would call: get_alerts")
            else:
                print("Invalid command. Type 'quit' to exit.")
        except KeyboardInterrupt:
            break
    
    print("👋 Goodbye!")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Basic MCP client for MCP-MQTT Bridge")
    parser.add_argument("--interactive", "-i", action="store_true",
                       help="Run in interactive mode")
    
    args = parser.parse_args()
    
    if args.interactive:
        interactive_mode()
    else:
        asyncio.run(main()) 