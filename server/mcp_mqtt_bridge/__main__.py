#!/usr/bin/env python3
"""
MCP-MQTT Bridge Server CLI

Command-line interface for running the MCP-MQTT Bridge Server.
"""

import asyncio
import argparse
import logging
import os
import sys
from pathlib import Path

from .bridge import MCPMQTTBridge

def setup_logging(log_level: str = "INFO"):
    """Setup logging configuration"""
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Invalid log level: {log_level}')
    
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="MCP-MQTT Bridge Server - Connect ESP32 IoT devices to LLMs"
    )
    
    # MQTT settings
    parser.add_argument(
        "--mqtt-broker", 
        default=os.getenv("MQTT_BROKER", "localhost"),
        help="MQTT broker hostname or IP address (default: localhost)"
    )
    parser.add_argument(
        "--mqtt-port", 
        type=int,
        default=int(os.getenv("MQTT_PORT", "1883")),
        help="MQTT broker port (default: 1883)"
    )
    parser.add_argument(
        "--mqtt-username",
        default=os.getenv("MQTT_USERNAME"),
        help="MQTT username for authentication"
    )
    parser.add_argument(
        "--mqtt-password", 
        default=os.getenv("MQTT_PASSWORD"),
        help="MQTT password for authentication"
    )
    
    # Database settings
    parser.add_argument(
        "--db-path",
        default=os.getenv("DB_PATH", "./data/bridge.db"),
        help="SQLite database file path (default: ./data/bridge.db)"
    )
    
    # System settings
    parser.add_argument(
        "--device-timeout",
        type=int,
        default=int(os.getenv("DEVICE_TIMEOUT_MINUTES", "5")),
        help="Device timeout in minutes (default: 5)"
    )
    parser.add_argument(
        "--log-level",
        default=os.getenv("LOG_LEVEL", "INFO"),
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)"
    )
    
    # MCP Server settings
    parser.add_argument(
        "--mcp-port",
        type=int,
        default=int(os.getenv("MCP_PORT", "8000")),
        help="MCP server port for remote connections (default: 8000)"
    )
    parser.add_argument(
        "--mcp-host",
        default=os.getenv("MCP_HOST", "0.0.0.0"),
        help="MCP server host to bind to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--enable-mcp-server",
        action="store_true",
        help="Enable MCP server for remote connections"
    )
    parser.add_argument(
        "--use-fastmcp",
        action="store_true",
        default=True,
        help="Use FastMCP implementation (default: True)"
    )
    parser.add_argument(
        "--stdio",
        action="store_true",
        help="Run FastMCP in stdio mode for client integration"
    )
    
    return parser.parse_args()

async def main():
    """Main entry point"""
    args = parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    # Create data directory if it doesn't exist
    db_path = Path(args.db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    logger.info("Starting MCP-MQTT Bridge Server...")
    logger.info(f"MQTT Broker: {args.mqtt_broker}:{args.mqtt_port}")
    logger.info(f"Database: {args.db_path}")
    logger.info(f"Device Timeout: {args.device_timeout} minutes")
    
    # Create and start bridge
    try:
        bridge = MCPMQTTBridge(
            mqtt_broker=args.mqtt_broker,
            mqtt_port=args.mqtt_port,
            mqtt_username=args.mqtt_username,
            mqtt_password=args.mqtt_password,
            db_path=str(db_path),
            device_timeout_minutes=args.device_timeout,
            use_fastmcp=args.use_fastmcp
        )
        
        # Handle stdio mode for FastMCP
        if args.stdio:
            logger.info("Running FastMCP bridge in stdio mode")
            
            # Initialize but don't start full bridge 
            await bridge.database.initialize()
            await bridge.mqtt.connect()
            
            # Run FastMCP stdio server
            await bridge.serve_mcp_stdio()
            return 0
        
        # Start the bridge
        await bridge.start()
        
        # Start MCP server if enabled
        mcp_task = None
        if args.enable_mcp_server:
            try:
                from .fast_mcp_server import run_mcp_server
                logger.info(f"Starting MCP server on {args.mcp_host}:{args.mcp_port}")
                
                # Run MCP server in background
                mcp_task = asyncio.create_task(
                    run_mcp_server(bridge, args.mcp_host, args.mcp_port)
                )
                
                # Wait for server to start
                await asyncio.sleep(2)
                logger.info("MCP server started successfully")
                
            except ImportError as e:
                logger.error(f"Failed to start MCP server: {e}")
                logger.error("Make sure MCP is installed: pip install mcp")
                return 1
            except Exception as e:
                logger.error(f"Error starting MCP server: {e}")
                return 1
        
        # Keep running
        if args.enable_mcp_server and mcp_task:
            logger.info("Bridge and MCP server running... Press Ctrl+C to stop")
            await asyncio.gather(
                asyncio.Event().wait(),  # Keep bridge running
                mcp_task
            )
        else:
            logger.info("Bridge running... Press Ctrl+C to stop")
            await asyncio.Event().wait()
        
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
    except Exception as e:
        logger.error(f"Error starting bridge: {e}")
        sys.exit(1)
    finally:
        try:
            await bridge.stop()
        except:
            pass
        logger.info("Bridge stopped")

if __name__ == "__main__":
    # Handle Windows event loop policy
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    asyncio.run(main()) 