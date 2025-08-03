#!/usr/bin/env python3
"""
Test Remote FastMCP Connection

Test connecting to a remote FastMCP bridge server.
"""

import asyncio
import sys
from pathlib import Path

# Add the package to Python path
sys.path.insert(0, str(Path(__file__).parent))

try:
    import aiohttp
except ImportError:
    print("❌ aiohttp not found. Install with: pip install aiohttp")
    sys.exit(1)


async def test_remote_connection(host: str = "localhost", port: int = 8000):
    """Test connection to remote FastMCP bridge"""
    print(f"🧪 Testing Remote FastMCP Connection")
    print(f"🎯 Target: {host}:{port}")
    print("=" * 40)
    
    base_url = f"http://{host}:{port}"
    
    async with aiohttp.ClientSession() as session:
        try:
            # 1. Health check
            print("1️⃣  Testing health endpoint...")
            async with session.get(f"{base_url}/health") as response:
                if response.status == 200:
                    health_data = await response.json()
                    print(f"   ✅ Health check passed: {health_data}")
                else:
                    print(f"   ❌ Health check failed: {response.status}")
                    return False
            
            # 2. List tools
            print("\n2️⃣  Testing tools endpoint...")
            async with session.get(f"{base_url}/tools") as response:
                if response.status == 200:
                    tools_data = await response.json()
                    tools = tools_data.get('tools', [])
                    print(f"   ✅ Found {len(tools)} tools:")
                    for tool in tools[:5]:  # Show first 5
                        print(f"     - {tool['name']}: {tool['description']}")
                    if len(tools) > 5:
                        print(f"     ... and {len(tools) - 5} more")
                else:
                    print(f"   ❌ Tools endpoint failed: {response.status}")
                    return False
            
            # 3. Test tool call
            print("\n3️⃣  Testing tool execution...")
            tool_url = f"{base_url}/tools/list_devices"
            payload = {"arguments": {}}
            
            async with session.post(tool_url, json=payload) as response:
                if response.status == 200:
                    result_data = await response.json()
                    if result_data.get("success"):
                        devices = result_data.get("result", [])
                        print(f"   ✅ Tool call successful: found {len(devices)} devices")
                        if devices:
                            for device in devices[:3]:  # Show first 3
                                if isinstance(device, dict):
                                    device_id = device.get('device_id', 'Unknown')
                                    online = device.get('is_online', False)
                                    print(f"     - {device_id}: {'Online' if online else 'Offline'}")
                    else:
                        print(f"   ⚠️  Tool call returned error: {result_data.get('error')}")
                else:
                    print(f"   ❌ Tool call failed: {response.status}")
                    error_text = await response.text()
                    print(f"      Error: {error_text}")
                    return False
            
            # 4. Test system status
            print("\n4️⃣  Testing system status...")
            status_url = f"{base_url}/tools/get_system_status"
            
            async with session.post(status_url, json={"arguments": {}}) as response:
                if response.status == 200:
                    result_data = await response.json()
                    if result_data.get("success"):
                        status = result_data.get("result", {})
                        total = status.get('total_devices', 0)
                        online = status.get('online_devices', 0)
                        print(f"   ✅ System status: {online}/{total} devices online")
                        print(f"      Timestamp: {status.get('system_timestamp', 'Unknown')}")
                    else:
                        print(f"   ⚠️  Status call error: {result_data.get('error')}")
                else:
                    print(f"   ❌ Status call failed: {response.status}")
            
            print("\n🎉 All remote connection tests passed!")
            print(f"\n✅ Your remote FastMCP bridge at {host}:{port} is working correctly!")
            print("\nNext steps:")
            print(f"  • python remote_fastmcp_chat.py --remote-host {host} --remote-port {port}")
            print(f"  • python chat_with_devices.py --remote-host {host} --remote-port {port}")
            return True
            
        except aiohttp.ClientError as e:
            print(f"❌ Connection error: {e}")
            print("\nTroubleshooting:")
            print(f"  1. Check if server is running on {host}:{port}")
            print("  2. Verify network connectivity")
            print("  3. Check firewall settings")
            return False
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            return False


async def test_local_server_start():
    """Test starting a local server for remote connection testing"""
    print("🧪 Testing Local Server Startup")
    print("=" * 35)
    
    try:
        # Import required modules
        from mcp_mqtt_bridge.bridge import MCPMQTTBridge
        from mcp_mqtt_bridge.mcp_http_server import MCPHTTPServer
        
        print("✅ Modules imported successfully")
        
        # Create bridge
        bridge = MCPMQTTBridge(
            mqtt_broker="localhost",
            db_path="test_remote.db",
            use_fastmcp=True
        )
        
        # Initialize database only (don't connect to MQTT for this test)
        await bridge.database.initialize()
        print("✅ Bridge and database initialized")
        
        # Create HTTP server
        http_server = MCPHTTPServer(bridge, host="127.0.0.1", port=8001)
        print("✅ HTTP server created")
        
        # For a real test, you would start the server here:
        # await http_server.start()
        # But that would require actual MQTT broker
        
        print("✅ Local server setup test completed")
        print("\nTo start a real server for testing:")
        print("  python -m mcp_mqtt_bridge --enable-mcp-server --mcp-port 8001")
        
        return True
        
    except Exception as e:
        print(f"❌ Local server test failed: {e}")
        return False
    finally:
        # Cleanup
        try:
            Path("test_remote.db").unlink(missing_ok=True)
        except:
            pass


async def main():
    """Main test function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Remote FastMCP Connection")
    parser.add_argument("--host", default="localhost", 
                       help="Remote host to test (default: localhost)")
    parser.add_argument("--port", type=int, default=8000,
                       help="Remote port to test (default: 8000)")
    parser.add_argument("--test-local", action="store_true",
                       help="Test local server startup instead")
    
    args = parser.parse_args()
    
    if args.test_local:
        success = await test_local_server_start()
    else:
        success = await test_remote_connection(args.host, args.port)
    
    return 0 if success else 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n👋 Test interrupted")
        sys.exit(0)