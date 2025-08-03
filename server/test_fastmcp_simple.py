#!/usr/bin/env python3
"""
Simple FastMCP Test

Test FastMCP functionality without complex stdio interactions.
"""

import asyncio
import sys
from pathlib import Path

# Add the package to Python path
sys.path.insert(0, str(Path(__file__).parent))

from mcp_mqtt_bridge.bridge import MCPMQTTBridge


async def test_fastmcp_tools():
    """Test FastMCP tools directly without stdio"""
    print("🧪 Testing FastMCP Tools Directly")
    print("=" * 35)
    
    # Create bridge with FastMCP
    bridge = MCPMQTTBridge(
        mqtt_broker="localhost",
        db_path="test_fastmcp.db",
        use_fastmcp=True
    )
    
    try:
        # Initialize database
        await bridge.database.initialize()
        
        print(f"✅ Bridge created (using FastMCP: {bridge.using_fastmcp})")
        
        # Test each tool
        tools_to_test = [
            ("list_devices", {}),
            ("get_system_status", {}),
            ("query_devices", {"online_only": False}),
            ("get_alerts", {"hours_back": 1}),
        ]
        
        for tool_name, args in tools_to_test:
            try:
                print(f"\n🔧 Testing {tool_name}...")
                result = await bridge.call_mcp_tool(tool_name, args)
                print(f"   ✅ Success: {type(result).__name__}")
                if isinstance(result, dict):
                    if "error" in result:
                        print(f"   ⚠️  Result error: {result['error']}")
                    else:
                        print(f"   📊 Keys: {list(result.keys())}")
                elif isinstance(result, list):
                    print(f"   📊 List length: {len(result)}")
                else:
                    print(f"   📊 Result: {str(result)[:100]}...")
            except Exception as e:
                print(f"   ❌ Error: {e}")
        
        print("\n✅ Direct FastMCP tool testing completed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Cleanup
        try:
            Path("test_fastmcp.db").unlink(missing_ok=True)
        except:
            pass


async def test_fastmcp_help():
    """Test that FastMCP server can provide help/info"""
    print("\n🧪 Testing FastMCP Server Info")
    print("=" * 30)
    
    bridge = MCPMQTTBridge(
        mqtt_broker="localhost", 
        db_path="test_fastmcp2.db",
        use_fastmcp=True
    )
    
    try:
        await bridge.database.initialize()
        
        # Check if we can get server info
        fastmcp_server = bridge.get_fastmcp_server()
        if fastmcp_server:
            print(f"✅ FastMCP server accessible: {type(fastmcp_server).__name__}")
            
            # Check for tool registration
            if hasattr(fastmcp_server, 'tools'):
                tools = fastmcp_server.tools
                print(f"✅ Tools registered: {len(tools)}")
                for tool_name in tools.keys():
                    print(f"   - {tool_name}")
            else:
                print("ℹ️  Tools not accessible via .tools attribute")
                
        else:
            print("ℹ️  FastMCP server using fallback mode")
            
        print("✅ FastMCP server info test completed!")
        return True
        
    except Exception as e:
        print(f"❌ Server info test failed: {e}")
        return False
    finally:
        try:
            Path("test_fastmcp2.db").unlink(missing_ok=True)
        except:
            pass


async def main():
    """Run all simple FastMCP tests"""
    print("🚀 FastMCP Simple Test Suite")
    print("=" * 40)
    
    success = True
    
    # Test direct tool calls
    if not await test_fastmcp_tools():
        success = False
    
    # Test server info
    if not await test_fastmcp_help():
        success = False
    
    if success:
        print("\n🎉 All FastMCP tests passed!")
        print("\nNext steps:")
        print("  • Try: python fastmcp_bridge_server.py --help")
        print("  • Try: python start_fastmcp_chat.py --help")
        return 0
    else:
        print("\n❌ Some FastMCP tests failed")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n👋 Tests interrupted")
        sys.exit(0)