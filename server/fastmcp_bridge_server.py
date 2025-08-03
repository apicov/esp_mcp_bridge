#!/usr/bin/env python3
"""
FastMCP Bridge Server

Standalone server that exposes ESP32 IoT device control through FastMCP.
This server can be used with FastMCP-compatible clients.

Usage:
    python fastmcp_bridge_server.py [--mqtt-broker localhost] [--db-path bridge.db]
    
    # For stdio mode (FastMCP client integration):
    python fastmcp_bridge_server.py --stdio
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add the package to Python path
sys.path.insert(0, str(Path(__file__).parent))

from mcp_mqtt_bridge.bridge import MCPMQTTBridge

logger = logging.getLogger(__name__)


async def main():
    """Main entry point for FastMCP bridge server"""
    parser = argparse.ArgumentParser(description="FastMCP ESP32 IoT Bridge Server")
    parser.add_argument("--mqtt-broker", default="localhost", 
                       help="MQTT broker hostname (default: localhost)")
    parser.add_argument("--mqtt-port", type=int, default=1883,
                       help="MQTT broker port (default: 1883)")
    parser.add_argument("--mqtt-username", help="MQTT username")
    parser.add_argument("--mqtt-password", help="MQTT password")
    parser.add_argument("--db-path", default="bridge.db",
                       help="Database file path (default: bridge.db)")
    parser.add_argument("--device-timeout", type=int, default=5,
                       help="Device timeout in minutes (default: 5)")
    parser.add_argument("--stdio", action="store_true",
                       help="Run in stdio mode for FastMCP client integration")
    parser.add_argument("--log-level", default="INFO",
                       choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                       help="Logging level (default: INFO)")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create bridge with FastMCP enabled
    bridge = MCPMQTTBridge(
        mqtt_broker=args.mqtt_broker,
        mqtt_port=args.mqtt_port,
        mqtt_username=args.mqtt_username,
        mqtt_password=args.mqtt_password,
        db_path=args.db_path,
        device_timeout_minutes=args.device_timeout,
        use_fastmcp=True  # Force FastMCP usage
    )
    
    try:
        if args.stdio:
            # Stdio mode for FastMCP client integration
            logger.info("Starting FastMCP bridge server in stdio mode")
            logger.info(f"MQTT broker: {args.mqtt_broker}:{args.mqtt_port}")
            logger.info(f"Database: {args.db_path}")
            
            # Start bridge components but not the full service loop
            logger.info("Initializing database...")
            await bridge.database.initialize()
            
            logger.info("Connecting to MQTT...")
            await bridge.mqtt.connect()
            
            # Serve FastMCP over stdio
            logger.info("Starting FastMCP stdio server...")
            await bridge.serve_mcp_stdio()
            
        else:
            # Regular bridge mode with HTTP server
            logger.info("Starting FastMCP bridge server")
            logger.info(f"MQTT broker: {args.mqtt_broker}:{args.mqtt_port}")
            logger.info(f"Database: {args.db_path}")
            
            # Start the full bridge
            await bridge.start()
            
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
    except Exception as e:
        logger.error(f"Error running FastMCP bridge server: {e}")
        return 1
    finally:
        try:
            await bridge.stop()
        except:
            pass
    
    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nShutdown complete")
        sys.exit(0)