#!/usr/bin/env python3
"""
FastMCP Client Example

Demonstrates how to use the FastMCP bridge server programmatically
without a chat interface.

Usage:
    python fastmcp_client_example.py
"""

import asyncio
import json
import sys
import subprocess
from pathlib import Path
from typing import Any, Dict

# Add the package to Python path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
except ImportError:
    print("❌ MCP library not found. Install with: pip install mcp")
    sys.exit(1)


class FastMCPClient:
    """Example FastMCP client for programmatic IoT device control"""
    
    def __init__(self, bridge_command: list = None):
        self.bridge_command = bridge_command or [
            sys.executable, "fastmcp_bridge_server.py", 
            "--stdio", "--log-level", "ERROR"
        ]
        self.mcp_session: ClientSession = None
        self._stdio_context = None
        self.available_tools = []

    async def connect(self) -> bool:
        """Connect to the FastMCP bridge server"""
        try:
            print("🔗 Connecting to FastMCP bridge...")
            
            # Connect via stdio
            server_params = StdioServerParameters(
                command=self.bridge_command[0],
                args=self.bridge_command[1:],
                env=None
            )
            
            self._stdio_context = stdio_client(server_params)
            read, write = await self._stdio_context.__aenter__()
            self.mcp_session = ClientSession(read, write)
            
            # Initialize the connection
            await self.mcp_session.initialize()
            
            # List available tools
            tools_result = await self.mcp_session.list_tools()
            self.available_tools = [tool.name for tool in tools_result.tools]
            
            print(f"✅ Connected! Available tools: {self.available_tools}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to connect: {e}")
            return False

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any] = None) -> Any:
        """Call a FastMCP tool"""
        if not self.mcp_session:
            raise RuntimeError("Not connected to FastMCP bridge")
        
        arguments = arguments or {}
        
        try:
            print(f"🔧 Calling {tool_name} with arguments: {arguments}")
            
            result = await self.mcp_session.call_tool(tool_name, arguments)
            
            # Extract content from result
            if hasattr(result, 'content') and result.content:
                content = result.content[0]
                if hasattr(content, 'text'):
                    try:
                        return json.loads(content.text)
                    except json.JSONDecodeError:
                        return content.text
                else:
                    return str(content)
            else:
                return result
                
        except Exception as e:
            print(f"❌ Error calling {tool_name}: {e}")
            return {"error": str(e)}

    async def disconnect(self):
        """Disconnect from the FastMCP bridge"""
        try:
            if self._stdio_context:
                await self._stdio_context.__aexit__(None, None, None)
            print("✅ Disconnected from FastMCP bridge")
        except Exception as e:
            print(f"⚠️  Error disconnecting: {e}")

    # Convenience methods for common operations
    async def list_devices(self) -> list:
        """List all connected devices"""
        return await self.call_tool("list_devices")

    async def read_sensor(self, device_id: str, sensor_type: str) -> dict:
        """Read a specific sensor"""
        return await self.call_tool("read_sensor", {
            "device_id": device_id,
            "sensor_type": sensor_type
        })

    async def read_all_sensors(self, device_ids: list = None) -> dict:
        """Read all sensors from all or specific devices"""
        args = {}
        if device_ids:
            args["device_ids"] = device_ids
        return await self.call_tool("read_all_sensors", args)

    async def control_actuator(self, device_id: str, actuator_type: str, action: str) -> dict:
        """Control an actuator"""
        return await self.call_tool("control_actuator", {
            "device_id": device_id,
            "actuator_type": actuator_type,
            "action": action
        })

    async def get_system_status(self) -> dict:
        """Get overall system status"""
        return await self.call_tool("get_system_status")


async def demo_fastmcp_client():
    """Demonstrate FastMCP client usage"""
    print("🧪 FastMCP Client Demo")
    print("=" * 30)
    
    client = FastMCPClient()
    
    try:
        # Connect to bridge
        if not await client.connect():
            return 1
        
        print("\n📋 Running demo operations...")
        
        # 1. List devices
        print("\n1️⃣  Listing devices:")
        devices = await client.list_devices()
        print(f"   Found {len(devices) if isinstance(devices, list) else 0} devices")
        for device in (devices if isinstance(devices, list) else []):
            if isinstance(device, dict):
                print(f"   - {device.get('device_id', 'Unknown')}: {'Online' if device.get('is_online', False) else 'Offline'}")
        
        # 2. Get system status
        print("\n2️⃣  System status:")
        status = await client.get_system_status()
        if isinstance(status, dict):
            print(f"   Total devices: {status.get('total_devices', 0)}")
            print(f"   Online devices: {status.get('online_devices', 0)}")
            print(f"   System time: {status.get('system_timestamp', 'Unknown')}")
        
        # 3. Read all sensors (if devices exist)
        print("\n3️⃣  Reading all sensors:")
        sensor_data = await client.read_all_sensors()
        if isinstance(sensor_data, dict):
            devices_data = sensor_data.get('devices', {})
            if devices_data:
                for device_id, sensors in devices_data.items():
                    print(f"   Device {device_id}:")
                    if isinstance(sensors, dict):
                        for sensor, reading in sensors.items():
                            if isinstance(reading, dict) and 'value' in reading:
                                value = reading['value']
                                unit = reading.get('unit', '')
                                print(f"     - {sensor}: {value} {unit}")
                            else:
                                print(f"     - {sensor}: {reading}")
            else:
                print("   No device data available")
        
        # 4. Try controlling an actuator (will fail gracefully if no devices)
        print("\n4️⃣  Testing actuator control:")
        if devices and isinstance(devices, list) and len(devices) > 0:
            device_id = devices[0].get('device_id')
            actuators = devices[0].get('actuators', [])
            if actuators:
                actuator_type = actuators[0]
                result = await client.control_actuator(device_id, actuator_type, "on")
                print(f"   Control result: {result.get('status', 'Unknown')}")
            else:
                print("   No actuators found on first device")
        else:
            print("   No devices available for actuator control")
        
        print("\n✅ Demo completed successfully!")
        return 0
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        await client.disconnect()


async def main():
    """Main entry point"""
    return await demo_fastmcp_client()


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n👋 Demo interrupted")
        sys.exit(0)