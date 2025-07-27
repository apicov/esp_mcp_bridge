#!/usr/bin/env python3
"""
Simple test to verify MCP connection works
"""

import asyncio
import os
from chat_with_devices import IoTChatInterface

async def test_mcp_connection():
    """Test MCP connection without OpenAI"""
    
    # Use a dummy API key for testing connection only
    chat = IoTChatInterface("test-key")
    
    try:
        print("Testing MCP connection...")
        
        # Try to initialize MCP
        success = await chat.initialize_mcp()
        
        if success:
            print("✅ MCP connection successful!")
            print(f"Available tools: {len(chat.available_tools)}")
            for tool in chat.available_tools:
                print(f"  - {tool['function']['name']}: {tool['function']['description']}")
        else:
            print("❌ MCP connection failed")
            
        # Clean up
        await chat.cleanup()
        
    except Exception as e:
        print(f"❌ Error testing MCP connection: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_mcp_connection())