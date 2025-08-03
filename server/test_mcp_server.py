#!/usr/bin/env python3
"""
Simple test script to verify MCP server functionality
"""

import asyncio
import logging
from mcp_mqtt_bridge.bridge import MCPMQTTBridge
from mcp_mqtt_bridge.fast_mcp_server import run_mcp_server

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    """Test the MCP server"""
    try:
        logger.info("🚀 Testing MCP server...")
        
        # Create bridge
        bridge = MCPMQTTBridge('localhost', 1883, db_path=':memory:')
        await bridge.start()
        logger.info("✅ Bridge started")
        
        # Start MCP server
        logger.info("🌐 Starting MCP server on port 8005...")
        await run_mcp_server(bridge, '127.0.0.1', 8005)
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())