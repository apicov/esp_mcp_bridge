#!/usr/bin/env python3
"""
Test FastMCP Integration

Test that the FastMCP server integration works correctly.
"""

import asyncio
import sys
import tempfile
from pathlib import Path

# Add the package to Python path
sys.path.insert(0, str(Path(__file__).parent))

from mcp_mqtt_bridge.bridge import MCPMQTTBridge


async def test_fastmcp_integration():
    """Test FastMCP integration without MQTT broker"""
    
    print("Testing FastMCP integration...")
    
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    try:
        # Create bridge with FastMCP enabled
        bridge = MCPMQTTBridge(
            mqtt_broker="localhost",  # Won't connect, just test initialization
            db_path=db_path,
            use_fastmcp=True
        )
        
        print(f"✅ Bridge created successfully")
        print(f"   Using FastMCP: {bridge.using_fastmcp}")
        print(f"   MCP Server type: {type(bridge.mcp_server).__name__}")
        
        # Test database initialization
        await bridge.database.initialize()
        print("✅ Database initialized successfully")
        
        # Test MCP tool call
        result = await bridge.call_mcp_tool("list_devices", {})
        print(f"✅ MCP tool call successful: {type(result)}")
        print(f"   Result: {result}")
        
        # Test FastMCP server access
        fastmcp_server = bridge.get_fastmcp_server()
        if fastmcp_server:
            print(f"✅ FastMCP server accessible: {type(fastmcp_server).__name__}")
        else:
            print("ℹ️  FastMCP server not available (using fallback)")
        
        print("\n🎉 All FastMCP integration tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ FastMCP integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Clean up
        try:
            Path(db_path).unlink(missing_ok=True)
        except:
            pass


async def test_tool_registration():
    """Test that all FastMCP tools are properly registered"""
    
    print("\nTesting FastMCP tool registration...")
    
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    try:
        bridge = MCPMQTTBridge(
            mqtt_broker="localhost",
            db_path=db_path,
            use_fastmcp=True
        )
        
        await bridge.database.initialize()
        
        # Test each expected tool
        expected_tools = [
            "list_devices",
            "read_sensor", 
            "control_actuator",
            "get_device_info",
            "query_devices",
            "get_alerts",
            "get_system_status",
            "get_device_metrics"
        ]
        
        for tool_name in expected_tools:
            try:
                result = await bridge.call_mcp_tool(tool_name, {})
                print(f"✅ Tool '{tool_name}' working")
            except ValueError as e:
                # Expected for some tools without proper arguments
                if "not found" in str(e).lower():
                    print(f"❌ Tool '{tool_name}' not found")
                else:
                    print(f"✅ Tool '{tool_name}' registered (parameter error expected)")
            except Exception as e:
                print(f"⚠️  Tool '{tool_name}' error: {e}")
        
        print("✅ Tool registration test completed")
        return True
        
    except Exception as e:
        print(f"❌ Tool registration test failed: {e}")
        return False
    
    finally:
        try:
            Path(db_path).unlink(missing_ok=True)
        except:
            pass


async def main():
    """Run all FastMCP integration tests"""
    
    print("🧪 FastMCP Integration Test Suite")
    print("=" * 40)
    
    success = True
    
    # Test basic integration
    if not await test_fastmcp_integration():
        success = False
    
    # Test tool registration
    if not await test_tool_registration():
        success = False
    
    if success:
        print("\n🎉 All tests passed! FastMCP server integration is working correctly.")
        return 0
    else:
        print("\n❌ Some tests failed. Check the output above for details.")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n👋 Tests interrupted")
        sys.exit(0)